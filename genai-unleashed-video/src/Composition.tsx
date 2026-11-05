import { loadFont as loadAnton } from "@remotion/google-fonts/Anton";
import { loadFont as loadSora } from "@remotion/google-fonts/Sora";
import { Audio } from "@remotion/media";
import React from "react";
import {
  AbsoluteFill,
  Composition,
  Img,
  interpolate,
  OffthreadVideo,
  Sequence,
  spring,
  staticFile,
  Still,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const { fontFamily: display } = loadAnton("normal", {
  weights: ["400"],
  subsets: ["latin"],
});
const { fontFamily: body } = loadSora("normal", {
  weights: ["600"],
  subsets: ["latin"],
});

const INK = "#050b24";
const YELLOW = "#ffe500";
// Cyborg Ninja runs at 160 BPM, so one beat is 11.25 frames at 30fps.
const BEAT = 11.25;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const Cut: React.FC<{
  name: string;
  at: number;
  beats: number;
  children: React.ReactNode;
}> = ({ name, at, beats, children }) => (
  <Sequence
    name={name}
    from={Math.round(at * BEAT)}
    durationInFrames={Math.round(beats * BEAT)}
  >
    {children}
  </Sequence>
);

const Flash: React.FC<{ color?: string; frames?: number; peak?: number }> = ({
  color = "white",
  frames = 4,
  peak = 0.35,
}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill
      style={{
        backgroundColor: color,
        opacity: interpolate(frame, [0, frames], [peak, 0], clamp),
      }}
    />
  );
};

const Shot: React.FC<{
  src: string;
  tilt?: number;
  focus?: string;
  // Bold Impact: a black-and-white hit for the first frames of a punchline.
  mono?: boolean;
  children?: React.ReactNode;
}> = ({ src, tilt = 1, focus = "center", mono = false, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const punch = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 240 },
    durationInFrames: 14,
  });
  const scale = interpolate(punch, [0, 1], [1.3, 1.05]) + frame * 0.0014;
  const shake = interpolate(frame, [0, 9], [16, 0], clamp);
  return (
    <AbsoluteFill style={{ backgroundColor: INK, overflow: "hidden" }}>
      <Img
        src={staticFile(src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: focus,
          filter: `contrast(1.14) saturate(1.12) grayscale(${mono ? interpolate(frame, [6, 12], [1, 0], clamp) : 0}) blur(${interpolate(frame, [0, 4], [7, 0], clamp)}px)`,
          scale: String(scale),
          rotate: `${interpolate(punch, [0, 1], [tilt * 2.4, 0])}deg`,
          translate: `${Math.sin(frame * 2.9) * shake}px ${Math.cos(frame * 2.3) * shake}px`,
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle, rgba(0,0,0,0) 52%, rgba(3,8,30,0.72) 100%)",
        }}
      />
      {children}
      <Flash />
    </AbsoluteFill>
  );
};

const Panel: React.FC<{
  index: number;
  children: React.ReactNode;
}> = ({ index, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({
    frame: frame - index * 3,
    fps,
    config: { damping: 18, stiffness: 260 },
    durationInFrames: 12,
  });
  const direction = index % 2 === 0 ? -1 : 1;
  return (
    <div
      style={{
        position: "relative",
        flex: 1,
        height: "100%",
        overflow: "hidden",
        translate: `0 ${(1 - enter) * direction * 105}%`,
      }}
    >
      {children}
    </div>
  );
};

const Panels: React.FC<{
  children: React.ReactNode;
  overlay?: React.ReactNode;
}> = ({ children, overlay }) => (
  <AbsoluteFill style={{ backgroundColor: INK }}>
    <div
      style={{
        display: "flex",
        gap: 10,
        width: "100%",
        height: "100%",
      }}
    >
      {React.Children.map(children, (child, index) => (
        <Panel index={index}>{child}</Panel>
      ))}
    </div>
    {overlay}
  </AbsoluteFill>
);

const fill: React.CSSProperties = {
  position: "absolute",
  inset: 0,
  width: "100%",
  height: "100%",
  objectFit: "cover",
  filter: "contrast(1.14) saturate(1.12)",
};

const Pic: React.FC<{ src: string }> = ({ src }) => (
  <Img src={staticFile(src)} style={fill} />
);

const Footage: React.FC<{
  src: string;
  trimBefore?: number;
  playbackRate?: number;
}> = ({ src, trimBefore = 0, playbackRate = 1.25 }) => (
  <OffthreadVideo
    src={staticFile(src)}
    muted
    trimBefore={trimBefore}
    playbackRate={playbackRate}
    style={fill}
  />
);

const Slam: React.FC<{
  text: string;
  size?: number;
  color?: string;
  y?: number;
}> = ({ text, size = 300, color = "white", y = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const hit = spring({
    frame,
    fps,
    config: { damping: 13, stiffness: 300 },
    durationInFrames: 10,
  });
  const split = interpolate(frame, [0, 7], [18, 0], clamp);
  return (
    <AbsoluteFill
      style={{ alignItems: "center", justifyContent: "center", padding: 80 }}
    >
      <div
        style={{
          fontFamily: display,
          fontSize: size,
          lineHeight: 1.02,
          color,
          textAlign: "center",
          textTransform: "uppercase",
          scale: String(interpolate(hit, [0, 1], [2.1, 1]) + frame * 0.0012),
          opacity: interpolate(frame, [0, 2], [0, 1], clamp),
          translate: `0 ${y}px`,
          textShadow: `${split}px 0 0 #ff2a55, ${-split}px 0 0 #18e0ff, 0 12px 50px rgba(0,0,0,0.65)`,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

const Tag: React.FC<{ title: string; subtitle?: string }> = ({
  title,
  subtitle,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const sub = interpolate(frame, [14, 22], [0, 1], clamp);
  // Kinetic words, one pop per word, no boxes (Edit Kit house rule).
  return (
    <>
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(0deg, rgba(5,11,36,0.85) 0%, rgba(5,11,36,0) 45%)",
        }}
      />
      <div style={{ position: "absolute", left: 110, bottom: 96 }}>
        <div
          style={{
            display: "flex",
            gap: "0.28em",
            fontFamily: display,
            fontSize: 130,
            lineHeight: 1.05,
            color: YELLOW,
            textTransform: "uppercase",
            textShadow: "0 10px 40px rgba(0,0,0,0.7)",
          }}
        >
          {title.split(" ").map((word, i) => {
            const pop = spring({
              frame: frame - 3 - i * 4,
              fps,
              config: { damping: 13, stiffness: 300 },
              durationInFrames: 10,
            });
            return (
              <span
                key={word + i}
                style={{
                  display: "inline-block",
                  opacity: pop,
                  scale: String(interpolate(pop, [0, 1], [1.8, 1])),
                  transformOrigin: "left bottom",
                }}
              >
                {word}
              </span>
            );
          })}
        </div>
        {subtitle ? (
          <div
            style={{
              marginTop: 10,
              fontFamily: body,
              fontWeight: 600,
              fontSize: 56,
              color: "white",
              textShadow: "0 6px 24px rgba(0,0,0,0.8)",
              opacity: sub,
              translate: `${(1 - sub) * 50}px 0`,
            }}
          >
            {subtitle}
          </div>
        ) : null}
      </div>
    </>
  );
};

const Grid: React.FC = () => (
  <AbsoluteFill
    style={{
      backgroundColor: INK,
      backgroundImage:
        "linear-gradient(rgba(90,140,255,0.16) 2px, transparent 2px), linear-gradient(90deg, rgba(90,140,255,0.16) 2px, transparent 2px)",
      backgroundSize: "120px 120px",
    }}
  />
);

const PosterSlam: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const hit = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 240 },
    durationInFrames: 14,
  });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <Grid />
      <Img
        src={staticFile("poster.jpg")}
        style={{
          height: 1000,
          boxShadow: "0 30px 100px rgba(0,0,0,0.8)",
          scale: String(interpolate(hit, [0, 1], [1.9, 1]) + frame * 0.001),
          rotate: `${interpolate(hit, [0, 1], [-7, -1.5])}deg`,
        }}
      />
      <Flash />
    </AbsoluteFill>
  );
};

const CREDENTIALS = [
  "2nd Year CSE AI",
  "Google Student Ambassador '26",
  "Techfest IITB '26",
  "Co-Founder & CMO, LoopFound",
];

const SpeakerHero: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const portrait = spring({
    frame,
    fps,
    config: { damping: 16, stiffness: 220 },
    durationInFrames: 14,
  });
  const name = spring({
    frame: frame - 4,
    fps,
    config: { damping: 14, stiffness: 280 },
    durationInFrames: 12,
  });
  return (
    <AbsoluteFill>
      <Grid />
      <Img
        src={staticFile("dp-portrait.jpg")}
        style={{
          position: "absolute",
          left: 90,
          top: 90,
          width: 720,
          height: 900,
          objectFit: "cover",
          objectPosition: "center top",
          border: `10px solid ${YELLOW}`,
          translate: `${(1 - portrait) * -115}% 0`,
          scale: String(1 + frame * 0.0007),
        }}
      />
      <div style={{ position: "absolute", left: 880, top: 110, width: 950 }}>
        <div
          style={{
            fontFamily: body,
            fontWeight: 600,
            fontSize: 68,
            color: "white",
            opacity: name,
          }}
        >
          Hi, I'm
        </div>
        <div
          style={{
            fontFamily: display,
            fontSize: 250,
            lineHeight: 1.1,
            color: YELLOW,
            textTransform: "uppercase",
            transformOrigin: "left center",
            scale: String(interpolate(name, [0, 1], [1.7, 1])),
            opacity: name,
          }}
        >
          Gopinath
        </div>
        <div style={{ marginTop: 30 }}>
          {CREDENTIALS.map((line, i) => (
            <div
              key={line}
              style={{
                fontFamily: body,
                fontWeight: 600,
                fontSize: 50,
                lineHeight: 1.55,
                color: "white",
                opacity: interpolate(
                  frame,
                  [14 + i * BEAT, 17 + i * BEAT],
                  [0, 1],
                  clamp,
                ),
                translate: `${interpolate(
                  frame,
                  [14 + i * BEAT, 20 + i * BEAT],
                  [50, 0],
                  clamp,
                )}px 0`,
              }}
            >
              {line}
            </div>
          ))}
        </div>
      </div>
      <Flash />
    </AbsoluteFill>
  );
};

// Screen position of the speaker's head in photo09.jpg at width 1920.
const SPEAKER_X = 970;
const SPEAKER_Y = 430;
const RING = 235;

// Beats drive the cold open: hit on 0, ring on 4, label on 6 with the words "the speaker".
const SpeakerSpotlight: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const slam = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 260 },
    durationInFrames: 12,
  });
  const push = spring({
    frame: frame - 4 * BEAT,
    fps,
    config: { damping: 18, stiffness: 240 },
    durationInFrames: 11,
  });
  const label = spring({
    frame: frame - 6 * BEAT,
    fps,
    config: { damping: 13, stiffness: 300 },
    durationInFrames: 10,
  });
  const caption = spring({
    frame: frame - 8 * BEAT,
    fps,
    config: { damping: 15, stiffness: 280 },
    durationInFrames: 10,
  });
  // Stepped zoom on every second beat once the label has landed.
  const sinceStep = Math.max(0, frame - 8 * BEAT);
  const steps = Math.floor(sinceStep / (2 * BEAT));
  const kick = frame >= 8 * BEAT ? 0.04 * Math.exp(-(sinceStep % (2 * BEAT)) / 3) : 0;
  const zoom =
    interpolate(slam, [0, 1], [1.45, 1]) +
    interpolate(push, [0, 1], [0, 0.15]) +
    steps * 0.015 +
    kick +
    frame * 0.0005;
  const shake = interpolate(frame, [0, 10], [22, 0], clamp);
  const radius = interpolate(push, [0, 1], [0, RING]);
  const photo: React.CSSProperties = {
    position: "absolute",
    left: 0,
    top: -180,
    width: 1920,
    height: 1440,
    transformOrigin: `${SPEAKER_X}px ${SPEAKER_Y + 180}px`,
    scale: String(zoom),
    translate: `${Math.sin(frame * 2.9) * shake}px ${Math.cos(frame * 2.3) * shake}px`,
  };
  return (
    <AbsoluteFill style={{ backgroundColor: INK, overflow: "hidden" }}>
      <Img
        src={staticFile("photo09.jpg")}
        style={{
          ...photo,
          filter: `contrast(1.14) saturate(${interpolate(push, [0, 1], [1.15, 0])}) brightness(${interpolate(push, [0, 1], [1, 0.52])}) blur(${interpolate(frame, [0, 5], [10, 0], clamp)}px)`,
        }}
      />
      <AbsoluteFill
        style={{
          clipPath: `circle(${radius}px at ${SPEAKER_X}px ${SPEAKER_Y}px)`,
        }}
      >
        <Img
          src={staticFile("photo09.jpg")}
          style={{ ...photo, filter: "contrast(1.14) saturate(1.2) brightness(1.08)" }}
        />
      </AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: SPEAKER_X - radius,
          top: SPEAKER_Y - radius,
          width: radius * 2,
          height: radius * 2,
          borderRadius: "50%",
          border: `10px solid ${YELLOW}`,
          boxSizing: "border-box",
          opacity: radius > 4 ? 1 : 0,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: SPEAKER_X + RING,
          top: SPEAKER_Y - 4,
          width: 70 * label,
          height: 8,
          backgroundColor: YELLOW,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: SPEAKER_X + RING + 70,
          top: SPEAKER_Y - 92,
          opacity: label,
          transformOrigin: "left center",
          scale: String(interpolate(label, [0, 1], [1.8, 1])),
        }}
      >
        <div
          style={{
            color: YELLOW,
            fontFamily: display,
            fontSize: 110,
            lineHeight: 1.1,
            textTransform: "uppercase",
            textShadow: "0 8px 30px rgba(0,0,0,0.8)",
          }}
        >
          The Speaker
        </div>
        <div
          style={{
            color: "white",
            fontFamily: body,
            fontWeight: 600,
            fontSize: 58,
            textShadow: "0 6px 24px rgba(0,0,0,0.85)",
          }}
        >
          Gopinath R
        </div>
        <div
          style={{
            marginTop: 6,
            color: YELLOW,
            fontFamily: body,
            fontWeight: 600,
            fontSize: 46,
            textShadow: "0 6px 24px rgba(0,0,0,0.85)",
            opacity: caption,
            translate: `${(1 - caption) * 60}px 0`,
          }}
        >
          Explaining GenAI
        </div>
      </div>
      <Flash frames={6} peak={0.9} />
      <Sequence from={Math.round(6 * BEAT)} layout="none">
        <Flash frames={5} peak={0.5} color={YELLOW} />
      </Sequence>
    </AbsoluteFill>
  );
};

const Credits: React.FC = () => {
  const frame = useCurrentFrame();
  const details = interpolate(frame, [14, 24], [0, 1], clamp);
  return (
    <AbsoluteFill>
      <Grid />
      <Slam text="From Ideas to Innovation" size={150} color={YELLOW} y={-290} />
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          color: "white",
          fontFamily: body,
          fontWeight: 600,
          opacity: details,
          translate: `0 ${60 + (1 - details) * 40}px`,
        }}
      >
        <div style={{ fontSize: 76 }}>Speaker: Gopinath R</div>
        <div style={{ fontSize: 60, marginTop: 18 }}>
          30 October 2026 · SCAS block
        </div>
        <div style={{ fontSize: 44, marginTop: 24, lineHeight: 1.35 }}>
          Department of CSE (Artificial Intelligence)
          <br />
          Sathyabama Institute of Science and Technology
        </div>
        <div style={{ fontSize: 28, marginTop: 34, opacity: 0.85 }}>
          Music: "Cyborg Ninja" by Kevin MacLeod (incompetech.com), CC BY 4.0
        </div>
      </AbsoluteFill>
      <Flash frames={6} />
    </AbsoluteFill>
  );
};

// Racks focus onto the group, then slams the title on the words "GenAI Unleashed".
const GroupFinale: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const title = spring({
    frame: frame - 110,
    fps,
    config: { damping: 14, stiffness: 240 },
    durationInFrames: 14,
  });
  const photo: React.CSSProperties = {
    position: "absolute",
    left: 0,
    top: -360,
    width: 1920,
    height: 1440,
    transformOrigin: "960px 930px",
    scale: String(interpolate(frame, [0, 200], [1.09, 1], clamp)),
  };
  return (
    <AbsoluteFill style={{ backgroundColor: INK, overflow: "hidden" }}>
      <Img
        src={staticFile("group3.jpg")}
        style={{ ...photo, filter: "blur(14px) brightness(0.38) saturate(0.7)" }}
      />
      <AbsoluteFill
        style={{
          opacity: interpolate(frame, [6, 30], [0, 1], clamp),
          maskImage:
            "linear-gradient(180deg, transparent 12%, black 24%, black 84%, transparent 97%)",
        }}
      >
        <Img
          src={staticFile("group3.jpg")}
          style={{ ...photo, filter: "contrast(1.1) saturate(1.16) brightness(1.06)" }}
        />
      </AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 28,
          textAlign: "center",
          fontFamily: display,
          fontSize: 190,
          lineHeight: 1.05,
          color: YELLOW,
          textTransform: "uppercase",
          textShadow: "0 10px 40px rgba(0,0,0,0.75)",
          opacity: title,
          scale: String(interpolate(title, [0, 1], [1.7, 1])),
        }}
      >
        GenAI Unleashed
      </div>
      <Flash frames={8} peak={0.85} />
    </AbsoluteFill>
  );
};

const Strobe: React.FC<{ at: number; photos: string[] }> = ({ at, photos }) => (
  <>
    {photos.map((src, i) => (
      <Cut key={src} name={`Strobe ${src}`} at={at + i / 2} beats={0.5}>
        <Shot src={src} tilt={i % 2 === 0 ? 1 : -1} />
      </Cut>
    ))}
  </>
);

// Punches the whole frame on the kick and snare grid during both drops.
const BeatPulse: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const inDrop =
    frame < 16 * BEAT ||
    (frame >= 24 * BEAT && frame < 56 * BEAT) ||
    (frame >= 64 * BEAT && frame < 84 * BEAT);
  const sinceBeat = frame % BEAT;
  const pulse = inDrop ? 0.022 * Math.exp(-sinceBeat / 2.5) : 0;
  return (
    <AbsoluteFill style={{ scale: String(1 + pulse), overflow: "hidden" }}>
      {children}
    </AbsoluteFill>
  );
};

export const EventRecap: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: INK }}>
      <BeatPulse>
        {/* Cold open: the voiceover baked into music.wav starts 10 frames in */}
        <Cut name="Speaker spotlight" at={0} beats={16}>
          <SpeakerSpotlight />
        </Cut>

        {/* Intro: the poster tagline, one word per beat over the room */}
        <Cut name="FROM" at={16} beats={1}>
          <Shot src="photo06.jpg">
            <AbsoluteFill style={{ backgroundColor: "rgba(5,11,36,0.68)" }} />
            <Slam text="From" />
          </Shot>
        </Cut>
        <Cut name="IDEAS" at={17} beats={1}>
          <Shot src="photo02.jpg" tilt={-1}>
            <AbsoluteFill style={{ backgroundColor: "rgba(5,11,36,0.68)" }} />
            <Slam text="Ideas" color={YELLOW} />
          </Shot>
        </Cut>
        <Cut name="TO" at={18} beats={1}>
          <Shot src="photo07.jpg">
            <AbsoluteFill style={{ backgroundColor: "rgba(5,11,36,0.68)" }} />
            <Slam text="To" />
          </Shot>
        </Cut>
        <Cut name="INNOVATION" at={19} beats={2}>
          <Shot src="photo01.jpg" tilt={-1} mono>
            <AbsoluteFill style={{ backgroundColor: "rgba(5,11,36,0.68)" }} />
            <Slam text="Innovation" color={YELLOW} size={340} />
          </Shot>
        </Cut>
        <Cut name="Poster" at={21} beats={2}>
          <PosterSlam />
        </Cut>
        <Strobe
          at={23}
          photos={["photo08.jpg", "photo11.jpg"]}
        />

        {/* Drop 1 */}
        <Cut name="Title slam" at={24} beats={4}>
          <Shot src="photo08.jpg" mono>
            <AbsoluteFill style={{ backgroundColor: "rgba(5,11,36,0.55)" }} />
            <Slam text="GenAI Unleashed" size={270} color={YELLOW} />
            <Flash peak={0.85} />
          </Shot>
        </Cut>
        <Cut name="Clip 1 panels" at={28} beats={4}>
          <Panels>
            <Footage src="clip1.mp4" trimBefore={0} />
            <Footage src="clip1.mp4" trimBefore={70} />
          </Panels>
        </Cut>
        <Cut name="Clip 2 panels" at={32} beats={4}>
          <Panels>
            <Footage src="clip2.mp4" trimBefore={0} />
            <Footage src="clip2.mp4" trimBefore={130} />
            <Footage src="clip2.mp4" trimBefore={270} />
          </Panels>
        </Cut>
        <Cut name="Pointing" at={36} beats={2}>
          <Shot src="photo01.jpg" />
        </Cut>
        <Cut name="Close up" at={38} beats={2}>
          <Shot src="photo09.jpg" tilt={-1} />
        </Cut>
        <Cut name="How AI paints" at={40} beats={4}>
          <Shot src="photo02.jpg">
            <Tag title="How AI paints" subtitle="From noise to picture" />
          </Shot>
        </Cut>
        <Cut name="Clip 3 panels" at={44} beats={4}>
          <Panels>
            <Footage src="clip3.mp4" trimBefore={70} />
            <Footage src="clip3.mp4" trimBefore={200} />
          </Panels>
        </Cut>
        <Cut name="Talk panels" at={48} beats={4}>
          <Panels>
            <Pic src="photo10.jpg" />
            <Pic src="photo11.jpg" />
            <Pic src="photo08.jpg" />
          </Panels>
        </Cut>
        <Cut name="Fast 1" at={52} beats={1}>
          <Shot src="photo11.jpg" />
        </Cut>
        <Cut name="Fast 2" at={53} beats={1}>
          <Shot src="photo10.jpg" tilt={-1} />
        </Cut>
        <Cut name="Fast 3" at={54} beats={1}>
          <Shot src="photo07.jpg" />
        </Cut>
        <Cut name="Fast 4" at={55} beats={1}>
          <Shot src="photo02.jpg" tilt={-1} />
        </Cut>

        {/* Breakdown */}
        <Cut name="Gopinath hero" at={56} beats={6}>
          <SpeakerHero />
        </Cut>
        <Strobe
          at={62}
          photos={["photo11.jpg", "photo08.jpg", "photo06.jpg", "photo09.jpg"]}
        />

        {/* Drop 2 */}
        <Cut name="Clip 2 big" at={64} beats={4}>
          <Panels>
            <Footage src="clip2.mp4" trimBefore={60} />
            <Footage src="clip3.mp4" trimBefore={120} />
            <Footage src="clip2.mp4" trimBefore={340} />
          </Panels>
        </Cut>
        <Cut name="Gesture" at={68} beats={4}>
          <Shot src="photo11.jpg" tilt={-1} />
        </Cut>
        <Cut name="Clip 3 panels 2" at={72} beats={4}>
          <Panels>
            <Footage src="clip3.mp4" trimBefore={0} />
            <Footage src="clip3.mp4" trimBefore={250} />
            <Footage src="clip2.mp4" trimBefore={190} />
          </Panels>
        </Cut>
        <Cut name="Group photo 1" at={76} beats={8}>
          <Shot src="group4.jpg">
            <Tag title="Everyone who showed up" />
          </Shot>
        </Cut>
        {/* Ending: the closing voiceover starts 20 frames into the finale */}
        <Cut name="Credits" at={84} beats={10}>
          <Credits />
        </Cut>
        <Cut name="Group finale" at={94} beats={22}>
          <GroupFinale />
        </Cut>
      </BeatPulse>
      <Audio name="Music" src={staticFile("music.wav")} />
    </AbsoluteFill>
  );
};

// WhatsApp crops a DP to a circle, so everything important stays inside it.
export const WhatsAppDp: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: INK, overflow: "hidden" }}>
    <Img
      src={staticFile("dp-portrait.jpg")}
      style={{
        width: "100%",
        height: "100%",
        objectFit: "cover",
        filter: "contrast(1.08) saturate(1.15)",
      }}
    />
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(180deg, rgba(5,11,36,0) 62%, rgba(5,11,36,0.95) 84%)",
      }}
    />
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: 770,
        textAlign: "center",
        fontFamily: display,
        fontSize: 118,
        lineHeight: 1,
        color: YELLOW,
        textTransform: "uppercase",
      }}
    >
      GenAI Unleashed
    </div>
    <div
      style={{
        position: "absolute",
        inset: 8,
        borderRadius: "50%",
        border: `14px solid ${YELLOW}`,
      }}
    />
  </AbsoluteFill>
);

export const MyComposition = () => {
  return (
    <>
      <Composition
        id="GenAIUnleashed"
        component={EventRecap}
        durationInFrames={1305}
        fps={30}
        width={1920}
        height={1080}
      />
      <Still id="WhatsAppDp" component={WhatsAppDp} width={1080} height={1080} />
    </>
  );
};
