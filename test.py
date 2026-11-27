# === ИМПОРТЫ ===
import os                   # модуль для работы с файловой системой
import pygame               # библиотека для создания окна и отрисовки
import numpy as np          # библиотека для математических расчётов
import matplotlib.pyplot as plt  # библиотека для построения графиков

pygame.init()     # ЗАПУСК PYGAME

# === ДАНО (ПАРАМЕТРЫ ИЗ ДОКУМЕНТАЦИИ) ===
m = 0.05    # масса груза (4 подшипника), кг
L = 0.4     # длина плеча (штанги), м
g = 9.81    # ускорение свободного падения, м/с^2
b = 0.003   # коэффициент вязкого трения в оси, Н*м*с/рад
rho_lin = 0.104976          # распределённая линейная плотность штанги, кг/м
m_rod = rho_lin * L         # масса штанги (0.042 кг при L=0.4 м)
J = m * L**2 + (1.0 / 3.0) * m_rod * L**2   # суммарный момент инерции J_Sigma

# === МАТЕМАТИЧЕСКАЯ МОДЕЛЬ МОТОРА JGB37-520 + ARDUINO ===
U_max = 12.0        # максимальное напряжение питания драйвера мотора, В
U_ard = 4.8         # рабочее управляющее напряжение с Arduino (4-5 Вольт)
R_a = 5.0           # активное сопротивление обмотки якоря, Ом
N_gear = 17.0       # передаточное число редуктора N (1:17)
eta_gear = 0.80     # КПД редуктора eta
K_e = 0.021         # коэффициент противо-ЭДС моторчика до редуктора, В/(рад/с)
K_t = 0.021         # коэффициент крутящего момента моторчика до редуктора, Н*м/А

# === ПАРАМЕТРЫ КОНТРОЛЛЕРА (П-РЕГУЛЯТОР ПО ЭНЕРГИИ + П/ПД ПО УГЛУ В +/- 15 ГРАД) ===
k_swing = 5.0                   # нормированный коэффициент П-регулятора по энергии (4-5 В)
switch_ang = np.radians(15.0)   # переход в регулятор по углу строго при +/- 15 градусах
k1 = 85.0           # П-регулятор по углу (В / рад)
k2 = 14.0           # Д-регулятор по угловой скорости (В / (рад/с))
k3 = 0.0            # И-регулятор
int_err = 0.0       # накопление интегральной ошибки

# === НАЧАЛЬНОЕ СОСТОЯНИЕ И ЭКРАН ===
cx = 500     # центр по x
cy = 300     # центр по y
scale = 350  # масштаб отрисовки
theta = np.radians(180.0)   # старт строго из нижнего положения покоя (180 градусов)
omega = 0.0     # начальная угловая скорость, рад/с
acc = 0.0       # угловое ускорение, рад/с^2
tau = 0.0       # крутящий момент мотора на выходном валу, Н*м
U = 0.0         # управляющее напряжение на моторе, В
I_curr = 0.0    # ток в обмотке якоря, А
E_curr_val = 0.0 # текущая энергия для отображения
E_star_val = 0.0 # целевая энергия E* для отображения
mode = "SWING-UP"   # режим контроллера

dt = 1/60          # 60 фпс
dt_phys = dt / 10  # шаг численного интегрирования физики
print(f"J_Sigma = {J:.5f} kg*m^2")

height = 600     # высота окна
width = 1000     # ширина окна
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("InvertedPendFTL - JGB37-520 + Arduino (4-5V Swing-Up)")
font = pygame.font.SysFont("Orbitron", 19)    # основной шрифт интерфейса
font2 = pygame.font.SysFont("Orbitron", 14)   # шрифт графиков
clock = pygame.time.Clock()
running = True
paused = False

# создание папки plots рядом со скриптом для сохранения графиков
folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plots")
os.makedirs(folder, exist_ok=True)

# === СЛАЙДЕРЫ ===
trk_L = pygame.Rect(20, 190, 200, 8)    # дорожка длины L
hnd_L = pygame.Rect(20, 182, 12, 24)    # ручка длины L
trk_m = pygame.Rect(20, 240, 200, 8)    # дорожка массы m
hnd_m = pygame.Rect(20, 232, 12, 24)    # ручка массы m
trk_b = pygame.Rect(20, 290, 200, 8)    # дорожка трения b
hnd_b = pygame.Rect(20, 282, 12, 24)    # ручка трения b
btn_r = pygame.Rect(20, 340, 120, 40)   # кнопка перезапуска RESTART
drag = None     # какую ручку сейчас тащим: None/L/m/b

def getval(trk, hnd, vmin, vmax):
    """позиция ручки -> значение параметра"""
    return vmin + (hnd.x - trk.x) / (trk.w - hnd.w) * (vmax - vmin)

def setpos(trk, hnd, vmin, vmax, val):
    """значение параметра -> позиция ручки"""
    hnd.x = trk.x + int((val - vmin) / (vmax - vmin) * (trk.w - hnd.w))

setpos(trk_L, hnd_L, 0.1, 0.6, L)
setpos(trk_m, hnd_m, 0.02, 0.2, m)
setpos(trk_b, hnd_b, 0.0, 0.05, b)

# === ФУНКЦИЯ МОДЕЛИ МОТОРА JGB37-520 (Формулы 1-2 из описания мотора) ===
def motor_dynamics(U_in, omega_out):
    """
    Вычисляет крутящий момент на выходе редуктора M_out и ток I по поданному напряжению U_in:
    1) omega_m = omega_out * N
    2) E = K_e * omega_m (противо-ЭДС)
    3) U = I * R + E  =>  I = (U - E) / R
    4) M = K_t * I
    5) M_out = M * N * eta
    """
    omega_m = omega_out * N_gear            # скорость вращения вала самого моторчика
    E_emf = K_e * omega_m                   # противо-ЭДС
    I = (U_in - E_emf) / R_a                # ток якоря
    M_rotor = K_t * I                       # электромагнитный момент ротора
    M_out = M_rotor * N_gear * eta_gear     # момент на выходном валу после редуктора
    return M_out, I

# === ЛОГИ ===
t_hist = []         # история времени
theta_hist = []     # история угла
omega_hist = []     # история угловой скорости
acc_hist = []       # история углового ускорения
u_hist = []         # история напряжения U
t_curr = 0.0        # текущее время

# === СОХРАНЕНИЕ ГРАФИКОВ ===
def save_plots():
    if len(t_hist) < 2:
        return
    plt.figure(figsize=(10, 12))
    plt.subplot(4, 1, 1)
    plt.plot(t_hist, np.degrees(theta_hist), label="theta, deg", color='blue')
    plt.axhline(0, color='black', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.subplot(4, 1, 2)
    plt.plot(t_hist, omega_hist, label="omega, rad/s", color='red')
    plt.axhline(0, color='black', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.subplot(4, 1, 3)
    plt.plot(t_hist, acc_hist, label="acc, rad/s^2", color='green')
    plt.axhline(0, color='black', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.subplot(4, 1, 4)
    plt.plot(t_hist, u_hist, label="U, Volts", color='purple')
    plt.axhline(0, color='black', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.xlabel("time, s")
    plt.tight_layout()
    plt.savefig(os.path.join(folder, "latest_plot.png"))
    plt.close()

# === ОСНОВНОЙ ЦИКЛ ===
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            paused = not paused
        if event.type == pygame.MOUSEBUTTONDOWN:
            if hnd_L.collidepoint(event.pos):
                drag = "L"
            elif hnd_m.collidepoint(event.pos):
                drag = "m"
            elif hnd_b.collidepoint(event.pos):
                drag = "b"
            elif btn_r.collidepoint(event.pos):
                theta = np.radians(180.0)   # сброс в нижнюю точку (180 град)
                omega = 0.0
                int_err = 0.0
                t_hist.clear()
                theta_hist.clear()
                omega_hist.clear()
                acc_hist.clear()
                u_hist.clear()
                t_curr = 0.0
        if event.type == pygame.MOUSEMOTION and drag is not None:
            if drag == "L":
                hnd_L.x = min(max(event.pos[0] - 6, trk_L.x), trk_L.x + trk_L.w - hnd_L.w)
                L = round(getval(trk_L, hnd_L, 0.1, 0.6) / 0.05) * 0.05
                setpos(trk_L, hnd_L, 0.1, 0.6, L)
            if drag == "m":
                hnd_m.x = min(max(event.pos[0] - 6, trk_m.x), trk_m.x + trk_m.w - hnd_m.w)
                m = round(getval(trk_m, hnd_m, 0.02, 0.2) / 0.01) * 0.01
                setpos(trk_m, hnd_m, 0.02, 0.2, m)
            if drag == "b":
                hnd_b.x = min(max(event.pos[0] - 6, trk_b.x), trk_b.x + trk_b.w - hnd_b.w)
                b = round(getval(trk_b, hnd_b, 0.0, 0.05) / 0.002) * 0.002
                setpos(trk_b, hnd_b, 0.0, 0.05, b)
        if event.type == pygame.MOUSEBUTTONUP:
            drag = None

    if not paused:
        for j in range(10):     # 10 подшагов численного интегрирования за кадр
            m_rod = rho_lin * L                                 # масса штанги m_p(L) = 0.104976 * L
            J = m * L**2 + (1.0 / 3.0) * m_rod * L**2           # момент инерции J_Sigma (Формула 4)
            M_grav_max = (m * L + m_rod * (L / 2.0)) * g        # максимальный момент тяжести (Формула 2)

            # --- ЧИСЛЕННОЕ ИНТЕГРИРОВАНИЕ МЕТОДОМ LEAPFROG ---
            # 1. Полушаг координаты (дрейф)
            theta_half = theta + 0.5 * omega * dt_phys
            # Приводим угол к интервалу [-pi, pi], где 0 — верхнее равновесие, +/-pi — нижнее
            theta_norm = (theta_half + np.pi) % (2.0 * np.pi) - np.pi

            # Расчёт полной механической энергии по Формулам (1), (3), (5):
            E_kin = 0.5 * J * (omega ** 2)
            E_pot_inv = M_grav_max * (1.0 - np.cos(theta_norm)) # П(theta) из Формулы (1)
            E_star_val = 2.0 * M_grav_max                       # E* = 2 * M_тяж,макс из Формулы (3)
            
            # Текущий уровень энергии на траектории раскачки (от 0 внизу до E* вверху)
            E_curr_val = E_kin + (E_star_val - E_pot_inv)

            # Напряжение, необходимое мотору просто для преодоления собственной противо-ЭДС и трения оси b:
            # Без этой добавки при малом L=0.1м (где скорость высокая) противо-ЭДС (7 В) больше 4.5 В, и мотор тормозит!
            E_emf_comp = K_e * (omega * N_gear)
            U_fric_comp = (b * omega) / (K_t * N_gear * eta_gear) * R_a

            # 2. Переключение режимов: если угол в пределах +/- 15 градусов от 0 -> регулятор по углу
            if abs(theta_norm) <= switch_ang:
                # === СТАБИЛИЗАЦИЯ В ОКРЕСТНОСТИ +/- 15 ГРАДУСОВ ОТ ВЕРХНЕЙ ТОЧКИ ===
                mode = "ANGLE (<=15 deg)"
                deadzone = 0.012    # зона нечувствительности энкодера (~0.7 град)
                if abs(theta_norm) < deadzone:
                    e = 0.0
                    U = 0.0
                else:
                    e = theta_norm - np.sign(theta_norm) * deadzone
                    int_err = np.clip(int_err + e * dt_phys, -0.5, 0.5)
                    # Формула (10): П/ПД-регулятор по углу
                    U = -k1 * e - k2 * omega - k3 * int_err
            else:
                # === РАСКАЧКА ПО ЭНЕРГИИ (SWING-UP CONTROL, когда угол вне +/- 15 градусов) ===
                mode = "SWING-UP (ENERGY)"
                int_err = 0.0
                # Если маятник стоит неподвижно в нижней точке на старте, даём стартовые 4.8 В с Arduino
                if abs(omega) < 1e-3 and abs(abs(theta_norm) - np.pi) < 0.05:
                    U = U_ard
                else:
                    # Нормированная ошибка энергии (E - E*) / E*, чтобы работало одинаково при любых m и L!
                    E_err_norm = (E_curr_val - E_star_val) / max(E_star_val, 1e-5)
                    direction = np.sign(omega) if abs(omega) > 1e-4 else -np.sign(theta_norm)

                    # Формула (7): U_swing = -k * (E - E*) * sign(omega)
                    # Пока энергия меньше целевой E*, подаём 4-5 Вольт управляющего сигнала Arduino
                    if E_err_norm < 0:
                        U_drive = max(-k_swing * E_err_norm, U_ard) * direction
                        # Добавляем компенсацию противо-ЭДС и трения, чтобы при L=0.1м и m=0.02кг мотор не тормозил
                        U = U_drive + E_emf_comp + U_fric_comp
                    else:
                        # Если энергии перекачали (E > E*), плавно притормаживаем
                        U = -k_swing * E_err_norm * direction

            # Ограничение напряжения питания драйвера мотора (+/- 12 В)
            U = float(np.clip(U, -U_max, U_max))

            # 3. Расчёт крутящего момента tau через электромеханическую модель мотора JGB37-520
            tau, I_curr = motor_dynamics(U, omega)

            # 4. Уравнение динамики маятника (Формула 1): J * acc = M_grav_max * sin(theta) - b * omega + tau
            acc = (M_grav_max * np.sin(theta_norm) - b * omega + tau) / J

            # 5. Полный шаг скорости (толчок) и завершающий полушаг координаты (дрейф)
            omega = omega + acc * dt_phys
            theta = theta_half + 0.5 * omega * dt_phys
            theta = (theta + np.pi) % (2.0 * np.pi) - np.pi

        # === ЗАПОЛНЕНИЕ ИСТОРИИ ===
        t_hist.append(t_curr)
        theta_hist.append(theta)
        omega_hist.append(omega)
        acc_hist.append(acc)
        u_hist.append(U)
        t_curr += dt

    # Очистка экрана и расчёт координат конца штанги
    screen.fill((255, 255, 255))
    x_end = cx - round(scale * L * np.sin(theta))
    y_end = cy - round(scale * L * np.cos(theta))

    # Отрисовка сектора захвата +/- 15 градусов
    x_left15 = cx - round(scale * L * np.sin(switch_ang))
    y_left15 = cy - round(scale * L * np.cos(switch_ang))
    x_right15 = cx - round(scale * L * np.sin(-switch_ang))
    y_right15 = cy - round(scale * L * np.cos(-switch_ang))
    pygame.draw.line(screen, (210, 230, 210), (cx, cy), (x_left15, y_left15), 2)
    pygame.draw.line(screen, (210, 230, 210), (cx, cy), (x_right15, y_right15), 2)

    # Отрисовка маятника
    pygame.draw.circle(screen, (40, 50, 60), (cx, cy), 10)
    pygame.draw.line(screen, (60, 70, 80), (cx, cy), (x_end, y_end), 5)
    pygame.draw.circle(screen, (80, 90, 100), (x_end, y_end), 15)

    # Отрисовка графиков
    if len(t_hist) > 1:
        graph_rect = pygame.Rect(600, 50, 350, 500)
        pygame.draw.rect(screen, (235, 235, 235), graph_rect)
        pygame.draw.rect(screen, (40, 50, 60), graph_rect, 2)
        window = max(t_hist[-1] - t_hist[0], 1.0)

        max_t, max_o, max_a, max_u_h = 1.0, 1.0, 1.0, 1.0
        for i in range(len(t_hist)):
            if abs(np.degrees(theta_hist[i])) > max_t:
                max_t = abs(np.degrees(theta_hist[i]))
            if abs(omega_hist[i]) > max_o:
                max_o = abs(omega_hist[i])
            if abs(acc_hist[i]) > max_a:
                max_a = abs(acc_hist[i])
            if abs(u_hist[i]) > max_u_h:
                max_u_h = abs(u_hist[i])

        scale_t = 180
        for s in [5, 15, 45, 90, 180, 360]:
            if s >= max_t:
                scale_t = s
                break
        scale_o = 50
        for s in [2, 5, 10, 15, 20, 50]:
            if s >= max_o:
                scale_o = s
                break
        scale_a = 500
        for s in [10, 20, 50, 100, 200, 500]:
            if s >= max_a:
                scale_a = s
                break
        scale_u = 12

        pygame.draw.line(screen, (120, 120, 120), (600, 112), (950, 112), 1)
        pygame.draw.line(screen, (120, 120, 120), (600, 237), (950, 237), 1)
        pygame.draw.line(screen, (120, 120, 120), (600, 362), (950, 362), 1)
        pygame.draw.line(screen, (120, 120, 120), (600, 487), (950, 487), 1)

        pts_t, pts_o, pts_a, pts_u = [], [], [], []
        for i in range(len(t_hist)):
            x_graph = 600 + int((t_hist[i] - t_hist[0]) / window * 350)
            y_t = 112 - int(np.degrees(theta_hist[i]) / scale_t * 50)
            y_o = 237 - int(omega_hist[i] / scale_o * 50)
            y_a = 362 - int(acc_hist[i] / scale_a * 50)
            y_u = 487 - int(u_hist[i] / scale_u * 50)
            pts_t.append((x_graph, y_t))
            pts_o.append((x_graph, y_o))
            pts_a.append((x_graph, y_a))
            pts_u.append((x_graph, y_u))

        screen.set_clip(graph_rect)
        if len(pts_t) > 1:
            pygame.draw.lines(screen, (30, 90, 200), False, pts_t, 2)
            pygame.draw.lines(screen, (200, 60, 60), False, pts_o, 2)
            pygame.draw.lines(screen, (60, 160, 60), False, pts_a, 2)
            pygame.draw.lines(screen, (160, 60, 160), False, pts_u, 2)
        screen.set_clip(None)

        lab1 = font2.render("theta, deg +/-" + str(scale_t), True, (30, 90, 200))
        lab2 = font2.render("omega, rad/s +/-" + str(scale_o), True, (200, 60, 60))
        lab3 = font2.render("acc, rad/s^2 +/-" + str(scale_a), True, (60, 160, 60))
        lab4 = font2.render("U, Volts +/-" + str(scale_u), True, (160, 60, 160))
        lab_t = font2.render("t, s: 0..." + str(round(window, 1)), True, (0, 0, 0))
        screen.blit(lab1, (605, 62))
        screen.blit(lab2, (605, 187))
        screen.blit(lab3, (605, 312))
        screen.blit(lab4, (605, 437))
        screen.blit(lab_t, (605, 555))

    # Телеметрия на экране
    mode_color = (30, 140, 60) if "ANGLE" in mode else (210, 110, 20)
    screen.blit(font.render(f"Theta: {np.degrees(theta):.1f} deg", True, (0, 0, 0)), (20, 18))
    screen.blit(font.render(f"U: {U:.2f} V  (I: {I_curr:.2f} A)", True, (0, 0, 0)), (20, 44))
    screen.blit(font.render(f"Tau: {tau:.3f} N*m", True, (0, 0, 0)), (20, 70))
    screen.blit(font.render(f"E: {E_curr_val:.3f} / E*: {E_star_val:.3f} J", True, (0, 0, 0)), (20, 96))
    screen.blit(font.render(f"Mode: {mode}", True, mode_color), (20, 122))

    if paused:
        screen.blit(font.render("PAUSED", True, (200, 60, 60)), (20, 148))

    # Отрисовка слайдеров
    pygame.draw.rect(screen, (180, 180, 180), trk_L)
    pygame.draw.rect(screen, (40, 50, 60), hnd_L)
    pygame.draw.rect(screen, (180, 180, 180), trk_m)
    pygame.draw.rect(screen, (40, 50, 60), hnd_m)
    pygame.draw.rect(screen, (180, 180, 180), trk_b)
    pygame.draw.rect(screen, (40, 50, 60), hnd_b)
    pygame.draw.rect(screen, (60, 160, 60), btn_r)
    screen.blit(font2.render("L: " + str(round(L, 2)) + " m", True, (0, 0, 0)), (20, 168))
    screen.blit(font2.render("m: " + str(round(m, 3)) + " kg", True, (0, 0, 0)), (20, 218))
    screen.blit(font2.render("b: " + str(round(b, 3)), True, (0, 0, 0)), (20, 268))
    screen.blit(font2.render("RESTART", True, (255, 255, 255)), (35, 352))

    pygame.display.flip()
    clock.tick(60)

save_plots()
pygame.quit()
