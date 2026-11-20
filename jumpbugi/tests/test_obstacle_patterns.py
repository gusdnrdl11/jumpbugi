"""기본 장애물·지상 및 비행형 패턴의 실제 마스크·물리 검사."""
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
    from .. import config, backend
    from ..main import JumpBugi
else:
    import config, backend
    from main import JumpBugi


class ObstaclePatternTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = JumpBugi(Path(directory.name) / 'score.txt')
        self.app.reset()

    def test_both_characters_have_four_matching_animation_masks(self):
        for name in config.CHICKEN_TYPES:
            frames = self.app.view.obstacle_frames[name]
            masks = self.app.view.obstacle_frame_masks[name]
            self.assertEqual(len(frames), 4)
            self.assertEqual(len(masks), 4)
            self.assertEqual(len({frame.get_size() for frame in frames}), 1)
            self.assertGreaterEqual(len({pygame.image.tobytes(frame, 'RGBA') for frame in frames}), 3)
            self.assertTrue(all(mask.count() for mask in masks))
            self.app.state.spawn_obstacle(name)
            for index in range(4):
                self.app.state.obstacle_animation_tick = index * config.OBSTACLE_FRAME_TICKS
                self.assertEqual(self.app.state.obstacle_frame_index, index)

    def test_all_animated_chickens_unlock_after_first_spring_and_stay_unlocked(self):
        state = self.app.state
        def select(pool):
            return next((p for p in pool if isinstance(p, tuple) and p[0] in config.CHICKEN_TYPES), pool[0])
        with patch.object(backend.random, 'choice', side_effect=select) as choose:
            interval = config.DAY_NIGHT_INTERVAL
            for elapsed, enabled in ((0, False), (interval, False), (2 * interval - 0.001, False),
                                     (2 * interval, True), (4 * interval, True), (6 * interval, True),
                                     (8 * interval - 0.001, True), (8 * interval, True),
                                     (9 * interval, True), (10 * interval - 0.001, True),
                                     (10 * interval, True), (16 * interval, True), (18 * interval, True)):
                state.background_elapsed = elapsed
                state.pattern_queue = []
                state.spawn_obstacle()
                self.assertEqual(state.obstacle_name in config.CHICKEN_TYPES, enabled)
                available = {kind for pattern in state.available_patterns for kind in pattern}
                self.assertEqual(available.intersection(config.CHICKEN_TYPES),
                                 set(config.CHICKEN_TYPES) if enabled else set())
        self.app.reset()
        self.assertFalse(state.obstacle_is_flying)
        self.assertEqual(state.pattern_queue, [])
        self.assertFalse(state.chicken_obstacles_enabled)

    def test_first_spring_filters_all_chickens_but_second_spring_preserves_them(self):
        state = self.app.state
        state.background_elapsed = config.DAY_NIGHT_INTERVAL
        state.pattern_queue = list(config.CHICKEN_TYPES) + ['sj.png']
        state.spawn_obstacle()
        self.assertEqual(state.obstacle_name, 'sj.png')
        self.assertEqual(state.pattern_queue, [])
        state.pattern_queue = list(config.CHICKEN_TYPES)
        state.spawn_obstacle()
        self.assertNotIn(state.obstacle_name, config.CHICKEN_TYPES)
        state.background_elapsed = config.SLOTS_PER_CYCLE * config.DAY_NIGHT_INTERVAL
        state.pattern_queue = list(config.CHICKEN_TYPES)
        for kind in config.CHICKEN_TYPES:
            state.spawn_obstacle()
            self.assertEqual(state.obstacle_name, kind)

    def test_first_spring_random_patterns_only_use_basic_types(self):
        state = self.app.state
        for second in range(2 * config.DAY_NIGHT_INTERVAL):
            state.background_elapsed = second
            for _ in range(20):
                state.spawn_obstacle()
                self.assertIn(state.obstacle_name, config.OBSTACLE_FILES)
                self.assertTrue(all(kind not in config.CHICKEN_TYPES for kind in state.pattern_queue))

    def test_ground_chicken_feet_stay_visible_and_draw_matches_collision_for_every_pose(self):
        state = self.app.state
        for name in config.CHICKEN_TYPES[:2]:
            for index, frame in enumerate(self.app.view.obstacle_frames[name]):
                with self.subTest(name=name, pose=index):
                    self.app.reset()
                    state.spawn_obstacle(name)
                    state.obstacle_animation_tick = index * config.OBSTACLE_FRAME_TICKS
                    bounds = frame.get_bounding_rect(min_alpha=20)
                    visible_bottom = state.obstacle_y + bounds.bottom
                    self.assertLessEqual(visible_bottom, config.SCREEN_SIZE[1])
                    self.assertGreaterEqual(visible_bottom, config.SCREEN_SIZE[1] - 3)
                    self.assertLess(state.obstacle_y + state.obstacle_size[1],
                                    config.SCREEN_SIZE[1] + config.OBSTACLE_GROUND_OFFSET)
                    contact = None
                    for x in range(state.player_size[0], -state.obstacle_size[0], -1):
                        state.obstacle_x = x + 0.75
                        if state.collides_with_obstacle():
                            contact = x
                            break
                    self.assertIsNotNone(contact)
                    with patch.object(self.app.view, 'screen', wraps=self.app.view.screen) as screen:
                        self.app.draw()
                    obstacle_call = screen.blit.call_args_list[2]
                    self.assertIs(obstacle_call.args[0], frame)
                    self.assertEqual(obstacle_call.args[1], (contact, int(state.obstacle_y)))
                    mask = self.app.view.obstacle_frame_masks[name][index]
                    offset = (contact, int(state.obstacle_y) - int(state.player_y))
                    self.assertIsNotNone(state.player_masks[state.player_frame_index].overlap(mask, offset))
                    state.update_step(0)
                    self.assertTrue(state.game_over)

    def test_flying_clears_every_grounded_pose_but_can_hit_a_jump(self):
        state = self.app.state
        for name in config.CHICKEN_TYPES[2:]:
            self.app.reset()
            # 기존 아래 통과 검사는 머리 가까이 지나가는 중간 높이로 고정한다.
            with patch.object(backend.random, 'random', return_value=0.5):
                state.spawn_obstacle(name)
            for player_frame in range(4):
                state.animation_tick = player_frame * config.RUN_FRAME_TICKS
                for bird_frame in range(4):
                    state.obstacle_animation_tick = bird_frame * config.OBSTACLE_FRAME_TICKS
                    for x in range(-state.obstacle_size[0], state.player_size[0] + 1):
                        state.obstacle_x = x
                        self.assertFalse(state.collides_with_obstacle())
            state.obstacle_x = 160
            state.jump()
            for _ in range(100):
                self.app.update(1 / 120)
                if state.game_over:
                    break
            self.assertTrue(state.game_over)

    @patch.object(backend.random, 'random', return_value=1.0)
    def test_all_patterns_have_a_safe_run_jump_solution_at_multiple_speeds(self, _random):
        for stage in (2, 4, 10, 20):
            for hz in (30, 60, 120):
                for pattern in config.GROUND_PATTERNS + config.SUMMER_PATTERNS:
                    with self.subTest(stage=stage, hz=hz, pattern=pattern):
                        self.app.reset()
                        state = self.app.state
                        state.background_elapsed = stage * config.DAY_NIGHT_INTERVAL
                        state.pattern_queue = list(pattern)
                        state.spawn_obstacle()
                        cleared = 0
                        expected_bonus = 0
                        for _ in range(15 * hz):
                            speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier
                            target = (state.player_size[0] - state.obstacle_size[0]) / 2 + speed * 0.35 \
                                if state.obstacle_name in config.WAVE_IMAGE_FILES else 60 + speed * 0.30
                            if (state.obstacle_requires_jump and not state.is_jumping
                                    and state.obstacle_x <= target):
                                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                            self.app.handle_events()
                            old_x = state.obstacle_x
                            old_name = state.obstacle_name
                            self.app.update(1 / hz)
                            self.assertFalse(state.game_over)
                            if state.obstacle_x > old_x:
                                cleared += 1
                                expected_bonus += config.PASS_BONUS * (2 if old_name == 'sj_pair'
                                                                      else 3 if old_name == 'sj_triple' else 1)
                                # 생성 뒤 같은 출력 프레임의 남은 물리가 이미 진행될 수 있다.
                                # 접근 여유는 정확한 생성 좌표에서 측정하고 잔여 이동도 확인한다.
                                approach = (state.obstacle_spawn_x - state.player_size[0]) / (
                                    config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier)
                                self.assertGreaterEqual(approach + 1e-9, state.obstacle_recovery_seconds)
                                frame_distance = (config.OBSTACLE_SPEED * config.PHYSICS_HZ
                                                  * state.speed_multiplier / hz)
                                self.assertGreaterEqual(state.obstacle_x + 1e-9,
                                                        state.obstacle_spawn_x - frame_distance)
                                if cleared == len(pattern):
                                    break
                        self.assertEqual(cleared, len(pattern))
                        self.assertEqual(state.score, int(state.survival_elapsed + 1e-9) + expected_bonus)

    def test_animation_stops_on_pause_and_game_over_and_assets_are_cached(self):
        state = self.app.state
        state.spawn_obstacle('chicken_white_flying')
        with patch.object(pygame.image, 'load', side_effect=AssertionError('이미지 재로딩')):
            self.app.update(0.1)
            self.app.draw()
            for flag in ('paused', 'game_over'):
                setattr(state, flag, True)
                before = (state.obstacle_x, state.obstacle_animation_tick)
                self.app.update(2)
                self.app.draw()
                self.assertEqual((state.obstacle_x, state.obstacle_animation_tick), before)
                setattr(state, flag, False)


class ExistingObstacleTests(unittest.TestCase):
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

    def test_each_random_obstacle_collision_and_reuse(self):
        app = self.app
        for name in config.OBSTACLE_FILES:
            with patch.object(backend.random, 'choice',
                              side_effect=lambda pool: name if pool == config.OBSTACLE_FILES else pool[0]) as choose:
                app.reset()
                choose.assert_called_once_with(config.OBSTACLE_FILES)
                self.assertEqual(app.state.obstacle_name, name)
                self.assertIs(app.view.obstacle_images[app.state.obstacle_name], app.view.obstacle_images[name])
                self.assertEqual(app.view.obstacle_images[app.state.obstacle_name].get_height(), config.OBSTACLE_HEIGHTS[name])
                # 설정 비율로 축소한 마스크에서도 몸통이 확실하게 겹치는 위치.
                app.state.obstacle_x = 60
                app.update()
                self.assertTrue(app.state.game_over)
                app.reset()
                app.state.obstacle_x = -app.view.obstacle_images[app.state.obstacle_name].get_width() - 1
                app.update()
                self.assertIn(app.state.obstacle_name, app.view.obstacle_images)
                self.assertEqual(app.state.obstacle_x, app.state.obstacle_spawn_x)

    def test_small_sj_size_ground_and_jump_clearance(self):
        app = self.app
        with patch.object(backend.random, 'choice', return_value='sj.png'):
            app.reset()
        self.assertEqual(app.view.obstacle_images[app.state.obstacle_name].get_height(),
                         config.OBSTACLE_HEIGHTS['sj.png'])
        self.assertEqual(len(app.view.obstacle_frames['sj.png']), 4)
        self.assertEqual(app.state.obstacle_y, 318)
        rect = app.view.obstacle_images[app.state.obstacle_name].get_rect(topleft=(60, app.state.obstacle_y))
        self.assertGreater(app.view.obstacle_masks['sj.png'].count(), 0)
        self.assertEqual(rect.bottom, 358)
        # 실제 윤곽 기준으로 이미 겹친 뒤가 아니라 접근 전에 점프한다.
        app.state.obstacle_x = 120
        self.key(pygame.K_SPACE)
        app.update()
        self.assertFalse(app.state.game_over)
        # 점프하지 않으면 작은 상찌도 실제로 부딪혀야 한다.
        app.reset()
        app.state.spawn_obstacle('sj.png')
        app.state.obstacle_x = 60
        app.update()
        self.assertTrue(app.state.game_over)


if __name__ == '__main__':
    unittest.main()
