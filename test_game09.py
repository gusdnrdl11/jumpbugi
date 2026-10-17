"""화면을 열지 않고 실행: python -B -m unittest -v test_game09"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
import game09 as game


class GameTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.record = Path(directory.name) / 'high_score.txt'
        self.app = game.HansungRun(self.record)
        pygame.event.clear()

    def key(self, value):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=value))
        self.app.handle_events()

    def test_scroll_speed_wrap_and_screen_coverage(self):
        app = self.app
        self.assertEqual(app.stage.get_size(), (960, 360))
        app.player_y = -1000  # 재등장 시 장애물의 지면 위치가 갱신되어도 충돌을 피한다.
        for frame in range(1, 482):
            previous = app.obstacle_x
            previous_width = app.obstacle_image.get_width()
            app.update()
            self.assertEqual(app.background_x, -((frame * 6) % 960))
            if previous - 6 + previous_width >= 0:
                self.assertEqual(app.obstacle_x, previous - 6)
            else:
                self.assertEqual(app.obstacle_x, 480)
            # 실제 출력 픽셀을 원본의 순환 좌표와 비교해 빈 공간과 좌표 오차를 검사한다.
            app.draw()
            for x in (0, 240, 479):
                source_x = (x - app.background_x) % 960
                self.assertEqual(app.screen.get_at((x, 150)),
                                 app.stage.get_at((source_x, 150)))

    def test_jump_landing_and_no_double_jump(self):
        app = self.app
        app.obstacle_y = -1000
        self.key(pygame.K_SPACE)
        app.update()
        self.assertLess(app.player_y, app.ground_y)
        velocity = app.velocity_y
        self.key(pygame.K_SPACE)
        self.assertEqual(app.velocity_y, velocity)
        for _ in range(100):
            app.update()
        self.assertEqual(app.player_y, app.ground_y)
        self.assertFalse(app.is_jumping)

    def test_collision_freeze_and_restart(self):
        app = self.app
        app.obstacle_x = 0
        app.update()
        self.assertTrue(app.game_over)
        frozen = (app.background_x, app.obstacle_x, app.player_y, app.score)
        self.key(pygame.K_SPACE)
        app.update()
        self.assertEqual(frozen, (app.background_x, app.obstacle_x, app.player_y, app.score))
        self.key(pygame.K_RETURN)
        self.assertFalse(app.game_over)
        self.assertEqual((app.background_x, app.obstacle_x, app.score), (0, 480, 0))
        self.assertEqual((app.player_y, app.velocity_y, app.is_jumping),
                         (app.ground_y, 0, False))

    def test_bonus_once_respawn_and_high_score_persistence(self):
        app = self.app
        self.assertEqual(app.high_score, 0)
        self.assertFalse(self.record.exists())
        app.obstacle_x = -app.obstacle_image.get_width() + game.OBSTACLE_SPEED
        app.update()
        self.assertEqual((app.score, app.high_score), (10, 0))
        self.assertFalse(self.record.exists())
        app.update()
        self.assertEqual(app.score, 10)
        self.assertEqual(app.obstacle_x, 480)
        self.assertFalse(app.passed)
        # 실제 충돌로 판을 종료했을 때만 새 기록이 표시·저장된다.
        app.obstacle_x = 0
        app.update()
        self.assertTrue(app.game_over)
        self.assertEqual(app.high_score, 10)
        app.reset()
        self.assertEqual((app.score, app.high_score), (0, 10))
        self.assertEqual(game.HansungRun(self.record).high_score, 10)
        app.score = 5
        app.record_high_score()
        self.assertEqual(self.record.read_text(), '10')
        app.score = 120
        app.record_high_score()
        self.assertEqual(game.HansungRun(self.record).high_score, 120)
        self.assertFalse(self.record.with_suffix('.tmp').exists())

    def test_running_legs_only_and_animation_freeze(self):
        app = self.app
        self.assertEqual(len(app.run_frames), 4)
        width, height = app.player_image.get_size()
        leg_top = int(height * game.LEG_START_RATIO)
        upper = pygame.image.tobytes(app.run_frames[0].subsurface((0, 0, width, leg_top)), 'RGBA')
        legs = set()
        for frame in app.run_frames:
            self.assertEqual(frame.get_size(), (width, height))
            self.assertEqual(pygame.image.tobytes(frame.subsurface((0, 0, width, leg_top)), 'RGBA'), upper)
            legs.add(pygame.image.tobytes(frame.subsurface((0, leg_top, width, height-leg_top)), 'RGBA'))
        self.assertEqual(len(legs), 4)
        for _ in range(game.RUN_FRAME_TICKS):
            app.update()
        self.assertEqual(app.animation_tick // game.RUN_FRAME_TICKS, 1)
        self.key(pygame.K_SPACE)
        frozen = app.animation_tick
        app.update()
        self.assertEqual(app.animation_tick, frozen)
        app.game_over = True
        app.update()
        self.assertEqual(app.animation_tick, frozen)

    def test_each_random_obstacle_collision_and_reuse(self):
        app = self.app
        for name in game.OBSTACLE_FILES:
            with patch.object(game.random, 'choice', return_value=name) as choose:
                app.reset()
                choose.assert_called_once_with(game.OBSTACLE_FILES)
                self.assertEqual(app.obstacle_name, name)
                self.assertIs(app.obstacle_image, app.obstacle_images[name])
                self.assertEqual(app.obstacle_image.get_height(), game.OBSTACLE_HEIGHTS[name])
                app.obstacle_x = 0
                app.update()
                self.assertTrue(app.game_over)
                app.reset()
                app.obstacle_x = -app.obstacle_image.get_width() - 1
                app.update()
                self.assertEqual(app.obstacle_name, name)
                self.assertEqual(app.obstacle_x, 480)

    def test_exit_records_score_once(self):
        for event in (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE),
                      pygame.event.Event(pygame.QUIT)):
            self.app.running = True
            self.app.score += 10
            pygame.event.post(event)
            self.app.handle_events()
            self.assertFalse(self.app.running)
            self.assertEqual(int(self.record.read_text()), self.app.score)

    def test_small_sangjji_size_ground_and_jump_clearance(self):
        app = self.app
        with patch.object(game.random, 'choice', return_value='sangjji.png'):
            app.reset()
        self.assertEqual(app.obstacle_image.get_size(), (39, 40))
        self.assertEqual(app.obstacle_y, 327)
        rect = app.obstacle_image.get_rect(topleft=(60, app.obstacle_y))
        hitbox = rect.inflate(*app.obstacle_hitbox_shrink)
        self.assertGreater(hitbox.width, 0)
        self.assertGreater(hitbox.height, 0)
        self.assertEqual(rect.bottom, 367)
        app.obstacle_x = 60
        self.key(pygame.K_SPACE)
        app.update()
        self.assertFalse(app.game_over)
        # 점프하지 않으면 작은 상찌도 실제로 부딪혀야 한다.
        app.reset()
        with patch.object(game.random, 'choice', return_value='sangjji.png'):
            app.spawn_obstacle()
        app.obstacle_x = 60
        app.update()
        self.assertTrue(app.game_over)

    def test_hud_layout_and_game_over_drawing(self):
        app = self.app
        app.screen = Mock(wraps=app.screen)
        for score in (0, 120, 999999):
            app.screen.reset_mock()
            app.score = app.high_score = score
            app.draw()
            calls = app.screen.blit.call_args_list
            best, current = calls[4].args[1], calls[5].args[1]
            self.assertEqual((current.right, current.top, best.top), (470, 10, 10))
            self.assertEqual(best.right + 20, current.left)
            self.assertGreaterEqual(best.left, 0)
        app.game_over = True
        app.screen.reset_mock()
        app.draw()
        self.assertEqual(app.screen.blit.call_count, 8)

    def test_exit_and_resource_path(self):
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.app.running)
        self.app.running = True
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.app.run()
        self.assertFalse(self.app.running)
        original = Path.cwd()
        try:
            os.chdir(game.IMAGE_DIR)
            self.assertEqual(game.load_image('hansung_morning.png', height=360).get_size(),
                             (960, 360))
        finally:
            os.chdir(original)


if __name__ == '__main__':
    unittest.main()
