import pygame
import numpy as np
import matplotlib.pyplot as plt

# === ФИЗИЧЕСКИЕ КОНСТАНТЫ ===
m = 0.1     # масса груза, кг.
L = 0.3     # длина палки, м.
g = 9.81    # ускорение свободного падения
b = 0.05    # трение

m_palki = 0.0   # масса палки
J = m * L**2 + m_palki * L**2 / 3   # момент инерции
print(f"Проверка J: {J:.4f} (должно быть 0.0090)")

k1 = 2     # П-регулятор
k2 = 1.5    # Д-регулятор
k3 = 0     # И-регулятор
max_tau = 1.5
int_err = 0.0

dt = 1/60        # 60 фпс
dt_phys = dt / 10  # микрошаг, чтобы ПИД не разваливался

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
    pygame.display.flip()
    clock.tick(60)
pygame.quit()