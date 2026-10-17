from pathlib import Path

import pygame


# 구조 개선: 게임 설정을 한곳에 모아 수치를 쉽게 조정한다.
SCREEN_SIZE = (480, 360)
FPS = 60
CHARACTER_HEIGHT = 120
PLAYER_GROUND_OFFSET = 2
OBSTACLE_GROUND_OFFSET = 7
OBSTACLE_SPEED = 6
JUMP_SPEED = -15
GRAVITY = 0.6
PASS_BONUS = 10
PLAYER_HITBOX_SHRINK = (-40, -40)
OBSTACLE_HITBOX_SHRINK = (-50, -35)
IMAGE_DIR = Path(__file__).resolve().parent / 'image'


def load_image(filename, *, size=None, height=None):
    """공통 이미지 로딩과 비율 유지 크기 조절."""
    # 구조 개선: 실행 디렉터리에 관계없이 이 파일 옆의 이미지를 찾는다.
    image = pygame.image.load(str(IMAGE_DIR / filename)).convert_alpha()
    if height is not None:
        size = (int(image.get_width() * height / image.get_height()), height)
    return pygame.transform.smoothscale(image, size) if size else image


class HansungRun:
    """자원과 상태를 소유하고 입력, 갱신, 그리기를 분리한다."""

    def __init__(self):
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption('Hansungrun')
        self.clock = pygame.time.Clock()
        self.stage = load_image('stage_1.png', size=SCREEN_SIZE)
        self.player_image = load_image('sangsangbugi_side.png', height=CHARACTER_HEIGHT)
        self.obstacle_image = load_image('hansungcat.png', height=CHARACTER_HEIGHT)
        self.ground_y = SCREEN_SIZE[1] - CHARACTER_HEIGHT + PLAYER_GROUND_OFFSET
        self.obstacle_y = SCREEN_SIZE[1] - CHARACTER_HEIGHT + OBSTACLE_GROUND_OFFSET
        self.score_font = pygame.font.SysFont(None, 30)
        self.game_over_text = pygame.font.SysFont(None, 80).render(
            'GAME OVER', True, (255, 0, 0)
        )
        self.restart_text = pygame.font.SysFont(None, 30).render(
            'press the Enter Restart', True, (255, 0, 0)
        )
        self.game_over_rect = self.game_over_text.get_rect(
            center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2)
        )
        self.running = True
        self.reset()

    def reset(self):
        # 구조 개선: 시작과 재시작의 초기화를 공유해 상태 누락을 방지한다.
        self.player_y = self.ground_y
        self.velocity_y = 0
        self.is_jumping = False
        self.obstacle_x = SCREEN_SIZE[0]
        self.score = 0
        self.passed = False
        self.game_over = False

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif self.game_over and event.key == pygame.K_RETURN:
                    self.reset()
                elif not self.game_over and event.key == pygame.K_SPACE:
                    if not self.is_jumping:
                        self.velocity_y = JUMP_SPEED
                        self.is_jumping = True

    def update(self):
        if self.game_over:
            return
        # 기존 조작감을 유지하기 위해 이동과 중력은 60FPS 프레임 단위로 유지한다.
        if self.is_jumping:
            self.velocity_y += GRAVITY
            self.player_y += self.velocity_y
            if self.player_y >= self.ground_y:
                self.player_y = self.ground_y
                self.velocity_y = 0
                self.is_jumping = False

        self.obstacle_x -= OBSTACLE_SPEED
        player_rect = self.player_image.get_rect(topleft=(0, self.player_y))
        obstacle_rect = self.obstacle_image.get_rect(
            topleft=(self.obstacle_x, self.obstacle_y)
        )
        player_hitbox = player_rect.inflate(*PLAYER_HITBOX_SHRINK)
        obstacle_hitbox = obstacle_rect.inflate(*OBSTACLE_HITBOX_SHRINK)
        if player_hitbox.colliderect(obstacle_hitbox):
            self.game_over = True
        if player_rect.left >= obstacle_rect.right and not self.passed:
            self.score += PASS_BONUS
            self.passed = True
        if self.obstacle_x + self.obstacle_image.get_width() < 0:
            self.obstacle_x = SCREEN_SIZE[0]
            self.passed = False

    def draw(self):
        # 배경 → 장애물 → 플레이어 → 점수 → 안내 순으로 겹쳐 그린다.
        self.screen.blit(self.stage, (0, 0))
        self.screen.blit(self.obstacle_image, (self.obstacle_x, self.obstacle_y))
        self.screen.blit(self.player_image, (0, self.player_y))
        self.screen.blit(self.score_font.render(str(self.score), True, (0, 0, 0)), (10, 10))
        if self.game_over:
            self.screen.blit(self.game_over_text, self.game_over_rect)
            self.screen.blit(self.restart_text,
                             (self.game_over_rect.x + 50, self.game_over_rect.y + 80))
        pygame.display.update()

    def run(self):
        # 구조 개선: 메인 루프는 각 단계의 실행 순서만 관리한다.
        while self.running:
            self.clock.tick(FPS)
            self.handle_events()
            if not self.running:
                break
            self.update()
            self.draw()


def main():
    pygame.init()
    # 구조 개선: 로딩 또는 실행 중 오류가 발생해도 pygame 자원을 정리한다.
    try:
        HansungRun().run()
    finally:
        pygame.quit()


# 구조 개선: import할 때 게임이 실행되지 않아 로직을 독립적으로 검증할 수 있다.
if __name__ == '__main__':
    main()

