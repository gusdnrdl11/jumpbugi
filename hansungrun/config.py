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
PLAYER_HITBOX_SHRINK = (-40, -40)
OBSTACLE_HITBOX_SHRINK = (-50, -40)
IMAGE_DIR = PROJECT_DIR / 'image'
# 프로젝트 내부 txt 폴더의 기존 기록을 계속 읽고 쓴다.
HIGH_SCORE_PATH = PROJECT_DIR / 'txt' / 'high_score.txt'
HUD_MARGIN = 10
HUD_GAP = 20
RUN_FRAME_TICKS = 6
DAY_NIGHT_INTERVAL = 30.0
BACKGROUND_FADE_SECONDS = 3.0
BACKGROUND_SIZE = (960, SCREEN_SIZE[1])
OBSTACLE_FILES = ('hansungcat.png', 'ggoggoandgguggu.png', 'sangjji.png')
# 장애물마다 키를 정하는 표다. 상찌는 120의 1/3인 40픽셀로 작게 보여 준다.
OBSTACLE_HEIGHTS = {name: (CHARACTER_HEIGHT // 3 if name == 'sangjji.png'
                           else CHARACTER_HEIGHT) for name in OBSTACLE_FILES}
