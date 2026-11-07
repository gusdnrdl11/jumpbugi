"""메인: 입력과 반복 실행, 프론트와 백 연결."""
import pygame
if __package__:
    from .backend import GameState
    from .frontend import GameView
    from .config import FPS, HIGH_SCORE_PATH, PHYSICS_HZ
else:
    from backend import GameState
    from frontend import GameView
    from config import FPS, HIGH_SCORE_PATH, PHYSICS_HZ


class HansungRun:
    """state는 게임 데이터, view는 화면을 맡는다."""

    def __init__(self, high_score_path=HIGH_SCORE_PATH):
        self.view = GameView()
        self.state = GameState(
            self.view.player_image.get_size(),
            {name: image.get_size() for name, image in self.view.obstacle_images.items()},
            len(self.view.run_frames), self.view.background_width, high_score_path,
        )
        self.clock = pygame.time.Clock()

    def reset(self):
        self.state.reset()
        self.view.sync_background(self.state.night_alpha)

    def update(self, dt=1 / PHYSICS_HZ):
        self.state.update(dt)
        self.view.sync_background(self.state.night_alpha)

    def update_background(self, dt):
        self.state.update_background(dt)
        self.view.sync_background(self.state.night_alpha)

    def draw(self):
        self.view.draw(self.state)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.state.stop()
            elif event.type == pygame.KEYDOWN:
                # ESC는 정지/재개, Ctrl+F4는 기록을 저장하고 종료한다.
                if event.key == pygame.K_ESCAPE:
                    self.state.paused = not self.state.paused
                elif event.key == pygame.K_F4 and getattr(event, 'mod', 0) & pygame.KMOD_CTRL:
                    self.state.stop()
                elif self.state.paused:
                    continue  # 정지 중에는 점프와 재시작을 받지 않는다.
                elif self.state.game_over and event.key == pygame.K_RETURN:
                    self.reset()
                elif not self.state.game_over and event.key == pygame.K_SPACE:
                    if not self.state.is_jumping:
                        self.state.jump()


    def run(self):
        # 구조 개선: 메인 루프는 각 단계의 실행 순서만 관리한다.
        while self.state.running:
            # 높은 출력 빈도와 경과 시간 적용으로 이동 간격과 속도 편차를 줄인다.
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            if not self.state.running:
                break
            self.update(dt)
            self.draw()


def main():
    pygame.init()
    try:
        HansungRun().run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
