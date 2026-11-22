"""상찌의 겨울 달리기·땅파기·밀집 무리와 화면·충돌·점프 검사."""
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
    from ..desktop_prototype import backend, config
    from ..desktop_prototype.main import JumpBugi
else:
    from desktop_prototype import backend, config
    from desktop_prototype.main import JumpBugi


class SjObstacleTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = JumpBugi(Path(directory.name) / 'score.txt')
        self.app.reset()
        pygame.event.clear()

    def test_first_winter_unlocks_running_and_burrowing_but_groups_wait_for_second_spring(self):
        state = self.app.state
        interval = config.DAY_NIGHT_INTERVAL
        for elapsed, enabled in ((0, False), (2 * interval, False), (4 * interval, False),
                                 (5 * interval, False), (6 * interval - 0.001, False), (6 * interval, True),
                                 (7 * interval, True), (8 * interval - 0.001, True), (8 * interval, True),
                                 (10 * interval, True), (16 * interval, True), (20 * interval, True)):
            with self.subTest(elapsed=elapsed):
                state.background_elapsed = elapsed
                state.pattern_queue = []
                with patch.object(backend.random, 'choice', side_effect=lambda pool: pool[0]) as choose:
                    state.spawn_obstacle()
                pool = state.available_patterns
                available = {kind for pattern in pool for kind in pattern}
                self.assertEqual(state.sj_obstacles_enabled, enabled)
                self.assertEqual(state.sj_groups_enabled, elapsed >= (config.SJ_GROUP_UNLOCK_SLOT * config.DAY_NIGHT_INTERVAL))
                self.assertEqual(state.sj_escape_enabled, elapsed >= (config.SJ_ESCAPE_UNLOCK_SLOT * config.DAY_NIGHT_INTERVAL))
                expected = {kind for kind in config.SJ_TYPES
                            if (kind not in config.SJ_CLUSTER_TYPES or elapsed >= (config.SJ_GROUP_UNLOCK_SLOT * config.DAY_NIGHT_INTERVAL))
                            and (kind != 'sj_escape' or elapsed >= (config.SJ_ESCAPE_UNLOCK_SLOT * config.DAY_NIGHT_INTERVAL))}
                self.assertEqual(available.intersection(config.SJ_TYPES),
                                 expected if enabled else set())

    def test_locked_queue_is_cleaned_and_reset_restores_first_spring(self):
        state = self.app.state
        interval = config.DAY_NIGHT_INTERVAL
        for elapsed in (0, 2 * interval, 4 * interval, 6 * interval - 0.001):
            with self.subTest(elapsed=elapsed):
                state.background_elapsed = elapsed
                state.pattern_queue = list(config.SJ_TYPES) + ['sj.png']
                state.spawn_obstacle()
                self.assertEqual(state.obstacle_name, 'sj.png')
                self.assertEqual(state.pattern_queue, [])
        for elapsed in (6 * interval, 7 * interval, 8 * interval - 0.001):
            with self.subTest(elapsed=elapsed):
                state.background_elapsed = elapsed
                state.pattern_queue = list(config.SJ_CLUSTER_TYPES) + ['sj_escape', 'sj_run.png']
                state.spawn_obstacle()
                self.assertEqual(state.obstacle_name, 'sj_run.png')
                self.assertIsNone(state.wave_jump)
                self.assertEqual(state.pattern_queue, [])
        state.background_elapsed = (config.SJ_GROUP_UNLOCK_SLOT * config.DAY_NIGHT_INTERVAL)
        state.pattern_queue = list(config.SJ_TYPES)
        for name in config.SJ_TYPES:
            state.spawn_obstacle()
            self.assertEqual(state.obstacle_name, name)
        self.app.reset()
        self.assertFalse(state.sj_obstacles_enabled)
        self.assertEqual(state.background_elapsed, 0)
        self.assertEqual(state.pattern_queue, [])
        self.assertIn(state.obstacle_name, config.OBSTACLE_FILES)

    def test_automatic_basic_sj_becomes_a_random_pair_or_triple_from_second_spring(self):
        state = self.app.state
        interval = config.DAY_NIGHT_INTERVAL
        for elapsed in (0, 4 * interval, 6 * interval - 0.001,
                        6 * interval, 7 * interval, 8 * interval - 0.001):
            state.background_elapsed = elapsed
            state.pattern_queue = ['sj.png']
            with patch.object(backend.random, 'choice') as choose:
                state.spawn_obstacle()
            choose.assert_not_called()
            self.assertEqual(state.obstacle_name, 'sj.png')
        for elapsed in (8 * interval, 16 * interval, 20 * interval):
            for name in config.SJ_CLUSTER_TYPES:
                with self.subTest(elapsed=elapsed, cluster=name):
                    state.background_elapsed = elapsed
                    state.pattern_queue = ['sj.png']
                    with patch.object(backend.random, 'choice', return_value=name) as choose:
                        state.spawn_obstacle()
                    self.assertEqual(state.obstacle_name, name)
                    self.assertEqual(set(choose.call_args.args[0]), set(config.SJ_CLUSTER_TYPES))
        with patch.object(backend.random, 'choice') as choose:
            state.spawn_obstacle('sj.png')
        choose.assert_not_called()
        self.assertEqual(state.obstacle_name, 'sj.png')

    def test_old_basic_pattern_also_uses_random_clusters_and_missing_assets_keep_single(self):
        state = self.app.state
        pattern = ('sj.png', 'chicken.png', 'hsucat.png')
        self.assertIn(pattern, config.GROUND_PATTERNS)
        for name in config.SJ_CLUSTER_TYPES:
            state.background_elapsed = (config.SJ_GROUP_UNLOCK_SLOT * config.DAY_NIGHT_INTERVAL)
            state.pattern_queue = []
            def select(pool):
                return pattern if pattern in pool else name
            with patch.object(backend.random, 'choice', side_effect=select), \
                 patch.object(backend.random, 'random', side_effect=[1.0, 0.0] + [1.0] * 20):
                state.spawn_obstacle()
            self.assertEqual(state.current_pattern, pattern)
            self.assertEqual(state.obstacle_name, name)
            self.assertEqual(state.pattern_queue, list(pattern[1:]))
        original_sizes = state.obstacle_sizes
        state.obstacle_sizes = {name: size for name, size in original_sizes.items()
                                if name not in config.SJ_CLUSTER_TYPES}
        self.addCleanup(setattr, state, 'obstacle_sizes', original_sizes)
        state.pattern_queue = ['sj.png']
        state.spawn_obstacle()
        self.assertEqual(state.obstacle_name, 'sj.png')

    def test_second_spring_random_patterns_make_every_new_type_reachable(self):
        state = self.app.state
        state.background_elapsed = (config.SJ_GROUP_UNLOCK_SLOT * config.DAY_NIGHT_INTERVAL)
        seen = set()
        for pattern in config.SJ_PATTERNS:
            with self.subTest(pattern=pattern):
                state.pattern_queue = []
                def select(pool):
                    return pattern if pattern in pool else pool[0]
                with patch.object(backend.random, 'choice', side_effect=select) as choose, \
                     patch.object(backend.random, 'random', side_effect=[1.0, 0.0] + [1.0] * 20):
                    state.spawn_obstacle()
                    self.assertIn(pattern, choose.call_args_list[0].args[0])
                    seen.add(state.obstacle_name)
                    for _ in pattern[1:]:
                        state.spawn_obstacle()
                        seen.add(state.obstacle_name)
        self.assertTrue(set(config.SJ_TYPES).issubset(seen))

    def test_cluster_pixels_are_two_or_three_basic_sjs_with_small_clear_gaps(self):
        singles = self.app.view.obstacle_frames['sj.png']
        self.assertEqual(len(singles), 4)
        for name, count in zip(config.SJ_CLUSTER_TYPES, (2, 3)):
            frames = self.app.view.obstacle_frames[name]
            self.assertEqual(len(frames), len(singles))
            for pose, (single, image) in enumerate(zip(singles, frames)):
                with self.subTest(name=name, pose=pose):
                    width, height = single.get_size()
                    self.assertEqual(image.get_size(),
                                     (count * width + (count - 1) * config.SJ_CLUSTER_GAP, height))
                    for index in range(count):
                        start = index * (width + config.SJ_CLUSTER_GAP)
                        copy = image.subsurface((start, 0, width, height))
                        self.assertEqual(pygame.image.tobytes(copy, 'RGBA'),
                                         pygame.image.tobytes(single, 'RGBA'))
                        if index < count - 1:
                            gap = image.subsurface((start + width, 0,
                                                    config.SJ_CLUSTER_GAP, height))
                            self.assertEqual(pygame.mask.from_surface(gap, 0).count(), 0)

    def test_single_and_all_new_frames_fit_above_the_screen_bottom(self):
        state = self.app.state
        for name in ('sj.png',) + config.SJ_TYPES:
            state.spawn_obstacle(name)
            self.assertEqual(state.obstacle_y + state.obstacle_size[1], 358)
            for index, frame in enumerate(self.app.view.obstacle_frames[name]):
                with self.subTest(name=name, frame=index):
                    bounds = frame.get_bounding_rect(min_alpha=20)
                    self.assertTrue(bounds)
                    self.assertGreaterEqual(state.obstacle_y + bounds.top, 0)
                    self.assertLessEqual(state.obstacle_y + bounds.bottom, config.SCREEN_SIZE[1])

    def test_running_sj_has_two_distinct_cached_poses_and_masks(self):
        name = 'sj_run.png'
        frames = self.app.view.obstacle_frames[name]
        masks = self.app.view.obstacle_frame_masks[name]
        self.assertEqual(len(frames), 2)
        self.assertEqual(len(masks), 2)
        self.assertEqual(len({frame.get_size() for frame in frames}), 1)
        self.assertEqual(frames[0].get_height(), 40)
        self.assertNotEqual(pygame.image.tobytes(frames[0], 'RGBA'),
                            pygame.image.tobytes(frames[1], 'RGBA'))
        state = self.app.state
        state.spawn_obstacle(name)
        for index in (0, 1, 2, 3):
            state.obstacle_animation_tick = index * config.OBSTACLE_FRAME_TICKS
            self.assertEqual(state.obstacle_frame_index, index % 2)
        for frame, mask in zip(frames, masks):
            self.assertEqual(frame.get_size(), mask.get_size())
            self.assertGreater(mask.count(), 0)

    def test_burrow_advances_by_approach_distance_then_keeps_the_final_hole(self):
        name = 'sj_burrow'
        state = self.app.state
        state.spawn_obstacle(name)
        frames = self.app.view.obstacle_frames[name]
        masks = self.app.view.obstacle_frame_masks[name]
        self.assertGreaterEqual(len(frames), 3)
        self.assertEqual(len(frames), len(masks))
        self.assertTrue(all(frame.get_size() == (112, 64) for frame in frames))
        self.assertNotEqual(pygame.image.tobytes(frames[0], 'RGBA'),
                            pygame.image.tobytes(frames[-1], 'RGBA'))
        self.assertEqual(masks[-1].count(), 0)
        for x in (800, 480, 405, 330, 255, 180, 100, 0, -30):
            with self.subTest(x=x):
                state.obstacle_x = x + (0.75 if x != 180 else 0)
                fraction = max(0, min(1, (state.sj_hole_start_x - state.obstacle_x)
                                       / (state.sj_hole_start_x - state.sj_hole_end_x)))
                expected = int(fraction * (len(frames) - 1))
                state.obstacle_animation_tick = 100000
                self.assertEqual(state.obstacle_frame_index, expected)
                with patch.object(self.app.view, 'screen', wraps=self.app.view.screen) as screen:
                    self.app.draw()
                call = screen.blit.call_args_list[2]
                self.assertIs(call.args[0], frames[expected])
                self.assertEqual(call.args[1], (int(state.obstacle_x), int(state.obstacle_y)))
                offset = (int(state.obstacle_x), int(state.obstacle_y) - int(state.player_y))
                expected_collision = state.player_masks[state.player_frame_index].overlap(
                    masks[expected], offset) is not None
                self.assertEqual(state.collides_with_obstacle(), expected_collision)
        self.assertEqual(state.obstacle_frame_index, len(frames) - 1)

    @patch.object(backend.random, 'random', return_value=1.0)
    def test_grounded_player_hits_exposed_types_but_can_cross_the_burrow(self, _random):
        state = self.app.state
        for name in config.SJ_TYPES:
            count = 2 if name == 'sj_run.png' else 1
            for obstacle_pose in range(count):
                for player_pose in range(len(self.app.view.run_frames)):
                    with self.subTest(name=name, obstacle=obstacle_pose, player=player_pose):
                        self.app.reset()
                        state.spawn_obstacle(name)
                        state.obstacle_animation_tick = obstacle_pose * config.OBSTACLE_FRAME_TICKS
                        state.animation_tick = player_pose * config.RUN_FRAME_TICKS
                        contact = None
                        for x in range(state.player_size[0], -state.obstacle_size[0], -1):
                            state.obstacle_x = x
                            if state.collides_with_obstacle():
                                contact = x
                                break
                        if name == 'sj_burrow':
                            self.assertIsNone(contact)
                            self.assertFalse(state.game_over)
                        else:
                            self.assertIsNotNone(contact)
                            state.update_step(0)
                            self.assertTrue(state.game_over)

    @patch.object(backend.random, 'random', return_value=1.0)
    def test_each_sj_type_is_clearable_at_unlocked_stages_and_frame_rates(self, _random):
        for name in config.SJ_TYPES:
            stages = (8, 10, 20) if name in config.SJ_CLUSTER_TYPES or name == 'sj_escape' else (6, 8, 10, 20)
            seconds_cases = tuple(stage * config.DAY_NIGHT_INTERVAL for stage in stages)
            for seconds in seconds_cases:
                for hz in (30, 60, 120):
                    with self.subTest(name=name, seconds=seconds, hz=hz):
                        self.app.reset()
                        state = self.app.state
                        state.background_elapsed = seconds
                        state.spawn_obstacle(name)
                        count = 2 if name == 'sj_pair' else 3 if name == 'sj_triple' else 1
                        expected_bonus = count * config.PASS_BONUS
                        requires_jump = name != 'sj_burrow'
                        jumped = False
                        for _ in range(3 * hz):
                            speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier
                            if requires_jump and not jumped and state.obstacle_x <= 60 + speed * 0.30:
                                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                                jumped = True
                            self.app.handle_events()
                            self.app.update(1 / hz)
                            self.assertFalse(state.game_over)
                            if state.score - int(state.survival_elapsed + 1e-9) >= expected_bonus:
                                break
                        self.assertEqual(jumped, requires_jump)
                        self.assertEqual(state.score - int(state.survival_elapsed + 1e-9), expected_bonus)

    def test_clusters_award_one_pass_bonus_per_member(self):
        state = self.app.state
        for name, count in zip(config.SJ_CLUSTER_TYPES, (2, 3)):
            with self.subTest(name=name):
                self.app.reset()
                state.spawn_obstacle(name)
                state.obstacle_x = -state.obstacle_size[0]
                state.update_step(0)
                self.assertEqual(state.score, count * config.PASS_BONUS)
                state.update_step(0)
                self.assertEqual(state.score, count * config.PASS_BONUS)

    def test_pause_game_over_and_reset_reuse_assets_and_freeze_burrowing(self):
        state = self.app.state
        with patch.object(pygame.image, 'load', side_effect=AssertionError('이미지 재로딩')):
            for name in config.SJ_TYPES:
                self.app.reset()
                state.spawn_obstacle(name)
                state.obstacle_x = 330
                self.app.draw()
                for flag in ('paused', 'game_over'):
                    setattr(state, flag, True)
                    before = (state.obstacle_x, state.obstacle_animation_tick,
                              state.obstacle_frame_index, state.background_elapsed)
                    self.app.update(2)
                    self.app.draw()
                    self.assertEqual((state.obstacle_x, state.obstacle_animation_tick,
                                      state.obstacle_frame_index, state.background_elapsed), before)
                    setattr(state, flag, False)
                self.app.reset()
                self.app.draw()


if __name__ == '__main__':
    unittest.main()
