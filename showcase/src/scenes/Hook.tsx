import { Video } from "@remotion/media";
import { AbsoluteFill, interpolate, staticFile, useCurrentFrame } from "remotion";
import { C } from "../theme";
import { Headline } from "./Headline";

// The payoff first: the end of assets/great-wave-demo.mp4, where the epicycles finish and the colors flood in.
export const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Headline title="Copy any image with math." at={0} />
      <div
        style={{
          position: "absolute",
          left: 240,
          top: 200,
          width: 1440,
          height: 810,
          borderRadius: 18,
          overflow: "hidden",
          boxShadow: "0 40px 90px rgba(31,30,29,0.22)",
          scale: String(interpolate(frame, [0, 90], [1.03, 1])),
        }}
      >
        <Video
          src={staticFile("great-wave-demo.mp4")}
          muted
          trimBefore={288}
          playbackRate={1.4}
          style={{ width: "100%", height: "100%" }}
        />
      </div>
    </AbsoluteFill>
  );
};
