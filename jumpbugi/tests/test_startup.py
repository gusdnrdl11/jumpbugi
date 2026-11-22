"""첫 실행 연출, 배경 페이드, 달리기 연속성과 재시작을 검사한다."""
import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

if __package__ and __package__.startswith('jumpbugi.'):
    from ..desktop_prototype import config
    from ..desktop_prototype.assets import intro_content_rect, prepare_intro_cover
    from ..desktop_prototype.main import JumpBugi
else:
    from desktop_prototype import config
    from desktop_prototype.assets import intro_content_rect, prepare_intro_cover
    from desktop_prototype.main import JumpBugi


class StartupTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.record = Path(directory.name) / 'score.txt'
        self.app = JumpBugi(self.record)
        pygame.event.clear()

    def key(self, key, mod=0):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod))
        self.app.handle_events()

    def snapshot(self):
        state = self.app.state
        return (state.score, state.survival_elapsed, state.background_elapsed,
                state.background_x, state.obstacle_x, state.obstacle_name,
                state.animation_tick, state.player_y, state.is_jumping, state.paused)

    def ready(self):
        self.app.update(config.SPLASH_SECONDS)
        self.assertEqual(self.app.phase, 'ready')

    def test_first_image_covers_screen_without_clipping_main_content(self):
        self.assertEqual(self.app.phase, 'splash')
        self.assertEqual(pygame.display.get_caption()[0], config.GAME_TITLE)
        self.assertTrue((config.IMAGE_DIR / config.START_IMAGE_FILE).is_file())
        source_bytes = (config.IMAGE_DIR / config.START_IMAGE_FILE).read_bytes()
        source = pygame.image.load(str(config.IMAGE_DIR / config.START_IMAGE_FILE)).convert_alpha()
        image = self.app.view.start_image
        prepared_pixels = pygame.image.tobytes(image, 'RGBA')
        self.assertEqual(self.app.view.screen.get_size(), config.SCREEN_SIZE)
        self.assertEqual(image.get_size(), config.SCREEN_SIZE)
        source_content = intro_content_rect(source)
        self.assertTrue(source.get_rect().contains(source_content))
        self.assertLess(source_content.width, source.get_width())
        self.assertLess(source_content.height, source.get_height())
        # 제목이 포함된 시작 그림에 별도 텍스트를 겹치지 않는다.
        # 원본과 준비한 cover 표면은 보존하고 이전 프레임은 모두 덮는다.
        self.app.view.screen.fill((255, 0, 255))
        self.app.draw()
        self.assertEqual(pygame.image.tobytes(self.app.view.screen, 'RGB'),
                         pygame.image.tobytes(image, 'RGB'))
        self.assertEqual(pygame.image.tobytes(image, 'RGBA'), prepared_pixels)
        self.assertEqual((config.IMAGE_DIR / config.START_IMAGE_FILE).read_bytes(), source_bytes)
        for x, y in ((0, 0), (479, 0), (0, 359), (479, 359), (240, 240)):
            self.assertEqual(self.app.view.screen.get_at((x, y)), image.get_at((x, y)))
        edges = ([(x, 0) for x in range(image.get_width())]
                 + [(x, image.get_height() - 1) for x in range(image.get_width())]
                 + [(0, y) for y in range(image.get_height())]
                 + [(image.get_width() - 1, y) for y in range(image.get_height())])
        for x, y in edges:
            self.assertEqual(image.get_at((x, y)).a, 255)
        # 현재 일러스트는 다섯 캐릭터와 소품이 안전 여백 안에 들어오면서도
        # 예전 360x270 contain 화면보다 크게 표시되어야 한다.
        visible_content = intro_content_rect(image)
        self.assertGreater(visible_content.left, 0)
        self.assertGreater(visible_content.top, 0)
        self.assertLess(visible_content.right, image.get_width())
        self.assertLess(visible_content.bottom, image.get_height())
        self.assertGreater(visible_content.width, image.get_width() * 0.9)
        self.assertGreater(visible_content.height, image.get_height() * 0.8)

    def test_ready_keeps_only_start_and_control_prompts_above_player(self):
        view = self.app.view
        self.app.draw()
        splash = pygame.image.tobytes(view.screen, 'RGB')
        self.ready()
        self.app.draw()
        self.assertNotEqual(pygame.image.tobytes(view.screen, 'RGB'), splash)
        # 입력 대기 화면 상부에는 시작 안내·조작 안내만 표시한다.
        expected = pygame.Surface(config.SCREEN_SIZE)
        expected.fill((255, 255, 255))
        center_x = config.SCREEN_SIZE[0] // 2
        for text, y in ((view.start_text, 160), (view.controls_text, 200)):
            expected.blit(text, text.get_rect(center=(center_x, y)))
        upper = pygame.Rect(0, 0, config.SCREEN_SIZE[0], 220)
        self.assertEqual(pygame.image.tobytes(view.screen.subsurface(upper), 'RGB'),
                         pygame.image.tobytes(expected.subsurface(upper), 'RGB'))
        old_title_area = pygame.Rect(0, 65, config.SCREEN_SIZE[0], 50)
        self.assertEqual(pygame.mask.from_surface(view.startup_labels.subsurface(old_title_area)).count(), 0)
        view.draw_startup('transition', 0, 0, background_x=-137)
        self.assertEqual(pygame.image.tobytes(view.screen.subsurface(upper), 'RGB'),
                         pygame.image.tobytes(expected.subsurface(upper), 'RGB'))

    def test_intro_content_bounds_ignore_transparent_faint_and_near_white_padding(self):
        source = pygame.Surface((240, 180), pygame.SRCALPHA)
        source.fill((0, 0, 0, 0))
        pygame.draw.rect(source, (20, 70, 90, 96), (12, 12, 216, 156))
        pygame.draw.rect(source, (248, 250, 252, 255), (24, 24, 192, 132))
        pygame.draw.rect(source, (20, 70, 90, 255), (60, 50, 120, 80))
        original = pygame.image.tobytes(source, 'RGBA')
        self.assertEqual(intro_content_rect(source), pygame.Rect(60, 50, 120, 80))
        image = prepare_intro_cover(source, config.SCREEN_SIZE)
        self.assertEqual(image.get_size(), config.SCREEN_SIZE)
        self.assertEqual(pygame.image.tobytes(source, 'RGBA'), original)

    def test_intro_cover_keeps_circles_round_and_crops_wide_and_tall_sources_centrally(self):
        target_size = (120, 90)
        background = (20, 60, 100, 255)
        for source_size in ((240, 120), (120, 240)):
            with self.subTest(source_size=source_size):
                source = pygame.Surface(source_size, pygame.SRCALPHA)
                source.fill(background)
                pygame.draw.circle(source, (230, 30, 30, 255), source.get_rect().center, 20)
                original = pygame.image.tobytes(source, 'RGBA')
                image = prepare_intro_cover(source, target_size)
                self.assertEqual(image.get_size(), target_size)
                self.assertEqual(pygame.image.tobytes(source, 'RGBA'), original)
                # cover는 모든 코너까지 원본으로 덮는다. contain이면 흰 밴드가 남는다.
                # RGB 단색의 0.75배 smoothscale만으로도 (20,60,100)이
                # (17,57,98)까지 반올림되는 것을 확인해 4계조 오차를 허용한다.
                for point in ((0, 0), (119, 0), (0, 89), (119, 89)):
                    for actual, expected in zip(image.get_at(point), background):
                        self.assertAlmostEqual(actual, expected, delta=4)
                circle = pygame.mask.from_threshold(image, (230, 30, 30, 255), (35, 35, 35, 255))
                circles = circle.get_bounding_rects()
                self.assertEqual(len(circles), 1)
                bounds = circles[0]
                # 가로/세로 독립 확대는 원을 타원으로 만들고, 한쪽 정렬 crop은
                # 원 중심을 화면 중심에서 옮기므로 각각 별도로 확인한다.
                self.assertAlmostEqual(bounds.width, bounds.height, delta=1)
                self.assertAlmostEqual(bounds.centerx, target_size[0] / 2, delta=1)
                self.assertAlmostEqual(bounds.centery, target_size[1] / 2, delta=1)

    def test_splash_ignores_keys_and_keeps_play_state_frozen(self):
        initial = self.snapshot()
        for key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_a):
            self.key(key)
            self.assertEqual(self.app.phase, 'splash')
            self.assertEqual(self.snapshot(), initial)
        self.app.update(-1)
        self.app.update(config.SPLASH_SECONDS / 2)
        self.app.update_background(100)
        self.assertEqual(self.app.phase, 'splash')
        self.app.update(config.SPLASH_SECONDS / 2)
        self.assertEqual(self.app.phase, 'ready')
        self.assertEqual(self.snapshot(), initial)

    def test_white_ready_screen_animates_without_obstacles_or_score_progress(self):
        self.ready()
        initial = self.snapshot()
        self.app.draw()
        first = pygame.image.tobytes(self.app.view.screen, 'RGB')
        self.app.update(config.RUN_FRAME_TICKS / config.PHYSICS_HZ)
        self.app.draw()
        second = pygame.image.tobytes(self.app.view.screen, 'RGB')
        self.assertNotEqual(first, second)
        self.assertEqual(self.app.view.screen.get_at((479, 359))[:3], (255, 255, 255))
        self.app.update(300)
        self.app.update_background(100)
        self.assertEqual(self.app.phase, 'ready')
        self.assertEqual(self.snapshot(), initial)
        self.assertFalse(self.record.exists())
        with patch.object(self.app.view, 'draw', side_effect=AssertionError('대기 중 플레이 출력')):
            self.app.draw()

    def test_any_key_starts_fade_without_jumping_or_pausing(self):
        for key in (pygame.K_a, pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_F4):
            with self.subTest(key=key):
                self.app.reset()
                self.app.phase = 'ready'
                self.app.intro_elapsed = 0.137
                initial = self.snapshot()
                self.key(key)
                state = self.app.state
                self.assertEqual(self.app.phase, 'transition')
                self.assertEqual(self.snapshot(), initial)
                self.assertEqual(self.app.intro_elapsed, 0.137)
                self.assertEqual(self.app.transition_elapsed, 0)
                self.app.draw()
                self.assertEqual(self.app.view.screen.get_at((479, 20))[:3], (255, 255, 255))
                self.app.update(config.START_FADE_SECONDS)
                self.assertEqual(self.app.phase, 'playing')
                self.assertFalse(state.is_jumping)
                self.assertFalse(state.paused)
                self.assertEqual(state.background_elapsed, 0)
                self.assertEqual(state.score, 0)
                self.assertEqual(state.obstacle_x, config.SCREEN_SIZE[0])
                self.assertIn(state.obstacle_name, config.OBSTACLE_FILES)
                self.app.draw()
                source_x = (240 - int(state.background_x)) % state.background_width
                self.assertEqual(self.app.view.screen.get_at((240, 150)),
                                 self.app.view.background_stages[0].get_at((source_x, 150)))
        initial_x = self.app.state.obstacle_x
        self.app.update(1 / config.PHYSICS_HZ)
        self.assertLess(self.app.state.obstacle_x, initial_x)
        self.key(pygame.K_SPACE)
        self.assertTrue(self.app.state.is_jumping)

    def test_start_key_batch_is_consumed_but_close_is_still_handled(self):
        self.ready()
        for key in (pygame.K_SPACE, pygame.K_SPACE, pygame.K_ESCAPE):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
        self.app.handle_events()
        self.assertEqual(self.app.phase, 'transition')
        self.assertFalse(self.app.state.is_jumping)
        self.assertFalse(self.app.state.paused)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.app.handle_events()
        self.assertFalse(self.app.state.running)

    def test_game_over_restart_returns_directly_to_campus_and_reuses_assets(self):
        with patch.object(pygame.image, 'load', side_effect=AssertionError('자원 재로딩')):
            self.app.draw()
            self.ready()
            self.app.draw()
            self.key(pygame.K_SPACE)
            self.app.update(config.START_FADE_SECONDS)
            self.assertEqual(self.app.phase, 'playing')
            self.app.state.obstacle_x = 0
            self.app.update(0.01)
            self.assertTrue(self.app.state.game_over)
            self.app.draw()
            self.key(pygame.K_RETURN)
            self.assertEqual(self.app.phase, 'playing')
            self.assertFalse(self.app.state.game_over)
            self.assertEqual(self.app.state.background_elapsed, 0)
            self.assertEqual(self.app.state.score, 0)
            self.app.draw()
            self.assertEqual(self.app.view.screen.get_at((240, 150)),
                             self.app.view.background_stages[0].get_at((240, 150)))

    def test_close_and_ctrl_f4_exit_every_phase(self):
        for phase in ('splash', 'ready', 'transition', 'playing'):
            for close in ('window', 'keyboard'):
                with self.subTest(phase=phase, close=close):
                    self.app.phase = phase
                    self.app.state.running = True
                    if close == 'window':
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                        self.app.handle_events()
                    else:
                        self.key(pygame.K_F4, pygame.KMOD_CTRL)
                    self.assertFalse(self.app.state.running)
        self.assertFalse(self.record.exists())

    def test_main_loop_passes_through_intro_and_fade_then_exits(self):
        events = [[], [], [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)],
                  [],
                  [pygame.event.Event(pygame.QUIT)]]
        self.app.clock = Mock()
        self.app.clock.tick.side_effect = [config.SPLASH_SECONDS * 500,
                                          config.SPLASH_SECONDS * 500,
                                          config.START_FADE_SECONDS * 500,
                                          config.START_FADE_SECONDS * 500, 1]
        phases = []
        original_draw = self.app.draw

        def draw():
            phases.append(self.app.phase)
            original_draw()

        with patch.object(pygame.event, 'get', side_effect=events), patch.object(self.app, 'draw', draw):
            self.app.run()
        self.assertEqual(phases, ['splash', 'ready', 'transition', 'playing'])
        self.assertFalse(self.app.state.running)

    def test_transition_fades_background_monotonically_and_keeps_bugi_opaque(self):
        view = self.app.view
        background = view.background_stages[0]
        source_pixels = pygame.image.tobytes(background, 'RGBA')
        source_alpha = background.get_alpha()
        frame = view.run_frames[0]
        frame_pixels = pygame.image.tobytes(frame, 'RGBA')
        ground_y = config.SCREEN_SIZE[1] - config.CHARACTER_HEIGHT + config.PLAYER_GROUND_OFFSET
        opaque_pixel = max(((x, y) for y in range(min(frame.get_height(), config.SCREEN_SIZE[1] - ground_y))
                            for x in range(frame.get_width())), key=lambda point: frame.get_at(point).a)
        player_point = (opaque_pixel[0], ground_y + opaque_pixel[1])
        background_x = -137
        sample = (479, 20)  # 제목·안내·캐릭터가 없는 배경 픽셀이다.
        expected_background = background.get_at((sample[0] - background_x, sample[1]))[:3]
        colors = []
        for progress in (0, 0.25, 0.5, 0.75, 1):
            view.draw_startup('transition', 0, progress, background_x=background_x)
            colors.append(view.screen.get_at(sample)[:3])
            # 배율 변환 후 알파가 254인 원본 픽셀도 있으므로 원래 알파로 합성한다.
            expected_pixel = pygame.Surface((1, 1))
            expected_pixel.fill((255, 255, 255))
            campus_pixel = background.subsurface((player_point[0] - background_x,
                                                  player_point[1], 1, 1)).copy()
            campus_pixel.set_alpha(round(255 * progress * progress * (3 - 2 * progress)))
            expected_pixel.blit(campus_pixel, (0, 0))
            expected_pixel.blit(frame, (0, 0), (*opaque_pixel, 1, 1))
            self.assertEqual(view.screen.get_at(player_point)[:3], expected_pixel.get_at((0, 0))[:3])
        self.assertEqual(colors[0], (255, 255, 255))
        self.assertEqual(colors[-1], expected_background)
        for channel in range(3):
            values = [color[channel] for color in colors]
            self.assertEqual(values, sorted(values, reverse=True))
            self.assertAlmostEqual(values[2], (255 + expected_background[channel]) / 2, delta=2)
        self.assertNotEqual(colors[0], colors[2])
        self.assertNotEqual(colors[2], colors[-1])
        self.assertEqual(background.get_alpha(), source_alpha)
        self.assertEqual(pygame.image.tobytes(background, 'RGBA'), source_pixels)
        self.assertEqual(pygame.image.tobytes(frame, 'RGBA'), frame_pixels)

    def test_startup_scroll_wrap_tiles_cover_white_canvas_and_match_playing(self):
        view = self.app.view
        state = self.app.state
        strip = pygame.Rect(0, 220, config.SCREEN_SIZE[0], 16)
        background = view.background_stages[0].copy()
        for offset in (-state.background_width + 5, -state.background_width + 0.5, -137.5):
            state.background_x = offset
            for progress in (0, 0.5, 1):
                with self.subTest(offset=offset, progress=progress):
                    expected = pygame.Surface(strip.size)
                    expected.fill((255, 255, 255))
                    background.set_alpha(round(255 * progress * progress * (3 - 2 * progress)))
                    # 각 출력 픽셀은 순환 배경의 한 열을 딱 한 번 합성해야 한다.
                    # 소수 좌표에서 두 타일이 겹치면 경계 픽셀이 더 짙어져 실패한다.
                    for x in range(strip.width):
                        source_x = (x - int(offset)) % state.background_width
                        expected.blit(background, (x, 0), (source_x, strip.y, 1, strip.height))
                    view.draw_startup('transition', 0, progress, background_x=state.background_x)
                    self.assertEqual(pygame.image.tobytes(view.screen.subsurface(strip), 'RGB'),
                                     pygame.image.tobytes(expected, 'RGB'))
            fully_revealed = pygame.image.tobytes(view.screen.subsurface(strip), 'RGB')
            view.draw(state)
            self.assertEqual(pygame.image.tobytes(view.screen.subsurface(strip), 'RGB'),
                             fully_revealed)

    def test_ready_start_and_fade_completion_keep_running_pose_and_position(self):
        self.ready()
        self.app.update(0.137)
        self.app.draw()
        before_start = pygame.image.tobytes(self.app.view.screen, 'RGB')
        self.key(pygame.K_SPACE)
        self.app.draw()
        self.assertEqual(pygame.image.tobytes(self.app.view.screen, 'RGB'), before_start)
        self.app.update(0.113)
        with patch.object(self.app.view, 'draw_startup', wraps=self.app.view.draw_startup) as draw:
            self.app.draw()
        self.assertEqual(draw.call_args.args[1], 2)  # 0.25초째의 세 번째 달리기 자세.
        self.assertEqual(draw.call_args.kwargs['background_x'], self.app.state.background_x)
        self.assertLess(self.app.state.background_x, 0)
        self.app.update(config.START_FADE_SECONDS - 0.113)
        self.assertEqual(self.app.phase, 'playing')
        index = self.app.state.player_frame_index
        expected_tick = (0.137 + config.START_FADE_SECONDS) * config.PHYSICS_HZ
        self.assertEqual(index, int(expected_tick / config.RUN_FRAME_TICKS) % len(self.app.view.run_frames))
        self.app.view.draw_startup('transition', index, 1,
                                   background_x=self.app.state.background_x)
        player_area = pygame.Rect(0, int(self.app.state.player_y),
                                  self.app.state.player_size[0],
                                  config.SCREEN_SIZE[1] - int(self.app.state.player_y))
        faded_player = pygame.image.tobytes(self.app.view.screen.subsurface(player_area), 'RGB')
        self.app.draw()
        self.assertEqual(pygame.image.tobytes(self.app.view.screen.subsurface(player_area), 'RGB'),
                         faded_player)
        self.app.update(1 / config.PHYSICS_HZ)
        self.assertEqual(self.app.state.player_frame_index,
                         int((expected_tick + 1) / config.RUN_FRAME_TICKS) % len(self.app.view.run_frames))

    def test_transition_freezes_gameplay_and_ignores_keys_until_completion(self):
        self.ready()
        self.key(pygame.K_a)
        initial = self.snapshot()
        self.app.update(-1)
        self.assertEqual(self.app.transition_elapsed, 0)
        self.assertEqual(self.snapshot(), initial)
        self.app.update(config.START_FADE_SECONDS / 4)
        elapsed = self.app.transition_elapsed
        scrolled = self.snapshot()
        self.assertNotEqual(scrolled[3], initial[3])
        self.assertAlmostEqual(scrolled[3], -config.BACKGROUND_SPEED * config.PHYSICS_HZ
                               * min(config.START_FADE_SECONDS / 4, 0.1))
        self.assertEqual(scrolled[:3] + scrolled[4:], initial[:3] + initial[4:])
        for key in (pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_a):
            self.key(key)
            self.assertEqual(self.app.phase, 'transition')
            self.assertEqual(self.app.transition_elapsed, elapsed)
            self.assertEqual(self.snapshot(), scrolled)
        self.app.update_background(100)
        self.assertEqual(self.snapshot(), scrolled)
        self.assertFalse(self.record.exists())
        self.app.update(config.START_FADE_SECONDS * 3 / 4)
        self.assertEqual(self.app.phase, 'playing')
        state = self.app.state
        self.assertEqual((state.score, state.survival_elapsed, state.background_elapsed), (0, 0, 0))
        self.assertEqual(state.obstacle_x, config.SCREEN_SIZE[0])
        self.app.update(1 / config.PHYSICS_HZ)
        self.assertLess(state.obstacle_x, config.SCREEN_SIZE[0])
        self.key(pygame.K_SPACE)
        self.assertTrue(state.is_jumping)

    def test_fade_scroll_speed_wrap_and_playing_continuity_at_30_60_and_120_fps(self):
        self.assertGreaterEqual(config.START_FADE_SECONDS, 1)
        self.assertLessEqual(config.START_FADE_SECONDS, 1.5)
        for hz in (30, 60, 120):
            with self.subTest(hz=hz):
                self.app.reset()
                self.app.phase = 'ready'
                state = self.app.state
                state.background_x = -state.background_width + 3
                initial_x = state.background_x
                self.key(pygame.K_a)
                frames = math.ceil(config.START_FADE_SECONDS * hz)
                for frame in range(1, frames):
                    self.app.update(1 / hz)
                    expected_x = -((-initial_x + config.BACKGROUND_SPEED
                                    * config.PHYSICS_HZ * frame / hz) % state.background_width)
                    self.assertAlmostEqual(state.background_x, expected_x)
                    self.assertEqual(state.obstacle_x, config.SCREEN_SIZE[0])
                    self.assertEqual((state.score, state.survival_elapsed, state.background_elapsed),
                                     (0, 0, 0))
                self.assertEqual(self.app.phase, 'transition')
                self.app.update(1 / hz)
                self.assertEqual(self.app.phase, 'playing')
                self.assertLessEqual(self.app.transition_elapsed - config.START_FADE_SECONDS, 1 / hz)
                expected_x = -((-initial_x + config.BACKGROUND_SPEED
                                * config.PHYSICS_HZ * frames / hz) % state.background_width)
                self.assertAlmostEqual(state.background_x, expected_x)
                self.assertEqual((state.score, state.survival_elapsed, state.background_elapsed),
                                 (0, 0, 0))
                self.assertEqual(state.obstacle_x, config.SCREEN_SIZE[0])
                self.app.update(1 / hz)
                expected_x = -((-expected_x + config.BACKGROUND_SPEED
                                * config.PHYSICS_HZ / hz) % state.background_width)
                self.assertAlmostEqual(state.background_x, expected_x)
                self.assertLess(state.obstacle_x, config.SCREEN_SIZE[0])


if __name__ == '__main__':
    unittest.main()
