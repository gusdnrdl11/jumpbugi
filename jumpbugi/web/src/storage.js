export const GAME_VERSION = '0.1.0';
const PREFIX = 'jumpbugi.web.v1.';
const DEMO = [
  { nickname: 'TestCat', score: 850, survival_time: 151 },
  { nickname: 'JumpBugi', score: 720, survival_time: 128 },
  { nickname: 'TestRunner', score: 650, survival_time: 116 },
  { nickname: 'HansungCat', score: 480, survival_time: 91 },
  { nickname: 'Runner', score: 320, survival_time: 65 },
];
const validNumber = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
const validIdentity = value => value && typeof value.player_id === 'string' && value.player_id.length > 0 && value.player_id.length <= 100 && typeof value.nickname === 'string' && value.nickname.length > 0 && value.nickname.length <= 40;
const validResult = value => validIdentity(value) && Number.isInteger(value.score) && validNumber(value.score) && validNumber(value.survival_time) && typeof value.played_at === 'string' && typeof value.game_version === 'string';

function makeId(random) {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const value = Math.floor(random() * 16);
    return (c === 'x' ? value : (value & 3) | 8).toString(16);
  });
}

export class PlayerStore {
  constructor(storage, { random = Math.random, now = () => new Date().toISOString() } = {}) {
    this.random = random;
    this.now = now;
    this.persistent = true;
    try { this.storage = storage === undefined ? globalThis.localStorage : storage; }
    catch { this.storage = null; }
    if (!this.storage) this.persistent = false;
    const identity = this.read('identity');
    this.identity = validIdentity(identity) ? identity : {
      player_id: makeId(random), nickname: `JumpBugi_${String(Math.floor(random() * 1000)).padStart(3, '0')}`,
    };
    this.write('identity', this.identity);
    const saved = this.read('results');
    this.results = Array.isArray(saved) ? saved.filter(validResult).slice(-50) : [];
    this.best = this.results.filter(result => result.player_id === this.identity.player_id).reduce((best, result) => Math.max(best, result.score), 0);
  }

  read(key) {
    try {
      const value = this.storage?.getItem(PREFIX + key);
      return value ? JSON.parse(value) : null;
    } catch { this.persistent = false; return null; }
  }

  write(key, value) {
    try {
      if (this.storage) this.storage.setItem(PREFIX + key, JSON.stringify(value));
      else this.persistent = false;
    } catch { this.persistent = false; }
  }

  get isDemo() { return this.results.length === 0; }

  recordRun({ score, survival_time, death_obstacle = null, max_speed = 1, device_type = 'desktop' } = {}) {
    if (!Number.isInteger(score) || !validNumber(score) || !validNumber(survival_time) || !validNumber(max_speed)) return null;
    const result = {
      ...this.identity, run_id: makeId(this.random), score, survival_time,
      game_version: GAME_VERSION, played_at: this.now(),
      death_obstacle: typeof death_obstacle === 'string' ? death_obstacle : null,
      max_speed, device_type: device_type === 'mobile' ? 'mobile' : 'desktop',
    };
    this.results.push(result);
    // Keep the best result even after more than 50 attempts.
    if (this.results.length > 50) {
      const bestResult = this.results.reduce((a, b) => a.score >= b.score ? a : b);
      this.results = this.results.slice(-50);
      if (!this.results.includes(bestResult)) this.results[0] = bestResult;
    }
    this.best = Math.max(this.best, score);
    this.write('results', this.results);
    return result;
  }

  leaderboard() {
    return [...(this.isDemo ? DEMO : this.results)].sort((a, b) => b.score - a.score || b.survival_time - a.survival_time).slice(0, 5);
  }
}
