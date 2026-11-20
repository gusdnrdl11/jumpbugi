"""장애물의 거리 기반 점프 계획과 표시·충돌에 공통으로 쓰는 포즈 계산."""
from __future__ import annotations

from dataclasses import dataclass
import random

if __package__:
    from . import config
else:
    import config


@dataclass
class SjMember:
    offset_x: int
    pattern: str | None
    jump_plan: GreetingJump | None
    passed: bool = False

    @property
    def hop_enabled(self):
        return self.jump_plan is not None

    @property
    def trigger_x(self):
        return (self.jump_plan.center_x + self.jump_plan.half_distance
                if self.jump_plan is not None else None)

    def is_jumping(self, group_x):
        return self.jump_plan is not None and self.jump_plan.is_jumping(group_x)

    def y_offset(self, group_x):
        return self.jump_plan.y_offset(group_x) if self.jump_plan is not None else 0.0


@dataclass
class GreetingJump:
    pattern: str
    height: float
    center_x: float
    half_distance: float

    def progress(self, x):
        return (self.center_x + self.half_distance - x) / (2 * self.half_distance)

    def is_jumping(self, x):
        return 0.0 < self.progress(x) < 1.0

    def y_offset(self, x):
        progress = self.progress(x)
        return -4 * self.height * progress * (1 - progress) if 0 < progress < 1 else 0.0


def build_hsucat_run_jump(pattern, *, obstacle_ground_y, obstacle_size,
                          player_size, ground_y, speed_multiplier):
    """달리는 캣의 높은·낮은 점프 계획을 생성 시 한 번 계산한다."""
    height = config.HSUCAT_RUN_JUMP_HEIGHTS[pattern]
    factor = config.HSUCAT_RUN_JUMP_CONTACT_FACTOR
    if pattern == 'high':
        required_lift = (obstacle_ground_y + obstacle_size[1]
                         - ground_y + config.HSUCAT_RUN_JUMP_CLEARANCE)
        height = max(height, required_lift + 1)
        factor = max(factor, (1 - required_lift / height) ** -0.5)
    contact_half = (player_size[0] + obstacle_size[0]) / 2
    speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * speed_multiplier
    return GreetingJump(pattern, height, (player_size[0] - obstacle_size[0]) / 2,
                        max(factor * contact_half, config.HSUCAT_RUN_JUMP_MIN_SECONDS * speed / 2))


def choose_sj_jump_pattern():
    """지상 유지·낮은 점프·높은 점프를 기존 확률로 한 번 선택한다."""
    roll = random.random()
    return ('high' if roll < config.SJ_HOP_PROBABILITY / 2 else
            'low' if roll < config.SJ_HOP_PROBABILITY else None)


def build_sj_jump(pattern, width, offset=0, index=None, jitter=0, *,
                  player_size, obstacle_size, obstacle_ground_y, ground_y,
                  speed_multiplier):
    """개별 상찌와 무리 멤버의 출발 위치·높이를 같은 거리 궤적으로 만든다."""
    center = (player_size[0] - width) / 2 - offset
    contact_half = (player_size[0] + width) / 2
    speed = config.OBSTACLE_SPEED * config.PHYSICS_HZ * speed_multiplier
    height = config.SJ_JUMP_HEIGHTS[pattern]
    if pattern == 'high':
        player_rise = min(0, config.JUMP_SPEED + config.GRAVITY / 2) ** 2 / (2 * config.GRAVITY)
        required_lift = (obstacle_ground_y + obstacle_size[1]
                         - (ground_y - player_rise) + config.SJ_HIGH_PLAYER_CLEARANCE)
        height = max(height, required_lift + 1)
        factor = max(config.SJ_HIGH_CONTACT_FACTOR, (1 - required_lift / height) ** -0.5)
        half_distance = max(factor * contact_half, config.SJ_HIGH_MIN_SECONDS * speed / 2)
        if index is not None:
            half_distance += index * (config.SJ_HOP_TRIGGER_SPACING + width + config.SJ_CLUSTER_GAP) + jitter
    elif index is not None:
        half_distance = max(contact_half + 1,
                            config.SJ_HOP_TRIGGER_X - index * config.SJ_HOP_TRIGGER_SPACING - jitter - center)
    else:
        half_distance = max(config.SJ_LOW_CONTACT_FACTOR * contact_half,
                            config.SJ_LOW_MIN_SECONDS * speed / 2)
    return GreetingJump(pattern, height, center, half_distance)


def build_greeting_jump(pattern, *, obstacle_y, obstacle_size, player_size,
                        ground_y, speed_multiplier):
    """기본 인사 캐릭터의 세 점프에서 몸 크기와 머리 위 여유를 반영한다."""
    height = config.WAVE_JUMP_HEIGHTS[pattern]
    factor = config.WAVE_JUMP_CONTACT_FACTORS[pattern]
    if pattern != 'low':
        required_lift = (obstacle_y + obstacle_size[1] - ground_y
                         + config.WAVE_UNDERPASS_CLEARANCE)
        height = max(height, required_lift + 1)
        factor = max(factor, (1 - required_lift / height) ** -0.5)
    contact_half = (player_size[0] + obstacle_size[0]) / 2
    half_distance = max(factor * contact_half, config.WAVE_JUMP_MIN_SECONDS
                        * config.OBSTACLE_SPEED * config.PHYSICS_HZ * speed_multiplier / 2)
    return GreetingJump(pattern, height, (player_size[0] - obstacle_size[0]) / 2,
                        half_distance)


def frame_index(name, frame_count, *, x, animation_tick, jumping=False,
                run_mode='run', hole_progress=0.0):
    """같은 동작 진행률로 화면과 충돌 마스크의 프레임 번호를 선택한다."""
    if jumping:
        return 0
    if frame_count and name == 'hsucat_crouch.png':
        progress = min(1.0, max(0.0, (config.HSUCAT_GIANT_YAWN_START_X - x)
                                / (config.HSUCAT_GIANT_YAWN_START_X - config.HSUCAT_GIANT_YAWN_END_X)))
        return int(progress * (frame_count - 1))
    if frame_count and name == 'hsucat_run.png':
        if run_mode == 'fall' and x <= config.HSUCAT_FALL_START_X:
            progress = min(1.0, max(0.0, (config.HSUCAT_FALL_START_X - x)
                                    / (config.HSUCAT_FALL_START_X - config.HSUCAT_FALL_END_X)))
            return config.HSUCAT_RUN_FRAME_COUNT + int(progress * (frame_count - config.HSUCAT_RUN_FRAME_COUNT - 1))
        return int(animation_tick // config.OBSTACLE_FRAME_TICKS) % config.HSUCAT_RUN_FRAME_COUNT
    if frame_count and name == 'hsucat_book.png':
        progress = min(1.0, max(0.0, (config.SCREEN_SIZE[0] - x) / config.HSUCAT_BOOK_DROP_DISTANCE))
        return int(progress * (frame_count - 1))
    if frame_count and name in config.SJ_HOLE_TYPES:
        return int(hole_progress * (frame_count - 1))
    return int(animation_tick // config.OBSTACLE_FRAME_TICKS) % frame_count if frame_count else 0


def cluster_parts(members, *, x, ground_y, frame_count, animation_tick):
    """상찌 무리의 개별 포즈와 정수 화면 좌표를 그리기·충돌에 함께 전달한다."""
    ground_frame = int(animation_tick // config.OBSTACLE_FRAME_TICKS) % frame_count
    return tuple((0 if member.is_jumping(x) else ground_frame,
                  int(x + member.offset_x),
                  int(ground_y + member.y_offset(x)))
                 for member in members)
