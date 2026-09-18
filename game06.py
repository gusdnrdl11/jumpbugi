import pygame

pygame.init()


background = pygame.display.set_mode((480,360))
pygame.display.set_caption("Hansungrun")

fps = pygame.time.Clock()

# image_bg = pygame.image.load() 배경인데 배경은 안넣음 상대경로로 줘야 다른컴퓨터에서도 프로젝트가 실행됨 "image/sangsangbugi.png"
hansungcat = pygame.image.load("image/hansungcat.png").convert_alpha()

# 배경의 가로 세로를 가져와옴
size_bg_width = background.get_size()[0]    
size_bg_height = background.get_size()[1]

# 이미지 크기 조절
original_width = hansungcat.get_width()
original_height = hansungcat.get_height()

# 높이(120) 기준으로 가로 비율을 조절함
new_height = 120
new_width = int(original_width * new_height / original_height)   

hansungcat = pygame.transform.smoothscale(
    hansungcat,
    (new_width, new_height))

GROUND_OFFSET = 7

# 한성캣 위치
x_pos_hansungcat = size_bg_width# 중요한 개념 게임의 좌표평면은 좌측 상단이 0,0임 / 지금 좌측 상단 0,0 기준으로 보면 이미지는 외부에 있음
y_pos_hansungcat = size_bg_height - ((size_bg_height//3) - 7)
# y 축의 값이 내려가야 증가 / 위로 올라가면 감소 즉 전체 배경 360(바닥면)에서 한성부기의 이미지 좌측상단의 크기를 빼주면됨
# 단 이미지의 모양에 따라 바닥면에 딱 붙게 하기 위해서 약간의 보정값이 필요함 그게 바로 저 GROUND_OFFSET임

x_speed_hansungcat = 2

play = True
entered_screen = False

while play:
    deltatime =fps.tick(60) # fps 조절 (스피드 조절)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            play = False
    x_pos_hansungcat -= x_speed_hansungcat

    if x_pos_hansungcat <= size_bg_width - new_width: 
        entered_screen = True
    # x_pos_hansungcat은 480 x 맥스값임
    # size_bg_width - new_width 는 한성캣이 정상적으로 내부로 이미지가 들어왔는지 확인해주는거임 480 - 한성캣의 이미지 크기(좌측상단기준)
    # 정상적으로 이미지가 내부로 들어왔다 size_bg_width - new_width 를 기준으로 판단하고 상태 변수를 True로 변경

    if x_pos_hansungcat <= 0:  # x좌표 즉 왼쪽 기준점으로 빠져나가지 않게 만드는건데 나는 빠져나가야함
        x_pos_hansungcat = 0
        x_speed_hansungcat = -x_speed_hansungcat 

    if entered_screen:  
        if x_pos_hansungcat >= size_bg_width - new_width:
            x_pos_hansungcat = size_bg_width - new_width
            x_speed_hansungcat = -x_speed_hansungcat
    # 기존 코드에서 내부로 위치를 고정시켜 버림
    # 내가 하고 싶었던건 이미지를 외부에서 시작해서 들어오게 만들고 내부로 들어왔을때 튕기게 만드는 구조
    # 내부에 상태변수를 두고 외부에서 아직 들어오지 않았다는 False값으로 초기화 시켜주고 
    # 내부로 들어왔을때 True로 변경 해준다음 그 값을 검사해서 한성캣의 오른쪽에서 튕기게 만들어주면 됨
                 
   
    # x,y축의 범위를 벗어나려고 그 범위 안으로 제한을 둘때 맥스 좌표값으로 갈 경우 양수를 음수로 음수를 양수로 맥스값에서 스피드를 조절하면 반대로감 
    
    # if x_pos_hansungcat + new_width >= size_bg_width:      한성캣의 이미지 너비는 왼쪽 상단을 기준으로 함 즉 x축 좌표 - 한성캣 이미지 크기
    #         x_pos_hansungcat = size_bg_width - new_width   를 뺀값을 넘어가려고 하면 화면을 벗어나려고 하는거임 넘어가지 못하게 고정해주자
    # 다만 이 코드는 오른쪽으로 이동할 가능성이 없기 때문에 예시만 줬음 / 장애물이 설정 위치값에서 왼쯕으로만 이동한다는 가정이 이미 되있음
    # 왼쪽으로 쭉 이동한 이미지가 경계값을 모두 이미지 크기만큼 벗어나게 되면 삭제하는 식으로 가면 될거 같음
        


    # 생각해봐야할것 좌측으로는 빠져나가야 하지만 우측으로는 빠져 나가면 안됨
    # y측 좌표는 모두 빠져 나가면 안됨
        
    # 배경 깔기
    # background.blit(사용할 배경,(0,0)) 여기선 배경을 안쓰고 그냥 투명한 색으로 채워만 놓음
    background.fill((255, 255, 255))

    # 한성캣 그리기
    background.blit(hansungcat,(x_pos_hansungcat, y_pos_hansungcat))  
    pygame.display.update()

pygame.quit()

