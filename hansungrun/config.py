"""공통 설정과 파일 경로."""
from pathlib import Path
PROJECT_DIR = Path(__file__).resolve().parent
# 구조 개선: 게임 설정을 한곳에 모아 수치를 쉽게 조정한다.
SCREEN_SIZE = (480, 360)
FPS = 120
# 기존 속도와 중력은 60Hz를 기준으로 실제 시간에 맞춰 환산한다.
PHYSICS_HZ = 60
CHARACTER_HEIGHT = 120
PLAYER_GROUND_OFFSET = 2
OBSTACLE_GROUND_OFFSET = 7
OBSTACLE_SPEED = 6
BACKGROUND_SPEED = OBSTACLE_SPEED
JUMP_SPEED = -15
GRAVITY = 0.6
PASS_BONUS = 10
SURVIVAL_POINTS_PER_SECOND = 1
SPEED_INCREASE_RATIO = 0.05
# 가장자리의 희미한 반투명 픽셀은 충돌에서 제외한다.
COLLISION_ALPHA_THRESHOLD = 127
# 장애물 윤곽을 설정 비율만큼 안쪽으로 줄인다(최소 1픽셀).
OBSTACLE_MASK_INSET_RATIO = 0.06
IMAGE_DIR = PROJECT_DIR / 'image'
# 프로젝트 내부 txt 폴더의 기존 기록을 계속 읽고 쓴다.
HIGH_SCORE_PATH = PROJECT_DIR / 'txt' / 'high_score.txt'
HUD_MARGIN = 10
HUD_GAP = 20
RUN_FRAME_TICKS = 6
DAY_NIGHT_INTERVAL = 30.0
BACKGROUND_FADE_SECONDS = 3.0
BACKGROUND_SIZE = (960, SCREEN_SIZE[1])
# 각 항목은 30초 슬롯이다. 겨울 밤 다음에는 다시 봄 낮으로 돌아간다.
BACKGROUND_FILES = tuple(
    f'hansung_{season}_{time}.png'
    for season in ('spring', 'summer', 'autumn', 'winter')
    for time in ('morning', 'night')
)
OBSTACLE_FILES = ('hansungcat.png', 'ggoggoandgguggu.png', 'sangjji.png')
# 장애물마다 키를 정하는 표다. 상찌는 120의 1/3인 40픽셀로 작게 보여 준다.
OBSTACLE_HEIGHTS = {name: (CHARACTER_HEIGHT // 3 if name == 'sangjji.png'
                           else CHARACTER_HEIGHT) for name in OBSTACLE_FILES}
CHICKEN_TYPES = ('chicken_white_ground', 'chicken_brown_ground',
                 'chicken_white_flying', 'chicken_brown_flying')
OBSTACLE_HEIGHTS.update({name: (80 if name.endswith('flying') else 96) for name in CHICKEN_TYPES})
CHICKEN_UNLOCK_SECONDS = 2 * DAY_NIGHT_INTERVAL  # 첫 봄이 끝나면 지상·비행형 모두 계속 허용.
FLYING_HEAD_GAP = 12
OBSTACLE_FRAME_TICKS = 6
# 이전 장애물이 완전히 사라진 뒤, 착지와 판단 시간을 보장하는 접근 간격.
OBSTACLE_RECOVERY_SECONDS = 1.2
GROUND_PATTERNS = (
    ('hansungcat.png', 'sangjji.png'),
    ('chicken_white_ground', 'chicken_brown_ground', 'sangjji.png'),
    ('sangjji.png', 'ggoggoandgguggu.png', 'hansungcat.png'),
    ('chicken_brown_ground', 'hansungcat.png'),
)
SUMMER_PATTERNS = (
    ('chicken_white_flying', 'sangjji.png', 'hansungcat.png'),
    ('sangjji.png', 'chicken_brown_flying', 'chicken_white_ground'),
    ('hansungcat.png', 'chicken_white_flying', 'chicken_brown_ground'),
    ('chicken_brown_flying', 'chicken_white_flying', 'sangjji.png'),
)
