#!/usr/bin/env python3
"""Camera arc: turn a flat clip into a 2.5D "real camera" arc move.

Pipeline: decode -> per-frame monocular depth (Depth Anything V2 Small, ONNX)
-> temporally smoothed depth -> depth-displaced mesh rendered by a perspective
camera that orbits a pivot on an eased arc (moderngl) -> ffmpeg encode.

Usage:
  camera_arc.py IN OUT [--start S] [--dur D] [--arc DEG] [--push P] ...
Run with the venv at ~/.claude/motion-kit/venv-camarc.
"""
import argparse, json, math, os, subprocess, sys
import numpy as np
import cv2
import moderngl
import onnxruntime as ort

MODEL = os.path.expanduser("~/.claude/motion-kit/models/da2s/onnx/model.onnx")


def probe(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height,r_frame_rate", "-of", "json", path])
    s = json.loads(out)["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return s["width"], s["height"], float(num) / float(den)


def read_frames(path, start, dur, w, h):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", path,
           "-vf", f"scale={w}:{h}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = w * h * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    p.wait()


class Depth:
    def __init__(self, dw=518, dh=294):
        self.s = ort.InferenceSession(MODEL, providers=["CoreMLExecutionProvider", "CPUExecutionProvider"])
        self.dw, self.dh = dw, dh
        self.mean = np.array([0.485, 0.456, 0.406], np.float32)
        self.std = np.array([0.229, 0.224, 0.225], np.float32)

    def __call__(self, rgb):
        x = cv2.resize(rgb, (self.dw, self.dh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        x = ((x - self.mean) / self.std).transpose(2, 0, 1)[None]
        return self.s.run(None, {"pixel_values": x})[0][0]  # relative disparity, bigger = nearer


def shift(a, dy, dx):
    """Shift without wrap-around (edge pixels repeat)."""
    h, w = a.shape[:2]
    p = np.pad(a, [(1, 1), (1, 1)] + [(0, 0)] * (a.ndim - 2), mode="edge")
    return p[1 - dy:1 - dy + h, 1 - dx:1 - dx + w]


def propagate_background(d, img, band=20, jump=0.04):
    """Clean plate behind occluders. A band on the near side of every depth jump is
    treated as unknown and refilled, ring by ring, from its farthest known neighbour,
    carrying that neighbour's colour and depth. Returns (background disparity, plate)."""
    k = 2 * band + 1
    near = d - cv2.erode(d, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))) > jump
    known = ~near
    cd, cc = d.copy(), img.copy()
    shifts = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    for _ in range(band + 2):
        best = np.full(d.shape, np.inf, np.float32)
        bc = np.zeros_like(cc)
        for dy, dx in shifts:
            sk, sd, sc = shift(known, dy, dx), shift(cd, dy, dx), shift(cc, dy, dx)
            m = ~known & sk & (sd < best)
            best[m], bc[m] = sd[m], sc[m]
        new = np.isfinite(best)
        if not new.any():
            break
        cd[new], cc[new] = best[new], bc[new]
        known |= new
    return cd, cc


def smootherstep(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * t * (t * (6 * t - 15) + 10)


def look_at(eye, target, up=(0, 1, 0), roll=0.0):
    f = target - eye; f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    c, s = math.cos(roll), math.sin(roll)
    r, u = c * r + s * u, -s * r + c * u
    m = np.identity(4, np.float32)
    m[0, :3], m[1, :3], m[2, :3] = r, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def perspective(fovy, aspect, n=0.05, f=50.0):
    t = 1 / math.tan(fovy / 2)
    m = np.zeros((4, 4), np.float32)
    m[0, 0], m[1, 1] = t / aspect, t
    m[2, 2], m[2, 3] = (f + n) / (n - f), 2 * f * n / (n - f)
    m[3, 2] = -1
    return m


VS = """
#version 330
uniform sampler2D disp;  // r = depth, g = background depth, b = edge strength
uniform mat4 mvp;
uniform float tx, ty, zn, zf;
uniform int layer;  // 0 = background plate, 1 = foreground
in vec2 uv;
out vec2 v_uv;
void main() {
    vec4 dd = texture(disp, uv);
    float d = layer == 0 ? dd.g : dd.r;
    float z = 1.0 / (d * (1.0 / zn - 1.0 / zf) + 1.0 / zf);
    vec2 ndc = uv * 2.0 - 1.0;
    vec3 p = vec3(ndc.x * tx * z, -ndc.y * ty * z, -z);
    v_uv = uv;
    gl_Position = mvp * vec4(p, 1.0);
}
"""
FS = """
#version 330
uniform sampler2D img, bgimg, disp;
uniform int layer;
in vec2 v_uv;
out vec4 color;
void main() {
    vec4 dd = texture(disp, v_uv);
    // stretched "rubber sheet" triangles across depth jumps are dropped; the plate shows through
    float alpha = layer == 1 ? 1.0 - smoothstep(0.6, 1.6, dd.b) : 1.0;
    if (alpha < 0.01) discard;
    vec3 c = layer == 1 ? texture(img, v_uv).rgb : texture(bgimg, v_uv).rgb;
    color = vec4(c, alpha);
}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--dur", type=float, default=10.0)
    ap.add_argument("--width", type=int, default=3840)
    ap.add_argument("--height", type=int, default=2160)
    ap.add_argument("--arc", type=float, default=9.0, help="total yaw sweep in degrees")
    ap.add_argument("--tilt", type=float, default=2.0, help="vertical arc in degrees (rises mid-move)")
    ap.add_argument("--push", type=float, default=0.06, help="dolly-in as fraction of pivot distance")
    ap.add_argument("--hfov", type=float, default=42.0, help="assumed source horizontal FOV")
    ap.add_argument("--overscan", type=float, default=1.16, help="crop factor that hides frame edges")
    ap.add_argument("--zfar", type=float, default=2.0, help="far/near depth ratio")
    ap.add_argument("--pivot-pct", type=float, default=80.0, help="disparity percentile used as orbit pivot")
    ap.add_argument("--drift", type=float, default=0.12, help="organic operator drift, degrees")
    ap.add_argument("--direction", type=int, default=1, choices=[-1, 1])
    ap.add_argument("--edge", type=float, default=0.018, help="disparity jump per texel treated as an occlusion edge")
    ap.add_argument("--grid", type=int, default=960, help="mesh columns")
    ap.add_argument("--proc-width", type=int, default=960, help="width for depth edges and the clean plate")
    ap.add_argument("--crf", type=int, default=15)
    a = ap.parse_args()

    sw, sh, fps = probe(a.inp)
    W, H = a.width, a.height
    tw, th = W, H  # texture size = output size (source is downscaled once)
    # 1) depth from a small decode, normalized per frame by robust percentiles, then smoothed in time
    est = Depth()
    pw, ph = a.proc_width, round(a.proc_width * H / W)
    disp, lo_hi, small = [], [], []
    for i, f in enumerate(read_frames(a.inp, a.start, a.dur, pw, ph)):
        small.append(f)
        d = est(f)
        lo_hi.append(np.percentile(d, [2, 98]))
        disp.append(d)
        if i % 25 == 0:
            print(f"depth {i}", file=sys.stderr)
    N = len(disp)
    lo_hi = np.array(lo_hi)
    k = cv2.getGaussianKernel(int(fps) | 1, fps / 4).ravel()
    lo_hi = np.stack([np.convolve(np.pad(lo_hi[:, j], len(k) // 2, mode="edge"), k, "valid") for j in range(2)], 1)
    ema = None
    pivots = []
    for i in range(N):
        d = np.clip((disp[i] - lo_hi[i, 0]) / (lo_hi[i, 1] - lo_hi[i, 0] + 1e-6), 0, 1)
        d = cv2.bilateralFilter(d.astype(np.float32), 7, 0.08, 5)
        ema = d if ema is None else 0.55 * ema + 0.45 * d
        # smooth upsample keeps contours clean; edge-aware filters copy screen texture into depth
        disp[i] = np.clip(cv2.resize(ema.astype(np.float32), (pw, ph), interpolation=cv2.INTER_CUBIC), 0, 1)
        pivots.append(np.percentile(ema, a.pivot_pct))
    # 1b) occlusion layers: background depth (foreground pushed back), edge band, inpainted plate
    layers, plates = [], []
    for i in range(N):
        # pull near surfaces ~2 px inside their silhouette so no background rim rides along
        d = cv2.erode(disp[i], cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        sc = pw / 518  # tuning below was done at 518 px wide
        bg, plate = propagate_background(d, small[i], band=round(20 * sc))
        bg = np.minimum(cv2.GaussianBlur(bg, (0, 0), 6 * sc), d)
        gx_ = np.abs(cv2.Sobel(d, cv2.CV_32F, 1, 0, ksize=3)) / 4
        gy_ = np.abs(cv2.Sobel(d, cv2.CV_32F, 0, 1, ksize=3)) / 4
        edge = np.maximum(gx_, gy_) * sc / a.edge  # >= 1.0 marks an occlusion edge
        edge = cv2.GaussianBlur(edge, (0, 0), 1.0)
        # revealed areas read as out-of-focus background, never as a hard cut-out shape
        filled = cv2.GaussianBlur((np.abs(plate.astype(np.int16) - small[i]).sum(2) > 0).astype(np.float32), (0, 0), 3 * sc)[..., None]
        soft = cv2.GaussianBlur(plate, (0, 0), 5 * sc).astype(np.float32)
        plates.append((plate * (1 - filled) + soft * filled).astype(np.uint8))
        layers.append(np.dstack([d, bg, edge, np.zeros_like(d)]).astype(np.float32))
    del small
    zn, zf = 1.0, a.zfar
    piv_d = float(np.median(pivots))
    piv_z = 1.0 / (piv_d * (1 / zn - 1 / zf) + 1 / zf)
    print(f"pivot disparity {piv_d:.3f} -> z {piv_z:.3f}", file=sys.stderr)

    # 2) GL setup
    ctx = moderngl.create_standalone_context()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.depth_func = "<="
    ctx.enable(moderngl.BLEND)
    ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
    prog = ctx.program(vertex_shader=VS, fragment_shader=FS)
    gx, gy = a.grid, int(a.grid * H / W)
    # mesh overhangs the frame by 10% (texture clamps) so the arc never reveals an edge
    u, v = np.meshgrid(np.linspace(-0.1, 1.1, gx + 1), np.linspace(-0.1, 1.1, gy + 1))
    verts = np.stack([u, v], -1).astype(np.float32).reshape(-1, 2)
    idx = []
    for y in range(gy):
        r0, r1 = y * (gx + 1), (y + 1) * (gx + 1)
        for x in range(gx):
            idx += [r0 + x, r1 + x, r0 + x + 1, r0 + x + 1, r1 + x, r1 + x + 1]
    vao = ctx.vertex_array(prog, [(ctx.buffer(verts), "2f", "uv")], ctx.buffer(np.array(idx, np.int32)))
    img_t = ctx.texture((tw, th), 3); img_t.filter = (moderngl.LINEAR, moderngl.LINEAR)
    dh_, dw_ = disp[0].shape
    disp_t = ctx.texture((dw_, dh_), 4, dtype="f4"); disp_t.filter = (moderngl.LINEAR, moderngl.LINEAR)
    bg_t = ctx.texture((dw_, dh_), 3); bg_t.filter = (moderngl.LINEAR, moderngl.LINEAR)
    for t_ in (img_t, disp_t, bg_t):
        t_.repeat_x = t_.repeat_y = False
    img_t.use(0); disp_t.use(1); bg_t.use(2)
    prog["img"] = 0; prog["disp"] = 1; prog["bgimg"] = 2
    hf = math.radians(a.hfov)
    tx = math.tan(hf / 2); ty = tx * H / W
    prog["tx"], prog["ty"], prog["zn"], prog["zf"] = tx, ty, zn, zf
    fbo = ctx.framebuffer(ctx.renderbuffer((W, H), 4, samples=4), ctx.depth_renderbuffer((W, H), samples=4))
    out_fbo = ctx.framebuffer(ctx.renderbuffer((W, H), 3))
    fovy = 2 * math.atan(ty / a.overscan)
    proj = perspective(fovy, W / H)

    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", f"{fps}", "-i", "-", "-ss", str(a.start), "-t", str(a.dur), "-i", a.inp,
        "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf),
        "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", a.out], stdin=subprocess.PIPE)

    pivot = np.array([0, 0, -piv_z], np.float32)
    A = math.radians(a.arc / 2) * a.direction
    for i, frame in enumerate(read_frames(a.inp, a.start, a.dur, tw, th)):
        if i >= N:
            break
        t = i / max(N - 1, 1)
        e = smootherstep(t)
        vel = 30 * t * t * (1 - t) ** 2  # derivative of smootherstep, peak 1.875
        yaw = A * (2 * e - 1)
        pitch = math.radians(a.tilt) * math.sin(math.pi * e)
        dr = math.radians(a.drift)
        yaw += dr * (math.sin(2 * math.pi * 0.11 * i / fps) + 0.5 * math.sin(2 * math.pi * 0.23 * i / fps + 1.3))
        pitch += dr * 0.7 * math.sin(2 * math.pi * 0.17 * i / fps + 0.4)
        roll = -math.radians(0.35) * a.direction * vel / 1.875  # gentle bank into the move
        dist = piv_z * (1 - a.push * e)
        eye = pivot + dist * np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)], np.float32)
        prog["mvp"].write((proj @ look_at(eye, pivot, roll=roll)).T.astype(np.float32).tobytes())
        # textures are uploaded top row first, so uv.y=0 is the image top
        img_t.write(frame.tobytes())
        disp_t.write(np.ascontiguousarray(layers[i]).tobytes())
        bg_t.write(np.ascontiguousarray(plates[i]).tobytes())
        fbo.use(); ctx.clear(0, 0, 0)
        prog["layer"] = 0; vao.render()
        prog["layer"] = 1; vao.render()
        ctx.copy_framebuffer(out_fbo, fbo)
        buf = np.frombuffer(out_fbo.read(components=3), np.uint8).reshape(H, W, 3)[::-1]  # GL reads bottom row first
        enc.stdin.write(buf.tobytes())
        if i % 25 == 0:
            print(f"render {i}/{N}", file=sys.stderr)
    enc.stdin.close(); enc.wait()
    print(a.out)


if __name__ == "__main__":
    main()
