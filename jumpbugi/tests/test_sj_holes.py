"""상찌의 빠른·느린 굴 진입과 둘째 봄 탈출의 표시·충돌·회피를 검사한다."""
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
    from .. import backend, config
    from ..main import JumpBugi
else:
    import backend, config
    from main import JumpBugi


class SjHoleTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = JumpBugi(Path(directory.name) / 'score.txt')
        self.app.reset()
        pygame.event.clear()

    def profiles(self, name):
        return config.SJ_BURROW_PROFILES if name == 'sj_burrow' else config.SJ_ESCAPE_PROFILES

    def spawn_profile(self, name, timing, stage=8):
        state = self.app.state
        state.background_elapsed = stage * config.DAY_NIGHT_INTERVAL
        choices = tuple(self.profiles(name))
        roll = (choices.index(timing) + 0.5) / len(choices)
        with patch.object(backend.random, 'random', return_value=roll):
            state.spawn_obstacle(name)
        self.assertEqual(state.sj_hole_timing, timing)
        return state

    def bonus(self):
        state = self.app.state
        return state.score - int(state.survival_elapsed + 1e-9) * config.SURVIVAL_POINTS_PER_SECOND

    def test_fast_and_slow_plans_are_chosen_once_and_progress_by_approach(self):
        state = self.app.state
        for name in config.SJ_HOLE_TYPES:
            spans = {}
            for roll, timing in ((0.0, 'fast'), (0.499999, 'fast'),
                                 (0.5, 'slow'), (1.0, 'slow')):
                with self.subTest(name=name, roll=roll):
                    self.app.reset()
                    state.background_elapsed = config.SJ_ESCAPE_UNLOCK_SECONDS
                    with patch.object(backend.random, 'random', return_value=roll) as choose:
                        state.spawn_obstacle(name)
                    self.assertEqual(choose.call_count, 1)
                    self.assertEqual(state.sj_hole_timing, timing)
                    self.assertGreaterEqual(state.sj_hole_end_x, state.player_size[0] + 32)
                    spans[timing] = state.sj_hole_start_x - state.sj_hole_end_x
                    frames = self.app.view.obstacle_frames[name]
                    self.assertEqual(len(frames), 12 if name == 'sj_burrow' else 4)
                    self.assertEqual({frame.get_size() for frame in frames}, {(112, 64)})
                    for x, expected in ((state.sj_hole_start_x + 100, 0),
                                        (state.sj_hole_start_x, 0),
                                        ((state.sj_hole_start_x + state.sj_hole_end_x) / 2,
                                         (len(frames) - 1) // 2),
                                        (state.sj_hole_end_x, len(frames) - 1),
                                        (-100, len(frames) - 1)):
                        state.obstacle_x = x
                        state.obstacle_animation_tick = 60000
                        self.assertEqual(state.obstacle_frame_index, expected)
                        with patch.object(self.app.view, 'screen', wraps=self.app.view.screen) as screen:
                            self.app.draw()
                        self.assertIs(screen.blit.call_args_list[2].args[0], frames[expected])
                    state.obstacle_x = state.obstacle_spawn_x
                    with patch.object(backend.random, 'random', side_effect=AssertionError('진행 중 속도 재선택')):
                        self.app.update(1 / config.PHYSICS_HZ)
                        self.app.draw()
                    self.assertEqual(state.sj_hole_timing, timing)
            self.assertLess(spans['fast'], spans['slow'])

    def test_hole_is_decorative_while_an_emerged_body_can_collide(self):
        state = self.app.state
        for name in config.SJ_HOLE_TYPES:
            frames = self.app.view.obstacle_frames[name]
            masks = self.app.view.obstacle_frame_masks[name]
            self.assertEqual(len(frames), len(masks))
            self.assertTrue(all(mask.get_size() == (112, 64) for mask in masks))
            for frame in frames:
                self.assertLessEqual(frame.get_bounding_rect(min_alpha=20).bottom, 64)
            self.assertGreater(pygame.mask.from_surface(frames[-1], 127).count(), 0)
        self.assertEqual(self.app.view.obstacle_frame_masks['sj_burrow'][-1].count(), 0)
        self.assertGreater(self.app.view.obstacle_frame_masks['sj_escape'][-1].count(), 0)

        # 주황색 구덩이의 양옆은 표시되지만 몸체 전용 충돌 마스크에는 남지 않는다.
        frame = self.app.view.obstacle_frames['sj_escape'][-1]
        mask = self.app.view.obstacle_frame_masks['sj_escape'][-1]
        # 연노란 배도 실제 몸체다. 초록 머리만 남는 불완전한 판정을 막는다.
        self.assertTrue(mask.get_at((50, 40)))
        self.assertTrue(mask.get_at((48, 50)))
        checked = 0
        for x in tuple(range(20)) + tuple(range(92, 112)):
            for y in range(64):
                r, g, b, a = frame.get_at((x, y))
                if a > 127 and r > g + 25 and g > b + 10:
                    checked += 1
                    self.assertFalse(mask.get_at((x, y)))
        self.assertGreater(checked, 0)

        for timing in ('fast', 'slow'):
            self.app.reset()
            self.spawn_profile('sj_burrow', timing)
            self.assertFalse(state.obstacle_requires_jump)
            for player_pose in range(state.frame_count):
                state.animation_tick = player_pose * config.RUN_FRAME_TICKS
                for x in range(-state.obstacle_size[0], state.player_size[0] + 1):
                    state.obstacle_x = x
                    self.assertFalse(state.collides_with_obstacle())
            self.app.reset()
            self.spawn_profile('sj_escape', timing)
            self.assertTrue(state.obstacle_requires_jump)
            contact = None
            for x in range(state.player_size[0], -state.obstacle_size[0], -1):
                state.obstacle_x = x
                if state.collides_with_obstacle():
                    contact = x
                    break
            self.assertIsNotNone(contact)
            state.update_step(0)
            self.assertTrue(state.game_over)

    def test_emergence_waits_for_the_next_spring_in_candidates_and_queue(self):
        state = self.app.state
        interval = config.DAY_NIGHT_INTERVAL
        for elapsed, enabled in ((0, False), (2 * interval, False), (4 * interval, False),
                                 (6 * interval, False), (8 * interval - 0.001, False),
                                 (8 * interval, True), (16 * interval, True)):
            with self.subTest(elapsed=elapsed):
                state.background_elapsed = elapsed
                state.pattern_queue = []
                with patch.object(backend.random, 'choice', side_effect=lambda pool: pool[0]) as choose:
                    state.spawn_obstacle()
                available = {kind for pattern in choose.call_args_list[0].args[0] for kind in pattern}
                self.assertEqual(state.sj_escape_enabled, enabled)
                self.assertEqual('sj_escape' in available, enabled)
        state.background_elapsed = 6 * interval
        state.pattern_queue = ['sj_escape', 'sj_burrow']
        state.spawn_obstacle()
        self.assertEqual(state.obstacle_name, 'sj_burrow')
        self.assertEqual(state.pattern_queue, [])
        state.background_elapsed = 8 * interval
        state.pattern_queue = ['sj_escape']
        state.spawn_obstacle()
        self.assertEqual(state.obstacle_name, 'sj_escape')
        self.app.reset()
        self.assertFalse(state.sj_escape_enabled)
        self.assertIsNone(state.sj_hole_timing)
        self.assertEqual(state.pattern_queue, [])

    def test_pause_restart_and_new_encounters_keep_cached_images_and_reset_progress(self):
        state = self.app.state
        for name in config.SJ_HOLE_TYPES:
            cached = self.app.view.obstacle_frames[name]
            for timing in ('fast', 'slow'):
                self.app.reset()
                self.spawn_profile(name, timing)
                state.obstacle_x = (state.sj_hole_start_x + state.sj_hole_end_x) / 2
                with patch.object(pygame.image, 'load', side_effect=AssertionError('이미지 재로딩')):
                    for flag in ('paused', 'game_over'):
                        setattr(state, flag, True)
                        before = (state.obstacle_x, state.sj_hole_timing, state.sj_hole_progress,
                                  state.obstacle_frame_index, state.background_elapsed, state.score)
                        self.app.update(2)
                        self.app.draw()
                        self.assertEqual((state.obstacle_x, state.sj_hole_timing, state.sj_hole_progress,
                                          state.obstacle_frame_index, state.background_elapsed, state.score), before)
                        setattr(state, flag, False)
                    self.spawn_profile(name, timing)
                    self.assertEqual(state.obstacle_frame_index, 0)
                    state.spawn_obstacle('chicken_white_ground')
                    self.assertIsNone(state.sj_hole_timing)
                    self.app.reset()
                    self.assertIsNone(state.sj_hole_timing)
                    self.assertIs(self.app.view.obstacle_frames[name], cached)

    def test_both_profiles_clear_and_score_ten_at_three_speeds_and_frame_rates(self):
        for name in config.SJ_HOLE_TYPES:
            for timing in ('fast', 'slow'):
                for stage in (8, 10, 20):
                    for hz in (30, 60, 120):
                        with self.subTest(name=name, timing=timing, stage=stage, hz=hz):
                            self.app.reset()
                            state = self.spawn_profile(name, timing, stage)
                            jumped = False
                            for _ in range(3 * hz):
                                speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier
                                target = min(360, 60 + speed * 0.30)
                                if name == 'sj_escape' and not jumped and state.obstacle_x <= target:
                                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                                    jumped = True
                                self.app.handle_events()
                                self.app.update(1 / hz)
                                self.assertFalse(state.game_over)
                                if self.bonus() == config.PASS_BONUS:
                                    break
                            self.assertEqual(jumped, name == 'sj_escape')
                            self.assertEqual(self.bonus(), 10)
                            score = state.score
                            state.update_step(0)
                            self.assertEqual(state.score, score)


if __name__ == '__main__':
    unittest.main()
