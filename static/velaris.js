/**
 * Velaris - Growth Horizon
 * Fondo animado en WebGL: simplex noise, mezcla de color, vignette y grano de pelicula.
 * Sin dependencias. Se auto-inicializa sobre cualquier elemento con [data-velaris].
 */
(function () {
    'use strict';

    var vertexShaderGLSL = `
attribute vec2 position;
varying vec2 vUv;
void main() {
  vUv = position * 0.5 + 0.5;
  gl_Position = vec4(position, 0.0, 1.0);
}
`;

    var fragmentShaderGLSL = `
precision highp float;
varying vec2 vUv;

uniform vec2  u_resolution;
uniform float u_time;
uniform float u_grain;
uniform vec3  u_colors[4];
uniform vec3  u_bg;

vec3 permute(vec3 x) { return mod(((x*34.0)+1.0)*x, 289.0); }

float snoise(vec2 v){
  const vec4 C = vec4(0.211324865405187, 0.366025403784439,
           -0.577350269189626, 0.024390243902439);
  vec2 i  = floor(v + dot(v, C.yy) );
  vec2 x0 = v -   i + dot(i, C.xx);
  vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod(i, 289.0);
  vec3 p = permute( permute( i.y + vec3(0.0, i1.y, 1.0 ))
  + i.x + vec3(0.0, i1.x, 1.0 ));
  vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy),
    dot(x12.zw,x12.zw)), 0.0);
  m = m*m ;
  m = m*m ;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * ( a0*a0 + h*h );
  vec3 g;
  g.x  = a0.x  * x0.x  + h.x  * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}

void main() {
  vec2 uv = vUv;
  float ratio = u_resolution.x / u_resolution.y;
  vec2 p = uv - 0.5;
  p.x *= ratio;

  float t = u_time * 0.1;

  float n1 = snoise(p * 0.4 + vec2(t * 0.2, -t * 0.3));
  float n2 = snoise(p * 0.55 + vec2(-t * 0.15, t * 0.25) + n1 * 0.25);
  float n3 = snoise(p * 0.75 + vec2(t * 0.1, -t * 0.2) + n2 * 0.2);

  vec3 col = u_bg;

  float dist = length(p) * 1.5;
  float vignette = 1.0 - smoothstep(0.3, 1.2, dist);

  col = mix(col, u_colors[0], smoothstep(-0.2, 0.5, n1) * 0.85);
  col = mix(col, u_colors[1], smoothstep(-0.1, 0.6, n2) * 0.7);
  col = mix(col, u_colors[2], smoothstep(-0.3, 0.4, n3) * 0.6);
  col = mix(col, u_colors[3], smoothstep(0.0, 0.7, n1 * n2) * 0.5);

  float glow = smoothstep(0.8, 0.0, dist) * 0.3;
  col += u_colors[1] * glow;

  col = mix(col * 0.2, col, vignette);

  float grain = fract(sin(dot(uv, vec2(12.9898, 78.233))) * 43758.5453 + u_time);
  col += (grain - 0.5) * u_grain * 0.1;

  gl_FragColor = vec4(col, 1.0);
}
`;

    // Paleta Growth Horizon: el cian-esmeralda del logo sobre el fondo #0D1117 del sidebar.
    // u_colors[1] es el color del resplandor central, por eso lleva el cian mas brillante.
    var DEFAULT_BG = '#0D1117';
    var DEFAULT_COLORS = ['#0e7490', '#22d3ee', '#10b981', '#0f3460'];
    var DEFAULT_SPEED = 2.0;
    var DEFAULT_GRAIN = 0.3;
    var DEFAULT_MOTION = 'auto';
    // Factor aplicado en modo 'auto' cuando el sistema pide movimiento reducido.
    var REDUCED_MOTION_FACTOR = 0.3;

    function hexToRgb(hex) {
        var h = String(hex).trim().replace('#', '');
        if (h.length === 3) {
            h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
        }
        return [
            parseInt(h.slice(0, 2), 16) / 255,
            parseInt(h.slice(2, 4), 16) / 255,
            parseInt(h.slice(4, 6), 16) / 255
        ];
    }

    /**
     * Monta el fondo animado dentro de un contenedor.
     * @param {HTMLElement} container
     * @param {{bg?: string, colors?: string[], speed?: number, grain?: number,
     *          motion?: 'auto'|'always'|'off'}} [options]
     * @returns {{destroy: function}|null} null si WebGL no esta disponible (queda el degradado CSS).
     */
    function createVelaris(container, options) {
        if (!container) return null;
        options = options || {};

        var bg = options.bg || DEFAULT_BG;
        var colors = (options.colors && options.colors.length) ? options.colors : DEFAULT_COLORS;
        var speed = typeof options.speed === 'number' && !isNaN(options.speed) ? options.speed : DEFAULT_SPEED;
        var grain = typeof options.grain === 'number' && !isNaN(options.grain) ? options.grain : DEFAULT_GRAIN;
        var motion = (options.motion === 'always' || options.motion === 'off') ? options.motion : DEFAULT_MOTION;

        var canvas = document.createElement('canvas');
        canvas.className = 'gh-velaris-canvas';
        canvas.setAttribute('aria-hidden', 'true');
        container.insertBefore(canvas, container.firstChild);

        function abort() {
            if (canvas.parentNode) canvas.parentNode.removeChild(canvas);
            return null;
        }

        var gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) return abort();

        function createShader(type, src) {
            var shader = gl.createShader(type);
            gl.shaderSource(shader, src);
            gl.compileShader(shader);
            if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
                console.error('Velaris: error al compilar shader', gl.getShaderInfoLog(shader));
                return null;
            }
            return shader;
        }

        var vertexShader = createShader(gl.VERTEX_SHADER, vertexShaderGLSL);
        var fragmentShader = createShader(gl.FRAGMENT_SHADER, fragmentShaderGLSL);
        if (!vertexShader || !fragmentShader) return abort();

        var program = gl.createProgram();
        gl.attachShader(program, vertexShader);
        gl.attachShader(program, fragmentShader);
        gl.linkProgram(program);
        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            console.error('Velaris: error al enlazar el programa', gl.getProgramInfoLog(program));
            return abort();
        }
        gl.useProgram(program);

        var buffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(
            gl.ARRAY_BUFFER,
            new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
            gl.STATIC_DRAW
        );

        var pos = gl.getAttribLocation(program, 'position');
        gl.enableVertexAttribArray(pos);
        gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);

        var locs = {
            res: gl.getUniformLocation(program, 'u_resolution'),
            time: gl.getUniformLocation(program, 'u_time'),
            grain: gl.getUniformLocation(program, 'u_grain'),
            colors: gl.getUniformLocation(program, 'u_colors'),
            bg: gl.getUniformLocation(program, 'u_bg')
        };

        // Uniforms fijos: se suben una sola vez, no en cada frame.
        // u_colors siempre son 4 vec3; si llegan menos colores, se repiten en ciclo.
        var flat = new Float32Array(12);
        for (var i = 0; i < 4; i++) {
            var rgb = hexToRgb(colors[i % colors.length]);
            flat[i * 3] = rgb[0];
            flat[i * 3 + 1] = rgb[1];
            flat[i * 3 + 2] = rgb[2];
        }
        gl.uniform3fv(locs.colors, flat);

        var bgRgb = hexToRgb(bg);
        gl.uniform3f(locs.bg, bgRgb[0], bgRgb[1], bgRgb[2]);
        gl.uniform1f(locs.grain, grain);

        function resize() {
            var dpr = Math.min(window.devicePixelRatio || 1, 2);
            canvas.width = Math.max(1, Math.round(container.clientWidth * dpr));
            canvas.height = Math.max(1, Math.round(container.clientHeight * dpr));
            gl.viewport(0, 0, canvas.width, canvas.height);
            gl.uniform2f(locs.res, canvas.width, canvas.height);
        }

        resize();

        var ro = null;
        if (typeof ResizeObserver === 'function') {
            ro = new ResizeObserver(resize);
            ro.observe(container);
        } else {
            window.addEventListener('resize', resize);
        }

        var raf = null;

        function destroy() {
            if (ro) {
                ro.disconnect();
            } else {
                window.removeEventListener('resize', resize);
            }
            if (raf) cancelAnimationFrame(raf);
            if (canvas.parentNode) canvas.parentNode.removeChild(canvas);
        }

        // Preferencia de movimiento reducido del sistema (en Windows: Accesibilidad >
        // Efectos visuales > Efectos de animacion). Segun el modo:
        //   'auto'   -> sigue animando, pero mas lento
        //   'always' -> la ignora y anima a velocidad completa
        //   'off'    -> un solo frame estatico
        var prefersReduce = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
        var effectiveSpeed = speed;

        if (motion === 'off') {
            effectiveSpeed = 0;
        } else if (motion === 'auto' && prefersReduce) {
            effectiveSpeed = speed * REDUCED_MOTION_FACTOR;
        }

        if (effectiveSpeed === 0) {
            gl.uniform1f(locs.time, 0.0);
            gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
            return { destroy: destroy };
        }

        function render(t) {
            gl.uniform1f(locs.time, t * 0.001 * effectiveSpeed);
            gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
            raf = requestAnimationFrame(render);
        }

        raf = requestAnimationFrame(render);

        return { destroy: destroy };
    }

    function parseColors(value) {
        if (!value) return null;
        var list = value.split(',').map(function (c) { return c.trim(); }).filter(Boolean);
        return list.length ? list : null;
    }

    function parseNumber(value) {
        if (value === undefined || value === null || value === '') return undefined;
        var n = parseFloat(value);
        return isNaN(n) ? undefined : n;
    }

    function autoInit() {
        var nodes = document.querySelectorAll('[data-velaris]');
        Array.prototype.forEach.call(nodes, function (el) {
            if (el.dataset.velarisReady) return;
            el.dataset.velarisReady = '1';
            createVelaris(el, {
                bg: el.dataset.velarisBg,
                colors: parseColors(el.dataset.velarisColors),
                speed: parseNumber(el.dataset.velarisSpeed),
                grain: parseNumber(el.dataset.velarisGrain),
                motion: el.dataset.velarisMotion
            });
        });
    }

    window.Velaris = {
        create: createVelaris,
        init: autoInit,
        DEFAULT_BG: DEFAULT_BG,
        DEFAULT_COLORS: DEFAULT_COLORS
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoInit);
    } else {
        autoInit();
    }
})();
