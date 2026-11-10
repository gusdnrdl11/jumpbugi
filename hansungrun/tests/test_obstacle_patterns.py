"""두 캐릭터 지상·비행형과 회피 가능한 패턴의 실제 마스크·물리 검사."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
if __package__ and __package__.startswith('hansungrun.'):
    from .. import config, backend
    from ..main import HansungRun
else:
    import config, backend
    from main import HansungRun


class ObstaclePatternTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = HansungRun(Path(directory.name) / 'score.txt')

    def test_both_characters_have_four_matching_animation_masks(self):
        for name in config.CHICKEN_TYPES:
            frames = self.app.view.obstacle_frames[name]
            masks = self.app.view.obstacle_frame_masks[name]
            self.assertEqual(len(frames), 4)
            self.assertEqual(len(masks), 4)
            self.assertEqual(len({frame.get_size() for frame in frames}), 1)
            self.assertGreaterEqual(len({pygame.image.tobytes(frame, 'RGBA') for frame in frames}), 3)
            self.assertTrue(all(mask.count() for mask in masks))
            self.app.state.spawn_obstacle(name)
            for index in range(4):
                self.app.state.obstacle_animation_tick = index * config.OBSTACLE_FRAME_TICKS
                self.assertEqual(self.app.state.obstacle_frame_index, index)

    def test_all_animated_chickens_unlock_after_first_spring_and_stay_unlocked(self):
        state = self.app.state
        def select(pool):
            return next((p for p in pool if isinstance(p, tuple) and p[0] in config.CHICKEN_TYPES), pool[0])
        with patch.object(backend.random, 'choice', side_effect=select) as choose:
            for elapsed, enabled in ((0, False), (30, False), (59.999, False), (60, True),
                                     (120, True), (180, True), (239.999, True),
                                     (240, True), (270, True), (299.999, True), (300, True),
                                     (480, True), (540, True)):
                state.background_elapsed = elapsed
                state.pattern_queue = []
                state.spawn_obstacle()
                self.assertEqual(state.obstacle_name in config.CHICKEN_TYPES, enabled)
                available = {kind for pattern in choose.call_args.args[0] for kind in pattern}
                self.assertEqual(available.intersection(config.CHICKEN_TYPES),
                                 set(config.CHICKEN_TYPES) if enabled else set())
        self.app.reset()
        self.assertFalse(state.obstacle_is_flying)
        self.assertEqual(state.pattern_queue, [])
        self.assertFalse(state.chicken_obstacles_enabled)

    def test_first_spring_filters_all_chickens_but_second_spring_preserves_them(self):
        state = self.app.state
        state.background_elapsed = 30
        state.pattern_queue = list(config.CHICKEN_TYPES) + ['sangjji.png']
        state.spawn_obstacle()
        self.assertEqual(state.obstacle_name, 'sangjji.png')
        self.assertEqual(state.pattern_queue, [])
        state.pattern_queue = list(config.CHICKEN_TYPES)
        state.spawn_obstacle()
        self.assertNotIn(state.obstacle_name, config.CHICKEN_TYPES)
        state.background_elapsed = 240
        state.pattern_queue = list(config.CHICKEN_TYPES)
        for kind in config.CHICKEN_TYPES:
            state.spawn_obstacle()
            self.assertEqual(state.obstacle_name, kind)

    def test_first_spring_random_patterns_only_use_static_images(self):
        state = self.app.state
        for second in range(60):
            state.background_elapsed = second
            for _ in range(20):
                state.spawn_obstacle()
                self.assertIn(state.obstacle_name, config.OBSTACLE_FILES)
                self.assertTrue(all(kind not in config.CHICKEN_TYPES for kind in state.pattern_queue))

    def test_flying_clears_every_grounded_pose_but_can_hit_a_jump(self):
        state = self.app.state
        for name in config.CHICKEN_TYPES[2:]:
            self.app.reset()
            state.spawn_obstacle(name)
            for player_frame in range(4):
                state.animation_tick = player_frame * config.RUN_FRAME_TICKS
                for bird_frame in range(4):
                    state.obstacle_animation_tick = bird_frame * config.OBSTACLE_FRAME_TICKS
                    for x in range(-state.obstacle_size[0], state.player_size[0] + 1):
                        state.obstacle_x = x
                        self.assertFalse(state.collides_with_obstacle())
            state.obstacle_x = 160
            state.jump()
            for _ in range(100):
                self.app.update(1 / 120)
                if state.game_over:
                    break
            self.assertTrue(state.game_over)

    def test_all_patterns_have_a_safe_run_jump_solution_at_multiple_speeds(self):
        for stage in (2, 4, 10, 20):
            for hz in (30, 60, 120):
                for pattern in config.GROUND_PATTERNS + config.SUMMER_PATTERNS:
                    with self.subTest(stage=stage, hz=hz, pattern=pattern):
                        self.app.reset()
                        state = self.app.state
                        state.background_elapsed = stage * 30
                        state.pattern_queue = list(pattern)
                        state.spawn_obstacle()
                        cleared = 0
                        for _ in range(15 * hz):
                            speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier
                            if (not state.obstacle_is_flying and not state.is_jumping
                                    and state.obstacle_x <= 60 + speed * 0.30):
                                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                            self.app.handle_events()
                            old_x = state.obstacle_x
                            self.app.update(1 / hz)
                            self.assertFalse(state.game_over)
                            if state.obstacle_x > old_x:
                                cleared += 1
                                approach = (state.obstacle_x - state.player_size[0]) / (
                                    config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier)
                                self.assertGreaterEqual(approach + 1e-9, config.OBSTACLE_RECOVERY_SECONDS)
                                if cleared == len(pattern):
                                    break
                        self.assertEqual(cleared, len(pattern))
                        self.assertEqual(state.score, int(state.survival_elapsed + 1e-9) + 10 * len(pattern))

    def test_animation_stops_on_pause_and_game_over_and_assets_are_cached(self):
        state = self.app.state
        state.spawn_obstacle('chicken_white_flying')
        with patch.object(pygame.image, 'load', side_effect=AssertionError('이미지 재로딩')):
            self.app.update(0.1)
            self.app.draw()
            for flag in ('paused', 'game_over'):
                setattr(state, flag, True)
                before = (state.obstacle_x, state.obstacle_animation_tick)
                self.app.update(2)
                self.app.draw()
                self.assertEqual((state.obstacle_x, state.obstacle_animation_tick), before)
                setattr(state, flag, False)


if __name__ == '__main__':
    unittest.main()
