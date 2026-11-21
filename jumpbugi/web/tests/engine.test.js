import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { GameEngine, RULES, difficultyForSlot, speedForSlot, masksOverlap } from '../src/engine.js';

const manifest = JSON.parse(readFileSync(new URL('../assets/manifest.json', import.meta.url)));
const engine = () => new GameEngine(manifest, { random: () => 0.9 });
const solidMask = (width, height) => ({ width, height, rows: Array(height).fill('1'.repeat(width)) });
const nearly = (actual, expected, tolerance = 1e-7) => assert.ok(Math.abs(actual - expected) < tolerance, `${actual} ≠ ${expected}`);
const bonus = game => game.score - Math.floor(game.elapsed + 1e-9);

test('640 × 360 logical field keeps the reference vertical physics and permits one jump', () => {
  const game = engine();
  assert.equal(RULES.width, 640);
  assert.equal(RULES.height, 360);
  assert.ok(game.playerX >= 0 && game.playerX + manifest.player.width < RULES.width / 2);
  assert.equal(game.playerY, 242);
  assert.equal(game.jump(), true);
  assert.equal(game.jump(), false);
  game.obstacle.x = 1e6;
  const lowPoints = [];
  for (let i = 0; i < 90; i++) { game.update(1 / 120); lowPoints.push(game.playerY); }
  assert.ok(Math.min(...lowPoints) < 85 && Math.min(...lowPoints) > 80);
  assert.equal(game.playerY, game.groundY);
  assert.equal(game.isJumping, false);
  assert.equal(game.jump(), true);
});

test('jump trajectory and landing remain equal at 30, 60 and 120 Hz', () => {
  const snapshots = [30, 60, 120].map(hz => {
    const game = engine(); game.obstacle.x = 1e6; game.jump();
    for (let i = 0; i < hz / 2; i++) game.update(1 / hz);
    return { y: game.playerY, velocity: game.velocityY, x: game.obstacle.x };
  });
  for (const value of snapshots) {
    nearly(value.y, snapshots[0].y);
    nearly(value.velocity, snapshots[0].velocity);
    nearly(value.x, snapshots[0].x);
  }
});

test('alpha masks exclude transparent pixels and use the same integer positions as drawing', () => {
  const left = { width: 3, height: 2, rows: ['001', '000'] };
  const right = { width: 3, height: 2, rows: ['100', '000'] };
  assert.equal(masksOverlap(left, 10, 5, right, 11, 5), false);
  assert.equal(masksOverlap(left, 10, 5, right, 12.9, 5), true);
  assert.equal(masksOverlap(left, 10, 5, right, 12, 6), false);
  assert.equal(masksOverlap(left, 10, 5, right, 13, 5), false);
});

test('pause and game over freeze physics, animation, clocks and points', () => {
  const game = engine(); game.update(0.1);
  const snapshot = () => [game.elapsed, game.score, game.obstacle.x, game.backgroundX, game.animationTick];
  const before = snapshot();
  game.setPaused(true); game.update(10);
  assert.deepEqual(snapshot(), before);
  assert.equal(game.jump(), false);
  game.togglePause(); assert.equal(game.paused, false);
  game.gameOver = true; game.update(10);
  assert.deepEqual(snapshot(), before);
  assert.equal(game.jump(), false);
});

test('season slots, smooth fade and speed curve use the Pygame schedule', () => {
  const game = engine();
  game.elapsed = 25;
  assert.deepEqual([game.totalSlots, game.slot, game.cycle, game.backgroundFrom, game.backgroundTo], [1, 1, 0, 0, 1]);
  assert.equal(game.backgroundAlpha, 0);
  game.elapsed = 27; nearly(game.backgroundAlpha, 0.5);
  game.elapsed = 29; assert.equal(game.backgroundAlpha, 1);
  game.elapsed = 200;
  assert.deepEqual([game.slot, game.cycle, game.backgroundFrom, game.backgroundTo], [0, 1, 7, 0]);
  nearly(speedForSlot(7), 1.07 ** 7);
  nearly(speedForSlot(15), 1.07 ** 7 * 1.002 ** 8);
  assert.equal(speedForSlot(1000), speedForSlot(15));
  assert.ok(difficultyForSlot(100).recoverySeconds >= -(2 * RULES.jumpSpeed / RULES.gravity + 1) / 60 + 0.18);
});

test('survival score is independent of display frequency and long delays cap movement', () => {
  for (const hz of [30, 60, 120]) {
    const game = engine(); game.obstacle.x = 1e6;
    for (let frame = 0; frame < hz * 61; frame++) game.update(1 / hz);
    assert.equal(game.score, 61);
    assert.equal(game.totalSlots, 2);
  }
  const game = engine(); game.obstacle.x = 1e6;
  game.update(10);
  assert.equal(game.score, 10);
  nearly(game.obstacle.x, 1e6 - 42);
});

test('pattern pools unlock in summer, autumn, winter and the second spring', () => {
  const game = engine();
  const contains = name => game.availablePatterns.some(pattern => pattern.includes(name));
  assert.equal(contains('chicken_white_flying'), false);
  assert.equal(contains('hsucat_run.png'), false);
  game.elapsed = 50; assert.equal(contains('chicken_white_flying'), true);
  assert.equal(contains('hsucat_run.png'), false);
  game.elapsed = 100; assert.equal(contains('hsucat_run.png'), true);
  assert.equal(contains('sj_burrow'), false);
  game.elapsed = 150; assert.equal(contains('sj_burrow'), true);
  assert.equal(contains('sj_pair'), false);
  assert.equal(contains('sj_escape'), false);
  game.elapsed = 200;
  assert.equal(contains('sj_pair'), true); assert.equal(contains('sj_escape'), true);
});

test('jump plans are fixed at spawn and reset returns to the first spring', () => {
  const game = engine(); game.elapsed = 199.9; game.spawnObstacle('hsucat.png');
  assert.equal(game.obstacle.jump, null);
  game.elapsed = 200.1; game.updateStep(0);
  assert.equal(game.obstacle.jump, null);
  game.random = () => 0;
  game.spawnObstacle('hsucat.png');
  assert.equal(game.obstacle.jump.pattern, 'high');
  game.reset();
  assert.equal(game.elapsed, 0); assert.equal(game.score, 0);
  assert.equal(game.gameOver, false); assert.equal(game.paused, false);
  assert.equal(game.obstacle.jump, null);
});

test('single bonuses and each group member are rewarded once at the rendered boundary', () => {
  const game = engine(); game.playerY = -1000;
  game.spawnObstacle('hsucat.png');
  game.obstacle.x = game.playerX - game.obstacle.width + 1.1;
  game.updateStep(0); assert.equal(game.score, 0);
  game.obstacle.x = game.playerX - game.obstacle.width;
  game.updateStep(0); game.updateStep(0); assert.equal(game.score, 10);
  for (const [name, count] of [['sj_pair', 2], ['sj_triple', 3]]) {
    game.reset(); game.playerY = -1000; game.spawnObstacle(name);
    const width = manifest.obstacles['sj.png'].width;
    for (let index = 0; index < count; index++) {
      const member = game.obstacle.members[index];
      game.obstacle.x = game.playerX - width - member.offset + 1.1;
      game.updateStep(0); assert.equal(game.score, index * 10);
      game.obstacle.x = game.playerX - width - member.offset;
      game.updateStep(0); game.updateStep(0);
      assert.equal(game.score, (index + 1) * 10);
      assert.equal(member.passed, true);
    }
  }
});

test('a passed group member is rewarded before a later member collides', () => {
  const fake = structuredClone(manifest);
  for (const frame of fake.player.frames) frame.mask = solidMask(fake.player.width, fake.player.height);
  for (const frame of fake.obstacles['sj.png'].frames) frame.mask = solidMask(fake.obstacles['sj.png'].width, 40);
  const game = new GameEngine(fake, { random: () => 0.9 });
  game.spawnObstacle('sj_pair');
  game.obstacle.x = game.playerX - fake.obstacles['sj.png'].width;
  game.updateStep(0);
  assert.equal(game.gameOver, true);
  assert.equal(game.score, 10);
  assert.equal(game.obstacle.members[0].passed, true);
  assert.equal(game.obstacle.members[1].passed, false);
});

function spawnCase(game, name, mode, slot) {
  game.elapsed = slot * 25;
  game.score = Math.floor(game.elapsed);
  const rolls = [];
  if (['hsucat.png', 'chicken.png'].includes(name)) {
    if (mode === null) rolls.push(0.99);
    else rolls.push(0, (['high', 'near', 'low'].indexOf(mode) + 0.5) / 3);
  } else if (name.endsWith('_flying')) rolls.push((['low', 'middle', 'high'].indexOf(mode) + 0.5) / 3);
  else if (name === 'hsucat_run.png') rolls.push((['fall', 'high', 'low', 'run'].indexOf(mode) + 0.5) / 4);
  else if (['sj.png', 'sj_run.png'].includes(name)) rolls.push(mode === 'high' ? 0 : mode === 'low' ? 0.5 : 0.99);
  else if (['sj_burrow', 'sj_escape'].includes(name)) rolls.push(mode === 'fast' ? 0 : 0.9);
  game.random = () => rolls.length ? rolls.shift() : 0.9;
  return game.spawnObstacle(name);
}

const encounters = [
  ...['hsucat.png', 'chicken.png'].flatMap(name => [null, 'high', 'near', 'low'].map(mode => [name, mode])),
  ...['chicken_white_flying', 'chicken_brown_flying'].flatMap(name => ['low', 'middle', 'high'].map(mode => [name, mode])),
  ['chicken_white_ground', null], ['chicken_brown_ground', null],
  ...['fall', 'high', 'low', 'run'].map(mode => ['hsucat_run.png', mode]),
  ['hsucat_crouch.png', null], ['hsucat_book.png', null],
  ...['sj.png', 'sj_run.png'].flatMap(name => [null, 'high', 'low'].map(mode => [name, mode])),
  ...['sj_burrow', 'sj_escape'].flatMap(name => ['fast', 'slow'].map(mode => [name, mode])),
];

test('all 32 obstacle plans can be cleared with the reference inputs and actual exported masks', () => {
  assert.equal(encounters.length, 32);
  for (const [name, mode] of encounters) {
    for (const slot of [8, 20]) {
      for (const hz of [30, 60, 120]) {
        const game = engine(); spawnCase(game, name, mode, slot);
        let jumped = false;
        const requiresJump = game.obstacleRequiresJump;
        for (let frame = 0; frame < 3 * hz; frame++) {
          const speed = 420 * game.speedMultiplier;
          let target = 60 + speed * 0.30;
          if (['hsucat.png', 'chicken.png'].includes(name)) target = (manifest.player.width - game.obstacle.width) / 2 + speed * 0.35;
          if (name === 'hsucat_crouch.png') target = 95 + speed * 0.12;
          if (requiresJump && !jumped && game.obstacle.x <= game.playerX + target) { game.jump(); jumped = true; }
          game.update(1 / hz);
          assert.equal(game.gameOver, false, `${name}/${mode} slot=${slot} hz=${hz} collided x=${game.obstacle.x}`);
          if (bonus(game) >= 10) break;
        }
        assert.equal(jumped, requiresJump, `${name}/${mode} jump decision`);
        assert.equal(bonus(game), 10, `${name}/${mode} slot=${slot} hz=${hz} bonus`);
      }
    }
  }
});

test('all-high and mixed jumping groups clear safely and award ten per animal', () => {
  for (const count of [2, 3]) {
    for (const allHigh of [true, false]) {
      for (const slot of [8, 20]) {
        for (const hz of [30, 60, 120]) {
          const game = engine(); game.elapsed = slot * 25; game.score = Math.floor(game.elapsed);
          const rolls = Array.from({ length: count }, (_, index) => [allHigh || index === 0 ? 0 : 0.5, 0.5]).flat();
          game.random = () => rolls.length ? rolls.shift() : 0.9;
          const members = game.spawnObstacle(count === 2 ? 'sj_pair' : 'sj_triple').members;
          let jumped = false;
          for (let frame = 0; frame < 3 * hz; frame++) {
            if (!allHigh && !jumped && game.obstacle.x <= game.playerX + 60 + 420 * game.speedMultiplier * 0.30) { game.jump(); jumped = true; }
            game.update(1 / hz);
            assert.equal(game.gameOver, false, `group=${count} high=${allHigh} slot=${slot} hz=${hz}`);
            if (bonus(game) >= count * 10) break;
          }
          assert.equal(bonus(game), count * 10);
          assert.ok(members.every(member => member.passed));
        }
      }
    }
  }
});
