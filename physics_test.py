import matplotlib.pyplot as plt
import numpy as np

a = 0.1
b = 0.3
c = 9.81
d = 0.05
e = 0.0
j = a * b**2 + e * b**2 / 3
x1 = 2.0
x2 = 1.5
x3 = 0.0
m_t = 1.5
dt = 1 / 60
dt2 = dt / 10
q1 = np.radians(10.0)
q2 = 0.0
err_sum = 0.0
steps = int(5.0 / dt2)

#массивы для граф
t_l = []
q1_l = []
q2_l = []
u_l = []

for i in range(steps):
    t_curr = i * dt2
    e_curr = q1
    err_sum = err_sum + e_curr * dt2
    
    if err_sum > 1.0:
        err_sum = 1.0
    if err_sum < -1.0:
        err_sum = -1.0
        
    u = -x1 * e_curr - x2 * q2 - x3 * err_sum
    
    if u > m_t:
        u = m_t
    if u < -m_t:
        u = -m_t
        
    acc = (a * c * b * np.sin(q1) - d * q2 + u) / j
    q2 = q2 + acc * dt2
    q1 = q1 + q2 * dt2

    if i % 10 == 0:
        t_l.append(t_curr)
        q1_l.append(np.degrees(q1))
        q2_l.append(q2)
        u_l.append(u)
        
plt.figure()
plt.subplot(2, 1, 1)
plt.plot(t_l, q1_l)
plt.grid()
plt.subplot(2, 1, 2)
plt.plot(t_l, u_l, 'r')
plt.grid()
plt.show()

print(round(np.degrees(q1), 4))
print(round(u, 4))
