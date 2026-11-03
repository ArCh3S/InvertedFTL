import pygame
import numpy as np
import matplotlib.pyplot as plt

m = 0.1     # масса груза, кг.
L = 0.3     # длина палки, м.
g = 9.81    # ускорение свободного падения
b = 0.05    # трение
m_palki = 0   # масса палки
J = m * L**2 + m_palki * L**2 / 3   # момент инерции
k1 = 2     # П-регулятор
k2 = 1.5    # Д-регулятор
k3 = 0     # И-регулятор
max_tau = 1.5 # максимальный момент
int_err = 0     # накопление ошибки
cx = 500
cy = 300
scale = 400
theta = np.radians(90)

dt = 1/60        # 60 фпс
dt_phys = dt / 10  # чтобы ПИД не поехал

print(f"{J:.4f}")

pygame.init()

height = 600     # высота
width = 1000 # ширина
parameters = np.array([width, height])
screen = pygame.display.set_mode(parameters)
pygame.display.set_caption("InvertedFLT")

clock = pygame.time.Clock()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
    screen.fill((255, 255, 255))
    x_k = cx - round(scale * L * np.sin(theta))
    y_k = cy - round(scale * L * np.cos(theta))
    
    pygame.draw.circle(screen, (40, 50, 60), (cx, cy), 10)
    pygame.draw.line(screen, (60, 70, 80), (cx, cy), (x_k, y_k), 5)
    pygame.draw.circle(screen, (80, 90, 100), (x_k, y_k), 15)
    
    pygame.display.flip()
    clock.tick(60)
pygame.quit()