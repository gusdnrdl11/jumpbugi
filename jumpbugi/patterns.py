"""해금된 장애물 순서와 대기열 선택. 이동·이미지·충돌은 다루지 않는다."""
from dataclasses import dataclass
import random

if __package__:
    from . import config
else:
    import config


@dataclass(frozen=True)
class PatternUnlocks:
    chicken: bool
    hsucat: bool
    sj: bool
    sj_groups: bool
    sj_escape: bool

    def allows(self, kind):
        return ((self.chicken or kind not in config.CHICKEN_TYPES)
                and (self.hsucat or kind not in config.HSUCAT_TYPES)
                and (self.sj or kind not in config.SJ_TYPES)
                and (self.sj_groups or kind not in config.SJ_CLUSTER_TYPES)
                and (self.sj_escape or kind != 'sj_escape'))


def available_patterns(obstacle_sizes, unlocks):
    """준비된 자원과 현재 해금 조건을 모두 만족하는 기존 순서만 돌려준다."""
    pool = config.GROUND_PATTERNS
    if unlocks.chicken:
        pool += config.SUMMER_PATTERNS
    if unlocks.hsucat:
        pool += config.HSUCAT_PATTERNS
    if unlocks.sj:
        pool += config.SJ_PATTERNS
    return [pattern for pattern in pool if all(
        kind in obstacle_sizes and unlocks.allows(kind) for kind in pattern)]


def unlocked_queue(queue, unlocks):
    """이미 선택된 순서에서도 잠긴 유형을 기존 순서대로 제외한다."""
    if not unlocks.chicken:
        queue = [kind for kind in queue if kind not in config.CHICKEN_TYPES]
    if not unlocks.hsucat:
        queue = [kind for kind in queue if kind not in config.HSUCAT_TYPES]
    if not unlocks.sj:
        queue = [kind for kind in queue if kind not in config.SJ_TYPES]
    if not unlocks.sj_groups:
        queue = [kind for kind in queue if kind not in config.SJ_CLUSTER_TYPES]
    if not unlocks.sj_escape:
        queue = [kind for kind in queue if kind != 'sj_escape']
    return queue


def choose_pattern(pool, difficulty):
    """어려운 풀 선택과 순서 연결 여부를 등장 시 한 번 결정한다."""
    hard = [pattern for pattern in pool if pattern in config.HARD_PATTERNS]
    if hard and random.random() < difficulty.hard_pattern_probability:
        pool = hard
    pattern = random.choice(pool)
    if random.random() >= difficulty.chain_probability:
        pattern = pattern[:1]
    return pattern
