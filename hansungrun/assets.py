"""이미지 읽기와 모션 시트 분리."""
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
        sheet = load_image('ggoggoandgguggu_side.png')
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


def load_hansungcat_frames(height):
    """한성캣 2×2 달리기 시트를 같은 배율·발 위치의 네 프레임으로 분리한다."""
    sheet = load_image('hansungcat_2.png')
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


def load_sangjji_obstacles(reference, *, height, burrow_size, gap):
    """상찌 달리기·굴 파기와 기존 상찌를 나란히 둔 묶음을 미리 만든다."""
    obstacles = {'sangjji_2.png': _load_two_pose_frames('sangjji_2.png', height)}
    for count, name in ((2, 'sangjji_pair'), (3, 'sangjji_triple')):
        cluster = pygame.Surface((reference.get_width() * count + gap * (count - 1),
                                  reference.get_height()), pygame.SRCALPHA)
        for index in range(count):
            cluster.blit(reference, (index * (reference.get_width() + gap), 0))
        obstacles[name] = [cluster]

    digging = _load_two_pose_frames('sangjji_3.png', height)
    source = load_image('sangjji_4.png')
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
    obstacles['sangjji_burrow'] = frames
    return obstacles


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


