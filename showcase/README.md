# Showcase video

The source of the README showcase video, made with [Remotion](https://www.remotion.dev/).

A creator finds an image for a video edit, asks Claude Code to copy it with math, and puts the transparent result on the timeline.

## Render

```bash
npm install
npm run render      # writes out/showcase.mp4
npm run dev         # opens Remotion Studio
```

`npm run assets` copies the example files from `../assets` to `public/`. The scenes use these files:

- `great-wave-original.jpg`: Hokusai, *The Great Wave off Kanagawa*, c. 1831. Public domain.
- `great-wave-demo.mp4`: output of `trace_image.py --anim-style fourier`.
- `great-wave-transparent.webm`: output of `trace_image.py --mode color --colors 16 --lines --transparent --anim`.

The music is `showcase/music.mp3` ("Quiet Horizon", made with ElevenLabs Music). To change it, put another 31-second track there; `npm run assets` copies it, and the render adds it with a fade in and a fade out. Use only music that you have the rights to.

The sound effects (keys, clicks, whooshes, chimes) are made by code: `python sfx/gen_sfx.py` writes `sfx/*.wav`. Their frames are in the `SFX` list in `src/Root.tsx`.

Remotion has its own license. Read [remotion.dev/license](https://www.remotion.dev/license) before you use it in a company.
