import pygame

pygame.init()

background = pygame.display.set_mode((480,360))
pygame.display.set_caption("hansungrun")

play = True

x_pos = background.get_size()[0]//2
y_pos = background.get_size()[1]//2

while play:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            play = False
        
        if event.type == pygame.MOUSEMOTION:
            x_pos,y_pos = pygame.mouse.get_pos()
            pygame.draw.circle(background,(255,0,255),(x_pos,y_pos),10) 
        if event.type == pygame.MOUSEBUTTONDOWN:
            background.fill((0,0,0))

    # background.fill((0,0,0))   
    # pygame.draw.circle(background,(255,0,255),(x_pos,y_pos),10) 

    pygame.display.update()

    # 위치에 따라서 어떻게 되는지를 잘 이해해야 한다
    # 마우스의 이동이 있을때 그리고 클릭시에 지우고
    # 아래의 주석처리 부분을 넣고 마우스의 모션이 있을때 좌표값만 가지고 있고
    # 모션다운이 사라지고 for안에 그리고 지우고가 있으면
    # 하나의 원이 지우고 그려지면서 마치 마우스를 따라 오는것처럼 보임

pygame.quit()
