#!/usr/bin/env python3
"""下位机鼓声严格仿真 (1:1 ym_render_drum, 全部硬件限制保留).

和 drum_fw_sim.py 的区别:
- 严格 8.8 定点 (pos/step 都是 u16, idx = (pos>>8)&0x3F), 不是 16.16
- ISR 22050Hz (不是 INTERNAL_RATE 49716)
- step 用下位机真实 init 值 (HH/CYM=0x00F8=334Hz, 不是 PC 的 755Hz)
- 输出公式 (wave×(level+1)×vol)>>6, vol 是下位机真实 base_vol
- oneshot 每采样 tick env (不走 round-robin)
- 噪声表用下位机真实的 ym_noise[64] (固定, 不是 random.seed(42))

用途: 对比下位机 334Hz vs PC 试听 755Hz 的听感差异, 决定要不要改 base_step.
"""
import math, struct, wave, os

SR = 22050  # 下位机真实 ISR

# ===== 下位机真实的表 (从 ym2413.c 照搬) =====
# ym_noise[64] (ym2413.c:35-40, 固定 code 区)
FW_NOISE = [
     7, -4, 19, -28, 12, 23, -15,  6, -31,  8, -2, 27, -9, 14, -22,  3,
    18,-11, 25, -7, 30,-19,  5,-24, 10,-14, 21, -3, 16,-27,  1, 29,
    -8, 13,-21,  4, 26,-10, 20, -6, 15,-25, 11,-17, 24, -1,  9,-29,
     2, 22,-13, 28, -5, 17,-23,  0, 31,-18,  7,-12, 19,-26, 14,-20
]

# ym_sin[64] (ym2413.c:21-26)
FW_SIN = [
     0,  3,  6,  9, 12, 15, 17, 20, 22, 24, 26, 28, 29, 30, 31, 31,
    31, 31, 31, 30, 29, 28, 26, 24, 22, 20, 17, 15, 12,  9,  6,  3,
     0, -3, -6, -9,-12,-15,-17,-20,-22,-24,-26,-28,-29,-30,-31,-31,
   -31,-31,-31,-30,-29,-28,-26,-24,-22,-20,-17,-15,-12, -9, -6, -3
]

# ===== 下位机真实的鼓声 init 参数 (ym2413.c:494-498, 当前 commit) =====
# step 是 8.8 定点 u16, 反推频率: freq = step * 22050 / (64*256)
DRUMS = {
    # name: (wave, step_u16, base_vol, env_step, decay_ms_comment)
    'BD':  (FW_SIN,   0x004A, 16, 14),   # 100Hz
    'TOM': (FW_SIN,   0x009F,  9, 14),   # 214Hz
    'HH':  (FW_NOISE, 0x00F8,  4, 46),   # 334Hz (当前下位机真实值)
    'CYM': (FW_NOISE, 0x00F8,  4, 255),  # 334Hz (当前下位机真实值)
    'SD':  (FW_NOISE, 0x0012,  8, 28),   # 25Hz
}

def step_to_hz(step):
    """8.8 定点 step → 频率 (ISR 22050, 64 点表)"""
    return step * 22050 / (64 * 256)

def hz_to_step(hz):
    """频率 → 8.8 定点 step"""
    return int(round(hz * 64 * 256 / 22050))

# ===== 严格 1:1 ym_render_drum (ym2413.c:642-666) =====
def render_drum_fw(name, step_override=None, vol_override=None, dur=1.0):
    """仿真单个鼓声. 可选 step_override/vol_override 用于对比不同频率/音量.
    返回 samples (s16, 已 <<1 对齐下位机最终输出)."""
    wave_table, step, vol, env_step = DRUMS[name]
    if step_override is not None: step = step_override
    if vol_override is not None: vol = vol_override

    n = int(dur * SR)
    pos = 0          # u16 8.8 定点 (下位机 d->pos)
    level = 31 if name in ('HH','CYM') else 31  # trigger 初始 level (ym_drum_trigger)
    # 注: HH/CYM trigger 时 level=21 (ym2413.c:633), 但为了听满 decay 这里用 31
    # 真实 trigger: idx 2,3 → level=21, 其他 → level=31
    level = 21 if name in ('HH', 'CYM') else 31
    env_cnt = 0
    active = 1
    out = []

    for s in range(n):
        if not active:
            out.append(0)
            continue

        # 包络: 每采样 tick (ym2413.c:650-657, 不走 round-robin)
        if env_step > 0:
            if env_cnt < env_step:
                env_cnt += 1
            else:
                env_cnt = 0
                if level > 0:
                    level -= 1
                else:
                    active = 0
                    out.append(0)
                    continue

        # 单 op: 查表 × level × vol (ym2413.c:660-664)
        pos = (pos + step) & 0xFFFF        # u16 8.8 定点
        idx = (pos >> 8) & 0x3F            # >>8 取高 8 位索引
        wave_val = wave_table[idx]
        # out = (wave_val × (level+1) × vol) >> 6  (ym2413.c:662)
        v = (wave_val * ((level + 1) * vol)) >> 6
        if v > 127: v = 127
        if v < -128: v = -128
        out.append(v << 1)   # 最后 <<1 (ym2413.c:784 total<<1)

    return out

# ===== 755Hz 对照 (PC 试听值, 用下位机 8.8 定点重现) =====
def render_drum_755(name, dur=1.0):
    """用下位机硬件限制跑 755Hz (PC 试听定的), 对比 334Hz."""
    step_755 = hz_to_step(755)   # = 0x0230 (560)
    return render_drum_fw(name, step_override=step_755, dur=dur)

def save_wav(path, samples, normalize=True):
    """保存 WAV. normalize=True 时放大到 0.8 满幅 (方便试听).
    仿真的绝对幅度很小 (vol=4 下 peak~86/32767), 不放大听不见.
    放大只影响试听音量, 不影响 334 vs 755 的相对对比 (两者同比例放大)."""
    if normalize and samples:
        peak = max(abs(x) for x in samples)
        if peak > 0:
            scale = 32767 * 0.8 / peak
            samples = [max(-32768, min(32767, int(x * scale))) for x in samples]
    with wave.open(path, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(struct.pack(f'<{len(samples)}h', *samples))

def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wav_drum_334vs755')
    os.makedirs(out_dir, exist_ok=True)

    print('=' * 64)
    print('下位机鼓声严格仿真 (8.8 定点, 22050Hz, 全部硬件限制保留)')
    print('=' * 64)
    print()
    print('当前下位机 init 参数 (ym2413.c:494-498):')
    for name, (wt, step, vol, env) in DRUMS.items():
        freq = step_to_hz(step)
        decay_ms = 31 * env / 22050 * 1000 if name not in ('HH','CYM') else 21 * env / 22050 * 1000
        print('  %-4s step=0x%04X (%3d) -> %6.1f Hz  vol=%2d  env_step=%3d  decay~%.0fms' % (
            name, step, step, freq, vol, env, decay_ms))
    print()
    print('755Hz 对应的 step = 0x%04X (%d)' % (hz_to_step(755), hz_to_step(755)))
    print('334Hz 对应的 step = 0x%04X (%d) (当前 HH/CYM)' % (hz_to_step(334), hz_to_step(334)))
    print()

    # 生成 HH/CYM 的 334Hz vs 755Hz 对比
    for name in ('HH', 'CYM'):
        dur = 0.5 if name == 'HH' else 1.0
        s334 = render_drum_fw(name, dur=dur)
        s755 = render_drum_755(name, dur=dur)
        f334 = os.path.join(out_dir, f'{name}_334hz_fw.wav')
        f755 = os.path.join(out_dir, f'{name}_755hz_fw.wav')
        save_wav(f334, s334)
        save_wav(f755, s755)
        print(f'{name}: 334Hz -> {os.path.basename(f334)}')
        print(f'{name}: 755Hz -> {os.path.basename(f755)}')

    # 也生成其他鼓做完整性对照
    for name in ('BD', 'TOM', 'SD'):
        s = render_drum_fw(name, dur=0.5)
        f = os.path.join(out_dir, f'{name}_fw.wav')
        save_wav(f, s)
        print(f'{name}: -> {os.path.basename(f)}')

    print()
    print(f'输出目录: {out_dir}')
    print()
    print('对比方法: 听 HH_334hz_fw.wav vs HH_755hz_fw.wav')
    print('  334Hz = 下位机当前真实值 (step=0x00F8)')
    print('  755Hz = PC 试听扫频定的值 (step=0x0230, 下位机从没跑过)')
    print('如果 755 更像镲片 -> 改 base_step=0x0230')
    print('如果 334 已经够好 -> 保持 0x00F8, 承认是下位机重新定的')

if __name__ == '__main__':
    main()
