import pygame

pygame.init()


background = pygame.display.set_mode((480,360))
pygame.display.set_caption("Hansungrun")

fps = pygame.time.Clock()

# image_bg = pygame.image.load() 배경인데 배경은 안넣음 상대경로로 줘야 다른컴퓨터에서도 프로젝트가 실행됨 "image/sangsangbugi.png"
hansungcat = pygame.image.load("image/hansungcat.png").convert_alpha()
sangsangbugi_side = pygame.image.load("image/sangsangbugi_side.png").convert_alpha()

# 배경의 가로 세로를 가져와옴
size_bg_width = background.get_size()[0]    
size_bg_height = background.get_size()[1]

# 이미지 크기 조절
original_width_hansungcat = hansungcat.get_width()
original_height_hansungcat = hansungcat.get_height()

original_width_sangsangbugi_side = sangsangbugi_side.get_width()
original_height_sangsangbugi_side = sangsangbugi_side.get_height()

# 높이(120) 기준으로 가로 비율을 조절함
new_height = 120
new_width_hansungcat = int(original_width_hansungcat * new_height / original_height_hansungcat)   

# 높이는 같은 기준으로 해줄것이기 때문
new_width_sangsangbugi_side = int(original_width_sangsangbugi_side * new_height / original_height_sangsangbugi_side)   

hansungcat = pygame.transform.smoothscale(
    hansungcat,
    (new_width_hansungcat, new_height))

sangsangbugi_side = pygame.transform.smoothscale(
    sangsangbugi_side,
    (new_width_sangsangbugi_side, new_height))


GROUND_OFFSET_bugi = 2 # 이미지 크기 때문에 바닥에 발이 닿게 수정
GROUND_OFFSET_cat = 7  # 이미지 크기 때문에 바닥에 발이 닿게 수정

# 이미지들의 위치
x_pos_hansungcat = size_bg_width # 중요한 개념 게임의 좌표평면은 좌측 상단이 0,0임 / 지금 좌측 상단 0,0 기준으로 보면 이미지는 외부에 있음
y_pos_hansungcat = size_bg_height - ((size_bg_height//3) - GROUND_OFFSET_cat)
# y 축의 값이 내려가야 증가 / 위로 올라가면 감소 즉 전체 배경 360(바닥면)에서 한성부기의 이미지 좌측상단의 크기를 빼주면됨
# 단 이미지의 모양에 따라 바닥면에 딱 붙게 하기 위해서 약간의 보정값이 필요함 그게 바로 저 GROUND_OFFSET임

# 상상부기이미지가 있는 위치
x_pos_sangsangbugi_side = 0 # 중요한 개념 게임의 좌표평면은 좌측 상단이 0,0임
y_pos_sangsangbugi_side = size_bg_height - new_height + GROUND_OFFSET_bugi

x_speed_hansungcat = 6 # 장애물이 전진해오는 초기 속도

# 무한 반복문 게임을 종료하기 위한 변수
play = True

jump_speed = -15    # 점프를 시작할때의 속도
# 파이썬의 경우 0,0 이 좌측 상단임 즉 캐릭터가 서있는 곳의 좌표는 +라는것 
# 즉 점프를 할때 스피드임
gravity = 0.4  # 중력
# 왜 중력이 있어야해? 점점점 자연스럽게 떨어지기 위해서 직선으로 슉 떨어지는게 아니라 자연스럽게 포물선으로 떨어져야함
velocity_y = 0  # y축 속도
is_jumping =  False # 점프중인지 확인하는 변수

ground_y = size_bg_height - new_height + GROUND_OFFSET_bugi # 캐릭터가 바닥에 도착했는가

# 포인트 관련
font_point= pygame.font.SysFont(None,30) # 기본 글자체 / 크기
point = 0
passed = False

# 게임오버
font_gameover = pygame.font.SysFont(None,80)
text_gameover = font_gameover.render('GAME OVER',True,(255,0,0)) # 가운데 bool값은 좀더 부드러운 처리해줌

size_text_width = text_gameover.get_rect().size[0]     # 텍스트를 가운데 넣어주기 위해서 텍스트 좌표를 계산해서 넣어줌
size_text_height = text_gameover.get_rect().size[1]

x_pos_text = size_bg_width / 2 - size_text_width/2    # 좌표값을 설정해줌
y_pos_text = size_bg_height / 2 - size_text_height/2

while play:
    deltatime =fps.tick(60) # fps 조절 (스피드 조절)
    for event in pygame.event.get():
         if event.type == pygame.QUIT:
             play = False

         if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if not is_jumping:   # 스페이스바가 눌리면
                    velocity_y = jump_speed # y축 속도를 처음 점프속도로 넣어줌
                    is_jumping = True   # 현재 점프중이니까 점프 인지 아닌지 판별하기 위한 변수를 True로 바꿔줌


    # 점프
    if is_jumping:  # 현재 상태가 점프임? True or False
        velocity_y += gravity
        y_pos_sangsangbugi_side += velocity_y 
        # y축 속도가 점점점 떨어져서 자연스럽게 포물선으로 내려와야함
        # x축은 자연스럽게 앞으로 가면 떨어짐
        # 쿠키런 스타일로 개조하기 위해서는 x축은 고정한 위치에 있으면 되고 y축의 점프만 있으면 됨
        # 장애물의 경우 좌우가 아닌 특정 방향 우->좌로 이동하고 화면 밖을 벗어나게 되면 장애물의 좌표를 
        # 초기 등장 좌표로 하여 반복하여 등장하게 만들면 됨

        if y_pos_sangsangbugi_side >= ground_y: # 땅에 도착했음? 값이 커지면 커질수록 아래로 내려감 좌표평면을 기억할것!
            y_pos_sangsangbugi_side = ground_y 
            velocity_y = 0
            is_jumping = False

    # 한성캣의 좌측으로 이동
    x_pos_hansungcat -= x_speed_hansungcat

    rect_sangsangbugi_side = sangsangbugi_side.get_rect()
    rect_sangsangbugi_side.left = x_pos_sangsangbugi_side
    rect_sangsangbugi_side.top = y_pos_sangsangbugi_side

    rect_hansungcat = hansungcat.get_rect()
    rect_hansungcat.left = x_pos_hansungcat
    rect_hansungcat.top = y_pos_hansungcat

    # 상상부기가 한성캣을 점프해서 넘어갔는가?그렇다면 점수를 더해줘!
    # 위치가 중요하다 먼저 점수를 판정하고 장애물의 위치를 초기화 한다 
    # 위치를 변경시키면 장애물의 위치값이 초기화되서 점수가 안올라감(초기화된 위치는 0이상이니까)
    if (rect_sangsangbugi_side.left >= rect_hansungcat.right) and not passed:
        point += 10
        passed =True

    # 한성캣의 취이가 x값 -로 벗어나게 되면 화면을 벗어난거임
    # 그러면 한성캣의 좌표를 다시 오른쪽 화면 밖 좌표값으로 초기화해줘서 마치 재등장한것처럼 만들어주면됨
    if x_pos_hansungcat + new_width_hansungcat < 0 : 
        x_pos_hansungcat = size_bg_width
        passed = False

    # 충돌시에 게임 오버
    if rect_sangsangbugi_side.colliderect(rect_hansungcat):
        background.blit(text_gameover,(x_pos_text,y_pos_text))
        pygame.display.update()
        pygame.time.delay(2000)
        play = False # 게임이 종료되게 만드려면 이 변수가 있어야함 
        # 다만 지금은 게임이 종료되면 GAME OVER가 뜨고 뜬 상태를 유지하고 난 후에 키를 입력받는데
        # 어떤 엔터키를 입력받자 그러면 재시작할수 있게 말이지
        # x_speed_hansungcat = -x_speed_hansungcat 충돌시에 반대편으로 이동하게 만드는건데 
        # 쿠키런 스타일은 그냥 빠져 나가야 하기 때문에 필요 없음

    # 배경 깔기
    # background.blit(사용할 배경,(0,0)) 여기선 배경을 안쓰고 그냥 투명한 색으로 채워만 놓음
    background.fill((255, 255, 255))

    # 이미지 그리기
    background.blit(hansungcat,(x_pos_hansungcat, y_pos_hansungcat))  
    background.blit(sangsangbugi_side,(x_pos_sangsangbugi_side, y_pos_sangsangbugi_side))

    text_point = font_point.render(str(point), True, (0,0,0))
    background.blit(text_point, (10,10))

    pygame.display.update()

pygame.quit()

