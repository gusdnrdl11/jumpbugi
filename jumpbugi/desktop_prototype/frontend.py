"""프론트: 준비된 이미지와 상태를 화면·UI로 그린다."""
import pygame
if __package__:
    from .assets import load_game_assets
    from .config import (
        GAME_TITLE,
        CHARACTER_HEIGHT,
        HUD_GAP,
        HUD_MARGIN,
        SCREEN_SIZE,
        PLAYER_GROUND_OFFSET,
    )
else:
    from assets import load_game_assets
    from config import (
        GAME_TITLE,
        CHARACTER_HEIGHT,
        HUD_GAP,
        HUD_MARGIN,
        SCREEN_SIZE,
        PLAYER_GROUND_OFFSET,
    )


class GameView:
    def __init__(self):
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption(GAME_TITLE)
        game_assets = load_game_assets()
        self.start_image = game_assets.start_image
        self.background_stages = game_assets.background_stages
        self.player_image = game_assets.player_image
        self.run_frames = game_assets.run_frames
        self.obstacle_images = game_assets.obstacle_images
        self.obstacle_frames = game_assets.obstacle_frames
        self.player_masks = game_assets.player_masks
        self.obstacle_masks = game_assets.obstacle_masks
        self.obstacle_frame_masks = game_assets.obstacle_frame_masks
        # 배경 혼합·스크롤용 사본은 화면 담당이 따로 보관한다.
        self.startup_background = self.background_stages[0].copy()
        self.background_overlay = self.background_stages[0].copy()
        self.stage = self.background_stages[0].copy()
        self.background_width = self.stage.get_width()
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
        self.rendered_background = (0, 0, 0)
        prompt_font = pygame.font.SysFont('malgungothic,applegothic,nanumgothic', 22)
        hint_font = pygame.font.SysFont('malgungothic,applegothic,nanumgothic', 16)
        self.start_text = prompt_font.render('아무 키나 누르면 시작', True, (20, 40, 65))
        self.controls_text = hint_font.render('SPACE 점프  ·  ESC 일시정지', True, (90, 100, 110))
        self.startup_labels = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
        center_x = SCREEN_SIZE[0] // 2
        for text, y in ((self.start_text, 160), (self.controls_text, 200)):
            self.startup_labels.blit(text, text.get_rect(center=(center_x, y)))

    def draw_scrolling_background(self, background, background_x):
        """인트로와 플레이에서 같은 스크롤 좌표에 배경 두 장을 이어 그린다."""
        # 소수 좌표를 따로 절삭하면 두 타일이 1픽셀 겹쳐 알파가 중복 적용된다.
        background_x = int(background_x)
        self.screen.blit(background, (background_x, 0))
        self.screen.blit(background, (background_x + self.background_width, 0))

    def draw_startup(self, phase, frame_index, progress=0.0, *, background_x=0.0):
        """전체 화면 시작 그림과 달리는 부기 뒤로 나타나는 배경을 그린다."""
        self.screen.fill((255, 255, 255))
        if phase == 'splash':
            self.screen.blit(self.start_image, (0, 0))
        else:
            progress = max(0.0, min(1.0, progress)) if phase == 'transition' else 0.0
            alpha = round(255 * progress * progress * (3 - 2 * progress))
            self.startup_background.set_alpha(alpha)
            self.draw_scrolling_background(self.startup_background, background_x)
            self.startup_labels.set_alpha(255 - alpha)
            self.screen.blit(self.startup_labels, (0, 0))
            # 플레이어는 페이드 위에 그려 밝기·위치·달리기 자세를 유지한다.
            self.screen.blit(self.run_frames[frame_index], (
                0, SCREEN_SIZE[1] - CHARACTER_HEIGHT + PLAYER_GROUND_OFFSET))
        pygame.display.flip()

    def sync_background(self, state):
        """그림 쌍과 혼합도를 함께 비교하고 매번 원본부터 합성한다."""
        key = (state.background_from_index, state.background_to_index, state.background_alpha)
        if key == self.rendered_background:
            return
        self.rendered_background = key
        source, target, alpha = key
        self.stage.blit(self.background_stages[source], (0, 0))
        if alpha:
            self.background_overlay.blit(self.background_stages[target], (0, 0))
            self.background_overlay.set_alpha(alpha)
            self.stage.blit(self.background_overlay, (0, 0))

    def draw(self, state):
        self.sync_background(state)
        # 배경 → 장애물 → 플레이어 → 점수 → 안내 순으로 겹쳐 그린다.
        self.draw_scrolling_background(self.stage, state.background_x)
        sj_parts = state.sj_cluster_parts
        if sj_parts:
            for frame_index, x, y in sj_parts:
                self.screen.blit(self.obstacle_frames['sj.png'][frame_index], (int(x), int(y)))
        else:
            self.screen.blit(self.obstacle_frames[state.obstacle_name][state.obstacle_frame_index],
                             (int(state.obstacle_x), int(state.obstacle_y)))
        self.screen.blit(self.run_frames[state.player_frame_index], (0, int(state.player_y)))
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


