import { Video } from "@remotion/media";
import { AbsoluteFill, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C } from "../theme";
import { Headline } from "./Headline";

// The real skill output: assets/great-wave-demo.mp4 (13 s), played at 2.2x.
export const Drawing: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 200 } });
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Headline
        title="Every curve is math."
        sub="Epicycles draw each region outline. Then the 16 color layers fade in."
        at={4}
      />
      <div
        style={{
          position: "absolute",
          left: 384,
          top: 270,
          width: 1152,
          height: 648,
          borderRadius: 18,
          overflow: "hidden",
          boxShadow: "0 40px 90px rgba(31,30,29,0.22)",
          scale: String(0.96 + 0.04 * enter),
          opacity: enter,
        }}
      >
        <Video
          src={staticFile("great-wave-demo.mp4")}
          muted
          playbackRate={2.2}
          style={{ width: "100%", height: "100%" }}
        />
      </div>
    </AbsoluteFill>
  );
};
