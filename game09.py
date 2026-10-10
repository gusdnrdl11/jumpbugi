import pygame

pygame.init()

background = pygame.display.set_mode((480,360))
pygame.display.set_caption("Hansungrun")

fps = pygame.time.Clock()

stage_1 = pygame.image.load("image/stage_1.png").convert_alpha()
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

stage_1 = pygame.transform.smoothscale(
    stage_1,
    (size_bg_width, size_bg_height))

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

# 무한 반복문
play = True
# 게임의 재시작 여부 
game_over =False

jump_speed = -15    # 점프를 시작할때의 속도
# 파이썬의 경우 0,0 이 좌측 상단임 즉 캐릭터가 서있는 곳의 좌표는 +라는것 
# 즉 점프를 할때 스피드임
gravity = 0.6  # 중력
# 왜 중력이 있어야해? 점점점 자연스럽게 떨어지기 위해서 직선으로 슉 떨어지는게 아니라 자연스럽게 포물선으로 떨어져야함
velocity_y = 0  # y축 속도
is_jumping =  False # 점프중인지 확인하는 변수

ground_y = size_bg_height - new_height + GROUND_OFFSET_bugi # 캐릭터가 바닥에 도착했는가

# 포인트 관련
font_point= pygame.font.SysFont(None,30) # 기본 글자체 / 크기
point = 0
passed = False

# 게임오버 텍스트
font_gameover = pygame.font.SysFont(None,80)
font_press = pygame.font.SysFont(None,30)

text_gameover = font_gameover.render('GAME OVER',True,(255,0,0)) # 가운데 bool값은 좀더 부드러운 처리해줌
text_press = font_press.render('press the Enter Restart',True,(255,0,0))

size_text_width = text_gameover.get_rect().size[0]     # 텍스트를 가운데 넣어주기 위해서 텍스트 좌표를 계산해서 넣어줌
size_text_height = text_gameover.get_rect().size[1]

x_pos_text = size_bg_width / 2 - size_text_width/2    # 좌표값을 설정해줌
y_pos_text = size_bg_height / 2 - size_text_height/2

while play:
    deltatime =fps.tick(60) # fps 조절 (스피드 조절)
    for event in pygame.event.get():
         if event.type == pygame.QUIT: # 게임을 아예 종료 X버튼을 눌러서
             play = False

         if event.type == pygame.KEYDOWN:   # 이벤트 타입 키다운
              # 게임오버 상태라면 ENTER로 재시작 / esc 게임 종료
            if event.key == pygame.K_ESCAPE:    # esc 눌리면 게임 종료
                play = False

           # 게임오버 상태라면 ENTER로 재시작
           # 엔터가 눌러서 재시작이 되면 모든 값을들 게임 초기값으로 변경함
            elif game_over and event.key == pygame.K_RETURN:
                y_pos_sangsangbugi_side = ground_y  # y축 위치값을 초기화
                velocity_y = 0
                is_jumping = False

                x_pos_hansungcat = size_bg_width

                point = 0
                passed = False

                game_over = False

            # 게임 중일 때만 점프
            elif not game_over and event.key == pygame.K_SPACE: 
                if not is_jumping:
                    velocity_y = jump_speed
                    is_jumping = True
                    # 게임오버가 아니고 스페이스 키가 눌렸을때 점프 스피드를 주고 점프중이라는 변수값을 True로 변경

    # 게임오버가 아닐 때만 게임 진행
    if not game_over:

        # 점프
        if is_jumping: 
            velocity_y += gravity   # 점점 숫자가 늘어야 아래로 향하는거임
            y_pos_sangsangbugi_side += velocity_y   # 상상부기의 위칫값이 그라운드에 섰을때까지

            if y_pos_sangsangbugi_side >= ground_y: # 상상부기 위치가 그라운드와 동일하거나 넘어가면
                y_pos_sangsangbugi_side = ground_y  # 그라운드 위치로 상상부기 위치를 맞춰줌
                velocity_y = 0                      # 그라운드에 있으니 속도를 0으로 초기화
                is_jumping = False                  # 점프가 완료됐으니 점프 상태를 False

        # 장애물 이동
        x_pos_hansungcat -= x_speed_hansungcat

        # 히트박스 갱신
        rect_sangsangbugi_side = sangsangbugi_side.get_rect(
            topleft=(x_pos_sangsangbugi_side,
                     y_pos_sangsangbugi_side))

        rect_hansungcat = hansungcat.get_rect(
            topleft=(x_pos_hansungcat,
                     y_pos_hansungcat))

        hitbox_sangsangbugi = rect_sangsangbugi_side.inflate(-40, -40)
        hitbox_hansungcat = rect_hansungcat.inflate(-50, -35)

        # 충돌
        if hitbox_sangsangbugi.colliderect(hitbox_hansungcat):
            game_over = True
        if (rect_sangsangbugi_side.left >= rect_hansungcat.right) and not passed:
            point += 10
            passed =True

        # 한성캣의 취이가 x값 -로 벗어나게 되면 화면을 벗어난거임
        # 그러면 한성캣의 좌표를 다시 오른쪽 화면 밖 좌표값으로 초기화해줘서 마치 재등장한것처럼 만들어주면됨
        if x_pos_hansungcat + new_width_hansungcat < 0 : 
            x_pos_hansungcat = size_bg_width
            passed = False


    # 배경
    background.blit(stage_1, (0,0))

    # 캐릭터
    background.blit(hansungcat,
                    (x_pos_hansungcat, y_pos_hansungcat))

    background.blit(sangsangbugi_side,
                    (x_pos_sangsangbugi_side, y_pos_sangsangbugi_side))

    # 점수
    text_point = font_point.render(str(point), True, (0,0,0))
    background.blit(text_point, (10,10))

    # 게임오버 글자 / 재시작 메세지
    if game_over:
        background.blit(text_gameover,
                        (x_pos_text, y_pos_text))
        background.blit(text_press,
                        (x_pos_text+50, y_pos_text+80))
    # 배경의 순서는 HTML의 Z-index와 같음.차곡 차곡 쌓이니 그 위에 점수와 메세지를 얹어서 표현해줘야함
    # 이미지 갱신
    pygame.display.update()

pygame.quit()

# TODO
# 1. 장애물 여러 종류 추가
# 2. 장애물 랜덤 등장
# 3. 생존 시간 점수 + 장애물 통과 보너스
# 4. 일정 시간마다 속도 / 장애물 수 증가
# 5. 낮 -> 밤 배경 전환
# 6. PAUSE 기능 여부 고민
# 7. 웹 배포 구조 검토
# 8. 이미지의 움직임

