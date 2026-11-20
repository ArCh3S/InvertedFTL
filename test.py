# === ИМПОРТЫ ===
import os                   # модуль для работы с файловой системой
import pygame               # библиотека для создания окна и отрисовки
import numpy as np          # библиотека для математических расчётов
import matplotlib.pyplot as plt  # библиотека для построения графиков

pygame.init()     # ЗАПУСК PYGAME

# === ДАНО ===
m = 0.1     # масса груза, кг.
L = 0.3     # длина палки, м.
g = 9.81    # ускорение свободного падения
b = 0.05    # трение
rho_lin = 0.104976          # линейная плотность палки, кг/м
m_rod = rho_lin * L         # масса палки
J = m * L**2 + m_rod * L**2 / 3   # момент инерции
k1 = 5.0     # П-регулятор
k2 = 0.6     # Д-регулятор
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
font = pygame.font.SysFont("Orbitron", 22)    # основной шрифт текста
font2 = pygame.font.SysFont("Orbitron", 14)   # мелкий шрифт для графиков
clock = pygame.time.Clock()     # создание часов
running = True     # симуляция запущена заранее
paused = False     # пауза

# создание папки plots рядом со скриптом для сохранения графиков
folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plots")
os.makedirs(folder, exist_ok=True)

# === ЛОГИ ===
t_hist = []         # список истории времени
theta_hist = []     # список истории угла
omega_hist = []     # список истории угловой скорости
acc_hist = []       # список истории углового ускорения
tau_hist = []       # список истории момента силы
t_curr = 0.0        # счётчик текущего времени

# === СОХРАНЕНИЕ ГРАФИКОВ ===
def save_plots():
    if len(t_hist) < 2:     # проверка наличия достаточного количества точек
        return
    plt.figure(figsize=(10, 12))    # задание размера полотна для графиков
    plt.subplot(4, 1, 1)            # первый подграфик (угол)
    plt.plot(t_hist, np.degrees(theta_hist), label="theta, deg", color='blue')
    plt.axhline(0, color='black', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.subplot(4, 1, 2)            # второй подграфик (угловая скорость)
    plt.plot(t_hist, omega_hist, label="omega, rad/s", color='red')
    plt.axhline(0, color='black', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.subplot(4, 1, 3)            # третий подграфик (угловое ускорение)
    plt.plot(t_hist, acc_hist, label="acc, rad/s^2", color='green')
    plt.axhline(0, color='black', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.subplot(4, 1, 4)            # четвёртый подграфик (момент силы)
    plt.plot(t_hist, tau_hist, label="tau, N*m", color='purple')
    plt.axhline(0, color='black', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.xlabel("time, s")           # подпись горизонтальной оси времени
    plt.tight_layout()              # выравнивание отступов между графиками
    plt.savefig(os.path.join(folder, "latest_plot.png"))    # сохранение картинки в файл
    plt.close()                     # закрытие фигуры

# === ОСНОВНОЙ ЦИКЛ ===
while running:
    for event in pygame.event.get():        # перебор всех событий окна
        if event.type == pygame.QUIT:       # при нажатии крестика
            running = False                 # закрываем симуляцию
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:       # аналогично с ESC
            running = False                                                     # и закрыванием
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:        # аналогично с SPACE
            paused = not paused                                                 # и остановкой
    if not paused:         # функция симуляции
        for j in range(10):     # 10 раз в цикл
            m_rod = rho_lin * L                     # пересчёт массы палки
            J = m * L**2 + m_rod * L**2 / 3         # заново считаем каждый раз, т.к. параметры могут меняться
            
            # --- ИНТЕГРИРОВАНИЕ МЕТОДОМ LEAPFROG ---
            # 1. Полушаг координаты (дрейф): сдвигаем угол на половину шага dt_phys
            theta_half = theta + 0.5 * omega * dt_phys
            
            # 2. Вычисление управления и ускорения в промежуточной точке полушага
            e = theta_half      # целевой угол (ошибка в полушаге)
            int_err = np.clip(int_err + e * dt_phys, -1, 1)   # анти-виндап
            tau = np.clip(-k1 * e - k2 * omega - k3 * int_err, -max_tau, max_tau)     # лимиты
            if abs(theta_half) < 0.026:             # реальная мёртвая зона датчика/мотора (~1.5 градуса)
                tau = 0.0                           # внутри мёртвой зоны привод не даёт момент
            acc = (m * g * L * np.sin(theta_half) - b * omega + tau) / J     # ускорение в середине шага
            
            # 3. Полный шаг скорости (толчок): обновляем угловую скорость через ускорение в полушаге
            omega = omega + acc * dt_phys           # угловая скорость на конце шага
            
            # 4. Второй полушаг координаты (дрейф): доводим угол до конца шага с уже новой скоростью
            theta = theta_half + 0.5 * omega * dt_phys         # угол на конце шага
            
        # === ЗАПОЛНЕНИЕ ИСТОРИИ ===
        t_hist.append(t_curr)       # сохранение текущего времени
        theta_hist.append(theta)    # сохранение угла
        omega_hist.append(omega)    # сохранение угловой скорости
        acc_hist.append(acc)        # сохранение углового ускорения
        tau_hist.append(tau)        # сохранение управляющего момента
        t_curr += dt                # шаг времени кадра
    # координаты груза и заполнение экрана
    screen.fill((255, 255, 255))                        # очистка экрана белым цветом
    x_end = cx - round(scale * L * np.sin(theta))       # расчёт X координаты груза
    y_end = cy - round(scale * L * np.cos(theta))       # расчёт Y координаты груза
    # рисуем маятник
    pygame.draw.circle(screen, (40, 50, 60), (cx, cy), 10)              # отрисовка оси крепления
    pygame.draw.line(screen, (60, 70, 80), (cx, cy), (x_end, y_end), 5) # отрисовка стержня
    pygame.draw.circle(screen, (80, 90, 100), (x_end, y_end), 15)       # отрисовка груза на конце
    # проверка существования точек и данные для графиков с рамкой
    if len(t_hist) > 1:
        graph_rect = pygame.Rect(600, 50, 350, 500)             # прямоугольник области графиков
        pygame.draw.rect(screen, (235, 235, 235), graph_rect)   # заливка фона графиков
        pygame.draw.rect(screen, (40, 50, 60), graph_rect, 2)   # отрисовка контура рамки
        window = max(t_hist[-1] - t_hist[0], 1.0)               # ширина временного окна
        # чтобы не было ошибок при 0 и определение максимумов
        max_t = 1.0     # максимальный угол
        max_o = 1.0     # максимальная угловая скорость
        max_a = 1.0     # максимальное угловое ускорение
        max_tau = 0.1   # максимальный момент силы
        for i in range(len(t_hist)):                            # поиск максимумов по истории
            if abs(np.degrees(theta_hist[i])) > max_t:
                max_t = abs(np.degrees(theta_hist[i]))          # обновление максимума угла
            if abs(omega_hist[i]) > max_o:
                max_o = abs(omega_hist[i])                      # обновление максимума скорости
            if abs(acc_hist[i]) > max_a:
                max_a = abs(acc_hist[i])                        # обновление максимума ускорения
            if abs(tau_hist[i]) > max_tau:
                max_tau = abs(tau_hist[i])                      # обновление максимума момента
        # масштаб(шкала)
        scale_t = 720   # стандартный масштаб угла
        for s in [2, 5, 10, 20, 45, 90, 180, 360, 720]:         # подбор подходящей шкалы угла
            if s >= max_t:
                scale_t = s
                break
        scale_o = 50    # стандартный масштаб угловой скорости
        for s in [1, 2, 5, 10, 20, 50]:                         # подбор шкалы скорости
            if s >= max_o:
                scale_o = s
                break
        scale_a = 500   # стандартный масштаб ускорения
        for s in [5, 10, 20, 50, 100, 200, 500]:                # подбор шкалы ускорения
            if s >= max_a:
                scale_a = s
                break
        scale_tau = 3   # стандартный масштаб момента силы
        for s in [0.5, 1, 1.5, 2, 3]:                           # подбор шкалы момента
            if s >= max_tau:
                scale_tau = s
                break
        pygame.draw.line(screen, (120, 120, 120), (600, 112), (950, 112), 1)   # нули (ось угла)
        pygame.draw.line(screen, (120, 120, 120), (600, 237), (950, 237), 1)   # нули (ось скорости)
        pygame.draw.line(screen, (120, 120, 120), (600, 362), (950, 362), 1)   # нули (ось ускорения)
        pygame.draw.line(screen, (120, 120, 120), (600, 487), (950, 487), 1)   # нули (ось момента)
        pts_t = []      # точки полилинии угла
        pts_o = []      # точки полилинии скорости
        pts_a = []      # точки полилинии ускорения
        pts_tau = []    # точки полилинии момента
        for i in range(len(t_hist)):    # расчёт пиксельных координат для каждой точки истории
            x_graph = 600 + int((t_hist[i] - t_hist[0]) / window * 350)     # координата X по времени
            y_t = 112 - int(np.degrees(theta_hist[i]) / scale_t * 50)       # координата Y угла
            y_o = 237 - int(omega_hist[i] / scale_o * 50)                   # координата Y скорости
            y_a = 362 - int(acc_hist[i] / scale_a * 50)                     # координата Y ускорения
            y_tau = 487 - int(tau_hist[i] / scale_tau * 50)                 # координата Y момента
            pts_t.append((x_graph, y_t))        # добавление точки угла
            pts_o.append((x_graph, y_o))        # добавление точки скорости
            pts_a.append((x_graph, y_a))        # добавление точки ускорения
            pts_tau.append((x_graph, y_tau))    # добавление точки момента
        screen.set_clip(graph_rect)             # обрезка рисования по границам окна графиков
        if len(pts_t) > 1:                      # если точек достаточно для линии
            pygame.draw.lines(screen, (30, 90, 200), False, pts_t, 2)       # кривая угла
            pygame.draw.lines(screen, (200, 60, 60), False, pts_o, 2)       # кривая скорости
            pygame.draw.lines(screen, (60, 160, 60), False, pts_a, 2)       # кривая ускорения
            pygame.draw.lines(screen, (160, 60, 160), False, pts_tau, 2)    # кривая момента
        screen.set_clip(None)                   # снятие ограничения области рисования
        lab1 = font2.render("theta, deg +/-" + str(scale_t), True, (30, 90, 200))   # текст шкалы угла
        lab2 = font2.render("omega, rad/s +/-" + str(scale_o), True, (200, 60, 60)) # текст шкалы скорости
        lab3 = font2.render("acc, rad/s^2 +/-" + str(scale_a), True, (60, 160, 60)) # текст шкалы ускорения
        lab4 = font2.render("tau, N*m +/-" + str(scale_tau), True, (160, 60, 160))  # текст шкалы момента
        lab_t = font2.render("t, s: 0..." + str(round(window, 1)), True, (0, 0, 0)) # текст шкалы времени
        screen.blit(lab1, (605, 62))            # вывод подписи угла
        screen.blit(lab2, (605, 187))           # вывод подписи скорости
        screen.blit(lab3, (605, 312))           # вывод подписи ускорения
        screen.blit(lab4, (605, 437))           # вывод подписи момента
        screen.blit(lab_t, (605, 555))          # вывод подписи времени
    theta_str = "Theta: " + str(round(np.degrees(theta), 2)) + " deg"   # строка текущего угла
    tau_str = "Tau: " + str(round(tau, 3)) + " N*m"                     # строка текущего момента
    text1 = font.render(theta_str, True, (0, 0, 0))                     # рендер текста угла
    text2 = font.render(tau_str, True, (0, 0, 0))                       # рендер текста момента
    screen.blit(text1, (20, 20))                                        # отображение угла на экране
    screen.blit(text2, (20, 50))                                        # отображение момента на экране
    if paused:                                                          # проверка состояния паузы
        text3 = font.render("PAUSED", True, (200, 60, 60))              # рендер надписи паузы
        screen.blit(text3, (20, 80))                                    # отображение надписи паузы
    pygame.display.flip()   # обновление кадра на экране
    clock.tick(60)          # ограничение частоты кадров до 60 FPS
save_plots()    # сохранение графиков после закрытия окна
pygame.quit()   # выгрузка модулей Pygame