import { useEffect, useRef } from "react";

export default function Background() {
  const canvasRef = useRef(null);
  const mouse = useRef({
    x: window.innerWidth / 2,
    y: window.innerHeight / 2,
  });

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    let animation;

    function resize() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }

    resize();

    window.addEventListener("resize", resize);

    window.addEventListener("mousemove", (e) => {
      mouse.current.x = e.clientX;
      mouse.current.y = e.clientY;
    });

    //------------------------
    // STARS
    //------------------------

    const stars = Array.from({ length: 350 }, () => ({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      r: Math.random() * 1.3,
      alpha: Math.random(),
      speed: Math.random() * 0.015,
    }));

    //------------------------
    // FLOATING PARTICLES
    //------------------------

    const particles = Array.from({ length: 120 }, () => ({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      vx: (Math.random() - 0.5) * 0.2,
      vy: -Math.random() * 0.2,
      size: Math.random() * 2,
      alpha: Math.random() * 0.5,
    }));

    let t = 0;

    function draw() {
      t += 0.003;

      const W = canvas.width;
      const H = canvas.height;

      ctx.clearRect(0, 0, W, H);

      //--------------------------------
      // DEEP SPACE
      //--------------------------------

      const bg = ctx.createLinearGradient(0, 0, 0, H);

      bg.addColorStop(0, "#01040A");
      bg.addColorStop(1, "#020611");

      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, W, H);

      //--------------------------------
      // MINIMAL GRID / BACKGROUND
      //--------------------------------

      ctx.strokeStyle = "rgba(0,170,255,0.02)";
      ctx.lineWidth = 1;

      const grid = 160;

      for (let x = 0; x < W; x += grid) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, H);
        ctx.stroke();
      }

      for (let y = 0; y < H; y += grid) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(W, y);
        ctx.stroke();
      }

      //--------------------------------
      // SOFT CENTER GLOW
      //--------------------------------

      const glow = ctx.createRadialGradient(
        W / 2,
        H * 0.45,
        0,
        W / 2,
        H * 0.45,
        220
      );

      glow.addColorStop(0, "rgba(0,220,255,0.10)");
      glow.addColorStop(1, "transparent");

      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, W, H);

      //--------------------------------
      // STARS
      //--------------------------------

      stars.forEach((s) => {
        s.alpha += Math.sin(t * 30 + s.x) * 0.001;

        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(220,245,255,${s.alpha * 0.45})`;
        ctx.fill();
      });

      //--------------------------------
      // CENTER GLOW
      //--------------------------------

      const centerGlow = ctx.createRadialGradient(
        W / 2,
        H * 0.45,
        0,
        W / 2,
        H * 0.45,
        240
      );

      centerGlow.addColorStop(0, "rgba(0,230,255,0.14)");
      centerGlow.addColorStop(1, "transparent");

      ctx.fillStyle = centerGlow;
      ctx.fillRect(0, 0, W, H);

      //--------------------------------
      // TOP CORNERS
      //--------------------------------

      ctx.strokeStyle = "rgba(0,190,255,0.08)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(40, 42);
      ctx.lineTo(40, 16);
      ctx.lineTo(80, 16);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(W - 40, 42);
      ctx.lineTo(W - 40, 16);
      ctx.lineTo(W - 80, 16);
      ctx.stroke();

      //--------------------------------
      // VIGNETTE
      //--------------------------------

      const vignette = ctx.createRadialGradient(
        W / 2,
        H / 2,
        H * 0.15,
        W / 2,
        H / 2,
        H * 0.95
      );

      vignette.addColorStop(0, "transparent");
      vignette.addColorStop(1, "rgba(0,0,0,.85)");

      ctx.fillStyle = vignette;

      ctx.fillRect(0, 0, W, H);

      animation = requestAnimationFrame(draw);
    }

    draw();

    return () => {
      cancelAnimationFrame(animation);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full"
      style={{
        zIndex: 0,
      }}
    />
  );
}