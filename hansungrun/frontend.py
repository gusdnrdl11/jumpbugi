"""프론트: 화면·이미지·글꼴·배경 혼합·출력."""
import pygame
if __package__:
    from .assets import load_image, load_run_frames
    from .config import (
        BACKGROUND_SIZE,
        CHARACTER_HEIGHT,
        HUD_GAP,
        HUD_MARGIN,
        OBSTACLE_FILES,
        OBSTACLE_HEIGHTS,
        RUN_FRAME_TICKS,
        SCREEN_SIZE
    )
else:
    from assets import load_image, load_run_frames
    from config import (
        BACKGROUND_SIZE,
        CHARACTER_HEIGHT,
        HUD_GAP,
        HUD_MARGIN,
        OBSTACLE_FILES,
        OBSTACLE_HEIGHTS,
        RUN_FRAME_TICKS,
        SCREEN_SIZE
    )


class GameView:
    def __init__(self):
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption('Hansungrun')
        # 스크롤 배경: 긴 이미지의 비율을 유지하고 같은 표면을 이어 그린다.
        # 배경만 불투명하게 변환해 이전 프레임과의 혼합·잔상을 방지한다.
        # 낮과 밤은 같은 크기·스크롤 위치에서 겹쳐야 전환 중에도 길이 이어진다.
        self.day_stage = load_image('hansung_morning.png', size=BACKGROUND_SIZE).convert()
        self.night_stage = load_image('hansung_night.png', size=BACKGROUND_SIZE).convert()
        self.night_overlay = self.night_stage.copy()
        self.stage = self.day_stage.copy()
        self.background_width = self.stage.get_width()
        self.player_image = load_image('sangsangbugi_side.png', height=CHARACTER_HEIGHT)
        self.run_frames = load_run_frames(self.player_image)
        # 자원을 한 번만 로딩하고 재등장 시 선택과 위치 초기화만 한다.
        self.obstacle_images = {
            name: load_image(name, height=OBSTACLE_HEIGHTS[name]) for name in OBSTACLE_FILES
        }
        self.score_font = pygame.font.SysFont(None, 30)
        self.game_over_text = pygame.font.SysFont(None, 80).render(
            'GAME OVER', True, (255, 0, 0)
        )
        self.restart_text = pygame.font.SysFont(None, 30).render(
            'press the Enter Restart', True, (255, 0, 0)
        )
        self.game_over_rect = self.game_over_text.get_rect(
            center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2)
        )
        # 정지 안내 표면은 한 번 만들어 재사용한다.
        self.pause_overlay = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
        self.pause_overlay.fill((0, 0, 0, 140))
        self.pause_text = self.score_font.render('PAUSED - ESC to resume', True, (255, 255, 255))
        self.rendered_alpha = 0

    def sync_background(self, alpha):
        """원본부터 합성해 잔상을 막고 같은 밝기의 중복 작업을 줄인다."""
        if alpha == self.rendered_alpha:
            return
        self.rendered_alpha = alpha
        self.stage.blit(self.day_stage, (0, 0))
        if alpha:
            self.night_overlay.set_alpha(alpha)
            self.stage.blit(self.night_overlay, (0, 0))

    def draw(self, state):
        self.sync_background(state.night_alpha)
        # 배경 → 장애물 → 플레이어 → 점수 → 안내 순으로 겹쳐 그린다.
        self.screen.blit(self.stage, (state.background_x, 0))
        self.screen.blit(self.stage, (state.background_x + self.background_width, 0))
        self.screen.blit(self.obstacle_images[state.obstacle_name], (state.obstacle_x, state.obstacle_y))
        frame_index = 0 if state.is_jumping else int(state.animation_tick // RUN_FRAME_TICKS)
        self.screen.blit(self.run_frames[frame_index], (0, state.player_y))
        # 우측 상단: 현재 점수를 오른쪽에 고정하고 최고점수를 그 왼쪽에 배치한다.
        # 밤하늘에서도 점수가 보이도록 배경과 함께 글자색을 밝힌다.
        shade = round(245 * state.night_alpha / 255)
        hud_color = (shade, shade, shade)
        score_text = self.score_font.render(f'SCORE {state.score}', True, hud_color)
        score_rect = score_text.get_rect(topright=(SCREEN_SIZE[0] - HUD_MARGIN, HUD_MARGIN))
        best_text = self.score_font.render(f'BEST {state.high_score}', True, hud_color)
        best_rect = best_text.get_rect(topright=(score_rect.left - HUD_GAP, HUD_MARGIN))
        self.screen.blit(best_text, best_rect)
        self.screen.blit(score_text, score_rect)
        if state.game_over:
            self.screen.blit(self.game_over_text, self.game_over_rect)
            self.screen.blit(self.restart_text,
                             (self.game_over_rect.x + 50, self.game_over_rect.y + 80))
        if state.paused:
            self.screen.blit(self.pause_overlay, (0, 0))
            self.screen.blit(self.pause_text, self.pause_text.get_rect(
                center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2)))
        pygame.display.flip()


