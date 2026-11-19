"""이미지 읽기와 모션 시트 분리."""
from math import ceil
import pygame
if __package__:
    from .config import (IMAGE_DIR, COLLISION_ALPHA_THRESHOLD, SJ_BASE_IMAGE_FILE,
                         HSUCAT_GIANT_IMAGE_FILE, HSUCAT_BOOK_IMAGE_FILE, HSUCAT_FALL_IMAGE_FILE,
                         SJ_ESCAPE_IMAGE_FILE)
else:
    from config import (IMAGE_DIR, COLLISION_ALPHA_THRESHOLD, SJ_BASE_IMAGE_FILE,
                        HSUCAT_GIANT_IMAGE_FILE, HSUCAT_BOOK_IMAGE_FILE, HSUCAT_FALL_IMAGE_FILE,
                        SJ_ESCAPE_IMAGE_FILE)

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


def load_hsucat_run_obstacle_frames(height):
    """기존 달리기 네 포즈와 같은 크기의 몸체로 넘어지는 네 포즈를 준비한다."""
    running = load_hsucat_frames(height)
    sheet = load_image(HSUCAT_FALL_IMAGE_FILE)
    poses = []
    for row in range(2):
        for col in range(2):
            left, right = col * sheet.get_width() // 2, (col + 1) * sheet.get_width() // 2
            top, bottom = row * sheet.get_height() // 2, (row + 1) * sheet.get_height() // 2
            cell = sheet.subsurface((left, top, right - left, bottom - top))
            poses.append(cell.subsurface(cell.get_bounding_rect(min_alpha=20)).copy())
    scale = height / max(pose.get_height() for pose in poses)
    falling = [pygame.transform.smoothscale(pose, (
        max(1, round(pose.get_width() * scale)), max(1, round(pose.get_height() * scale))))
        for pose in poses]
    width = max(running[0].get_width(), *(pose.get_width() for pose in falling))
    frames = []
    for pose in running + falling:
        frame = pygame.Surface((width, height), pygame.SRCALPHA)
        # 넘어지며 넓어지는 몸은 오른쪽으로 펼치고 기존 달리기의 x좌표는 유지한다.
        frame.blit(pose, (0, height - pose.get_height()))
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


def load_greeting_frames(filename, height):
    """2×2 인사 포즈를 공통 배율과 양발 중심·발바닥 높이에 맞춘다."""
    sheet = load_image(filename)
    poses = []
    for row in range(2):
        for col in range(2):
            left, right = col * sheet.get_width() // 2, (col + 1) * sheet.get_width() // 2
            top, bottom = row * sheet.get_height() // 2, (row + 1) * sheet.get_height() // 2
            cell = sheet.subsurface((left, top, right - left, bottom - top))
            bounds = cell.get_bounding_rect(min_alpha=20)
            # 팔의 너비가 달라도 몸통이 좌우로 흔들리지 않도록 양발 중심을 쓴다.
            foot_height = max(1, round(bounds.height * 0.08))
            feet = cell.subsurface((0, bounds.bottom - foot_height,
                                   cell.get_width(), foot_height)).get_bounding_rect(min_alpha=20)
            poses.append((cell.subsurface(bounds).copy(), feet.centerx - bounds.left))
    scale = height / max(pose.get_height() for pose, _ in poses)
    anchor = ceil(max(foot_x for _, foot_x in poses) * scale)
    width = anchor + ceil(max(pose.get_width() - foot_x for pose, foot_x in poses) * scale)
    frames = []
    for pose, foot_x in poses:
        resized = pygame.transform.smoothscale(pose, (
            max(1, round(pose.get_width() * scale)), max(1, round(pose.get_height() * scale))))
        frame = pygame.Surface((width, height), pygame.SRCALPHA)
        frame.blit(resized, (anchor - round(foot_x * scale), height - resized.get_height()))
        frames.append(frame)
    return frames


def load_sj_wave_frames(height):
    """기본 상찌의 손 흔들기 시트를 공통 인사 포즈 로더로 준비한다."""
    return load_greeting_frames(SJ_BASE_IMAGE_FILE, height)


def load_hsucat_giant_frames(size):
    """거대 캣의 하품 시트 한 장을 같은 배율·발 위치의 네 포즈로 준비한다."""
    # 이전 이미지의 실제 몸체 영역을 기준으로 크기·발 위치와 회피 난이도를 유지한다.
    bounds = load_image('hsucat_crouch.png', size=size).get_bounding_rect(min_alpha=20)
    sheet = load_image(HSUCAT_GIANT_IMAGE_FILE)
    poses = []
    for row in range(2):
        for col in range(2):
            left, right = col * sheet.get_width() // 2, (col + 1) * sheet.get_width() // 2
            top, bottom = row * sheet.get_height() // 2, (row + 1) * sheet.get_height() // 2
            cell = sheet.subsurface((left, top, right - left, bottom - top))
            poses.append(cell.subsurface(cell.get_bounding_rect(min_alpha=20)).copy())
    scale = min(bounds.width / max(pose.get_width() for pose in poses),
                bounds.height / max(pose.get_height() for pose in poses))
    frames = []
    for pose in poses:
        resized = pygame.transform.smoothscale(pose, (
            max(1, round(pose.get_width() * scale)), max(1, round(pose.get_height() * scale))))
        frame = pygame.Surface(size, pygame.SRCALPHA)
        frame.blit(resized, resized.get_rect(midbottom=bounds.midbottom))
        frames.append(frame)
    return frames


def load_hsucat_book_frames(height):
    """책이 옆으로 떨어져도 몸체 좌표를 유지하는 네 포즈를 준비한다."""
    reference = load_image('hsucat_book.png', height=height)
    bounds = reference.get_bounding_rect(min_alpha=20)
    sheet = load_image(HSUCAT_BOOK_IMAGE_FILE)
    cells = []
    for row in range(2):
        for col in range(2):
            left, right = col * sheet.get_width() // 2, (col + 1) * sheet.get_width() // 2
            top, bottom = row * sheet.get_height() // 2, (row + 1) * sheet.get_height() // 2
            cells.append(sheet.subsurface((left, top, right - left, bottom - top)))
    # 포즈마다 따로 가운데 정렬하면 책의 이동에 따라 캐릭터까지 움직이게 된다.
    areas = [cell.get_bounding_rect(min_alpha=20) for cell in cells]
    source = areas[0].unionall(areas[1:])
    scale = min(bounds.width / source.width, bounds.height / source.height)
    size = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
    frames = []
    for cell in cells:
        resized = pygame.transform.smoothscale(cell.subsurface(source), size)
        frame = pygame.Surface(reference.get_size(), pygame.SRCALPHA)
        frame.blit(resized, resized.get_rect(midbottom=bounds.midbottom))
        frames.append(frame)
    return frames


def _load_sj_escape_frames(size):
    """구덩이 바닥을 맞춘 탈출 네 포즈와 몸체 전용 충돌 표면을 준비한다."""
    sheet = load_image(SJ_ESCAPE_IMAGE_FILE)
    poses = []
    for row in range(2):
        for col in range(2):
            left, right = col * sheet.get_width() // 2, (col + 1) * sheet.get_width() // 2
            top, bottom = row * sheet.get_height() // 2, (row + 1) * sheet.get_height() // 2
            cell = sheet.subsurface((left, top, right - left, bottom - top))
            poses.append(cell.subsurface(cell.get_bounding_rect(min_alpha=20)).copy())
    scale = min(size[0] / max(pose.get_width() for pose in poses),
                size[1] / max(pose.get_height() for pose in poses))
    frames, bodies = [], []
    for pose in poses:
        resized = pygame.transform.smoothscale(pose, (
            max(1, round(pose.get_width() * scale)), max(1, round(pose.get_height() * scale))))
        frame = pygame.Surface(size, pygame.SRCALPHA)
        frame.blit(resized, resized.get_rect(midbottom=(size[0] // 2, size[1])))
        # 초록 몸체와 연노란 배를 함께 잡고, 주황 구덩이는 판정에서 제외한다.
        green = pygame.Mask(size)
        for x in range(size[0]):
            for y in range(size[1]):
                red, green_channel, blue, alpha = frame.get_at((x, y))
                green_body = green_channel > red + 20 and green_channel > blue + 20
                pale_belly = green_channel > red - 24 and green_channel > blue + 35 and green_channel > 165
                if alpha > COLLISION_ALPHA_THRESHOLD and (green_body or pale_belly):
                    green.set_at((x, y))
        body = pygame.Surface(size, pygame.SRCALPHA)
        for component in green.connected_components(3):
            outline = component.outline()
            if len(outline) >= 3:
                pygame.draw.polygon(body, (255, 255, 255, 255), outline)
        frames.append(frame)
        bodies.append(body)
    return frames, bodies


def load_sj_obstacles(reference, *, height, burrow_size, gap, reference_frames=None, collision_frames=None):
    """상찌 달리기·굴 진입/탈출과 손 흔드는 묶음을 미리 만든다."""
    obstacles = {'sj_run.png': _load_two_pose_frames('sj_run.png', height)}
    reference_frames = reference_frames if reference_frames is not None else [reference]
    for count, name in ((2, 'sj_pair'), (3, 'sj_triple')):
        frames = []
        for pose in reference_frames:
            cluster = pygame.Surface((reference.get_width() * count + gap * (count - 1),
                                      reference.get_height()), pygame.SRCALPHA)
            for index in range(count):
                cluster.blit(pose, (index * (reference.get_width() + gap), 0))
            frames.append(cluster)
        obstacles[name] = frames

    digging = _load_two_pose_frames('sj_dig.png', height)
    source = load_image('sj_hole.png')
    hole = source.subsurface(source.get_bounding_rect(min_alpha=20)).copy()
    scale = min(burrow_size[0] / hole.get_width(), burrow_size[1] / hole.get_height())
    hole = pygame.transform.smoothscale(hole, (
        max(1, round(hole.get_width() * scale)), max(1, round(hole.get_height() * scale))))
    width, bottom = burrow_size
    frames = []
    body_frames = []
    for index in range(12):
        frame = pygame.Surface(burrow_size, pygame.SRCALPHA)
        body = pygame.Surface(burrow_size, pygame.SRCALPHA)
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
                body.set_clip((0, 0, width, opening_bottom))
            body.blit(pose, pose.get_rect(midbottom=(width // 2, bottom + round(height * sink))))
            body.set_clip(None)
            frame.blit(body, (0, 0))
        if visible_hole is not None:
            # 앞쪽 흙 테두리를 몸 앞에 겹쳐 굴 안으로 들어가는 깊이를 표현한다.
            lip_top = round(visible_hole.get_height() * 0.65)
            frame.blit(visible_hole, (hole_rect.left, hole_rect.top + lip_top),
                       (0, lip_top, visible_hole.get_width(), visible_hole.get_height() - lip_top))
        frames.append(frame)
        body_frames.append(body)
    obstacles['sj_burrow'] = frames
    escaping, escape_bodies = _load_sj_escape_frames(burrow_size)
    obstacles['sj_escape'] = escaping
    if collision_frames is not None:
        collision_frames['sj_burrow'] = body_frames
        collision_frames['sj_escape'] = escape_bodies
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


