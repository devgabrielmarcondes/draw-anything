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

Remotion has its own license. Read [remotion.dev/license](https://www.remotion.dev/license) before you use it in a company.
