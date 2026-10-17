from pathlib import Path

import random
import pygame


# 구조 개선: 게임 설정을 한곳에 모아 수치를 쉽게 조정한다.
SCREEN_SIZE = (480, 360)
FPS = 60
CHARACTER_HEIGHT = 120
PLAYER_GROUND_OFFSET = 2
OBSTACLE_GROUND_OFFSET = 7
OBSTACLE_SPEED = 6
BACKGROUND_SPEED = OBSTACLE_SPEED
JUMP_SPEED = -15
GRAVITY = 0.6
PASS_BONUS = 10
PLAYER_HITBOX_SHRINK = (-40, -40)
OBSTACLE_HITBOX_SHRINK = (-50, -35)
IMAGE_DIR = Path(__file__).resolve().parent / 'image'
HIGH_SCORE_PATH = Path(__file__).resolve().parent / 'high_score.txt'
HUD_MARGIN = 10
HUD_GAP = 20
RUN_FRAME_TICKS = 6
LEG_START_RATIO = 0.78
OBSTACLE_FILES = ('hansungcat.png', 'ggoggoandgguggu.png', 'sangjji.png')
# 장애물마다 키를 정하는 표다. 상찌는 120의 1/3인 40픽셀로 작게 보여 준다.
OBSTACLE_HEIGHTS = {name: (CHARACTER_HEIGHT // 3 if name == 'sangjji.png'
                           else CHARACTER_HEIGHT) for name in OBSTACLE_FILES}


def load_image(filename, *, size=None, height=None):
    """공통 이미지 로딩과 비율 유지 크기 조절."""
    # 구조 개선: 실행 디렉터리에 관계없이 이 파일 옆의 이미지를 찾는다.
    image = pygame.image.load(str(IMAGE_DIR / filename)).convert_alpha()
    if height is not None:
        size = (int(image.get_width() * height / image.get_height()), height)
    return pygame.transform.smoothscale(image, size) if size else image


def load_run_frames(reference):
    """2×2 모션 시트를 분리하고 상체는 고정한 채 다리만 교체한다."""
    sheet = load_image('sangsangbugi_side_motion.png')
    size = reference.get_size()
    target_bounds = reference.get_bounding_rect(min_alpha=20)
    poses = []
    for row in range(2):
        for column in range(2):
            # 홀수 폭도 마지막 열까지 포함하고 투명 여백을 제거한다.
            left = column * sheet.get_width() // 2
            right = (column + 1) * sheet.get_width() // 2
            top = row * sheet.get_height() // 2
            bottom = (row + 1) * sheet.get_height() // 2
            cell = sheet.subsurface((left, top, right - left, bottom - top))
            bounds = cell.get_bounding_rect(min_alpha=20)
            # 기존 캐릭터의 실제 표시 영역에 맞춰 크기·여백·지면 위치를 유지한다.
            pose = pygame.Surface(size, pygame.SRCALPHA)
            pose.blit(pygame.transform.smoothscale(
                cell.subsurface(bounds), target_bounds.size), target_bounds)
            poses.append(pose)
    leg_top = int(size[1] * LEG_START_RATIO)
    frames = []
    for pose in poses:
        frame = poses[0].copy()
        # 투명 영역까지 지워 이전 포즈의 다리가 겹쳐 남지 않도록 한다.
        frame.fill((0, 0, 0, 0), (0, leg_top, size[0], size[1] - leg_top))
        frame.blit(pose, (0, leg_top), (0, leg_top, size[0], size[1] - leg_top))
        frames.append(frame)
    return frames


class HansungRun:
    """자원과 상태를 소유하고 입력, 갱신, 그리기를 분리한다."""

    def __init__(self, high_score_path=HIGH_SCORE_PATH):
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption('Hansungrun')
        self.clock = pygame.time.Clock()
        # 스크롤 배경: 긴 이미지의 비율을 유지하고 같은 표면을 이어 그린다.
        # 배경만 불투명하게 변환해 이전 프레임과의 혼합·잔상을 방지한다.
        self.stage = load_image('hansung_morning.png', height=SCREEN_SIZE[1]).convert()
        self.background_width = self.stage.get_width()
        self.player_image = load_image('sangsangbugi_side.png', height=CHARACTER_HEIGHT)
        self.run_frames = load_run_frames(self.player_image)
        # 자원을 한 번만 로딩하고 재등장 시 선택과 위치 초기화만 한다.
        self.obstacle_images = {
            name: load_image(name, height=OBSTACLE_HEIGHTS[name]) for name in OBSTACLE_FILES
        }
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
        # 최고점수는 한 판의 상태와 분리하여 재시작과 프로그램 종료 후에도 보존한다.
        self.high_score_path = Path(high_score_path)
        self.high_score = self.load_high_score()
        self.reset()

    def load_high_score(self):
        try:
            value = int(self.high_score_path.read_text(encoding='utf-8').strip())
        except FileNotFoundError:
            return 0  # 최초 실행에는 저장 파일이 없다.
        if value < 0:
            raise ValueError('최고점수는 음수일 수 없습니다.')
        return value

    def record_high_score(self):
        if self.score > self.high_score:
            # 저장 완료 후 교체하여 쓰기 도중 기존 기록이 잘리는 것을 방지한다.
            temporary_path = self.high_score_path.with_suffix('.tmp')
            temporary_path.write_text(str(self.score), encoding='utf-8')
            temporary_path.replace(self.high_score_path)
            self.high_score = self.score

    def reset(self):
        # 구조 개선: 시작과 재시작의 초기화를 공유해 상태 누락을 방지한다.
        self.player_y = self.ground_y
        self.velocity_y = 0
        self.is_jumping = False
        self.spawn_obstacle()
        self.animation_tick = 0
        self.background_x = 0
        self.score = 0
        self.passed = False
        self.game_over = False

    def spawn_obstacle(self):
        """세 종류 중 균등 무작위 선택. 같은 종류가 연속 등장할 수도 있다."""
        self.obstacle_name = random.choice(OBSTACLE_FILES)
        self.obstacle_image = self.obstacle_images[self.obstacle_name]
        # 작은 상찌도 공중에 뜨지 않게 그림의 아래쪽을 같은 바닥에 맞춘다.
        self.obstacle_y = SCREEN_SIZE[1] - self.obstacle_image.get_height() + OBSTACLE_GROUND_OFFSET
        # 그림이 작아지면 부딪힘 검사 상자도 함께 작아져야 한다.
        # 큰 그림의 보정값을 그대로 빼면 작은 상자의 폭이 음수가 될 수 있다.
        scale = self.obstacle_image.get_height() / CHARACTER_HEIGHT
        self.obstacle_hitbox_shrink = tuple(int(value * scale) for value in OBSTACLE_HITBOX_SHRINK)
        self.obstacle_x = SCREEN_SIZE[0]
        self.passed = False

    def stop(self):
        # 진행 중 종료해도 해당 판의 기록을 반영한다.
        self.record_high_score()
        self.running = False

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.stop()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.stop()
                elif self.game_over and event.key == pygame.K_RETURN:
                    self.reset()
                elif not self.game_over and event.key == pygame.K_SPACE:
                    if not self.is_jumping:
                        self.velocity_y = JUMP_SPEED
                        self.is_jumping = True

    def update(self):
        if self.game_over:
            return
        # 장애물과 같은 속도로 이동하며 반복 경계를 넘은 이동량도 보존한다.
        # 게임오버 시 위에서 반환하므로 배경도 정지한다.
        self.background_x = -(
            (-self.background_x + BACKGROUND_SPEED) % self.background_width
        )
        if not self.is_jumping:
            self.animation_tick = (self.animation_tick + 1) % (len(self.run_frames) * RUN_FRAME_TICKS)
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
        obstacle_hitbox = obstacle_rect.inflate(*self.obstacle_hitbox_shrink)
        if player_hitbox.colliderect(obstacle_hitbox):
            self.game_over = True
            # 통과마다 저장하지 않고 한 판이 끝난 시점에만 최고점수를 반영한다.
            self.record_high_score()
            return
        if player_rect.left >= obstacle_rect.right and not self.passed:
            self.score += PASS_BONUS
            self.passed = True
        if self.obstacle_x + self.obstacle_image.get_width() < 0:
            self.spawn_obstacle()

    def draw(self):
        # 배경 → 장애물 → 플레이어 → 점수 → 안내 순으로 겹쳐 그린다.
        self.screen.blit(self.stage, (self.background_x, 0))
        self.screen.blit(self.stage, (self.background_x + self.background_width, 0))
        self.screen.blit(self.obstacle_image, (self.obstacle_x, self.obstacle_y))
        frame_index = 0 if self.is_jumping else self.animation_tick // RUN_FRAME_TICKS
        self.screen.blit(self.run_frames[frame_index], (0, self.player_y))
        # 우측 상단: 현재 점수를 오른쪽에 고정하고 최고점수를 그 왼쪽에 배치한다.
        score_text = self.score_font.render(f'SCORE {self.score}', True, (0, 0, 0))
        score_rect = score_text.get_rect(topright=(SCREEN_SIZE[0] - HUD_MARGIN, HUD_MARGIN))
        best_text = self.score_font.render(f'BEST {self.high_score}', True, (0, 0, 0))
        best_rect = best_text.get_rect(topright=(score_rect.left - HUD_GAP, HUD_MARGIN))
        self.screen.blit(best_text, best_rect)
        self.screen.blit(score_text, score_rect)
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

