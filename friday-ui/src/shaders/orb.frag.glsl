varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vPosition;
uniform float u_time;
uniform float u_audioLevel;
uniform vec3  u_color;
uniform float u_bloomStrength;

// 2D Simplex noise
vec3 mod289v3(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec2 mod289v2(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec3 permute3(vec3 x) { return mod289v3(((x*34.0)+1.0)*x); }

float snoise(vec2 v) {
  const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
  vec2 i  = floor(v + dot(v, C.yy));
  vec2 x0 = v - i + dot(i, C.xx);
  vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod289v2(i);
  vec3 p = permute3(permute3(i.y + vec3(0.0,i1.y,1.0)) + i.x + vec3(0.0,i1.x,1.0));
  vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
  m = m*m; m = m*m;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);
  vec3 g;
  g.x  = a0.x  * x0.x  + h.x  * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}

void main() {
  vec3 viewDir = normalize(cameraPosition - vPosition);
  float NdotV  = clamp(dot(normalize(vNormal), viewDir), 0.0, 1.0);

  vec2 uv = vUv * 2.0 - 1.0;
  float dist = length(uv);
  float angle = atan(uv.y, uv.x);

  float t = u_time * 0.72;
  float noiseA = snoise(vUv * 4.2 + vec2(t, t * 0.55)) * 0.5 + 0.5;
  float noiseB = snoise(vUv * 9.4 - vec2(t * 0.7, t * 1.2)) * 0.5 + 0.5;
  float plasma = mix(noiseA, noiseB, 0.45);

  float coreGlow = exp(-pow(dist * 3.8, 2.0)) * 1.6;
  // stronger, tighter main ring for arc-reactor feel
  float mainRing = exp(-pow((dist - 0.36) * 16.0, 2.0)) * (1.25 + 0.28 * sin(t * 4.2));
  float secondaryRing = exp(-pow((dist - 0.51) * 12.0, 2.0)) * 0.65;
  float detailRing = exp(-pow((dist - 0.60) * 16.0, 2.0)) * 0.24;
  float radialLines = pow(abs(sin(angle * 18.0 + t * 2.4)), 18.0) * smoothstep(0.7, 0.18, dist) * 0.62;
  // add a sharper audio-reactive pulse near the core
  float pulse = exp(-pow((dist - 0.24) * 14.0, 2.0)) * (0.55 + 0.6 * sin(t * 3.0)) * (1.0 + u_audioLevel * 1.2);
  float plasmaGlow = plasma * 0.18 * (1.0 + u_audioLevel * 0.6);
  float fresnel = pow(1.0 - NdotV, 2.6) * u_bloomStrength * 0.6;

  float energy = coreGlow + mainRing + secondaryRing + detailRing + radialLines * 0.4 + pulse * 0.16 + plasmaGlow;
  // Tony Stark / arc-reactor palette: bright cyan core, subtle warm gold rim highlights
  vec3 coreTint = vec3(0.85, 0.95, 1.0); // bluish-white core
  vec3 cyanAccent = vec3(0.2, 0.85, 1.0);
  vec3 goldRim = vec3(1.0, 0.68, 0.22);

  vec3 baseColor = coreTint * (coreGlow * 1.6 + pulse * 0.9);
  baseColor += cyanAccent * (mainRing * 0.9 + radialLines * 0.24 + plasmaGlow * 0.6);
  // warm metallic rim blended in by fresnel and secondary rings
  baseColor = mix(baseColor, goldRim * 0.72, secondaryRing * 0.6 + detailRing * 0.18 + fresnel * 0.22);
  baseColor = clamp(baseColor * energy, 0.0, 3.5);

  float alpha = clamp(energy * 0.98 + fresnel * 0.32, 0.0, 1.0);
  // slight white-hot center bloom
  gl_FragColor = vec4(baseColor, alpha);
}
