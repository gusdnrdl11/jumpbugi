"""공통 설정과 파일 경로."""
from pathlib import Path
PROJECT_DIR = Path(__file__).resolve().parent
GAME_TITLE = '점프부기'
START_IMAGE_FILE = 'intro.png'
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
OBSTACLE_SPEED = 7
BACKGROUND_SPEED = OBSTACLE_SPEED - 1
JUMP_SPEED = -15
GRAVITY = 0.68
# 점프·비행·높이에 관계없는 장애물 하나의 통과 보너스. 상찌 무리는 마리마다 적용한다.
PASS_BONUS = 10
SURVIVAL_POINTS_PER_SECOND = 1
# 슬롯 0~7은 확실히 가속하고, 8~15는 완만하게 가속한 뒤 고정한다.
EARLY_SPEED_INCREASE = 0.07
MID_SPEED_INCREASE = 0.002
MAX_SPEED_MULTIPLIER = 1.75
# 가장자리의 희미한 반투명 픽셀은 충돌에서 제외한다.
COLLISION_ALPHA_THRESHOLD = 130
# 장애물 윤곽을 설정 비율만큼 안쪽으로 줄인다(최소 1픽셀).
OBSTACLE_MASK_INSET_RATIO = 0.06
IMAGE_DIR = PROJECT_DIR / 'image'
# 프로젝트 내부 txt 폴더의 기존 기록을 계속 읽고 쓴다.
HIGH_SCORE_PATH = PROJECT_DIR / 'txt' / 'high_score.txt'
HUD_MARGIN = 10
HUD_GAP = 20
RUN_FRAME_TICKS = 6
DAY_NIGHT_INTERVAL = 25
BACKGROUND_FADE_SECONDS = 4.0
BACKGROUND_SIZE = (960, SCREEN_SIZE[1])
# 각 항목은 DAY_NIGHT_INTERVAL 길이의 슬롯이다. 겨울 밤 다음에는 다시 봄 낮으로 돌아간다.
BACKGROUND_FILES = tuple(
    f'hansung_{season}_{time}.png'
    for season in ('spring', 'summer', 'autumn', 'winter')
    for time in ('morning', 'night')
)
SLOTS_PER_CYCLE = len(BACKGROUND_FILES)
OBSTACLE_FILES = ('hsucat.png', 'chicken.png', 'sj.png')
WAVE_IMAGE_FILES = {'chicken.png': 'chicken_wave.png', 'hsucat.png': 'hsucat_wave.png'}
WAVE_GROUND_OFFSET = -2
WAVE_JUMP_UNLOCK_SLOT = SLOTS_PER_CYCLE
WAVE_JUMP_PROBABILITY = 0.65
WAVE_JUMP_HEIGHTS = {'high': 192.0, 'near': 128.0, 'low': 12.0}
WAVE_JUMP_CONTACT_FACTORS = {'high': 2.2, 'near': 4.8, 'low': 2.2}
WAVE_JUMP_MIN_SECONDS = 0.9
WAVE_UNDERPASS_CLEARANCE = 4
# 장애물마다 키를 정하는 표다. 상찌는 120의 1/3인 40픽셀로 작게 보여 준다.
OBSTACLE_HEIGHTS = {name: (CHARACTER_HEIGHT // 3 if name == 'sj.png'
                           else CHARACTER_HEIGHT) for name in OBSTACLE_FILES}
HSUCAT_TYPES = ('hsucat_run.png', 'hsucat_crouch.png', 'hsucat_book.png')
# 거대 캣은 하품 시트 한 장을 한 번 진행한 뒤 입을 벌린 자세를 유지한다.
HSUCAT_GIANT_IMAGE_FILE = 'hsucat_yawn.png'
HSUCAT_GIANT_FRAME_COUNT = 4
HSUCAT_GIANT_SIZE = (202, CHARACTER_HEIGHT)
HSUCAT_GIANT_YAWN_START_X = float(SCREEN_SIZE[0])
HSUCAT_GIANT_YAWN_END_X = 140.0
HSUCAT_BOOK_IMAGE_FILE = 'hsucat_drop_book.png'
HSUCAT_BOOK_DROP_DISTANCE = 300.0
HSUCAT_RUN_MODES = ('fall', 'high', 'low', 'run')
HSUCAT_RUN_FRAME_COUNT = 4
HSUCAT_FALL_IMAGE_FILE = 'hsucat_fall.png'
HSUCAT_FALL_START_X = 420.0
HSUCAT_FALL_END_X = 180.0
HSUCAT_RUN_GROUND_OFFSET = -2
# 높은 점프는 화면 위로 사라지고, 낮은 점프는 플레이어가 뛰어넘는다.
HSUCAT_RUN_JUMP_HEIGHTS = {'high': float(SCREEN_SIZE[1] + 24), 'low': 24.0}
HSUCAT_RUN_JUMP_CONTACT_FACTOR = 2.2
HSUCAT_RUN_JUMP_MIN_SECONDS = 0.9
HSUCAT_RUN_JUMP_CLEARANCE = 16
OBSTACLE_HEIGHTS.update({name: CHARACTER_HEIGHT for name in HSUCAT_TYPES})
HSUCAT_UNLOCK_SLOT = 4  # 첫 가을부터 이후 봄에도 계속 허용.
SJ_CLUSTER_TYPES = ('sj_pair', 'sj_triple')
SJ_HOLE_TYPES = ('sj_burrow', 'sj_escape')
SJ_TYPES = ('sj_run.png',) + SJ_HOLE_TYPES + SJ_CLUSTER_TYPES
SJ_UNLOCK_SLOT = 6  # 달리기·굴 파기는 첫 겨울부터 허용.
SJ_GROUP_UNLOCK_SLOT = SLOTS_PER_CYCLE  # 무리는 둘째 봄부터.
SJ_ESCAPE_UNLOCK_SLOT = SJ_GROUP_UNLOCK_SLOT
SJ_JUMP_UNLOCK_SLOT = SJ_GROUP_UNLOCK_SLOT
SJ_SINGLE_JUMP_TYPES = ('sj.png', 'sj_run.png')
SJ_CLUSTER_GAP = 3
SJ_BASE_IMAGE_FILE = 'sj_wave.png'
# 둘째 봄부터 각 상찌가 낮은 점프·높은 점프·지상 이동을 선택한다.
SJ_HOP_PROBABILITY = 0.65
SJ_JUMP_HEIGHTS = {'high': 306.0, 'low': 18.0}
SJ_HIGH_CONTACT_FACTOR = 4.8
SJ_HIGH_MIN_SECONDS = 0.9
SJ_HIGH_PLAYER_CLEARANCE = 8
SJ_LOW_CONTACT_FACTOR = 2.2
SJ_LOW_MIN_SECONDS = 0.8
SJ_HOP_TRIGGER_X = 370.0
SJ_HOP_TRIGGER_SPACING = 80.0
SJ_HOP_TRIGGER_JITTER = 25.0
SJ_BURROW_SIZE = (112, 64)
SJ_ESCAPE_IMAGE_FILE = 'sj_escape.png'
# 두 동작 모두 플레이어와 만나기 전에 진입·탈출을 마쳐 회피 여유를 둔다.
SJ_BURROW_PROFILES = {'fast': (480.0, 330.0), 'slow': (480.0, 170.0)}
SJ_ESCAPE_PROFILES = {'fast': (480.0, 300.0), 'slow': (480.0, 180.0)}
SJ_HOLE_CLEARANCE = 32
OBSTACLE_HEIGHTS.update({name: (SJ_BURROW_SIZE[1] if name in SJ_HOLE_TYPES
                               else CHARACTER_HEIGHT // 3) for name in SJ_TYPES})
CHICKEN_TYPES = ('chicken_white_ground', 'chicken_brown_ground',
                 'chicken_white_flying', 'chicken_brown_flying')
OBSTACLE_HEIGHTS.update({name: (80 if name.endswith('flying') else 96) for name in CHICKEN_TYPES})
CHICKEN_UNLOCK_SLOT = 2  # 첫 봄이 끝나면 지상·비행형 모두 계속 허용.
# 중간 높이는 머리를 스치듯 아래로 통과하고 낮은 비행만 점프로 넘는다.
FLYING_LEVELS = ('low', 'middle', 'high')
FLYING_HEAD_GAPS = {'high': 72, 'middle': 2, 'low': -92}
OBSTACLE_FRAME_TICKS = 6
# 이전 장애물이 완전히 사라진 뒤 다음 장애물이 접근하는 시간.
# 실제 간격은 항상 전체 점프 시간 + MIN_RECOVERY_TIME 이상이다.
CYCLE_RECOVERY_SECONDS = (1.2, 1.05, 0.9)
MIN_RECOVERY_TIME = 0.18
HARD_PATTERN_PROBABILITIES = (0.15, 0.45, 0.75)
PATTERN_CHAIN_PROBABILITIES = (0.25, 0.65, 0.9)
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
    ('sj_escape', 'sj_run.png'),
)
# 모두 기존 동작의 순서 조합이며 한 번에 한 장애물(또는 상찌 무리)만 접근한다.
HARD_PATTERNS = (
    SUMMER_PATTERNS[-1],
    HSUCAT_PATTERNS[2],
    SJ_PATTERNS[2],
    SJ_PATTERNS[3],
    SJ_PATTERNS[4],
)
