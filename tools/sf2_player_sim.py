#!/usr/bin/env python3
"""SF2 采样器 PC 仿真
读取 sf2_extract.py 输出的 WAV + JSON 映射,
模拟 STC32G ADPCM 引擎: loop + 包络 + 变频 + ADPCM 编解码

用法:
    python sf2_player_sim.py  <sf2_extract_dir> [sample_idx] [midi_note] [duration_s]

示例:
    python sf2_player_sim.py D:/.../sf2_extract 15 60 2.0
    python sf2_player_sim.py D:/.../sf2_extract 15 60 2.0 --adpcm
    python sf2_player_sim.py D:/.../sf2_extract 7 60 3.0 --adpcm --envelope 10 300 0 200
"""

import struct, wave, os, sys, json, math

# ========== 降采样 (与 sf2_extract.py 相同) ==========
def resample(src, src_rate, dst_rate):
    if src_rate == dst_rate:
        return list(src)
    ratio = src_rate / dst_rate
    n = int(len(src) / ratio)
    out = []
    for j in range(n):
        pos = j * ratio
        idx = int(pos)
        frac = pos - idx
        if idx + 1 < len(src):
            val = src[idx] * (1 - frac) + src[idx + 1] * frac
        else:
            val = src[min(idx, len(src) - 1)]
        out.append(int(val))
    return out

# ========== ADPCM Type A 编码 ==========
STEPS_TBL = [16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,494,544,598,658,724,796,876,963,1060,1166,1282,1411,1552]
STEP_INC_ENC = [-16,-16,-16,-16,32,80,112,144]

def adpcm_encode(pcm):
    nibbles = []
    acc = 0
    step_idx = 0
    for s in pcm:
        target = max(-2048, min(2047, s))
        row = step_idx >> 4
        step = STEPS_TBL[min(row, 48)]
        best_nib = 0
        best_diff = 999999
        for nib in range(16):
            val = (2 * (nib & 7) + 1) * step // 8
            if nib & 8: val = -val
            test = (acc + val) & 0xFFF
            if test & 0x800: test -= 0x1000
            diff = abs(test - target)
            if diff < best_diff:
                best_diff = diff
                best_nib = nib
        nibbles.append(best_nib)
        delta = (2 * (best_nib & 7) + 1) * step // 8
        if best_nib & 8: delta = -delta
        acc += delta
        acc &= 0xFFF
        step_idx += STEP_INC_ENC[best_nib & 7]
        if step_idx < 0: step_idx = 0
        if step_idx > 768: step_idx = 768
    result = bytearray()
    for i in range(0, len(nibbles), 2):
        hi = nibbles[i]
        lo = nibbles[i + 1] if i + 1 < len(nibbles) else 0
        result.append((hi << 4) | lo)
    return bytes(result), len(nibbles)

# ========== 采样器 Voice ==========
class Sf2Voice:
    def __init__(self, pcm_data, loop_start, loop_end, has_loop,
                 orig_pitch, sample_rate, use_adpcm=False):
        self.pcm = pcm_data
        self.loop_start = loop_start
        self.loop_end = loop_end
        self.has_loop = has_loop
        self.orig_pitch = orig_pitch
        self.sample_rate = sample_rate

        self.pos = 0.0        # float 位置 (采样索引)
        self.active = True
        self.vol = 1.0

        # 包络
        self.env_phase = 'attack'  # attack -> decay -> sustain -> release -> off
        self.env_val = 0.0         # 0.0 ~ 1.0
        self.env_atk = 0.005      # seconds
        self.env_dec = 0.3
        self.env_sus = 0.3        # sustain level 0.0-1.0 (from SF2 0-100%)
        self.env_rel = 0.2
        self.env_timer = 0.0

        # ADPCM mode
        self.use_adpcm = use_adpcm
        if use_adpcm:
            rom, self.nib_count = adpcm_encode(pcm_data)
            self.adpcm_rom = rom
            self.adpcm_addr = 0
            self.adpcm_acc = 0
            self.adpcm_step_idx = 0
            self.adpcm_cache = 0
            self.adpcm_s_prev = 0
            self.adpcm_s_cur = 0
            # 预解码第一个
            self.adpcm_s_cur = self._adpcm_decode()
            # ADPCM loop 点就是 resampled 后的采样索引 (每个采样=1 nibble)
            self.adpcm_loop_start = loop_start
            self.adpcm_loop_end = loop_end
        self.pitch_ratio = 1.0

    def _adpcm_decode(self):
        if self.adpcm_addr >= self.nib_count:
            self.active = False
            return 0
        if self.adpcm_addr & 1:
            nib = self.adpcm_cache & 0x0F
        else:
            ri = self.adpcm_addr >> 1
            if ri >= len(self.adpcm_rom):
                self.active = False
                return 0
            self.adpcm_cache = self.adpcm_rom[ri]
            nib = (self.adpcm_cache >> 4) & 0x0F
        self.adpcm_addr += 1
        row = self.adpcm_step_idx >> 4
        step = STEPS_TBL[min(row, 48)]
        delta = (2 * (nib & 7) + 1) * step // 8
        if nib & 8: delta = -delta
        self.adpcm_acc += delta
        self.adpcm_acc &= 0xFFF
        val = self.adpcm_acc
        if val & 0x800: val -= 0x1000
        self.adpcm_step_idx += STEP_INC_ENC[nib & 7]
        if self.adpcm_step_idx < 0: self.adpcm_step_idx = 0
        if self.adpcm_step_idx > 768: self.adpcm_step_idx = 768
        return val

    def _adpcm_tick(self, step_val_8x8):
        """8.8 fixed point step tick, 与 STC32G pcm_render 相同逻辑"""
        if not self.active:
            return 0
        # step_val = pitch_ratio * 0x0100
        self.now_step = getattr(self, 'now_step', 0)
        self.now_step += step_val_8x8
        if self.now_step >= 0x100:
            cnt = self.now_step >> 8
            self.now_step &= 0xFF
            for _ in range(cnt):
                self.adpcm_s_prev = self.adpcm_s_cur
                s = self._adpcm_decode()
                if not self.active:
                    self.now_step = 0
                    return self.adpcm_s_prev
                self.adpcm_s_cur = s
                # loop wrap: 到达 loop_end 时回绕
                if self.has_loop and self.adpcm_loop_end > self.adpcm_loop_start and self.adpcm_addr >= self.adpcm_loop_end:
                    loop_len = self.adpcm_loop_end - self.adpcm_loop_start
                    self.adpcm_addr = self.adpcm_loop_start + (self.adpcm_addr - self.adpcm_loop_start) % loop_len
        frac = self.now_step
        if frac > 0 and step_val_8x8 < 0x100:
            out = self.adpcm_s_prev + (self.adpcm_s_cur - self.adpcm_s_prev) * frac / 256
        else:
            out = self.adpcm_s_cur
        return out

    def set_envelope(self, atk_s, dec_s, sus_pct, rel_s):
        self.env_atk = atk_s
        self.env_dec = dec_s
        self.env_sus = sus_pct / 100.0
        self.env_rel = rel_s

    def set_midi_note(self, midi_note):
        """设置 MIDI 音高, 计算变频比"""
        semi_diff = midi_note - self.orig_pitch
        self.pitch_ratio = 2.0 ** (semi_diff / 12.0)
        # 8.8 step: base = 0x0100 (原速)
        self.step_8x8 = int(0x0100 * self.pitch_ratio)
        self.step_8x8 = max(1, min(self.step_8x8, 0xFFFF))
        self.pos = 0.0

    def tick(self, dt):
        """渲染一个采样 (在 sample_rate 下调用), 返回 int16"""
        if not self.active:
            return 0

        if self.use_adpcm:
            s = self._adpcm_tick(self.step_8x8)
        else:
            # float 位置 + 线性插值 (TinySoundFont 风格)
            pos = self.pos
            if self.has_loop and self.loop_end > self.loop_start and pos >= self.loop_end:
                loop_len = self.loop_end - self.loop_start
                pos = self.loop_start + (pos - self.loop_start) % loop_len

            idx = int(pos)
            frac = pos - idx

            if idx < 0 or idx >= len(self.pcm):
                self.active = False
                return 0

            next_idx = idx + 1
            if self.has_loop and next_idx >= self.loop_end:
                next_idx = self.loop_start
            elif next_idx >= len(self.pcm):
                next_idx = idx

            s = self.pcm[idx] * (1.0 - frac) + self.pcm[next_idx] * frac
            self.pos += self.pitch_ratio

            if not self.has_loop and self.pos >= len(self.pcm):
                self.active = False

        # 包络
        self.env_timer += dt
        if self.env_phase == 'attack':
            self.env_val = min(1.0, self.env_timer / self.env_atk) if self.env_atk > 0 else 1.0
            if self.env_val >= 1.0:
                self.env_phase = 'decay'
                self.env_timer = 0.0
        elif self.env_phase == 'decay':
            if self.env_dec > 0:
                self.env_val = max(self.env_sus, 1.0 - self.env_timer / self.env_dec)
            else:
                self.env_val = self.env_sus
            if self.env_val <= self.env_sus:
                self.env_val = self.env_sus
                self.env_phase = 'sustain'
                self.env_timer = 0.0
        elif self.env_phase == 'sustain':
            self.env_val = self.env_sus
        elif self.env_phase == 'release':
            self.env_val = max(0.0, self.env_val - self.env_timer / self.env_rel) if self.env_rel > 0 else 0.0
            if self.env_val <= 0:
                self.active = False

        out = int(s * self.env_val * self.vol)
        return max(-32768, min(32767, out))

    def note_off(self):
        if self.env_phase in ('attack', 'decay', 'sustain'):
            self.env_phase = 'release'
            self.env_timer = 0.0


def main():
    if len(sys.argv) < 2:
        print("用法: python sf2_player_sim.py <sf2_extract_dir> [sample_idx] [midi] [dur] [--adpcm] [--envelope atk dec sus rel]")
        sys.exit(1)

    extract_dir = os.path.abspath(sys.argv[1])
    json_path = os.path.join(extract_dir, 'sf2_mapping.json')
    wav_dir = os.path.join(extract_dir, 'wav')
    out_dir = os.path.join(extract_dir, 'sim_output')
    os.makedirs(out_dir, exist_ok=True)

    # 解析参数
    args = sys.argv[2:]
    use_adpcm = '--adpcm' in args
    args = [a for a in args if a != '--adpcm']

    env_params = None
    if '--envelope' in args:
        ei = args.index('--envelope')
        env_params = [float(args[ei+1]), float(args[ei+2]), float(args[ei+3]), float(args[ei+4])]
        args = args[:ei] + args[ei+5:]

    sample_idx = int(args[0]) if len(args) > 0 else 15   # 默认 Grand Piano
    midi_note = int(args[1]) if len(args) > 1 else 60     # 默认 C4
    duration = float(args[2]) if len(args) > 2 else 2.0   # 默认 2 秒

    # 加载映射
    with open(json_path, 'r') as f:
        mapping = json.load(f)

    target_rate = mapping['target_rate']
    sinfo = mapping['samples'][str(sample_idx)]
    print(f"采样: [{sample_idx}] {sinfo['name']}  orig_pitch={sinfo['orig_pitch']} rate={target_rate}Hz")
    print(f"  loop={sinfo['loop_start']}->{sinfo['loop_end']} has_loop={sinfo['has_loop']}")
    print(f"  n_samples={sinfo['n_samples']} duration={sinfo['duration']:.3f}s")

    # 读取 WAV (已是降采样后的)
    wav_name = f"{sample_idx:02d}_{sinfo['name']}.wav"
    wav_path = os.path.join(wav_dir, wav_name)
    with wave.open(wav_path, 'r') as wf:
        pcm_data = list(struct.unpack(f'<{wf.getnframes()}h', wf.readframes(wf.getnframes())))
    print(f"  WAV: {len(pcm_data)} samples")

    # JSON 里已经是修正后的 resampled loop 点
    loop_start_rs = sinfo['loop_start']
    loop_end_rs = sinfo['loop_end']
    print(f"  loop: {loop_start_rs} -> {loop_end_rs}")

    # 创建 Voice
    voice = Sf2Voice(pcm_data, loop_start_rs, loop_end_rs, sinfo['has_loop'],
                     sinfo['orig_pitch'], target_rate, use_adpcm=use_adpcm)
    voice.set_midi_note(midi_note)

    # 包络
    if env_params:
        voice.set_envelope(*env_params)
        print(f"  envelope: atk={env_params[0]}s dec={env_params[1]}s sus={env_params[2]}% rel={env_params[3]}s")
    else:
        # 默认包络
        voice.set_envelope(0.01, 0.5, 30, 0.3)
        print(f"  envelope: default (atk=10ms dec=500ms sus=30% rel=300ms)")

    semi = midi_note - sinfo['orig_pitch']
    print(f"  MIDI {midi_note} (orig={sinfo['orig_pitch']}, diff={semi:+d} semi)")
    print(f"  pitch_ratio={voice.pitch_ratio:.4f} step=0x{voice.step_8x8:04X}")
    mode = 'ADPCM' if use_adpcm else 'PCM float'
    print(f"  mode: {mode}")

    # 渲染
    n_frames = int(duration * target_rate)
    note_off_time = duration * 0.7  # 70% 时间后 note_off (release 阶段)
    samples = []
    for i in range(n_frames):
        t = i / target_rate
        if voice.active and t >= note_off_time and voice.env_phase != 'release':
            voice.note_off()
        dt = 1.0 / target_rate
        s = voice.tick(dt)
        samples.append(s)

    # 输出 WAV
    out_name = f"sim_{sinfo['name']}_{midi_note}"
    if use_adpcm: out_name += '_adpcm'
    out_name += '.wav'
    out_path = os.path.join(out_dir, out_name)
    with wave.open(out_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(target_rate)
        wf.writeframes(struct.pack(f'<{len(samples)}h', *samples))

    print(f"\n输出: {out_path} ({len(samples)} frames, {duration:.1f}s)")
    print("Done!")


if __name__ == "__main__":
    main()
