"""누적 계절 슬롯과 배경 혼합값. 화면 출력과 난이도 정책에 의존하지 않는다."""
from dataclasses import dataclass
import math

if __package__:
    from . import config
else:
    import config


@dataclass(frozen=True)
class SeasonProgress:
    total_slots_passed: int
    current_slot: int
    season_cycle_count: int

    @classmethod
    def from_elapsed(cls, elapsed, interval):
        if interval <= 0:
            raise ValueError('슬롯 시간은 0보다 커야 합니다.')
        total = math.floor((max(0.0, elapsed) + 1e-9) / interval)
        return cls(total, total % config.SLOTS_PER_CYCLE,
                   total // config.SLOTS_PER_CYCLE)


@dataclass(frozen=True)
class BackgroundTransition:
    from_index: int
    to_index: int
    alpha: int
    night_alpha: int


def background_transition(elapsed, interval):
    """같은 슬롯 시계에서 배경 두 장의 혼합도와 HUD 밝기를 계산한다."""
    cycle = SeasonProgress.from_elapsed(elapsed, interval).total_slots_passed
    slot_elapsed = max(0.0, elapsed - cycle * interval)
    progress = min(slot_elapsed / min(config.BACKGROUND_FADE_SECONDS, interval), 1.0)
    eased = progress * progress * (3 - 2 * progress)
    to_index = cycle % len(config.BACKGROUND_FILES)
    from_index = (cycle - 1) % len(config.BACKGROUND_FILES) if cycle else 0
    alpha = round(255 * eased) if cycle else 0
    source_night = from_index % 2
    target_night = to_index % 2
    night_alpha = round(255 * (source_night * (1 - eased) + target_night * eased))
    return BackgroundTransition(from_index, to_index, alpha, night_alpha)
