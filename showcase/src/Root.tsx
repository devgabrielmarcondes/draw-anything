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
import { DROP, Editor } from "./scenes/Editor";
import { AGENTS, EndCard, START, STEP } from "./scenes/EndCard";
import { Hook } from "./scenes/Hook";
import { ASK, Terminal } from "./scenes/Terminal";

const CLIP = 120; // wave.webm: 4 s
import { whip as whipPan } from "./whip";

const FPS = 30;
const whip = springTiming({ config: { damping: 200 }, durationInFrames: 18 });

// Beat grid of music.mp3 ("Quiet Horizon"): 78.3 BPM, first beat at 0.63 s.
const beat = (k: number) => Math.round(18.8 + 22.99 * k);
// Scene changes (the middle of each transition) fall on beats. The music rises at beat 10.
const CUTS = [beat(3), beat(7), beat(18), beat(25), beat(33)];
const TRANS = [18, 18, 18, 18, 24]; // whip, whip, whip, whip, iris
const TOTAL = 930; // 31 s, the length of the track
// Scene starts and lengths from the cuts (a transition overlaps two scenes).
const STARTS = [0, ...CUTS.map((c, i) => c - TRANS[i] / 2)];
const LEN = STARTS.map((s, i) => (i < CUTS.length ? STARTS[i + 1] + TRANS[i] - s : TOTAL - s));
const [HOOK, FIND, ASK_AT, , DROP_AT, END] = STARTS;

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

// Sound effects: [frame, file in public/sfx, volume]. Frames come from the scene animations.
const whooshes = CUTS.slice(0, 4).map((c): [number, string, number] => [c - 9, "whoosh", 0.45]);
const typing = Array.from({ length: 27 }, (_, i): [number, string, number] => [
  ASK_AT + ASK.typeFrom + 2 * i,
  `key${(i * 7) % 4}`,
  0.22 + 0.08 * ((i * 5) % 3),
]);
const SFX: [number, string, number][] = [
  [HOOK + 19, "shimmer", 0.25], // the colors flood in
  ...whooshes,
  [FIND + 28, "pop", 0.5], // the image card lands
  [ASK_AT + 4, "swish", 0.3], // drag the image into the prompt
  [ASK_AT + ASK.drop, "pop", 0.45], // drop it: the image is attached
  ...typing,
  [ASK_AT + ASK.press, "click", 0.6], // click send
  [ASK_AT + 112, "blip", 0.3], // tool lines
  [ASK_AT + 128, "blip", 0.3],
  [ASK_AT + 168, "blip", 0.25],
  [ASK_AT + 186, "blip", 0.25],
  [ASK_AT + 206, "chime", 0.35], // done
  [DROP_AT + DROP.grab, "click", 0.5], // grab wave.webm
  [DROP_AT + DROP.grab + 2, "swish", 0.35],
  [DROP_AT + DROP.release, "drop", 0.6], // drop it on V2
  [DROP_AT + DROP.release + CLIP, "chime", 0.3], // the drawing is complete
  [END - 6, "shimmer", 0.35], // iris
  ...AGENTS.slice(1).map((_, i): [number, string, number] => [
    END + Math.round(START + STEP * i),
    i === AGENTS.length - 2 ? "blip" : "tick",
    0.3,
  ]),
];

const SFX_GAIN = 0.3; // all effects, under the music

const Sfx: React.FC = () => (
  <>
    {SFX.map(([at, name, volume], i) => (
      <Sequence key={i} from={at} layout="none">
        <Audio src={staticFile(`sfx/${name}.wav`)} volume={volume * SFX_GAIN} />
      </Sequence>
    ))}
  </>
);

const Showcase: React.FC = () => (
  <>
    {hasMusic ? <Music /> : null}
    <Sfx />
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={LEN[0]} name="Hook">
        <Drift>
          <Hook />
        </Drift>
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={whipPan("left")} timing={whip} />
      <TransitionSeries.Sequence durationInFrames={LEN[1]} name="Find">
        <Drift>
          <Find />
        </Drift>
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={whipPan("left")} timing={whip} />
      <TransitionSeries.Sequence durationInFrames={LEN[2]} name="Ask">
        <Drift>
          <Terminal />
        </Drift>
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={whipPan("up")} timing={whip} />
      <TransitionSeries.Sequence durationInFrames={LEN[3]} name="Draw">
        <Drift>
          <Drawing />
        </Drift>
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={whipPan("right")} timing={whip} />
      <TransitionSeries.Sequence durationInFrames={LEN[4]} name="Drop">
        <Drift>
          <Drop />
        </Drift>
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition
        presentation={iris({ width: 1920, height: 1080 })}
        timing={springTiming({ config: { damping: 200 }, durationInFrames: 24 })}
      />
      <TransitionSeries.Sequence durationInFrames={LEN[5]} name="End">
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
    <Composition id="Showcase" component={Showcase} durationInFrames={TOTAL} {...size} />
    <Folder name="Scenes">
      <Composition id="Hook" component={Hook} durationInFrames={LEN[0]} {...size} />
      <Composition id="Find" component={Find} durationInFrames={LEN[1]} {...size} />
      <Composition id="Ask" component={Terminal} durationInFrames={LEN[2]} {...size} />
      <Composition id="Draw" component={Drawing} durationInFrames={LEN[3]} {...size} />
      <Composition id="Drop" component={Drop} durationInFrames={LEN[4]} {...size} />
      <Composition id="End" component={EndCard} durationInFrames={LEN[5]} {...size} />
    </Folder>
  </>
);
