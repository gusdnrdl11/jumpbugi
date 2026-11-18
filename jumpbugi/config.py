"""공통 설정과 파일 경로."""
from pathlib import Path
PROJECT_DIR = Path(__file__).resolve().parent
GAME_TITLE = '점프부기'
START_IMAGE_FILE = 'start.png'
SPLASH_SECONDS = 2.0
START_FADE_SECONDS = 1.25
# 구조 개선: 게임 설정을 한곳에 모아 수치를 쉽게 조정한다.
SCREEN_SIZE = (480, 360)
FPS = 120
# 기존 속도와 중력은 60Hz를 기준으로 실제 시간에 맞춰 환산한다.
PHYSICS_HZ = 60
CHARACTER_HEIGHT = 120
PLAYER_GROUND_OFFSET = 2
OBSTACLE_GROUND_OFFSET = 7
# 지상 날갯짓 캐릭터의 발 전체가 화면 안에 보이도록 바닥에서 2픽셀 띄운다.
CHICKEN_GROUND_OFFSET = -2
# 작은 상찌도 발과 꼬리가 화면 아래로 잘리지 않게 올린다.
SJ_GROUND_OFFSET = -2
OBSTACLE_SPEED = 8
BACKGROUND_SPEED = OBSTACLE_SPEED - 1
JUMP_SPEED = -15
GRAVITY = 0.7
PASS_BONUS = 10
SURVIVAL_POINTS_PER_SECOND = 1
SPEED_INCREASE_RATIO = 0.07
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
BACKGROUND_FADE_SECONDS = 4.0
BACKGROUND_SIZE = (960, SCREEN_SIZE[1])
# 각 항목은 30초 슬롯이다. 겨울 밤 다음에는 다시 봄 낮으로 돌아간다.
BACKGROUND_FILES = tuple(
    f'hansung_{season}_{time}.png'
    for season in ('spring', 'summer', 'autumn', 'winter')
    for time in ('morning', 'night')
)
OBSTACLE_FILES = ('hsucat.png', 'chicken.png', 'sj.png')
# 장애물마다 키를 정하는 표다. 상찌는 120의 1/3인 40픽셀로 작게 보여 준다.
OBSTACLE_HEIGHTS = {name: (CHARACTER_HEIGHT // 3 if name == 'sj.png'
                           else CHARACTER_HEIGHT) for name in OBSTACLE_FILES}
HSUCAT_TYPES = ('hsucat_run.png', 'hsucat_crouch.png', 'hsucat_book.png')
# 웅크린 캣은 원본 비율로 표시해 기존 캣보다 넓은 큰 장애물로 유지한다.
OBSTACLE_HEIGHTS.update({name: CHARACTER_HEIGHT for name in HSUCAT_TYPES})
HSUCAT_UNLOCK_SECONDS = 4 * DAY_NIGHT_INTERVAL  # 첫 가을부터 이후 봄에도 계속 허용.
SJ_CLUSTER_TYPES = ('sj_pair', 'sj_triple')
SJ_TYPES = ('sj_run.png', 'sj_burrow') + SJ_CLUSTER_TYPES
SJ_UNLOCK_SECONDS = 6 * DAY_NIGHT_INTERVAL  # 첫 겨울부터 다음 봄에도 계속 허용.
SJ_CLUSTER_GAP = 3
SJ_BURROW_SIZE = (112, 64)
# 화면 진입부터 x=180까지 땅을 파고 들어간 뒤에는 구덩이로 남는다.
SJ_BURROW_DISTANCE = 300
OBSTACLE_HEIGHTS.update({name: (SJ_BURROW_SIZE[1] if name == 'sj_burrow'
                               else CHARACTER_HEIGHT // 3) for name in SJ_TYPES})
CHICKEN_TYPES = ('chicken_white_ground', 'chicken_brown_ground',
                 'chicken_white_flying', 'chicken_brown_flying')
OBSTACLE_HEIGHTS.update({name: (80 if name.endswith('flying') else 96) for name in CHICKEN_TYPES})
CHICKEN_UNLOCK_SECONDS = 2 * DAY_NIGHT_INTERVAL  # 첫 봄이 끝나면 지상·비행형 모두 계속 허용.
FLYING_HEAD_GAP = 12
OBSTACLE_FRAME_TICKS = 6
# 이전 장애물이 완전히 사라진 뒤, 착지와 판단 시간을 보장하는 접근 간격.
OBSTACLE_RECOVERY_SECONDS = 1.2
GROUND_PATTERNS = (
    ('hsucat.png', 'sj.png'),
    ('chicken_white_ground', 'chicken_brown_ground', 'sj.png'),
    ('sj.png', 'chicken.png', 'hsucat.png'),
    ('chicken_brown_ground', 'hsucat.png'),
)
SUMMER_PATTERNS = (
    ('chicken_white_flying', 'sj.png', 'hsucat.png'),
    ('sj.png', 'chicken_brown_flying', 'chicken_white_ground'),
    ('hsucat.png', 'chicken_white_flying', 'chicken_brown_ground'),
    ('chicken_brown_flying', 'chicken_white_flying', 'sj.png'),
)
HSUCAT_PATTERNS = (
    ('hsucat_run.png', 'sj.png'),
    ('hsucat_crouch.png', 'hsucat_run.png'),
    ('hsucat_book.png', 'chicken_white_flying', 'sj.png'),
    ('chicken_brown_ground', 'hsucat_book.png', 'hsucat_crouch.png'),
)
SJ_PATTERNS = (
    ('sj_run.png', 'sj_burrow'),
    ('sj_burrow', 'sj.png'),
    ('sj_pair', 'chicken_white_flying'),
    ('sj_triple', 'sj_run.png'),
)
