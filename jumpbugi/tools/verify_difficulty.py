"""실제 마스크·물리로 각 장애물 동작의 회피 구간과 연속 플레이를 검증한다.

실행: python -B tools/verify_difficulty.py --output output/prototype-difficulty-report.json
자동 입력의 이론적 회피 검사이며 사람의 반응 속도나 재미를 평가하지 않는다.
"""
import os
import argparse
import itertools
import json
import random
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
if __package__ and '.' in __package__:
    from ..desktop_prototype import backend, config
    from ..desktop_prototype.frontend import GameView
    from ..desktop_prototype.main import JumpBugi
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from desktop_prototype import backend
    from desktop_prototype import config
    from desktop_prototype.frontend import GameView
    from desktop_prototype.main import JumpBugi


@dataclass(frozen=True)
class Plan:
    name: str
    variants: tuple = ()

    @property
    def key(self):
        suffix = ','.join('ground' if value is None else str(value) for value in self.variants)
        return f'{self.name}:{suffix}' if suffix else self.name


@contextmanager
def seeded_random(seed):
    """장애물 종류와 동작·시점의 모든 난수를 같은 시드로 재현한다."""
    generator = random.Random(seed)
    with patch.object(backend.random, 'choice', side_effect=generator.choice), \
         patch.object(backend.random, 'random', side_effect=generator.random), \
         patch.object(backend.random, 'uniform', side_effect=generator.uniform):
        yield


def plans_for_slot(slot):
    """명시적 이름으로 해금을 우회하지 않고 해당 슬롯에서 허용한 동작을 나열한다."""
    plans = [Plan(name, (variant,)) for name in config.WAVE_IMAGE_FILES
             for variant in ((None, 'high', 'near', 'low')
                             if slot >= config.WAVE_JUMP_UNLOCK_SLOT else (None,))]
    plans += [Plan(name, (variant,)) for name in config.SJ_SINGLE_JUMP_TYPES
              if name == 'sj.png' or slot >= config.SJ_UNLOCK_SLOT
              for variant in ((None, 'high', 'low')
                              if slot >= config.SJ_JUMP_UNLOCK_SLOT else (None,))]
    if slot >= config.CHICKEN_UNLOCK_SLOT:
        plans += [Plan(name, (level,)) for name in config.CHICKEN_TYPES
                  if name.endswith('_flying') for level in config.FLYING_LEVELS]
        plans += [Plan(name) for name in config.CHICKEN_TYPES if name.endswith('_ground')]
    if slot >= config.HSUCAT_UNLOCK_SLOT:
        plans += [Plan('hsucat_run.png', (mode,)) for mode in config.HSUCAT_RUN_MODES
                  if mode not in config.HSUCAT_RUN_JUMP_HEIGHTS or slot >= config.WAVE_JUMP_UNLOCK_SLOT]
        plans += [Plan('hsucat_crouch.png'), Plan('hsucat_book.png')]
    if slot >= config.SJ_UNLOCK_SLOT:
        plans += [Plan('sj_burrow', (timing,)) for timing in config.SJ_BURROW_PROFILES]
    if slot >= config.SJ_ESCAPE_UNLOCK_SLOT:
        plans += [Plan('sj_escape', (timing,)) for timing in config.SJ_ESCAPE_PROFILES]
    if slot >= config.SJ_GROUP_UNLOCK_SLOT:
        plans += [Plan(name, variants) for name, count in zip(config.SJ_CLUSTER_TYPES, (2, 3))
                  for variants in itertools.product((None, 'low', 'high'), repeat=count)]
    return plans


def spawn_plan(state, plan, slot, distance=None, *, jitter=12.5):
    """동작을 한 번 고정한 뒤 실제 spawn 함수로 그리기·충돌 상태를 함께 만든다."""
    state.background_elapsed = slot * config.DAY_NIGHT_INTERVAL
    name = plan.name
    variants = plan.variants
    rolls = []
    if (name in config.SJ_SINGLE_JUMP_TYPES + config.SJ_CLUSTER_TYPES
            and slot >= config.SJ_JUMP_UNLOCK_SLOT):
        rolls = [0.0 if value == 'high' else config.SJ_HOP_PROBABILITY * 0.75
                 if value == 'low' else 1.0 for value in variants]
    elif name in config.WAVE_IMAGE_FILES and slot >= config.WAVE_JUMP_UNLOCK_SLOT:
        variant, = variants
        rolls = [1.0] if variant is None else [
            0.0, (tuple(config.WAVE_JUMP_HEIGHTS).index(variant) + 0.5) / len(config.WAVE_JUMP_HEIGHTS)]
    elif name.endswith('_flying'):
        rolls = [(config.FLYING_LEVELS.index(variants[0]) + 0.5) / len(config.FLYING_LEVELS)]
    elif name == 'hsucat_run.png':
        modes = tuple(mode for mode in config.HSUCAT_RUN_MODES
                      if mode not in config.HSUCAT_RUN_JUMP_HEIGHTS or slot >= config.WAVE_JUMP_UNLOCK_SLOT)
        rolls = [(modes.index(variants[0]) + 0.5) / len(modes)]
    elif name in config.SJ_HOLE_TYPES:
        profiles = config.SJ_BURROW_PROFILES if name == 'sj_burrow' else config.SJ_ESCAPE_PROFILES
        rolls = [(tuple(profiles).index(variants[0]) + 0.5) / len(profiles)]
    with patch.object(backend.random, 'random', side_effect=rolls), \
         patch.object(backend.random, 'uniform', return_value=jitter):
        state.spawn_obstacle(name)
    if distance is not None:
        state.obstacle_x = float(distance)
        if state.wave_jump is not None:
            state.obstacle_y = state.obstacle_ground_y + state.wave_jump.y_offset(state.obstacle_x)


def pass_bonus(state):
    return state.score - int(state.survival_elapsed + 1e-9) * config.SURVIVAL_POINTS_PER_SECOND


def safe_runs(distances, step):
    """안전 거리 사이에 실패 구간이 있으면 서로 다른 구간으로 기록한다."""
    runs = []
    for distance in distances:
        if runs and distance == runs[-1][1] + step:
            runs[-1][1] = distance
        else:
            runs.append([distance, distance])
    return runs


def jump_target(state):
    speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier
    if state.obstacle_name in config.WAVE_IMAGE_FILES:
        return (state.player_size[0] - state.obstacle_size[0]) / 2 + speed * 0.35
    if state.obstacle_name == 'hsucat_crouch.png':
        return 95 + speed * 0.12
    return 60 + speed * 0.30


def evaluate(*, slots=(0, 2, 4, 6, 7, 8, 15, 16, 64), search_step=4,
             continuous_seconds=600, frame_rates=(30, 60, 120)):
    pygame.init()
    try:
        view = GameView()
        with tempfile.TemporaryDirectory() as directory, seeded_random(20261120):
            def new_state():
                return backend.GameState(
                    view.player_image.get_size(),
                    {name: image.get_size() for name, image in view.obstacle_images.items()},
                    len(view.run_frames), view.background_width, Path(directory) / 'score.txt',
                    player_masks=view.player_masks, obstacle_masks=view.obstacle_masks,
                    obstacle_frame_masks=view.obstacle_frame_masks)

            report = []
            failures = []
            # 검색점마다 같은 동작을 고정하여 난수로 서로 다른 회피 구간이 섞이지 않게 한다.
            for slot in slots:
                row = {'total_slots_passed': slot, 'current_slot': slot % len(config.BACKGROUND_FILES),
                       'season_cycle_count': slot // len(config.BACKGROUND_FILES),
                       'seconds': slot * config.DAY_NIGHT_INTERVAL, 'plans': {}}
                for plan in plans_for_slot(slot):
                    safe = []
                    factor = 0.0
                    expected_bonus = 0
                    requires_jump = False
                    for distance in range(80, 401, search_step):
                        state = new_state()
                        spawn_plan(state, plan, slot, distance)
                        factor = state.speed_multiplier
                        expected_bonus = state.obstacle_pass_bonus
                        requires_jump = state.obstacle_requires_jump
                        if requires_jump:
                            state.jump()
                        for _ in range(3 * 120):
                            state.update(1 / 120)
                            if state.game_over or pass_bonus(state) >= expected_bonus:
                                break
                        if pass_bonus(state) == expected_bonus and not state.game_over:
                            safe.append(distance)
                    runs = safe_runs(safe, search_step)
                    longest = max(runs, key=lambda run: run[1] - run[0]) if runs else None
                    row['plans'][plan.key] = {
                        'action': 'jump' if requires_jump else 'stay_grounded',
                        'pass_points': expected_bonus, 'safe_x_runs': runs,
                        'longest_window_ms': round((longest[1] - longest[0]) /
                                                   (config.OBSTACLE_SPEED * config.PHYSICS_HZ * factor)
                                                   * 1000) if longest else 0}
                    if not runs:
                        failures.append({'slot': slot, 'plan': plan.key, 'reason': 'no_safe_input'})
                state = new_state()
                state.background_elapsed = slot * config.DAY_NIGHT_INTERVAL
                row['multiplier'] = round(state.speed_multiplier, 6)
                report.append(row)

            plays = []
            for hz in frame_rates:
                with seeded_random(20261120):
                    app = JumpBugi(Path(directory) / 'continuous_score.txt')
                    app.reset()
                    state = app.state
                    jumps, passes = 0, 0
                    slots_seen = set()
                    last_was_airborne = False
                    landings = 0
                    for tick in range(round(continuous_seconds * hz)):
                        slots_seen.add(state.total_slots_passed)
                        if (state.obstacle_requires_jump and not state.is_jumping
                                and not state.passed and state.obstacle_x <= jump_target(state)):
                            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                            jumps += 1
                        app.handle_events()
                        old_x = state.obstacle_x
                        app.update(1 / hz)
                        if last_was_airborne and not state.is_jumping:
                            landings += 1
                        last_was_airborne = state.is_jumping
                        if state.obstacle_x > old_x:
                            passes += 1
                        if tick % hz == 0 or state.game_over:
                            app.draw()
                        if state.game_over:
                            break
                    result = {'hz': hz, 'survived_seconds': round(state.survival_elapsed, 3),
                              'game_over': state.game_over, 'jumps': jumps, 'landings': landings,
                              'encounters_passed': passes, 'score': state.score,
                              'pass_bonus': pass_bonus(state), 'obstacle': state.obstacle_name,
                              'slots_seen': sorted(slots_seen), 'final_multiplier': state.speed_multiplier}
                    plays.append(result)
                    if state.game_over:
                        failures.append({'hz': hz, 'reason': 'continuous_collision',
                                         'seconds': result['survived_seconds'], 'obstacle': state.obstacle_name})
            return {'prototype': 'HansungRun Pygame Prototype 1.0',
                    'report_date': date.today().isoformat(),
                    'slot_seconds': config.DAY_NIGHT_INTERVAL,
                    'screen_size': list(config.SCREEN_SIZE),
                    'mask_inset_ratio': config.OBSTACLE_MASK_INSET_RATIO,
                    'configuration': {
                        'obstacle_speed': config.OBSTACLE_SPEED,
                        'background_speed': config.BACKGROUND_SPEED,
                        'physics_hz': config.PHYSICS_HZ,
                        'jump_speed': config.JUMP_SPEED,
                        'gravity': config.GRAVITY,
                        'collision_alpha_threshold': config.COLLISION_ALPHA_THRESHOLD,
                        'early_speed_increase': config.EARLY_SPEED_INCREASE,
                        'mid_speed_increase': config.MID_SPEED_INCREASE,
                        'max_speed_multiplier': config.MAX_SPEED_MULTIPLIER,
                        'cycle_recovery_seconds': config.CYCLE_RECOVERY_SECONDS,
                        'min_recovery_time': config.MIN_RECOVERY_TIME,
                        'hard_pattern_probabilities': config.HARD_PATTERN_PROBABILITIES,
                        'pattern_chain_probabilities': config.PATTERN_CHAIN_PROBABILITIES},
                    'method': f'120 Hz {search_step}px deterministic per-plan search; actual event bot at '
                              f'{"/".join(map(str, frame_rates))} Hz; jitter fixed at 12.5 px',
                    'limits': ['이론적 자동 회피이며 사람의 반응 속도·재미를 입증하지 않음',
                               '안전 구간은 검사한 이산 입력과 현재 설정에 해당함',
                               '상찌 출발 시점의 무작위 흔들림은 중앙값으로 고정함'],
                    'stages': report, 'continuous_play': plays, 'failures': failures,
                    'passed': not failures}
    finally:
        pygame.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--continuous-seconds', type=float, default=600)
    args = parser.parse_args()
    result = evaluate(continuous_seconds=args.continuous_seconds)
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'passed': result['passed'], 'continuous_play': result['continuous_play'],
                          'failures': result['failures']}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['passed'] else 1)
