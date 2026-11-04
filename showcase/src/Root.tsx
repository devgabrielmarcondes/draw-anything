import { linearTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { Composition, Folder } from "remotion";
import { Drawing } from "./scenes/Drawing";
import { Editor } from "./scenes/Editor";
import { EndCard } from "./scenes/EndCard";
import { Terminal } from "./scenes/Terminal";

const FPS = 30;
const T = 15; // transition length in frames

const Find = () => <Editor title="You found the perfect image for your video." sub="Now you need it as clean, editable motion." />;
const Drop = () => (
  <Editor withOverlay title="Drop it on your timeline." sub="Transparent background. Sharp at any size." />
);

const Showcase: React.FC = () => (
  <TransitionSeries>
    <TransitionSeries.Sequence durationInFrames={120} name="Find">
      <Find />
    </TransitionSeries.Sequence>
    <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: T })} />
    <TransitionSeries.Sequence durationInFrames={270} name="Ask">
      <Terminal />
    </TransitionSeries.Sequence>
    <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: T })} />
    <TransitionSeries.Sequence durationInFrames={195} name="Draw">
      <Drawing />
    </TransitionSeries.Sequence>
    <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: T })} />
    <TransitionSeries.Sequence durationInFrames={150} name="Drop">
      <Drop />
    </TransitionSeries.Sequence>
    <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: T })} />
    <TransitionSeries.Sequence durationInFrames={120} name="End">
      <EndCard />
    </TransitionSeries.Sequence>
  </TransitionSeries>
);

const size = { fps: FPS, width: 1920, height: 1080 };

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Showcase" component={Showcase} durationInFrames={120 + 270 + 195 + 150 + 120 - 4 * T} {...size} />
    <Folder name="Scenes">
      <Composition id="Find" component={Find} durationInFrames={120} {...size} />
      <Composition id="Ask" component={Terminal} durationInFrames={270} {...size} />
      <Composition id="Draw" component={Drawing} durationInFrames={195} {...size} />
      <Composition id="Drop" component={Drop} durationInFrames={150} {...size} />
      <Composition id="End" component={EndCard} durationInFrames={120} {...size} />
    </Folder>
  </>
);
