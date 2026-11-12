"""알파 픽셀·마스크 충돌과 게임오버·재시작 검사."""
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
    from .. import config
    from ..assets import collision_mask
    from ..main import HansungRun
else:
    import config
    from assets import collision_mask
    from main import HansungRun


def opaque_pixels(image):
    return {(x, y) for y in range(image.get_height()) for x in range(image.get_width())
            if image.get_at((x, y)).a > config.COLLISION_ALPHA_THRESHOLD}


def inset_pixels(pixels, radius):
    # pygame.Mask를 사용하지 않는 독립적인 기준 결과.
    return {(x, y) for x, y in pixels
            if all((x + dx, y + dy) in pixels
                   for dx in range(-radius, radius + 1)
                   for dy in range(-radius, radius + 1))}


class MaskCollisionTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = HansungRun(Path(directory.name) / 'score.txt')

    def test_alpha_threshold_holes_and_inset(self):
        image = pygame.Surface((9, 9), pygame.SRCALPHA)
        image.fill((255, 255, 255, 255), (1, 1, 7, 7))
        image.set_at((4, 4), (255, 255, 255, 0))
        image.set_at((0, 0), (255, 255, 255, 127))
        image.set_at((8, 8), (255, 255, 255, 128))
        for radius in (0, 1, 2):
            mask = collision_mask(image, radius)
            expected = inset_pixels(opaque_pixels(image), radius)
            actual = {(x, y) for y in range(9) for x in range(9) if mask.get_at((x, y))}
            self.assertEqual(actual, expected)

    def test_real_images_match_pixel_oracle_and_game_over(self):
        app = self.app
        cases = 0
        for name, obstacle in app.view.obstacle_images.items():
            raw = opaque_pixels(obstacle)
            radius = max(1, round(obstacle.get_height() * config.OBSTACLE_MASK_INSET_RATIO))
            reduced = inset_pixels(raw, radius)
            self.assertTrue(reduced)
            self.assertLess(len(reduced), len(raw))
            for index, frame in enumerate(app.view.run_frames):
                player = opaque_pixels(frame)
                for player_y in (200, 242, 300):
                    for x in (-20, 0, 40, 60, 80, 100, 120):
                        for shrink, pixels in ((False, raw), (True, reduced)):
                            with self.subTest(name=name, frame=index, y=player_y, x=x, shrink=shrink):
                                app.reset()
                                state = app.state
                                # 이 검사는 각 이미지의 첫 포즈를 독립적으로 대조한다.
                                state.obstacle_frame_masks = {}
                                state.obstacle_name = name
                                state.obstacle_size = obstacle.get_size()
                                state.obstacle_y = 360 - obstacle.get_height() + config.OBSTACLE_GROUND_OFFSET
                                state.obstacle_x = x
                                state.player_y = player_y
                                state.animation_tick = index * config.RUN_FRAME_TICKS
                                state.obstacle_masks = dict(app.view.obstacle_masks)
                                state.obstacle_masks[name] = collision_mask(obstacle, radius if shrink else 0)
                                dy = state.obstacle_y - player_y
                                expected = any((ox + x, oy + dy) in player for ox, oy in pixels)
                                self.assertEqual(state.collides_with_obstacle(), expected)
                                state.update_step(0)
                                self.assertEqual(state.game_over, expected)
                                cases += 1
        self.assertEqual(cases, len(app.view.obstacle_images) * 168)

    def test_edge_contact_is_forgiven_but_body_contact_ends_game(self):
        app = self.app
        for name in config.OBSTACLE_FILES:
            image = app.view.obstacle_images[name]
            with self.subTest(name=name):
                app.reset()
                state = app.state
                state.obstacle_name = name
                state.obstacle_size = image.get_size()
                state.obstacle_y = 360 - image.get_height() + config.OBSTACLE_GROUND_OFFSET
                player = app.view.player_masks[0]
                raw = collision_mask(image)
                dy = state.obstacle_y - int(state.player_y)
                contacts = [x for x in range(150, -1, -1)
                            if player.overlap(raw, (x, dy)) is not None]
                self.assertTrue(contacts)
                state.obstacle_x = contacts[0]
                self.assertFalse(state.collides_with_obstacle())
                state.update_step(0)
                self.assertFalse(state.game_over)
                # 오른쪽에서 실제 이동시키면 안쪽 윤곽에 닿은 순간 종료한다.
                for _ in range(150):
                    state.update(1 / 120)
                    if state.game_over:
                        break
                self.assertTrue(state.game_over)
                offset = (int(state.obstacle_x), int(state.obstacle_y) - int(state.player_y))
                self.assertIsNotNone(app.view.player_masks[state.player_frame_index].overlap(raw, offset))
                self.assertTrue(state.collides_with_obstacle())

    def test_timed_jump_clears_every_obstacle_at_multiple_frame_rates(self):
        for name in config.OBSTACLE_FILES:
            for hz in (30, 60, 120):
                with self.subTest(name=name, hz=hz):
                    self.app.reset()
                    state = self.app.state
                    state.obstacle_name = name
                    state.obstacle_size = self.app.view.obstacle_images[name].get_size()
                    state.obstacle_y = 360 - state.obstacle_size[1] + config.OBSTACLE_GROUND_OFFSET
                    state.obstacle_x = 160
                    state.jump()
                    for _ in range(hz):
                        self.app.update(1 / hz)
                        self.assertFalse(state.game_over)
                    self.assertFalse(state.is_jumping)
                    self.assertEqual(state.score, config.PASS_BONUS + config.SURVIVAL_POINTS_PER_SECOND)

    def test_jump_frame_and_fractional_coordinates_match_rendering(self):
        app = self.app
        state = app.state
        state.animation_tick = 3 * config.RUN_FRAME_TICKS
        state.is_jumping = True
        state.player_y = 222.8
        state.obstacle_x = -1.8
        self.assertEqual(state.player_frame_index, 0)
        with patch.object(app.view, 'screen', wraps=app.view.screen) as screen:
            app.draw()
            calls = screen.blit.call_args_list
            self.assertEqual(calls[2].args[1], (-1, int(state.obstacle_y)))
            self.assertIs(calls[3].args[0], app.view.run_frames[0])
            self.assertEqual(calls[3].args[1], (0, 222))
        expected = app.view.player_masks[0].overlap(
            app.view.obstacle_masks[state.obstacle_name], (-1, int(state.obstacle_y) - 222)) is not None
        self.assertEqual(state.collides_with_obstacle(), expected)


class CollisionLifecycleTests(unittest.TestCase):
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

    def test_collision_freeze_and_restart(self):
        app = self.app
        app.state.obstacle_x = 60
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


if __name__ == '__main__':
    unittest.main()
