import { GameEngine } from './engine.js';
import { PlayerStore } from './storage.js';
import { isLocalServerMode, LocalServerSync } from './api.js';

const WIDTH = 640;
const HEIGHT = 360;
const $ = id => document.getElementById(id);
const canvas = $('game-canvas');
const context = canvas.getContext('2d', { alpha: false });
const store = new PlayerStore();
const images = new Map();
const overlays = ['loading', 'ready', 'pause', 'result'];
let engine;
let manifest;
let introArtwork;
let phase = 'loading';
let introElapsed = 0;
let transitionElapsed = 0;
let previousTime = null;
let recorded = false;
let lastUI = '';
const serverSync = new LocalServerSync({
  enabled: isLocalServerMode(window.location), identity: store.identity,
  onChange: () => renderLeaderboard(),
});

// Read-only access to the running instance for local browser verification.
Object.defineProperty(window, '__JUMPBUGI__', {
  value: Object.freeze({ get engine() { return engine; }, get phase() { return phase; },
    get server() { return serverSync.snapshot; } }),
});

export function formatTime(seconds) {
  const whole = Math.floor(Math.max(0, seconds));
  return `${String(Math.floor(whole / 60)).padStart(2, '0')}:${String(whole % 60).padStart(2, '0')}`;
}

function showOverlay(name) {
  for (const value of overlays) $(value + '-overlay').hidden = value !== name;
}

function syncCanvasResolution() {
  if (!context) return;
  const ratio = Math.min(2, Math.max(1, window.devicePixelRatio || 1));
  canvas.width = WIDTH * ratio;
  canvas.height = HEIGHT * ratio;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = 'high';
}

function changePhase(next) {
  phase = next;
  document.body.dataset.phase = next;
  refreshUI(true);
}

function renderLeaderboard() {
  const server = serverSync.snapshot;
  const shared = server.enabled && server.state === 'saved' && server.leaderboard !== null;
  $('nickname').textContent = store.identity.nickname;
  $('ranking-mode').textContent = shared ? '로컬 서버 공동 기록'
    : server.enabled ? '이 브라우저의 기록 · 서버 대기' : store.isDemo ? '예시 기록' : '이 브라우저의 기록';
  $('personal-best-label').textContent = '이 브라우저 최고';
  $('ranking-note').textContent = store.isDemo
    ? '첫 플레이 후 내 기록이 표시됩니다.'
    : '이 브라우저에 저장된 기록입니다.';
  if (server.enabled) {
    let message = server.state === 'syncing' ? '서버에 반영 중…'
      : server.state === 'error' ? `${server.error} 기록은 이 브라우저에 보관됩니다.`
      : shared ? '서버의 사용자별 최고 기록' : '서버 연결 대기';
    if (server.state === 'saved' && server.lastSavedRunId) message = '서버 저장 완료 · 사용자별 최고 기록';
    if (server.pendingCount) message += ` 미전송 ${server.pendingCount}개.`;
    if (server.state === 'error' && server.nicknamePending) message += ' 닉네임 반영도 대기 중입니다.';
    if (!server.persistent && server.pendingCount) message += ' 전송 대기는 이번 접속 동안만 유지됩니다.';
    if (server.localOnlyCount) message += ` 대기열 초과 ${server.localOnlyCount}개는 이 브라우저에만 보관됩니다.`;
    const status = document.createElement('span');
    status.textContent = message;
    $('ranking-note').classList.add('server-note');
    $('ranking-note').dataset.state = server.state;
    const retry = document.createElement('button');
    retry.id = 'server-retry-button';
    retry.className = 'board-button board-refresh';
    retry.type = 'button';
    retry.textContent = server.state === 'error' || server.pendingCount ? '재시도' : '새로고침';
    retry.setAttribute('aria-label', server.state === 'error' || server.pendingCount ? '서버 저장 재시도' : '공동 기록 새로고침');
    retry.disabled = server.state === 'syncing';
    retry.addEventListener('click', () => { void serverSync.retry(); });
    $('ranking-note').replaceChildren(status, retry);
  }
  $('ranking-best').textContent = store.results.length ? `${store.best.toLocaleString('ko-KR')}점` : '기록 없음';
  $('storage-note').hidden = store.persistent;
  if (!store.persistent) $('storage-note').textContent = '브라우저 저장소를 사용할 수 없어 닉네임과 기록은 이번 접속 동안만 보관해요.';
  $('ranking-list').replaceChildren(...(shared ? server.leaderboard : store.leaderboard()).map((entry, index) => {
    const item = document.createElement('li');
    const number = document.createElement('span');
    number.className = 'rank-number';
    number.textContent = String(index + 1).padStart(2, '0');
    const name = document.createElement('div');
    name.className = 'rank-name';
    const nickname = document.createElement('strong');
    const displayName = !shared && entry.player_id === store.identity.player_id ? store.identity.nickname : entry.nickname;
    nickname.textContent = displayName;
    nickname.title = displayName;
    const time = document.createElement('span');
    time.textContent = `달린 시간 ${formatTime(entry.survival_time)}`;
    name.append(nickname, time);
    const score = document.createElement('span');
    score.className = 'rank-score';
    score.textContent = entry.score.toLocaleString('ko-KR');
    item.append(number, name, score);
    return item;
  }));
}

function closeNicknameEditor() {
  $('nickname-form').hidden = true;
  $('nickname-edit-button').setAttribute('aria-expanded', 'false');
  $('nickname-edit-button').focus({ preventScroll: true });
}

function editNickname() {
  if (phase === 'playing' && !engine.gameOver) {
    engine.setPaused(true);
    refreshUI(true);
  }
  $('nickname-input').value = store.identity.nickname;
  $('nickname-input').removeAttribute('aria-invalid');
  $('nickname-error').textContent = '';
  $('nickname-form').hidden = false;
  $('nickname-edit-button').setAttribute('aria-expanded', 'true');
  $('nickname-input').focus({ preventScroll: true });
  $('nickname-input').select();
}

function saveNickname(event) {
  event.preventDefault();
  const result = store.setNickname($('nickname-input').value);
  if (!result.ok) {
    $('nickname-error').textContent = result.error;
    $('nickname-input').setAttribute('aria-invalid', 'true');
    $('nickname-input').focus({ preventScroll: true });
    return;
  }
  closeNicknameEditor();
  renderLeaderboard();
  if (result.changed) void serverSync.syncIdentity();
}

function refreshUI(force = false) {
  const paused = !!engine?.paused;
  const score = engine?.score ?? 0;
  const elapsed = engine?.elapsed ?? 0;
  const key = `${phase}:${paused}:${score}:${Math.floor(elapsed)}`;
  if (!force && key === lastUI) return;
  lastUI = key;
  document.body.dataset.paused = String(paused);
  $('score').textContent = score.toLocaleString('ko-KR');
  $('elapsed').textContent = formatTime(elapsed);
  if (phase === 'loading') showOverlay('loading');
  else if (phase === 'ready') showOverlay('ready');
  else if (phase === 'gameover') showOverlay('result');
  else if (paused) showOverlay('pause');
  else showOverlay(null);
}

function start() {
  if (phase !== 'ready') return;
  transitionElapsed = 0;
  changePhase('transition');
  canvas.focus({ preventScroll: true });
}

function restart() {
  if (phase !== 'gameover') return;
  engine.reset();
  recorded = false;
  changePhase('playing');
  canvas.focus({ preventScroll: true });
}

function jump() {
  if (phase === 'ready') start();
  else if (phase === 'playing' && !engine.paused && !engine.gameOver) engine.jump();
}

function togglePause() {
  if (phase !== 'playing' || engine.gameOver) return;
  engine.togglePause();
  refreshUI(true);
  if (!engine.paused) canvas.focus({ preventScroll: true });
}

function pauseForBackground() {
  previousTime = null;
  if (phase === 'playing' && !engine.gameOver) {
    engine.setPaused(true);
    refreshUI(true);
  }
}

function finishRun() {
  if (recorded) return;
  recorded = true;
  const result = store.recordRun({
    score: engine.score, survival_time: engine.elapsed,
    death_obstacle: engine.obstacle?.name,
    max_speed: engine.speedMultiplier,
    device_type: matchMedia('(pointer: coarse)').matches ? 'mobile' : 'desktop',
  });
  renderLeaderboard();
  changePhase('gameover');
  // Keyboard users can immediately restart; canvas retains focus for Enter.
  canvas.focus({ preventScroll: true });
  if (result) void serverSync.submit(result);
}

function drawBackground(index, x, alpha = 1) {
  if (alpha <= 0) return;
  const asset = manifest.backgrounds[index];
  const image = images.get(asset.file);
  context.globalAlpha = alpha;
  const offset = Math.floor(x);
  context.drawImage(image, offset, 0, asset.width, HEIGHT);
  context.drawImage(image, offset + asset.width, 0, asset.width, HEIGHT);
  context.globalAlpha = 1;
}

function drawFrame(frame, x, y) {
  context.drawImage(images.get(frame.file), Math.trunc(x), Math.trunc(y));
}

function prepareIntroArtwork(image) {
  const surface = document.createElement('canvas');
  surface.width = image.naturalWidth;
  surface.height = image.naturalHeight;
  const introContext = surface.getContext('2d', { willReadFrequently: true });
  if (!introContext) return image;
  introContext.fillStyle = '#fff';
  introContext.fillRect(0, 0, surface.width, surface.height);
  introContext.drawImage(image, 0, 0);
  const pixels = introContext.getImageData(0, 0, surface.width, surface.height);
  const { data } = pixels;
  const { width, height } = surface;
  const visited = new Uint8Array(width * height);
  const queue = new Uint32Array(width * height);
  let head = 0;
  let tail = 0;
  const visit = index => {
    if (visited[index]) return;
    visited[index] = 1;
    const offset = index * 4;
    const minimum = Math.min(data[offset], data[offset + 1], data[offset + 2]);
    const maximum = Math.max(data[offset], data[offset + 1], data[offset + 2]);
    if (minimum < 220 || maximum - minimum > 35) return;
    const progress = Math.min(1, (minimum - 220) / 25);
    const blend = progress * progress * (3 - 2 * progress);
    for (let channel = 0; channel < 3; channel++) {
      data[offset + channel] += (255 - data[offset + channel]) * blend;
    }
    queue[tail++] = index;
  };
  // Only flatten near-white background connected to the outside edge. Keep
  // the original PNG and the enclosed artwork, highlights and proportions.
  for (let x = 0; x < width; x++) { visit(x); visit((height - 1) * width + x); }
  for (let y = 0; y < height; y++) { visit(y * width); visit(y * width + width - 1); }
  while (head < tail) {
    const index = queue[head++];
    const x = index % width;
    if (x > 0) visit(index - 1);
    if (x < width - 1) visit(index + 1);
    if (index >= width) visit(index - width);
    if (index < width * (height - 1)) visit(index + width);
  }
  introContext.putImageData(pixels, 0, 0);
  return surface;
}

function draw() {
  context.fillStyle = '#fff';
  context.fillRect(0, 0, WIDTH, HEIGHT);
  if (phase === 'splash' || phase === 'ready') {
    const image = introArtwork;
    // Show the entire original 4:3 introduction within the wider game field.
    const scale = Math.min(WIDTH / image.width, HEIGHT / image.height);
    const width = image.width * scale;
    const height = image.height * scale;
    context.drawImage(image, (WIDTH - width) / 2, (HEIGHT - height) / 2, width, height);
    return;
  }
  if (phase === 'transition') {
    const progress = Math.min(transitionElapsed / 1.25, 1);
    const alpha = progress * progress * (3 - 2 * progress);
    drawBackground(0, engine.backgroundX, alpha);
    const frame = Math.floor(introElapsed * 60 / 6) % manifest.player.frames.length;
    drawFrame(manifest.player.frames[frame], engine.playerX, engine.playerY);
    return;
  }
  drawBackground(engine.backgroundFrom, engine.backgroundX);
  drawBackground(engine.backgroundTo, engine.backgroundX, engine.backgroundAlpha);
  for (const part of engine.drawParts) {
    const frames = manifest.obstacles[part.name].frames;
    drawFrame(frames[part.frame % frames.length], part.x, part.y);
  }
  drawFrame(manifest.player.frames[engine.playerFrame], engine.playerX, engine.playerY);
}

function frame(now) {
  requestAnimationFrame(frame);
  if (document.hidden || !engine || phase === 'loading') { previousTime = null; return; }
  const dt = previousTime === null ? 0 : Math.max(0, (now - previousTime) / 1000);
  previousTime = now;
  if (phase === 'splash') {
    introElapsed += dt;
    if (introElapsed >= 2) { introElapsed = 0; changePhase('ready'); }
  } else if (phase === 'ready') introElapsed += dt;
  else if (phase === 'transition') {
    introElapsed += dt;
    transitionElapsed += dt;
    engine.scrollBackground(Math.min(dt, 0.1));
    if (transitionElapsed + 1e-9 >= 1.25) {
      engine.animationTick = (introElapsed * 60) % (manifest.player.frames.length * 6);
      changePhase('playing');
    }
  } else if (phase === 'playing') {
    engine.update(dt);
    if (engine.gameOver) finishRun();
  }
  draw();
  refreshUI();
}

async function load() {
  renderLeaderboard();
  changePhase('loading');
  try {
    if (!context) throw new Error('Canvas를 지원하지 않는 브라우저입니다.');
    syncCanvasResolution();
    const response = await fetch('./assets/manifest.json');
    if (!response.ok) throw new Error(`자산 목록을 읽지 못했어요 (${response.status}).`);
    manifest = await response.json();
    const paths = [...new Set([manifest.intro.file, ...manifest.backgrounds.map(asset => asset.file),
      ...manifest.player.frames.map(asset => asset.file),
      ...Object.values(manifest.obstacles).flatMap(asset => asset.frames.map(frame => frame.file))])];
    let loaded = 0;
    await Promise.all(paths.map(path => new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => {
        images.set(path, image);
        loaded++;
        $('loading-detail').textContent = `이미지 불러오는 중 · ${Math.round(loaded / paths.length * 100)}%`;
        resolve();
      };
      image.onerror = () => reject(new Error(`이미지를 읽지 못했어요: ${path}`));
      image.src = new URL(path, document.baseURI).href;
    })));
    introArtwork = prepareIntroArtwork(images.get(manifest.intro.file));
    engine = new GameEngine(manifest);
    changePhase('splash');
    draw();
    requestAnimationFrame(frame);
  } catch (error) {
    $('loading-text').textContent = '게임을 불러오지 못했어요';
    $('loading-detail').textContent = location.protocol === 'file:' ? 'web 폴더의 실행 파일이나 로컬 서버로 접속해주세요.' : error.message;
    $('loading-text').classList.remove('visually-hidden');
    $('loading-detail').classList.remove('visually-hidden');
    document.querySelector('.loading-spinner').hidden = true;
    $('reload-button').hidden = false;
    console.error(error);
  }
}

document.addEventListener('keydown', event => {
  if (event.repeat || event.ctrlKey || event.metaKey || event.altKey || event.isComposing) return;
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) return;
  if (event.code === 'Tab' || ['ShiftLeft', 'ShiftRight', 'ControlLeft', 'ControlRight', 'AltLeft', 'AltRight', 'MetaLeft', 'MetaRight'].includes(event.code)) return;
  if (event.target.closest('button, a') && event.code !== 'Escape') return;
  if (phase === 'ready') { event.preventDefault(); start(); }
  else if (phase === 'playing' && event.code === 'Escape') { event.preventDefault(); togglePause(); }
  else if (phase === 'playing' && event.code === 'Space') { event.preventDefault(); jump(); }
  else if (phase === 'gameover' && event.code === 'Enter') { event.preventDefault(); restart(); }
  else if (['Space', 'ArrowUp', 'ArrowDown'].includes(event.code) && event.target === canvas) event.preventDefault();
});
canvas.addEventListener('pointerdown', event => {
  if (!event.isPrimary || event.button !== 0) return;
  event.preventDefault();
  canvas.focus({ preventScroll: true });
  jump();
});
$('start-button').addEventListener('click', start);
$('restart-button').addEventListener('click', restart);
$('resume-button').addEventListener('click', togglePause);
$('reload-button').addEventListener('click', () => location.reload());
$('nickname-edit-button').addEventListener('click', editNickname);
$('nickname-form').addEventListener('submit', saveNickname);
$('nickname-cancel-button').addEventListener('click', closeNicknameEditor);
$('nickname-form').addEventListener('keydown', event => {
  if (event.key === 'Escape' && !event.isComposing) {
    event.preventDefault();
    event.stopPropagation();
    closeNicknameEditor();
  }
});
$('nickname-input').addEventListener('input', () => {
  $('nickname-input').removeAttribute('aria-invalid');
  $('nickname-error').textContent = '';
});
document.addEventListener('visibilitychange', () => { if (document.hidden) pauseForBackground(); else previousTime = null; });
window.addEventListener('blur', pauseForBackground);
window.addEventListener('resize', syncCanvasResolution);
if (serverSync.enabled) {
  window.addEventListener('online', () => { void serverSync.retry(); });
  void serverSync.retry();
}
load();
