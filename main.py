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
omega = 0.0

dt = 1/60        # 60 фпс
dt_phys = dt / 10  # чтобы ПИД не поехал

print(f"{J:.4f}")

pygame.init()

height = 600     # высота
width = 1000 # ширина
parameters = np.array([width, height])
screen = pygame.display.set_mode(parameters)
pygame.display.set_caption("InvertedPendFTL")
font = pygame.font.SysFont("Arial", 22)

clock = pygame.time.Clock()
running = True
paused = False

t_ist = []
theta_ist = []
omega_ist = []
tau_ist = []
t_tek = 0.0

def save_plots():
    if len(t_ist) < 2:
        return
    plt.figure(figsize=(12, 5))
    plt.subplot(1, 2, 1)
    plt.plot(t_ist, np.degrees(theta_ist), label="theta, grad", color='blue')
    plt.axhline(0, color='black', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.subplot(1, 2, 2)
    plt.plot(t_ist, omega_ist, label="omega, rad/s", color='red')
    plt.axhline(0, color='black', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.savefig("plots/latest_plot.png")
    plt.close()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            paused = not paused
    if not paused:
        for j in range(10):
            J = m * L**2 + m_palki * L**2 / 3
            e = theta
            int_err = np.clip(int_err + e * dt_phys, -1, 1)   # анти-виндап
            tau = np.clip(-k1 * e - k2 * omega - k3 * int_err, -max_tau, max_tau)
            if abs(theta) < 0.026 and abs(omega) < 0.1:
                tau = 0.0
            viz = (m * g * L * np.sin(theta) - b * omega + tau) / J
            omega = omega + viz * dt_phys
            theta = theta + omega * dt_phys
        t_ist.append(t_tek)
        theta_ist.append(theta)
        omega_ist.append(omega)
        tau_ist.append(tau)
        t_tek += dt

    screen.fill((255, 255, 255))
    x_k = cx - round(scale * L * np.sin(theta))
    y_k = cy - round(scale * L * np.cos(theta))

    pygame.draw.circle(screen, (40, 50, 60), (cx, cy), 10)
    pygame.draw.line(screen, (60, 70, 80), (cx, cy), (x_k, y_k), 5)
    pygame.draw.circle(screen, (80, 90, 100), (x_k, y_k), 15)

    if len(t_ist) > 1:
        graph_rect = pygame.Rect(600, 50, 350, 500)
        pygame.draw.rect(screen, (235, 235, 235), graph_rect)
        pygame.draw.rect(screen, (40, 50, 60), graph_rect, 2)
        t_min = t_ist[-1] - 5.0
        start_idx = 0
        for i in range(len(t_ist)):
            if t_ist[i] >= t_min:
                start_idx = i
                break

        maks_t = 1.0
        maks_o = 1.0
        for i in range(start_idx, len(t_ist)):
            if abs(np.degrees(theta_ist[i])) > maks_t:
                maks_t = abs(np.degrees(theta_ist[i]))
            if abs(omega_ist[i]) > maks_o:
                maks_o = abs(omega_ist[i])

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

        pygame.draw.line(screen, (120, 120, 120), (600, 150), (950, 150), 1)   # нули
        pygame.draw.line(screen, (120, 120, 120), (600, 450), (950, 450), 1)

        pts_t = []
        pts_o = []
        for i in range(start_idx, len(t_ist)):
            x_graf = 600 + int((t_ist[i] - t_min) / 5.0 * 350)
            y_t = 150 - int(np.degrees(theta_ist[i]) / shk_t * 100)
            y_o = 450 - int(omega_ist[i] / shk_o * 100)
            pts_t.append((x_graf, y_t))
            pts_o.append((x_graf, y_o))

        screen.set_clip(graph_rect)
        if len(pts_t) > 1:
            pygame.draw.lines(screen, (30, 90, 200), False, pts_t, 2)
            pygame.draw.lines(screen, (200, 60, 60), False, pts_o, 2)
        screen.set_clip(None)

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