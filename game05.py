import pygame

pygame.init()


background = pygame.display.set_mode((480,360))
pygame.display.set_caption("Hansungrun")

fps = pygame.time.Clock()

# image_bg = pygame.image.load() 배경인데 배경은 안넣음 상대경로로 줘야 다른컴퓨터에서도 프로젝트가 실행됨 "image/sangsangbugi.png"
image_sangsangbugi_side = pygame.image.load("image/sangsangbugi_side.png").convert_alpha()

# 배경의 가로 세로를 가져와옴
size_bg_width = background.get_size()[0]    
size_bg_height = background.get_size()[1]

# 이미지 크기 조절
original_width = image_sangsangbugi_side.get_width()
original_height = image_sangsangbugi_side.get_height()

# 높이(120) 기준으로 가로 비율을 조절함
new_height = 120
new_width = int(original_width * new_height / original_height)   

image_sangsangbugi_side = pygame.transform.smoothscale(
    image_sangsangbugi_side,
    (new_width, new_height))


GROUND_OFFSET = 7  # 상상부기를 바닥에 딱 붙이기 위해서 주는 보정값

# 상상부기 위치
x_pos_sangsangbugi_side = 0 # 중요한 개념 게임의 좌표평면은 좌측 상단이 0,0임
y_pos_sangsangbugi_side = size_bg_height - new_height 
# 왼쪽 끝이 좌표평면의 0,0에 있는거임! 
# y 축의 값이 내려가야 증가 / 위로 올라가면 감소 즉 전체 배경 360(바닥면)에서 한성부기의 이미지 좌측상단의 크기를 빼주면됨
# 단 이미지의 모양에 따라 바닥면에 딱 붙게 하기 위해서 약간의 보정값이 필요함 그게 바로 저 GROUND_OFFSET임

to_x = 0 
to_y = 0

play = True

while play:
    deltatime =fps.tick(60) # fps 조절 (스피드 조절)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            play = False
        if event.type == pygame.KEYDOWN: # 키의 상태를 키 다운 / 키 업으로 구분해서 사용
            if event.key == pygame.K_UP:
                to_y = -4
            elif event.key == pygame.K_DOWN:
                to_y = 4
            elif event.key == pygame.K_RIGHT:
                to_x = 4
            elif event.key == pygame.K_LEFT:
                to_x = -4

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_UP:
                to_y = 0
            elif event.key == pygame.K_DOWN:
                to_y = 0
            elif event.key == pygame.K_RIGHT:
                to_x = 0
            elif event.key == pygame.K_LEFT:
                to_x = 0

    # 한성부기를 움직이자
    x_pos_sangsangbugi_side += to_x
    y_pos_sangsangbugi_side += to_y

    # 배경 깔기
    # background.blit(사용할 배경,(0,0)) 여기선 배경을 안쓰고 그냥 투명한 색으로 채워만 놓음
    background.fill((255, 255, 255))

    # 한성부기 그리기
    background.blit(image_sangsangbugi_side,(x_pos_sangsangbugi_side, y_pos_sangsangbugi_side))  

    pygame.display.update()

pygame.quit()


