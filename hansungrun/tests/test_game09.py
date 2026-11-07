"""hansungrun 폴더: python -B -m unittest discover -s tests -v"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
if __package__ and __package__.startswith('hansungrun.'):
    from .. import config as game
    from .. import backend
    from ..assets import load_image
    from ..main import HansungRun
else:
    import config as game
    import backend
    from assets import load_image
    from main import HansungRun


class GameTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.record = Path(directory.name) / 'high_score.txt'
        self.app = HansungRun(self.record)
        pygame.event.clear()

    def key(self, value):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=value))
        self.app.handle_events()

    def test_scroll_speed_wrap_and_screen_coverage(self):
        app = self.app
        self.assertEqual(app.view.stage.get_size(), (960, 360))
        app.state.player_y = -1000  # 재등장 시 장애물의 지면 위치가 갱신되어도 충돌을 피한다.
        for frame in range(1, 482):
            previous = app.state.obstacle_x
            previous_width = app.view.obstacle_images[app.state.obstacle_name].get_width()
            app.update()
            self.assertEqual(app.state.background_x, -((frame * 6) % 960))
            if previous - 6 + previous_width >= 0:
                self.assertEqual(app.state.obstacle_x, previous - 6)
            else:
                self.assertEqual(app.state.obstacle_x, 480)
            # 실제 출력 픽셀을 원본의 순환 좌표와 비교해 빈 공간과 좌표 오차를 검사한다.
            app.draw()
            for x in (0, 240, 479):
                source_x = int((x - app.state.background_x) % 960)
                self.assertEqual(app.view.screen.get_at((x, 150)),
                                 app.view.stage.get_at((source_x, 150)))

    def test_jump_landing_and_no_double_jump(self):
        app = self.app
        app.state.obstacle_y = -1000
        self.key(pygame.K_SPACE)
        app.update()
        self.assertLess(app.state.player_y, app.state.ground_y)
        velocity = app.state.velocity_y
        self.key(pygame.K_SPACE)
        self.assertEqual(app.state.velocity_y, velocity)
        for _ in range(100):
            app.update()
        self.assertEqual(app.state.player_y, app.state.ground_y)
        self.assertFalse(app.state.is_jumping)

    def test_collision_freeze_and_restart(self):
        app = self.app
        app.state.obstacle_x = 0
        app.update()
        self.assertTrue(app.state.game_over)
        frozen = (app.state.background_x, app.state.obstacle_x, app.state.player_y, app.state.score)
        self.key(pygame.K_SPACE)
        app.update()
        self.assertEqual(frozen, (app.state.background_x, app.state.obstacle_x, app.state.player_y, app.state.score))
        self.key(pygame.K_RETURN)
        self.assertFalse(app.state.game_over)
        self.assertEqual((app.state.background_x, app.state.obstacle_x, app.state.score), (0, 480, 0))
        self.assertEqual((app.state.player_y, app.state.velocity_y, app.state.is_jumping),
                         (app.state.ground_y, 0, False))

    def test_bonus_once_respawn_and_high_score_persistence(self):
        app = self.app
        self.assertEqual(app.state.high_score, 0)
        self.assertFalse(self.record.exists())
        app.state.obstacle_x = -app.view.obstacle_images[app.state.obstacle_name].get_width() + game.OBSTACLE_SPEED
        app.update()
        self.assertEqual((app.state.score, app.state.high_score), (10, 0))
        self.assertFalse(self.record.exists())
        app.update()
        self.assertEqual(app.state.score, 10)
        self.assertEqual(app.state.obstacle_x, 480)
        self.assertFalse(app.state.passed)
        # 실제 충돌로 판을 종료했을 때만 새 기록이 표시·저장된다.
        app.state.obstacle_x = 0
        app.update()
        self.assertTrue(app.state.game_over)
        self.assertEqual(app.state.high_score, 10)
        app.reset()
        self.assertEqual((app.state.score, app.state.high_score), (0, 10))
        self.assertEqual(HansungRun(self.record).state.high_score, 10)
        app.state.score = 5
        app.state.record_high_score()
        self.assertEqual(self.record.read_text(), '10')
        app.state.score = 120
        app.state.record_high_score()
        self.assertEqual(HansungRun(self.record).state.high_score, 120)
        self.assertFalse(self.record.with_suffix('.tmp').exists())

    def test_four_poses_and_animation_freeze(self):
        app = self.app
        self.assertEqual(len(app.view.run_frames), 4)
        width, height = app.view.player_image.get_size()
        leg_top = int(height * 0.78)  # 다리 영역에 실제 포즈 차이가 있는지 검사한다.
        legs = set()
        for frame in app.view.run_frames:
            self.assertEqual(frame.get_size(), (width, height))
            legs.add(pygame.image.tobytes(frame.subsurface((0, leg_top, width, height-leg_top)), 'RGBA'))
        self.assertEqual(len(legs), 4)
        for _ in range(game.RUN_FRAME_TICKS):
            app.update()
        self.assertEqual(app.state.animation_tick // game.RUN_FRAME_TICKS, 1)
        app.state.obstacle_y = -1000
        for expected in (2, 3, 0):
            for _ in range(game.RUN_FRAME_TICKS):
                app.update()
            self.assertEqual(app.state.animation_tick // game.RUN_FRAME_TICKS, expected)
        self.key(pygame.K_SPACE)
        frozen = app.state.animation_tick
        app.update()
        self.assertEqual(app.state.animation_tick, frozen)
        app.state.game_over = True
        app.update()
        self.assertEqual(app.state.animation_tick, frozen)

    def test_each_random_obstacle_collision_and_reuse(self):
        app = self.app
        for name in game.OBSTACLE_FILES:
            with patch.object(backend.random, 'choice', return_value=name) as choose:
                app.reset()
                choose.assert_called_once_with(game.OBSTACLE_FILES)
                self.assertEqual(app.state.obstacle_name, name)
                self.assertIs(app.view.obstacle_images[app.state.obstacle_name], app.view.obstacle_images[name])
                self.assertEqual(app.view.obstacle_images[app.state.obstacle_name].get_height(), game.OBSTACLE_HEIGHTS[name])
                app.state.obstacle_x = 0
                app.update()
                self.assertTrue(app.state.game_over)
                app.reset()
                app.state.obstacle_x = -app.view.obstacle_images[app.state.obstacle_name].get_width() - 1
                app.update()
                self.assertEqual(app.state.obstacle_name, name)
                self.assertEqual(app.state.obstacle_x, 480)

    def test_exit_records_score_once(self):
        for event in (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F4, mod=pygame.KMOD_CTRL),
                      pygame.event.Event(pygame.QUIT)):
            self.app.state.running = True
            self.app.state.score += 10
            pygame.event.post(event)
            self.app.handle_events()
            self.assertFalse(self.app.state.running)
            self.assertEqual(int(self.record.read_text()), self.app.state.score)

    def test_small_sangjji_size_ground_and_jump_clearance(self):
        app = self.app
        with patch.object(backend.random, 'choice', return_value='sangjji.png'):
            app.reset()
        self.assertEqual(app.view.obstacle_images[app.state.obstacle_name].get_size(), (39, 40))
        self.assertEqual(app.state.obstacle_y, 327)
        rect = app.view.obstacle_images[app.state.obstacle_name].get_rect(topleft=(60, app.state.obstacle_y))
        hitbox = rect.inflate(*app.state.obstacle_hitbox_shrink)
        self.assertGreater(hitbox.width, 0)
        self.assertGreater(hitbox.height, 0)
        self.assertEqual(rect.bottom, 367)
        app.state.obstacle_x = 60
        self.key(pygame.K_SPACE)
        app.update()
        self.assertFalse(app.state.game_over)
        # 점프하지 않으면 작은 상찌도 실제로 부딪혀야 한다.
        app.reset()
        with patch.object(backend.random, 'choice', return_value='sangjji.png'):
            app.state.spawn_obstacle()
        app.state.obstacle_x = 60
        app.update()
        self.assertTrue(app.state.game_over)

    def test_hud_layout_and_game_over_drawing(self):
        app = self.app
        app.view.screen = Mock(wraps=app.view.screen)
        for score in (0, 120, 999999):
            app.view.screen.reset_mock()
            app.state.score = app.state.high_score = score
            app.draw()
            calls = app.view.screen.blit.call_args_list
            best, current = calls[4].args[1], calls[5].args[1]
            self.assertEqual((current.right, current.top, best.top), (470, 10, 10))
            self.assertEqual(best.right + 20, current.left)
            self.assertGreaterEqual(best.left, 0)
        app.state.game_over = True
        app.view.screen.reset_mock()
        app.draw()
        self.assertEqual(app.view.screen.blit.call_count, 8)

    def test_pause_and_timing(self):
        # 점프 도중 모든 상태가 멈추고 재개하면 이어지는지 확인한다.
        app = self.app
        app.state.obstacle_y = -1000
        self.key(pygame.K_SPACE)
        app.update()
        self.key(pygame.K_ESCAPE)
        frozen = (app.state.player_y, app.state.velocity_y, app.state.background_x, app.state.obstacle_x, app.state.animation_tick, app.state.score)
        self.key(pygame.K_SPACE)
        app.update(0.1)
        self.assertEqual(frozen, (app.state.player_y, app.state.velocity_y, app.state.background_x, app.state.obstacle_x, app.state.animation_tick, app.state.score))
        app.draw()
        self.key(pygame.K_ESCAPE)
        app.update()
        self.assertNotEqual(app.state.player_y, frozen[0])
        # 60Hz와 120Hz에서 같은 시간 동안 같은 이동과 점프가 나와야 한다.
        states = []
        for hz in (60, 120):
            app.reset()
            app.state.obstacle_y = -1000
            self.key(pygame.K_SPACE)
            for _ in range(hz // 6):
                app.update(1 / hz)
            states.append((app.state.player_y, app.state.velocity_y, app.state.background_x, app.state.obstacle_x))
        for actual, expected in zip(*states):
            self.assertAlmostEqual(actual, expected)

    def test_exit_and_resource_path(self):
        self.key(pygame.K_ESCAPE)
        self.assertTrue(self.app.state.running)
        self.assertTrue(self.app.state.paused)
        self.app.state.running = True
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.app.run()
        self.assertFalse(self.app.state.running)
        original = Path.cwd()
        try:
            os.chdir(game.IMAGE_DIR)
            self.assertEqual(load_image('hansung_morning.png', height=360).get_size(),
                             (960, 360))
        finally:
            os.chdir(original)

    def test_day_night_boundaries_and_return(self):
        app = self.app
        app.state.player_y = -1000
        # 실제 update 경로로 30초 전까지 진행한다.
        for _ in range(299):
            app.update(0.1)
        self.assertEqual(app.state.night_alpha, 0)
        app.update(0.1)
        self.assertAlmostEqual(app.state.background_elapsed, 30)
        self.assertEqual(app.state.night_alpha, 0)
        app.update_background(1.5)
        self.assertIn(app.state.night_alpha, (127, 128))
        app.update_background(1.5)
        self.assertEqual(app.state.night_alpha, 255)
        self.assertEqual(pygame.image.tobytes(app.view.stage, 'RGB'),
                         pygame.image.tobytes(app.view.night_stage, 'RGB'))
        app.update_background(27)
        self.assertEqual(app.state.night_alpha, 255)
        app.update_background(1.5)
        self.assertIn(app.state.night_alpha, (127, 128))
        app.update_background(1.5)
        self.assertEqual(app.state.night_alpha, 0)
        self.assertEqual(pygame.image.tobytes(app.view.stage, 'RGB'),
                         pygame.image.tobytes(app.view.day_stage, 'RGB'))

    def test_background_freeze_reset_and_long_frame(self):
        app = self.app
        app.state.player_y = -1000
        app.update(31.5)
        self.assertAlmostEqual(app.state.background_elapsed, 31.5)
        self.assertIn(app.state.night_alpha, (127, 128))
        self.assertAlmostEqual(app.state.background_x, -36)
        frozen = (app.state.background_elapsed, app.state.night_alpha,
                  pygame.image.tobytes(app.view.stage, 'RGB'))
        for flag in ('paused', 'game_over'):
            setattr(app.state, flag, True)
            app.update(10)
            self.assertEqual(frozen, (app.state.background_elapsed, app.state.night_alpha,
                                     pygame.image.tobytes(app.view.stage, 'RGB')))
            setattr(app.state, flag, False)
        app.reset()
        self.assertEqual((app.state.background_elapsed, app.state.night_alpha, app.state.background_x), (0, 0, 0))
        self.assertEqual(pygame.image.tobytes(app.view.stage, 'RGB'),
                         pygame.image.tobytes(app.view.day_stage, 'RGB'))

    def test_fade_pixels_scroll_alignment_and_monotonicity(self):
        app = self.app
        app.state.player_y = -1000
        app.state.obstacle_y = -1000
        app.update_background(30)
        values = []
        for _ in range(30):
            app.update_background(0.1)
            values.append(app.state.night_alpha)
        self.assertEqual(values, sorted(values))
        self.assertEqual(values[-1], 255)
        app.reset()
        app.state.player_y = app.state.obstacle_y = -1000
        app.update_background(31.5)
        app.state.background_x = -959
        app.draw()
        expected = app.view.day_stage.copy()
        overlay = app.view.night_stage.copy()
        overlay.set_alpha(app.state.night_alpha)
        expected.blit(overlay, (0, 0))
        for x in (0, 240, 479):
            source_x = (x + 959) % app.state.background_width
            self.assertEqual(app.view.screen.get_at((x, 150)), expected.get_at((source_x, 150)))
        self.assertIsNone(app.view.stage.get_alpha())

    def test_seasonal_assets(self):
        for season in ('spring', 'summer', 'autumn', 'winter'):
            for time in ('morning', 'night'):
                image = load_image(f'hansung_{season}_{time}.png')
                self.assertEqual(image.get_size(), (2048, 768))
                self.assertEqual(pygame.mask.from_surface(image).count(), 2048 * 768)
        for time in ('morning', 'night'):
            active = load_image(f'hansung_{time}.png')
            spring = load_image(f'hansung_spring_{time}.png')
            self.assertEqual(pygame.image.tobytes(active, 'RGB'),
                             pygame.image.tobytes(spring, 'RGB'))


class BackendTests(unittest.TestCase):
    def test_rules_and_storage_without_display_or_images(self):
        """백은 화면·이미지·폰트를 준비하지 않아도 움직임과 기록을 처리한다."""
        pygame.quit()
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / 'score.txt'
            sizes = {name: (80, game.OBSTACLE_HEIGHTS[name])
                     for name in game.OBSTACLE_FILES}
            with patch.object(pygame.display, 'set_mode', side_effect=AssertionError('화면 접근')), \
                 patch.object(pygame.image, 'load', side_effect=AssertionError('이미지 접근')):
                state = backend.GameState((90, 120), sizes, 4, 960, record)
                state.obstacle_y = -1000
                state.jump()
                state.update(0.1)
                self.assertLess(state.player_y, state.ground_y)
                state.paused = True
                frozen = (state.player_y, state.background_elapsed)
                state.update(10)
                self.assertEqual((state.player_y, state.background_elapsed), frozen)
                state.score = 42
                state.stop()
                restored = backend.GameState((90, 120), sizes, 4, 960, record)
                self.assertEqual(restored.high_score, 42)


if __name__ == '__main__':
    unittest.main()
