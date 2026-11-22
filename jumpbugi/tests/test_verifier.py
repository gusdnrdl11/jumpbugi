"""검증 보고서가 서로 다른 동작이나 끊긴 안전 구간을 섞지 않는지 검사한다."""
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
    from ..desktop_prototype.frontend import GameView
    from ..tools import verify_difficulty as verifier
else:
    from desktop_prototype import backend, config
    from desktop_prototype.frontend import GameView
    from tools import verify_difficulty as verifier


class VerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.view = GameView()
        cls.directory = tempfile.TemporaryDirectory()
        cls.record = Path(cls.directory.name) / 'score.txt'

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()
        pygame.quit()

    def new_state(self):
        view = self.view
        return backend.GameState(
            view.player_image.get_size(),
            {name: image.get_size() for name, image in view.obstacle_images.items()},
            len(view.run_frames), view.background_width, self.record,
            player_masks=view.player_masks, obstacle_masks=view.obstacle_masks,
            obstacle_frame_masks=view.obstacle_frame_masks)

    def test_disjoint_safe_inputs_never_become_one_reported_safe_interval(self):
        self.assertEqual(verifier.safe_runs([], 4), [])
        self.assertEqual(verifier.safe_runs([80, 84, 88, 100, 108, 112], 4),
                         [[80, 88], [100, 100], [108, 112]])

    def test_plans_follow_tunable_unlock_slots_and_keep_variants_separate(self):
        self.assertEqual({plan.name for plan in verifier.plans_for_slot(0)},
                         set(config.OBSTACLE_FILES))
        plans = verifier.plans_for_slot(config.SJ_GROUP_UNLOCK_SLOT)
        self.assertEqual(len({plan.key for plan in plans}), len(plans))
        self.assertEqual({plan.name for plan in plans}, set(self.view.obstacle_images))
        self.assertEqual(sum(plan.name == 'sj_pair' for plan in plans), 3 ** 2)
        self.assertEqual(sum(plan.name == 'sj_triple' for plan in plans), 3 ** 3)
        for slot, expected in ((config.WAVE_JUMP_UNLOCK_SLOT - 1, {'fall', 'run'}),
                               (config.WAVE_JUMP_UNLOCK_SLOT, {'fall', 'high', 'low', 'run'})):
            self.assertEqual({plan.variants[0] for plan in verifier.plans_for_slot(slot)
                              if plan.name == 'hsucat_run.png'}, expected)
        with patch.object(config, 'CHICKEN_UNLOCK_SLOT', 3), \
             patch.object(config, 'HSUCAT_UNLOCK_SLOT', 5), \
             patch.object(config, 'SJ_UNLOCK_SLOT', 7), \
             patch.object(config, 'SJ_GROUP_UNLOCK_SLOT', 9), \
             patch.object(config, 'SJ_ESCAPE_UNLOCK_SLOT', 9):
            for slot, names in ((2, config.CHICKEN_TYPES), (4, config.HSUCAT_TYPES),
                                (6, ('sj_run.png', 'sj_burrow')), (8, config.SJ_CLUSTER_TYPES + ('sj_escape',))):
                self.assertTrue({plan.name for plan in verifier.plans_for_slot(slot)}.isdisjoint(names))
                self.assertTrue(set(names).issubset({plan.name for plan in verifier.plans_for_slot(slot + 1)}))

    def test_every_fixed_plan_really_selects_its_requested_spawn_motion(self):
        for slot in (config.HSUCAT_UNLOCK_SLOT, config.SJ_GROUP_UNLOCK_SLOT):
            for plan in verifier.plans_for_slot(slot):
                with self.subTest(slot=slot, plan=plan.key):
                    state = self.new_state()
                    verifier.spawn_plan(state, plan, slot)
                    self.assertEqual(state.obstacle_name, plan.name)
                    if plan.name in config.SJ_CLUSTER_TYPES:
                        self.assertEqual(tuple(member.pattern for member in state.sj_members), plan.variants)
                    elif plan.name in config.WAVE_IMAGE_FILES or plan.name in config.SJ_SINGLE_JUMP_TYPES:
                        self.assertEqual(state.wave_jump.pattern if state.wave_jump else None, plan.variants[0])
                    elif plan.name == 'hsucat_run.png':
                        self.assertEqual(state.hsucat_run_mode, plan.variants[0])
                    elif plan.name.endswith('_flying'):
                        self.assertEqual(state.chicken_flight_level, plan.variants[0])
                    elif plan.name in config.SJ_HOLE_TYPES:
                        self.assertEqual(state.sj_hole_timing, plan.variants[0])

    def test_native_plan_controller_clears_every_variant_and_scores_every_member(self):
        for slot in (config.SJ_GROUP_UNLOCK_SLOT, 2 * config.SLOTS_PER_CYCLE):
            for plan in verifier.plans_for_slot(slot):
                with self.subTest(slot=slot, plan=plan.key):
                    state = self.new_state()
                    verifier.spawn_plan(state, plan, slot)
                    expected = state.obstacle_pass_bonus
                    jumped = False
                    for _ in range(3 * 120):
                        if (state.obstacle_requires_jump and not jumped
                                and state.obstacle_x <= verifier.jump_target(state)):
                            state.jump()
                            jumped = True
                        state.update(1 / 120)
                        self.assertFalse(state.game_over)
                        if verifier.pass_bonus(state) >= expected:
                            break
                    self.assertEqual(verifier.pass_bonus(state), expected)


if __name__ == '__main__':
    unittest.main()
