// Copy the example files from ../assets to public/ (they are not duplicated in git).
import { copyFileSync, cpSync, existsSync, mkdirSync } from "node:fs";

mkdirSync("public", { recursive: true });
for (const f of ["great-wave-original.jpg", "great-wave-demo.mp4", "great-wave-transparent.webm"]) {
  copyFileSync(`../assets/${f}`, `public/${f.replace("great-wave-transparent", "wave")}`);
}
// Optional soundtrack: showcase/music.mp3 (the video renders silent without it).
if (existsSync("music.mp3")) copyFileSync("music.mp3", "public/music.mp3");
// Sound effects, made by sfx/gen_sfx.py.
cpSync("sfx", "public/sfx", { recursive: true, filter: (f) => !f.endsWith(".py") });
