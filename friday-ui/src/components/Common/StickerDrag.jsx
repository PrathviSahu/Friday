import React, { useEffect, useRef, useCallback, useState } from 'react';

// Default sticker image
const DEFAULT_IMAGE =
    "https://imagedelivery.net/IEUjvl3YUlxY-MrTpOAWDQ/3fb4a247-64e9-4c54-2391-86598eebfe00/w=800";

const RENDER_SCALE = 2;
const PAD_BASE = 20;
const MESH_GRID_SIZE = 32;
const DRAG_Z_INDEX_BASE = 1000;

let zIndexCounter = DRAG_Z_INDEX_BASE;
function getNextZIndex() {
    zIndexCounter += 1;
    return zIndexCounter;
}

const DRAG_TILT_SENSITIVITY = 3;
const DRAG_TILT_SMOOTHING = 0.05;
const SHEEN_TILT_SHIFT = 0.05;
const SHEEN_TILT_DEADZONE = 0.035;
const ANIM_SPEED = 1.92;
const HOLO_MOTION_BUMP = 0.15;
const HOLO_MOTION_DECAY = 0.88;

// ============================================================================
// WebGL Shaders (OriginKit Vinyl Sticker Peel Engine)
// ============================================================================

const VERTEX_SHADER = `
attribute vec2 aPos;
attribute vec2 aUV;
uniform float uPeel;
uniform float uLift;
uniform float uPeelAngle;
uniform float uPasting;
uniform float uScale;
uniform float uElevation;
varying vec2 vUV;
varying float vHi;
varying float vSh;

void main() {
    vUV = aUV;
    vec2 p = aPos;
    vHi = 0.0;
    vSh = 0.0;

    if (uPeel > 0.0) {
        vec2 peelAxis = vec2(cos(uPeelAngle), sin(uPeelAngle));
        vec2 uvCentered = aUV - vec2(0.5);
        float proj = dot(uvCentered, peelAxis);
        float diag = 0.5 - proj;

        float peelLine = -0.3 + uPeel * 2.0;

        float rampWidth = 0.6;
        float lifted = smoothstep(peelLine - rampWidth, peelLine, diag);
        lifted = 1.0 - lifted;

        float scale = 1.0 + lifted * uElevation;
        p *= scale;

        float inRamp = smoothstep(peelLine - rampWidth, peelLine - rampWidth * 0.5, diag) *
                       smoothstep(peelLine + 0.05, peelLine - rampWidth * 0.3, diag);

        float curveAmount = uPasting > 0.5 ? 0.06 : 0.12;
        p += (-peelAxis) * inRamp * curveAmount;

        float t = smoothstep(peelLine - rampWidth, peelLine, diag);
        vHi = inRamp * 0.75 * pow(1.0 - t, 1.2);
        vSh = inRamp * 0.75 * pow(t, 1.2);
    }

    gl_Position = vec4(p * uScale, 0.0, 1.0);
}
`;

const FRAGMENT_SHADER = `
precision mediump float;
uniform sampler2D uTex;
uniform vec2 uTilt;
uniform float uSheenStrength;
uniform float uSheenTiltShift;
uniform float uSheenTiltDeadzone;
uniform float uMaxTiltDeg;
uniform float uHoloMode;
uniform float uHoloMotion;
uniform vec3 uSheenColor;
varying vec2 vUV;
varying float vHi;
varying float vSh;

vec3 overlayBlend(vec3 base, vec3 blend) {
    return mix(2.0 * base * blend, 1.0 - 2.0 * (1.0 - base) * (1.0 - blend), step(0.5, base));
}

vec3 hsl2rgb(float h, float s, float l) {
    float c = (1.0 - abs(2.0 * l - 1.0)) * s;
    float x = c * (1.0 - abs(mod(h * 6.0, 2.0) - 1.0));
    float m = l - c * 0.5;
    vec3 rgb;
    if (h < 1.0/6.0) rgb = vec3(c, x, 0.0);
    else if (h < 2.0/6.0) rgb = vec3(x, c, 0.0);
    else if (h < 3.0/6.0) rgb = vec3(0.0, c, x);
    else if (h < 4.0/6.0) rgb = vec3(0.0, x, c);
    else if (h < 5.0/6.0) rgb = vec3(x, 0.0, c);
    else rgb = vec3(c, 0.0, x);
    return rgb + m;
}

void main() {
    vec4 tex = texture2D(uTex, vUV);
    if (tex.a < 0.01) discard;

    vec3 c = tex.rgb * 0.95;

    float maxTilt = max(0.001, uMaxTiltDeg);
    float tiltMag = clamp(length(uTilt) / maxTilt, 0.0, 1.0);
    float tiltGate = smoothstep(uSheenTiltDeadzone, 1.0, tiltMag);

    float gradient = fract(vUV.x * 0.5 + vUV.y * 0.5 + uTilt.x * uSheenTiltShift + uTilt.y * uSheenTiltShift);

    if (uHoloMode > 0.5) {
        float holoStrength = uSheenStrength * uHoloMotion;
        float distFromWhite = length(tex.rgb - vec3(1.0));
        float nonWhiteMask = smoothstep(0.06, 0.22, distFromWhite);
        vec3 rainbow = hsl2rgb(gradient, 0.8, 0.55);
        c = mix(c, rainbow, holoStrength * nonWhiteMask * tex.a);
    } else {
        float effectStrength = uSheenStrength * tiltGate;
        float sheen = smoothstep(0.2, 0.5, gradient) * (1.0 - smoothstep(0.5, 0.8, gradient));
        c = mix(c, uSheenColor, sheen * effectStrength * tex.a);
    }

    float hiW = clamp(vHi, 0.0, 1.0) * 0.55;
    float shW = clamp(vSh, 0.0, 1.0) * 0.60;

    vec3 hi = overlayBlend(c, vec3(1.0));
    c = mix(c, hi, hiW);

    vec3 sh = overlayBlend(c, vec3(0.0));
    c = mix(c, sh, shW);
    c *= (1.0 - shW * 0.35);

    c = clamp(c, 0.0, 1.0);
    gl_FragColor = vec4(c, tex.a);
}
`;

const STATIC_SHADOW_DEFAULT = "0px 1px 2px 0px rgba(0, 0, 0, 0.30)";
const DYNAMIC_SHADOW_DEFAULT = "0px 13px 14px 0px rgba(0, 0, 0, 0.30)";

function parseColorToRgb(input) {
    if (!input) return [1, 1, 1];
    const s = input.trim();
    const m = s.match(/rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)/i);
    if (m) return [+m[1] / 255, +m[2] / 255, +m[3] / 255];
    let h = s.replace(/^#/, "");
    if (h.length === 3) h = h.split("").map((c) => c + c).join("");
    if (h.length >= 6)
        return [
            parseInt(h.slice(0, 2), 16) / 255,
            parseInt(h.slice(2, 4), 16) / 255,
            parseInt(h.slice(4, 6), 16) / 255,
        ];
    return [1, 1, 1];
}

function parseBoxShadow(shadow) {
    const result = { x: 0, y: 0, blur: 0, color: "rgba(0,0,0,0.3)" };
    if (!shadow) return result;
    const colorMatch = shadow.match(/(rgba?\([^)]+\)|#[0-9a-fA-F]{3,8}|\b[a-z]+\b(?=\s*$))/i);
    if (colorMatch) result.color = colorMatch[0];
    const numbers = shadow.match(/-?\d+(\.\d+)?(px)?/g);
    if (numbers) {
        const vals = numbers.map((n) => parseFloat(n));
        if (vals.length >= 1) result.x = vals[0];
        if (vals.length >= 2) result.y = vals[1];
        if (vals.length >= 3) result.blur = vals[2];
    }
    return result;
}

function lerpShadow(a, b, t) {
    const x = a.x + (b.x - a.x) * t;
    const y = a.y + (b.y - a.y) * t;
    const blur = a.blur + (b.blur - a.blur) * t;
    const color = t > 0.5 ? b.color : a.color;
    return `drop-shadow(${x.toFixed(2)}px ${y.toFixed(2)}px ${blur.toFixed(2)}px ${color})`;
}

const resolveImageSource = (input) => {
    if (!input) return undefined;
    if (typeof input === "string") return input.trim() || undefined;
    return input.src || input.url || input.asset?.url || undefined;
};

export default function StickerDrag({
    image,
    imageWidth = 400,
    imageHeight = 300,
    tilt = 45,
    tiltSmoothing = DRAG_TILT_SMOOTHING,
    lighting = true,
    lightingStrength = 10,
    lightingColor = "#ffffff",
    sheenMode = "sheen",
    elevation: elevationLevel = 10,
    staticShadow = STATIC_SHADOW_DEFAULT,
    dynamicShadow = DYNAMIC_SHADOW_DEFAULT,
    style,
}) {
    const tiltSensitivity = DRAG_TILT_SENSITIVITY;
    const maxTilt = Math.max(1, tilt);
    const sheenStrength = lighting ? Math.max(1, Math.min(10, lightingStrength)) / 10 : 0;
    const sheenColor = React.useMemo(() => parseColorToRgb(lightingColor), [lightingColor]);
    const elevation = (Math.max(1, Math.min(10, elevationLevel)) / 10) * 0.3;

    const containerRef = useRef(null);
    const stickerRef = useRef(null);
    const innerRef = useRef(null);
    const canvasRef = useRef(null);

    const glRef = useRef(null);
    const programRef = useRef(null);
    const textureRef = useRef(null);
    const vboRef = useRef(null);
    const iboRef = useRef(null);
    const indexCountRef = useRef(0);

    const stateRef = useRef({
        x: 0, y: 0, width: 200, height: 200,
        imageAspectRatio: null, scale: 1.0,
        held: false, peeling: false, sticking: false,
        dragStartX: 0, dragStartY: 0, dragOrigX: 0, dragOrigY: 0,
        peel: 0, lift: 0, peelAngle: -Math.PI / 4,
        dragTiltX: 0, dragTiltY: 0, currentTiltX: 0, currentTiltY: 0,
        prevTiltX: 0, prevTiltY: 0, holoMotion: 0,
        lastMoveX: 0, lastMoveY: 0, lastMoveT: 0,
        texReady: false,
    });

    const animationRef = useRef(null);
    const lastTickTRef = useRef(null);

    const draw = useCallback(() => {
        const gl = glRef.current;
        const program = programRef.current;
        const texture = textureRef.current;
        const state = stateRef.current;

        if (!gl || !program || !texture || !state.texReady) return;

        gl.viewport(0, 0, gl.canvas.width, gl.canvas.height);
        gl.clearColor(0, 0, 0, 0);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

        gl.useProgram(program);

        gl.bindBuffer(gl.ARRAY_BUFFER, vboRef.current);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, iboRef.current);

        const aPos = gl.getAttribLocation(program, "aPos");
        const aUV = gl.getAttribLocation(program, "aUV");
        gl.enableVertexAttribArray(aPos);
        gl.enableVertexAttribArray(aUV);
        gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 16, 0);
        gl.vertexAttribPointer(aUV, 2, gl.FLOAT, false, 16, 8);

        gl.uniform1f(gl.getUniformLocation(program, "uPeel"), state.peel);
        gl.uniform1f(gl.getUniformLocation(program, "uLift"), state.lift);
        gl.uniform1f(gl.getUniformLocation(program, "uPeelAngle"), state.peelAngle);
        gl.uniform1f(gl.getUniformLocation(program, "uPasting"), state.sticking ? 1.0 : 0.0);
        gl.uniform1f(gl.getUniformLocation(program, "uScale"), state.scale);
        gl.uniform1f(gl.getUniformLocation(program, "uElevation"), elevation);

        gl.uniform2f(gl.getUniformLocation(program, "uTilt"), state.currentTiltX, state.currentTiltY);
        gl.uniform1f(gl.getUniformLocation(program, "uSheenStrength"), sheenStrength);
        gl.uniform3f(gl.getUniformLocation(program, "uSheenColor"), sheenColor[0], sheenColor[1], sheenColor[2]);
        gl.uniform1f(gl.getUniformLocation(program, "uSheenTiltShift"), SHEEN_TILT_SHIFT);
        gl.uniform1f(gl.getUniformLocation(program, "uSheenTiltDeadzone"), SHEEN_TILT_DEADZONE);
        gl.uniform1f(gl.getUniformLocation(program, "uMaxTiltDeg"), maxTilt);
        gl.uniform1f(gl.getUniformLocation(program, "uHoloMode"), sheenMode === "holo" ? 1.0 : 0.0);
        gl.uniform1f(gl.getUniformLocation(program, "uHoloMotion"), state.holoMotion);

        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.uniform1i(gl.getUniformLocation(program, "uTex"), 0);

        gl.drawElements(gl.TRIANGLES, indexCountRef.current, gl.UNSIGNED_SHORT, 0);
    }, [sheenStrength, sheenColor, sheenMode, elevation, maxTilt]);

    const parsedStaticShadow = React.useMemo(() => parseBoxShadow(staticShadow), [staticShadow]);
    const parsedDynamicShadow = React.useMemo(() => parseBoxShadow(dynamicShadow), [dynamicShadow]);

    const updateShadowCSS = useCallback(() => {
        const canvas = canvasRef.current;
        const state = stateRef.current;
        if (!canvas) return;
        const tRaw = Math.max(state.lift, state.peel);
        const t = tRaw * tRaw * (3 - 2 * tRaw);
        canvas.style.filter = lerpShadow(parsedStaticShadow, parsedDynamicShadow, t);
    }, [parsedStaticShadow, parsedDynamicShadow]);

    const tick = useCallback((timestamp) => {
        const state = stateRef.current;

        if (lastTickTRef.current === null) lastTickTRef.current = timestamp;
        const dt = Math.min((timestamp - lastTickTRef.current) / 1000, 0.1);
        lastTickTRef.current = timestamp;

        const step = ANIM_SPEED * dt;
        let changed = false;

        if (state.peeling) {
            if (state.peel < 1 || state.lift < 1) {
                state.peel = Math.min(1, state.peel + step);
                state.lift = Math.min(1, state.lift + step);
                changed = true;
            }
        }

        if (state.sticking) {
            if (state.peel > 0 || state.lift > 0) {
                state.peel = Math.max(0, state.peel - step);
                state.lift = Math.max(0, state.lift - step);
                changed = true;
            } else {
                state.sticking = false;
            }
        }

        const holoDecayActive = sheenMode === "holo" && state.holoMotion > 0.005;
        if (holoDecayActive) {
            state.holoMotion *= HOLO_MOTION_DECAY;
            if (state.holoMotion < 0.005) state.holoMotion = 0;
            changed = true;
        }

        if (changed) updateShadowCSS();
        if (changed || state.held || holoDecayActive) draw();

        if (state.held || state.peeling || state.sticking || holoDecayActive) {
            animationRef.current = requestAnimationFrame(tick);
        } else {
            animationRef.current = null;
            lastTickTRef.current = null;
        }
    }, [draw, updateShadowCSS, sheenMode]);

    const ensureTickRunning = useCallback(() => {
        if (animationRef.current !== null) return;
        lastTickTRef.current = null;
        animationRef.current = requestAnimationFrame(tick);
    }, [tick]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const gl = canvas.getContext("webgl", { alpha: true, antialias: true, premultipliedAlpha: false });
        if (!gl) return;

        glRef.current = gl;

        const compileShader = (source, type) => {
            const shader = gl.createShader(type);
            if (!shader) return null;
            gl.shaderSource(shader, source);
            gl.compileShader(shader);
            if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
                console.error("Shader compile error:", gl.getShaderInfoLog(shader));
                gl.deleteShader(shader);
                return null;
            }
            return shader;
        };

        const vs = compileShader(VERTEX_SHADER, gl.VERTEX_SHADER);
        const fs = compileShader(FRAGMENT_SHADER, gl.FRAGMENT_SHADER);
        if (!vs || !fs) return;

        const program = gl.createProgram();
        if (!program) return;

        gl.attachShader(program, vs);
        gl.attachShader(program, fs);
        gl.linkProgram(program);

        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            console.error("Program link error:", gl.getProgramInfoLog(program));
            return;
        }

        programRef.current = program;

        const N = MESH_GRID_SIZE;
        const verts = [];
        const inds = [];

        for (let j = 0; j <= N; j++) {
            for (let i = 0; i <= N; i++) {
                verts.push((i / N) * 2 - 1, (j / N) * 2 - 1, i / N, 1 - j / N);
            }
        }

        for (let j = 0; j < N; j++) {
            for (let i = 0; i < N; i++) {
                const a = j * (N + 1) + i;
                inds.push(a, a + 1, a + N + 1, a + 1, a + N + 2, a + N + 1);
            }
        }

        const vbo = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.STATIC_DRAW);
        vboRef.current = vbo;

        const ibo = gl.createBuffer();
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(inds), gl.STATIC_DRAW);
        iboRef.current = ibo;
        indexCountRef.current = inds.length;

        gl.viewport(0, 0, canvas.width, canvas.height);
        gl.clearColor(0, 0, 0, 0);
        gl.clear(gl.COLOR_BUFFER_BIT);

        return () => {
            if (animationRef.current) cancelAnimationFrame(animationRef.current);
            gl.deleteShader(vs);
            gl.deleteShader(fs);
            gl.deleteProgram(program);
            if (vboRef.current) gl.deleteBuffer(vboRef.current);
            if (iboRef.current) gl.deleteBuffer(iboRef.current);
            if (textureRef.current) gl.deleteTexture(textureRef.current);
        };
    }, []);

    const handleResize = useCallback(() => {
        const container = containerRef.current;
        const canvas = canvasRef.current;
        const sticker = stickerRef.current;
        const gl = glRef.current;
        const state = stateRef.current;

        if (!container || !canvas || !sticker || !gl) return;

        const containerWidth = container.clientWidth || 400;
        const containerHeight = container.clientHeight || 300;

        const width = imageWidth > 0 ? imageWidth : containerWidth;
        const height = imageHeight > 0 ? imageHeight : containerHeight;

        const maxDim = Math.max(width, height);
        const elevationPad = maxDim * elevation * 0.6;
        const effectivePad = PAD_BASE + elevationPad;
        const canvasWidth = width + effectivePad * 2;
        const canvasHeight = height + effectivePad * 2;

        const scaleX = width / canvasWidth;
        const scaleY = height / canvasHeight;
        const scale = Math.min(scaleX, scaleY);

        const x = (containerWidth - width) / 2;
        const y = (containerHeight - height) / 2;

        canvas.width = Math.round(canvasWidth * RENDER_SCALE);
        canvas.height = Math.round(canvasHeight * RENDER_SCALE);
        canvas.style.width = `${canvasWidth}px`;
        canvas.style.height = `${canvasHeight}px`;

        canvas.style.position = "absolute";
        canvas.style.left = `${-effectivePad}px`;
        canvas.style.top = `${-effectivePad}px`;

        sticker.style.width = `${width}px`;
        sticker.style.height = `${height}px`;
        sticker.style.left = `${x}px`;
        sticker.style.top = `${y}px`;

        state.width = width;
        state.height = height;
        state.x = x;
        state.y = y;
        state.scale = scale;

        gl.viewport(0, 0, canvas.width, canvas.height);
        if (state.texReady) draw();
    }, [draw, elevation, imageWidth, imageHeight]);

    useEffect(() => {
        const imageSrc = resolveImageSource(image) || DEFAULT_IMAGE;
        const gl = glRef.current;
        if (!gl || !programRef.current) return;

        const img = new Image();
        img.crossOrigin = "anonymous";

        img.onload = () => {
            const state = stateRef.current;
            state.imageAspectRatio = img.width / img.height;

            if (textureRef.current) gl.deleteTexture(textureRef.current);

            const texture = gl.createTexture();
            if (!texture) return;

            gl.bindTexture(gl.TEXTURE_2D, texture);
            gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);

            textureRef.current = texture;
            state.texReady = true;

            handleResize();
            updateShadowCSS();
        };

        img.src = imageSrc;
        return () => { stateRef.current.texReady = false; };
    }, [image, handleResize, updateShadowCSS]);

    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;
        handleResize();

        const ro = new ResizeObserver(() => handleResize());
        ro.observe(container);
        return () => ro.disconnect();
    }, [handleResize]);

    const handleMouseDown = useCallback((e) => {
        e.preventDefault();
        const state = stateRef.current;
        const container = containerRef.current;
        const sticker = stickerRef.current;
        const inner = innerRef.current;
        if (!container || !sticker || !inner) return;

        const rect = sticker.getBoundingClientRect();
        const grabOffsetX = e.clientX - rect.left;
        const grabOffsetY = e.clientY - rect.top;
        inner.style.transformOrigin = `${grabOffsetX}px ${grabOffsetY}px`;

        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const dx = e.clientX - centerX;
        const dy = e.clientY - centerY;
        state.peelAngle = Math.atan2(dy, dx);

        state.dragStartX = e.clientX;
        state.dragStartY = e.clientY;
        state.dragOrigX = state.x;
        state.dragOrigY = state.y;

        state.peel = 0;
        state.lift = 0;
        state.held = true;
        state.peeling = true;
        state.sticking = false;

        state.lastMoveX = e.clientX;
        state.lastMoveY = e.clientY;
        state.lastMoveT = performance.now();

        container.style.zIndex = `${getNextZIndex()}`;
        ensureTickRunning();
    }, [ensureTickRunning]);

    useEffect(() => {
        const handleMouseMove = (e) => {
            const state = stateRef.current;
            if (!state.held) return;
            const sticker = stickerRef.current;
            const inner = innerRef.current;
            if (!sticker || !inner) return;

            state.x = state.dragOrigX + (e.clientX - state.dragStartX);
            state.y = state.dragOrigY + (e.clientY - state.dragStartY);
            sticker.style.left = `${state.x}px`;
            sticker.style.top = `${state.y}px`;

            const now = performance.now();
            const dt = Math.max(1, now - state.lastMoveT);
            const velX = ((e.clientX - state.lastMoveX) / dt) * 16;
            const velY = ((e.clientY - state.lastMoveY) / dt) * 16;
            state.lastMoveX = e.clientX;
            state.lastMoveY = e.clientY;
            state.lastMoveT = now;

            const targetTiltY = Math.max(-maxTilt, Math.min(maxTilt, velX * tiltSensitivity));
            const targetTiltX = Math.max(-maxTilt, Math.min(maxTilt, -velY * tiltSensitivity));

            state.dragTiltX += (targetTiltX - state.dragTiltX) * tiltSmoothing;
            state.dragTiltY += (targetTiltY - state.dragTiltY) * tiltSmoothing;

            state.currentTiltX = state.dragTiltX;
            state.currentTiltY = state.dragTiltY;

            if (sheenMode === "holo") {
                const tiltDelta = Math.abs(state.dragTiltX - state.prevTiltX) + Math.abs(state.dragTiltY - state.prevTiltY);
                state.holoMotion = Math.min(1, state.holoMotion + tiltDelta * HOLO_MOTION_BUMP);
                state.prevTiltX = state.dragTiltX;
                state.prevTiltY = state.dragTiltY;
            }

            inner.style.transform = `rotateX(${state.dragTiltX}deg) rotateY(${state.dragTiltY}deg)`;
        };

        const handleMouseUp = () => {
            const state = stateRef.current;
            if (!state.held) return;
            const inner = innerRef.current;

            state.held = false;
            state.peeling = false;
            state.sticking = true;

            if (state.peel >= 0.95 && inner) {
                const rect = inner.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                const dx = state.lastMoveX - centerX;
                const dy = state.lastMoveY - centerY;
                state.peelAngle = Math.atan2(-dy, -dx);
                state.peel = 1;
            }

            const settleTilt = () => {
                state.dragTiltX *= 0.9;
                state.dragTiltY *= 0.9;
                state.currentTiltX = state.dragTiltX;
                state.currentTiltY = state.dragTiltY;

                if (inner) inner.style.transform = `rotateX(${state.dragTiltX}deg) rotateY(${state.dragTiltY}deg)`;

                if (Math.abs(state.dragTiltX) > 0.1 || Math.abs(state.dragTiltY) > 0.1) {
                    requestAnimationFrame(settleTilt);
                } else {
                    state.dragTiltX = 0; state.dragTiltY = 0;
                    state.currentTiltX = 0; state.currentTiltY = 0;
                    state.prevTiltX = 0; state.prevTiltY = 0;
                    if (inner) inner.style.transform = "";
                }
            };
            settleTilt();
            ensureTickRunning();
        };

        window.addEventListener("mousemove", handleMouseMove);
        window.addEventListener("mouseup", handleMouseUp);
        return () => {
            window.removeEventListener("mousemove", handleMouseMove);
            window.removeEventListener("mouseup", handleMouseUp);
        };
    }, [tiltSensitivity, tiltSmoothing, ensureTickRunning, sheenMode, maxTilt]);

    return (
        <div
            ref={containerRef}
            style={{
                position: "relative",
                width: "100%",
                height: "100%",
                overflow: "visible",
                perspective: "800px",
                ...style,
            }}
        >
            <div
                ref={stickerRef}
                style={{
                    position: "absolute",
                    width: "100%",
                    height: "100%",
                    cursor: "grab",
                    userSelect: "none",
                    perspective: "800px",
                    transformStyle: "preserve-3d",
                    willChange: "transform",
                    overflow: "visible",
                }}
                onMouseDown={handleMouseDown}
            >
                <div
                    ref={innerRef}
                    style={{
                        position: "absolute",
                        width: "100%",
                        height: "100%",
                        transformStyle: "preserve-3d",
                        overflow: "visible",
                    }}
                >
                    <canvas
                        ref={canvasRef}
                        style={{
                            display: "block",
                            pointerEvents: "none",
                            position: "absolute",
                        }}
                    />
                </div>
            </div>
        </div>
    );
}
