"""슬롯 시간 변경, 유한 가속, 점프 해금과 재입력 간격을 검증한다."""
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
    from .. import backend, config, difficulty
else:
    import backend, config, difficulty


class DifficultyTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        names = config.OBSTACLE_FILES + config.CHICKEN_TYPES + config.HSUCAT_TYPES + config.SJ_TYPES
        sizes = {name: (80, config.OBSTACLE_HEIGHTS[name]) for name in names}
        sizes.update({'sj.png': (42, 40), 'sj_run.png': (42, 40),
                      'sj_pair': (87, 40), 'sj_triple': (132, 40)})
        self.state = backend.GameState(
            (90, 120), sizes, 4, 960, Path(directory.name) / 'score.txt',
            player_masks=[pygame.Mask((90, 120), fill=True) for _ in range(4)],
            obstacle_masks={name: pygame.Mask(size, fill=True) for name, size in sizes.items()})

    def test_progression_boundaries_are_independent_of_slot_seconds(self):
        for interval in (1, 20, 25, 30):
            for slot in (0, 1, 2, 4, 6, 7, 8, 15, 16, 1000):
                with self.subTest(interval=interval, slot=slot):
                    progress = difficulty.SeasonProgress.from_elapsed(slot * interval, interval)
                    self.assertEqual((progress.total_slots_passed, progress.current_slot,
                                      progress.season_cycle_count), (slot, slot % 8, slot // 8))
                    if slot:
                        before = difficulty.SeasonProgress.from_elapsed(slot * interval - 1e-6, interval)
                        self.assertEqual(before.total_slots_passed, slot - 1)
        with self.assertRaises(ValueError):
            difficulty.SeasonProgress.from_elapsed(1, 0)

    def test_every_unlock_and_background_slot_follows_runtime_interval(self):
        state = self.state
        unlocks = {'chicken_obstacles_enabled': 2, 'hsucat_obstacles_enabled': 4,
                   'sj_obstacles_enabled': 6, 'greeting_jumps_enabled': 8,
                   'sj_groups_enabled': 8, 'sj_jumps_enabled': 8, 'sj_escape_enabled': 8}
        for interval in (1, 20, 25, 30):
            with patch.object(backend, 'DAY_NIGHT_INTERVAL', interval):
                state.reset()
                for slot in range(25):
                    if slot:
                        state.update_background(interval)
                    with self.subTest(interval=interval, slot=slot):
                        self.assertEqual(state.total_slots_passed, slot)
                        self.assertEqual(state.current_slot, slot % 8)
                        self.assertEqual(state.season_cycle_count, slot // 8)
                        self.assertEqual(state.background_to_index, slot % 8)
                        for name, unlock in unlocks.items():
                            self.assertEqual(getattr(state, name), slot >= unlock, name)
                        available = {name for pattern in state.available_patterns for name in pattern}
                        for kinds, unlock in ((config.CHICKEN_TYPES, 2), (config.HSUCAT_TYPES, 4),
                                              (config.SJ_CLUSTER_TYPES, 8), (('sj_escape',), 8)):
                            self.assertEqual(set(kinds).issubset(available), slot >= unlock)

    def test_all_jump_motion_is_locked_for_first_cycle_including_running_cat(self):
        state = self.state
        names = tuple(config.WAVE_IMAGE_FILES) + config.SJ_SINGLE_JUMP_TYPES + config.SJ_CLUSTER_TYPES
        for interval in (1, 25, 30):
            with patch.object(backend, 'DAY_NIGHT_INTERVAL', interval):
                for slot in range(8):
                    state.background_elapsed = slot * interval
                    for roll in (0.0, 0.5, 0.999):
                        with patch.object(backend.random, 'random', return_value=roll):
                            for name in names:
                                state.spawn_obstacle(name)
                                self.assertIsNone(state.wave_jump, (slot, name, roll))
                                self.assertTrue(all(not member.hop_enabled for member in state.sj_members))
                            state.spawn_obstacle('hsucat_run.png')
                            self.assertIn(state.hsucat_run_mode, ('fall', 'run'))
                            self.assertIsNone(state.wave_jump)
                state.background_elapsed = 8 * interval
                for mode in ('high', 'low'):
                    roll = (config.HSUCAT_RUN_MODES.index(mode) + 0.5) / len(config.HSUCAT_RUN_MODES)
                    with patch.object(backend.random, 'random', return_value=roll):
                        state.spawn_obstacle('hsucat_run.png')
                        self.assertEqual(state.hsucat_run_mode, mode)
                        self.assertIsNotNone(state.wave_jump)
                        self.assertEqual(state.wave_jump.pattern, mode)
                with patch.object(backend.random, 'random', return_value=0):
                    for name in names:
                        state.spawn_obstacle(name)
                        self.assertTrue(state.wave_jump is not None or any(m.hop_enabled for m in state.sj_members), name)

    def test_existing_obstacle_does_not_start_jumping_when_slot_eight_arrives(self):
        state = self.state
        for name in tuple(config.WAVE_IMAGE_FILES) + config.SJ_SINGLE_JUMP_TYPES + ('hsucat_run.png',):
            state.background_elapsed = 8 * config.DAY_NIGHT_INTERVAL - 0.01
            with patch.object(backend.random, 'random', return_value=0.5):
                state.spawn_obstacle(name)
            state.update_background(0.02)
            self.assertTrue(state.greeting_jumps_enabled)
            self.assertIsNone(state.wave_jump, name)

    def test_speed_changes_shrink_and_stop_in_late_cycles(self):
        speeds = [difficulty.speed_multiplier_for_slot(slot) for slot in range(25)]
        self.assertEqual(speeds[0], 1)
        self.assertAlmostEqual(speeds[7], 1.07 ** 7)
        self.assertAlmostEqual(speeds[8], speeds[7] * 1.002)
        self.assertAlmostEqual(speeds[15], 1.07 ** 7 * 1.002 ** 8)
        self.assertLess(speeds[8] - speeds[7], speeds[7] - speeds[6])
        self.assertEqual(speeds, sorted(speeds))
        for slot in (16, 100, 10000, 10 ** 9):
            self.assertEqual(difficulty.speed_multiplier_for_slot(slot), speeds[15])
            self.assertLessEqual(difficulty.speed_multiplier_for_slot(slot), config.MAX_SPEED_MULTIPLIER)
        with patch.object(config, 'MAX_SPEED_MULTIPLIER', 1.2):
            self.assertEqual(difficulty.speed_multiplier_for_slot(10000), 1.2)

    def test_cycle_profiles_increase_patterns_and_preserve_landing_time(self):
        profiles = [difficulty.profile_for_slot(slot) for slot in (0, 8, 16)]
        self.assertGreater(profiles[0].recovery_seconds, profiles[1].recovery_seconds)
        self.assertGreater(profiles[1].recovery_seconds, profiles[2].recovery_seconds)
        self.assertLess(profiles[0].hard_pattern_probability, profiles[1].hard_pattern_probability)
        self.assertLess(profiles[1].chain_probability, profiles[2].chain_probability)
        with patch.object(config, 'CYCLE_RECOVERY_SECONDS', (0, 0, 0)):
            for slot in (0, 8, 16, 1000):
                self.assertAlmostEqual(difficulty.profile_for_slot(slot).recovery_seconds,
                                       difficulty.jump_flight_seconds() + config.MIN_RECOVERY_TIME)

    def test_late_selection_increases_scripted_chains_and_hard_pool(self):
        state = self.state
        for slot, hard, chain in ((6, False, False), (8, False, True), (16, True, True)):
            state.background_elapsed = slot * config.DAY_NIGHT_INTERVAL
            state.pattern_queue = []
            with patch.object(backend.random, 'random', return_value=0.5), \
                 patch.object(backend.random, 'choice', side_effect=lambda pool: pool[0]) as choose:
                state.spawn_obstacle()
            pool = choose.call_args_list[0].args[0]
            self.assertEqual(all(pattern in config.HARD_PATTERNS for pattern in pool), hard)
            self.assertEqual(bool(state.pattern_queue), chain)
            self.assertEqual(len(state.current_pattern), len(state.pattern_queue) + 1)

    def test_jump_landing_and_reinput_precede_next_contact_even_across_short_slots(self):
        state = self.state
        dt = 1 / 120
        for interval in (1, 25):
            with patch.object(backend, 'DAY_NIGHT_INTERVAL', interval), \
                 patch.object(state, 'collides_with_obstacle', return_value=False), \
                 patch.object(backend.random, 'random', return_value=0.999):
                for slot in (0, 6, 7, 8, 15, 16, 2000):
                    with self.subTest(interval=interval, slot=slot):
                        state.reset()
                        state.background_elapsed = (slot + 0.99) * interval
                        state.first_obstacle = False
                        state.spawn_obstacle('hsucat.png')
                        state.jump()  # 직전 장애물이 사라지는 순간에 뛰어도 회복할 수 있어야 한다.
                        elapsed = 0.0
                        landed = None
                        while state.obstacle_x > state.player_size[0] and elapsed < 3:
                            state.update(dt)
                            elapsed += dt
                            if not state.is_jumping and landed is None:
                                landed = elapsed
                        self.assertIsNotNone(landed)
                        self.assertGreaterEqual(elapsed - landed + dt, config.MIN_RECOVERY_TIME)
                        self.assertFalse(state.is_jumping)
                        state.jump()
                        self.assertTrue(state.is_jumping)

    def test_pause_game_over_and_reset_preserve_progression_contract(self):
        state = self.state
        state.background_elapsed = 16 * config.DAY_NIGHT_INTERVAL + 0.5
        frozen = (state.season_progress, state.difficulty)
        for flag in ('paused', 'game_over'):
            setattr(state, flag, True)
            state.update(100)
            self.assertEqual((state.season_progress, state.difficulty), frozen)
            setattr(state, flag, False)
        state.reset()
        self.assertEqual((state.total_slots_passed, state.current_slot, state.season_cycle_count), (0, 0, 0))
        self.assertEqual(state.speed_multiplier, 1)
        self.assertEqual(config.SCREEN_SIZE, (480, 360))


if __name__ == '__main__':
    unittest.main()
