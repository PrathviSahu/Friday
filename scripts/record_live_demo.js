import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const OUTPUT_DIR = '/Users/snehasahu/Desktop/FRIDAY_Demo_Screenshots/recordings';
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

// Clean old recordings
fs.readdirSync(OUTPUT_DIR).forEach(f => {
  if (f.endsWith('.webm') || f.endsWith('.mp4')) {
    try { fs.unlinkSync(path.join(OUTPUT_DIR, f)); } catch (_) {}
  }
});

async function run() {
  console.log('🚀 Starting F.R.I.D.A.Y. Automated Live Demo Recording...');

  const browser = await chromium.launch({
    headless: true,
    args: [
      '--disable-web-security',
      '--enable-features=WebGLEnable',
      '--ignore-gpu-blocklist',
      '--use-gl=swiftshader',
      '--no-sandbox',
    ]
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    recordVideo: {
      dir: OUTPUT_DIR,
      size: { width: 1920, height: 1080 }
    }
  });

  const page = await context.newPage();

  async function setupVisualCursor() {
    await page.evaluate(() => {
      if (document.getElementById('hud-virtual-cursor')) return;
      const cur = document.createElement('div');
      cur.id = 'hud-virtual-cursor';
      cur.style.cssText = `
        position: fixed;
        top: 0; left: 0;
        width: 32px; height: 32px;
        pointer-events: none;
        z-index: 2147483647;
        transform: translate(960px, 540px);
        transition: transform 0.06s cubic-bezier(0.16, 1, 0.3, 1);
        filter: drop-shadow(0 0 10px #00E5FF) drop-shadow(0 0 24px rgba(0,229,255,0.7));
      `;
      cur.innerHTML = `
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <path d="M5 2L26 15L15 18L10 29L5 2Z" fill="#00E5FF" stroke="#001824" stroke-width="2" stroke-linejoin="round"/>
          <circle cx="5" cy="2" r="2.5" fill="#FFFFFF" />
        </svg>
      `;
      document.body.appendChild(cur);

      window.__moveCursor = (x, y) => {
        const el = document.getElementById('hud-virtual-cursor');
        if (el) el.style.transform = `translate(${x}px, ${y}px)`;
      };

      window.__clickRipple = (x, y) => {
        const rip = document.createElement('div');
        rip.style.cssText = `
          position: fixed;
          top: ${y - 24}px; left: ${x - 24}px;
          width: 48px; height: 48px;
          border-radius: 50%;
          border: 2.5px solid #00E5FF;
          background: radial-gradient(circle, rgba(0, 229, 255, 0.4) 0%, transparent 70%);
          pointer-events: none;
          z-index: 2147483646;
          animation: hudClickRipple 0.5s ease-out forwards;
        `;
        document.body.appendChild(rip);
        setTimeout(() => rip.remove(), 550);
      };

      const style = document.createElement('style');
      style.textContent = `
        @keyframes hudClickRipple {
          0% { transform: scale(0.2); opacity: 1; }
          100% { transform: scale(2.2); opacity: 0; }
        }
      `;
      document.head.appendChild(style);
    });
  }

  let curPos = { x: 960, y: 540 };

  async function smoothMoveTo(x, y, steps = 22) {
    const startX = curPos.x;
    const startY = curPos.y;
    for (let i = 1; i <= steps; i++) {
      const t = i / steps;
      const ease = t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
      const currX = Math.round(startX + (x - startX) * ease);
      const currY = Math.round(startY + (y - startY) * ease);
      await page.mouse.move(currX, currY);
      await page.evaluate(({ cx, cy }) => window.__moveCursor?.(cx, cy), { cx: currX, cy: currY });
      await page.waitForTimeout(14);
    }
    curPos = { x, y };
  }

  async function smoothClick(selectorOrCoords, waitAfter = 1000) {
    let targetX, targetY;
    if (typeof selectorOrCoords === 'string') {
      const el = await page.waitForSelector(selectorOrCoords, { timeout: 7000 });
      const box = await el.boundingBox();
      if (!box) throw new Error('Cannot find box for ' + selectorOrCoords);
      targetX = Math.round(box.x + box.width / 2);
      targetY = Math.round(box.y + box.height / 2);
    } else {
      targetX = selectorOrCoords.x;
      targetY = selectorOrCoords.y;
    }

    await smoothMoveTo(targetX, targetY);
    await page.waitForTimeout(120);
    await page.evaluate(({ cx, cy }) => window.__clickRipple?.(cx, cy), { cx: targetX, cy: targetY });
    await page.mouse.click(targetX, targetY);
    await page.waitForTimeout(waitAfter);
  }

  async function smoothType(text, delayBetween = 60) {
    for (const char of text) {
      await page.keyboard.type(char);
      await page.waitForTimeout(delayBetween + Math.floor(Math.random() * 25));
    }
    await page.waitForTimeout(250);
  }

  // ─────────────────────────────────────────────────────────────
  // SCENE 1: LOCK SCREEN & BIOMETRIC / INSTANT DEMO UNLOCK (0s - 12s)
  // ─────────────────────────────────────────────────────────────
  console.log('📍 Scene 1: Initializing FRIDAY Lock Screen...');
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await setupVisualCursor();
  await page.waitForTimeout(3500);

  console.log('🖱️ Unlocking with Instant Demo Access...');
  const unlockBtn = page.locator('button:has-text("Instant Demo Access"), button:has-text("Instant Demo")').first();
  await unlockBtn.waitFor({ state: 'visible', timeout: 5000 });
  const unlockBox = await unlockBtn.boundingBox();
  if (unlockBox) {
    await smoothClick({ x: unlockBox.x + unlockBox.width / 2, y: unlockBox.y + unlockBox.height / 2 }, 4000);
  }

  console.log('✨ System Unlocked! Main HUD standing by...');
  await page.waitForTimeout(2000);

  // ─────────────────────────────────────────────────────────────
  // SCENE 2: VOICE & FAST-PATH COMMAND + SPOTIFY (12s - 26s)
  // ─────────────────────────────────────────────────────────────
  console.log('📍 Scene 2: Testing Fast-Path Input: "play Kesariya"...');
  const inputBar = page.locator('input[placeholder*="Type or speak"], input[placeholder*="command"]').first();
  await inputBar.waitFor({ state: 'visible', timeout: 5000 });
  const inputBox = await inputBar.boundingBox();
  if (inputBox) {
    await smoothClick({ x: inputBox.x + 120, y: inputBox.y + inputBox.height / 2 }, 300);
    await smoothType('play Kesariya');
    await page.waitForTimeout(300);
    await page.keyboard.press('Enter');
  }

  console.log('🎵 Fast-Path response rendered! Interacting with Spotify...');
  await page.waitForTimeout(3000);

  // Interacting with Spotify player
  const spotifySearch = page.locator('input[placeholder*="Search tracks"], input[placeholder*="Search"]').first();
  if (await spotifySearch.isVisible()) {
    const sBox = await spotifySearch.boundingBox();
    if (sBox) {
      await smoothClick({ x: sBox.x + 80, y: sBox.y + sBox.height / 2 }, 200);
      await smoothType('Kesariya Arijit Singh');
      await page.waitForTimeout(1500);
    }
  }

  // Click Play in Spotify Card
  const playBtn = page.locator('button:has-text("▶"), button[aria-label*="Play"]').first();
  if (await playBtn.isVisible()) {
    const pBox = await playBtn.boundingBox();
    if (pBox) {
      await smoothClick({ x: pBox.x + pBox.width / 2, y: pBox.y + pBox.height / 2 }, 2000);
    }
  }

  await page.waitForTimeout(1500);

  // Close Spotify Card
  const closeSpotify = page.locator('button[title*="Close"], button:has-text("✕")').last();
  if (await closeSpotify.isVisible()) {
    const csBox = await closeSpotify.boundingBox();
    if (csBox) {
      await smoothClick({ x: csBox.x + csBox.width / 2, y: csBox.y + csBox.height / 2 }, 1500);
    }
  }

  // ─────────────────────────────────────────────────────────────
  // SCENE 3: CAREER INTELLIGENCE OS (26s - 45s)
  // ─────────────────────────────────────────────────────────────
  console.log('📍 Scene 3: Opening Career Intelligence OS...');
  const careerBtn = page.locator('button:has-text("CAREER OS"), button:has-text("Career OS")').first();
  if (await careerBtn.isVisible()) {
    const crBox = await careerBtn.boundingBox();
    if (crBox) {
      await smoothClick({ x: crBox.x + crBox.width / 2, y: crBox.y + crBox.height / 2 }, 3500);
    }
  }

  console.log('💼 Career OS Board loaded. Inspecting live ATS opportunity matches...');
  await page.waitForTimeout(2000);

  // Click on Java Developer job card
  const javaJob = page.locator('div:has-text("Java Developer"), div:has-text("Full Stack Developer")').first();
  if (await javaJob.isVisible()) {
    const jBox = await javaJob.boundingBox();
    if (jBox) {
      await smoothClick({ x: jBox.x + jBox.width / 2, y: jBox.y + jBox.height / 2 }, 3500);
    }
  }

  await page.waitForTimeout(2500);

  // Hover over the 80% Match gauge and F.R.I.D.A.Y. Analysis
  await smoothMoveTo(1150, 200, 20);
  await page.waitForTimeout(2000);

  // Close Career OS to return to Main HUD
  console.log('Closing Career OS...');
  const closeCareer = page.locator('button[title="Return to Main HUD"]').first();
  if (await closeCareer.isVisible()) {
    const ccBox = await closeCareer.boundingBox();
    if (ccBox) {
      await smoothClick({ x: ccBox.x + ccBox.width / 2, y: ccBox.y + ccBox.height / 2 }, 2000);
    }
  } else {
    await page.keyboard.press('Escape');
    await page.waitForTimeout(1500);
  }

  // ─────────────────────────────────────────────────────────────
  // SCENE 4: QUANTUM TRADING WORKSTATION (45s - 65s)
  // ─────────────────────────────────────────────────────────────
  console.log('📍 Scene 4: Opening Quantum Trading Workstation...');
  const tradingBtn = page.locator('button:has-text("TRADING STATION"), button:has-text("Trading Station")').first();
  if (await tradingBtn.isVisible()) {
    const trBox = await tradingBtn.boundingBox();
    if (trBox) {
      await smoothClick({ x: trBox.x + trBox.width / 2, y: trBox.y + trBox.height / 2 }, 4500);
    }
  }

  console.log('📈 Trading Station active. Switching Watchlist assets (Reliance, TCS, Infy)...');
  await page.waitForTimeout(2500);

  // Click items in watchlist
  const stockItems = page.locator('div:has-text("REL"), div:has-text("TCS"), div:has-text("INFY"), div:has-text("NIF"), button:has-text("15m"), button:has-text("1h")');
  const count = await stockItems.count();
  if (count > 0) {
    for (let i = 0; i < Math.min(count, 3); i++) {
      const item = stockItems.nth(i);
      if (await item.isVisible()) {
        const itemBox = await item.boundingBox();
        if (itemBox) {
          await smoothClick({ x: itemBox.x + itemBox.width / 2, y: itemBox.y + itemBox.height / 2 }, 2500);
        }
      }
    }
  }

  await page.waitForTimeout(2500);

  // Close Trading Workstation
  console.log('Closing Trading Station...');
  const closeTrading = page.locator('button[title="Exit Trading Station"]').first();
  if (await closeTrading.isVisible()) {
    const ctBox = await closeTrading.boundingBox();
    if (ctBox) {
      await smoothClick({ x: ctBox.x + ctBox.width / 2, y: ctBox.y + ctBox.height / 2 }, 2000);
    }
  } else {
    await page.keyboard.press('Escape');
    await page.waitForTimeout(1500);
  }

  // ─────────────────────────────────────────────────────────────
  // SCENE 5: 17-IN-1 STARK MODULAR DASHBOARD (65s - 80s)
  // ─────────────────────────────────────────────────────────────
  console.log('📍 Scene 5: Opening 17-in-1 Stark Modular Dashboard...');
  const dashBtn = page.locator('button:has-text("DASHBOARD")').first();
  if (await dashBtn.isVisible()) {
    const dBox = await dashBtn.boundingBox();
    if (dBox) {
      await smoothClick({ x: dBox.x + dBox.width / 2, y: dBox.y + dBox.height / 2 }, 3000);
    }
  }

  console.log('⚡ Scrolling through all 17 AI OS modules...');
  await page.waitForTimeout(1500);

  await smoothMoveTo(1200, 500);
  for (let s = 0; s < 6; s++) {
    await page.mouse.wheel(0, 320);
    await page.waitForTimeout(700);
  }
  await page.waitForTimeout(2000);

  for (let s = 0; s < 6; s++) {
    await page.mouse.wheel(0, -320);
    await page.waitForTimeout(500);
  }
  await page.waitForTimeout(1500);

  // Close Dashboard
  console.log('Closing Dashboard drawer...');
  const closeDash = page.locator('button[title="Close Dashboard"]').first();
  if (await closeDash.isVisible()) {
    const cdBox = await closeDash.boundingBox();
    if (cdBox) {
      await smoothClick({ x: cdBox.x + cdBox.width / 2, y: cdBox.y + cdBox.height / 2 }, 2000);
    }
  }

  // ─────────────────────────────────────────────────────────────
  // SCENE 6: SECURING SYSTEM / LOCK FAST-PATH (80s - 88s)
  // ─────────────────────────────────────────────────────────────
  console.log('📍 Scene 6: Executing Fast-Path Lock Command...');
  const finalInput = page.locator('input[placeholder*="Type or speak"]').first();
  if (await finalInput.isVisible()) {
    const fiBox = await finalInput.boundingBox();
    if (fiBox) {
      await smoothClick({ x: fiBox.x + 120, y: fiBox.y + fiBox.height / 2 }, 200);
      await smoothType('lock system');
      await page.waitForTimeout(300);
      await page.keyboard.press('Enter');
    }
  }

  console.log('🔒 System locked! Standing by on secure screen...');
  await page.waitForTimeout(4000);

  console.log('🎬 Recording complete! Finalizing video...');
  await context.close();
  await browser.close();
  console.log('✅ Video saved successfully to:', OUTPUT_DIR);
}

run().catch(err => {
  console.error('❌ Error during demo recording:', err);
  process.exit(1);
});
