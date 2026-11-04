import { Audio } from "@remotion/media";
import { springTiming, TransitionSeries } from "@remotion/transitions";
import { iris } from "@remotion/transitions/iris";
import {
  AbsoluteFill,
  Composition,
  Folder,
  getStaticFiles,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Drawing } from "./scenes/Drawing";
import { Editor } from "./scenes/Editor";
import { EndCard } from "./scenes/EndCard";
import { Terminal } from "./scenes/Terminal";
import { whip as whipPan } from "./whip";

const FPS = 30;
const T = 18; // transition length in frames
const DROP = 165 + 54; // wave.webm (5.5 s), then a hold on the finished drawing; the iris takes the last 24
const whip = springTiming({ config: { damping: 200 }, durationInFrames: T });

// The camera never parks: a slow push and a small roll over each scene.
const Drift: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill
      style={{
        scale: interpolate(frame, [0, durationInFrames], [1, 1.04]),
        rotate: interpolate(frame, [0, durationInFrames], ["-0.25deg", "0.25deg"]),
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

const Find = () => (
  <Editor title="You found the perfect image for your video." sub="Now you need it as clean, editable motion." />
);
const Drop = () => (
  <Editor withOverlay title="Drop it on your timeline." sub="Transparent background. Sharp at any size." />
);

// Music fades in over 0.5 s and out over the last 1.5 s.
const Music: React.FC = () => {
  const { durationInFrames } = useVideoConfig();
  return (
    <Audio
      src={staticFile("music.mp3")}
      volume={(f) =>
        interpolate(f, [0, 15, durationInFrames - 45, durationInFrames], [0, 0.8, 0.8, 0], {
          extrapolateRight: "clamp",
        })
      }
    />
  );
};
const hasMusic = getStaticFiles().some((f) => f.name === "music.mp3");

// Scene starts on the full timeline (each transition overlaps two scenes).
const ASK = 120 - T;
const DRAW = ASK + 270 - T;
const DROP_AT = DRAW + 195 - T;
const END = DROP_AT + DROP - 24;

// Sound effects: [frame, file in public/sfx, volume]. Frames follow the scene animations.
const typing: [number, string, number][] = Array.from({ length: 30 }, (_, i) => [
  ASK + 27 + 2 * i,
  `key${(i * 7) % 4}`,
  0.22 + 0.08 * ((i * 5) % 3),
]);
const SFX: [number, string, number][] = [
  [28, "pop", 0.5], // the image card lands
  [ASK, "whoosh", 0.45],
  [ASK + 11, "click", 0.5], // image attached to the prompt
  ...typing,
  [ASK + 98, "enter", 0.6], // prompt sent
  [ASK + 112, "blip", 0.3], // tool lines
  [ASK + 128, "blip", 0.3],
  [ASK + 168, "blip", 0.25],
  [ASK + 186, "blip", 0.25],
  [ASK + 206, "chime", 0.35], // done
  [DRAW, "whoosh", 0.45],
  [DROP_AT, "whoosh", 0.45],
  [DROP_AT + 10, "swish", 0.35], // drag the clip to V2
  [DROP_AT + 22, "drop", 0.6], // drop it
  [DROP_AT + 165, "chime", 0.3], // the drawing is complete
  [END - 20, "shimmer", 0.35], // iris
  ...Array.from({ length: 8 }, (_, i): [number, string, number] => [END + 30 + 11 * i, i === 7 ? "blip" : "tick", 0.3]),
];

const Sfx: React.FC = () => (
  <>
    {SFX.map(([at, name, volume], i) => (
      <Sequence key={i} from={at} layout="none">
        <Audio src={staticFile(`sfx/${name}.wav`)} volume={volume} />
      </Sequence>
    ))}
  </>
);

const Showcase: React.FC = () => (
  <>
    {hasMusic ? <Music /> : null}
    <Sfx />
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={120} name="Find">
        <Drift>
          <Find />
        </Drift>
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={whipPan("left")} timing={whip} />
      <TransitionSeries.Sequence durationInFrames={270} name="Ask">
        <Drift>
          <Terminal />
        </Drift>
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={whipPan("up")} timing={whip} />
      <TransitionSeries.Sequence durationInFrames={195} name="Draw">
        <Drift>
          <Drawing />
        </Drift>
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={whipPan("right")} timing={whip} />
      <TransitionSeries.Sequence durationInFrames={DROP} name="Drop">
        <Drift>
          <Drop />
        </Drift>
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition
        presentation={iris({ width: 1920, height: 1080 })}
        timing={springTiming({ config: { damping: 200 }, durationInFrames: 24 })}
      />
      <TransitionSeries.Sequence durationInFrames={190} name="End">
        <Drift>
          <EndCard />
        </Drift>
      </TransitionSeries.Sequence>
    </TransitionSeries>
  </>
);

const size = { fps: FPS, width: 1920, height: 1080 };

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Showcase"
      component={Showcase}
      durationInFrames={120 + 270 + 195 + DROP + 190 - 3 * T - 24}
      {...size}
    />
    <Folder name="Scenes">
      <Composition id="Find" component={Find} durationInFrames={120} {...size} />
      <Composition id="Ask" component={Terminal} durationInFrames={270} {...size} />
      <Composition id="Draw" component={Drawing} durationInFrames={195} {...size} />
      <Composition id="Drop" component={Drop} durationInFrames={DROP} {...size} />
      <Composition id="End" component={EndCard} durationInFrames={190} {...size} />
    </Folder>
  </>
);
