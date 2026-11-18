"""게임 실행·입력·플레이어 모션·화면 출력과 백엔드 분리 검사."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

if __package__ and __package__.startswith('jumpbugi.'):
    from .. import config, backend
    from ..assets import load_image
    from ..main import JumpBugi
    from ..storage import load_high_score
else:
    import config, backend
    from assets import load_image
    from main import JumpBugi
    from storage import load_high_score


class GameTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.directory = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.score_path = Path(self.directory.name) / 'scores' / 'best.txt'
        self.game = JumpBugi(self.score_path)
        self.game.reset()
        pygame.event.clear()

    def tearDown(self):
        pygame.quit()
        self.directory.cleanup()

    def key(self, key):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
        self.game.handle_events()

    def test_render_jump_pause_and_restart(self):
        self.game.draw()
        self.key(pygame.K_SPACE)
        self.game.update()
        self.assertLess(self.game.state.player_y, self.game.state.ground_y)
        self.key(pygame.K_ESCAPE)
        position = self.game.state.player_y
        self.game.update()
        self.assertEqual(self.game.state.player_y, position)
        self.game.draw()
        self.key(pygame.K_ESCAPE)
        self.game.state.obstacle_x = 10000
        for _ in range(60):
            self.game.update()
        self.assertFalse(self.game.state.is_jumping)
        self.game.state.obstacle_x = 60
        self.game.update()
        self.assertTrue(self.game.state.game_over)
        self.game.draw()
        self.key(pygame.K_RETURN)
        self.assertFalse(self.game.state.game_over)
        self.assertEqual(self.game.state.score, 0)

    def test_score_background_and_main_loop_exit(self):
        self.game.state.obstacle_x = -self.game.state.obstacle_size[0]
        self.game.update()
        self.assertEqual(self.game.state.score, 10)
        self.game.update_background(config.DAY_NIGHT_INTERVAL + config.BACKGROUND_FADE_SECONDS)
        self.assertEqual(self.game.state.night_alpha, 255)
        self.game.draw()
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.game.run()
        self.assertFalse(self.game.state.running)
        self.assertEqual(load_high_score(self.score_path), 10)


class GameBehaviorTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.record = Path(directory.name) / 'high_score.txt'
        self.app = JumpBugi(self.record)
        self.app.reset()
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
            self.assertEqual(app.state.background_x, -((frame * config.BACKGROUND_SPEED) % 960))
            if previous - config.OBSTACLE_SPEED + previous_width >= 0:
                self.assertEqual(app.state.obstacle_x, previous - config.OBSTACLE_SPEED)
            else:
                self.assertEqual(app.state.obstacle_x, app.state.obstacle_spawn_x)
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
        for _ in range(config.RUN_FRAME_TICKS):
            app.update()
        self.assertEqual(app.state.animation_tick // config.RUN_FRAME_TICKS, 1)
        app.state.obstacle_y = -1000
        for expected in (2, 3, 0):
            for _ in range(config.RUN_FRAME_TICKS):
                app.update()
            self.assertEqual(app.state.animation_tick // config.RUN_FRAME_TICKS, expected)
        self.key(pygame.K_SPACE)
        frozen = app.state.animation_tick
        app.update()
        self.assertEqual(app.state.animation_tick, frozen)
        app.state.game_over = True
        app.update()
        self.assertEqual(app.state.animation_tick, frozen)

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
            os.chdir(config.IMAGE_DIR)
            self.assertEqual(load_image('hansung_morning.png', height=360).get_size(),
                             (960, 360))
        finally:
            os.chdir(original)


class BackendTests(unittest.TestCase):
    def test_rules_and_storage_without_display_or_images(self):
        """백은 화면·이미지·폰트를 준비하지 않아도 움직임과 기록을 처리한다."""
        pygame.quit()
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / 'score.txt'
            sizes = {name: (80, config.OBSTACLE_HEIGHTS[name])
                     for name in config.OBSTACLE_FILES}
            masks = dict(player_masks=[pygame.Mask((90, 120), fill=True) for _ in range(4)],
                         obstacle_masks={name: pygame.Mask(size, fill=True)
                                         for name, size in sizes.items()})
            with patch.object(pygame.display, 'set_mode', side_effect=AssertionError('화면 접근')), \
                 patch.object(pygame.image, 'load', side_effect=AssertionError('이미지 접근')):
                state = backend.GameState((90, 120), sizes, 4, 960, record, **masks)
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
                restored = backend.GameState((90, 120), sizes, 4, 960, record, **masks)
                self.assertEqual(restored.high_score, 42)


if __name__ == '__main__':
    unittest.main()
