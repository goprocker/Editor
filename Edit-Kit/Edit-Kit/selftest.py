#!/usr/bin/env python3
"""Edit Kit self-test (Mac / Windows / Linux).

Checks every requirement, then builds and renders a real 3-second test video through the whole pipeline:
scaffold -> composition with kinetic captions + chip -> hyperframes check -> render -> SFX + music -> mix -> finalize -> QA.
Writes selftest_report.txt. If anything fails, send that file to the kit author.

  python selftest.py          (Windows)
  python3 selftest.py         (Mac / Linux)
"""
import json, re, os, platform, shutil, subprocess, sys, tempfile, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
SK = os.path.join(HERE, "skills")
if not os.path.isdir(SK):  # running from an installed copy
    SK = os.path.join(os.path.expanduser("~"), ".claude", "skills")
sys.path.insert(0, os.path.join(SK, "fx", "scripts"))
for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PY = sys.executable
results, log = [], []


def step(name, fn):
    t = time.time()
    try:
        msg = fn() or "ok"
        results.append((name, True, msg)); print(f"[PASS] {name}: {msg}")
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        results.append((name, False, msg)); print(f"[FAIL] {name}: {msg}")
        log.append(f"--- {name}\n{traceback.format_exc()}")
    log.append(f"{name} took {time.time() - t:.1f}s")


def run(cmd, cwd=None, timeout=900):
    exe = shutil.which(cmd[0]) or shutil.which(cmd[0] + ".cmd") or cmd[0]
    r = subprocess.run([exe] + cmd[1:], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    log.append(f"$ {' '.join(cmd)}\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    if r.returncode != 0:
        raise RuntimeError(f"exit {r.returncode}: {(r.stderr or r.stdout).strip()[-400:]}")
    return r.stdout


def need_python():
    if sys.version_info < (3, 9): raise RuntimeError(f"Python {platform.python_version()} is too old, need 3.9+")
    import numpy, PIL  # noqa: F401
    return f"Python {platform.python_version()}, numpy {numpy.__version__}, Pillow {PIL.__version__}"


def need_node():
    v = run(["node", "--version"]).strip()
    if int(v.lstrip("v").split(".")[0]) < 22: raise RuntimeError(f"Node {v} is too old: HyperFrames needs Node 22+ (nodejs.org, LTS)")
    return f"Node {v}"


def need_ffmpeg():
    from ff import ffmpeg
    p = ffmpeg(); v = run([p, "-version"]).splitlines()[0]
    return f"{v[:60]} ({p})"


def need_hyperframes():
    return "HyperFrames " + run(["npx", "--yes", "hyperframes", "--version"], timeout=600).strip().splitlines()[-1]


W = tempfile.mkdtemp(prefix="motionkit_selftest_")
P = os.path.join(W, "proj")
WORDS = [["Your", 0.2, 0.45], ["first", 0.45, 0.8], ["edit,", 0.8, 1.2], ["one", 1.3, 1.6], ["prompt.", 1.6, 2.2]]


def scaffold():
    run([PY, os.path.join(SK, "fx", "scripts", "new_project.py"), P, "--aspect", "16:9", "--duration", "3"])
    html = open(os.path.join(P, "index.html"), encoding="utf-8").read()
    html = html.replace('<div class="mk-layer" id="front"></div>', '''<div class="mk-layer" id="front">
        <div class="mk-chip mk-glass" id="c1" style="left:700px;top:300px"><span class="mk-tick"><svg viewBox="0 0 30 30"><path id="k1" d="M7 15.5 L13 21 L23 9"/></svg></span>Self-test café ✓</div>
      </div>''')
    html = html.replace('<div class="mk-caps" id="caps"></div>', '<div class="mk-caps" id="caps" style="left:360px;width:1200px;top:700px;height:200px"></div>')
    # insert the test edit right after the "build the edit here" comment, whatever its exact wording
    m = re.search(r"\n( *)// build the edit here[^\n]*\n", html)
    if not m: raise RuntimeError("could not find the 'build the edit here' line in the new project")
    html = html[:m.end()] + (f"      MK.captions({{ words: {json.dumps(WORDS)}, container: '#caps', end: 3 }});\n"
                        "      MK.chipIn('#c1', 1.3); MK.draw('#k1', 1.4, 0.22, 30);\n"
                        "      MK.zoom('#front', 0.8, { to: 1.08, hold: 0.6 });\n") + html[m.end():]
    open(os.path.join(P, "index.html"), "w", encoding="utf-8").write(html)
    json.dump([{"t": 1.3, "cue": "click"}, {"t": 0.8, "cue": "pop"}], open(os.path.join(W, "cues.json"), "w", encoding="utf-8"))
    return P


def check():
    out = run(["npx", "--yes", "hyperframes", "check"], cwd=P, timeout=600)
    if "Check failed" in out: raise RuntimeError(out[-600:])
    return "lint + layout passed"


def render():
    out = os.path.join(W, "silent.mp4")
    run(["npx", "--yes", "hyperframes", "render", "-o", out], cwd=P, timeout=1200)
    # the edit must actually move: compare a tiny greyscale copy of an early and a late frame
    from ff import ffmpeg
    grab = lambda t: subprocess.run([ffmpeg(), "-v", "error", "-ss", str(t), "-i", out, "-frames:v", "1", "-vf", "scale=64:36,format=gray",
                                     "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    a, b = grab(0.1), grab(2.5)
    diff = sum(abs(x - y) for x, y in zip(a, b)) / max(1, len(a))
    if diff < 1.0: raise RuntimeError(f"the rendered video does not move (frame difference {diff:.2f}): animations did not run")
    return f"{os.path.getsize(out) / 1e6:.2f} MB, animation verified (frame difference {diff:.1f})"


def audio():
    os.makedirs(os.path.join(W, "audio"), exist_ok=True)
    run([PY, os.path.join(SK, "sound", "scripts", "sfx_music.py"), "--cues", os.path.join(W, "cues.json"), "--dur", "3", "--out", os.path.join(W, "audio")])
    run([PY, os.path.join(SK, "sound", "scripts", "mix.py"), "--music", os.path.join(W, "audio", "music_raw.wav"),
         "--sfx", os.path.join(W, "audio", "sfx.wav"), "--dur", "3", "--out", os.path.join(W, "audio", "mix.wav")])
    return "sfx + music + mix"


def finalize():
    out = os.path.join(HERE if os.access(HERE, os.W_OK) else W, "selftest_video.mp4")
    run([PY, os.path.join(SK, "fx", "scripts", "finalize.py"), "--video", os.path.join(W, "silent.mp4"), "--audio", os.path.join(W, "audio", "mix.wav"), "--out", out])
    return out


def qa():
    out = run([PY, os.path.join(SK, "qa", "scripts", "qa.py"), results[-1][2], "--expect", "1920x1080", "--lufs", "-20",
               "--cues", os.path.join(W, "cues.json"), "--sfx", os.path.join(W, "audio", "sfx.wav")], cwd=W)
    if "[FAIL]" in out: raise RuntimeError(out.strip())
    return "format, loudness, sync"


print(f"Edit Kit self-test on {platform.system()} {platform.release()} ({platform.machine()})\n")
step("python + numpy + pillow", need_python)
step("node 22+", need_node)
step("ffmpeg", need_ffmpeg)
step("hyperframes", need_hyperframes)
step("skills found", lambda: f"{len([d for d in os.listdir(SK) if os.path.isfile(os.path.join(SK, d, 'SKILL.md'))])} skills in {SK}")
if all(ok for _, ok, _ in results):
    for name, fn in [("scaffold project", scaffold), ("hyperframes check", check), ("render video", render),
                     ("sound design + mix", audio), ("finalize mp4", finalize), ("QA", qa)]:
        step(name, fn)
        if not results[-1][1]: break
ok = all(r[1] for r in results)
rep = os.path.join(HERE if os.access(HERE, os.W_OK) else W, "selftest_report.txt")
with open(rep, "w", encoding="utf-8") as f:
    f.write(f"{platform.platform()} | Python {platform.python_version()}\n")
    for n, o, m in results: f.write(f"[{'PASS' if o else 'FAIL'}] {n}: {m}\n")
    f.write("\n\n" + "\n".join(log))
print(f"\n{'ALL PASSED - Edit Kit works on this computer.' if ok else 'SOMETHING FAILED - send selftest_report.txt to the person who shared the kit.'}")
print(f"report: {rep}")
sys.exit(0 if ok else 1)
