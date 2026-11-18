"""이미지 읽기와 모션 시트 분리."""
from math import ceil
import pygame
if __package__:
    from .config import IMAGE_DIR, COLLISION_ALPHA_THRESHOLD
else:
    from config import IMAGE_DIR, COLLISION_ALPHA_THRESHOLD

def load_image(filename, *, size=None, height=None):
    """공통 이미지 로딩과 비율 유지 크기 조절."""
    # 구조 개선: 실행 디렉터리에 관계없이 이 파일 옆의 이미지를 찾는다.
    image = pygame.image.load(str(IMAGE_DIR / filename)).convert_alpha()
    if height is not None:
        size = (int(image.get_width() * height / image.get_height()), height)
    return pygame.transform.smoothscale(image, size) if size else image


def intro_content_rect(image):
    """투명·희미한 흰 외곽을 제외하고 인트로 그림의 실제 경계를 찾는다."""
    opaque = pygame.mask.from_surface(image, 223)
    near_white = pygame.mask.from_threshold(
        image, (255, 255, 255, 255), (32, 32, 32, 255))
    near_white.invert()
    foreground = opaque.overlap_mask(near_white, (0, 0))
    rects = foreground.get_bounding_rects() or opaque.get_bounding_rects()
    return rects[0].unionall(rects[1:]) if rects else image.get_rect()


def prepare_intro_cover(image, size):
    """콘텐츠 중심으로 비율을 유지해 화면을 덮고 넘치는 부분만 잘라낸다."""
    bounds = intro_content_rect(image)
    # 작은 안전 여백으로 양옆의 책·꼬리를 보존하되 원본 외곽은 화면 밖으로 보낸다.
    padding = round(max(bounds.size) * 0.04)
    source_rect = bounds.inflate(2 * padding, 2 * padding).clip(image.get_rect())
    scale = max(size[0] / source_rect.width, size[1] / source_rect.height)
    scaled_size = (ceil(source_rect.width * scale), ceil(source_rect.height * scale))
    # 실제 그림 안의 흰 배경은 유지하고 표시 표면은 불투명하게 준비한다.
    content = pygame.Surface(source_rect.size).convert()
    content.fill((255, 255, 255))
    content.blit(image, (0, 0), source_rect)
    scaled = pygame.transform.smoothscale(content, scaled_size)
    prepared = pygame.Surface(size).convert()
    # 화면 크기의 표면이 중앙 source crop과 destination (0, 0, w, h)를 결정한다.
    prepared.blit(scaled, scaled.get_rect(center=prepared.get_rect().center))
    return prepared


def collision_mask(image, inset=0):
    """출력 크기의 알파 윤곽을 사용하고 장애물 테두리만 안쪽으로 깎는다."""
    mask = pygame.mask.from_surface(image, COLLISION_ALPHA_THRESHOLD)
    for _ in range(inset):
        # 8방향 이웃이 모두 채워진 픽셀만 남긴다. 구멍과 여백도 유지된다.
        eroded = mask.copy()
        for dx, dy in ((-1, -1), (0, -1), (1, -1), (-1, 0),
                       (1, 0), (-1, 1), (0, 1), (1, 1)):
            eroded = eroded.overlap_mask(mask, (dx, dy))
        mask = eroded
    return mask


def load_chicken_frames(row, height, sheet=None):
    """2행×4열 시트에서 한 캐릭터를 잘라 공통 배율·발 위치로 정렬한다."""
    if sheet is None:
        sheet = load_image('chicken_flap.png')
    poses = []
    top, bottom = row * sheet.get_height() // 2, (row + 1) * sheet.get_height() // 2
    for col in range(4):
        left, right = col * sheet.get_width() // 4, (col + 1) * sheet.get_width() // 4
        cell = sheet.subsurface((left, top, right - left, bottom - top))
        poses.append(cell.subsurface(cell.get_bounding_rect(min_alpha=20)).copy())
    scale = height / max(pose.get_height() for pose in poses)
    width = max(1, round(max(pose.get_width() for pose in poses) * scale))
    frames = []
    for pose in poses:
        resized = pygame.transform.smoothscale(pose, (
            max(1, round(pose.get_width() * scale)), max(1, round(pose.get_height() * scale))))
        frame = pygame.Surface((width, height), pygame.SRCALPHA)
        frame.blit(resized, resized.get_rect(midbottom=(width // 2, height)))
        frames.append(frame)
    return frames


def load_hsucat_frames(height):
    """한성캣 2×2 달리기 시트를 같은 배율·발 위치의 네 프레임으로 분리한다."""
    sheet = load_image('hsucat_run.png')
    poses = []
    for row in range(2):
        for col in range(2):
            left, right = col * sheet.get_width() // 2, (col + 1) * sheet.get_width() // 2
            top, bottom = row * sheet.get_height() // 2, (row + 1) * sheet.get_height() // 2
            cell = sheet.subsurface((left, top, right - left, bottom - top))
            poses.append(cell.subsurface(cell.get_bounding_rect(min_alpha=20)).copy())
    scale = height / max(pose.get_height() for pose in poses)
    width = max(1, round(max(pose.get_width() for pose in poses) * scale))
    frames = []
    for pose in poses:
        resized = pygame.transform.smoothscale(pose, (
            max(1, round(pose.get_width() * scale)), max(1, round(pose.get_height() * scale))))
        frame = pygame.Surface((width, height), pygame.SRCALPHA)
        frame.blit(resized, resized.get_rect(midbottom=(width // 2, height)))
        frames.append(frame)
    return frames


def _load_two_pose_frames(filename, height):
    """가로 두 포즈를 공통 배율과 발 위치로 정렬한다."""
    sheet = load_image(filename)
    poses = []
    for col in range(2):
        left, right = col * sheet.get_width() // 2, (col + 1) * sheet.get_width() // 2
        cell = sheet.subsurface((left, 0, right - left, sheet.get_height()))
        poses.append(cell.subsurface(cell.get_bounding_rect(min_alpha=20)).copy())
    scale = height / max(pose.get_height() for pose in poses)
    width = max(1, round(max(pose.get_width() for pose in poses) * scale))
    frames = []
    for pose in poses:
        resized = pygame.transform.smoothscale(pose, (
            max(1, round(pose.get_width() * scale)), max(1, round(pose.get_height() * scale))))
        frame = pygame.Surface((width, height), pygame.SRCALPHA)
        frame.blit(resized, resized.get_rect(midbottom=(width // 2, height)))
        frames.append(frame)
    return frames


def load_sj_obstacles(reference, *, height, burrow_size, gap):
    """상찌 달리기·굴 파기와 기존 상찌를 나란히 둔 묶음을 미리 만든다."""
    obstacles = {'sj_run.png': _load_two_pose_frames('sj_run.png', height)}
    for count, name in ((2, 'sj_pair'), (3, 'sj_triple')):
        cluster = pygame.Surface((reference.get_width() * count + gap * (count - 1),
                                  reference.get_height()), pygame.SRCALPHA)
        for index in range(count):
            cluster.blit(reference, (index * (reference.get_width() + gap), 0))
        obstacles[name] = [cluster]

    digging = _load_two_pose_frames('sj_dig.png', height)
    source = load_image('sj_hole.png')
    hole = source.subsurface(source.get_bounding_rect(min_alpha=20)).copy()
    scale = min(burrow_size[0] / hole.get_width(), burrow_size[1] / hole.get_height())
    hole = pygame.transform.smoothscale(hole, (
        max(1, round(hole.get_width() * scale)), max(1, round(hole.get_height() * scale))))
    width, bottom = burrow_size
    frames = []
    for index in range(12):
        frame = pygame.Surface(burrow_size, pygame.SRCALPHA)
        opening = min(1.0, max(0.0, (index - 1) / 4))
        visible_hole = None
        if opening:
            visible_hole = pygame.transform.smoothscale(hole, (
                max(1, round(hole.get_width() * opening)),
                max(1, round(hole.get_height() * opening))))
            hole_rect = visible_hole.get_rect(midbottom=(width // 2, bottom))
            frame.blit(visible_hole, hole_rect)
        if index < 11:
            pose = digging[index % len(digging)]
            sink = max(0.0, (index - 6) / 4)
            # 아래로 이동하는 몸은 굴 입구에서 잘라 땅 밑으로 사라지게 한다.
            if visible_hole is not None:
                opening_bottom = hole_rect.top + round(hole_rect.height * 0.65)
                frame.set_clip((0, 0, width, opening_bottom))
            frame.blit(pose, pose.get_rect(midbottom=(width // 2, bottom + round(height * sink))))
            frame.set_clip(None)
        if visible_hole is not None:
            # 앞쪽 흙 테두리를 몸 앞에 겹쳐 굴 안으로 들어가는 깊이를 표현한다.
            lip_top = round(visible_hole.get_height() * 0.65)
            frame.blit(visible_hole, (hole_rect.left, hole_rect.top + lip_top),
                       (0, lip_top, visible_hole.get_width(), visible_hole.get_height() - lip_top))
        frames.append(frame)
    obstacles['sj_burrow'] = frames
    return obstacles


def load_run_frames(reference):
    """2×2 시트의 네 달리기 포즈를 공통 배율과 발 위치로 정렬한다."""
    sheet = load_image('bugi_run.png')
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


