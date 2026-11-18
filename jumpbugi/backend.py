"""백: 좌표·점프·충돌·점수·낮밤 시간을 계산한다. 화면을 그리지 않는다."""
from pathlib import Path
import random
import pygame
if __package__:
    from .config import (
        BACKGROUND_FADE_SECONDS,
        BACKGROUND_FILES,
        BACKGROUND_SPEED,
        CHARACTER_HEIGHT,
        DAY_NIGHT_INTERVAL,
        GRAVITY,
        HIGH_SCORE_PATH,
        JUMP_SPEED,
        OBSTACLE_FILES,
        OBSTACLE_GROUND_OFFSET,
        OBSTACLE_SPEED,
        PASS_BONUS,
        PHYSICS_HZ,
        PLAYER_GROUND_OFFSET,
        RUN_FRAME_TICKS,
        SCREEN_SIZE,
        SURVIVAL_POINTS_PER_SECOND,
        SPEED_INCREASE_RATIO,
        CHICKEN_UNLOCK_SECONDS,
        CHICKEN_TYPES,
        CHICKEN_GROUND_OFFSET,
        HSUCAT_TYPES,
        HSUCAT_UNLOCK_SECONDS,
        HSUCAT_PATTERNS,
        SJ_TYPES,
        SJ_CLUSTER_TYPES,
        SJ_UNLOCK_SECONDS,
        SJ_GROUND_OFFSET,
        SJ_BURROW_DISTANCE,
        SJ_PATTERNS,
        FLYING_HEAD_GAP,
        OBSTACLE_FRAME_TICKS,
        OBSTACLE_RECOVERY_SECONDS,
        GROUND_PATTERNS,
        SUMMER_PATTERNS,
    )
    from .storage import load_high_score, save_high_score
else:
    from config import (
        BACKGROUND_FADE_SECONDS,
        BACKGROUND_FILES,
        BACKGROUND_SPEED,
        CHARACTER_HEIGHT,
        DAY_NIGHT_INTERVAL,
        GRAVITY,
        HIGH_SCORE_PATH,
        JUMP_SPEED,
        OBSTACLE_FILES,
        OBSTACLE_GROUND_OFFSET,
        OBSTACLE_SPEED,
        PASS_BONUS,
        PHYSICS_HZ,
        PLAYER_GROUND_OFFSET,
        RUN_FRAME_TICKS,
        SCREEN_SIZE,
        SURVIVAL_POINTS_PER_SECOND,
        SPEED_INCREASE_RATIO,
        CHICKEN_UNLOCK_SECONDS,
        CHICKEN_TYPES,
        CHICKEN_GROUND_OFFSET,
        HSUCAT_TYPES,
        HSUCAT_UNLOCK_SECONDS,
        HSUCAT_PATTERNS,
        SJ_TYPES,
        SJ_CLUSTER_TYPES,
        SJ_UNLOCK_SECONDS,
        SJ_GROUND_OFFSET,
        SJ_BURROW_DISTANCE,
        SJ_PATTERNS,
        FLYING_HEAD_GAP,
        OBSTACLE_FRAME_TICKS,
        OBSTACLE_RECOVERY_SECONDS,
        GROUND_PATTERNS,
        SUMMER_PATTERNS,
    )
    from storage import load_high_score, save_high_score


class GameState:
    def __init__(self, player_size, obstacle_sizes, frame_count, background_width,
                 high_score_path=HIGH_SCORE_PATH, *, player_masks, obstacle_masks,
                 obstacle_frame_masks=None):
        self.player_size = player_size
        self.obstacle_sizes = obstacle_sizes
        self.frame_count = frame_count
        self.player_masks = player_masks
        self.obstacle_masks = obstacle_masks
        self.obstacle_frame_masks = obstacle_frame_masks or {}
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
        self.background_elapsed = 0.0
        self.pattern_queue = []
        self.current_pattern = ()
        self.first_obstacle = True
        self.spawn_obstacle()
        self.animation_tick = 0
        self.background_x = 0
        self.background_from_index = 0
        self.background_to_index = 0
        self.background_alpha = 0
        self.night_alpha = 0
        self.score = 0
        self.survival_elapsed = 0.0
        self.passed = False
        self.game_over = False
        self.paused = False


    def spawn_obstacle(self, name=None):
        """여름에 날갯짓, 가을에 한성캣, 겨울에 새 상찌와 묶음 장애물을 해금한다."""
        if name is not None:
            self.obstacle_name = name
        elif self.first_obstacle:
            self.obstacle_name = random.choice(OBSTACLE_FILES)
        else:
            if not self.chicken_obstacles_enabled:
                self.pattern_queue = [kind for kind in self.pattern_queue if kind not in CHICKEN_TYPES]
            if not self.hsucat_obstacles_enabled:
                self.pattern_queue = [kind for kind in self.pattern_queue if kind not in HSUCAT_TYPES]
            if not self.sj_obstacles_enabled:
                self.pattern_queue = [kind for kind in self.pattern_queue if kind not in SJ_TYPES]
            if not self.pattern_queue:
                pool = GROUND_PATTERNS
                if self.chicken_obstacles_enabled:
                    pool += SUMMER_PATTERNS
                if self.hsucat_obstacles_enabled:
                    pool += HSUCAT_PATTERNS
                if self.sj_obstacles_enabled:
                    pool += SJ_PATTERNS
                pool = [pattern for pattern in pool if all(
                    kind in self.obstacle_sizes and (self.chicken_obstacles_enabled or kind not in CHICKEN_TYPES)
                    and (self.hsucat_obstacles_enabled or kind not in HSUCAT_TYPES)
                    and (self.sj_obstacles_enabled or kind not in SJ_TYPES)
                    for kind in pattern)]
                self.current_pattern = random.choice(pool)
                self.pattern_queue = list(self.current_pattern)
            self.obstacle_name = self.pattern_queue.pop(0)
        # 겨울 이후 기본 상찌 순서도 한 번에 넘는 2·3마리 묶음 중 하나로 바꾼다.
        # 명시적인 이름 지정은 검증용으로 유지한다.
        if name is None and self.sj_obstacles_enabled and self.obstacle_name == 'sj.png':
            clusters = [kind for kind in SJ_CLUSTER_TYPES if kind in self.obstacle_sizes]
            if clusters:
                self.obstacle_name = random.choice(clusters)
        self.obstacle_size = self.obstacle_sizes[self.obstacle_name]
        # 작은 상찌도 공중에 뜨지 않게 그림의 아래쪽을 같은 바닥에 맞춘다.
        self.obstacle_y = SCREEN_SIZE[1] - self.obstacle_size[1] + OBSTACLE_GROUND_OFFSET
        if self.obstacle_is_flying:
            self.obstacle_y = self.ground_y - FLYING_HEAD_GAP - self.obstacle_size[1]
        elif self.obstacle_name in CHICKEN_TYPES:
            self.obstacle_y = SCREEN_SIZE[1] - self.obstacle_size[1] + CHICKEN_GROUND_OFFSET
        elif self.obstacle_name == 'sj.png' or self.obstacle_name in SJ_TYPES:
            self.obstacle_y = SCREEN_SIZE[1] - self.obstacle_size[1] + SJ_GROUND_OFFSET
        # 한 마리가 화면을 완전히 벗어난 뒤 다음 마리를 만든다. 다음 가속도 여유에 포함.
        self.obstacle_spawn_x = (SCREEN_SIZE[0] if self.first_obstacle else max(
            SCREEN_SIZE[0], self.player_size[0] + OBSTACLE_SPEED * PHYSICS_HZ
            * self.speed_multiplier * (1 + SPEED_INCREASE_RATIO) * OBSTACLE_RECOVERY_SECONDS))
        self.obstacle_x = self.obstacle_spawn_x
        self.first_obstacle = False
        self.obstacle_animation_tick = 0.0
        self.passed = False

    @property
    def chicken_obstacles_enabled(self):
        return self.background_elapsed + 1e-9 >= CHICKEN_UNLOCK_SECONDS

    @property
    def hsucat_obstacles_enabled(self):
        return self.background_elapsed + 1e-9 >= HSUCAT_UNLOCK_SECONDS

    @property
    def sj_obstacles_enabled(self):
        return self.background_elapsed + 1e-9 >= SJ_UNLOCK_SECONDS

    @property
    def obstacle_is_flying(self):
        return self.obstacle_name.endswith('_flying')

    @property
    def obstacle_frame_index(self):
        frames = self.obstacle_frame_masks.get(self.obstacle_name)
        if frames and self.obstacle_name == 'sj_burrow':
            progress = min(1.0, max(0.0, (SCREEN_SIZE[0] - self.obstacle_x) / SJ_BURROW_DISTANCE))
            return int(progress * (len(frames) - 1))
        return int(self.obstacle_animation_tick // OBSTACLE_FRAME_TICKS) % len(frames) if frames else 0


    def stop(self):
        # 진행 중 종료해도 해당 판의 기록을 반영한다.
        self.record_high_score()
        self.running = False

    @property
    def player_frame_index(self):
        """점프 중에는 화면과 충돌 모두 달리기 첫 프레임을 사용한다."""
        return 0 if self.is_jumping else int(self.animation_tick // RUN_FRAME_TICKS)

    def collides_with_obstacle(self):
        """화면에 그리는 정수 좌표와 동일한 위치에서 불투명 픽셀을 비교한다."""
        offset = (int(self.obstacle_x), int(self.obstacle_y) - int(self.player_y))
        frames = self.obstacle_frame_masks.get(self.obstacle_name)
        mask = frames[self.obstacle_frame_index] if frames else self.obstacle_masks[self.obstacle_name]
        return self.player_masks[self.player_frame_index].overlap(
            mask, offset
        ) is not None

    @property
    def speed_multiplier(self):
        """배경 전환이 시작될 때 설정 비율만큼 속도를 누적한다."""
        stage = int((self.background_elapsed + 1e-9) // DAY_NIGHT_INTERVAL)
        return (1 + SPEED_INCREASE_RATIO) ** stage


    def update(self, dt=1 / PHYSICS_HZ):
        """경과 시간만큼 진행하며 작은 단계로 나눠 충돌 누락을 방지한다."""
        if self.game_over or self.paused:
            return
        dt = max(dt, 0.0)
        previous_seconds = int(self.survival_elapsed + 1e-9)
        self.survival_elapsed += dt
        self.score += (int(self.survival_elapsed + 1e-9) - previous_seconds) * SURVIVAL_POINTS_PER_SECOND
        # 환경 시계는 실제 플레이 시간을 사용하고, 물리만 긴 지연을 제한한다.
        self.update_background(dt)
        # 창 이동 등 긴 지연 후에는 최대 0.1초까지만 따라잡는다.
        remaining = min(dt, 0.1) * PHYSICS_HZ
        while remaining > 1e-9 and not self.game_over:
            # 가속 후에도 한 번의 검사 사이 이동은 기본 장애물 속도 이하로 나눈다.
            step = min(remaining, 1.0 / self.speed_multiplier)
            self.update_step(step)
            remaining -= step


    def update_background(self, dt):
        """계절별 낮·밤 8장을 30초마다 순환하고 4초 동안 섞는다."""
        self.background_elapsed += dt
        cycle = int((self.background_elapsed + 1e-9) // DAY_NIGHT_INTERVAL)
        elapsed = max(0.0, self.background_elapsed - cycle * DAY_NIGHT_INTERVAL)
        progress = min(elapsed / BACKGROUND_FADE_SECONDS, 1.0)
        # 시작과 끝의 변화 속도를 낮춰 갑자기 밝기가 꺾이지 않게 한다.
        eased = progress * progress * (3 - 2 * progress)
        self.background_to_index = cycle % len(BACKGROUND_FILES)
        self.background_from_index = (cycle - 1) % len(BACKGROUND_FILES) if cycle else 0
        self.background_alpha = round(255 * eased) if cycle else 0
        # HUD 색은 전환하는 두 그림의 낮/밤 밝기에 맞춰 보간한다.
        source_night = self.background_from_index % 2
        target_night = self.background_to_index % 2
        self.night_alpha = round(255 * (source_night * (1 - eased) + target_night * eased))

    def scroll_background(self, dt):
        """계절·점수·장애물을 진행하지 않고 배경의 스크롤 위치만 옮긴다."""
        step = max(0.0, dt) * PHYSICS_HZ
        # 인트로와 플레이가 같은 속도와 순환 좌표를 공유한다.
        self.background_x = -(
            (-self.background_x + BACKGROUND_SPEED * self.speed_multiplier * step) % self.background_width
        )

    def update_step(self, step):
        """기존 한 프레임 수치에 시간 비율을 적용한다."""
        self.scroll_background(step / PHYSICS_HZ)
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

        self.obstacle_x -= OBSTACLE_SPEED * self.speed_multiplier * step
        self.obstacle_animation_tick += step
        player_rect = pygame.Rect((0, 0), self.player_size)
        player_rect.topleft = (0, int(self.player_y))
        obstacle_rect = pygame.Rect((0, 0), self.obstacle_size)
        obstacle_rect.topleft = (int(self.obstacle_x), int(self.obstacle_y))
        if player_rect.colliderect(obstacle_rect) and self.collides_with_obstacle():
            self.game_over = True
            # 통과마다 저장하지 않고 한 판이 끝난 시점에만 최고점수를 반영한다.
            self.record_high_score()
            return
        if player_rect.left >= obstacle_rect.right and not self.passed:
            self.score += PASS_BONUS
            self.passed = True
        if self.obstacle_x + self.obstacle_size[0] < 0:
            self.spawn_obstacle()


