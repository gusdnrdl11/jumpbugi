"""한성캣의 계절 해금·크기·애니메이션과 실제 점프 회피 검사."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
if __package__ and __package__.startswith('jumpbugi.'):
    from .. import backend, config
    from ..main import JumpBugi
else:
    import backend, config
    from main import JumpBugi


class HsucatObstacleTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = JumpBugi(Path(directory.name) / 'score.txt')
        self.app.reset()

    def test_first_autumn_unlocks_every_cat_and_later_springs_keep_them(self):
        state = self.app.state
        interval = config.DAY_NIGHT_INTERVAL
        for elapsed, enabled in ((0, False), (interval, False), (2 * interval - 0.001, False),
                                 (2 * interval, False), (3 * interval, False), (4 * interval - 0.001, False),
                                 (4 * interval, True),
                                 (6 * interval, True), (8 * interval - 0.001, True), (8 * interval, True),
                                 (9 * interval, True), (16 * interval, True), (18 * interval, True)):
            with self.subTest(elapsed=elapsed):
                state.background_elapsed = elapsed
                state.pattern_queue = []
                with patch.object(backend.random, 'choice', side_effect=lambda pool: pool[0]) as choose:
                    state.spawn_obstacle()
                available = {kind for pattern in state.available_patterns for kind in pattern}
                self.assertEqual(state.hsucat_obstacles_enabled, enabled)
                self.assertEqual(available.intersection(config.HSUCAT_TYPES),
                                 set(config.HSUCAT_TYPES) if enabled else set())

    def test_first_spring_and_summer_clean_locked_cats_from_queue_and_reset_locks_again(self):
        state = self.app.state
        interval = config.DAY_NIGHT_INTERVAL
        for elapsed in (interval, 2 * interval - 0.001, 2 * interval, 3 * interval, 4 * interval - 0.001):
            with self.subTest(elapsed=elapsed):
                state.background_elapsed = elapsed
                state.pattern_queue = list(config.HSUCAT_TYPES) + ['sj.png']
                state.spawn_obstacle()
                self.assertEqual(state.obstacle_name, 'sj.png')
                self.assertEqual(state.pattern_queue, [])
        state.background_elapsed = len(config.BACKGROUND_FILES) * interval
        state.pattern_queue = list(config.HSUCAT_TYPES)
        for name in config.HSUCAT_TYPES:
            state.spawn_obstacle()
            self.assertEqual(state.obstacle_name, name)
        self.app.reset()
        self.assertFalse(state.hsucat_obstacles_enabled)
        self.assertIn(state.obstacle_name, config.OBSTACLE_FILES)
        self.assertEqual(state.pattern_queue, [])

    def test_every_new_cat_is_reachable_by_random_pattern_choice(self):
        state = self.app.state
        state.background_elapsed = (config.HSUCAT_UNLOCK_SLOT * config.DAY_NIGHT_INTERVAL)
        for pattern in config.HSUCAT_PATTERNS:
            with self.subTest(pattern=pattern):
                state.pattern_queue = []
                with patch.object(backend.random, 'choice', return_value=pattern) as choose, \
                     patch.object(backend.random, 'random', side_effect=[1.0, 0.0] + [1.0] * 20):
                    state.spawn_obstacle()
                self.assertIn(pattern, choose.call_args.args[0])
                actual = [state.obstacle_name]
                for _ in pattern[1:]:
                    state.spawn_obstacle()
                    actual.append(state.obstacle_name)
                self.assertEqual(tuple(actual), pattern)
        available = {kind for pattern in config.HSUCAT_PATTERNS for kind in pattern}
        self.assertTrue(set(config.HSUCAT_TYPES).issubset(available))

    def test_large_cat_replaces_the_still_image_with_one_cached_yawn_animation(self):
        image = self.app.view.obstacle_images['hsucat_crouch.png']
        frames = self.app.view.obstacle_frames['hsucat_crouch.png']
        self.assertEqual(image.get_size(), config.HSUCAT_GIANT_SIZE)
        self.assertGreater(image.get_width(), self.app.view.obstacle_images['hsucat.png'].get_width())
        self.assertIs(image, frames[0])
        self.assertEqual(len(frames), config.HSUCAT_GIANT_FRAME_COUNT)
        self.assertEqual(config.HSUCAT_GIANT_IMAGE_FILE, 'hsucat_yawn.png')
        self.assertEqual(len(self.app.view.obstacle_frame_masks['hsucat_crouch.png']),
                         config.HSUCAT_GIANT_FRAME_COUNT)
        self.assertNotIn('hsucat_sleepy.png', self.app.view.obstacle_frames)
        self.assertNotIn('hsucat_yawn.png', self.app.view.obstacle_frames)

    def test_running_sheet_has_four_distinct_frames_with_matching_masks(self):
        name = 'hsucat_run.png'
        frames = self.app.view.obstacle_frames[name]
        masks = self.app.view.obstacle_frame_masks[name]
        self.assertEqual(len(frames), 8)
        self.assertEqual(len(masks), 8)
        self.assertEqual(len({frame.get_size() for frame in frames}), 1)
        self.assertEqual(frames[0].get_height(), 120)
        self.assertGreaterEqual(len({pygame.image.tobytes(frame, 'RGBA') for frame in frames}), 3)
        state = self.app.state
        with patch.object(backend.random, 'random', return_value=1.0):
            state.spawn_obstacle(name)
        for index, (frame, mask) in enumerate(zip(frames[:4], masks[:4])):
            with self.subTest(frame=index):
                self.assertEqual(mask.get_size(), frame.get_size())
                self.assertGreater(mask.count(), 0)
                state.obstacle_animation_tick = index * config.OBSTACLE_FRAME_TICKS
                self.assertEqual(state.obstacle_frame_index, index)
                with patch.object(self.app.view, 'screen', wraps=self.app.view.screen) as screen:
                    self.app.draw()
                self.assertIs(screen.blit.call_args_list[2].args[0], frame)

    @patch.object(backend.random, 'random', return_value=1.0)
    def test_grounded_player_collides_with_each_new_cat(self, _random):
        state = self.app.state
        for name in config.HSUCAT_TYPES:
            with self.subTest(name=name):
                self.app.reset()
                state.spawn_obstacle(name)
                offset = (config.HSUCAT_RUN_GROUND_OFFSET if name == 'hsucat_run.png'
                          else config.OBSTACLE_GROUND_OFFSET)
                self.assertEqual(state.obstacle_y + state.obstacle_size[1],
                                 config.SCREEN_SIZE[1] + offset)
                contact = None
                for x in range(state.player_size[0], -state.obstacle_size[0], -1):
                    state.obstacle_x = x
                    if state.collides_with_obstacle():
                        contact = x
                        break
                self.assertIsNotNone(contact)
                state.update_step(0)
                self.assertTrue(state.game_over)

    @patch.object(backend.random, 'random', return_value=1.0)
    def test_each_new_cat_has_a_timed_jump_at_multiple_speeds_and_frame_rates(self, _random):
        for name in config.HSUCAT_TYPES:
            for stage in (4, 6, 10, 20):
                seconds = stage * config.DAY_NIGHT_INTERVAL
                for hz in (30, 60, 120):
                    with self.subTest(name=name, seconds=seconds, hz=hz):
                        self.app.reset()
                        state = self.app.state
                        state.background_elapsed = seconds
                        state.spawn_obstacle(name)
                        for _ in range(3 * hz):
                            speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier
                            # 넓은 엎드린 캣은 몸 전체를 넘도록 다른 지상형보다 늦게 뛴다.
                            target = (95 + speed * 0.12 if name == 'hsucat_crouch.png'
                                      else 60 + speed * 0.30)
                            if not state.is_jumping and state.obstacle_x <= target:
                                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                            self.app.handle_events()
                            self.app.update(1 / hz)
                            self.assertFalse(state.game_over)
                            if state.score >= config.PASS_BONUS:
                                break
                        self.assertGreaterEqual(state.score, config.PASS_BONUS)

    def test_pause_game_over_and_reset_reuse_all_cat_assets(self):
        state = self.app.state
        with patch.object(pygame.image, 'load', side_effect=AssertionError('이미지 재로딩')):
            for name in config.HSUCAT_TYPES:
                state.spawn_obstacle(name)
                self.app.update(0.1)
                self.app.draw()
                for flag in ('paused', 'game_over'):
                    setattr(state, flag, True)
                    before = (state.obstacle_x, state.obstacle_animation_tick)
                    self.app.update(2)
                    self.app.draw()
                    self.assertEqual((state.obstacle_x, state.obstacle_animation_tick), before)
                    setattr(state, flag, False)
                self.app.reset()
                self.app.draw()


if __name__ == '__main__':
    unittest.main()
