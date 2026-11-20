"""게임 상태와 갱신 순서. 기능별 계산을 연결하고 화면은 그리지 않는다."""
from __future__ import annotations
from pathlib import Path
import random
import math
import pygame
if __package__:
    from . import obstacles, patterns as pattern_rules
    from .obstacles import GreetingJump, SjMember
    from .season import SeasonProgress, background_transition
    from .config import (
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
        CHICKEN_UNLOCK_SLOT,
        CHICKEN_TYPES,
        CHICKEN_GROUND_OFFSET,
        HSUCAT_RUN_MODES,
        HSUCAT_RUN_GROUND_OFFSET,
        HSUCAT_RUN_JUMP_HEIGHTS,
        HSUCAT_UNLOCK_SLOT,
        SJ_TYPES,
        SJ_CLUSTER_TYPES,
        SJ_CLUSTER_GAP,
        SJ_GROUP_UNLOCK_SLOT,
        SJ_JUMP_UNLOCK_SLOT,
        SJ_SINGLE_JUMP_TYPES,
        SJ_HOP_TRIGGER_JITTER,
        WAVE_IMAGE_FILES,
        WAVE_GROUND_OFFSET,
        WAVE_JUMP_UNLOCK_SLOT,
        WAVE_JUMP_PROBABILITY,
        WAVE_JUMP_HEIGHTS,
        SJ_UNLOCK_SLOT,
        SJ_GROUND_OFFSET,
        SJ_HOLE_TYPES,
        SJ_BURROW_PROFILES,
        SJ_ESCAPE_PROFILES,
        SJ_ESCAPE_UNLOCK_SLOT,
        SJ_HOLE_CLEARANCE,
        FLYING_LEVELS,
        FLYING_HEAD_GAPS,
    )
    from .storage import load_high_score, save_high_score
    from .difficulty import profile_for_slot, speed_multiplier_for_slot
else:
    import obstacles
    import patterns as pattern_rules
    from obstacles import GreetingJump, SjMember
    from season import SeasonProgress, background_transition
    from config import (
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
        CHICKEN_UNLOCK_SLOT,
        CHICKEN_TYPES,
        CHICKEN_GROUND_OFFSET,
        HSUCAT_RUN_MODES,
        HSUCAT_RUN_GROUND_OFFSET,
        HSUCAT_RUN_JUMP_HEIGHTS,
        HSUCAT_UNLOCK_SLOT,
        SJ_TYPES,
        SJ_CLUSTER_TYPES,
        SJ_CLUSTER_GAP,
        SJ_GROUP_UNLOCK_SLOT,
        SJ_JUMP_UNLOCK_SLOT,
        SJ_SINGLE_JUMP_TYPES,
        SJ_HOP_TRIGGER_JITTER,
        WAVE_IMAGE_FILES,
        WAVE_GROUND_OFFSET,
        WAVE_JUMP_UNLOCK_SLOT,
        WAVE_JUMP_PROBABILITY,
        WAVE_JUMP_HEIGHTS,
        SJ_UNLOCK_SLOT,
        SJ_GROUND_OFFSET,
        SJ_HOLE_TYPES,
        SJ_BURROW_PROFILES,
        SJ_ESCAPE_PROFILES,
        SJ_ESCAPE_UNLOCK_SLOT,
        SJ_HOLE_CLEARANCE,
        FLYING_LEVELS,
        FLYING_HEAD_GAPS,
    )
    from storage import load_high_score, save_high_score
    from difficulty import profile_for_slot, speed_multiplier_for_slot



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


    @property
    def available_patterns(self):
        return pattern_rules.available_patterns(self.obstacle_sizes, self.pattern_unlocks)

    @property
    def pattern_unlocks(self):
        return pattern_rules.PatternUnlocks(
            chicken=self.chicken_obstacles_enabled,
            hsucat=self.hsucat_obstacles_enabled,
            sj=self.sj_obstacles_enabled,
            sj_groups=self.sj_groups_enabled,
            sj_escape=self.sj_escape_enabled)

    def spawn_obstacle(self, name=None):
        """계절별 추가 유형을 해금하고 둘째 봄부터 상찌 무리와 점프를 선택한다."""
        if name is not None:
            self.obstacle_name = name
        elif self.first_obstacle:
            self.obstacle_name = random.choice(OBSTACLE_FILES)
        else:
            self.pattern_queue = pattern_rules.unlocked_queue(self.pattern_queue, self.pattern_unlocks)
            if not self.pattern_queue:
                self.current_pattern = pattern_rules.choose_pattern(self.available_patterns, self.difficulty)
                self.pattern_queue = list(self.current_pattern)
            self.obstacle_name = self.pattern_queue.pop(0)
        # 둘째 봄부터 기본 상찌 순서도 2·3마리 묶음 중 하나로 바꾼다.
        # 명시적인 이름 지정은 검증용으로 유지한다.
        if name is None and self.sj_groups_enabled and self.obstacle_name == 'sj.png':
            clusters = [kind for kind in SJ_CLUSTER_TYPES if kind in self.obstacle_sizes]
            if clusters:
                self.obstacle_name = random.choice(clusters)
        self.obstacle_size = self.obstacle_sizes[self.obstacle_name]
        self.chicken_flight_level = None
        # 작은 상찌도 공중에 뜨지 않게 그림의 아래쪽을 같은 바닥에 맞춘다.
        self.obstacle_y = SCREEN_SIZE[1] - self.obstacle_size[1] + OBSTACLE_GROUND_OFFSET
        if self.obstacle_is_flying:
            self.chicken_flight_level = FLYING_LEVELS[min(int(random.random() * len(FLYING_LEVELS)),
                                                        len(FLYING_LEVELS) - 1)]
            self.obstacle_y = (self.ground_y - FLYING_HEAD_GAPS[self.chicken_flight_level]
                               - self.obstacle_size[1])
        elif self.obstacle_name == 'hsucat_run.png':
            self.obstacle_y = SCREEN_SIZE[1] - self.obstacle_size[1] + HSUCAT_RUN_GROUND_OFFSET
        elif self.obstacle_name in WAVE_IMAGE_FILES:
            self.obstacle_y = SCREEN_SIZE[1] - self.obstacle_size[1] + WAVE_GROUND_OFFSET
        elif self.obstacle_name in CHICKEN_TYPES:
            self.obstacle_y = SCREEN_SIZE[1] - self.obstacle_size[1] + CHICKEN_GROUND_OFFSET
        elif self.obstacle_name == 'sj.png' or self.obstacle_name in SJ_TYPES:
            self.obstacle_y = SCREEN_SIZE[1] - self.obstacle_size[1] + SJ_GROUND_OFFSET
        # 직전 장애물이 사라진 뒤 전체 점프와 재입력 시간을 확보한다.
        # 짧은 테스트 슬롯에서 여러 번 가속하더라도 다음 접촉까지 이 시간을 보장한다.
        recovery = self.obstacle_recovery_seconds
        future_slot = self.total_slots_passed + math.ceil(recovery / DAY_NIGHT_INTERVAL)
        approach_speed = OBSTACLE_SPEED * PHYSICS_HZ * speed_multiplier_for_slot(future_slot)
        self.obstacle_spawn_x = (SCREEN_SIZE[0] if self.first_obstacle else max(
            SCREEN_SIZE[0], self.player_size[0] + approach_speed * recovery))
        self.obstacle_x = self.obstacle_spawn_x
        self.obstacle_ground_y = self.obstacle_y
        self.first_obstacle = False
        self.obstacle_animation_tick = 0.0
        self.sj_hole_timing = None
        self.sj_hole_start_x = float(SCREEN_SIZE[0])
        self.sj_hole_end_x = self.sj_hole_start_x
        if self.obstacle_name in SJ_HOLE_TYPES:
            profiles = SJ_BURROW_PROFILES if self.obstacle_name == 'sj_burrow' else SJ_ESCAPE_PROFILES
            timings = tuple(profiles)
            self.sj_hole_timing = timings[min(int(random.random() * len(timings)), len(timings) - 1)]
            self.sj_hole_start_x, end_x = profiles[self.sj_hole_timing]
            self.sj_hole_end_x = max(end_x, self.player_size[0] + SJ_HOLE_CLEARANCE)
        self.sj_members = []
        self.wave_jump = None
        self.hsucat_run_mode = 'run'
        if self.obstacle_name == 'hsucat_run.png':
            modes = HSUCAT_RUN_MODES if self.greeting_jumps_enabled else tuple(
                mode for mode in HSUCAT_RUN_MODES if mode not in HSUCAT_RUN_JUMP_HEIGHTS)
            self.hsucat_run_mode = modes[min(int(random.random() * len(modes)), len(modes) - 1)]
            if self.hsucat_run_mode in HSUCAT_RUN_JUMP_HEIGHTS:
                self.wave_jump = self.build_hsucat_run_jump(self.hsucat_run_mode)
        if (self.obstacle_name in WAVE_IMAGE_FILES and self.greeting_jumps_enabled
                and random.random() < WAVE_JUMP_PROBABILITY):
            patterns = tuple(WAVE_JUMP_HEIGHTS)
            pattern = patterns[min(int(random.random() * len(patterns)), len(patterns) - 1)]
            self.wave_jump = obstacles.build_greeting_jump(
                pattern, obstacle_y=self.obstacle_y, obstacle_size=self.obstacle_size,
                player_size=self.player_size, ground_y=self.ground_y,
                speed_multiplier=self.speed_multiplier)
        if self.obstacle_name in SJ_CLUSTER_TYPES:
            count = 2 if self.obstacle_name == 'sj_pair' else 3
            single_width = self.obstacle_sizes['sj.png'][0]
            for index in range(count):
                offset = index * (single_width + SJ_CLUSTER_GAP)
                pattern = self.choose_sj_jump_pattern() if self.sj_jumps_enabled else None
                jitter = random.uniform(0, SJ_HOP_TRIGGER_JITTER)
                plan = self.build_sj_jump(pattern, single_width, offset, index, jitter) if pattern else None
                self.sj_members.append(SjMember(offset, pattern, plan))
        elif self.obstacle_name in SJ_SINGLE_JUMP_TYPES and self.sj_jumps_enabled:
            pattern = self.choose_sj_jump_pattern()
            if pattern:
                self.wave_jump = self.build_sj_jump(pattern, self.obstacle_size[0])
        self.passed = False

    def build_hsucat_run_jump(self, pattern):
        return obstacles.build_hsucat_run_jump(
            pattern, obstacle_ground_y=self.obstacle_ground_y,
            obstacle_size=self.obstacle_size, player_size=self.player_size,
            ground_y=self.ground_y, speed_multiplier=self.speed_multiplier)

    def choose_sj_jump_pattern(self):
        return obstacles.choose_sj_jump_pattern()

    def build_sj_jump(self, pattern, width, offset=0, index=None, jitter=0):
        return obstacles.build_sj_jump(
            pattern, width, offset, index, jitter, player_size=self.player_size,
            obstacle_size=self.obstacle_size, obstacle_ground_y=self.obstacle_ground_y,
            ground_y=self.ground_y, speed_multiplier=self.speed_multiplier)

    @property
    def sj_cluster_parts(self):
        """그리기와 충돌이 공유하는 각 상찌의 포즈와 정수 화면 좌표."""
        if self.obstacle_name not in SJ_CLUSTER_TYPES or not self.sj_members:
            return ()
        frame_count = len(self.obstacle_frame_masks.get('sj.png', ())) or 1
        return obstacles.cluster_parts(
            self.sj_members, x=self.obstacle_x, ground_y=self.obstacle_y,
            frame_count=frame_count, animation_tick=self.obstacle_animation_tick)

    @property
    def greeting_jumps_enabled(self):
        return self.total_slots_passed >= WAVE_JUMP_UNLOCK_SLOT

    @property
    def wave_jump_active(self):
        return self.wave_jump is not None and self.wave_jump.is_jumping(self.obstacle_x)

    @property
    def obstacle_requires_jump(self):
        """현재 동작과 비행 높이에 맞는 검증용 회피 입력을 판단한다."""
        if self.obstacle_name == 'sj_burrow':
            return False
        if self.obstacle_name in SJ_CLUSTER_TYPES and self.sj_members:
            return any(member.pattern != 'high' for member in self.sj_members)
        if self.obstacle_is_flying:
            return self.chicken_flight_level == 'low'
        return not self.obstacle_is_flying and (self.wave_jump is None or self.wave_jump.pattern == 'low')

    @property
    def chicken_obstacles_enabled(self):
        return self.total_slots_passed >= CHICKEN_UNLOCK_SLOT

    @property
    def hsucat_obstacles_enabled(self):
        return self.total_slots_passed >= HSUCAT_UNLOCK_SLOT

    @property
    def sj_obstacles_enabled(self):
        return self.total_slots_passed >= SJ_UNLOCK_SLOT

    @property
    def sj_groups_enabled(self):
        return self.total_slots_passed >= SJ_GROUP_UNLOCK_SLOT

    @property
    def sj_jumps_enabled(self):
        return self.total_slots_passed >= SJ_JUMP_UNLOCK_SLOT

    @property
    def sj_escape_enabled(self):
        return self.total_slots_passed >= SJ_ESCAPE_UNLOCK_SLOT

    @property
    def sj_hole_progress(self):
        if self.sj_hole_timing is None:
            return 0.0
        return min(1.0, max(0.0, (self.sj_hole_start_x - self.obstacle_x)
                           / (self.sj_hole_start_x - self.sj_hole_end_x)))

    @property
    def obstacle_is_flying(self):
        return self.obstacle_name.endswith('_flying')

    @property
    def obstacle_frame_index(self):
        frames = self.obstacle_frame_masks.get(self.obstacle_name)
        return obstacles.frame_index(
            self.obstacle_name, len(frames) if frames else 0,
            x=self.obstacle_x, animation_tick=self.obstacle_animation_tick,
            jumping=self.wave_jump_active, run_mode=self.hsucat_run_mode,
            hole_progress=self.sj_hole_progress)


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
        parts = self.sj_cluster_parts
        if parts:
            masks = self.obstacle_frame_masks.get('sj.png') or [self.obstacle_masks['sj.png']]
            return any(self.player_masks[self.player_frame_index].overlap(
                masks[frame], (x, y - int(self.player_y))) is not None
                for frame, x, y in parts)
        offset = (int(self.obstacle_x), int(self.obstacle_y) - int(self.player_y))
        frames = self.obstacle_frame_masks.get(self.obstacle_name)
        mask = frames[self.obstacle_frame_index] if frames else self.obstacle_masks[self.obstacle_name]
        return self.player_masks[self.player_frame_index].overlap(
            mask, offset
        ) is not None

    @property
    def season_progress(self):
        return SeasonProgress.from_elapsed(self.background_elapsed, DAY_NIGHT_INTERVAL)

    @property
    def total_slots_passed(self):
        return self.season_progress.total_slots_passed

    @property
    def current_slot(self):
        return self.season_progress.current_slot

    @property
    def season_cycle_count(self):
        return self.season_progress.season_cycle_count

    @property
    def difficulty(self):
        return profile_for_slot(self.total_slots_passed)

    @property
    def speed_multiplier(self):
        return self.difficulty.speed_multiplier

    @property
    def obstacle_recovery_seconds(self):
        return self.difficulty.recovery_seconds


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
        """같은 계절 시계의 전환값을 게임 상태에 반영한다."""
        self.background_elapsed += dt
        transition = background_transition(self.background_elapsed, DAY_NIGHT_INTERVAL)
        self.background_from_index = transition.from_index
        self.background_to_index = transition.to_index
        self.background_alpha = transition.alpha
        self.night_alpha = transition.night_alpha

    def scroll_background(self, dt):
        """계절·점수·장애물을 진행하지 않고 배경의 스크롤 위치만 옮긴다."""
        step = max(0.0, dt) * PHYSICS_HZ
        # 인트로와 플레이가 같은 속도와 순환 좌표를 공유한다.
        self.background_x = -(
            (-self.background_x + BACKGROUND_SPEED * self.speed_multiplier * step) % self.background_width
        )

    def award_pass_bonuses(self, player_left=0):
        """높이·점프 입력·동작과 무관하게 수평 통과한 장애물마다 한 번 보상한다.

        비행형·높은 점프 아래 통과도 같은 규칙이며, 상찌 무리는 마리별로 기록한다.
        """
        if self.obstacle_name in SJ_CLUSTER_TYPES and self.sj_members:
            width = self.obstacle_sizes['sj.png'][0]
            for member in self.sj_members:
                if not member.passed and int(self.obstacle_x + member.offset_x) + width <= player_left:
                    self.score += PASS_BONUS
                    member.passed = True
            self.passed = all(member.passed for member in self.sj_members)
        elif not self.passed and int(self.obstacle_x) + self.obstacle_size[0] <= player_left:
            self.score += PASS_BONUS
            self.passed = True

    @property
    def obstacle_pass_bonus(self):
        """현재 장애물 전체를 통과했을 때의 총 보너스."""
        count = len(self.sj_members) if self.obstacle_name in SJ_CLUSTER_TYPES else 1
        return PASS_BONUS * max(1, count)

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
        if self.wave_jump is not None:
            self.obstacle_y = self.obstacle_ground_y + self.wave_jump.y_offset(self.obstacle_x)
        self.obstacle_animation_tick += step
        player_rect = pygame.Rect((0, 0), self.player_size)
        player_rect.topleft = (0, int(self.player_y))
        obstacle_rect = pygame.Rect((0, 0), self.obstacle_size)
        obstacle_rect.topleft = (int(self.obstacle_x), int(self.obstacle_y))
        # 모든 동작에 공통 적용하며 앞 상찌를 통과한 점수는 뒤 상찌와 충돌해도 보존한다.
        self.award_pass_bonuses(player_rect.left)
        parts = self.sj_cluster_parts
        candidate = (any(player_rect.colliderect(pygame.Rect((x, y), self.obstacle_sizes['sj.png']))
                         for _, x, y in parts) if parts else player_rect.colliderect(obstacle_rect))
        if candidate and self.collides_with_obstacle():
            self.game_over = True
            # 통과마다 저장하지 않고 한 판이 끝난 시점에만 최고점수를 반영한다.
            self.record_high_score()
            return
        if self.obstacle_x + self.obstacle_size[0] < 0:
            self.spawn_obstacle()


