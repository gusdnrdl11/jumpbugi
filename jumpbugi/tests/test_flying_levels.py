"""꾸꾸·꼬꼬의 상·중·하 비행 높이와 회피·득점을 검사한다."""
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
    from ..desktop_prototype import backend, config
    from ..desktop_prototype.main import JumpBugi
else:
    from desktop_prototype import backend, config
    from desktop_prototype.main import JumpBugi


class FlyingLevelTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = JumpBugi(Path(directory.name) / 'score.txt')
        self.app.reset()
        pygame.event.clear()
        self.names = tuple(name for name in config.CHICKEN_TYPES if name.endswith('_flying'))

    def spawn_level(self, name, level, seconds=None):
        state = self.app.state
        state.background_elapsed = (config.CHICKEN_UNLOCK_SLOT * config.DAY_NIGHT_INTERVAL
                                    if seconds is None else seconds)
        roll = (config.FLYING_LEVELS.index(level) + 0.5) / len(config.FLYING_LEVELS)
        with patch.object(backend.random, 'random', return_value=roll):
            state.spawn_obstacle(name)
        self.assertEqual(state.chicken_flight_level, level)
        return state

    def bonus(self):
        state = self.app.state
        return state.score - int(state.survival_elapsed + 1e-9) * config.SURVIVAL_POINTS_PER_SECOND

    def test_spawn_selects_each_level_once_and_reset_or_ground_spawn_clears_it(self):
        state = self.app.state
        choices = ((0.0, 'low'), (0.333332, 'low'), (1 / 3, 'middle'),
                   (0.666665, 'middle'), (2 / 3, 'high'), (1.0, 'high'))
        for name in self.names:
            for roll, level in choices:
                with self.subTest(name=name, roll=roll):
                    state.background_elapsed = config.CHICKEN_UNLOCK_SLOT * config.DAY_NIGHT_INTERVAL
                    with patch.object(backend.random, 'random', return_value=roll) as choose:
                        state.spawn_obstacle(name)
                    self.assertEqual(choose.call_count, 1)
                    self.assertEqual(state.chicken_flight_level, level)
                    self.assertEqual(state.obstacle_requires_jump, level == 'low')
                    self.assertTrue(state.chicken_obstacles_enabled)
                    before = (state.chicken_flight_level, state.obstacle_y)
                    with patch.object(backend.random, 'random', side_effect=AssertionError('비행 중 높이 재선택')):
                        self.app.update(1 / 120)
                        self.app.draw()
                    self.assertEqual((state.chicken_flight_level, state.obstacle_y), before)
            state.spawn_obstacle('chicken_white_ground')
            self.assertIsNone(state.chicken_flight_level)
            self.app.reset()
            self.assertIsNone(state.chicken_flight_level)
            self.assertFalse(state.chicken_obstacles_enabled)

    def test_high_and_middle_clear_all_grounded_player_and_wing_poses(self):
        state = self.app.state
        for name in self.names:
            for level in ('high', 'middle'):
                with self.subTest(name=name, level=level):
                    self.spawn_level(name, level)
                    gap = state.ground_y - (state.obstacle_y + state.obstacle_size[1])
                    if level == 'middle':
                        self.assertGreater(gap, 0)
                        self.assertLessEqual(gap, 4)
                    else:
                        self.assertGreaterEqual(gap, 40)
                    for player_frame in range(4):
                        state.animation_tick = player_frame * config.RUN_FRAME_TICKS
                        for bird_frame in range(4):
                            state.obstacle_animation_tick = bird_frame * config.OBSTACLE_FRAME_TICKS
                            for x in range(-state.obstacle_size[0], state.player_size[0] + 1):
                                state.obstacle_x = x
                                self.assertFalse(state.collides_with_obstacle())

    def test_low_hits_a_grounded_player_and_an_unnecessary_middle_jump_can_collide(self):
        state = self.app.state
        for name in self.names:
            for bird_frame in range(4):
                with self.subTest(name=name, bird_frame=bird_frame):
                    self.app.reset()
                    self.spawn_level(name, 'low')
                    self.assertGreater(state.obstacle_y, state.ground_y)
                    state.obstacle_animation_tick = bird_frame * config.OBSTACLE_FRAME_TICKS
                    contact = next((x for x in range(state.player_size[0], -state.obstacle_size[0], -1)
                                    if self.at_x_collides(x)), None)
                    self.assertIsNotNone(contact)
                    state.obstacle_x = contact
                    state.update_step(0)
                    self.assertTrue(state.game_over)
            self.app.reset()
            self.spawn_level(name, 'middle')
            state.obstacle_x = 160
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
            self.app.handle_events()
            for _ in range(120):
                self.app.update(1 / 120)
                if state.game_over:
                    break
            self.assertTrue(state.game_over)

    def at_x_collides(self, x):
        self.app.state.obstacle_x = x
        return self.app.state.collides_with_obstacle()

    def test_render_and_collision_share_positions_and_pause_reuses_the_assets(self):
        state = self.app.state
        for name in self.names:
            cached = self.app.view.obstacle_frames[name]
            for level in config.FLYING_LEVELS:
                self.spawn_level(name, level)
                state.obstacle_x = 160.75
                probe = Mock()
                probe.overlap.return_value = None
                with patch.object(state, 'player_masks', [probe] * state.frame_count):
                    for frame in range(4):
                        state.obstacle_animation_tick = frame * config.OBSTACLE_FRAME_TICKS
                        with patch.object(self.app.view, 'screen', wraps=self.app.view.screen) as screen:
                            self.app.draw()
                        call = screen.blit.call_args_list[2]
                        self.assertIs(call.args[0], cached[frame])
                        self.assertEqual(call.args[1], (160, int(state.obstacle_y)))
                        self.assertFalse(state.collides_with_obstacle())
                        self.assertIs(probe.overlap.call_args.args[0],
                                      self.app.view.obstacle_frame_masks[name][frame])
                with patch.object(pygame.image, 'load', side_effect=AssertionError('이미지 재로딩')):
                    for flag in ('paused', 'game_over'):
                        setattr(state, flag, True)
                        before = (state.obstacle_x, state.obstacle_y, state.chicken_flight_level,
                                  state.obstacle_frame_index, state.obstacle_animation_tick)
                        self.app.update(2)
                        self.app.draw()
                        self.assertEqual((state.obstacle_x, state.obstacle_y, state.chicken_flight_level,
                                          state.obstacle_frame_index, state.obstacle_animation_tick), before)
                        setattr(state, flag, False)
                    self.spawn_level(name, level)
                    self.app.reset()
                    self.assertIs(self.app.view.obstacle_frames[name], cached)

    def test_both_birds_and_three_levels_clear_and_award_ten_at_four_speeds_and_three_fps(self):
        for name in self.names:
            for level in config.FLYING_LEVELS:
                for seconds in (slot * config.DAY_NIGHT_INTERVAL for slot in (2, 4, 10, 20)):
                    for hz in (30, 60, 120):
                        with self.subTest(name=name, level=level, seconds=seconds, hz=hz):
                            self.app.reset()
                            state = self.spawn_level(name, level, seconds)
                            jumped = False
                            for _ in range(3 * hz):
                                speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier
                                if level == 'low' and not jumped and state.obstacle_x <= 60 + speed * 0.30:
                                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                                    jumped = True
                                self.app.handle_events()
                                self.app.update(1 / hz)
                                self.assertFalse(state.game_over)
                                if self.bonus() == config.PASS_BONUS:
                                    break
                            self.assertEqual(jumped, level == 'low')
                            self.assertEqual(self.bonus(), 10)
                            score = state.score
                            state.update_step(0)
                            self.assertEqual(state.score, score)


if __name__ == '__main__':
    unittest.main()
