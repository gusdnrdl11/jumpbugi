// Real Chrome + Edge, fresh profiles, natural game overs, and the local PostgreSQL API.
// Usage: node tools/verify_local_backend.mjs http://127.0.0.1:8000/?server=1
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';

const project = fileURLToPath(new URL('../', import.meta.url));
const target = new URL(process.argv[2] ?? 'http://127.0.0.1:8000/?server=1');
assert.ok(['127.0.0.1', 'localhost', '[::1]'].includes(target.hostname), 'Use the local backend only');
assert.equal(target.protocol, 'http:', 'Use the local HTTP development server');
target.searchParams.set('server', '1');
const runTag = `${Date.now()}-${process.pid}`;
const output = path.join(project, 'web', '.qa', 'local-backend', runTag);
const sharedNickname = '검증부기';
const report = { run_tag: runTag, started_at: new Date().toISOString(), url: target.href, passed: false, checks: [], browsers: [], errors: [] };
const browsers = [
  { name: 'Chrome', candidates: [process.env.CHROME_PATH, 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'] },
  { name: 'Edge', candidates: [process.env.EDGE_PATH, 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', 'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe'] },
];
await mkdir(output, { recursive: true });

async function api(route, payload) {
  const response = await fetch(new URL(`/api/${route}`, target), {
    ...(payload === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }),
    signal: AbortSignal.timeout(10000),
  });
  return { status: response.status, body: await response.json() };
}

async function waitFor(action, timeout = 20000, description = 'browser or server state') {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) { const value = await action(); if (value) return value; await delay(100); }
  throw new Error(`Timed out waiting for ${description}`);
}

async function connectBrowser(executable, profile, errors, apiRequests) {
  const launchArguments = [
    '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--disable-extensions', '--disable-background-networking', '--disable-background-timer-throttling',
    '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank',
  ];
  const child = spawn(executable, launchArguments, { windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'] });
  let socket; let sessionId; let nextId = 0;
  let stderr = '';
  const pending = new Map();
  const requests = new Map();
  function send(method, params = {}, session = sessionId) {
    return new Promise((resolve, reject) => {
      const id = ++nextId;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, 10000);
      pending.set(id, { resolve, reject, timer });
      socket.send(JSON.stringify({ id, method, params, ...(session ? { sessionId: session } : {}) }));
    });
  }
  async function close() {
    if (socket?.readyState === WebSocket.OPEN) {
      await Promise.race([send('Browser.close', {}, null).catch(() => {}), delay(1000)]);
      socket.close();
    }
    for (const request of pending.values()) { clearTimeout(request.timer); request.reject(new Error('Browser closed')); }
    pending.clear();
    if (child.exitCode === null) child.kill();
  }
  try {
    const endpoint = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`Browser CDP startup failed: ${stderr.slice(-1000)}`)), 20000);
      child.once('error', error => { clearTimeout(timer); reject(error); });
      child.once('exit', code => { clearTimeout(timer); reject(new Error(`Browser exited ${code}: ${stderr.slice(-1000)}`)); });
      child.stderr.on('data', data => {
        stderr = (stderr + data.toString()).slice(-8000);
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
        clearTimeout(request.timer); pending.delete(message.id);
        if (message.error) request.reject(new Error(message.error.message));
        else request.resolve(message.result ?? {});
      } else if (message.method === 'Runtime.exceptionThrown') {
        errors.push(message.params.exceptionDetails.exception?.description ?? message.params.exceptionDetails.text);
      } else if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') {
        errors.push(message.params.args.map(arg => arg.value ?? arg.description).join(' '));
      } else if (message.method === 'Network.requestWillBeSent'
        && message.params.request.url.startsWith(`${target.origin}/api/`)) {
        const request = { request_id: message.params.requestId,
          url: message.params.request.url, method: message.params.request.method };
        if (message.params.request.postData) {
          try {
            const body = JSON.parse(message.params.request.postData);
            request.identity = { player_id: body.player_id, run_id: body.run_id, nickname: body.nickname };
          } catch { /* Non-JSON requests are still recorded by URL and status. */ }
        }
        requests.set(message.params.requestId, request);
        apiRequests.push(request);
      } else if (message.method === 'Network.responseReceived') {
        const request = requests.get(message.params.requestId);
        if (request) request.status = message.params.response.status;
      } else if (message.method === 'Network.loadingFailed') {
        const request = requests.get(message.params.requestId);
        if (request) request.error = message.params.errorText;
      }
    });
    await new Promise((resolve, reject) => {
      socket.addEventListener('open', resolve, { once: true });
      socket.addEventListener('error', reject, { once: true });
    });
    const version = await send('Browser.getVersion', {}, null);
    const { targetId } = await send('Target.createTarget', { url: 'about:blank' }, null);
    ({ sessionId } = await send('Target.attachToTarget', { targetId, flatten: true }, null));
    await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable');
    await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    await send('Page.bringToFront');
    const evaluate = async expression => {
      const response = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
      if (response.exceptionDetails) throw new Error(response.exceptionDetails.exception?.description ?? response.exceptionDetails.text);
      return response.result.value;
    };
    return { send, evaluate, version, close,
      get process() { return { pid: child.pid, executable: child.spawnfile,
        arguments: launchArguments, exit_code: child.exitCode, stderr_tail: stderr.slice(-4000) }; },
      until: (expression, timeout) => waitFor(() => evaluate(expression), timeout, expression) };
  } catch (error) { await close(); throw error; }
}

async function captureFailure(client, result) {
  result.browser_process = client.process;
  try {
    result.failure_snapshot = await client.evaluate(`(() => {
      const read = key => {
        try { return JSON.parse(localStorage.getItem('jumpbugi.web.v1.' + key) || 'null'); }
        catch (error) { return { read_error: error.message }; }
      };
      const brief = rows => Array.isArray(rows) ? rows.map(row => ({
        run_id: row.run_id, player_id: row.player_id, score: row.score,
        survival_time: row.survival_time, played_at: row.played_at,
      })) : rows;
      const game = window.__JUMPBUGI__;
      return { url: location.href, ready_state: document.readyState,
        phase: game?.phase, server: game?.server,
        engine: game?.engine ? { score: game.engine.score, elapsed: game.engine.elapsed,
          gameOver: game.engine.gameOver, paused: game.engine.paused } : null,
        identity: read('identity'), local_runs: brief(read('results')),
        pending_runs: brief(read('pending')),
        ranking_mode: document.querySelector('#ranking-mode')?.textContent,
        ranking_note: document.querySelector('#ranking-note')?.textContent };
    })()`);
  } catch (error) { result.failure_snapshot_error = error.message; }
  try {
    const screenshot = await client.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
    const filename = path.join(output, `${result.name.toLowerCase()}-failure.png`);
    await writeFile(filename, Buffer.from(screenshot.data, 'base64'));
    result.failure_screenshot = filename;
  } catch (error) { result.failure_screenshot_error = error.message; }
  if (result.player_id) {
    try {
      result.failure_api_runs = await api(`runs?player_id=${encodeURIComponent(result.player_id)}&limit=50`);
    } catch (error) { result.failure_api_runs_error = error.message; }
  }
}

async function click(client, selector, touch = false) {
  const point = await client.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element) throw new Error('Missing control: ' + ${JSON.stringify(selector)});
    element.scrollIntoView({ block: 'center', inline: 'nearest' });
    const r = element.getBoundingClientRect(); return { x:r.x+r.width/2, y:r.y+r.height/2 };
  })()`);
  if (touch) {
    await client.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ ...point, radiusX: 1, radiusY: 1, force: 1, id: 0 }] });
    await client.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    return;
  }
  await client.send('Input.dispatchMouseEvent', { type: 'mousePressed', ...point, button: 'left', buttons: 1, clickCount: 1 });
  await client.send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...point, button: 'left', buttons: 0, clickCount: 1 });
}

async function typeNickname(client, value, touch = false) {
  await click(client, '#nickname-input', touch);
  assert.equal(await client.evaluate(`document.activeElement.id`), 'nickname-input', 'Nickname input did not receive focus');
  await client.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, modifiers: 2 });
  await client.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, modifiers: 2 });
  await client.send('Input.insertText', { text: value });
}

async function layout(client) {
  return client.evaluate(`(() => {
    const board = document.querySelector('.ranking-card');
    window.__qaNicknameBoard ??= board;
    const r = board.getBoundingClientRect();
    const input = document.querySelector('#nickname-input');
    const editorVisible = !document.querySelector('#nickname-form').hidden;
    const ir = input.getBoundingClientRect();
    return { top:r.top+scrollY, left:r.left+scrollX, width:r.width,
      same_node:board === window.__qaNicknameBoard,
      bounded:document.documentElement.scrollWidth <= innerWidth+1 && board.scrollWidth <= board.clientWidth+1,
      editor_bounded:!editorVisible || ir.left >= r.left-1 && ir.right <= r.right+1 };
  })()`);
}

async function assertNicknameLayout(client, expected, description) {
  const actual = await layout(client);
  assert.equal(actual.same_node, true, `${description}: ranking DOM was replaced`);
  assert.equal(actual.bounded, true, `${description}: nickname UI overflows the page or ranking card`);
  assert.equal(actual.editor_bounded, true, `${description}: nickname input exceeds the card`);
  assert.ok(Math.abs(actual.top - expected.top) <= 1 && Math.abs(actual.left - expected.left) <= 1,
    `${description}: nickname edit moved the ranking board`);
  return actual;
}

async function renameInUI(client, nickname, baseline, label, touch = false) {
  await click(client, '#nickname-edit-button', touch);
  await client.until(`document.querySelector('#nickname-form').hidden === false`);
  await assertNicknameLayout(client, baseline, `${label} open`);
  await typeNickname(client, nickname, touch);
  await click(client, '#nickname-save-button', touch);
  const trimmed = nickname.trim();
  await client.until(`document.querySelector('#nickname-form').hidden === true
    && JSON.parse(localStorage.getItem('jumpbugi.web.v1.identity')).nickname === ${JSON.stringify(trimmed)}
    && window.__JUMPBUGI__.server.registeredNickname === ${JSON.stringify(trimmed)}
    && window.__JUMPBUGI__.server.state === 'saved'`);
  assert.equal(await client.evaluate(`document.querySelector('#nickname').textContent`), trimmed);
  return assertNicknameLayout(client, baseline, `${label} saved`);
}

async function pressKey(client, key, code, windowsVirtualKeyCode) {
  const text = key === 'Enter' ? '\r' : key === ' ' ? ' ' : undefined;
  await client.send('Input.dispatchKeyEvent', { type: 'keyDown', key, code, windowsVirtualKeyCode,
    ...(text === undefined ? {} : { text, unmodifiedText: text }) });
  await client.send('Input.dispatchKeyEvent', { type: 'keyUp', key, code, windowsVirtualKeyCode });
}

async function verifyNicknameBeforeStart(client, result, identity) {
  result.stage = 'ready nickname editing, keyboard isolation and IME';
  await client.until(`window.__JUMPBUGI__.server.state === 'saved'`);
  const baseline = await layout(client);
  await click(client, '#nickname-edit-button');
  assert.equal(await client.evaluate(`document.querySelector('#nickname-input').disabled || document.querySelector('#nickname-input').readOnly`), false);
  await typeNickname(client, 'ReadyBugi');
  await pressKey(client, ' ', 'Space', 32);
  assert.equal(await client.evaluate(`window.__JUMPBUGI__.phase`), 'ready', 'Typing Space started the game');
  for (const composition of [{ isComposing: true }, { keyCode: 229 }]) {
    assert.equal(await client.evaluate(`document.querySelector('#nickname-input').dispatchEvent(new KeyboardEvent('keydown', {
      key:'Enter', code:'Enter', bubbles:true, cancelable:true, ...${JSON.stringify(composition)}
    }))`), false, 'IME Enter must prevent implicit nickname submission');
    assert.equal(await client.evaluate(`document.querySelector('#nickname-form').hidden`), false);
  }
  await client.evaluate(`document.activeElement.blur()`);
  await pressKey(client, 'a', 'KeyA', 65);
  await pressKey(client, ' ', 'Space', 32);
  assert.equal(await client.evaluate(`window.__JUMPBUGI__.phase`), 'ready', 'A key outside the open editor started the game');
  await click(client, '#nickname-input');
  await pressKey(client, 'Escape', 'Escape', 27);
  assert.equal(await client.evaluate(`document.querySelector('#nickname-form').hidden`), true);
  assert.deepEqual(await client.evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.identity'))`), identity);
  await click(client, '#nickname-edit-button');
  await typeNickname(client, 'ReadyBugi');
  await pressKey(client, 'Enter', 'Enter', 13);
  await client.until(`document.querySelector('#nickname-form').hidden && window.__JUMPBUGI__.server.state === 'saved'
    && window.__JUMPBUGI__.server.registeredNickname === 'ReadyBugi'`);
  assert.equal(await client.evaluate(`window.__JUMPBUGI__.phase`), 'ready', 'Saving with Enter also started the game');
  assert.deepEqual(await client.evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.identity'))`), { ...identity, nickname: 'ReadyBugi' });
  await renameInUI(client, identity.nickname, baseline, 'restore ready nickname');
  await click(client, '#nickname-edit-button');
  await typeNickname(client, 'UnsavedBugi');
  result.checks.push('Ready input accepts keyboard text; Space, unfocused editor keys and IME Enter cannot start or submit; Escape cancels and Enter saves the same UUID to the server');
}

async function verifyNicknameBlocked(client, result, expectedPhase) {
  const state = await client.evaluate(`(() => {
    const identity = localStorage.getItem('jumpbugi.web.v1.identity');
    const paused = window.__JUMPBUGI__.engine.paused;
    const edit = document.querySelector('#nickname-edit-button');
    edit.click();
    edit.dispatchEvent(new MouseEvent('click', { bubbles:true }));
    document.querySelector('#nickname-input').value = 'BlockedBugi';
    document.querySelector('#nickname-form').dispatchEvent(new Event('submit', { bubbles:true, cancelable:true }));
    return { phase:window.__JUMPBUGI__.phase, hidden:document.querySelector('#nickname-form').hidden,
      disabled:['nickname-edit-button','nickname-input','nickname-save-button','nickname-cancel-button']
        .every(id => document.getElementById(id).disabled),
      identity_unchanged:localStorage.getItem('jumpbugi.web.v1.identity') === identity,
      paused_unchanged:window.__JUMPBUGI__.engine.paused === paused };
  })()`);
  assert.deepEqual(state, { phase:expectedPhase, hidden:true, disabled:true, identity_unchanged:true, paused_unchanged:true });
  result.checks.push(`${expectedPhase} (${await client.evaluate(`window.__JUMPBUGI__.engine.paused ? 'paused' : 'active'`)}): nickname controls disabled; forced click/submit cannot edit or save`);
}

async function verifyNickname(client, result, identity, runs, route) {
  result.stage = 'nickname UI validation and desktop rename';
  const { evaluate, until, send } = client;
  const originalBest = await evaluate(`document.querySelector('#ranking-best').textContent`);
  const before = await layout(client);
  result.original_identity = identity;
  result.original_best_display = originalBest;
  result.expected_current_nickname = sharedNickname;
  await click(client, '#nickname-edit-button');
  await until(`document.querySelector('#nickname-form').hidden === false`);
  const requestsBeforeInvalid = result.api_requests.filter(request => request.method === 'POST' && request.url.includes('/api/players')).length;
  for (const invalid of ['   ', 'a\u200bb']) {
    await typeNickname(client, invalid);
    await click(client, '#nickname-save-button');
    await until(`document.querySelector('#nickname-error').textContent.trim().length > 0`);
    assert.equal(await evaluate(`document.querySelector('#nickname-form').hidden`), false);
    assert.deepEqual(await evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.identity'))`), identity);
    await assertNicknameLayout(client, before, 'desktop invalid nickname');
  }
  assert.equal(result.api_requests.filter(request => request.method === 'POST' && request.url.includes('/api/players')).length, requestsBeforeInvalid,
    'Invalid nickname must not make a server rename request');
  await click(client, '#nickname-cancel-button');
  result.nickname_desktop_layout = await renameInUI(client, `  ${sharedNickname}  `, before, 'desktop rename');
  const afterRename = await evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.identity'))`);
  const requestsBeforeCancel = result.api_requests.filter(request => request.method === 'POST' && request.url.includes('/api/players')).length;
  await click(client, '#nickname-edit-button');
  await typeNickname(client, '취소검증');
  await click(client, '#nickname-cancel-button');
  assert.equal(await evaluate(`document.querySelector('#nickname-form').hidden`), true);
  assert.deepEqual(await evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.identity'))`), afterRename);
  assert.equal(result.api_requests.filter(request => request.method === 'POST' && request.url.includes('/api/players')).length, requestsBeforeCancel,
    'Canceling an unsaved nickname must not request a server rename');
  await assertNicknameLayout(client, before, 'desktop canceled rename');
  result.stage = 'nickname markup is rendered as literal text';
  const tagNickname = '<b>부기</b>';
  await renameInUI(client, tagNickname, before, 'literal-tag nickname');
  const markup = await evaluate(`({
    text:document.querySelector('#nickname').textContent,
    inserted_markup:document.querySelectorAll('#nickname *, #ranking-list strong b').length
  })`);
  assert.equal(markup.text, tagNickname, 'Visible-tag nickname must remain literal text');
  assert.equal(markup.inserted_markup, 0, 'Nickname introduced HTML elements');
  result.nickname_literal_text = { input:tagNickname, ...markup };
  await renameInUI(client, sharedNickname, before, 'restore name after literal-tag check');
  result.checks.push('Canceled nickname edits preserve identity without a request; visible HTML-tag text stays literal and introduces no nickname or ranking markup');
  result.stage = 'mobile nickname editor and fixed ranking layout';
  await send('Emulation.setDeviceMetricsOverride', { width:390, height:844, deviceScaleFactor:1, mobile:true });
  await send('Emulation.setTouchEmulationEnabled', { enabled:true });
  await delay(100);
  const mobile = await layout(client);
  await renameInUI(client, sharedNickname.repeat(3), mobile, 'mobile 12-character rename', true);
  result.nickname_mobile_layout = await renameInUI(client, sharedNickname, mobile, 'mobile final rename', true);
  const beforeTouchCancel = await evaluate(`localStorage.getItem('jumpbugi.web.v1.identity')`);
  await click(client, '#nickname-edit-button', true);
  await typeNickname(client, 'TouchCancel', true);
  await click(client, '#nickname-cancel-button', true);
  assert.equal(await evaluate(`document.querySelector('#nickname-form').hidden`), true);
  assert.equal(await evaluate(`localStorage.getItem('jumpbugi.web.v1.identity')`), beforeTouchCancel);
  result.checks.push('Mobile touch events open, focus, save and cancel the nickname editor without changing the UUID or historical runs');
  await send('Emulation.setTouchEmulationEnabled', { enabled:false });
  await send('Emulation.setDeviceMetricsOverride', { width:1280, height:900, deviceScaleFactor:1, mobile:false });
  const current = await evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.identity'))`);
  assert.deepEqual(current, { ...identity, nickname:sharedNickname });
  assert.deepEqual(await evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.results'))`), runs);
  assert.equal(await evaluate(`document.querySelector('#ranking-best').textContent`), originalBest);
  const historic = (await api(route)).body.items.find(item => item.run_id === runs[0].run_id);
  assert.equal(historic.nickname, identity.nickname, 'Rename must preserve the historical run nickname');
  assert.equal((await api('runs', runs[0])).status, 200, 'Retrying the old run must remain idempotent after rename');
  result.current_identity = current;
  result.server_state_after_rename = await evaluate(`window.__JUMPBUGI__.server`);
  result.current_best_display = await evaluate(`document.querySelector('#ranking-best').textContent`);
  result.historic_run_nickname = historic.nickname;
  result.local_runs_unchanged = true;
  result.checks.push('Desktop rejects blank/control-format nicknames without a request; PC/mobile rename trims input and preserves board position, UUID, exact local runs and best score');
}

try {
  const health = await api('health');
  assert.equal(health.status, 200); assert.equal(health.body.database, 'ok');
  report.checks.push('API health confirms a database connection');
  for (const browser of browsers) {
    const executable = browser.candidates.filter(Boolean).find(candidate => existsSync(candidate));
    assert.ok(executable, `${browser.name} was not found; set ${browser.name.toUpperCase()}_PATH`);
    assert.equal(path.basename(executable).toLowerCase(), browser.name === 'Chrome' ? 'chrome.exe' : 'msedge.exe', 'Use the named browser executable');
    const result = { name: browser.name, executable, profile: path.join(output, browser.name.toLowerCase()),
      stage: 'launching fresh browser profile', checks: [], errors: [], api_requests: [] };
    report.browsers.push(result);
    const client = await connectBrowser(executable, result.profile, result.errors, result.api_requests);
    try {
      result.version = client.version;
      result.browser_process = client.process;
      const { evaluate, until, send } = client;
      result.stage = 'loading game and browser identity';
      await send('Page.navigate', { url: target.href });
      await until(`window.__JUMPBUGI__?.phase === 'ready'`, 30000);
      const identity = await evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.identity'))`);
      assert.ok(identity?.player_id);
      result.player_id = identity.player_id;
      result.identity = identity;
      await verifyNicknameBeforeStart(client, result, identity);
      assert.deepEqual(await evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.results') || '[]')`), []);
      assert.equal(await evaluate(`window.__JUMPBUGI__.server?.enabled`), true, 'Server mode is not enabled');
      result.stage = 'actual start click and natural collision';
      const point = await evaluate(`(() => {const r=document.querySelector('#start-button').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);
      await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...point, button: 'left', buttons: 1, clickCount: 1 });
      await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...point, button: 'left', buttons: 0, clickCount: 1 });
      await until(`window.__JUMPBUGI__.phase === 'transition'`);
      await verifyNicknameBlocked(client, result, 'transition');
      await until(`window.__JUMPBUGI__.phase === 'playing'`);
      await verifyNicknameBlocked(client, result, 'playing');
      await pressKey(client, 'Escape', 'Escape', 27);
      assert.equal(await evaluate(`window.__JUMPBUGI__.engine.paused`), true);
      await verifyNicknameBlocked(client, result, 'playing');
      await pressKey(client, 'Escape', 'Escape', 27);
      await until(`window.__JUMPBUGI__.phase === 'gameover'`, 20000);
      const runs = await evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.results') || '[]')`);
      assert.equal(runs.length, 1, 'Natural collision must record exactly one run');
      const run = runs[0];
      result.run_id = run.run_id;
      result.submitted_run = run;
      result.sql_lookup = {
        query: 'SELECT run_id::text, player_id::text, score, survival_time, game_version, device_type, received_at FROM runs WHERE run_id = %s::uuid AND player_id = %s::uuid',
        parameters: [run.run_id, identity.player_id],
      };
      assert.equal(run.player_id, identity.player_id);
      assert.equal(run.score, await evaluate(`window.__JUMPBUGI__.engine.score`));
      const route = `runs?player_id=${encodeURIComponent(identity.player_id)}&limit=50`;
      result.stage = 'waiting for the exact natural-run UUID in the database API';
      const stored = await waitFor(async () => {
        const response = await api(route);
        result.last_api_runs = response;
        assert.equal(response.status, 200);
        return response.body.items.find(item => item.run_id === run.run_id);
      }, 20000, `${browser.name} run ${run.run_id} through ${route}`);
      assert.equal(stored.score, run.score); assert.equal(stored.survival_time, run.survival_time);
      assert.equal(stored.player_id, identity.player_id); assert.ok(stored.received_at);
      await until(`window.__JUMPBUGI__.server.state === 'saved' && window.__JUMPBUGI__.server.pendingCount === 0`);
      assert.equal(await evaluate(`Array.isArray(window.__JUMPBUGI__.server.leaderboard)`), true);
      result.stored_run = stored;
      result.server_state = await evaluate(`window.__JUMPBUGI__.server`);
      result.checks.push('Actual start click and natural collision submit one local run to the API; server acknowledges it and refreshes ranking');
      result.stage = 'idempotent, conflicting and invalid API submissions';
      const before = (await api(route)).body.items;
      assert.equal((await api('runs', run)).status, 200, 'Identical retry must be idempotent');
      assert.equal((await api('runs', { ...run, score: run.score + 1 })).status, 409, 'Conflicting retry must be rejected');
      assert.equal((await api('runs', { ...run, score: -1 })).status, 422, 'Negative score must fail validation');
      const after = (await api(route)).body.items;
      assert.equal(after.length, before.length); assert.equal(after.filter(item => item.run_id === run.run_id).length, 1);
      assert.equal(after.find(item => item.run_id === run.run_id).score, run.score);
      result.checks.push('Identical submission returns 200 without duplication; changed retry returns 409; invalid score returns 422 without changing the stored run');
      await verifyNickname(client, result, identity, runs, route);
      result.stage = 'reload retries a historical-name payload without reverting the current nickname';
      const requestsBeforeReload = result.api_requests.length;
      // Re-create a lost-ack retry in this disposable QA profile only. The exact
      // already-stored historical payload must keep its original run_id/name.
      await evaluate(`localStorage.setItem('jumpbugi.web.v1.pending', JSON.stringify(${JSON.stringify(runs)}))`);
      result.restored_queue_test = { seeded_acknowledged_retry:true, run_id:run.run_id,
        historical_nickname:run.nickname, current_nickname:sharedNickname };
      await send('Page.navigate', { url: target.href });
      await until(`window.__JUMPBUGI__?.phase === 'ready'`, 30000);
      await until(`window.__JUMPBUGI__.server.state === 'saved'
        && window.__JUMPBUGI__.server.pendingCount === 0
        && window.__JUMPBUGI__.server.registeredNickname === ${JSON.stringify(sharedNickname)}`);
      assert.deepEqual(await evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.identity'))`), result.current_identity);
      assert.equal(await evaluate(`document.querySelector('#nickname').textContent`), sharedNickname);
      assert.equal(await evaluate(`document.querySelector('#ranking-best').textContent`), result.original_best_display);
      assert.deepEqual(await evaluate(`JSON.parse(localStorage.getItem('jumpbugi.web.v1.results'))`), runs);
      const reloaded = (await api(route)).body.items.filter(item => item.run_id === run.run_id);
      assert.equal(reloaded.length, 1); assert.equal(reloaded[0].nickname, identity.nickname);
      const retry = result.api_requests.slice(requestsBeforeReload).find(request => request.method === 'POST'
        && request.url.endsWith('/api/runs') && request.identity?.run_id === run.run_id);
      assert.ok(retry, 'Reload must actually retry the restored historical-name payload');
      assert.equal(retry.status, 200); assert.equal(retry.identity.nickname, identity.nickname);
      const registration = result.api_requests.slice(requestsBeforeReload).find(request => request.method === 'POST'
        && request.url.endsWith('/api/players'));
      assert.equal(registration?.identity?.nickname, sharedNickname, 'Restored queue must register the current identity');
      result.restored_queue_test.pending_after_retry = 0;
      result.restored_queue_test.request = retry;
      result.expected_current_nickname = sharedNickname;
      result.checks.push('Same-profile reload preserves the edited nickname and retries the exact old-name run without duplication or reverting the current player name');
      assert.deepEqual(result.errors, [], 'Unexpected browser runtime or console errors');
      result.stage = 'passed';
    } catch (error) {
      result.failure = error.stack ?? String(error);
      await captureFailure(client, result);
      throw error;
    } finally { await client.close(); }
  }
  assert.equal(report.browsers.length, 2);
  assert.notEqual(report.browsers[0].player_id, report.browsers[1].player_id, 'Chrome and Edge identities must be independent');
  assert.notEqual(report.browsers[0].run_id, report.browsers[1].run_id);
  assert.equal(report.browsers[0].current_identity.nickname, sharedNickname);
  assert.equal(report.browsers[1].current_identity.nickname, sharedNickname);
  const ranking = await api('leaderboard?limit=100');
  assert.equal(ranking.status, 200); assert.ok(Array.isArray(ranking.body.items));
  report.ranking = report.browsers.map(browser => {
    const entry = ranking.body.items.find(item => item.player_id === browser.player_id);
    if (entry) assert.equal(entry.nickname, sharedNickname, 'Shared ranking must use the current player name');
    return { player_id:browser.player_id, included:Boolean(entry), nickname:entry?.nickname };
  });
  if (ranking.body.items.length < 100) assert.ok(report.ranking.every(item => item.included), 'Global ranking must include both players when fewer than 100 entries exist');
  report.checks.push('Real Chrome and real Edge use different executables and isolated player/result storage; both runs exist in the server API');
  report.checks.push('Chrome and Edge share one edited display nickname but retain distinct UUIDs; ranking uses current names while historical runs keep their original names');
  report.passed = true;
} catch (error) {
  report.errors.push(error.stack ?? String(error));
  process.exitCode = 1;
} finally {
  report.finished_at = new Date().toISOString();
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ...report, report_path: path.join(output, 'report.json') }, null, 2));
}
