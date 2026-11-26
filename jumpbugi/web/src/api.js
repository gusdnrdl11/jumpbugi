export const PENDING_KEY = 'jumpbugi.web.v1.pending';
export const MAX_PENDING_RUNS = 50;

// Pages and the standalone static server keep their existing local-only mode.
export function isLocalServerMode(location) {
  const host = String(location?.hostname ?? '').toLowerCase();
  return ['http:', 'https:'].includes(location?.protocol)
    && ['localhost', '127.0.0.1', '[::1]', '::1'].includes(host)
    && new URLSearchParams(location?.search ?? '').get('server') === '1';
}

const validLeader = row => row && typeof row.nickname === 'string'
  && Number.isSafeInteger(row.score) && row.score >= 0
  && Number.isFinite(row.survival_time) && row.survival_time >= 0;

export class LocalServerSync {
  constructor({ enabled = false, identity, storage, fetch = globalThis.fetch,
    onChange = () => {}, timeoutMs = 5000 } = {}) {
    this.enabled = enabled;
    this.identity = identity;
    // Browser fetch requires the Window/global receiver, not this sync object.
    this.fetch = fetch.bind(globalThis);
    this.onChange = onChange;
    this.timeoutMs = timeoutMs;
    this.state = 'idle';
    this.error = '';
    this.leaderboard = null;
    this.persistent = true;
    this.pending = [];
    this.localOnlyCount = 0;
    this.lastSavedRunId = null;
    this.latestRunId = null;
    this.registeredNickname = null;
    this.inFlight = null;
    this.storage = null;
    if (!enabled) return;
    try {
      this.storage = storage === undefined ? globalThis.localStorage : storage;
      if (!this.storage) this.persistent = false;
      const saved = JSON.parse(this.storage?.getItem(PENDING_KEY) ?? '[]');
      const seen = new Set();
      if (Array.isArray(saved)) this.pending = saved.filter(run => {
        if (!run || run.player_id !== identity.player_id || typeof run.run_id !== 'string'
          || seen.has(run.run_id)) return false;
        seen.add(run.run_id);
        return true;
      }).slice(0, MAX_PENDING_RUNS);
      this.latestRunId = this.pending.at(-1)?.run_id ?? null;
    } catch { this.persistent = false; }
  }

  get snapshot() {
    return Object.freeze({ enabled: this.enabled, state: this.state,
      pendingCount: this.pending.length, persistent: this.persistent,
      localOnlyCount: this.localOnlyCount, lastSavedRunId: this.lastSavedRunId,
      latestRunId: this.latestRunId,
      latestPending: this.pending.some(run => run.run_id === this.latestRunId),
      registeredNickname: this.registeredNickname,
      nicknamePending: this.enabled && this.registeredNickname !== this.identity.nickname,
      error: this.error,
      leaderboard: this.leaderboard?.map(row => ({ ...row })) ?? null });
  }

  notify() { this.onChange(this.snapshot); }

  persist() {
    try {
      if (!this.storage) this.persistent = false;
      else this.storage.setItem(PENDING_KEY, JSON.stringify(this.pending));
    } catch { this.persistent = false; }
  }

  async request(path, method = 'GET', body) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await this.fetch(path, { method, cache: 'no-store',
        credentials: 'omit', redirect: 'error', signal: controller.signal,
        ...(body === undefined ? {} : {
          headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
        }) });
      if (!response.ok) throw new Error(`서버 응답 ${response.status}`);
      return await response.json();
    } catch (error) {
      if (controller.signal.aborted) throw new Error('서버 응답 시간이 초과되었습니다.');
      throw error;
    } finally { clearTimeout(timer); }
  }

  submit(run) {
    if (!this.enabled || !run) return Promise.resolve(this.snapshot);
    if (run.player_id !== this.identity.player_id) {
      return Promise.resolve(this.snapshot);
    }
    this.latestRunId = run.run_id;
    if (!this.pending.some(item => item.run_id === run.run_id)) {
      if (this.pending.length >= MAX_PENDING_RUNS) {
        this.localOnlyCount++;
        this.state = 'error';
        this.error = '전송 대기열이 가득 찼습니다.';
        this.notify();
        return Promise.resolve(this.snapshot);
      }
      // Persist the exact run_id and payload before making any network request.
      this.pending.push({ ...run });
      this.persist();
    }
    return this.retry();
  }

  retry() {
    if (!this.enabled) return Promise.resolve(this.snapshot);
    if (this.inFlight) return this.inFlight;
    this.state = 'syncing';
    this.error = '';
    this.notify();
    this.inFlight = this.flush().finally(() => { this.inFlight = null; });
    return this.inFlight;
  }

  syncIdentity() { return this.retry(); }

  async registerIdentity() {
    do {
      // A name can change while this request is in flight. Acknowledge only
      // its snapshot, then register the latest identity before finishing.
      const identity = { ...this.identity };
      const player = await this.request('/api/players', 'POST', identity);
      if (player.player_id !== identity.player_id || player.nickname !== identity.nickname) {
        throw new Error('서버 사용자 응답이 다릅니다.');
      }
      this.registeredNickname = identity.nickname;
    } while (this.registeredNickname !== this.identity.nickname);
  }

  async flush() {
    try {
      await this.registerIdentity();
      do {
        if (this.registeredNickname !== this.identity.nickname) await this.registerIdentity();
        while (this.pending.length) {
          const run = this.pending[0];
          const saved = await this.request('/api/runs', 'POST', run);
          if (saved.run_id !== run.run_id || saved.player_id !== run.player_id) {
            throw new Error('서버 저장 응답이 다릅니다.');
          }
          this.pending.shift();
          this.lastSavedRunId = run.run_id;
          this.persist();
        }
        if (this.registeredNickname !== this.identity.nickname) continue;
        const board = await this.request('/api/leaderboard?limit=5');
        if (!Array.isArray(board.items) || !board.items.every(validLeader)) {
          throw new Error('서버 기록 형식이 올바르지 않습니다.');
        }
        if (this.registeredNickname === this.identity.nickname) this.leaderboard = board.items.slice(0, 5);
        // A game can finish or a name can change while the board is loading.
      } while (this.pending.length || this.registeredNickname !== this.identity.nickname);
      this.state = 'saved';
    } catch (error) {
      this.state = 'error';
      this.error = error.message || '서버에 연결할 수 없습니다.';
      this.leaderboard = null;
    }
    this.notify();
    return this.snapshot;
  }
}
