#!/usr/bin/env python3
"""用 emu 指数衰减时间常数, 生成 sus_hold[32] 表 (每 level 停留 tick 数).

emu SUSTAIN 输出指数衰减: ratio(t) = 2^(-t/tau)
fw level 线性控制输出, 要让输出指数衰减:
  level(t) = 31 × 2^(-t/tau)
  level 从 n 降到 n-1 的时间 = tau × log2(n/(n-1))
  高 level 停留久, 低 level 停留短 (模拟指数)

sus_hold[n] = level n 停留几个 fw-tick 才降到 n-1
fw-tick = 16采样/22050 = 0.726ms
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# emu harpsichord 衰减时间常数 (从 RMS 曲线: -3dB@~100ms)
# ratio@100ms = 0.732 (实测), tau = 100/log2(1/0.732) = 100/0.451 = 221.7ms
# 用多点拟合: 取 @200ms ratio=0.533, @500ms ratio=0.209
# log2(0.533)=-0.908 @200ms -> tau=220; log2(0.209)=-2.259 @500ms -> tau=221
# tau ≈ 221ms 一致, 好
TAU_MS = 221.0
FW_TICK_MS = 16/22050*1000  # 0.726ms

print(f"=== sus_hold[32] 生成 (指数衰减 tau={TAU_MS}ms, fw-tick={FW_TICK_MS:.3f}ms) ===\n")

sus_hold = [0]*32
for n in range(1, 32):
    if n == 1:
        hold_ms = TAU_MS * math.log2(1/0.5)  # level 1->0, 用 1/0.5 近似
    else:
        hold_ms = TAU_MS * math.log2(n/(n-1))
    hold_tick = hold_ms / FW_TICK_MS
    sus_hold[n] = max(1, round(hold_tick))

print(f"{'level':>6} {'hold_tick':>10}")
print("-" * 20)
for n in range(1, 32):
    if n == 1:
        h = TAU_MS * math.log2(1/0.5)
    else:
        h = TAU_MS * math.log2(n/(n-1))
    print(f"{n:>6} {sus_hold[n]:>10}  (理论 {h/FW_TICK_MS:.1f}tick)")

print(f"\nsus_hold[32] = {sus_hold}")
print(f"\n用法 (下位机/仿真):")
print(f"  SUSTAIN 阶段: 维持一个 sus_cnt 计数器")
print(f"    sus_cnt++; if (sus_cnt >= sus_hold[level]) {{ sus_cnt=0; level--; }}")
print(f"  高 level sus_hold 大 (慢降), 低 level sus_hold 小 (快降) -> 指数衰减形态")

# 验证: 模拟 fw level 衰减, 看输出曲线
print(f"\n=== 验证: fw level 模拟衰减曲线 ===")
level = 31; cnt = 0
fw_out_ratio = []
for tick in range(2000):  # 2000 fw-tick = 1.45s
    if level > 0:
        cnt += 1
        if cnt >= sus_hold[level]:
            cnt = 0; level -= 1
    fw_out_ratio.append((level+1)/32)  # 输出 ∝ level+1

# 对照 emu: ratio(t) = 2^(-t/tau)
print(f"{'ms':>5} {'emu_ratio':>10} {'fw_ratio':>10} {'emu_dB':>8} {'fw_dB':>8}")
for ms in [0, 50, 100, 200, 300, 500, 700, 950, 1000]:
    t_s = ms/1000
    emu_r = 2**(-t_s*1000/TAU_MS)
    tick = int(ms/FW_TICK_MS)
    fw_r = fw_out_ratio[min(tick, len(fw_out_ratio)-1)]
    print(f"{ms:>5} {emu_r:>10.3f} {fw_r:>10.3f} {20*math.log10(emu_r):>+8.1f} {20*math.log10(fw_r):>+8.1f}")

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sus_hold_gen.txt'), 'w') as f:
    f.write(str(sus_hold))
print(f"\n表已存 sus_hold_gen.txt")
