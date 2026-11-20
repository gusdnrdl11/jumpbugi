"""생존 득점·통과 보너스·최고점수 저장과 배경 전환 가속 검사."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
if __package__ and __package__.startswith('jumpbugi.'):
    from ..backend import GameState
    from ..main import JumpBugi
    from ..difficulty import speed_multiplier_for_slot
    from .. import config
else:
    from backend import GameState
    from main import JumpBugi
    from difficulty import speed_multiplier_for_slot
    import config


class ScoringSpeedTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.record = Path(directory.name) / 'score.txt'
        sizes = {name: (80, config.OBSTACLE_HEIGHTS[name]) for name in config.OBSTACLE_FILES}
        self.state = GameState((90, 120), sizes, 4, 960, self.record,
                               player_masks=[pygame.Mask((90, 120), fill=True) for _ in range(4)],
                               obstacle_masks={name: pygame.Mask(size, fill=True) for name, size in sizes.items()})
        self.state.obstacle_y = -1000

    def test_whole_seconds_and_bonus_are_additive(self):
        state = self.state
        for _ in range(119):
            state.update(1 / 120)
        self.assertEqual(state.score, 0)
        state.update(1 / 120)
        self.assertEqual(state.score, 1)
        state.obstacle_x = -state.obstacle_size[0]
        state.update(1 / 120)
        self.assertEqual(state.score, 11)
        state.obstacle_y = -1000
        for _ in range(119):
            state.update(1 / 120)
        self.assertEqual(state.score, 12)

    def test_pause_game_over_and_restart(self):
        state = self.state
        state.update(29.5)
        self.assertEqual(state.score, 29)
        frozen = (state.survival_elapsed, state.background_elapsed, state.score, state.speed_multiplier)
        for flag in ('paused', 'game_over'):
            setattr(state, flag, True)
            state.update(60)
            self.assertEqual((state.survival_elapsed, state.background_elapsed, state.score, state.speed_multiplier), frozen)
            setattr(state, flag, False)
        state.update(0.5)
        self.assertEqual(state.score, 30)
        stage = int((state.background_elapsed + 1e-9) // config.DAY_NIGHT_INTERVAL)
        self.assertAlmostEqual(state.speed_multiplier, speed_multiplier_for_slot(stage))
        state.stop()
        self.assertEqual(self.record.read_text(), '30')
        state.reset()
        self.assertEqual((state.score, state.survival_elapsed, state.speed_multiplier), (0, 0, 1))

    def test_speed_boundaries_and_configured_scroll_speeds(self):
        state = self.state
        interval = config.DAY_NIGHT_INTERVAL
        for seconds, slot in ((interval - 0.001, 0), (interval, 1),
                              (2 * interval - 0.001, 1), (2 * interval, 2),
                              (6 * interval, 6), (10 * interval, 10),
                              (16 * interval, 16), (1000 * interval, 1000)):
            with self.subTest(seconds=seconds):
                factor = speed_multiplier_for_slot(slot)
                state.background_elapsed = seconds
                self.assertAlmostEqual(state.speed_multiplier, factor)
                state.background_x = 0
                state.obstacle_x = 480
                state.update_step(1)
                self.assertAlmostEqual(state.background_x, -config.BACKGROUND_SPEED * factor)
                self.assertAlmostEqual(state.obstacle_x, 480 - config.OBSTACLE_SPEED * factor)

    def test_survival_points_are_frame_rate_independent(self):
        for hz in (30, 60, 120):
            with self.subTest(hz=hz):
                self.state.reset()
                self.state.obstacle_y = -1000
                self.state.obstacle_x = 100000
                for _ in range(hz * 61):
                    self.state.update(1 / hz)
                self.assertEqual(self.state.score, 61)
                stage = int((self.state.background_elapsed + 1e-9) // config.DAY_NIGHT_INTERVAL)
                self.assertAlmostEqual(self.state.speed_multiplier, speed_multiplier_for_slot(stage))

    def test_collision_saves_combined_score_and_then_stops_scoring(self):
        state = self.state
        state.update(2.25)
        state.obstacle_x = -state.obstacle_size[0]
        state.update(1 / 120)
        state.obstacle_x = 0
        state.obstacle_y = state.ground_y
        state.update(1 / 120)
        self.assertTrue(state.game_over)
        self.assertEqual(state.score, 12)
        self.assertEqual(self.record.read_text(), '12')
        state.update(100)
        self.assertEqual(state.score, 12)


class ScoringPersistenceTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.record = Path(directory.name) / 'high_score.txt'
        self.app = JumpBugi(self.record)
        self.app.reset()
        pygame.event.clear()

    def test_bonus_once_respawn_and_high_score_persistence(self):
        app = self.app
        self.assertEqual(app.state.high_score, 0)
        self.assertFalse(self.record.exists())
        app.state.obstacle_x = -app.view.obstacle_images[app.state.obstacle_name].get_width() + config.OBSTACLE_SPEED
        app.update()
        self.assertEqual((app.state.score, app.state.high_score), (10, 0))
        self.assertFalse(self.record.exists())
        app.update()
        self.assertEqual(app.state.score, 10)
        self.assertEqual(app.state.obstacle_x, app.state.obstacle_spawn_x)
        self.assertFalse(app.state.passed)
        # 실제 충돌로 판을 종료했을 때만 새 기록이 표시·저장된다.
        app.state.obstacle_x = 60
        app.update()
        self.assertTrue(app.state.game_over)
        self.assertEqual(app.state.high_score, 10)
        app.reset()
        self.assertEqual((app.state.score, app.state.high_score), (0, 10))
        self.assertEqual(JumpBugi(self.record).state.high_score, 10)
        app.state.score = 5
        app.state.record_high_score()
        self.assertEqual(self.record.read_text(), '10')
        app.state.score = 120
        app.state.record_high_score()
        self.assertEqual(JumpBugi(self.record).state.high_score, 120)
        self.assertFalse(self.record.with_suffix('.tmp').exists())

    def test_exit_records_score_once(self):
        for event in (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F4, mod=pygame.KMOD_CTRL),
                      pygame.event.Event(pygame.QUIT)):
            self.app.state.running = True
            self.app.state.score += 10
            pygame.event.post(event)
            self.app.handle_events()
            self.assertFalse(self.app.state.running)
            self.assertEqual(int(self.record.read_text()), self.app.state.score)


if __name__ == '__main__':
    unittest.main()
