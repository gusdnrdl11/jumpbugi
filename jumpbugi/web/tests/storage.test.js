import test from 'node:test';
import assert from 'node:assert/strict';
import { PlayerStore } from '../src/storage.js';

class MemoryStorage {
  constructor() { this.data = new Map(); }
  getItem(key) { return this.data.get(key) ?? null; }
  setItem(key, value) { this.data.set(key, String(value)); }
  removeItem(key) { this.data.delete(key); }
}

const RESULT_KEY = 'jumpbugi.web.v1.results';
const NOW = '2026-11-21T12:00:00.000Z';
const makeStore = storage => new PlayerStore(storage, { now: () => NOW, random: () => 0.25 });
const run = (score = 20, survival_time = 10) => ({
  score, survival_time, death_obstacle: 'sj.png', max_speed: 1.07, device_type: 'desktop',
});

test('the same browser retains its player identity without using its nickname as an ID', () => {
  const storage = new MemoryStorage();
  const first = makeStore(storage);
  assert.equal(typeof first.identity.player_id, 'string');
  assert.ok(first.identity.player_id.length > 8);
  assert.equal(typeof first.identity.nickname, 'string');
  assert.notEqual(first.identity.player_id, first.identity.nickname);
  assert.deepEqual(makeStore(storage).identity, first.identity);
});

test('a finished run stores identity and export-ready result metadata', () => {
  const storage = new MemoryStorage();
  const store = makeStore(storage);
  const result = store.recordRun(run(53, 23.5));
  assert.ok(result);
  assert.equal(result.player_id, store.identity.player_id);
  assert.equal(result.nickname, store.identity.nickname);
  assert.equal(result.score, 53);
  assert.equal(result.survival_time, 23.5);
  assert.equal(result.game_version, '0.1.0');
  assert.equal(result.played_at, NOW);
  assert.equal(result.death_obstacle, 'sj.png');
  assert.ok(result.run_id);
  assert.equal(store.best, 53);
  assert.equal(store.results.length, 1);
  assert.equal(store.isDemo, false);
  assert.equal(makeStore(storage).best, 53);
  assert.equal(makeStore(storage).results.length, 1);
});

test('a lower later score never lowers the best score', () => {
  const store = makeStore(new MemoryStorage());
  store.recordRun(run(120, 20));
  store.recordRun(run(7, 7));
  assert.equal(store.best, 120);
});

test('ranking uses score first, survival time second, and only the five leading records', () => {
  const store = makeStore(new MemoryStorage());
  for (const score of [10, 80, 30, 60, 50, 70]) store.recordRun(run(score, score));
  store.recordRun(run(80, 90));
  const leaders = store.leaderboard();
  assert.equal(leaders.length, 5);
  assert.deepEqual(leaders.map(result => result.score), [80, 80, 70, 60, 50]);
  assert.equal(leaders[0].survival_time, 90);
});

test('invalid score and survival values are never persisted as a result', () => {
  const store = makeStore(new MemoryStorage());
  for (const invalid of [NaN, Infinity, -1, '10', null, undefined]) {
    assert.equal(store.recordRun({ ...run(), score: invalid }), null);
    assert.equal(store.recordRun({ ...run(), survival_time: invalid }), null);
  }
  assert.equal(store.results.length, 0);
  assert.equal(store.best, 0);
});

test('corrupt browser data does not prevent a new playable session', () => {
  const storage = new MemoryStorage();
  storage.setItem('jumpbugi.web.v1.identity', '{broken');
  storage.setItem(RESULT_KEY, '{broken');
  const store = makeStore(storage);
  assert.ok(store.identity.player_id);
  assert.equal(store.best, 0);
  assert.equal(store.results.length, 0);
  assert.ok(store.recordRun(run()));
});

test('storage denial falls back to session memory and still keeps score', () => {
  const storage = {
    getItem() { throw new Error('storage denied'); },
    setItem() { throw new Error('storage denied'); },
  };
  const store = makeStore(storage);
  assert.equal(store.persistent, false);
  assert.ok(store.recordRun(run(77, 17)));
  assert.equal(store.best, 77);
  assert.equal(store.leaderboard()[0].score, 77);
});

test('completed run history is bounded to fifty results', () => {
  const storage = new MemoryStorage();
  const store = makeStore(storage);
  for (let score = 1; score <= 70; score++) store.recordRun(run(score, score));
  assert.equal(store.results.length, 50);
  assert.equal(JSON.parse(storage.getItem(RESULT_KEY)).length, 50);
  assert.equal(store.best, 70);
  assert.equal(makeStore(storage).results.length, 50);
});

test('the personal best survives more than fifty lower attempts and a reload', () => {
  const storage = new MemoryStorage();
  const store = makeStore(storage);
  store.recordRun(run(999, 150));
  for (let score = 1; score <= 70; score++) store.recordRun(run(score, score));
  assert.equal(store.results.length, 50);
  assert.equal(store.best, 999);
  assert.equal(makeStore(storage).best, 999);
});

test('renaming trims the name while preserving identity, best score and historical snapshots', () => {
  const storage = new MemoryStorage();
  const store = makeStore(storage);
  const identity = store.identity;
  const originalId = identity.player_id;
  const previous = store.recordRun(run(120, 20));
  const oldResults = JSON.stringify(store.results);
  const changed = store.setNickname('  새Bugi7  ');
  assert.deepEqual(changed, { ok: true, nickname: '새Bugi7', changed: true, persistent: true });
  assert.equal(store.identity, identity, 'the API client must keep its shared identity reference');
  assert.equal(identity.player_id, originalId);
  assert.equal(identity.nickname, '새Bugi7');
  assert.equal(store.best, 120);
  assert.equal(JSON.stringify(store.results), oldResults);
  assert.equal(storage.getItem(RESULT_KEY), oldResults);
  const reloaded = makeStore(storage);
  assert.deepEqual(reloaded.identity, identity);
  assert.deepEqual(reloaded.results, [previous]);
  assert.equal(reloaded.best, 120);
  assert.equal(store.recordRun(run()).nickname, '새Bugi7');
  assert.notEqual(previous.nickname, '새Bugi7');
});

test('nickname limits count Unicode codepoints and allow visible Korean, Latin, numbers and emoji', () => {
  const store = makeStore(new MemoryStorage());
  for (const nickname of ['부기', 'Bugi07', '부기 B7', 'B!', '😀부', '😀'.repeat(12)]) {
    assert.equal(store.setNickname(nickname).ok, true, nickname);
    assert.equal(store.identity.nickname, nickname);
  }
  assert.equal(store.setNickname('😀'.repeat(13)).ok, false);
  assert.equal(store.setNickname('가'.repeat(12)).ok, true);
  assert.equal(store.setNickname('가'.repeat(13)).ok, false);
});

test('invalid nickname edits never change the identity or persisted data', () => {
  const storage = new MemoryStorage();
  const store = makeStore(storage);
  const original = { ...store.identity };
  const saved = storage.getItem('jumpbugi.web.v1.identity');
  for (const nickname of ['', '   ', 'A', 'a'.repeat(13), '부\u0000기', '부\u007f기',
    '부\u200b기', '\t부기', '부기\n', '\ufeff부기', '부\ud800기', '부\u2028기', '부\u2029기', null, 12]) {
    const result = store.setNickname(nickname);
    assert.equal(result.ok, false, JSON.stringify(nickname));
    assert.ok(result.error.length > 0);
    assert.deepEqual(store.identity, original);
    assert.equal(storage.getItem('jumpbugi.web.v1.identity'), saved);
  }
});

test('nickname edits still work for the current session when browser storage is blocked', () => {
  const store = makeStore({ getItem() { throw new Error('denied'); }, setItem() { throw new Error('denied'); } });
  const identity = store.identity;
  const result = store.setNickname('이번부기');
  assert.equal(result.ok, true);
  assert.equal(result.persistent, false);
  assert.equal(store.identity, identity);
  assert.equal(identity.nickname, '이번부기');
});

test('a legacy nickname longer than the editing limit does not regenerate its player ID or history', () => {
  const storage = new MemoryStorage();
  const old = { player_id: 'legacy-player', nickname: '기존닉네임'.repeat(4) };
  storage.setItem('jumpbugi.web.v1.identity', JSON.stringify(old));
  const store = makeStore(storage);
  assert.deepEqual(store.identity, old);
  const previous = store.recordRun(run(120, 20));
  const reloaded = makeStore(storage);
  assert.equal(reloaded.identity.player_id, old.player_id);
  assert.deepEqual(reloaded.results, [previous]);
  assert.equal(reloaded.setNickname('새부기').ok, true);
  assert.equal(reloaded.identity.player_id, old.player_id);
  assert.equal(reloaded.results[0].nickname, old.nickname);
});
