"""속도·접근 간격·패턴 확률. 화면·파일·난수에 의존하지 않는다."""
from dataclasses import dataclass

if __package__:
    from . import config
    from .season import SeasonProgress  # 기존 import 경로도 유지한다.
else:
    import config
    from season import SeasonProgress


@dataclass(frozen=True)
class DifficultyProfile:
    speed_multiplier: float
    recovery_seconds: float
    hard_pattern_probability: float
    chain_probability: float


def speed_multiplier_for_slot(total_slots):
    slot = max(0, total_slots)
    early = min(slot, config.SLOTS_PER_CYCLE - 1)
    middle = min(max(slot - (config.SLOTS_PER_CYCLE - 1), 0), config.SLOTS_PER_CYCLE)
    return min(config.MAX_SPEED_MULTIPLIER,
               (1 + config.EARLY_SPEED_INCREASE) ** early
               * (1 + config.MID_SPEED_INCREASE) ** middle)


def jump_flight_seconds():
    """백엔드의 적분식으로 지면에 돌아와 다시 입력 가능한 시각을 구한다."""
    return max(0.0, -(2 * config.JUMP_SPEED / config.GRAVITY + 1) / config.PHYSICS_HZ)


def profile_for_slot(total_slots):
    cycle = min(max(0, total_slots) // config.SLOTS_PER_CYCLE, 2)
    recovery = max(config.CYCLE_RECOVERY_SECONDS[cycle],
                   jump_flight_seconds() + config.MIN_RECOVERY_TIME)
    return DifficultyProfile(speed_multiplier_for_slot(total_slots), recovery,
                             config.HARD_PATTERN_PROBABILITIES[cycle],
                             config.PATTERN_CHAIN_PROBABILITIES[cycle])
