import numpy as np
import matplotlib.pyplot as plt
import pygame
pygame.init()

g = 9.81
l = 0.4    # длина стержня
m_gr = 0.05 # масса груза
m_sh = 0.042    # масса штанги
b = 0.05    # трение
J = m_gr * l**2 + m_sh * l**2 / 3   # момент инерции
k1 = 2     # П-регулятор
k2 = 1.5    # Д-регулятор
k3 = 0     # И-регулятор
max_tau = 1.5 # максимальный момент
int_err = 0     # накопление ошибки
omega = 0
theta = np.radians(180)

dt = 1 / 60 # 60 фпс
dt_ph = dt / 10     # чтобы не было разрывов в ПИДе

width = 1000
height  = 600
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption('InvertedPendulumFLT')
cx = 500
cy = 300
scale = 400

print(f"{J:.4f}")

clock = pygame.time.Clock()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False 
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
    screen.fill(0, 0, 0)
    pygame.display.flip()
    clock.tick(60)
