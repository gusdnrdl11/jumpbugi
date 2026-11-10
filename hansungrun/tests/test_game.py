"""실제 이미지와 입력 이벤트를 사용하는 화면 없는 실행 테스트."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

if __package__ and __package__.startswith('hansungrun.'):
    from ..main import HansungRun
    from ..storage import load_high_score
else:
    from main import HansungRun
    from storage import load_high_score


class GameTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.directory = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.score_path = Path(self.directory.name) / 'scores' / 'best.txt'
        self.game = HansungRun(self.score_path)
        pygame.event.clear()

    def tearDown(self):
        pygame.quit()
        self.directory.cleanup()

    def key(self, key):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
        self.game.handle_events()

    def test_render_jump_pause_and_restart(self):
        self.game.draw()
        self.key(pygame.K_SPACE)
        self.game.update()
        self.assertLess(self.game.state.player_y, self.game.state.ground_y)
        self.key(pygame.K_ESCAPE)
        position = self.game.state.player_y
        self.game.update()
        self.assertEqual(self.game.state.player_y, position)
        self.game.draw()
        self.key(pygame.K_ESCAPE)
        self.game.state.obstacle_x = 10000
        for _ in range(60):
            self.game.update()
        self.assertFalse(self.game.state.is_jumping)
        self.game.state.obstacle_x = 60
        self.game.update()
        self.assertTrue(self.game.state.game_over)
        self.game.draw()
        self.key(pygame.K_RETURN)
        self.assertFalse(self.game.state.game_over)
        self.assertEqual(self.game.state.score, 0)

    def test_score_background_and_main_loop_exit(self):
        self.game.state.obstacle_x = -self.game.state.obstacle_size[0]
        self.game.update()
        self.assertEqual(self.game.state.score, 10)
        self.game.update_background(33)
        self.assertEqual(self.game.state.night_alpha, 255)
        self.game.draw()
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.game.run()
        self.assertFalse(self.game.state.running)
        self.assertEqual(load_high_score(self.score_path), 10)


if __name__ == '__main__':
    unittest.main()
