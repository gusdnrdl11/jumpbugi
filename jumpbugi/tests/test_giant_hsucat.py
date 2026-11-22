"""거대 한성캣의 단일 하품 시트·접근별 포즈와 실제 회피를 검사한다."""
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
    from ..desktop_prototype import assets, backend, config
    from ..desktop_prototype.main import JumpBugi
else:
    from desktop_prototype import assets, backend, config
    from desktop_prototype.main import JumpBugi


class GiantHsucatTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = JumpBugi(Path(directory.name) / 'score.txt')
        self.app.reset()
        pygame.event.clear()

    def spawn_giant(self, seconds=None):
        state = self.app.state
        state.background_elapsed = (config.HSUCAT_UNLOCK_SLOT * config.DAY_NIGHT_INTERVAL) if seconds is None else seconds
        with patch.object(backend.random, 'random', side_effect=AssertionError('하품 이미지 무작위 선택')):
            state.spawn_obstacle('hsucat_crouch.png')
        return state

    def test_one_yawn_sheet_has_four_transparent_aligned_large_frames_without_sleepy(self):
        name = 'hsucat_crouch.png'
        frames = self.app.view.obstacle_frames[name]
        masks = self.app.view.obstacle_frame_masks[name]
        self.assertEqual(config.HSUCAT_GIANT_IMAGE_FILE, 'hsucat_yawn.png')
        self.assertEqual(len(frames), 4)
        self.assertEqual(len(masks), 4)
        self.assertEqual({frame.get_size() for frame in frames}, {(202, 120)})
        # 마지막 두 장면은 입을 벌린 자세를 유지하므로 같은 그림이어도 허용한다.
        self.assertGreaterEqual(len({pygame.image.tobytes(frame, 'RGBA') for frame in frames}), 3)
        self.assertNotIn('hsucat_sleepy.png', self.app.view.obstacle_frames)
        self.assertNotIn('hsucat_yawn.png', self.app.view.obstacle_frames)
        reference = pygame.transform.smoothscale(
            pygame.image.load(str(config.IMAGE_DIR / 'hsucat_crouch.png')).convert_alpha(),
            config.HSUCAT_GIANT_SIZE).get_bounding_rect(min_alpha=20)
        for index, (frame, mask) in enumerate(zip(frames, masks)):
            with self.subTest(frame=index):
                self.assertGreater(mask.count(), 0)
                self.assertLess(mask.count(), 202 * 120)
                self.assertEqual(mask.get_size(), frame.get_size())
                bounds = frame.get_bounding_rect(min_alpha=20)
                self.assertTrue(reference.contains(bounds))
                self.assertGreaterEqual(bounds.bottom, reference.bottom - 1)
                for position in ((0, 0), (201, 0), (0, 119), (201, 119)):
                    self.assertEqual(frame.get_at(position).a, 0)
        original_load = pygame.image.load
        def reject_sleepy(filename, *args, **kwargs):
            self.assertNotEqual(Path(filename).name, 'hsucat_sleepy.png')
            return original_load(filename, *args, **kwargs)
        with patch.object(pygame.image, 'load', side_effect=reject_sleepy):
            prepared = assets.load_hsucat_giant_frames(config.HSUCAT_GIANT_SIZE)
        self.assertIsInstance(prepared, list)
        self.assertEqual(len(prepared), 4)

    def test_spawn_never_selects_another_image_and_offscreen_time_keeps_first_pose(self):
        state = self.spawn_giant()
        self.assertGreaterEqual(state.obstacle_x, config.HSUCAT_GIANT_YAWN_START_X)
        self.assertEqual(state.obstacle_frame_index, 0)
        state.obstacle_x = config.HSUCAT_GIANT_YAWN_START_X + 200
        state.obstacle_animation_tick = 10000 * config.OBSTACLE_FRAME_TICKS
        state.player_y = -1000
        with patch.object(backend.random, 'random', side_effect=AssertionError('이동 중 이미지 재선택')):
            self.app.update(0.1)
            self.app.draw()
        self.assertGreater(state.obstacle_x, config.HSUCAT_GIANT_YAWN_START_X)
        self.assertEqual(state.obstacle_frame_index, 0)
        self.spawn_giant()
        self.assertEqual(state.obstacle_frame_index, 0)

    def test_yawn_progresses_once_by_position_and_keeps_open_pose_in_render_and_collision(self):
        state = self.spawn_giant()
        frames = self.app.view.obstacle_frames['hsucat_crouch.png']
        masks = self.app.view.obstacle_frame_masks['hsucat_crouch.png']
        start = config.HSUCAT_GIANT_YAWN_START_X
        end = config.HSUCAT_GIANT_YAWN_END_X
        span = start - end
        positions = ((start + 1, 0), (start, 0),
                     (start - span / 3 + 0.001, 0), (start - span / 3 - 0.001, 1),
                     (start - 2 * span / 3 + 0.001, 1), (start - 2 * span / 3 - 0.001, 2),
                     (end + 0.001, 2), (end, 3), (0, 3), (-100, 3))
        probe = Mock()
        probe.overlap.return_value = None
        with patch.object(state, 'player_masks', [probe] * state.frame_count):
            for x, expected in positions:
                with self.subTest(x=x):
                    state.obstacle_x = x
                    state.obstacle_animation_tick = 10000 * config.OBSTACLE_FRAME_TICKS
                    self.assertEqual(state.obstacle_frame_index, expected)
                    with patch.object(self.app.view, 'screen', wraps=self.app.view.screen) as screen:
                        self.app.draw()
                    self.assertIs(screen.blit.call_args_list[2].args[0], frames[expected])
                    self.assertFalse(state.collides_with_obstacle())
                    self.assertIs(probe.overlap.call_args.args[0], masks[expected])
        state.obstacle_x = end
        for tick in (0, 5, 10000):
            state.obstacle_animation_tick = tick * config.OBSTACLE_FRAME_TICKS
            self.assertEqual(state.obstacle_frame_index, 3)

    def test_last_open_pose_has_real_silhouette_collision_without_a_background_rectangle(self):
        state = self.spawn_giant()
        state.obstacle_x = state.player_size[0]
        self.assertEqual(state.obstacle_frame_index, 3)
        self.assertFalse(state.collides_with_obstacle())
        contact = next((x for x in range(state.player_size[0], -state.obstacle_size[0], -1)
                        if self.at_x_collides(x)), None)
        self.assertIsNotNone(contact)
        state.obstacle_x = contact
        self.assertEqual(state.obstacle_frame_index, 3)
        state.update_step(0)
        self.assertTrue(state.game_over)

    def test_yawn_opens_more_slowly_but_finishes_before_the_player_and_keeps_its_hold(self):
        state = self.spawn_giant()
        start = config.HSUCAT_GIANT_YAWN_START_X
        end = config.HSUCAT_GIANT_YAWN_END_X
        old_span = start - 220
        self.assertGreater(start - end, old_span)
        self.assertLessEqual(start - end, old_span * 1.5)
        self.assertGreaterEqual(end, state.player_size[0])
        # 예전에는 이미 다음 자세였던 같은 화면 위치에서 더 천천히 입을 벌린다.
        for x, expected in ((300, 1), (200, 2), (end, 3), (0, 3), (-100, 3)):
            with self.subTest(x=x):
                state.obstacle_x = x
                state.obstacle_animation_tick = 60000
                self.assertEqual(state.obstacle_frame_index, expected)

    def at_x_collides(self, x):
        self.app.state.obstacle_x = x
        return self.app.state.collides_with_obstacle()

    def test_pause_game_over_respawn_and_reset_keep_cached_images_and_reset_yawn_progress(self):
        frames = self.app.view.obstacle_frames['hsucat_crouch.png']
        state = self.spawn_giant()
        state.obstacle_x = config.HSUCAT_GIANT_YAWN_END_X
        self.assertEqual(state.obstacle_frame_index, 3)
        with patch.object(pygame.image, 'load', side_effect=AssertionError('이미지 재로딩')):
            for flag in ('paused', 'game_over'):
                setattr(state, flag, True)
                before = (state.obstacle_x, state.obstacle_animation_tick, state.obstacle_frame_index)
                self.app.update(2)
                self.app.draw()
                self.assertEqual((state.obstacle_x, state.obstacle_animation_tick,
                                  state.obstacle_frame_index), before)
                setattr(state, flag, False)
            self.spawn_giant()
            self.assertEqual(state.obstacle_frame_index, 0)
            self.app.reset()
            self.assertEqual(state.background_elapsed, 0)
            self.assertIs(self.app.view.obstacle_frames['hsucat_crouch.png'], frames)

    def test_yawn_is_jumpable_and_awards_ten_at_four_speed_stages_and_three_frame_rates(self):
        for stage in (4, 6, 10, 20):
            seconds = stage * config.DAY_NIGHT_INTERVAL
            for hz in (30, 60, 120):
                with self.subTest(stage=stage, hz=hz):
                    self.app.reset()
                    state = self.spawn_giant(seconds)
                    self.assertIsNone(state.wave_jump)
                    jumped = False
                    seen = set()
                    for _ in range(3 * hz):
                        seen.add(state.obstacle_frame_index)
                        speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier
                        if not jumped and state.obstacle_x <= 95 + speed * 0.12:
                            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                            jumped = True
                        self.app.handle_events()
                        self.app.update(1 / hz)
                        self.assertFalse(state.game_over)
                        bonus = state.score - int(state.survival_elapsed + 1e-9) * config.SURVIVAL_POINTS_PER_SECOND
                        if bonus == config.PASS_BONUS:
                            break
                    self.assertTrue(jumped)
                    self.assertEqual(seen, {0, 1, 2, 3})
                    self.assertEqual(bonus, 10)


if __name__ == '__main__':
    unittest.main()
