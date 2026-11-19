"""책을 떨어뜨리는 한성캣의 배치·진행·충돌과 실제 입력 회피를 검사한다."""
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
    from .. import config
    from ..main import JumpBugi
else:
    import config
    from main import JumpBugi


class BookHsucatTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = JumpBugi(Path(directory.name) / 'score.txt')
        self.app.reset()
        pygame.event.clear()

    def spawn_book(self, seconds=120):
        state = self.app.state
        state.background_elapsed = seconds
        state.spawn_obstacle('hsucat_book.png')
        return state

    def test_four_transparent_poses_keep_the_cat_fixed_as_books_spread_right(self):
        frames = self.app.view.obstacle_frames['hsucat_book.png']
        masks = self.app.view.obstacle_frame_masks['hsucat_book.png']
        self.assertEqual(len(frames), 4)
        self.assertEqual(len(masks), 4)
        self.assertEqual({frame.get_size() for frame in frames}, {(180, 120)})
        self.assertEqual(len({pygame.image.tobytes(frame, 'RGBA') for frame in frames}), 4)
        bounds = [frame.get_bounding_rect(min_alpha=20) for frame in frames]
        self.assertLessEqual(max(rect.left for rect in bounds) - min(rect.left for rect in bounds), 1)
        self.assertLessEqual(max(rect.top for rect in bounds) - min(rect.top for rect in bounds), 1)
        self.assertEqual([rect.right for rect in bounds], sorted(rect.right for rect in bounds))
        self.assertGreater(bounds[-1].width, bounds[0].width * 1.7)
        reference = pygame.image.load(str(config.IMAGE_DIR / 'hsucat_book.png')).convert_alpha()
        reference = pygame.transform.smoothscale(reference, (180, 120)).get_bounding_rect(min_alpha=20)
        for frame, mask, rect in zip(frames, masks, bounds):
            self.assertTrue(reference.contains(rect))
            self.assertGreater(mask.count(), 0)
            self.assertLess(mask.count(), 180 * 120)
            self.assertEqual(mask.get_size(), frame.get_size())
            for position in ((0, 0), (179, 0), (0, 119), (179, 119)):
                self.assertEqual(frame.get_at(position).a, 0)

    def test_position_advances_once_and_render_uses_the_same_pose_as_collision(self):
        state = self.spawn_book()
        frames = self.app.view.obstacle_frames['hsucat_book.png']
        masks = self.app.view.obstacle_frame_masks['hsucat_book.png']
        probe = Mock()
        probe.overlap.return_value = None
        # 출발 전과 각 경계 양쪽, 낙하 완료 뒤에도 마지막 포즈가 유지되는지 확인한다.
        positions = ((580, 0), (480, 0), (381, 0), (380, 1), (281, 1),
                     (280, 2), (181, 2), (180, 3), (60, 3), (-100, 3))
        with patch.object(state, 'player_masks', [probe] * state.frame_count):
            for x, expected in positions:
                with self.subTest(x=x, pose=expected):
                    state.obstacle_x = x
                    state.obstacle_animation_tick = 10000
                    self.assertEqual(state.obstacle_frame_index, expected)
                    with patch.object(self.app.view, 'screen', wraps=self.app.view.screen) as screen:
                        self.app.draw()
                    self.assertIs(screen.blit.call_args_list[2].args[0], frames[expected])
                    self.assertFalse(state.collides_with_obstacle())
                    self.assertIs(probe.overlap.call_args.args[0], masks[expected])
        state.obstacle_x = 60
        self.assertTrue(state.collides_with_obstacle())
        state.update_step(0)
        self.assertTrue(state.game_over)

    def test_pause_game_over_and_respawn_preserve_progress_and_reuse_frames(self):
        state = self.spawn_book()
        frames = self.app.view.obstacle_frames['hsucat_book.png']
        state.obstacle_x = 300
        state.player_y = -1000
        with patch.object(pygame.image, 'load', side_effect=AssertionError('이미지 재로딩')):
            for flag in ('paused', 'game_over'):
                setattr(state, flag, True)
                before = (state.obstacle_x, state.obstacle_frame_index, state.obstacle_animation_tick)
                self.app.update(2)
                self.app.draw()
                self.assertEqual((state.obstacle_x, state.obstacle_frame_index,
                                  state.obstacle_animation_tick), before)
                setattr(state, flag, False)
            state.obstacle_x = 60
            self.assertEqual(state.obstacle_frame_index, 3)
            state.spawn_obstacle('hsucat_book.png')
            self.assertEqual(state.obstacle_frame_index, 0)
            self.app.reset()
            self.assertEqual(state.background_elapsed, 0)
            self.assertIs(self.app.view.obstacle_frames['hsucat_book.png'], frames)
            self.spawn_book()
            self.assertEqual(state.obstacle_frame_index, 0)

    def test_drop_animation_is_jumpable_and_scores_ten_at_four_speeds_and_three_fps(self):
        for seconds in (120, 180, 300, 600):
            for hz in (30, 60, 120):
                with self.subTest(seconds=seconds, hz=hz):
                    self.app.reset()
                    state = self.spawn_book(seconds)
                    self.assertIsNone(state.wave_jump)
                    jumped = False
                    for _ in range(3 * hz):
                        speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier
                        if not jumped and state.obstacle_x <= 60 + speed * 0.30:
                            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                            jumped = True
                        self.app.handle_events()
                        self.app.update(1 / hz)
                        self.assertFalse(state.game_over)
                        bonus = (state.score - int(state.survival_elapsed + 1e-9)
                                 * config.SURVIVAL_POINTS_PER_SECOND)
                        if bonus == config.PASS_BONUS:
                            break
                    self.assertTrue(jumped)
                    self.assertEqual(bonus, 10)


if __name__ == '__main__':
    unittest.main()
