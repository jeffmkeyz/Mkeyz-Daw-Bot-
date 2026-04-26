<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Mkeyz Studio — Showcase</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
* { margin:0; padding:0; box-sizing:border-box; }

:root {
  --gold:#f5c518;
  --purple:#9c27b0;
  --green:#00e676;
  --fire:#ff4d4d;
}

html, body {
  width:100%; height:100%;
  background:#000;
  overflow:hidden;
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif;
  color:#fff;
}

/* ── CANVAS BACKGROUND ── */
#bg-canvas {
  position:fixed; inset:0; z-index:0;
}

/* ── SCENES ── */
.scene {
  position:fixed; inset:0; z-index:10;
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  padding:40px 28px;
  opacity:0; pointer-events:none;
  transition:none;
}
.scene.active { opacity:1; pointer-events:all; }

/* ── SCENE 0: INTRO ── */
.intro-logo {
  font-size:48px; font-weight:900; letter-spacing:-2px;
  background:linear-gradient(135deg,#fff 0%,var(--gold) 60%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  opacity:0; transform:scale(0.7);
  transition:all 0.8s cubic-bezier(0.34,1.56,0.64,1);
  text-align:center; line-height:1;
}
.intro-logo.show { opacity:1; transform:scale(1); }

.intro-sub {
  font-size:14px; color:rgba(255,255,255,0.5); margin-top:12px;
  letter-spacing:4px; text-transform:uppercase;
  opacity:0; transform:translateY(20px);
  transition:all 0.6s ease 0.4s;
  text-align:center;
}
.intro-sub.show { opacity:1; transform:translateY(0); }

.intro-line {
  width:0; height:1px; background:linear-gradient(90deg,transparent,var(--gold),transparent);
  margin-top:24px; transition:width 1s ease 0.8s;
}
.intro-line.show { width:200px; }

/* ── SCENE 1: TAGLINE ── */
.tagline {
  font-size:32px; font-weight:900; text-align:center; line-height:1.2;
  letter-spacing:-1px;
}
.tagline .line {
  display:block; overflow:hidden; opacity:0; transform:translateY(40px);
  transition:all 0.6s cubic-bezier(0.34,1.56,0.64,1);
}
.tagline .line.show { opacity:1; transform:translateY(0); }
.tagline .highlight { color:var(--gold); }

/* ── FEATURE SCENES ── */
.feat-icon {
  font-size:72px; opacity:0; transform:scale(0.5) rotate(-10deg);
  transition:all 0.5s cubic-bezier(0.34,1.56,0.64,1);
  margin-bottom:20px;
}
.feat-icon.show { opacity:1; transform:scale(1) rotate(0); }

.feat-title {
  font-size:28px; font-weight:900; text-align:center;
  opacity:0; transform:translateX(-40px);
  transition:all 0.5s ease 0.2s;
  letter-spacing:-0.5px;
}
.feat-title.show { opacity:1; transform:translateX(0); }

.feat-desc {
  font-size:15px; color:rgba(255,255,255,0.6); text-align:center;
  margin-top:10px; line-height:1.6;
  opacity:0; transform:translateY(20px);
  transition:all 0.5s ease 0.35s;
  max-width:280px;
}
.feat-desc.show { opacity:1; transform:translateY(0); }

.feat-tags {
  display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin-top:16px;
}
.feat-tag {
  padding:6px 14px; border-radius:100px; font-size:12px; font-weight:700;
  opacity:0; transform:scale(0.8);
  transition:all 0.3s ease;
}
.feat-tag.show { opacity:1; transform:scale(1); }

/* ── SCENE: PLANS ── */
.plans-row {
  display:flex; gap:12px; width:100%; max-width:340px;
}
.plan-card {
  flex:1; border-radius:16px; padding:16px 10px; text-align:center;
  opacity:0; transform:translateY(40px);
  transition:all 0.5s cubic-bezier(0.34,1.56,0.64,1);
}
.plan-card.show { opacity:1; transform:translateY(0); }
.plan-emoji { font-size:28px; margin-bottom:8px; }
.plan-name  { font-size:13px; font-weight:800; margin-bottom:4px; }
.plan-price { font-size:11px; opacity:0.6; }

/* ── SCENE: FINALE ── */
.finale-title {
  font-size:36px; font-weight:900; text-align:center;
  background:linear-gradient(135deg,#fff,var(--gold));
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  opacity:0; transform:scale(0.8);
  transition:all 0.8s cubic-bezier(0.34,1.56,0.64,1);
  letter-spacing:-1px;
}
.finale-title.show { opacity:1; transform:scale(1); }

.finale-url {
  font-size:20px; font-weight:700; color:var(--gold); margin-top:16px;
  opacity:0; transition:all 0.6s ease 0.5s;
}
.finale-url.show { opacity:1; }

.finale-cta {
  margin-top:28px; padding:16px 36px; border-radius:100px; border:none;
  background:linear-gradient(135deg,var(--gold),#ff8c00);
  font-size:17px; font-weight:800; color:#000; cursor:pointer;
  opacity:0; transform:translateY(20px);
  transition:all 0.5s ease 0.8s;
}
.finale-cta.show { opacity:1; transform:translateY(0); }
.finale-cta:active { transform:scale(0.97); }

/* ── PROGRESS BAR ── */
#progress-bar {
  position:fixed; bottom:0; left:0; height:3px;
  background:linear-gradient(90deg,var(--gold),var(--fire));
  z-index:100; transition:width 0.1s linear;
  box-shadow:0 0 8px var(--gold);
}

/* ── SKIP BTN ── */
#skip-btn {
  position:fixed; top:20px; right:20px; z-index:200;
  background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.2);
  border-radius:100px; padding:8px 16px; color:rgba(255,255,255,0.5);
  font-size:12px; font-weight:600; cursor:pointer; backdrop-filter:blur(8px);
}

/* ── PARTICLES ── */
.particle {
  position:fixed; border-radius:50%; pointer-events:none; z-index:5;
  animation:particleFloat linear forwards;
}
@keyframes particleFloat {
  0%   { transform:translateY(100vh) scale(0); opacity:0.8; }
  100% { transform:translateY(-20vh) scale(1); opacity:0; }
}

/* ── GLITCH ── */
@keyframes glitch {
  0%,100% { transform:translate(0); }
  20%     { transform:translate(-2px,2px); }
  40%     { transform:translate(2px,-2px); }
  60%     { transform:translate(-1px,1px); }
  80%     { transform:translate(1px,-1px); }
}
.glitch { animation:glitch 0.3s ease; }

/* ── SCAN LINE ── */
.scan-line {
  position:fixed; left:0; right:0; height:2px;
  background:linear-gradient(90deg,transparent,rgba(245,197,24,0.4),transparent);
  z-index:15; pointer-events:none;
  animation:scanLine 3s linear infinite;
}
@keyframes scanLine {
  from { top:-2px; }
  to   { top:100%; }
}
</style>
</head>
<body>

<canvas id="bg-canvas"></canvas>
<div class="scan-line"></div>
<div id="progress-bar" style="width:0%"></div>
<button id="skip-btn" onclick="goToFinale()">Skip →</button>

<!-- SCENE 0: LOGO INTRO -->
<div class="scene" id="s0">
  <div class="intro-logo" id="intro-logo">MKEYZ<br>STUDIO</div>
  <div class="intro-sub" id="intro-sub">Powered by Telegram</div>
  <div class="intro-line" id="intro-line"></div>
</div>

<!-- SCENE 1: TAGLINE -->
<div class="scene" id="s1">
  <div class="tagline">
    <span class="line" id="tl1">El primer</span>
    <span class="line" id="tl2"><span class="highlight">estudio musical</span></span>
    <span class="line" id="tl3">dentro de Telegram</span>
  </div>
</div>

<!-- SCENE 2: DAW -->
<div class="scene" id="s2">
  <div class="feat-icon" id="fi2">🎛️</div>
  <div class="feat-title" id="ft2">Mini DAW</div>
  <div class="feat-desc" id="fd2">Pitch · Speed · Reverb · EQ · Delay<br>Procesa audio directamente en el chat</div>
  <div class="feat-tags" id="ftags2">
    <span class="feat-tag" style="background:#1a1500;color:#f5c518;border:1px solid #f5c51844">Pitch Shift</span>
    <span class="feat-tag" style="background:#1a1500;color:#f5c518;border:1px solid #f5c51844">Reverb</span>
    <span class="feat-tag" style="background:#1a1500;color:#f5c518;border:1px solid #f5c51844">EQ</span>
    <span class="feat-tag" style="background:#1a1500;color:#f5c518;border:1px solid #f5c51844">Delay</span>
  </div>
</div>

<!-- SCENE 3: CHORD GENERATOR -->
<div class="scene" id="s3">
  <div class="feat-icon" id="fi3">🎹</div>
  <div class="feat-title" id="ft3">Chord Generator</div>
  <div class="feat-desc" id="fd3">Progresiones de acordes por género<br>Export directo a MIDI para FL Studio</div>
  <div class="feat-tags" id="ftags3">
    <span class="feat-tag" style="background:#1a0040;color:#a78bfa;border:1px solid #a78bfa44">Trap</span>
    <span class="feat-tag" style="background:#1a0040;color:#a78bfa;border:1px solid #a78bfa44">R&B</span>
    <span class="feat-tag" style="background:#1a0040;color:#a78bfa;border:1px solid #a78bfa44">Lo-Fi</span>
    <span class="feat-tag" style="background:#1a0040;color:#a78bfa;border:1px solid #a78bfa44">.MIDI</span>
  </div>
</div>

<!-- SCENE 4: VOICE STUDIO -->
<div class="scene" id="s4">
  <div class="feat-icon" id="fi4">🎤</div>
  <div class="feat-title" id="ft4">Voice Studio</div>
  <div class="feat-desc" id="fd4">Graba ideas al instante<br>Compressor · Reverb · Pitch en vivo</div>
  <div class="feat-tags" id="ftags4">
    <span class="feat-tag" style="background:#001a00;color:#00e676;border:1px solid #00e67644">Grabación</span>
    <span class="feat-tag" style="background:#001a00;color:#00e676;border:1px solid #00e67644">Efectos</span>
    <span class="feat-tag" style="background:#001a00;color:#00e676;border:1px solid #00e67644">Descarga</span>
  </div>
</div>

<!-- SCENE 5: GAMES -->
<div class="scene" id="s5">
  <div class="feat-icon" id="fi5">🎮</div>
  <div class="feat-title" id="ft5">Beat Battle Arena</div>
  <div class="feat-desc" id="fd5">Sube tu beat y que la comunidad vote<br>Ranking global · 24 horas por batalla</div>
  <div class="feat-tags" id="ftags5">
    <span class="feat-tag" style="background:#1a0000;color:#ff4d4d;border:1px solid #ff4d4d44">🔥 Fuego</span>
    <span class="feat-tag" style="background:#1a0000;color:#ff4d4d;border:1px solid #ff4d4d44">💀 Skip</span>
    <span class="feat-tag" style="background:#1a0000;color:#ff4d4d;border:1px solid #ff4d4d44">🏆 Ranking</span>
  </div>
</div>

<!-- SCENE 6: RETO SEMANAL -->
<div class="scene" id="s6">
  <div class="feat-icon" id="fi6">🏆</div>
  <div class="feat-title" id="ft6">Reto Semanal</div>
  <div class="feat-desc" id="fd6">Nuevo reto cada lunes<br>Sube tu audio · La comunidad vota al mejor</div>
  <div class="feat-tags" id="ftags6">
    <span class="feat-tag" style="background:#1a1500;color:#f5c518;border:1px solid #f5c51844">Beat 140 BPM</span>
    <span class="feat-tag" style="background:#1a1500;color:#f5c518;border:1px solid #f5c51844">Freestyle</span>
    <span class="feat-tag" style="background:#1a1500;color:#f5c518;border:1px solid #f5c51844">Sample Flip</span>
  </div>
</div>

<!-- SCENE 7: PLANES -->
<div class="scene" id="s7">
  <div class="feat-title" id="ft7" style="margin-bottom:20px;font-size:24px">Elige tu plan</div>
  <div class="plans-row">
    <div class="plan-card" id="pc1" style="background:#111;border:1px solid #222;transition-delay:0s">
      <div class="plan-emoji">🆓</div>
      <div class="plan-name">Free</div>
      <div class="plan-price">Gratis</div>
    </div>
    <div class="plan-card" id="pc2" style="background:#1a1500;border:1px solid #f5c51844;transition-delay:0.15s">
      <div class="plan-emoji">⭐</div>
      <div class="plan-name" style="color:#f5c518">Pro</div>
      <div class="plan-price">50 Stars</div>
    </div>
    <div class="plan-card" id="pc3" style="background:#1a0040;border:1px solid #a78bfa44;transition-delay:0.3s">
      <div class="plan-emoji">🎛️</div>
      <div class="plan-name" style="color:#a78bfa">Studio</div>
      <div class="plan-price">150 Stars</div>
    </div>
  </div>
</div>

<!-- SCENE 8: FINALE -->
<div class="scene" id="s8">
  <div class="finale-title" id="finale-title">Tu estudio.<br>En tu bolsillo.</div>
  <div class="finale-url" id="finale-url">t.me/MkeyzDAWbot</div>
  <button class="finale-cta" id="finale-cta" onclick="openBot()">🚀 Entrar al Studio</button>
</div>

<script>
const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); tg.setHeaderColor("#000000"); tg.setBackgroundColor("#000000"); }

// ── AUDIO ENGINE ──────────────────────────────────────────────
let audioCtx;
function getAudio() {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  return audioCtx;
}

function playKick() {
  try {
    const ctx  = getAudio();
    const osc  = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.frequency.setValueAtTime(150, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(40, ctx.currentTime + 0.1);
    gain.gain.setValueAtTime(0.8, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
    osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.2);
  } catch(e) {}
}

function playHihat() {
  try {
    const ctx    = getAudio();
    const buffer = ctx.createBuffer(1, ctx.sampleRate * 0.05, ctx.sampleRate);
    const data   = buffer.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
    const src    = ctx.createBufferSource();
    const filter = ctx.createBiquadFilter();
    const gain   = ctx.createGain();
    filter.type = "highpass"; filter.frequency.value = 8000;
    src.buffer = buffer;
    src.connect(filter); filter.connect(gain); gain.connect(ctx.destination);
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.05);
    src.start(ctx.currentTime);
  } catch(e) {}
}

function playWhoosh() {
  try {
    const ctx  = getAudio();
    const osc  = ctx.createOscillator();
    const gain = ctx.createGain();
    const filter = ctx.createBiquadFilter();
    osc.connect(filter); filter.connect(gain); gain.connect(ctx.destination);
    filter.type = "bandpass"; filter.frequency.value = 1200;
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(800, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(200, ctx.currentTime + 0.3);
    gain.gain.setValueAtTime(0.2, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
    osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.3);
  } catch(e) {}
}

function playRise() {
  try {
    const ctx  = getAudio();
    const osc  = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.type = "sine";
    osc.frequency.setValueAtTime(200, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1200, ctx.currentTime + 0.8);
    gain.gain.setValueAtTime(0.1, ctx.currentTime);
    gain.gain.linearRampToValueAtTime(0.3, ctx.currentTime + 0.5);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.9);
    osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.9);
  } catch(e) {}
}

function playChime() {
  try {
    const ctx   = getAudio();
    const freqs = [523, 659, 784, 1047];
    freqs.forEach((f, i) => {
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain); gain.connect(ctx.destination);
      osc.type = "sine"; osc.frequency.value = f;
      const t = ctx.currentTime + i * 0.08;
      gain.gain.setValueAtTime(0, t);
      gain.gain.linearRampToValueAtTime(0.15, t + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.8);
      osc.start(t); osc.stop(t + 0.8);
    });
  } catch(e) {}
}

// Beat loop
let beatLoop;
function startBeat() {
  let step = 0;
  beatLoop = setInterval(() => {
    if (step % 4 === 0) playKick();
    if (step % 2 === 1) playHihat();
    step++;
  }, 150);
}
function stopBeat() { clearInterval(beatLoop); }

// ── BACKGROUND CANVAS ─────────────────────────────────────────
const bgCanvas = document.getElementById("bg-canvas");
const bgCtx    = bgCanvas.getContext("2d");
let particles  = [];
let bgHue      = 280;

function initBg() {
  bgCanvas.width  = window.innerWidth;
  bgCanvas.height = window.innerHeight;
}

function drawBg() {
  requestAnimationFrame(drawBg);
  bgCtx.fillStyle = `rgba(0,0,0,0.08)`;
  bgCtx.fillRect(0, 0, bgCanvas.width, bgCanvas.height);

  // Grid lines
  bgCtx.strokeStyle = `rgba(245,197,24,0.03)`;
  bgCtx.lineWidth = 1;
  for (let x = 0; x < bgCanvas.width; x += 40) {
    bgCtx.beginPath();
    bgCtx.moveTo(x, 0); bgCtx.lineTo(x, bgCanvas.height);
    bgCtx.stroke();
  }
  for (let y = 0; y < bgCanvas.height; y += 40) {
    bgCtx.beginPath();
    bgCtx.moveTo(0, y); bgCtx.lineTo(bgCanvas.width, y);
    bgCtx.stroke();
  }

  // Floating orbs
  if (Math.random() < 0.05) {
    particles.push({
      x: Math.random() * bgCanvas.width,
      y: bgCanvas.height + 10,
      r: Math.random() * 3 + 1,
      speed: Math.random() * 1 + 0.5,
      hue: Math.random() * 60 + 260,
      opacity: Math.random() * 0.5 + 0.1,
    });
  }

  particles = particles.filter(p => p.y > -20);
  particles.forEach(p => {
    p.y -= p.speed;
    bgCtx.beginPath();
    bgCtx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    bgCtx.fillStyle = `hsla(${p.hue},100%,70%,${p.opacity})`;
    bgCtx.fill();
  });
}

// ── SCENES ENGINE ─────────────────────────────────────────────
const TOTAL_DURATION = 30000; // 30 seconds
const SCENES = [
  { id:"s0", duration:3000, enter: enterS0 },
  { id:"s1", duration:3500, enter: enterS1 },
  { id:"s2", duration:3000, enter: enterFeature.bind(null,2) },
  { id:"s3", duration:3000, enter: enterFeature.bind(null,3) },
  { id:"s4", duration:3000, enter: enterFeature.bind(null,4) },
  { id:"s5", duration:3000, enter: enterFeature.bind(null,5) },
  { id:"s6", duration:3000, enter: enterFeature.bind(null,6) },
  { id:"s7", duration:3500, enter: enterS7 },
  { id:"s8", duration:5000, enter: enterFinale },
];

let currentScene = -1;
let totalElapsed = 0;
let progressInterval;

function showScene(idx) {
  // Hide all
  document.querySelectorAll(".scene").forEach(s => s.classList.remove("active"));
  // Show current
  const sceneEl = document.getElementById(SCENES[idx].id);
  if (sceneEl) sceneEl.classList.add("active");
  currentScene = idx;
  SCENES[idx].enter();
}

function hideScene(idx) {
  const sceneEl = document.getElementById(SCENES[idx]?.id);
  if (sceneEl) sceneEl.classList.remove("active");
}

function enterS0() {
  playRise();
  setTimeout(() => {
    document.getElementById("intro-logo").classList.add("show");
    setTimeout(() => {
      document.getElementById("intro-sub").classList.add("show");
      document.getElementById("intro-line").classList.add("show");
    }, 400);
  }, 100);
}

function enterS1() {
  playWhoosh();
  setTimeout(() => { document.getElementById("tl1").classList.add("show"); playKick(); }, 100);
  setTimeout(() => { document.getElementById("tl2").classList.add("show"); playKick(); }, 500);
  setTimeout(() => { document.getElementById("tl3").classList.add("show"); playKick(); }, 900);
}

function enterFeature(n) {
  playWhoosh();
  setTimeout(() => { document.getElementById("fi"+n).classList.add("show"); playKick(); }, 100);
  setTimeout(() => { document.getElementById("ft"+n).classList.add("show"); }, 300);
  setTimeout(() => { document.getElementById("fd"+n).classList.add("show"); }, 500);
  const tags = document.querySelectorAll("#ftags"+n+" .feat-tag");
  tags.forEach((t, i) => {
    setTimeout(() => {
      t.classList.add("show");
      playHihat();
    }, 700 + i * 100);
  });
}

function enterS7() {
  playChime();
  setTimeout(() => document.getElementById("ft7").classList.add("show"), 100);
  setTimeout(() => { document.getElementById("pc1").classList.add("show"); playHihat(); }, 300);
  setTimeout(() => { document.getElementById("pc2").classList.add("show"); playHihat(); }, 500);
  setTimeout(() => { document.getElementById("pc3").classList.add("show"); playHihat(); }, 700);
}

function enterFinale() {
  stopBeat();
  playRise();
  setTimeout(() => playChime(), 600);
  setTimeout(() => { document.getElementById("finale-title").classList.add("show"); }, 200);
  setTimeout(() => { document.getElementById("finale-url").classList.add("show"); }, 800);
  setTimeout(() => { document.getElementById("finale-cta").classList.add("show"); }, 1200);
  if (tg) tg.HapticFeedback?.notificationOccurred("success");
}

function goToFinale() {
  clearTimeout(nextSceneTimeout);
  clearInterval(progressInterval);
  showScene(SCENES.length - 1);
  document.getElementById("progress-bar").style.width = "100%";
  document.getElementById("skip-btn").style.display = "none";
}

let nextSceneTimeout;
function runScene(idx) {
  if (idx >= SCENES.length) return;
  showScene(idx);

  nextSceneTimeout = setTimeout(() => {
    runScene(idx + 1);
  }, SCENES[idx].duration);
}

function openBot() {
  if (tg) {
    tg.close();
  } else {
    window.open("https://t.me/MkeyzDAWbot", "_blank");
  }
}

// Progress bar
function startProgress() {
  let elapsed = 0;
  progressInterval = setInterval(() => {
    elapsed += 100;
    const pct = Math.min(100, (elapsed / TOTAL_DURATION) * 100);
    document.getElementById("progress-bar").style.width = pct + "%";
    if (elapsed >= TOTAL_DURATION) clearInterval(progressInterval);
  }, 100);
}

// ── START ─────────────────────────────────────────────────────
window.addEventListener("resize", initBg);
initBg();
drawBg();
startBeat();
startProgress();
runScene(0);
</script>
</body>
</html>
