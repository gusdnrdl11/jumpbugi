"""실제 마스크·물리로 점프 가능 구간과 연속 자동 플레이를 검증한다.

실행: python -B tools/verify_difficulty.py
화면 없는 자동 입력이며 사람의 반응 속도나 재미를 평가하지 않는다.
"""
import os
import argparse
import json
import random
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame
import backend
import config
from frontend import GameView
from main import JumpBugi


def evaluate():
    pygame.init()
    try:
        view = GameView()
        with tempfile.TemporaryDirectory() as directory:
            def new_state():
                return backend.GameState(
                    view.player_image.get_size(),
                    {name: image.get_size() for name, image in view.obstacle_images.items()},
                    len(view.run_frames), view.background_width, Path(directory) / 'score.txt',
                    player_masks=view.player_masks, obstacle_masks=view.obstacle_masks,
                    obstacle_frame_masks=view.obstacle_frame_masks)

            windows = {}
            report = []
            # 2픽셀 간격으로 도약부터 장애물 통과 또는 충돌까지 실제 계산한다.
            for stage in range(21):
                windows[stage] = {}
                factor = (1 + config.SPEED_INCREASE_RATIO) ** stage
                row = {'seconds': stage * config.DAY_NIGHT_INTERVAL,
                       'multiplier': round(factor, 4), 'obstacles': {}}
                for name in view.obstacle_images:
                    safe = []
                    for distance in range(80, 401, 2):
                        state = new_state()
                        state.background_elapsed = stage * config.DAY_NIGHT_INTERVAL
                        state.spawn_obstacle(name)
                        state.obstacle_x = distance
                        if not state.obstacle_is_flying:
                            state.jump()
                        for _ in range(240):
                            state.update(1 / 120)
                            if state.game_over or state.score >= config.PASS_BONUS:
                                break
                        if state.score >= config.PASS_BONUS and not state.game_over:
                            safe.append(distance)
                    windows[stage][name] = safe
                    row['obstacles'][name] = {
                        'action': 'stay_grounded' if name.endswith('_flying') else 'jump',
                        'min_x': min(safe) if safe else None,
                        'max_x': max(safe) if safe else None,
                        'window_ms': round((max(safe) - min(safe)) /
                                           (config.OBSTACLE_SPEED * config.PHYSICS_HZ * factor) * 1000) if safe else 0}
                report.append(row)

            plays = []
            for hz in (30, 60, 120):
                generator = random.Random(20261111)
                with patch.object(backend.random, 'choice', side_effect=generator.choice):
                    app = JumpBugi(Path(directory) / 'continuous_score.txt')
                    app.reset()  # 난이도 검사는 첫 실행 연출 뒤의 실제 플레이만 대상으로 한다.
                    state = app.state
                    jumps = 0
                    for _ in range(600 * hz):
                        stage = min(20, int((state.background_elapsed + 1e-9) // config.DAY_NIGHT_INTERVAL))
                        safe = windows[stage][state.obstacle_name]
                        target = (min(safe) + max(safe)) / 2 if safe else 400
                        if (not state.obstacle_is_flying and not state.is_jumping
                                and not state.passed and state.obstacle_x <= target):
                            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                            jumps += 1
                        app.handle_events()
                        app.update(1 / hz)
                        if _ % hz == 0 or state.game_over:
                            app.draw()
                        if state.game_over:
                            break
                    plays.append({'hz': hz, 'survived_seconds': round(state.survival_elapsed, 3),
                                  'game_over': state.game_over, 'jumps': jumps, 'score': state.score,
                                  'obstacle': state.obstacle_name})
            return {'mask_inset_ratio': config.OBSTACLE_MASK_INSET_RATIO,
                    'method': '120Hz single jumps, 2px search; seeded continuous bot at 30/60/120Hz',
                    'stages': report, 'continuous_play': plays}
    finally:
        pygame.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = evaluate()
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result['continuous_play'], ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
