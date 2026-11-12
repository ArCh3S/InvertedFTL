# === ИМПОРТЫ ===
import os
import pygame
import numpy as np
import matplotlib.pyplot as plt

pygame.init()     # ЗАПУСК PYGAME

# === ДАНО ===
m = 0.1     # масса груза, кг.
L = 0.3     # длина палки, м.
g = 9.81    # ускорение свободного падения
b = 0.05    # трение
ro_lin = 0.104976
m_palki = ro_lin * L   # масса палки
J = m * L**2 + m_palki * L**2 / 3   # момент инерции
k1 = 5.0     # П-регулятор
k2 = 0.6    # Д-регулятор
k3 = 0.0     # И-регулятор
max_tau = 1.5 # максимальный момент
int_err = 0.0     # накопление ошибки
cx = 500     # центр по x
cy = 300     # центр по y
scale = 400     # масштаб
theta = np.radians(90)     # начальное положение
omega = 0.0     # угловая скорость
dt = 1/60        # 60 фпс
dt_phys = dt / 10  # чтобы ПИД не поехал, обновление ставим чаще, иначе начинается тряска
print(f"{J:.4f}")     # вывод момента инерции для проверки
height = 600     # высота
width = 1000     # ширина
screen = pygame.display.set_mode((width, height))     # параметры экрана
pygame.display.set_caption("InvertedPendFTL")    # название окна
font = pygame.font.SysFont("Orbitron", 22)    # шрифт
font2 = pygame.font.SysFont("Orbitron", 14)
clock = pygame.time.Clock()     # создание часов
running = True     # симуляция запущена заранее
paused = False     # пауза

papka = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plots")
os.makedirs(papka, exist_ok=True)

# === ЛОГИ ===
t_ist = []
theta_ist = []
omega_ist = []
usk_ist = []
tau_ist = []
t_tek = 0.0

# === СОХРАНЕНИЕ ГРАФИКОВ ===
def save_plots():
    if len(t_ist) < 2:
        return
    plt.figure(figsize=(10, 12))
    plt.subplot(4, 1, 1)
    plt.plot(t_ist, np.degrees(theta_ist), label="theta, grad", color='blue')
    plt.axhline(0, color='black', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.subplot(4, 1, 2)
    plt.plot(t_ist, omega_ist, label="omega, rad/s", color='red')
    plt.axhline(0, color='black', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.subplot(4, 1, 3)
    plt.plot(t_ist, usk_ist, label="usk, rad/s^2", color='green')
    plt.axhline(0, color='black', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.subplot(4, 1, 4)
    plt.plot(t_ist, tau_ist, label="tau, N*m", color='purple')
    plt.axhline(0, color='black', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.xlabel("vremya, s")
    plt.tight_layout()
    plt.savefig(os.path.join(papka, "latest_plot.png"))
    plt.close()

# === ОСНОВНОЙ ЦИКЛ ===
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:       # при нажатии крестика
            running = False                 # закрываем симуляцию
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:       # аналогично с ESC
            running = False                                                     # и закрыванием
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE: # аналогично с SPACE
            paused = not paused                                             # и остановкой
    if not paused:         # функция симуляции
        for j in range(10):     # 10 раз в цикл
            m_palki = ro_lin * L
            J = m * L**2 + m_palki * L**2 / 3       # заново считаем каждый раз, т.к. параметры могут меняться
            e = theta           # целевой угол
            int_err = np.clip(int_err + e * dt_phys, -1, 1)   # анти-виндап
            tau = np.clip(-k1 * e - k2 * omega - k3 * int_err, -max_tau, max_tau)     # лимиты
            if abs(theta) < 0.026 and abs(omega) < 0.1:
                tau = 0.0          # момент силы(управление)
            usk = (m * g * L * np.sin(theta) - b * omega + tau) / J     # ускорение
            omega = omega + usk * dt_phys           # угловая скорость
            theta = theta + omega * dt_phys         # угол
        # === ЗАПОЛНЕНИЕ ИСТОРИИ ===
        t_ist.append(t_tek)
        theta_ist.append(theta)
        omega_ist.append(omega)
        usk_ist.append(usk)
        tau_ist.append(tau)
        t_tek += dt
    # координаты груза и заполнение экрана
    screen.fill((255, 255, 255))
    x_k = cx - round(scale * L * np.sin(theta))
    y_k = cy - round(scale * L * np.cos(theta))
    # рисуем маятник
    pygame.draw.circle(screen, (40, 50, 60), (cx, cy), 10)
    pygame.draw.line(screen, (60, 70, 80), (cx, cy), (x_k, y_k), 5)
    pygame.draw.circle(screen, (80, 90, 100), (x_k, y_k), 15)
    # проверка существования точек и данные для графиков с рамкой
    if len(t_ist) > 1:
        graph_rect = pygame.Rect(600, 50, 350, 500)
        pygame.draw.rect(screen, (235, 235, 235), graph_rect)
        pygame.draw.rect(screen, (40, 50, 60), graph_rect, 2)
        okno = max(t_ist[-1] - t_ist[0], 1.0)
        # чтобы не было ошибок при 0 и определение максимумов
        maks_t = 1.0     # максимальный угол
        maks_o = 1.0     # максимальная угловая скорость
        maks_u = 1.0
        maks_tau = 0.1
        for i in range(len(t_ist)):
            if abs(np.degrees(theta_ist[i])) > maks_t:
                maks_t = abs(np.degrees(theta_ist[i]))
            if abs(omega_ist[i]) > maks_o:
                maks_o = abs(omega_ist[i])
            if abs(usk_ist[i]) > maks_u:
                maks_u = abs(usk_ist[i])
            if abs(tau_ist[i]) > maks_tau:
                maks_tau = abs(tau_ist[i])
        # масштаб(шкала)
        shk_t = 720
        for s in [2, 5, 10, 20, 45, 90, 180, 360, 720]:
            if s >= maks_t:
                shk_t = s
                break
        shk_o = 50
        for s in [1, 2, 5, 10, 20, 50]:
            if s >= maks_o:
                shk_o = s
                break
        shk_u = 500
        for s in [5, 10, 20, 50, 100, 200, 500]:
            if s >= maks_u:
                shk_u = s
                break
        shk_tau = 3
        for s in [0.5, 1, 1.5, 2, 3]:
            if s >= maks_tau:
                shk_tau = s
                break
        pygame.draw.line(screen, (120, 120, 120), (600, 112), (950, 112), 1)   # нули
        pygame.draw.line(screen, (120, 120, 120), (600, 237), (950, 237), 1)
        pygame.draw.line(screen, (120, 120, 120), (600, 362), (950, 362), 1)
        pygame.draw.line(screen, (120, 120, 120), (600, 487), (950, 487), 1)
        pts_t = []
        pts_o = []
        pts_u = []
        pts_tau = []
        for i in range(len(t_ist)):
            x_graf = 600 + int((t_ist[i] - t_ist[0]) / okno * 350)
            y_t = 112 - int(np.degrees(theta_ist[i]) / shk_t * 50)
            y_o = 237 - int(omega_ist[i] / shk_o * 50)
            y_u = 362 - int(usk_ist[i] / shk_u * 50)
            y_tau = 487 - int(tau_ist[i] / shk_tau * 50)
            pts_t.append((x_graf, y_t))
            pts_o.append((x_graf, y_o))
            pts_u.append((x_graf, y_u))
            pts_tau.append((x_graf, y_tau))
        screen.set_clip(graph_rect)
        if len(pts_t) > 1:
            pygame.draw.lines(screen, (30, 90, 200), False, pts_t, 2)
            pygame.draw.lines(screen, (200, 60, 60), False, pts_o, 2)
            pygame.draw.lines(screen, (60, 160, 60), False, pts_u, 2)
            pygame.draw.lines(screen, (160, 60, 160), False, pts_tau, 2)
        screen.set_clip(None)
        lab1 = font2.render("theta, deg +/-" + str(shk_t), True, (30, 90, 200))
        lab2 = font2.render("omega, rad/s +/-" + str(shk_o), True, (200, 60, 60))
        lab3 = font2.render("usk, rad/s^2 +/-" + str(shk_u), True, (60, 160, 60))
        lab4 = font2.render("tau, N*m +/-" + str(shk_tau), True, (160, 60, 160))
        lab_t = font2.render("t, s: 0..." + str(round(okno, 1)), True, (0, 0, 0))
        screen.blit(lab1, (605, 62))
        screen.blit(lab2, (605, 187))
        screen.blit(lab3, (605, 312))
        screen.blit(lab4, (605, 437))
        screen.blit(lab_t, (605, 555))
    theta_str = "Theta: " + str(round(np.degrees(theta), 2)) + " deg"
    tau_str = "Tau: " + str(round(tau, 3)) + " N*m"
    tekst1 = font.render(theta_str, True, (0, 0, 0))
    tekst2 = font.render(tau_str, True, (0, 0, 0))
    screen.blit(tekst1, (20, 20))
    screen.blit(tekst2, (20, 50))
    if paused:
        tekst3 = font.render("PAUZA", True, (200, 60, 60))
        screen.blit(tekst3, (20, 80))
    pygame.display.flip()
    clock.tick(60)
save_plots()
pygame.quit()