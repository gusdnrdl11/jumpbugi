import test from 'node:test';
import assert from 'node:assert/strict';
import { isLocalServerMode, LocalServerSync, MAX_PENDING_RUNS, PENDING_KEY } from '../src/api.js';

class MemoryStorage {
  constructor() { this.data = new Map(); }
  getItem(key) { return this.data.get(key) ?? null; }
  setItem(key, value) { this.data.set(key, String(value)); }
}

const uuid = number => `00000000-0000-4000-8000-${String(number).padStart(12, '0')}`;
const identity = { player_id: uuid(1), nickname: 'JumpBugi_001' };
const run = (number = 2) => ({ ...identity, run_id: uuid(number), score: 35,
  survival_time: 15, game_version: '0.1.0', played_at: '2026-11-25T01:00:00.000Z',
  death_obstacle: 'sj.png', max_speed: 1, device_type: 'desktop' });
const leader = { ...identity, score: 35, survival_time: 15 };
const response = (value, status = 200) => ({ ok: status >= 200 && status < 300,
  status, json: async () => structuredClone(value) });

function fakeServer(handler) {
  const calls = [];
  const fetch = async (path, options) => {
    const body = options.body === undefined ? undefined : JSON.parse(options.body);
    calls.push({ path, options, body });
    if (handler) {
      const result = await handler(path, options, body, calls);
      if (result !== undefined) return result;
    }
    if (path === '/api/players') return response(body, 201);
    if (path === '/api/runs') return response(body, 201);
    if (path === '/api/leaderboard?limit=5') return response({ items: [leader] });
    throw new Error(`Unexpected request: ${path}`);
  };
  return { calls, fetch };
}

function client(server, storage = new MemoryStorage(), options = {}) {
  return new LocalServerSync({ enabled: true, identity, storage, fetch: server.fetch, ...options });
}

test('API mode requires explicit opt-in on a loopback HTTP origin', () => {
  for (const host of ['localhost', '127.0.0.1', '[::1]']) {
    assert.equal(isLocalServerMode(new URL(`http://${host}:8000/?server=1`)), true);
    assert.equal(isLocalServerMode(new URL(`http://${host}:8000/`)), false);
  }
  for (const url of ['https://example.github.io/?server=1', 'http://127.0.0.1.example.com/?server=1',
    'http://192.168.0.2/?server=1', 'file:///game.html?server=1', 'http://localhost/?server=0']) {
    assert.equal(isLocalServerMode(new URL(url)), false);
  }
});

test('local-only mode never accesses the pending store or performs API requests', async () => {
  let calls = 0;
  const sync = new LocalServerSync({ enabled: false, identity,
    storage: { getItem() { throw new Error('must not read'); }, setItem() { calls++; } },
    fetch: async () => { calls++; throw new Error('must not request'); } });
  await sync.submit(run());
  await sync.retry();
  await sync.syncIdentity();
  assert.equal(calls, 0);
  assert.equal(sync.snapshot.pendingCount, 0);
  assert.equal(sync.snapshot.enabled, false);
});

test('browser-style fetch keeps its required global receiver through registration and saving', async () => {
  const server = fakeServer();
  const sync = client({ fetch: function (path, options) {
    assert.equal(this, globalThis, 'native browser fetch must receive its global object');
    return server.fetch(path, options);
  } });
  await sync.submit(run());
  assert.equal(sync.snapshot.state, 'saved');
  assert.equal(sync.snapshot.pendingCount, 0);
  assert.equal(sync.snapshot.lastSavedRunId, run().run_id);
  assert.deepEqual(server.calls.map(call => call.path), ['/api/players', '/api/runs', '/api/leaderboard?limit=5']);
});

test('a new result is persisted before registration and saved without changing its payload', async () => {
  const storage = new MemoryStorage();
  const server = fakeServer((path) => {
    if (path === '/api/players') assert.deepEqual(JSON.parse(storage.getItem(PENDING_KEY)), [run()]);
  });
  const sync = client(server, storage);
  await sync.submit(run());
  assert.deepEqual(server.calls.map(call => call.path), ['/api/players', '/api/runs', '/api/leaderboard?limit=5']);
  assert.deepEqual(server.calls[1].body, run());
  assert.equal(server.calls[1].options.credentials, 'omit');
  assert.equal(server.calls[1].options.redirect, 'error');
  assert.equal(sync.snapshot.state, 'saved');
  assert.equal(sync.snapshot.pendingCount, 0);
  assert.equal(sync.snapshot.lastSavedRunId, run().run_id);
  assert.deepEqual(sync.snapshot.leaderboard, [leader]);
  assert.deepEqual(JSON.parse(storage.getItem(PENDING_KEY)), []);
});

test('starting server mode does not upload older browser-local history', async () => {
  const storage = new MemoryStorage();
  storage.setItem('jumpbugi.web.v1.results', JSON.stringify([run()]));
  const server = fakeServer();
  await client(server, storage).retry();
  assert.deepEqual(server.calls.map(call => call.path), ['/api/players', '/api/leaderboard?limit=5']);
  assert.deepEqual(JSON.parse(storage.getItem('jumpbugi.web.v1.results')), [run()]);
});

test('a lost POST response is retried after reload with the same run_id and accepts an idempotent 200', async () => {
  const storage = new MemoryStorage();
  let attempts = 0;
  const posted = [];
  const server = fakeServer((path, options, body) => {
    if (path === '/api/runs') {
      posted.push(body);
      if (++attempts === 1) throw new Error('connection lost after server saved');
      return response(body, 200);
    }
  });
  const first = client(server, storage);
  await first.submit(run());
  assert.equal(first.snapshot.state, 'error');
  assert.equal(first.snapshot.pendingCount, 1);
  assert.equal(first.snapshot.leaderboard, null);
  const reloaded = client(server, storage);
  assert.equal(reloaded.snapshot.pendingCount, 1);
  await reloaded.retry();
  assert.deepEqual(posted, [run(), run()]);
  assert.equal(reloaded.snapshot.state, 'saved');
  assert.equal(reloaded.snapshot.pendingCount, 0);
});

test('registration failure keeps every result pending and leaves local data intact', async () => {
  const storage = new MemoryStorage();
  storage.setItem('jumpbugi.web.v1.results', JSON.stringify([run()]));
  const server = fakeServer(path => path === '/api/players' ? response({}, 503) : undefined);
  const sync = client(server, storage);
  await sync.submit(run());
  assert.equal(sync.snapshot.pendingCount, 1);
  assert.equal(sync.snapshot.state, 'error');
  assert.match(sync.snapshot.error, /503/);
  assert.equal(server.calls.length, 1);
  assert.deepEqual(JSON.parse(storage.getItem('jumpbugi.web.v1.results')), [run()]);
});

test('conflicting or unacknowledged runs remain queued rather than being silently discarded', async () => {
  for (const result of [response({}, 409), response({ ...run(), run_id: uuid(99) })]) {
    const server = fakeServer(path => path === '/api/runs' ? result : undefined);
    const sync = client(server);
    await sync.submit(run());
    assert.equal(sync.snapshot.state, 'error');
    assert.equal(sync.snapshot.pendingCount, 1);
    assert.equal(sync.snapshot.lastSavedRunId, null);
  }
});

test('a result arriving during leaderboard refresh is drained by the same sync without a stale board', async () => {
  let release;
  let entered;
  const boardStarted = new Promise(resolve => { entered = resolve; });
  const boardGate = new Promise(resolve => { release = resolve; });
  let boardCalls = 0;
  const server = fakeServer(async path => {
    if (path === '/api/leaderboard?limit=5' && ++boardCalls === 1) {
      entered();
      await boardGate;
    }
  });
  const sync = client(server);
  const saving = sync.submit(run(2));
  await boardStarted;
  const second = sync.submit(run(3));
  release();
  await Promise.all([saving, second]);
  assert.deepEqual(server.calls.filter(call => call.path === '/api/runs').map(call => call.body.run_id), [uuid(2), uuid(3)]);
  assert.equal(sync.snapshot.pendingCount, 0);
  assert.equal(sync.snapshot.lastSavedRunId, uuid(3));
  assert.equal(boardCalls, 2);
});

test('pending queues are bounded without evicting older unsent results', async () => {
  const storage = new MemoryStorage();
  const pending = Array.from({ length: MAX_PENDING_RUNS }, (_, index) => run(index + 2));
  storage.setItem(PENDING_KEY, JSON.stringify(pending));
  const server = fakeServer();
  const sync = client(server, storage);
  await sync.submit(run(100));
  assert.equal(sync.snapshot.pendingCount, MAX_PENDING_RUNS);
  assert.equal(sync.snapshot.localOnlyCount, 1);
  assert.equal(sync.snapshot.state, 'error');
  assert.equal(server.calls.length, 0);
  assert.deepEqual(JSON.parse(storage.getItem(PENDING_KEY)), pending);
});

test('storage denial keeps a usable session queue and clearly reports that it is not durable', async () => {
  const storage = { getItem() { throw new Error('denied'); }, setItem() { throw new Error('denied'); } };
  let offline = true;
  const server = fakeServer(() => { if (offline) throw new Error('offline'); });
  const sync = client(server, storage);
  await sync.submit(run());
  assert.equal(sync.snapshot.persistent, false);
  assert.equal(sync.snapshot.pendingCount, 1);
  offline = false;
  await sync.retry();
  assert.equal(sync.snapshot.state, 'saved');
  assert.equal(sync.snapshot.pendingCount, 0);
});

test('an invalid shared leaderboard falls back cleanly after an acknowledged save', async () => {
  const server = fakeServer(path => path === '/api/leaderboard?limit=5'
    ? response({ items: [{ nickname: 'broken', score: '35', survival_time: 15 }] }) : undefined);
  const sync = client(server);
  await sync.submit(run());
  assert.equal(sync.snapshot.state, 'error');
  assert.equal(sync.snapshot.leaderboard, null);
  assert.equal(sync.snapshot.pendingCount, 0);
  assert.equal(sync.snapshot.lastSavedRunId, run().run_id);
});

test('pending results stay scoped to the browser identity that created them', async () => {
  const storage = new MemoryStorage();
  storage.setItem(PENDING_KEY, JSON.stringify([run()]));
  const server = fakeServer();
  const sync = client(server, storage, { identity: { player_id: uuid(9), nickname: 'OtherBrowser' } });
  await sync.retry();
  assert.equal(sync.snapshot.pendingCount, 0);
  assert.equal(server.calls.some(call => call.path === '/api/runs'), false);
});

test('a nickname change registers the current identity and refreshes the board without creating a run', async () => {
  const current = { ...identity, nickname: '검증부기' };
  let registered;
  const server = fakeServer((path, options, body) => {
    if (path === '/api/players') registered = { ...body };
    if (path === '/api/leaderboard?limit=5') return response({ items: [{ ...leader, nickname: registered.nickname }] });
  });
  const sync = client(server, new MemoryStorage(), { identity: current });
  await sync.syncIdentity();
  assert.equal(sync.identity, current);
  assert.equal(sync.snapshot.registeredNickname, '검증부기');
  assert.equal(sync.snapshot.nicknamePending, false);
  assert.equal(sync.snapshot.leaderboard[0].nickname, '검증부기');
  assert.deepEqual(server.calls.map(call => call.path), ['/api/players', '/api/leaderboard?limit=5']);
});

test('renaming repeatedly during registration eventually acknowledges only the latest name', async () => {
  let entered;
  let release;
  const started = new Promise(resolve => { entered = resolve; });
  const gate = new Promise(resolve => { release = resolve; });
  const current = { ...identity };
  let registered;
  let registrations = 0;
  const server = fakeServer(async (path, options, body) => {
    if (path === '/api/players') {
      if (++registrations === 1) { entered(); await gate; }
      registered = { ...body };
    }
    if (path === '/api/leaderboard?limit=5') return response({ items: [{ ...leader, nickname: registered.nickname }] });
  });
  const sync = client(server, new MemoryStorage(), { identity: current });
  const initial = sync.retry();
  await started;
  current.nickname = '중간부기';
  const middle = sync.syncIdentity();
  current.nickname = '최종부기';
  const latest = sync.syncIdentity();
  release();
  await Promise.all([initial, middle, latest]);
  assert.deepEqual(server.calls.filter(call => call.path === '/api/players').map(call => call.body.nickname), [identity.nickname, '최종부기']);
  assert.equal(current.nickname, '최종부기', 'an older server response must not replace the local name');
  assert.equal(sync.snapshot.registeredNickname, '최종부기');
  assert.equal(sync.snapshot.leaderboard[0].nickname, '최종부기');
  assert.equal(sync.snapshot.nicknamePending, false);
});

test('renaming while a board request is pending discards that stale board and refreshes the latest name', async () => {
  let entered;
  let release;
  const started = new Promise(resolve => { entered = resolve; });
  const gate = new Promise(resolve => { release = resolve; });
  const current = { ...identity };
  let registered;
  let boardCalls = 0;
  const server = fakeServer(async (path, options, body) => {
    if (path === '/api/players') registered = { ...body };
    if (path === '/api/leaderboard?limit=5') {
      const nickname = registered.nickname;
      if (++boardCalls === 1) { entered(); await gate; }
      return response({ items: [{ ...leader, nickname }] });
    }
  });
  const sync = client(server, new MemoryStorage(), { identity: current });
  const initial = sync.retry();
  await started;
  current.nickname = '변경부기';
  const renamed = sync.syncIdentity();
  release();
  await Promise.all([initial, renamed]);
  assert.equal(boardCalls, 2);
  assert.equal(sync.snapshot.state, 'saved');
  assert.equal(sync.snapshot.registeredNickname, '변경부기');
  assert.equal(sync.snapshot.leaderboard[0].nickname, '변경부기');
});

test('pending runs keep their historical nickname while registration uses the current name', async () => {
  const storage = new MemoryStorage();
  storage.setItem(PENDING_KEY, JSON.stringify([run()]));
  const current = { ...identity, nickname: '현재부기' };
  const server = fakeServer();
  const sync = client(server, storage, { identity: current });
  await sync.syncIdentity();
  assert.equal(server.calls.find(call => call.path === '/api/players').body.nickname, '현재부기');
  assert.deepEqual(server.calls.find(call => call.path === '/api/runs').body, run());
  assert.equal(sync.snapshot.registeredNickname, '현재부기');
  assert.equal(current.nickname, '현재부기');
  assert.equal(sync.snapshot.pendingCount, 0);
});

test('a rename during an old run submission is registered after its response without rewriting the run', async () => {
  let entered;
  let release;
  const started = new Promise(resolve => { entered = resolve; });
  const gate = new Promise(resolve => { release = resolve; });
  const current = { ...identity };
  let registered;
  const server = fakeServer(async (path, options, body) => {
    if (path === '/api/players') registered = { ...body };
    if (path === '/api/runs') { entered(); await gate; }
    if (path === '/api/leaderboard?limit=5') return response({ items: [{ ...leader, nickname: registered.nickname }] });
  });
  const sync = client(server, new MemoryStorage(), { identity: current });
  const initial = sync.submit(run());
  await started;
  current.nickname = '새이름부기';
  const renamed = sync.syncIdentity();
  release();
  await Promise.all([initial, renamed]);
  assert.deepEqual(server.calls.find(call => call.path === '/api/runs').body, run());
  assert.equal(sync.snapshot.registeredNickname, '새이름부기');
  assert.equal(sync.snapshot.leaderboard[0].nickname, '새이름부기');
  assert.equal(sync.snapshot.lastSavedRunId, run().run_id);
});

test('a failed rename remains locally current and can be retried without a pending run', async () => {
  const current = { ...identity, nickname: '오프라인부기' };
  let offline = true;
  const server = fakeServer(path => {
    if (offline && path === '/api/players') return response({}, 503);
    if (path === '/api/leaderboard?limit=5') return response({ items: [] });
  });
  const sync = client(server, new MemoryStorage(), { identity: current });
  await sync.syncIdentity();
  assert.equal(sync.snapshot.state, 'error');
  assert.equal(sync.snapshot.pendingCount, 0);
  assert.equal(sync.snapshot.nicknamePending, true);
  assert.equal(current.nickname, '오프라인부기');
  offline = false;
  await sync.retry();
  assert.equal(sync.snapshot.state, 'saved');
  assert.equal(sync.snapshot.registeredNickname, '오프라인부기');
  assert.equal(sync.snapshot.nicknamePending, false);
});
