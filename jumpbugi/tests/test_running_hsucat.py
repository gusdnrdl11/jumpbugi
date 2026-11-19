"""달리는 한성캣의 달리기·넘어짐·높은 점프와 아래 통과 득점을 검사한다."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

if __package__ and __package__.startswith('jumpbugi.'):
    from .. import assets, backend, config
    from ..main import JumpBugi
else:
    import assets, backend, config
    from main import JumpBugi


class RunningHsucatTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = JumpBugi(Path(directory.name) / 'score.txt')
        self.app.reset()
        pygame.event.clear()

    def spawn_mode(self, mode, seconds=120):
        state = self.app.state
        state.background_elapsed = seconds
        roll = (config.HSUCAT_RUN_MODES.index(mode) + 0.5) / len(config.HSUCAT_RUN_MODES)
        with patch.object(backend.random, 'random', return_value=roll):
            state.spawn_obstacle('hsucat_run.png')
        self.assertEqual(state.hsucat_run_mode, mode)
        return state

    def bonus(self):
        state = self.app.state
        return state.score - int(state.survival_elapsed + 1e-9) * config.SURVIVAL_POINTS_PER_SECOND

    def test_run_pixels_are_preserved_and_fall_poses_lower_without_clipping_feet(self):
        frames = self.app.view.obstacle_frames['hsucat_run.png']
        masks = self.app.view.obstacle_frame_masks['hsucat_run.png']
        self.assertEqual(len(frames), 8)
        self.assertEqual(len(masks), 8)
        self.assertEqual({frame.get_size() for frame in frames}, {(122, 120)})
        original = assets.load_hsucat_frames(120)
        for old, padded in zip(original, frames[:4]):
            self.assertEqual(pygame.image.tobytes(padded.subsurface(old.get_rect()), 'RGBA'),
                             pygame.image.tobytes(old, 'RGBA'))
            self.assertEqual(padded.subsurface((90, 0, 32, 120)).get_bounding_rect().width, 0)
        self.assertEqual(len({pygame.image.tobytes(frame, 'RGBA') for frame in frames[4:]}), 4)
        falls = [frame.get_bounding_rect(min_alpha=20) for frame in frames[4:]]
        self.assertGreater(falls[0].height, falls[-1].height)
        self.assertGreater(falls[-1].width, falls[0].width)
        state = self.spawn_mode('fall')
        for frame, mask in zip(frames, masks):
            bounds = frame.get_bounding_rect(min_alpha=20)
            self.assertEqual(mask.get_size(), frame.get_size())
            self.assertGreater(mask.count(), 0)
            self.assertEqual(bounds.bottom, 120)
            self.assertEqual(state.obstacle_y + bounds.bottom, 358)

    def test_each_mode_is_selected_once_with_equal_probability_and_existing_autumn_unlock(self):
        state = self.app.state
        for roll, mode in ((0.0, 'fall'), (0.333332, 'fall'), (1 / 3, 'high'),
                           (0.666665, 'high'), (2 / 3, 'run'), (1.0, 'run')):
            with self.subTest(roll=roll):
                state.background_elapsed = 120
                with patch.object(backend.random, 'random', return_value=roll) as choose:
                    state.spawn_obstacle('hsucat_run.png')
                self.assertEqual(choose.call_count, 1)
                self.assertEqual(state.hsucat_run_mode, mode)
                self.assertEqual(state.wave_jump is not None, mode == 'high')
                self.assertEqual(state.obstacle_requires_jump, mode != 'high')
                self.assertTrue(state.hsucat_obstacles_enabled)
                state.player_y = -1000
                with patch.object(backend.random, 'random', side_effect=AssertionError('도중 재선택')):
                    self.app.update(1 / 120)
                    self.app.draw()
                self.assertEqual(state.hsucat_run_mode, mode)

    def test_running_loops_and_falling_connects_once_with_matching_visible_collision_pose(self):
        state = self.spawn_mode('run')
        frames = self.app.view.obstacle_frames['hsucat_run.png']
        masks = self.app.view.obstacle_frame_masks['hsucat_run.png']
        for tick in range(12):
            state.obstacle_animation_tick = tick * config.OBSTACLE_FRAME_TICKS
            self.assertEqual(state.obstacle_frame_index, tick % 4)
        self.spawn_mode('fall')
        probe = Mock()
        probe.overlap.return_value = None
        positions = ((421, 2), (420, 4), (341, 4), (340, 5), (261, 5),
                     (260, 6), (181, 6), (180, 7), (60, 7), (-100, 7))
        with patch.object(state, 'player_masks', [probe] * state.frame_count):
            for x, expected in positions:
                with self.subTest(x=x):
                    state.obstacle_x = x
                    state.obstacle_animation_tick = 10 * config.OBSTACLE_FRAME_TICKS
                    self.assertEqual(state.obstacle_frame_index, expected)
                    with patch.object(self.app.view, 'screen', wraps=self.app.view.screen) as screen:
                        self.app.draw()
                    self.assertIs(screen.blit.call_args_list[2].args[0], frames[expected])
                    self.assertFalse(state.collides_with_obstacle())
                    self.assertIs(probe.overlap.call_args.args[0], masks[expected])
        state.obstacle_x = 60
        state.update_step(0)
        self.assertTrue(state.game_over)

    def test_high_jump_stays_above_grounded_bugi_and_underpass_scores_once(self):
        state = self.spawn_mode('high')
        plan = state.wave_jump
        self.assertGreaterEqual(plan.height, 228)
        for x in range(state.player_size[0] - 1, -state.obstacle_size[0], -3):
            with self.subTest(x=x):
                state.obstacle_x = x
                state.update_step(0)
                self.assertFalse(state.game_over)
                self.assertTrue(state.wave_jump_active)
                self.assertEqual(state.obstacle_frame_index, 0)
                self.assertLessEqual(state.obstacle_y + state.obstacle_size[1], state.ground_y - 16)
        state.obstacle_x = -state.obstacle_size[0]
        state.update_step(0)
        self.assertEqual(state.score, 10)
        self.assertTrue(state.passed)
        state.update_step(0)
        self.assertEqual(state.score, 10)

    def test_pause_game_over_new_spawn_and_reset_keep_mode_state_and_cached_images(self):
        frames = self.app.view.obstacle_frames['hsucat_run.png']
        state = self.spawn_mode('high')
        state.obstacle_x = 80
        state.update_step(0)
        with patch.object(pygame.image, 'load', side_effect=AssertionError('이미지 재로딩')):
            for flag in ('paused', 'game_over'):
                setattr(state, flag, True)
                before = (state.obstacle_x, state.obstacle_y, state.obstacle_frame_index,
                          state.hsucat_run_mode, state.wave_jump)
                self.app.update(2)
                self.app.draw()
                self.assertEqual((state.obstacle_x, state.obstacle_y, state.obstacle_frame_index,
                                  state.hsucat_run_mode, state.wave_jump), before)
                setattr(state, flag, False)
            self.spawn_mode('fall')
            self.assertIsNone(state.wave_jump)
            self.assertEqual(state.obstacle_frame_index, 0)
            self.app.reset()
            self.assertEqual(state.hsucat_run_mode, 'run')
            self.assertIsNone(state.wave_jump)
            self.assertEqual(state.background_elapsed, 0)
            self.assertIs(self.app.view.obstacle_frames['hsucat_run.png'], frames)

    def test_all_three_modes_are_clearable_and_award_ten_at_four_speeds_and_three_fps(self):
        for mode in config.HSUCAT_RUN_MODES:
            for seconds in (120, 180, 300, 600):
                for hz in (30, 60, 120):
                    with self.subTest(mode=mode, seconds=seconds, hz=hz):
                        self.app.reset()
                        state = self.spawn_mode(mode, seconds)
                        jumped = False
                        for _ in range(3 * hz):
                            speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier
                            if mode != 'high' and not jumped and state.obstacle_x <= 60 + speed * 0.30:
                                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                                jumped = True
                            self.app.handle_events()
                            self.app.update(1 / hz)
                            self.assertFalse(state.game_over)
                            if self.bonus() == 10:
                                break
                        self.assertEqual(jumped, mode != 'high')
                        self.assertEqual(self.bonus(), 10)


if __name__ == '__main__':
    unittest.main()
