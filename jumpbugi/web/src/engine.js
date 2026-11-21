// Browser-only port of backend.py, obstacles.py, patterns.py, season.py and
// difficulty.py. All coordinates below are logical pixels, independent of CSS.
export const RULES = Object.freeze({
  width: 640, height: 360, playerX: 25, groundY: 242,
  physicsHz: 60, gravity: 0.68, jumpSpeed: -15,
  obstacleSpeed: 7, backgroundSpeed: 6, frameTicks: 6,
  slotSeconds: 25, fadeSeconds: 4, passBonus: 10,
});

const BASE = ['hsucat.png', 'chicken.png', 'sj.png'];
const CHICKEN = ['chicken_white_ground', 'chicken_brown_ground',
  'chicken_white_flying', 'chicken_brown_flying'];
const CATS = ['hsucat_run.png', 'hsucat_crouch.png', 'hsucat_book.png'];
const GROUPS = ['sj_pair', 'sj_triple'];
const HOLES = ['sj_burrow', 'sj_escape'];
const SJ = ['sj_run.png', ...HOLES, ...GROUPS];
const WAVE = ['hsucat.png', 'chicken.png'];
const GROUND_PATTERNS = [
  ['hsucat.png', 'sj.png'],
  ['chicken_white_ground', 'chicken_brown_ground', 'sj.png'],
  ['sj.png', 'chicken.png', 'hsucat.png'],
  ['chicken_brown_ground', 'hsucat.png'],
];
const SUMMER_PATTERNS = [
  ['chicken_white_flying', 'sj.png', 'hsucat.png'],
  ['sj.png', 'chicken_brown_flying', 'chicken_white_ground'],
  ['hsucat.png', 'chicken_white_flying', 'chicken_brown_ground'],
  ['chicken_brown_flying', 'chicken_white_flying', 'sj.png'],
];
const CAT_PATTERNS = [
  ['hsucat_run.png', 'sj.png'], ['hsucat_crouch.png', 'hsucat_run.png'],
  ['hsucat_book.png', 'chicken_white_flying', 'sj.png'],
  ['chicken_brown_ground', 'hsucat_book.png', 'hsucat_crouch.png'],
];
const SJ_PATTERNS = [
  ['sj_run.png', 'sj_burrow'], ['sj_burrow', 'sj.png'],
  ['sj_pair', 'chicken_white_flying'], ['sj_triple', 'sj_run.png'],
  ['sj_escape', 'sj_run.png'],
];
const HARD_PATTERNS = [SUMMER_PATTERNS[3], CAT_PATTERNS[2], ...SJ_PATTERNS.slice(2)];
const clamp = (value, low = 0, high = 1) => Math.max(low, Math.min(high, value));

export function speedForSlot(slot) {
  const stage = Math.max(0, slot);
  return Math.min(1.75, 1.07 ** Math.min(stage, 7)
    * 1.002 ** Math.min(Math.max(stage - 7, 0), 8));
}

export function difficultyForSlot(slot) {
  const cycle = Math.min(Math.floor(Math.max(0, slot) / 8), 2);
  const flight = -(2 * RULES.jumpSpeed / RULES.gravity + 1) / RULES.physicsHz;
  return {
    speedMultiplier: speedForSlot(slot),
    recoverySeconds: Math.max([1.2, 1.05, 0.9][cycle], flight + 0.18),
    hardProbability: [0.15, 0.45, 0.75][cycle],
    chainProbability: [0.25, 0.65, 0.9][cycle],
  };
}

function jumpPlan(pattern, height, centerX, halfDistance) {
  return {
    pattern, height, centerX, halfDistance,
    progress(x) { return (this.centerX + this.halfDistance - x) / (2 * this.halfDistance); },
    active(x) { const p = this.progress(x); return p > 0 && p < 1; },
    offset(x) { const p = this.progress(x); return p > 0 && p < 1 ? -4 * this.height * p * (1 - p) : 0; },
  };
}

// Test exactly the pixels shown by the renderer. Exported masks already contain
// the original alpha threshold and the obstacle-only contour inset.
export function masksOverlap(a, ax, ay, b, bx, by) {
  ax = Math.trunc(ax); ay = Math.trunc(ay);
  bx = Math.trunc(bx); by = Math.trunc(by);
  const left = Math.max(ax, bx), right = Math.min(ax + a.width, bx + b.width);
  const top = Math.max(ay, by), bottom = Math.min(ay + a.height, by + b.height);
  if (left >= right || top >= bottom) return false;
  for (let y = top; y < bottom; y++) {
    const ar = a.rows[y - ay], br = b.rows[y - by];
    for (let x = left; x < right; x++) {
      if (ar[x - ax] === '1' && br[x - bx] === '1') return true;
    }
  }
  return false;
}

export class GameEngine {
  constructor(manifest, { random = Math.random } = {}) {
    this.manifest = manifest;
    this.random = random;
    this.playerX = RULES.playerX;
    this.groundY = RULES.groundY;
    this.reset();
  }

  reset() {
    this.playerY = this.groundY;
    this.velocityY = 0;
    this.isJumping = false;
    this.elapsed = 0;
    this.animationTick = 0;
    this.backgroundX = 0;
    this.score = 0;
    this.gameOver = false;
    this.paused = false;
    this.deathObstacle = null;
    this.patternQueue = [];
    this.currentPattern = [];
    this.firstObstacle = true;
    this.spawnObstacle();
  }

  get totalSlots() { return Math.floor((Math.max(0, this.elapsed) + 1e-9) / RULES.slotSeconds); }
  get slot() { return this.totalSlots % 8; }
  get cycle() { return Math.floor(this.totalSlots / 8); }
  get difficulty() { return difficultyForSlot(this.totalSlots); }
  get speedMultiplier() { return speedForSlot(this.totalSlots); }
  get playerFrame() { return this.isJumping ? 0 : Math.floor(this.animationTick / RULES.frameTicks); }
  get backgroundFrom() { return this.totalSlots ? (this.totalSlots - 1) % 8 : 0; }
  get backgroundTo() { return this.slot; }
  get backgroundAlpha() {
    if (!this.totalSlots) return 0;
    const p = clamp((this.elapsed - this.totalSlots * RULES.slotSeconds) / RULES.fadeSeconds);
    return p * p * (3 - 2 * p);
  }

  allows(name) {
    return name in this.manifest.obstacles
      && (this.totalSlots >= 2 || !CHICKEN.includes(name))
      && (this.totalSlots >= 4 || !CATS.includes(name))
      && (this.totalSlots >= 6 || !SJ.includes(name))
      && (this.totalSlots >= 8 || !GROUPS.includes(name))
      && (this.totalSlots >= 8 || name !== 'sj_escape');
  }

  get availablePatterns() {
    let pool = [...GROUND_PATTERNS];
    if (this.totalSlots >= 2) pool.push(...SUMMER_PATTERNS);
    if (this.totalSlots >= 4) pool.push(...CAT_PATTERNS);
    if (this.totalSlots >= 6) pool.push(...SJ_PATTERNS);
    return pool.filter(pattern => pattern.every(name => this.allows(name)));
  }

  pick(values) { return values[Math.min(values.length - 1, Math.floor(this.random() * values.length))]; }

  choosePattern() {
    let pool = this.availablePatterns;
    const hard = pool.filter(pattern => HARD_PATTERNS.includes(pattern));
    if (hard.length && this.random() < this.difficulty.hardProbability) pool = hard;
    const chosen = this.pick(pool);
    return this.random() >= this.difficulty.chainProbability ? chosen.slice(0, 1) : [...chosen];
  }

  chooseSjPattern() {
    const roll = this.random();
    return roll < 0.325 ? 'high' : roll < 0.65 ? 'low' : null;
  }

  makeJump(pattern, kind, width, offset = 0, index = null, jitter = 0) {
    const o = this.obstacle;
    const pw = this.manifest.player.width;
    const center = this.playerX + (pw - width) / 2 - offset;
    const contactHalf = (pw + width) / 2;
    const speed = RULES.obstacleSpeed * RULES.physicsHz * this.speedMultiplier;
    let height, factor, minimum, clearance;
    if (kind === 'sj') {
      height = pattern === 'high' ? 306 : 18;
      factor = pattern === 'high' ? 4.8 : 2.2;
      minimum = pattern === 'high' ? 0.9 : 0.8;
      clearance = 8;
    } else if (kind === 'running') {
      height = pattern === 'high' ? 384 : 24;
      factor = 2.2; minimum = 0.9; clearance = 16;
    } else {
      height = { high: 192, near: 128, low: 12 }[pattern];
      factor = pattern === 'near' ? 4.8 : 2.2;
      minimum = 0.9; clearance = 4;
    }
    if (pattern !== 'low') {
      const playerRise = kind === 'sj'
        ? Math.min(0, RULES.jumpSpeed + RULES.gravity / 2) ** 2 / (2 * RULES.gravity) : 0;
      const lift = o.groundY + o.height - (this.groundY - playerRise) + clearance;
      height = Math.max(height, lift + 1);
      factor = Math.max(factor, (1 - lift / height) ** -0.5);
    }
    let halfDistance = Math.max(factor * contactHalf, minimum * speed / 2);
    if (kind === 'sj' && index !== null) {
      if (pattern === 'high') halfDistance += index * (80 + width + 3) + jitter;
      else halfDistance = Math.max(contactHalf + 1, this.playerX + 370 - index * 80 - jitter - center);
    }
    return jumpPlan(pattern, height, center, halfDistance);
  }

  spawnObstacle(explicitName = null) {
    let name = explicitName;
    if (!name) {
      if (this.firstObstacle) name = this.pick(BASE);
      else {
        this.patternQueue = this.patternQueue.filter(kind => this.allows(kind));
        if (!this.patternQueue.length) {
          this.currentPattern = this.choosePattern();
          this.patternQueue = [...this.currentPattern];
        }
        name = this.patternQueue.shift();
      }
      if (this.totalSlots >= 8 && name === 'sj.png') name = this.pick(GROUPS);
    }
    const asset = this.manifest.obstacles[name];
    if (!asset) throw new Error(`Missing obstacle asset: ${name}`);
    const { width, height } = asset;
    const flying = name.endsWith('_flying');
    const flightLevel = flying ? this.pick(['low', 'middle', 'high']) : null;
    let y = RULES.height - height + 7;
    if (flying) y = this.groundY - { high: 72, middle: 2, low: -92 }[flightLevel] - height;
    else if (WAVE.includes(name) || CHICKEN.includes(name) || name === 'hsucat_run.png'
      || name === 'sj.png' || SJ.includes(name)) y = RULES.height - height - 2;
    const recovery = this.difficulty.recoverySeconds;
    const futureSlot = this.totalSlots + Math.ceil(recovery / RULES.slotSeconds);
    const approachSpeed = RULES.obstacleSpeed * RULES.physicsHz * speedForSlot(futureSlot);
    const x = this.firstObstacle ? RULES.width
      : Math.max(RULES.width, this.playerX + this.manifest.player.width + approachSpeed * recovery);
    const o = this.obstacle = {
      name, x, y, width, height, spawnX: x, groundY: y,
      animationTick: 0, flightLevel, jump: null, members: [], passed: false,
      runMode: 'run', holeTiming: null, holeStart: 480 + this.playerX, holeEnd: 480 + this.playerX,
    };
    this.firstObstacle = false;
    if (HOLES.includes(name)) {
      o.holeTiming = this.pick(['fast', 'slow']);
      // Shift original 480-based action coordinates by the player's move right.
      // Duration and clearance remain those of the Pygame reference.
      const end = name === 'sj_burrow' ? { fast: 330, slow: 170 } : { fast: 300, slow: 180 };
      o.holeEnd = this.playerX + Math.max(end[o.holeTiming], this.manifest.player.width + 32);
    }
    if (name === 'hsucat_run.png') {
      o.runMode = this.pick(this.totalSlots >= 8 ? ['fall', 'high', 'low', 'run'] : ['fall', 'run']);
      if (['high', 'low'].includes(o.runMode)) o.jump = this.makeJump(o.runMode, 'running', width);
    }
    if (WAVE.includes(name) && this.totalSlots >= 8 && this.random() < 0.65) {
      const pattern = this.pick(['high', 'near', 'low']);
      o.jump = this.makeJump(pattern, 'wave', width);
    }
    if (GROUPS.includes(name)) {
      const singleWidth = this.manifest.obstacles['sj.png'].width;
      const count = name === 'sj_pair' ? 2 : 3;
      for (let index = 0; index < count; index++) {
        const offset = index * (singleWidth + 3);
        const pattern = this.totalSlots >= 8 ? this.chooseSjPattern() : null;
        const jitter = this.random() * 25;
        const plan = pattern ? this.makeJump(pattern, 'sj', singleWidth, offset, index, jitter) : null;
        o.members.push({ offset, pattern, jump: plan, passed: false });
      }
    } else if (['sj.png', 'sj_run.png'].includes(name) && this.totalSlots >= 8) {
      const pattern = this.chooseSjPattern();
      if (pattern) o.jump = this.makeJump(pattern, 'sj', width);
    }
    return o;
  }

  get obstacleRequiresJump() {
    const o = this.obstacle;
    if (o.name === 'sj_burrow') return false;
    if (o.members.length) return o.members.some(member => member.pattern !== 'high');
    if (o.flightLevel) return o.flightLevel === 'low';
    return !o.jump || o.jump.pattern === 'low';
  }

  get obstacleFrame() {
    const o = this.obstacle;
    const count = this.manifest.obstacles[o.name].frames.length;
    if (o.jump?.active(o.x)) return 0;
    const relativeX = o.x - this.playerX;
    if (o.name === 'hsucat_crouch.png') return Math.floor(clamp((480 - relativeX) / (480 - 140)) * (count - 1));
    if (o.name === 'hsucat_run.png') {
      if (o.runMode === 'fall' && relativeX <= 420) {
        return 4 + Math.floor(clamp((420 - relativeX) / (420 - 180)) * (count - 5));
      }
      return Math.floor(o.animationTick / RULES.frameTicks) % Math.min(4, count);
    }
    if (o.name === 'hsucat_book.png') return Math.floor(clamp((480 - relativeX) / 300) * (count - 1));
    if (HOLES.includes(o.name)) return Math.floor(clamp((o.holeStart - o.x) / (o.holeStart - o.holeEnd)) * (count - 1));
    return Math.floor(o.animationTick / RULES.frameTicks) % count;
  }

  get drawParts() {
    const o = this.obstacle;
    if (o.members.length) {
      const count = this.manifest.obstacles['sj.png'].frames.length;
      const frame = Math.floor(o.animationTick / RULES.frameTicks) % count;
      return o.members.map(member => ({
        name: 'sj.png', frame: member.jump?.active(o.x) ? 0 : frame,
        x: Math.trunc(o.x + member.offset), y: Math.trunc(o.groundY + (member.jump?.offset(o.x) ?? 0)),
      }));
    }
    return [{ name: o.name, frame: this.obstacleFrame, x: Math.trunc(o.x), y: Math.trunc(o.y) }];
  }

  jump() {
    if (this.paused || this.gameOver || this.isJumping) return false;
    this.velocityY = RULES.jumpSpeed;
    this.isJumping = true;
    return true;
  }
  setPaused(value) { if (!this.gameOver) this.paused = Boolean(value); }
  togglePause() { this.setPaused(!this.paused); return this.paused; }

  scrollBackground(dt) {
    const width = this.manifest.backgrounds[0].width;
    this.backgroundX = -((-this.backgroundX
      + RULES.backgroundSpeed * this.speedMultiplier * Math.max(0, dt) * RULES.physicsHz) % width);
  }

  awardPassBonuses() {
    const o = this.obstacle;
    if (o.members.length) {
      const width = this.manifest.obstacles['sj.png'].width;
      for (const member of o.members) {
        if (!member.passed && Math.trunc(o.x + member.offset) + width <= this.playerX) {
          this.score += RULES.passBonus;
          member.passed = true;
        }
      }
      o.passed = o.members.every(member => member.passed);
    } else if (!o.passed && Math.trunc(o.x) + o.width <= this.playerX) {
      this.score += RULES.passBonus;
      o.passed = true;
    }
  }

  collides() {
    const playerMask = this.manifest.player.frames[this.playerFrame].mask;
    return this.drawParts.some(part => masksOverlap(playerMask, this.playerX, this.playerY,
      this.manifest.obstacles[part.name].frames[part.frame].mask, part.x, part.y));
  }

  updateStep(step) {
    this.scrollBackground(step / RULES.physicsHz);
    if (!this.isJumping) {
      this.animationTick = (this.animationTick + step)
        % (this.manifest.player.frames.length * RULES.frameTicks);
    }
    if (this.isJumping) {
      this.playerY += this.velocityY * step + RULES.gravity * step * (step + 1) / 2;
      this.velocityY += RULES.gravity * step;
      if (this.playerY >= this.groundY) {
        this.playerY = this.groundY;
        this.velocityY = 0;
        this.isJumping = false;
      }
    }
    const o = this.obstacle;
    o.x -= RULES.obstacleSpeed * this.speedMultiplier * step;
    if (o.jump) o.y = o.groundY + o.jump.offset(o.x);
    o.animationTick += step;
    this.awardPassBonuses();
    if (this.collides()) {
      this.gameOver = true;
      this.deathObstacle = o.name;
      return;
    }
    if (o.x + o.width < 0) this.spawnObstacle();
  }

  update(dt = 1 / RULES.physicsHz) {
    if (this.gameOver || this.paused) return;
    const seconds = Number.isFinite(dt) ? Math.max(0, dt) : 0;
    const previousSeconds = Math.floor(this.elapsed + 1e-9);
    this.elapsed += seconds;
    this.score += Math.floor(this.elapsed + 1e-9) - previousSeconds;
    // Match the reference: clocks use elapsed time, movement catches up at most
    // 100 ms, split further at high speed so collision checks never skip bodies.
    let remaining = Math.min(seconds, 0.1) * RULES.physicsHz;
    while (remaining > 1e-9 && !this.gameOver) {
      const step = Math.min(remaining, 1 / this.speedMultiplier);
      this.updateStep(step);
      remaining -= step;
    }
  }
}
