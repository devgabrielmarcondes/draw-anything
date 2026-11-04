# SDF in GLSL (Shadertoy, TouchDesigner, p5.js/WebGL, Blender)

The functions in `scripts/sdf.py` have direct GLSL equivalents. For Shadertoy, give a full shader like this one. Change only `scene()`.

```glsl
// Paste into shadertoy.com/new
float sdCircle(vec2 p, float r) { return length(p) - r; }
float sdBox(vec2 p, vec2 b) { vec2 d = abs(p) - b; return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0); }
float sdSegment(vec2 p, vec2 a, vec2 b) { vec2 pa = p - a, ba = b - a; float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0); return length(pa - ba * h); }
float opSmoothUnion(float a, float b, float k) { float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0); return mix(b, a, h) - k * h * (1.0 - h); }
vec2 opRepPolar(vec2 p, float n) { float s = 6.2831853 / n; float a = mod(atan(p.y, p.x) + s * 0.5, s) - s * 0.5; return length(p) * vec2(cos(a), sin(a)); }
mat2 rot(float a) { float c = cos(a), s = sin(a); return mat2(c, -s, s, c); }

float scene(vec2 p, float t) {
    vec2 q = opRepPolar(rot(t * 0.3) * p, 8.0);
    float petal = sdCircle((q - vec2(0.55, 0.0)) * vec2(1.0, 2.3), 0.3) / 2.3;
    return opSmoothUnion(petal, sdCircle(p, 0.22), 0.06);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 p = (2.0 * fragCoord - iResolution.xy) / iResolution.y * 1.3;
    float d = scene(p, iTime);
    float px = 2.6 / iResolution.y;
    vec3 bg = vec3(0.04, 0.05, 0.07);
    vec3 col = mix(bg, vec3(1.0, 0.44, 0.57), exp(-max(d, 0.0) / 0.08) * 0.6);   // glow
    col = mix(col, vec3(1.0, 0.44, 0.57), clamp(0.5 - d / px, 0.0, 1.0));       // fill
    fragColor = vec4(col, 1.0);
}
```

Python → GLSL: `translate(P,x,y)` → `p - vec2(x,y)`; `rotate(P,a)` → `rot(a) * p` (same direction); `mirror_x(P)` → `vec2(abs(p.x), p.y)`; `repeat(P,cx,cy)` → `p - c * round(p / c)`; `onion(d,w)` → `abs(d) - w`; `lerp` → `mix`.
For more primitives (star, heart, polygon, arc), use the Inigo Quilez "2D distance functions". The script uses the same formulas.
