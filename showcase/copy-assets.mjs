// Copy the example files from ../assets to public/ (they are not duplicated in git).
import { copyFileSync, mkdirSync } from "node:fs";

mkdirSync("public", { recursive: true });
for (const f of ["great-wave-original.jpg", "great-wave-demo.mp4", "great-wave-transparent.webm"]) {
  copyFileSync(`../assets/${f}`, `public/${f.replace("great-wave-transparent", "wave")}`);
}
