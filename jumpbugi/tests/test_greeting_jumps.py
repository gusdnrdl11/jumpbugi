"""기본 인사 캐릭터의 첫해 제한과 세 점프 패턴의 실제 회피를 검사한다."""
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


class GreetingJumpTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = JumpBugi(Path(directory.name) / 'score.txt')
        self.app.reset()
        pygame.event.clear()

    def spawn_pattern(self, name, pattern, seconds=240):
        state = self.app.state
        state.background_elapsed = seconds
        if pattern is None:
            with patch.object(backend.random, 'random', return_value=1.0):
                state.spawn_obstacle(name)
        else:
            patterns = tuple(config.WAVE_JUMP_HEIGHTS)
            selection = (patterns.index(pattern) + 0.5) / len(patterns)
            with patch.object(backend.random, 'random', side_effect=(0.0, selection)):
                state.spawn_obstacle(name)
        self.assertEqual(state.wave_jump.pattern if state.wave_jump else None, pattern)
        return state.wave_jump

    def test_basic_characters_use_four_aligned_greeting_poses_and_masks(self):
        self.assertEqual(config.WAVE_IMAGE_FILES,
                         {'chicken.png': 'chicken_wave.png', 'hsucat.png': 'hsucat_wave.png'})
        state = self.app.state
        for name in config.WAVE_IMAGE_FILES:
            with self.subTest(name=name):
                frames = self.app.view.obstacle_frames[name]
                masks = self.app.view.obstacle_frame_masks[name]
                self.assertEqual(len(frames), 4)
                self.assertEqual(len(masks), 4)
                self.assertEqual(len({frame.get_size() for frame in frames}), 1)
                self.assertEqual(len({pygame.image.tobytes(frame, 'RGBA') for frame in frames}), 4)
                self.assertEqual(frames[0].get_height(), config.CHARACTER_HEIGHT)
                self.spawn_pattern(name, None, seconds=0)
                self.assertEqual(state.obstacle_y + state.obstacle_size[1], 358)
                for index, (frame, mask) in enumerate(zip(frames, masks)):
                    state.obstacle_animation_tick = index * config.OBSTACLE_FRAME_TICKS
                    self.assertEqual(state.obstacle_frame_index, index)
                    self.assertEqual(frame.get_size(), mask.get_size())
                    self.assertGreater(mask.count(), 0)
                    self.assertGreaterEqual(frame.get_bounding_rect(min_alpha=20).bottom,
                                            frame.get_height() - 1)

    def test_first_year_only_waves_and_jump_eligibility_is_captured_at_spawn(self):
        state = self.app.state
        self.assertEqual(config.WAVE_JUMP_UNLOCK_SECONDS, 240)
        for name in config.WAVE_IMAGE_FILES:
            for seconds in (0, 30, 60, 120, 180, 239.999):
                with self.subTest(name=name, seconds=seconds):
                    state.background_elapsed = seconds
                    with patch.object(backend.random, 'random', return_value=0.0):
                        state.spawn_obstacle(name)
                    self.assertFalse(state.greeting_jumps_enabled)
                    self.assertIsNone(state.wave_jump)
                    self.assertFalse(state.wave_jump_active)
                    self.assertTrue(state.obstacle_requires_jump)
            state.background_elapsed = 239.999
            state.spawn_obstacle(name)
            state.background_elapsed = 240
            state.obstacle_x = 300
            ground_y = state.obstacle_y
            with patch.object(backend.random, 'random', side_effect=AssertionError('접근 중 점프 재선택')):
                state.update_step(0)
            self.assertTrue(state.greeting_jumps_enabled)
            self.assertIsNone(state.wave_jump)
            self.assertEqual(state.obstacle_y, ground_y)
            self.spawn_pattern(name, 'high', seconds=240)
            self.assertFalse(state.obstacle_requires_jump)

    def test_later_years_randomly_choose_ground_or_each_of_three_patterns(self):
        state = self.app.state
        self.assertEqual(set(config.WAVE_JUMP_HEIGHTS), {'high', 'near', 'low'})
        for name in config.WAVE_IMAGE_FILES:
            for seconds in (240, 480, 960):
                for pattern in (None, 'high', 'near', 'low'):
                    with self.subTest(name=name, seconds=seconds, pattern=pattern):
                        self.spawn_pattern(name, pattern, seconds)
                        self.assertEqual(state.obstacle_requires_jump, pattern in (None, 'low'))
                        self.assertEqual(state.obstacle_y + state.obstacle_size[1], 358)
        state.spawn_obstacle('chicken_white_flying')
        self.assertIsNone(state.wave_jump)
        self.assertFalse(state.obstacle_requires_jump)

    def test_high_and_near_patterns_clear_the_entire_grounded_contact_interval(self):
        state = self.app.state
        for name in config.WAVE_IMAGE_FILES:
            for pattern in ('high', 'near'):
                with self.subTest(name=name, pattern=pattern):
                    self.app.reset()
                    self.spawn_pattern(name, pattern)
                    for player_pose in range(len(self.app.view.run_frames)):
                        state.animation_tick = player_pose * config.RUN_FRAME_TICKS
                        for x in range(-state.obstacle_size[0] + 1, state.player_size[0] + 1):
                            state.obstacle_x = x + 0.75
                            state.update_step(0)
                            self.assertTrue(state.wave_jump_active)
                            self.assertEqual(state.obstacle_frame_index, 0)
                            self.assertLessEqual(state.obstacle_y + state.obstacle_size[1],
                                                 state.ground_y - config.WAVE_UNDERPASS_CLEARANCE)
                            self.assertFalse(state.collides_with_obstacle())
                            self.assertFalse(state.game_over)

    def test_airborne_pose_and_collision_use_the_drawn_height(self):
        state = self.app.state
        for name in config.WAVE_IMAGE_FILES:
            with self.subTest(name=name):
                self.app.reset()
                plan = self.spawn_pattern(name, 'high')
                state.obstacle_x = plan.center_x + 0.75
                state.player_y = -1000
                for tick in (0, 6, 12, 18, 24):
                    state.obstacle_animation_tick = tick
                    state.update_step(0)
                    self.assertTrue(state.wave_jump_active)
                    self.assertEqual(state.obstacle_frame_index, 0)
                with patch.object(self.app.view, 'screen', wraps=self.app.view.screen) as screen:
                    self.app.draw()
                call = screen.blit.call_args_list[2]
                self.assertIs(call.args[0], self.app.view.obstacle_frames[name][0])
                self.assertEqual(call.args[1], (int(state.obstacle_x), int(state.obstacle_y)))
                state.player_y = 100.75
                mask = self.app.view.obstacle_frame_masks[name][0]
                offset = (int(state.obstacle_x), int(state.obstacle_y) - int(state.player_y))
                self.assertIsNotNone(state.player_masks[state.player_frame_index].overlap(mask, offset))
                ground_rect = pygame.Rect(int(state.obstacle_x), int(state.obstacle_ground_y),
                                          *state.obstacle_size)
                player_rect = pygame.Rect(0, int(state.player_y), *state.player_size)
                self.assertFalse(player_rect.colliderect(ground_rect))
                state.update_step(0)
                self.assertTrue(state.game_over)

    def test_high_and_near_underpasses_remain_safe_across_acceleration_boundaries(self):
        for name in config.WAVE_IMAGE_FILES:
            for pattern in ('high', 'near'):
                for hz in (30, 60, 120):
                    with self.subTest(name=name, pattern=pattern, hz=hz):
                        self.app.reset()
                        state = self.app.state
                        plan = self.spawn_pattern(name, pattern, seconds=269.95)
                        state.obstacle_x = plan.center_x + plan.half_distance * 0.5
                        original_speed = state.speed_multiplier
                        crossed = False
                        for _ in range(2 * hz):
                            self.app.update(1 / hz)
                            crossed |= state.speed_multiplier > original_speed
                            self.assertFalse(state.game_over)
                            self.assertFalse(state.is_jumping)
                            if state.score >= config.PASS_BONUS:
                                break
                        self.assertTrue(crossed)
                        self.assertGreaterEqual(state.score, config.PASS_BONUS)

    def test_pause_game_over_and_reset_preserve_or_clear_jump_plans(self):
        state = self.app.state
        for name in config.WAVE_IMAGE_FILES:
            self.app.reset()
            plan = self.spawn_pattern(name, 'near')
            state.obstacle_x = plan.center_x + plan.half_distance * 0.5
            self.app.update(1 / 120)
            self.assertTrue(state.wave_jump_active)
            for flag in ('paused', 'game_over'):
                setattr(state, flag, True)
                before = (state.obstacle_x, state.obstacle_y, state.obstacle_frame_index, state.wave_jump)
                with patch.object(pygame.image, 'load', side_effect=AssertionError('이미지 재로딩')), \
                     patch.object(backend.random, 'random', side_effect=AssertionError('점프 재선택')):
                    self.app.update(2)
                    self.app.draw()
                self.assertEqual((state.obstacle_x, state.obstacle_y, state.obstacle_frame_index,
                                  state.wave_jump), before)
                setattr(state, flag, False)
            self.app.reset()
            self.assertIsNone(state.wave_jump)
            self.assertFalse(state.wave_jump_active)
            self.assertEqual(state.background_elapsed, 0)

    def test_all_patterns_have_the_intended_escape_at_multiple_speeds_and_frame_rates(self):
        for name in config.WAVE_IMAGE_FILES:
            for pattern in (None, 'high', 'near', 'low'):
                for seconds in (240, 300, 600):
                    for hz in (30, 60, 120):
                        with self.subTest(name=name, pattern=pattern, seconds=seconds, hz=hz):
                            self.app.reset()
                            state = self.app.state
                            plan = self.spawn_pattern(name, pattern, seconds)
                            center = ((state.player_size[0] - state.obstacle_size[0]) / 2)
                            jumped = False
                            for _ in range(3 * hz):
                                speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier
                                if state.obstacle_requires_jump and not jumped and state.obstacle_x <= center + speed * 0.35:
                                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                                    jumped = True
                                self.app.handle_events()
                                self.app.update(1 / hz)
                                self.assertFalse(state.game_over)
                                if state.score >= config.PASS_BONUS:
                                    break
                            self.assertEqual(jumped, pattern in (None, 'low'))
                            self.assertEqual(state.score - int(state.survival_elapsed + 1e-9),
                                             config.PASS_BONUS)


if __name__ == '__main__':
    unittest.main()
