"""백: 좌표·점프·충돌·점수·낮밤 시간을 계산한다. 화면을 그리지 않는다."""
from pathlib import Path
import random
import pygame
if __package__:
    from .config import (
        BACKGROUND_FADE_SECONDS,
        BACKGROUND_SPEED,
        CHARACTER_HEIGHT,
        DAY_NIGHT_INTERVAL,
        GRAVITY,
        HIGH_SCORE_PATH,
        JUMP_SPEED,
        OBSTACLE_FILES,
        OBSTACLE_GROUND_OFFSET,
        OBSTACLE_HITBOX_SHRINK,
        OBSTACLE_SPEED,
        PASS_BONUS,
        PHYSICS_HZ,
        PLAYER_GROUND_OFFSET,
        PLAYER_HITBOX_SHRINK,
        RUN_FRAME_TICKS,
        SCREEN_SIZE
    )
    from .storage import load_high_score, save_high_score
else:
    from config import (
        BACKGROUND_FADE_SECONDS,
        BACKGROUND_SPEED,
        CHARACTER_HEIGHT,
        DAY_NIGHT_INTERVAL,
        GRAVITY,
        HIGH_SCORE_PATH,
        JUMP_SPEED,
        OBSTACLE_FILES,
        OBSTACLE_GROUND_OFFSET,
        OBSTACLE_HITBOX_SHRINK,
        OBSTACLE_SPEED,
        PASS_BONUS,
        PHYSICS_HZ,
        PLAYER_GROUND_OFFSET,
        PLAYER_HITBOX_SHRINK,
        RUN_FRAME_TICKS,
        SCREEN_SIZE
    )
    from storage import load_high_score, save_high_score


class GameState:
    def __init__(self, player_size, obstacle_sizes, frame_count, background_width,
                 high_score_path=HIGH_SCORE_PATH):
        self.player_size = player_size
        self.obstacle_sizes = obstacle_sizes
        self.frame_count = frame_count
        self.background_width = background_width
        self.ground_y = SCREEN_SIZE[1] - CHARACTER_HEIGHT + PLAYER_GROUND_OFFSET
        self.high_score_path = Path(high_score_path)
        self.high_score = load_high_score(self.high_score_path)
        self.running = True
        self.reset()

    def record_high_score(self):
        if self.score > self.high_score:
            save_high_score(self.high_score_path, self.score)
            self.high_score = self.score

    def jump(self):
        if not self.paused and not self.game_over and not self.is_jumping:
            self.velocity_y = JUMP_SPEED
            self.is_jumping = True

    def reset(self):
        # 구조 개선: 시작과 재시작의 초기화를 공유해 상태 누락을 방지한다.
        self.player_y = self.ground_y
        self.velocity_y = 0
        self.is_jumping = False
        self.spawn_obstacle()
        self.animation_tick = 0
        self.background_x = 0
        self.background_elapsed = 0.0
        self.night_alpha = 0
        self.score = 0
        self.passed = False
        self.game_over = False
        self.paused = False


    def spawn_obstacle(self):
        """세 종류 중 균등 무작위 선택. 같은 종류가 연속 등장할 수도 있다."""
        self.obstacle_name = random.choice(OBSTACLE_FILES)
        self.obstacle_size = self.obstacle_sizes[self.obstacle_name]
        # 작은 상찌도 공중에 뜨지 않게 그림의 아래쪽을 같은 바닥에 맞춘다.
        self.obstacle_y = SCREEN_SIZE[1] - self.obstacle_size[1] + OBSTACLE_GROUND_OFFSET
        # 그림이 작아지면 부딪힘 검사 상자도 함께 작아져야 한다.
        # 큰 그림의 보정값을 그대로 빼면 작은 상자의 폭이 음수가 될 수 있다.
        scale = self.obstacle_size[1] / CHARACTER_HEIGHT
        self.obstacle_hitbox_shrink = tuple(int(value * scale) for value in OBSTACLE_HITBOX_SHRINK)
        self.obstacle_x = SCREEN_SIZE[0]
        self.passed = False


    def stop(self):
        # 진행 중 종료해도 해당 판의 기록을 반영한다.
        self.record_high_score()
        self.running = False


    def update(self, dt=1 / PHYSICS_HZ):
        """경과 시간만큼 진행하며 작은 단계로 나눠 충돌 누락을 방지한다."""
        if self.game_over or self.paused:
            return
        # 환경 시계는 실제 플레이 시간을 사용하고, 물리만 긴 지연을 제한한다.
        self.update_background(max(dt, 0.0))
        # 창 이동 등 긴 지연 후에는 최대 0.1초까지만 따라잡는다.
        remaining = min(max(dt, 0.0), 0.1) * PHYSICS_HZ
        while remaining > 1e-9 and not self.game_over:
            step = min(remaining, 1.0)
            self.update_step(step)
            remaining -= step


    def update_background(self, dt):
        """30초마다 낮/밤을 바꾸며 3초 동안 부드럽게 섞는다."""
        self.background_elapsed += dt
        cycle = int((self.background_elapsed + 1e-9) // DAY_NIGHT_INTERVAL)
        elapsed = max(0.0, self.background_elapsed - cycle * DAY_NIGHT_INTERVAL)
        progress = min(elapsed / BACKGROUND_FADE_SECONDS, 1.0)
        # 시작과 끝의 변화 속도를 낮춰 갑자기 밝기가 꺾이지 않게 한다.
        eased = progress * progress * (3 - 2 * progress)
        weight = (eased if cycle % 2 else 1 - eased) if cycle else 0.0
        alpha = round(255 * weight)
        self.night_alpha = alpha

    def update_step(self, step):
        """기존 한 프레임 수치에 시간 비율을 적용한다."""
        # 장애물과 같은 속도로 이동하며 반복 경계를 넘은 이동량도 보존한다.
        # 게임오버 시 위에서 반환하므로 배경도 정지한다.
        self.background_x = -(
            (-self.background_x + BACKGROUND_SPEED * step) % self.background_width
        )
        if not self.is_jumping:
            self.animation_tick = (self.animation_tick + step) % (self.frame_count * RUN_FRAME_TICKS)
        # 분할 간격에 관계없이 같은 포물선이 되도록 기존 중력 적분을 보정한다.
        if self.is_jumping:
            self.player_y += self.velocity_y * step + GRAVITY * step * (step + 1) / 2
            self.velocity_y += GRAVITY * step
            if self.player_y >= self.ground_y:
                self.player_y = self.ground_y
                self.velocity_y = 0
                self.is_jumping = False

        self.obstacle_x -= OBSTACLE_SPEED * step
        player_rect = pygame.Rect((0, 0), self.player_size)
        player_rect.topleft = (0, self.player_y)
        obstacle_rect = pygame.Rect((0, 0), self.obstacle_size)
        obstacle_rect.topleft = (self.obstacle_x, self.obstacle_y)
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
        if self.obstacle_x + self.obstacle_size[0] < 0:
            self.spawn_obstacle()


