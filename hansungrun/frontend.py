"""프론트: 화면·이미지·글꼴·배경 혼합·출력."""
import pygame
if __package__:
    from .assets import load_image, load_run_frames, load_chicken_frames, collision_mask
    from .config import (
        BACKGROUND_SIZE,
        BACKGROUND_FILES,
        CHARACTER_HEIGHT,
        CHICKEN_TYPES,
        HUD_GAP,
        HUD_MARGIN,
        OBSTACLE_FILES,
        OBSTACLE_HEIGHTS,
        OBSTACLE_MASK_INSET_RATIO,
        SCREEN_SIZE
    )
else:
    from assets import load_image, load_run_frames, load_chicken_frames, collision_mask
    from config import (
        BACKGROUND_SIZE,
        BACKGROUND_FILES,
        CHARACTER_HEIGHT,
        CHICKEN_TYPES,
        HUD_GAP,
        HUD_MARGIN,
        OBSTACLE_FILES,
        OBSTACLE_HEIGHTS,
        OBSTACLE_MASK_INSET_RATIO,
        SCREEN_SIZE
    )


class GameView:
    def __init__(self):
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption('Hansungrun')
        # 스크롤 배경: 긴 이미지의 비율을 유지하고 같은 표면을 이어 그린다.
        # 배경만 불투명하게 변환해 이전 프레임과의 혼합·잔상을 방지한다.
        # 계절별 낮·밤도 같은 크기·스크롤 위치에서 섞어 길이 이어지게 한다.
        self.background_stages = tuple(
            load_image(filename, size=BACKGROUND_SIZE).convert() for filename in BACKGROUND_FILES
        )
        self.background_overlay = self.background_stages[0].copy()
        self.stage = self.background_stages[0].copy()
        self.background_width = self.stage.get_width()
        self.player_image = load_image('sangsangbugi_side.png', height=CHARACTER_HEIGHT)
        self.run_frames = load_run_frames(self.player_image)
        # 자원을 한 번만 로딩하고 재등장 시 선택과 위치 초기화만 한다.
        self.obstacle_images = {
            name: load_image(name, height=OBSTACLE_HEIGHTS[name]) for name in OBSTACLE_FILES
        }
        self.obstacle_frames = {name: [image] for name, image in self.obstacle_images.items()}
        chicken_sheet = load_image('ggoggoandgguggu_side.png')
        for name in CHICKEN_TYPES:
            self.obstacle_frames[name] = load_chicken_frames(
                0 if 'white' in name else 1, OBSTACLE_HEIGHTS[name], chicken_sheet)
            self.obstacle_images[name] = self.obstacle_frames[name][0]
        # 크기 조절 후 한 번만 생성하며 실제 표시 프레임과 같은 마스크를 쓴다.
        self.player_masks = [collision_mask(frame) for frame in self.run_frames]
        self.obstacle_masks = {
            name: collision_mask(image, max(1, round(image.get_height() * OBSTACLE_MASK_INSET_RATIO)))
            for name, image in self.obstacle_images.items()
        }
        self.obstacle_frame_masks = {
            name: [collision_mask(frame, max(1, round(frame.get_height() * OBSTACLE_MASK_INSET_RATIO)))
                   for frame in frames]
            for name, frames in self.obstacle_frames.items() if len(frames) > 1
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
        self.rendered_background = (0, 0, 0)

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
        self.screen.blit(self.stage, (state.background_x, 0))
        self.screen.blit(self.stage, (state.background_x + self.background_width, 0))
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


