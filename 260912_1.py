import pygame

pygame.init()

to_x = 0 
to_y = 0

background = pygame.display.set_mode((480,360))
pygame.display.set_caption("Hansungrun")

fps = pygame.time.Clock()

x_pos = background.get_size()[0]//2
y_pos = background.get_size()[1]//2

play=True
while play:
    deltatime =fps.tick(60)

    for event in pygame.event.get():
        print(event.type)
        if event.type == pygame.QUIT:
          play = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                to_y = -1
            elif event.key == pygame.K_DOWN:
                to_y = 1
            elif event.key == pygame.K_RIGHT:
                to_x = 1
            elif event.key == pygame.K_LEFT:
                to_x = -1

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_UP:
                to_y = 0
            elif event.key == pygame.K_DOWN:
                to_y = 0
            elif event.key == pygame.K_RIGHT:
                to_x = 0
            elif event.key == pygame.K_LEFT:
                to_x = 0

    x_pos += to_x
    y_pos += to_y

    background.fill((255,255,255))
    pygame.draw.circle(background,(0,0,0),(x_pos,y_pos),5)
    pygame.display.update()

pygame.quit()