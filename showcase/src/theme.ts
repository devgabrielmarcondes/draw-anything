import { loadFont as loadSerif } from "@remotion/google-fonts/Newsreader";
import { loadFont as loadSans } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { Easing } from "remotion";

export const serif = loadSerif("normal", { weights: ["400", "500"], subsets: ["latin"] }).fontFamily;
export const sans = loadSans("normal", { weights: ["400", "500", "600"], subsets: ["latin"] }).fontFamily;
export const mono = loadMono("normal", { weights: ["400", "500"], subsets: ["latin"] }).fontFamily;

export const C = {
  bg: "#F4F1EA",
  ink: "#1F1E1D",
  muted: "#77736A",
  coral: "#D97757",
  ui: "#1C1B19",
  panel: "#262522",
  line: "#3A3935",
  uiText: "#E9E6DF",
  uiMuted: "#9C988F",
};

export const ease = Easing.bezier(0.16, 1, 0.3, 1);
export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
