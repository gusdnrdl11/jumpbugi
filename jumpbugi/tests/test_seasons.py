"""계절별 낮·밤 순서, 전환 픽셀, 순환·정지·재시작 회귀 검사."""
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
    from .. import config
    from ..assets import load_image
    from ..main import JumpBugi
    from ..difficulty import speed_multiplier_for_slot
else:
    import config
    from assets import load_image
    from main import JumpBugi
    from difficulty import speed_multiplier_for_slot


class SeasonCycleTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = JumpBugi(Path(directory.name) / 'score.txt')
        self.app.reset()

    def at(self, seconds):
        self.app.reset()
        self.app.update_background(seconds)
        return self.app.state

    def assert_stage_pixels(self, expected):
        self.assertEqual(pygame.image.tobytes(self.app.view.stage, 'RGB'),
                         pygame.image.tobytes(expected, 'RGB'))

    def test_background_asset_order_and_display_sizes(self):
        expected = tuple(f'hansung_{season}_{time}.png'
                         for season in ('spring', 'summer', 'autumn', 'winter')
                         for time in ('morning', 'night'))
        self.assertEqual(config.BACKGROUND_FILES, expected)
        self.assertEqual(len(self.app.view.background_stages), 8)
        for stage in self.app.view.background_stages:
            self.assertEqual(stage.get_size(), config.BACKGROUND_SIZE)
            self.assertIsNone(stage.get_alpha())
        state = self.at(0)
        self.assertEqual((state.background_from_index, state.background_to_index,
                          state.background_alpha), (0, 0, 0))
        self.assert_stage_pixels(self.app.view.background_stages[0])

    def test_all_boundaries_and_fade_pixels_over_two_cycles(self):
        interval = config.DAY_NIGHT_INTERVAL
        fade = config.BACKGROUND_FADE_SECONDS
        for transition in range(1, 17):
            source = (transition - 1) % 8
            target = transition % 8
            with self.subTest(transition=transition, phase='before'):
                state = self.at(transition * interval - 0.001)
                self.assertEqual(state.background_to_index, source)
                self.assert_stage_pixels(self.app.view.background_stages[source])
            with self.subTest(transition=transition, phase='start'):
                state = self.at(transition * interval)
                self.assertEqual((state.background_from_index, state.background_to_index,
                                  state.background_alpha), (source, target, 0))
                self.assert_stage_pixels(self.app.view.background_stages[source])
            with self.subTest(transition=transition, phase='midpoint'):
                state = self.at(transition * interval + fade / 2)
                self.assertEqual((state.background_from_index, state.background_to_index),
                                 (source, target))
                self.assertIn(state.background_alpha, (127, 128))
                expected = self.app.view.background_stages[source].copy()
                overlay = self.app.view.background_stages[target].copy()
                overlay.set_alpha(state.background_alpha)
                expected.blit(overlay, (0, 0))
                self.assert_stage_pixels(expected)
                self.assertIsNone(self.app.view.stage.get_alpha())
            with self.subTest(transition=transition, phase='complete'):
                state = self.at(transition * interval + fade)
                self.assertEqual(state.background_alpha, 255)
                self.assert_stage_pixels(self.app.view.background_stages[target])

    def test_winter_returns_to_spring_without_resetting_speed(self):
        cycle_seconds = config.SLOTS_PER_CYCLE * config.DAY_NIGHT_INTERVAL
        state = self.at(cycle_seconds)
        self.assertEqual((state.background_from_index, state.background_to_index), (7, 0))
        self.assert_stage_pixels(self.app.view.background_stages[7])
        self.assertAlmostEqual(state.speed_multiplier, speed_multiplier_for_slot(8))
        self.app.update_background(config.BACKGROUND_FADE_SECONDS)
        self.assert_stage_pixels(self.app.view.background_stages[0])
        self.assertAlmostEqual(state.speed_multiplier, speed_multiplier_for_slot(8))
        self.assertEqual(state.background_elapsed, cycle_seconds + config.BACKGROUND_FADE_SECONDS)

    def test_same_alpha_different_pairs_invalidates_render_cache(self):
        self.at(config.DAY_NIGHT_INTERVAL + config.BACKGROUND_FADE_SECONDS)
        first = pygame.image.tobytes(self.app.view.stage, 'RGB')
        self.app.update_background(2 * config.DAY_NIGHT_INTERVAL)
        state = self.app.state
        self.assertEqual((state.background_from_index, state.background_to_index,
                          state.background_alpha), (2, 3, 255))
        self.assert_stage_pixels(self.app.view.background_stages[3])
        self.assertNotEqual(first, pygame.image.tobytes(self.app.view.stage, 'RGB'))

    def test_large_update_pause_game_over_and_restart(self):
        state = self.app.state
        state.player_y = -1000
        midpoint = 27 * config.DAY_NIGHT_INTERVAL + config.BACKGROUND_FADE_SECONDS / 2
        self.app.update(midpoint)
        self.assertAlmostEqual(state.background_elapsed, midpoint)
        self.assertEqual((state.background_from_index, state.background_to_index), (2, 3))
        self.assertIn(state.background_alpha, (127, 128))
        frozen = (state.background_elapsed, state.background_from_index,
                  state.background_to_index, state.background_alpha,
                  pygame.image.tobytes(self.app.view.stage, 'RGB'))
        for flag in ('paused', 'game_over'):
            setattr(state, flag, True)
            self.app.update(120)
            self.assertEqual((state.background_elapsed, state.background_from_index,
                              state.background_to_index, state.background_alpha,
                              pygame.image.tobytes(self.app.view.stage, 'RGB')), frozen)
            setattr(state, flag, False)
        self.app.reset()
        self.assertEqual((state.background_elapsed, state.background_from_index,
                          state.background_to_index, state.background_alpha,
                          state.speed_multiplier), (0, 0, 0, 0, 1))
        self.assert_stage_pixels(self.app.view.background_stages[0])

    def test_transitions_and_drawing_do_not_reload_images(self):
        with patch.object(pygame.image, 'load', side_effect=AssertionError('실행 중 이미지 재로딩')):
            for step in range(17):
                self.app.update_background(config.DAY_NIGHT_INTERVAL)
                self.app.draw()
                self.app.update_background(config.BACKGROUND_FADE_SECONDS / 2)
                self.app.draw()


class BackgroundTransitionTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.record = Path(directory.name) / 'high_score.txt'
        self.app = JumpBugi(self.record)
        self.app.reset()
        pygame.event.clear()

    def test_spring_night_and_summer_day_boundaries(self):
        app = self.app
        app.state.player_y = -1000
        # 실제 update 경로로 첫 슬롯 경계 직전까지 진행한다.
        for _ in range(round(config.DAY_NIGHT_INTERVAL * 10) - 1):
            app.update(0.1)
        self.assertEqual(app.state.night_alpha, 0)
        app.update(0.1)
        self.assertAlmostEqual(app.state.background_elapsed, config.DAY_NIGHT_INTERVAL)
        self.assertEqual(app.state.night_alpha, 0)
        app.update_background(config.BACKGROUND_FADE_SECONDS / 2)
        self.assertIn(app.state.night_alpha, (127, 128))
        app.update_background(config.BACKGROUND_FADE_SECONDS / 2)
        self.assertEqual(app.state.night_alpha, 255)
        self.assertEqual(pygame.image.tobytes(app.view.stage, 'RGB'),
                         pygame.image.tobytes(app.view.background_stages[1], 'RGB'))
        app.update_background(config.DAY_NIGHT_INTERVAL - config.BACKGROUND_FADE_SECONDS)
        self.assertEqual(app.state.night_alpha, 255)
        app.update_background(config.BACKGROUND_FADE_SECONDS / 2)
        self.assertIn(app.state.night_alpha, (127, 128))
        app.update_background(config.BACKGROUND_FADE_SECONDS / 2)
        self.assertEqual(app.state.night_alpha, 0)
        self.assertEqual(pygame.image.tobytes(app.view.stage, 'RGB'),
                         pygame.image.tobytes(app.view.background_stages[2], 'RGB'))

    def test_background_freeze_reset_and_long_frame(self):
        app = self.app
        app.state.player_y = -1000
        midpoint = config.DAY_NIGHT_INTERVAL + config.BACKGROUND_FADE_SECONDS / 2
        app.update(midpoint)
        self.assertAlmostEqual(app.state.background_elapsed, midpoint)
        self.assertIn(app.state.night_alpha, (127, 128))
        self.assertAlmostEqual(app.state.background_x, -config.BACKGROUND_SPEED * config.PHYSICS_HZ
                               * 0.1 * (1 + config.EARLY_SPEED_INCREASE))
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
                         pygame.image.tobytes(app.view.background_stages[0], 'RGB'))

    def test_fade_pixels_scroll_alignment_and_monotonicity(self):
        app = self.app
        app.state.player_y = -1000
        app.state.obstacle_y = -1000
        app.update_background(config.DAY_NIGHT_INTERVAL)
        values = []
        for _ in range(round(config.BACKGROUND_FADE_SECONDS * 10)):
            app.update_background(0.1)
            values.append(app.state.night_alpha)
        self.assertEqual(values, sorted(values))
        self.assertEqual(values[-1], 255)
        app.reset()
        app.state.player_y = app.state.obstacle_y = -1000
        app.update_background(config.DAY_NIGHT_INTERVAL + config.BACKGROUND_FADE_SECONDS / 2)
        app.state.background_x = -959
        app.draw()
        expected = app.view.background_stages[0].copy()
        overlay = app.view.background_stages[1].copy()
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


if __name__ == '__main__':
    unittest.main()
