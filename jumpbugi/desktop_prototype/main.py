"""메인: 입력과 반복 실행, 프론트와 백 연결."""
import pygame
if __package__:
    from .backend import GameState
    from .frontend import GameView
    from .config import (FPS, HIGH_SCORE_PATH, PHYSICS_HZ, RUN_FRAME_TICKS,
                         SPLASH_SECONDS, START_FADE_SECONDS)
else:
    from backend import GameState
    from frontend import GameView
    from config import (FPS, HIGH_SCORE_PATH, PHYSICS_HZ, RUN_FRAME_TICKS,
                        SPLASH_SECONDS, START_FADE_SECONDS)


class JumpBugi:
    """첫 실행 연출과 입력을 관리하고 플레이 규칙은 state에 맡긴다."""

    def __init__(self, high_score_path=HIGH_SCORE_PATH):
        self.view = GameView()
        self.state = GameState(
            self.view.player_image.get_size(),
            {name: image.get_size() for name, image in self.view.obstacle_images.items()},
            len(self.view.run_frames), self.view.background_width, high_score_path,
            player_masks=self.view.player_masks, obstacle_masks=self.view.obstacle_masks,
            obstacle_frame_masks=self.view.obstacle_frame_masks,
        )
        self.clock = pygame.time.Clock()
        self.phase = 'splash'
        self.intro_elapsed = 0.0
        self.transition_elapsed = 0.0

    def reset(self):
        self.state.reset()
        self.view.sync_background(self.state)
        # 재시작할 때는 시작 이미지와 흰 배경 대기를 반복하지 않는다.
        self.phase = 'playing'
        self.intro_elapsed = 0.0
        self.transition_elapsed = 0.0

    def update(self, dt=1 / PHYSICS_HZ):
        if self.phase != 'playing':
            self.intro_elapsed += max(0.0, dt)
            if self.phase == 'splash' and self.intro_elapsed >= SPLASH_SECONDS:
                self.phase = 'ready'
                self.intro_elapsed = 0.0
            elif self.phase == 'transition':
                self.transition_elapsed += max(0.0, dt)
                # 배경은 보이지 않을 때부터 플레이와 같은 속도로 움직인다.
                # 점수·계절·장애물은 멈추고 긴 지연의 이동 제한만 공유한다.
                self.state.scroll_background(min(max(0.0, dt), 0.1))
                if self.transition_elapsed + 1e-9 >= START_FADE_SECONDS:
                    # 스크롤 위치는 유지하고 달리던 자세와 시간도 그대로 잇는다.
                    self.state.animation_tick = (
                        self.intro_elapsed * PHYSICS_HZ
                        % (len(self.view.run_frames) * RUN_FRAME_TICKS))
                    self.phase = 'playing'
            return
        self.state.update(dt)
        self.view.sync_background(self.state)

    def update_background(self, dt):
        if self.phase != 'playing':
            return
        self.state.update_background(dt)
        self.view.sync_background(self.state)

    def draw(self):
        if self.phase == 'playing':
            self.view.draw(self.state)
        else:
            frame = int(self.intro_elapsed * PHYSICS_HZ / RUN_FRAME_TICKS)
            progress = (min(1.0, self.transition_elapsed / START_FADE_SECONDS)
                        if self.phase == 'transition' and START_FADE_SECONDS > 0 else 0.0)
            self.view.draw_startup(self.phase, frame % len(self.view.run_frames), progress,
                                   background_x=self.state.background_x)

    def handle_events(self):
        started = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.state.stop()
                break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F4 and getattr(event, 'mod', 0) & pygame.KMOD_CTRL:
                    self.state.stop()
                    break
                elif self.phase in ('splash', 'transition') or started:
                    continue
                elif self.phase == 'ready':
                    self.phase = 'transition'
                    self.transition_elapsed = 0.0
                    # 시작에 사용한 Space나 같은 입력 묶음의 키로 점프하지 않는다.
                    started = True
                elif event.key == pygame.K_ESCAPE:
                    self.state.paused = not self.state.paused
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
        JumpBugi().run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
