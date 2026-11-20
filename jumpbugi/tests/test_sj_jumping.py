"""둘째 봄 상찌의 혼합 점프·공중 포즈·실제 회피와 마리별 득점을 검사한다."""
import itertools
import os
import random
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


class SjJumpingTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = JumpBugi(Path(directory.name) / 'score.txt')
        self.app.reset()
        pygame.event.clear()

    def spawn_plan(self, name, patterns, seed=1, seconds=None):
        generator = random.Random(seed)
        rolls = {'high': 0.0, 'low': config.SJ_HOP_PROBABILITY * 0.75, None: 1.0}
        self.app.state.background_elapsed = (config.SJ_JUMP_UNLOCK_SLOT * config.DAY_NIGHT_INTERVAL
                                            if seconds is None else seconds)
        with patch.object(backend.random, 'random', side_effect=[rolls[pattern] for pattern in patterns]), \
             patch.object(backend.random, 'uniform', side_effect=generator.uniform):
            self.app.state.spawn_obstacle(name)

    def clear_encounter(self, name, patterns, seconds, hz):
        self.app.reset()
        self.spawn_plan(name, patterns, seed=seconds + hz, seconds=seconds)
        state = self.app.state
        members = tuple(state.sj_members)
        count = len(members) or 1
        needs_jump = any(pattern != 'high' for pattern in patterns)
        jumped = False
        for _ in range(3 * hz):
            speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier
            if needs_jump and not jumped and state.obstacle_x <= 60 + speed * 0.30:
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                jumped = True
            self.app.handle_events()
            self.app.update(1 / hz)
            self.assertFalse(state.game_over)
            if state.score - int(state.survival_elapsed + 1e-9) >= count * config.PASS_BONUS:
                break
        self.assertEqual(jumped, needs_jump)
        self.assertTrue(all(member.passed for member in members))
        self.assertEqual(state.score - int(state.survival_elapsed + 1e-9), count * config.PASS_BONUS)

    def test_basic_sj_uses_four_aligned_wave_frames_and_masks(self):
        frames = self.app.view.obstacle_frames['sj.png']
        masks = self.app.view.obstacle_frame_masks['sj.png']
        self.assertEqual(config.SJ_BASE_IMAGE_FILE, 'sj_wave.png')
        self.assertEqual(len(frames), 4)
        self.assertEqual(len(masks), 4)
        self.assertEqual(len({pygame.image.tobytes(frame, 'RGBA') for frame in frames}), 4)
        self.assertEqual(len({frame.get_size() for frame in frames}), 1)
        state = self.app.state
        state.spawn_obstacle('sj.png')
        self.assertEqual(state.sj_cluster_parts, ())
        for index, (frame, mask) in enumerate(zip(frames, masks)):
            state.obstacle_animation_tick = index * config.OBSTACLE_FRAME_TICKS
            self.assertEqual(state.obstacle_frame_index, index)
            self.assertEqual(frame.get_height(), config.OBSTACLE_HEIGHTS['sj.png'])
            self.assertEqual(mask.get_size(), frame.get_size())
            self.assertGreater(mask.count(), 0)
            self.assertGreaterEqual(frame.get_bounding_rect(min_alpha=20).bottom, frame.get_height() - 1)

    def test_first_year_has_no_jumps_and_existing_plans_do_not_change_at_unlock(self):
        state = self.app.state
        self.assertEqual(config.SJ_GROUP_UNLOCK_SLOT, 8)
        self.assertEqual(config.SJ_JUMP_UNLOCK_SLOT, 8)
        unlock_seconds = config.SJ_JUMP_UNLOCK_SLOT * config.DAY_NIGHT_INTERVAL
        for seconds in tuple(slot * config.DAY_NIGHT_INTERVAL for slot in (0, 2, 4, 6, 7)) + (unlock_seconds - 0.001,):
            for name in config.SJ_SINGLE_JUMP_TYPES + config.SJ_CLUSTER_TYPES:
                with self.subTest(seconds=seconds, name=name):
                    state.background_elapsed = seconds
                    with patch.object(backend.random, 'random', side_effect=AssertionError('첫해 점프 선택')):
                        state.spawn_obstacle(name)  # 이름 지정은 검증용으로 계절 제한을 우회한다.
                    self.assertFalse(state.sj_groups_enabled)
                    self.assertFalse(state.sj_jumps_enabled)
                    self.assertIsNone(state.wave_jump)
                    self.assertTrue(all(member.pattern is None for member in state.sj_members))
        state.background_elapsed = unlock_seconds - 0.001
        state.spawn_obstacle('sj_pair')
        original = tuple(state.sj_members)
        state.background_elapsed = unlock_seconds
        state.obstacle_x = 300
        state.player_y = -1000
        with patch.object(backend.random, 'random', side_effect=AssertionError('접근 중 재선택')):
            self.app.update(1 / 120)
        self.assertTrue(state.sj_groups_enabled)
        self.assertEqual(tuple(state.sj_members), original)
        self.assertTrue(all(member.jump_plan is None for member in original))

    def test_every_member_selects_ground_low_or_high_and_separate_departures(self):
        state = self.app.state
        for name, count in zip(config.SJ_CLUSTER_TYPES, (2, 3)):
            for patterns in itertools.product((None, 'low', 'high'), repeat=count):
                with self.subTest(name=name, patterns=patterns):
                    self.spawn_plan(name, patterns, seed=count)
                    self.assertEqual(tuple(member.pattern for member in state.sj_members), patterns)
                    self.assertEqual(tuple(member.hop_enabled for member in state.sj_members),
                                     tuple(pattern is not None for pattern in patterns))
                    self.assertEqual(tuple(member.offset_x for member in state.sj_members),
                                     tuple(index * (state.obstacle_sizes['sj.png'][0] + config.SJ_CLUSTER_GAP)
                                           for index in range(count)))
                    starts = sorted(member.trigger_x for member in state.sj_members if member.hop_enabled)
                    self.assertTrue(all(second - first + 1e-9 >= config.SJ_HOP_TRIGGER_SPACING
                                        - config.SJ_HOP_TRIGGER_JITTER
                                        for first, second in zip(starts, starts[1:])))
                    self.assertTrue(all(not member.is_jumping(state.obstacle_x) for member in state.sj_members))
                    self.assertEqual(state.obstacle_requires_jump, any(pattern != 'high' for pattern in patterns))

    def test_distance_plans_depart_separately_freeze_hands_and_land(self):
        state = self.app.state
        for patterns in (('low', 'high'), ('high', 'low', 'high')):
            with self.subTest(patterns=patterns):
                self.spawn_plan('sj_pair' if len(patterns) == 2 else 'sj_triple', patterns)
                members = tuple(state.sj_members)
                first_x = max(member.trigger_x for member in members) + 20
                last_x = min(member.jump_plan.center_x - member.jump_plan.half_distance
                             for member in members) - 20
                starts, peaks = {}, [0.0] * len(members)
                air_frames = [set() for _ in members]
                ground_frames = [set() for _ in members]
                for tick, x in enumerate(range(int(first_x), int(last_x) - 1, -4)):
                    state.obstacle_x = x
                    state.obstacle_animation_tick = tick
                    for index, (member, part) in enumerate(zip(members, state.sj_cluster_parts)):
                        offset = member.y_offset(x)
                        self.assertLessEqual(offset, 0)
                        self.assertGreaterEqual(offset, -config.SJ_JUMP_HEIGHTS[member.pattern])
                        self.assertGreaterEqual(part[2], 0)
                        self.assertLessEqual(part[2] + state.obstacle_sizes['sj.png'][1], config.SCREEN_SIZE[1])
                        peaks[index] = max(peaks[index], -offset)
                        if member.is_jumping(x):
                            starts.setdefault(index, x)
                            air_frames[index].add(part[0])
                        else:
                            ground_frames[index].add(part[0])
                self.assertEqual(len(starts), len(members))
                self.assertEqual(len(set(starts.values())), len(members))
                self.assertTrue(all(frames == {0} for frames in air_frames))
                self.assertTrue(all(len(frames) > 1 for frames in ground_frames))
                self.assertTrue(all(peak > config.SJ_JUMP_HEIGHTS[member.pattern] * 0.98
                                    for peak, member in zip(peaks, members)))
                self.assertTrue(all(member.y_offset(last_x) == 0 for member in members))

    def test_high_members_clear_the_players_highest_jump_while_low_members_are_crossed(self):
        state = self.app.state
        state.obstacle_x = 100000
        state.jump()
        highest_y = state.player_y
        for _ in range(120):
            state.update_step(0.25)
            highest_y = min(highest_y, state.player_y)
        self.assertLess(highest_y, state.ground_y - 150)
        for name, patterns in (('sj_pair', ('high', 'low')), ('sj_pair', ('low', 'high')),
                               ('sj_triple', ('high', 'low', 'high'))):
            self.spawn_plan(name, patterns)
            state.player_y = highest_y
            state.is_jumping = True
            for x in range(-state.obstacle_size[0], state.player_size[0] + 1):
                state.obstacle_x = x + 0.75
                self.assertFalse(state.collides_with_obstacle())
                for member, (_, part_x, part_y) in zip(state.sj_members, state.sj_cluster_parts):
                    if member.pattern == 'high' and part_x < state.player_size[0] \
                            and part_x + state.obstacle_sizes['sj.png'][0] > 0:
                        self.assertLessEqual(part_y + state.obstacle_sizes['sj.png'][1],
                                             highest_y - config.SJ_HIGH_PLAYER_CLEARANCE)

    def test_airborne_collision_matches_each_visible_position_and_frame(self):
        state = self.app.state
        self.spawn_plan('sj_pair', (None, 'low'))
        state.obstacle_animation_tick = 3 * config.OBSTACLE_FRAME_TICKS
        state.player_y = 190.75
        contact = None
        for x in range(-state.obstacle_size[0], state.player_size[0] + 1):
            state.obstacle_x = x + 0.75
            if state.collides_with_obstacle():
                contact = state.obstacle_x
                break
        self.assertIsNotNone(contact)
        parts = state.sj_cluster_parts
        self.assertEqual(tuple(frame for frame, _, _ in parts), (3, 0))
        self.assertFalse(pygame.Rect(0, int(state.player_y), *state.player_size).colliderect(
            pygame.Rect(int(state.obstacle_x), int(state.obstacle_y), *state.obstacle_size)))
        with patch.object(self.app.view, 'screen', wraps=self.app.view.screen) as screen:
            self.app.draw()
        for call, (frame, x, y) in zip(screen.blit.call_args_list[2:4], parts):
            self.assertIs(call.args[0], self.app.view.obstacle_frames['sj.png'][frame])
            self.assertEqual(call.args[1], (x, y))
        state.update_step(0)
        self.assertTrue(state.game_over)

    def test_distance_hop_positions_match_at_30_60_and_120_fps(self):
        results = []
        for hz in (30, 60, 120):
            self.app.reset()
            state = self.app.state
            self.spawn_plan('sj_triple', ('high', 'low', 'high'), seed=7)
            state.obstacle_x = 390
            state.player_y = -1000
            for _ in range(hz // 5):
                self.app.update(1 / hz)
            results.append((state.obstacle_x, state.sj_cluster_parts))
        for actual in results[1:]:
            self.assertAlmostEqual(actual[0], results[0][0])
            self.assertEqual(actual[1], results[0][1])

    def test_pause_game_over_reset_and_asset_reuse_include_member_plans(self):
        state = self.app.state
        self.spawn_plan('sj_triple', ('high', None, 'low'))
        state.obstacle_x = 350
        state.player_y = -1000
        for flag in ('paused', 'game_over'):
            setattr(state, flag, True)
            before = (state.obstacle_x, state.obstacle_animation_tick,
                      tuple(member.passed for member in state.sj_members), state.sj_cluster_parts)
            with patch.object(pygame.image, 'load', side_effect=AssertionError('이미지 재로딩')), \
                 patch.object(backend.random, 'random', side_effect=AssertionError('점프 재선택')):
                self.app.update(2)
                self.app.draw()
            self.assertEqual((state.obstacle_x, state.obstacle_animation_tick,
                              tuple(member.passed for member in state.sj_members), state.sj_cluster_parts), before)
            setattr(state, flag, False)
        state.spawn_obstacle('hsucat.png')
        self.assertEqual(state.sj_members, [])
        self.assertEqual(state.sj_cluster_parts, ())
        self.spawn_plan('sj_pair', ('high', 'low'))
        self.app.reset()
        self.assertEqual(state.sj_members, [])
        self.assertIsNone(state.wave_jump)
        self.assertFalse(state.sj_jumps_enabled)

    def test_every_mixed_group_is_clearable_at_second_year_speeds_and_frame_rates(self):
        for name, count in zip(config.SJ_CLUSTER_TYPES, (2, 3)):
            for patterns in itertools.product((None, 'low', 'high'), repeat=count):
                for seconds in (slot * config.DAY_NIGHT_INTERVAL for slot in (8, 10, 20)):
                    for hz in (30, 60, 120):
                        with self.subTest(name=name, patterns=patterns, seconds=seconds, hz=hz):
                            self.clear_encounter(name, patterns, seconds, hz)

    def test_single_running_sj_selects_ground_low_or_high_after_the_first_year(self):
        for name in config.SJ_SINGLE_JUMP_TYPES:
            for pattern in (None, 'low', 'high'):
                for seconds in (slot * config.DAY_NIGHT_INTERVAL for slot in (8, 10, 20)):
                    for hz in (30, 60, 120):
                        with self.subTest(name=name, pattern=pattern, seconds=seconds, hz=hz):
                            self.clear_encounter(name, (pattern,), seconds, hz)


if __name__ == '__main__':
    unittest.main()
