// Uses an installed Chromium browser and Node's built-in WebSocket; no npm dependencies.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';
import { RULES } from '../src/engine.js';

const webRoot = fileURLToPath(new URL('../', import.meta.url));
const url = process.argv[2] ?? 'http://127.0.0.1:8000/';
const candidates = [
  process.env.BROWSER_PATH,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome',
].filter(Boolean);
const browserPath = candidates.find(candidate => existsSync(candidate));
if (!browserPath) throw new Error('Chrome/Edge was not found. Set BROWSER_PATH to its executable.');

const output = path.join(webRoot, '.qa');
await mkdir(output, { recursive: true });
const profile = path.join(output, `browser-profile-${Date.now()}`);
const child = spawn(browserPath, [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--disable-extensions', '--disable-background-networking', '--remote-debugging-port=0',
  `--user-data-dir=${profile}`, 'about:blank',
], { windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'] });

let socket;
const pending = new Map();
const errors = [];
let nextId = 0;
let sessionId;
const report = [];

function send(method, params = {}, targetSession = sessionId) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timed out: ${method}`)); }, 10000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params, ...(targetSession ? { sessionId: targetSession } : {}) }));
  });
}

async function evaluate(expression) {
  const response = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (response.exceptionDetails) throw new Error(response.exceptionDetails.text);
  return response.result.value;
}

async function until(expression, timeout = 10000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const result = await evaluate(expression);
    if (result) return result;
    await delay(50);
  }
  throw new Error(`Page condition timed out: ${expression}`);
}

async function key(key, code, virtualKeyCode) {
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key, code, windowsVirtualKeyCode: virtualKeyCode });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key, code, windowsVirtualKeyCode: virtualKeyCode });
}

async function screenshot(filename) {
  const result = await send('Page.captureScreenshot', { format: 'png' });
  await writeFile(path.join(output, filename), Buffer.from(result.data, 'base64'));
}

async function dimensions(width, height, mobile) {
  await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile });
  await send('Emulation.setTouchEmulationEnabled', { enabled: mobile });
}

async function touchCanvas() {
  const point = await evaluate(`(() => { const r = document.querySelector('canvas').getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; })()`);
  await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ ...point, radiusX: 1, radiusY: 1, force: 1, id: 0 }] });
  await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
}

async function stoppedGameState() {
  return evaluate(`(() => { const game = window.__JUMPBUGI__.engine; return {
    phase: window.__JUMPBUGI__.phase, gameOver: game.gameOver, paused: game.paused,
    elapsed: game.elapsed, score: game.score, obstacleX: game.obstacle.x,
    backgroundX: game.backgroundX, playerY: game.playerY,
    animationTick: game.animationTick, playerFrame: game.playerFrame,
    obstacleAnimationTick: game.obstacle.animationTick
  }; })()`);
}

async function checkGameOverMessage() {
  assert.equal(await evaluate(`document.querySelector('#result-overlay').hidden`), false, 'Game over overlay is hidden');
  assert.equal(await evaluate(`document.querySelector('#game-over-title').innerText.trim()`), 'GAME OVER', 'Game over message is missing');
  assert.equal(await evaluate(`document.querySelector('#game-over-title').getBoundingClientRect().height > 0`), true, 'Game over message is not visible');
}

async function rememberRankingLayout() {
  await evaluate(`(() => {
    const card = document.querySelector('.ranking-card');
    window.__qaRankingNode ??= card;
    const rect = card.getBoundingClientRect();
    window.__qaRankingPosition = { top: rect.top + scrollY, left: rect.left + scrollX };
  })()`);
}

async function checkFixedRanking(belowGame = false) {
  const layout = await evaluate(`(() => {
    const card = document.querySelector('.ranking-card');
    const game = document.querySelector('.game-column');
    const rect = card.getBoundingClientRect();
    const gameRect = game.getBoundingClientRect();
    const canvasRect = document.querySelector('canvas').getBoundingClientRect();
    const hud = document.querySelector('.game-hud');
    const hudRect = hud.getBoundingClientRect();
    const style = getComputedStyle(card);
    const pause = document.querySelector('#pause-button');
    return {
      count: document.querySelectorAll('.ranking-card').length,
      sameNode: card === window.__qaRankingNode,
      visible: !card.hidden && style.display !== 'none' && style.visibility !== 'hidden' && rect.height > 0,
      top: rect.top + scrollY, left: rect.left + scrollX,
      expected: window.__qaRankingPosition,
      followsGame: Boolean(game.compareDocumentPosition(card) & Node.DOCUMENT_POSITION_FOLLOWING),
      belowGame: rect.top >= gameRect.bottom,
      scoreBelowCanvas: !hud.hidden && hudRect.height > 0 && hudRect.top >= canvasRect.bottom - 1,
      rankingBelowScore: rect.top >= hudRect.bottom - 1,
      pauseHidden: pause.hidden && pause.disabled && getComputedStyle(pause).display === 'none'
    };
  })()`);
  assert.equal(layout.count, 1, 'Ranking board was duplicated');
  assert.equal(layout.sameNode, true, 'Game state replaced the ranking board');
  assert.equal(layout.visible, true, 'Game state hid the ranking board');
  assert.ok(Math.abs(layout.top - layout.expected.top) <= 1, 'Game state moved the ranking board vertically');
  assert.ok(Math.abs(layout.left - layout.expected.left) <= 1, 'Game state moved the ranking board horizontally');
  assert.equal(layout.followsGame, true, 'Ranking board no longer follows the game in the page structure');
  assert.equal(layout.scoreBelowCanvas, true, 'Score and result area is not below the game canvas');
  if (belowGame) {
    assert.equal(layout.belowGame, true, 'Mobile ranking is not below the game');
    assert.equal(layout.rankingBelowScore, true, 'Mobile ranking is not below the score and result area');
  }
  assert.equal(layout.pauseHidden, true, 'The upper pause button became visible or enabled');
}

try {
  const endpoint = await new Promise((resolve, reject) => {
    let stderr = '';
    const timer = setTimeout(() => reject(new Error(`Browser did not expose CDP: ${stderr.slice(-1200)}`)), 15000);
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('exit', code => { clearTimeout(timer); reject(new Error(`Browser exited with code ${code}: ${stderr.slice(-1200)}`)); });
    child.stderr.on('data', data => {
      stderr += data.toString();
      const match = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) { clearTimeout(timer); resolve(match[1]); }
    });
  });
  socket = new WebSocket(endpoint);
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const request = pending.get(message.id);
      if (!request) return;
      clearTimeout(request.timer);
      pending.delete(message.id);
      if (message.error) request.reject(new Error(message.error.message));
      else request.resolve(message.result ?? {});
    } else if (message.method === 'Runtime.exceptionThrown') {
      errors.push(message.params.exceptionDetails.exception?.description ?? message.params.exceptionDetails.text);
    } else if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') {
      errors.push(message.params.args.map(arg => arg.value ?? arg.description).join(' '));
    }
  });
  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, { once: true });
    socket.addEventListener('error', reject, { once: true });
  });
  const { targetId } = await send('Target.createTarget', { url: 'about:blank' }, null);
  ({ sessionId } = await send('Target.attachToTarget', { targetId, flatten: true }, null));
  await send('Page.enable');
  await send('Runtime.enable');
  await dimensions(1440, 1000, false);
  await send('Page.navigate', { url });
  await until(`window.__JUMPBUGI__?.engine && window.__JUMPBUGI__.phase === 'splash'`, 30000);
  await delay(80);
  assert.equal(await evaluate(`(() => { const c = document.querySelector('canvas'); return c.getContext('2d').getImageData(0, 0, c.width, c.height).data.some((value, index) => index % 4 !== 3 && value < 200); })()`), true, 'Intro canvas is blank');
  assert.equal(await evaluate(`(() => { const c=document.querySelector('canvas'); const ctx=c.getContext('2d'); const x=Math.round(c.width/8); return [.2,.5,.8].every(ratio => {const pixel=ctx.getImageData(x,Math.floor(c.height*ratio),1,1).data; return pixel[0]===255 && pixel[1]===255 && pixel[2]===255;}); })()`), true, 'Intro artwork edge differs from the white canvas');
  assert.equal(await evaluate(`getComputedStyle(document.querySelector('.game-card')).boxShadow`), 'none', 'Intro still has a translucent outer shadow');
  const introCanvas = await evaluate(`document.querySelector('canvas').toDataURL()`);
  await rememberRankingLayout();
  await checkFixedRanking();
  await screenshot('desktop-intro.png');
  await until(`window.__JUMPBUGI__?.engine && window.__JUMPBUGI__.phase === 'ready'`, 30000);
  assert.equal(await evaluate(`document.querySelector('canvas').toDataURL()`), introCanvas, 'Ready phase removed or cropped the intro');
  assert.equal(await evaluate(`document.querySelector('.game-hud').hidden`), false, 'Persistent score and result area is hidden');
  const readyObstacleX = await evaluate(`window.__JUMPBUGI__.engine.obstacle.x`);
  await delay(2300);
  assert.equal(await evaluate(`window.__JUMPBUGI__.phase`), 'ready', 'Intro did not wait for input');
  assert.equal(await evaluate(`document.querySelector('canvas').toDataURL()`), introCanvas, 'Intro disappeared while waiting for input');
  assert.equal(await evaluate(`window.__JUMPBUGI__.engine.score`), 0, 'Waiting intro earned score');
  assert.equal(await evaluate(`window.__JUMPBUGI__.engine.obstacle.x`), readyObstacleX, 'Waiting intro moved an obstacle');
  assert.equal(await evaluate(`window.__JUMPBUGI__.engine.playerX`), RULES.playerX, 'Browser player position differs from the current configuration');
  assert.equal(await evaluate(`document.querySelectorAll('.site-header,.page-heading,.score-strip,.controls-row,.how-to,.site-footer,#season-label,#game-status,#jump-button,#best-score').length`), 0, 'Removed explanatory UI is still present');
  assert.equal(await evaluate(`['start-button','pause-button','resume-button','restart-button'].every(id => document.getElementById(id).textContent.trim() === '')`), true, 'A game control still has visible text');
  assert.equal(await evaluate(`document.documentElement.scrollWidth <= innerWidth + 1`), true, 'Desktop page overflows horizontally');
  await checkFixedRanking();
  await screenshot('desktop-ready.png');
  report.push('intro: visible through splash and ready; remains until input; no score or obstacle progress');
  report.push('desktop: configured player position; explanatory UI removed; icon controls; no horizontal overflow');

  await key(' ', 'Space', 32);
  await until(`window.__JUMPBUGI__.phase === 'playing'`);
  assert.equal(await evaluate(`document.querySelector('.game-hud').hidden`), false, 'Playing HUD is hidden');
  assert.equal(await evaluate(`document.querySelector('.game-column').innerText.replace(/\\s+/g, '').trim()`), 'SCORE0TIME00:00', 'Game area includes text beyond SCORE and TIME');
  assert.equal(await evaluate(`document.querySelector('#score').getBoundingClientRect().left < document.querySelector('#elapsed').getBoundingClientRect().left`), true, 'SCORE is not left of TIME');
  assert.equal(await evaluate(`window.__JUMPBUGI__.engine.isJumping`), false, 'Start key also triggered jump');
  await checkFixedRanking();
  await key('Escape', 'Escape', 27);
  assert.equal(await evaluate(`window.__JUMPBUGI__.engine.paused`), true);
  await checkFixedRanking();
  const elapsed = await evaluate(`window.__JUMPBUGI__.engine.elapsed`);
  await delay(250);
  assert.equal(await evaluate(`window.__JUMPBUGI__.engine.elapsed`), elapsed, 'Paused game continued to progress');
  await key('Escape', 'Escape', 27);
  await key(' ', 'Space', 32);
  assert.equal(await evaluate(`window.__JUMPBUGI__.engine.isJumping`), true, 'Space did not jump');
  await checkFixedRanking();
  await screenshot('desktop-jump.png');
  report.push('keyboard: start consumes first Space; jump; pause freezes elapsed time; resume');

  await until(`window.__JUMPBUGI__.phase === 'gameover'`, 15000);
  await checkGameOverMessage();
  await checkFixedRanking();
  const stopped = await stoppedGameState();
  const identity = await evaluate(`localStorage.getItem('jumpbugi.web.v1.identity')`);
  const results = await evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.results'))`);
  assert.equal(results.length, 1, 'Game over should save exactly one result');
  assert.equal(results[0].score, await evaluate(`window.__JUMPBUGI__.engine.score`));
  await delay(250);
  assert.deepEqual(await stoppedGameState(), stopped, 'A completed game continued to move, animate or score');
  await key('Escape', 'Escape', 27);
  await key(' ', 'Space', 32);
  assert.deepEqual(await stoppedGameState(), stopped, 'Escape or Space resumed a completed game');
  assert.equal(await evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.results')).length`), 1, 'Game over saved duplicate results');
  await screenshot('desktop-gameover.png');
  await key('Enter', 'Enter', 13);
  assert.equal(await evaluate(`window.__JUMPBUGI__.phase`), 'playing', 'Restart replayed intro');
  assert.equal(await evaluate(`window.__JUMPBUGI__.engine.gameOver`), false);
  assert.equal(await evaluate(`window.__JUMPBUGI__.engine.score`), 0);
  await checkFixedRanking();
  await key('Escape', 'Escape', 27);
  report.push('game over: GAME OVER message; movement, animation and score stop; Escape and Space keep the result; Enter restarts; one result saved');

  await dimensions(390, 844, true);
  await send('Page.navigate', { url });
  await until(`window.__JUMPBUGI__?.engine && window.__JUMPBUGI__.phase === 'ready'`, 30000);
  assert.equal(await evaluate(`localStorage.getItem('jumpbugi.web.v1.identity')`), identity, 'Player ID changed on reload');
  assert.equal(await evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.results')).length`), 1, 'Stored result lost on reload');
  assert.equal(await evaluate(`document.documentElement.scrollWidth <= innerWidth + 1`), true, 'Portrait page overflows horizontally');
  await rememberRankingLayout();
  await checkFixedRanking(true);
  await screenshot('mobile-portrait.png');
  await touchCanvas();
  await checkFixedRanking(true);
  await until(`window.__JUMPBUGI__.phase === 'playing'`);
  assert.equal(await evaluate(`window.__JUMPBUGI__.engine.isJumping`), false, 'Start touch also triggered jump');
  await touchCanvas();
  assert.equal(await evaluate(`window.__JUMPBUGI__.engine.isJumping`), true, 'Touch did not jump');
  await checkFixedRanking(true);
  await screenshot('mobile-playing.png');
  report.push('mobile portrait: ranking remains below the game through ready, transition and playing; touch starts then jumps');

  await key('Escape', 'Escape', 27);
  await checkFixedRanking(true);
  await dimensions(844, 390, true);
  await delay(100);
  await rememberRankingLayout();
  await checkFixedRanking(true);
  assert.equal(await evaluate(`document.documentElement.scrollWidth <= innerWidth + 1`), true, 'Landscape page overflows horizontally');
  assert.equal(await evaluate(`document.querySelector('canvas').getBoundingClientRect().bottom <= innerHeight`), true, 'Landscape game falls below the viewport');
  await screenshot('mobile-landscape.png');
  report.push('mobile landscape: resize keeps layout usable');
  await key('Escape', 'Escape', 27);
  await until(`window.__JUMPBUGI__.phase === 'gameover'`, 15000);
  await checkGameOverMessage();
  await checkFixedRanking(true);
  assert.equal(await evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.results')).length`), 2);
  await screenshot('mobile-gameover.png');
  await evaluate(`document.querySelector('#restart-button').click()`);
  assert.equal(await evaluate(`window.__JUMPBUGI__.phase`), 'playing');
  await checkFixedRanking(true);
  report.push('fixed UI: one persistent ranking node keeps its page position in every state; upper pause button remains hidden; Esc pause and resume work');
  report.push('persistence: identity and result retained on reload; mobile ranking stays in place on game over and restart');
  assert.deepEqual(errors, [], `Browser errors: ${errors.join('\n')}`);
  await writeFile(path.join(output, 'browser-report.json'), JSON.stringify({ url, browser: browserPath, checks: report, errors }, null, 2));
  console.log(JSON.stringify({ passed: true, checks: report, screenshots: output }, null, 2));
} finally {
  if (socket?.readyState === WebSocket.OPEN) {
    await Promise.race([send('Browser.close', {}, null).catch(() => {}), delay(1000)]);
    socket.close();
  }
  for (const request of pending.values()) { clearTimeout(request.timer); request.reject(new Error('Browser closed')); }
  if (child.exitCode === null) child.kill();
}
