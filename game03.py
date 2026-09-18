import pygame

pygame.init()

background = pygame.display.set_mode((480,360))
pygame.display.set_caption("hansungrun")

play = True

x = background.get_size()[0]//2
y = background.get_size()[1]//2

while play:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            play = False

    background.fill((255,255,255))

    # pygame.draw.line(background, (0,0,0), (240,0), (240,360),3)
    # pygame.draw.line(background, (0,0,0), (0,180), (480,180),3)
    
    # pygame.draw.line(background, (0,0,0), (0,0), (480,360),5)
    # pygame.draw.line(background, (0,0,0), (0,360), (480,0),5)
    
    # for i in range(0,480,30):
    #     pygame.draw.line(background, (0,0,0), (i,0), (i,360))
    # for i in range(0,360,30):
    #     pygame.draw.line(background, (0,0,0), (0,i), (480,i))
    
    # pygame.draw.circle(background,(255,0,0), (240,180),50,5)
    # pygame.draw.rect(background,(0,255,0),(240,180,100,50),5)
    # pygame.draw.ellipse(background,(0,255,0),(100,200,100,50),5)
    
    pygame.draw.polygon(background, (255,255,0), ((146,0),(291,106),(236,277),(56,277),(0,106)),10)

    pygame.draw.line(background, (0,0,0), (x,0),(x,y*2))
    pygame.draw.line(background, (0,0,0), (0,y),(x*2,y))

    pygame.display.update()

pygame.quit()
    
