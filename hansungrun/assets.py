"""이미지 읽기와 모션 시트 분리."""
import pygame
if __package__:
    from .config import IMAGE_DIR
else:
    from config import IMAGE_DIR

def load_image(filename, *, size=None, height=None):
    """공통 이미지 로딩과 비율 유지 크기 조절."""
    # 구조 개선: 실행 디렉터리에 관계없이 이 파일 옆의 이미지를 찾는다.
    image = pygame.image.load(str(IMAGE_DIR / filename)).convert_alpha()
    if height is not None:
        size = (int(image.get_width() * height / image.get_height()), height)
    return pygame.transform.smoothscale(image, size) if size else image


def load_run_frames(reference):
    """2×2 시트의 네 달리기 포즈를 공통 배율과 발 위치로 정렬한다."""
    sheet = load_image('sangsangbugi_run_4frames.png')
    poses = []
    for row in range(2):
        for col in range(2):
            # 분할 경계를 따로 계산해 홀수 크기의 마지막 픽셀도 포함한다.
            x, right = col * sheet.get_width() // 2, (col + 1) * sheet.get_width() // 2
            y, bottom = row * sheet.get_height() // 2, (row + 1) * sheet.get_height() // 2
            cell = sheet.subsurface((x, y, right-x, bottom-y))
            poses.append(cell.subsurface(cell.get_bounding_rect(min_alpha=20)).copy())
    bounds = reference.get_bounding_rect(min_alpha=20)
    # 공통 배율로 몸통 크기를 유지하고 발바닥을 같은 지면에 맞춘다.
    scale = min(bounds.width / max(p.get_width() for p in poses),
                bounds.height / max(p.get_height() for p in poses))
    frames = []
    for pose in poses:
        size = (max(1, round(pose.get_width()*scale)), max(1, round(pose.get_height()*scale)))
        resized = pygame.transform.smoothscale(pose, size)
        frame = pygame.Surface(reference.get_size(), pygame.SRCALPHA)
        frame.blit(resized, resized.get_rect(midbottom=bounds.midbottom))
        frames.append(frame)
    return frames


