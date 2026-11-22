"""아래 통과와 점프 회피의 보너스·상찌 마리별 점수 보존을 검사한다."""
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
    from ..desktop_prototype import backend, config
    from ..desktop_prototype.main import JumpBugi
else:
    from desktop_prototype import backend, config
    from desktop_prototype.main import JumpBugi


class UnderpassScoringTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.record = Path(directory.name) / 'score.txt'
        self.app = JumpBugi(self.record)
        self.app.reset()
        pygame.event.clear()

    def spawn_sj(self, name, patterns, seconds=None):
        state = self.app.state
        state.background_elapsed = (config.SJ_JUMP_UNLOCK_SLOT * config.DAY_NIGHT_INTERVAL) if seconds is None else seconds
        rolls = [0.0 if pattern == 'high' else config.SJ_HOP_PROBABILITY * 0.75
                 if pattern == 'low' else 1.0 for pattern in patterns]
        with patch.object(backend.random, 'random', side_effect=rolls), \
             patch.object(backend.random, 'uniform', return_value=12.5):
            state.spawn_obstacle(name)
        return tuple(state.sj_members)

    def single_cases(self):
        cases = [(name, pattern, pattern not in ('high', 'near'))
                 for name in config.WAVE_IMAGE_FILES for pattern in (None, 'high', 'near', 'low')]
        cases += [(name, level, level == 'low') for name in config.CHICKEN_TYPES
                  if name.endswith('_flying') for level in config.FLYING_LEVELS]
        cases += [(name, None, True) for name in config.CHICKEN_TYPES if name.endswith('_ground')]
        cases += [('hsucat_run.png', mode, mode != 'high') for mode in config.HSUCAT_RUN_MODES]
        cases += [('hsucat_crouch.png', None, True), ('hsucat_book.png', None, True)]
        cases += [(name, pattern, pattern != 'high') for name in config.SJ_SINGLE_JUMP_TYPES
                  for pattern in (None, 'high', 'low')]
        cases += [('sj_burrow', timing, False) for timing in config.SJ_BURROW_PROFILES]
        cases += [('sj_escape', timing, True) for timing in config.SJ_ESCAPE_PROFILES]
        return cases

    def spawn_single_case(self, name, pattern, seconds):
        state = self.app.state
        state.background_elapsed = seconds
        if name in config.SJ_SINGLE_JUMP_TYPES:
            self.spawn_sj(name, [pattern], seconds)
        elif name in config.WAVE_IMAGE_FILES:
            rolls = [1.0] if pattern is None else [
                0.0, (tuple(config.WAVE_JUMP_HEIGHTS).index(pattern) + 0.5) / len(config.WAVE_JUMP_HEIGHTS)]
            with patch.object(backend.random, 'random', side_effect=rolls):
                state.spawn_obstacle(name)
        elif name.endswith('_flying'):
            roll = (config.FLYING_LEVELS.index(pattern) + 0.5) / len(config.FLYING_LEVELS)
            with patch.object(backend.random, 'random', return_value=roll):
                state.spawn_obstacle(name)
        elif name == 'hsucat_run.png':
            roll = (config.HSUCAT_RUN_MODES.index(pattern) + 0.5) / len(config.HSUCAT_RUN_MODES)
            with patch.object(backend.random, 'random', return_value=roll):
                state.spawn_obstacle(name)
        elif name in config.SJ_HOLE_TYPES:
            profiles = config.SJ_BURROW_PROFILES if name == 'sj_burrow' else config.SJ_ESCAPE_PROFILES
            roll = (tuple(profiles).index(pattern) + 0.5) / len(profiles)
            with patch.object(backend.random, 'random', return_value=roll):
                state.spawn_obstacle(name)
        else:
            state.spawn_obstacle(name)

    def jump_target(self, name):
        state = self.app.state
        speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * state.speed_multiplier
        if name in config.WAVE_IMAGE_FILES:
            return (state.player_size[0] - state.obstacle_size[0]) / 2 + speed * 0.35
        if name == 'hsucat_crouch.png':
            return 95 + speed * 0.12
        return 60 + speed * 0.30

    def bonus(self):
        state = self.app.state
        return state.score - int(state.survival_elapsed + 1e-9) * config.SURVIVAL_POINTS_PER_SECOND

    def test_each_member_scores_once_at_its_own_rendered_horizontal_boundary(self):
        state = self.app.state
        for name, count in zip(config.SJ_CLUSTER_TYPES, (2, 3)):
            with self.subTest(name=name):
                self.app.reset()
                members = self.spawn_sj(name, [None] * count)
                state.player_y = -1000
                width = state.obstacle_sizes['sj.png'][0]
                for index, member in enumerate(members):
                    boundary = -width - member.offset_x
                    # int()로 그리는 마지막 한 열이 남아 있을 때는 아직 통과하지 않았다.
                    state.obstacle_x = boundary + 0.75
                    state.update_step(0)
                    self.assertEqual(state.score, index * config.PASS_BONUS)
                    self.assertFalse(member.passed)
                    state.obstacle_x = boundary
                    state.update_step(0)
                    self.assertEqual(state.score, (index + 1) * config.PASS_BONUS)
                    self.assertTrue(member.passed)
                    self.assertEqual(state.passed, index == count - 1)
                    state.update_step(0)
                    self.assertEqual(state.score, (index + 1) * config.PASS_BONUS)
                self.assertTrue(all(member.passed for member in members))

    def test_one_update_can_award_all_members_and_respawn_resets_their_flags(self):
        state = self.app.state
        for name, count in zip(config.SJ_CLUSTER_TYPES, (2, 3)):
            with self.subTest(name=name):
                self.app.reset()
                members = self.spawn_sj(name, ['high'] * count)
                state.obstacle_x = -state.obstacle_size[0]
                state.update_step(0)
                self.assertEqual(state.score, count * config.PASS_BONUS)
                self.assertTrue(all(member.passed for member in members))
                state.update_step(0)
                self.assertEqual(state.score, count * config.PASS_BONUS)
                state.update(1 / 120)
                self.assertEqual(state.score, count * config.PASS_BONUS)
                self.assertFalse(state.passed)
                fresh = self.spawn_sj(name, [None] * count)
                self.assertTrue(all(not member.passed for member in fresh))
                state.player_y = -1000
                state.obstacle_x = -state.obstacle_sizes['sj.png'][0]
                state.update_step(0)
                self.assertEqual(state.score, (count + 1) * config.PASS_BONUS)

    def test_single_underpasses_and_jump_overs_each_award_ten_points(self):
        state = self.app.state
        cases = self.single_cases()
        self.assertEqual(len(cases), 32)
        self.assertEqual({name for name, _, _ in cases},
                         set(self.app.view.obstacle_images) - set(config.SJ_CLUSTER_TYPES))
        for name, pattern, should_jump in cases:
            for stage in (8, 20):
                for hz in (30, 60, 120):
                    with self.subTest(name=name, pattern=pattern, stage=stage, hz=hz):
                        self.app.reset()
                        self.spawn_single_case(name, pattern, stage * config.DAY_NIGHT_INTERVAL)
                        self.assertEqual(state.obstacle_requires_jump, should_jump)
                        jumped = False
                        crossed_contact = False
                        for _ in range(3 * hz):
                            if should_jump and not jumped and state.obstacle_x <= self.jump_target(name):
                                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                                jumped = True
                            if state.obstacle_x <= state.player_size[0] and state.obstacle_x + state.obstacle_size[0] > 0:
                                crossed_contact = True
                            self.app.handle_events()
                            self.app.update(1 / hz)
                            self.assertFalse(state.game_over)
                            if self.bonus() >= config.PASS_BONUS:
                                break
                        self.assertTrue(crossed_contact)
                        self.assertEqual(jumped, should_jump)
                        self.assertEqual(self.bonus(), config.PASS_BONUS)
                        score = state.score
                        state.update_step(0)
                        self.assertEqual(state.score, score)

    def test_every_single_plan_scores_once_at_horizontal_boundary_with_either_player_state(self):
        state = self.app.state
        for name, pattern, _ in self.single_cases():
            for airborne in (False, True):
                with self.subTest(name=name, pattern=pattern, airborne=airborne):
                    self.app.reset()
                    self.spawn_single_case(name, pattern, 8 * config.DAY_NIGHT_INTERVAL)
                    state.is_jumping = airborne
                    state.player_y = state.ground_y - (20 if airborne else 0)
                    boundary = -state.obstacle_size[0]
                    state.obstacle_x = boundary + 0.75
                    state.update_step(0)
                    self.assertEqual(self.bonus(), 0)
                    self.assertFalse(state.passed)
                    state.obstacle_x = boundary
                    state.update_step(0)
                    self.assertFalse(state.game_over)
                    self.assertEqual(self.bonus(), config.PASS_BONUS)
                    self.assertTrue(state.passed)
                    state.update_step(0)
                    self.assertEqual(self.bonus(), config.PASS_BONUS)
                    self.spawn_single_case(name, pattern, 8 * config.DAY_NIGHT_INTERVAL)
                    self.assertFalse(state.passed)

    def test_all_high_and_mixed_clusters_award_ten_for_every_member(self):
        state = self.app.state
        for name, count in zip(config.SJ_CLUSTER_TYPES, (2, 3)):
            for patterns in (['high'] * count, ['high'] + ['low'] * (count - 1)):
                for stage in (8, 20):
                    for hz in (30, 60, 120):
                        with self.subTest(name=name, patterns=patterns, stage=stage, hz=hz):
                            self.app.reset()
                            members = self.spawn_sj(name, patterns, stage * config.DAY_NIGHT_INTERVAL)
                            jumped = False
                            expected_bonus = count * config.PASS_BONUS
                            for _ in range(3 * hz):
                                if state.obstacle_requires_jump and not jumped and state.obstacle_x <= self.jump_target(name):
                                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                                    jumped = True
                                self.app.handle_events()
                                self.app.update(1 / hz)
                                self.assertFalse(state.game_over)
                                self.assertLessEqual(self.bonus(), expected_bonus)
                                if self.bonus() == expected_bonus:
                                    break
                            self.assertEqual(jumped, 'low' in patterns)
                            self.assertEqual(self.bonus(), expected_bonus)
                            self.assertTrue(all(member.passed for member in members))

    def test_passed_member_is_rewarded_before_a_later_members_fatal_collision(self):
        state = self.app.state
        members = self.spawn_sj('sj_pair', ['high', None])
        # 충돌과 점수 처리의 순서를 검사하므로 윤곽 대신 명확한 꽉 찬 마스크를 쓴다.
        state.player_masks = [pygame.Mask(state.player_size, fill=True) for _ in state.player_masks]
        state.obstacle_frame_masks = dict(state.obstacle_frame_masks)
        state.obstacle_frame_masks['sj.png'] = [pygame.Mask(state.obstacle_sizes['sj.png'], fill=True)
                                               for _ in range(4)]
        state.obstacle_x = -state.obstacle_sizes['sj.png'][0]
        self.assertTrue(state.collides_with_obstacle())
        state.update_step(0)
        self.assertTrue(state.game_over)
        self.assertTrue(members[0].passed)
        self.assertFalse(members[1].passed)
        self.assertEqual(state.score, config.PASS_BONUS)
        self.assertEqual(state.high_score, config.PASS_BONUS)
        self.assertEqual(int(self.record.read_text()), config.PASS_BONUS)
        state.update(10)
        self.assertEqual(state.score, config.PASS_BONUS)

    def test_pause_game_over_and_reset_do_not_duplicate_member_points(self):
        state = self.app.state
        members = self.spawn_sj('sj_triple', [None] * 3)
        state.player_y = -1000
        state.obstacle_x = -state.obstacle_sizes['sj.png'][0]
        state.update_step(0)
        self.assertEqual(state.score, config.PASS_BONUS)
        for flag in ('paused', 'game_over'):
            setattr(state, flag, True)
            before = (state.score, state.obstacle_x, tuple(member.passed for member in members))
            state.update(2)
            self.assertEqual((state.score, state.obstacle_x, tuple(member.passed for member in members)), before)
            setattr(state, flag, False)
        self.app.reset()
        self.assertEqual(state.score, 0)
        self.assertEqual(state.sj_members, [])
        fresh = self.spawn_sj('sj_triple', [None] * 3)
        self.assertTrue(all(not member.passed for member in fresh))
        state.player_y = -1000
        state.obstacle_x = -state.obstacle_sizes['sj.png'][0]
        state.update_step(0)
        self.assertEqual(state.score, config.PASS_BONUS)

    def test_survival_points_and_partial_member_bonuses_are_added_once(self):
        state = self.app.state
        self.spawn_sj('sj_triple', [None] * 3)
        state.player_y = -1000
        state.survival_elapsed = 1.99
        state.score = config.SURVIVAL_POINTS_PER_SECOND
        state.obstacle_x = -state.obstacle_sizes['sj.png'][0] + 1.0
        state.update(0.01)
        self.assertEqual(state.score, 2 * config.SURVIVAL_POINTS_PER_SECOND + config.PASS_BONUS)
        state.update(0.001)
        self.assertEqual(state.score, 2 * config.SURVIVAL_POINTS_PER_SECOND + config.PASS_BONUS)


if __name__ == '__main__':
    unittest.main()
