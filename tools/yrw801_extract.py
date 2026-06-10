#!/usr/bin/env python3
"""YRW801 (OPL4 Wave ROM) 解析 + 试听 WAV 生成
从 2MB ROM 提取乐器元数据 + PCM 波形, 生成可听 WAV

用法:
    python yrw801_extract.py                          # 列出所有乐器
    python yrw801_extract.py --wav 0 1 2 3 4 5        # 生成指定乐器 C4 试听
    python yrw801_extract.py --wav-all                 # 生成全部 175 个乐器试听
    python yrw801_extract.py --wav-range 0 127        # 生成旋律乐器 0-127
    python yrw801_extract.py --export 0 1 2 3          # 导出精选乐器为 WAV (原始采样率)
"""

import struct, os, sys, wave

ROM_PATH = 'D:/working/vscode-projects/Reference_Project/vgm_libs/libvgm-master/emu/cores/yrw801.rom'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yrw801_out')

# GM 乐器名 (128 melody + 47 percussion)
# YRW801 顺序: 0-127 旋律 (GM), 128-175 打击乐
GM_NAMES = [
    "Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano", "Honky-tonk Piano",
    "Electric Piano 1", "Electric Piano 2", "Harpsichord", "Clavinet",
    "Celesta", "Glockenspiel", "Music Box", "Vibraphone",
    "Marimba", "Xylophone", "Tubular Bells", "Dulcimer",
    "Drawbar Organ", "Percussive Organ", "Rock Organ", "Church Organ",
    "Reed Organ", "Accordion", "Harmonica", "Tango Accordion",
    "Nylon Guitar", "Steel Guitar", "Jazz Guitar", "Clean Guitar",
    "Overdriven Guitar", "Distortion Guitar", "Guitar Harmonics", "Acoustic Bass",
    "Finger Bass", "Pick Bass", "Fretless Bass", "Slap Bass 1",
    "Slap Bass 2", "Synth Bass 1", "Synth Bass 2", "Violin",
    "Viola", "Cello", "Contrabass", "Tremolo Strings",
    "Pizzicato Strings", "Orchestral Harp", "Timpani", "String Ensemble 1",
    "String Ensemble 2", "Synth Strings 1", "Synth Strings 2", "Choir Aahs",
    "Voice Oohs", "Synth Choir", "Orchestra Hit", "Trumpet",
    "Trombone", "Tuba", "Muted Trumpet", "French Horn",
    "Brass Section", "Synth Brass 1", "Synth Brass 2", "Soprano Sax",
    "Alto Sax", "Tenor Sax", "Baritone Sax", "Oboe",
    "English Horn", "Bassoon", "Clarinet", "Piccolo",
    "Flute", "Recorder", "Pan Flute", "Blown Bottle",
    "Shakuhachi", "Whistle", "Ocarina", "Lead 1 (square)",
    "Lead 2 (saw)", "Lead 3 (cal lead)", "Lead 4 (chiff)", "Lead 5 (charang)",
    "Lead 6 (voice)", "Lead 7 (fifths)", "Lead 8 (bass+lead)", "Pad 1 (new age)",
    "Pad 2 (warm)", "Pad 3 (polysynth)", "Pad 4 (choir)", "Pad 5 (bowed)",
    "Pad 6 (metallic)", "Pad 7 (halo)", "Pad 8 (sweep)", "FX 1 (rain)",
    "FX 2 (soundtrack)", "FX 3 (crystal)", "FX 4 (atmosphere)", "FX 5 (brightness)",
    "FX 6 (goblins)", "FX 7 (echoes)", "FX 8 (sci-fi)", "Sitar",
    "Banjo", "Shamisen", "Koto", "Kalimba",
    "Bagpipe", "Fiddle", "Shanai", "Tinkle Bell",
    "Agogo", "Steel Drums", "Woodblock", "Taiko Drum",
    "Melodic Tom", "Synth Drum", "Reverse Cymbal", "Guitar Fret Noise",
    "Breath Noise", "Seashore", "Bird Tweet", "Telephone Ring",
    "Helicopter", "Applause", "Gunshot", "Sit Pad",
]

PERC_NAMES = [
    "Standard Kit", "Standard Kit Alt", "Room Kit", "Room Kit Alt",
    "Power Kit", "Power Kit Alt", "Electronic Kit", "Electronic Kit Alt",
    "TR-808 Kit", "TR-808 Kit Alt", "Jazz Kit", "Jazz Kit Alt",
    "Brush Kit", "Brush Kit Alt", "Orchestra Kit", "Orchestra Kit Alt",
    "SFX Kit", "SFX Kit Alt", "CT-S700 Kit", "CT-S700 Kit Alt",
    "Ambient Kit", "Ambient Kit Alt", "Standard Kit 2", "Standard Kit 2 Alt",
    "Room Kit 2", "Room Kit 2 Alt", "Power Kit 2", "Power Kit 2 Alt",
    "Electronic Kit 2", "Electronic Kit 2 Alt", "TR-808 Kit 2", "TR-808 Kit 2 Alt",
    "Jazz Kit 2", "Jazz Kit 2 Alt", "Brush Kit 2", "Brush Kit 2 Alt",
    "Orchestra Kit 2", "Orchestra Kit 2 Alt", "SFX Kit 2", "SFX Kit 2 Alt",
    "CT-S700 Kit 2", "CT-S700 Kit 2 Alt", "Ambient Kit 2", "Ambient Kit 2 Alt",
]


def parse_rom(rom_data):
    """解析 YRW801 ROM, 返回乐器列表"""
    instruments = []
    # YRW801: 128 melody + 47 percussion = 175 标准乐器
    # 元数据表从地址 0 开始, 每 12 字节一条
    # 但 ROM 可能包含额外的采样条目 (start 地址可能回绕)
    # 所以我们扫描所有合法条目, 最多 512
    n_inst = 0
    for idx in range(0, min(len(rom_data) - 12, 512 * 12), 12):
        b = rom_data[idx:idx+12]
        start_raw = (b[0] << 16) | (b[1] << 8) | b[2]
        raw_start = start_raw & 0x1FFFFF
        end_raw = (b[5] << 8) | b[6]
        end = 0x10000 - end_raw
        loop = (b[3] << 8) | b[4]
        # 基本合法性: end > 0, end <= 0x10000, start 在 ROM 范围内
        if end <= 0 or end > 0x10000:
            break
        if raw_start + end > len(rom_data) + 4096:  # 允许一点溢出
            break
        n_inst += 1

    meta_end = n_inst * 12
    print(f"元数据表: {n_inst} 乐器, {meta_end} 字节")

    for idx in range(0, meta_end, 12):
        b = rom_data[idx:idx+12]
        start_raw = (b[0] << 16) | (b[1] << 8) | b[2]
        fmt = (start_raw >> 21) & 0x03
        start = start_raw & 0x1FFFFF
        loop = (b[3] << 8) | b[4]
        end_val = (b[5] << 8) | b[6]
        end = 0x10000 - end_val
        lfo_vib = b[7]
        attack_reg = (b[8] >> 4) & 0xf
        decay1_reg = b[8] & 0xf
        decay2_reg = b[9] & 0xf
        decay_level = (b[9] >> 4) & 0xf
        release_reg = b[10] & 0xf
        key_rate_scale = (b[10] >> 4) & 0xf
        lfo_amp = b[11] & 0xf

        # 提取 PCM 数据
        has_loop = loop < end and end > 0
        n_samples = end

        pcm = []
        if fmt & 0x04:  # 12-bit linear (参考 multipcm.c)
            if start + (n_samples + 1) // 2 * 3 <= len(rom_data):
                for j in range(n_samples):
                    adr = start + (j >> 1) * 3
                    if (j & 1) == 0:
                        w = (rom_data[adr] << 8) | ((rom_data[adr + 1] & 0x0F) << 4)
                    else:
                        w = (rom_data[adr + 2] << 8) | (rom_data[adr + 1] & 0xF0)
                    pcm.append(w if w < 0x8000 else w - 0x10000)
            else:
                pcm = [0]
                n_samples = 0
        else:
            # 8-bit linear
            if start + n_samples <= len(rom_data):
                for j in range(n_samples):
                    val = rom_data[start + j]
                    pcm.append((val - 128) << 8)
            else:
                pcm = [0]
                n_samples = 0

        inst_id = idx // 12
        if inst_id < 128:
            name = GM_NAMES[inst_id] if inst_id < len(GM_NAMES) else f"Melody {inst_id}"
        else:
            pid = inst_id - 128
            name = PERC_NAMES[pid] if pid < len(PERC_NAMES) else f"Perc {pid}"

        inst = {
            'id': inst_id,
            'name': name,
            'start': start,
            'loop': loop,
            'end': end,
            'n_samples': n_samples,
            'has_loop': has_loop,
            'format': fmt,
            'attack': attack_reg,
            'decay1': decay1_reg,
            'decay2': decay2_reg,
            'decay_level': decay_level,
            'release': release_reg,
            'key_rate_scale': key_rate_scale,
            'lfo_vib': lfo_vib,
            'lfo_amp': lfo_amp,
            'pcm': pcm,
        }
        instruments.append(inst)

    return instruments


def resample(pcm, src_n, dst_n):
    """简单线性插值降采样"""
    if src_n == 0 or dst_n == 0:
        return []
    ratio = src_n / dst_n
    out = []
    for j in range(dst_n):
        pos = j * ratio
        i = int(pos)
        f = pos - i
        if i + 1 < src_n:
            val = pcm[i] * (1 - f) + pcm[i + 1] * f
        else:
            val = pcm[min(i, src_n - 1)]
        out.append(int(val))
    return out


def render_voice(pcm, loop_s, loop_e, has_loop, dur, rate, midi_note=60, orig_pitch=60):
    """渲染一个 voice: pitch + loop + envelope"""
    semi = midi_note - orig_pitch
    pitch_ratio = 2.0 ** (semi / 12.0)
    n_frames = int(dur * rate)
    out = []

    pos = 0.0
    note_off_time = dur * 0.7

    for i in range(n_frames):
        t = i / rate
        # loop wrap
        if has_loop and loop_e > loop_s and pos >= loop_e:
            loop_len = loop_e - loop_s
            pos = loop_s + (pos - loop_s) % loop_len

        idx = int(pos)
        frac = pos - idx
        if idx < 0 or idx >= len(pcm):
            break

        next_idx = idx + 1
        if has_loop and next_idx >= loop_e:
            next_idx = loop_s
        elif next_idx >= len(pcm):
            next_idx = idx

        s = pcm[idx] * (1 - frac) + pcm[next_idx] * frac
        pos += pitch_ratio

        # envelope
        if t < 0.01:
            e = t / 0.01
        elif t < 0.15:
            e = 1.0 - 0.3 * ((t - 0.01) / 0.14)
        elif t < note_off_time:
            e = 0.7
        else:
            e = max(0, 0.7 * (1.0 - (t - note_off_time) / (dur - note_off_time)))

        out.append(max(-32768, min(32767, int(s * e))))

    return out


def main():
    # 加载 ROM
    print(f"加载 YRW801 ROM: {ROM_PATH}")
    with open(ROM_PATH, 'rb') as f:
        rom_data = f.read()
    print(f"  ROM 大小: {len(rom_data)} bytes ({len(rom_data)/1024/1024:.1f} MB)")

    instruments = parse_rom(rom_data)

    # 列出所有乐器
    print(f"\n=== YRW801 乐器列表 ({len(instruments)} 个) ===\n")

    # 解析命令行参数
    args = sys.argv[1:]
    do_wav = '--wav' in args
    do_wav_all = '--wav-all' in args
    do_export = '--export' in args
    do_wav_range = '--wav-range' in args

    if do_wav_range:
        ri = args.index('--wav-range')
        range_start = int(args[ri+1])
        range_end = int(args[ri+2])
    else:
        range_start = range_end = 0

    os.makedirs(OUT_DIR, exist_ok=True)

    for inst in instruments:
        pid = inst['id']
        fmt_str = "8bit" if inst['format'] == 0 else "12bit" if inst['format'] == 2 else f"?{inst['format']}"
        loop_tag = f" loop={inst['loop']}->{inst['end']}" if inst['has_loop'] else " ONESHOT"
        kb = inst['n_samples'] / 1024.0

        # 只对 melody 显示详细信息
        if pid < 128:
            print(f"  {pid:3d}: {inst['name']:25s} {fmt_str:4s} {inst['n_samples']:6d}s ({kb:5.1f}KB){loop_tag} atk={inst['attack']} d1={inst['decay1']} d2={inst['decay2']} sl={inst['decay_level']} rel={inst['release']}")
        else:
            print(f"  {pid:3d}: {inst['name']:25s} {fmt_str:4s} {inst['n_samples']:6d}s ({kb:5.1f}KB){loop_tag}")

    # 生成 WAV
    rate = 44100  # YRW801 原始采样率
    dur = 3.0

    def gen_wav(inst, subdir='wav'):
        if inst['n_samples'] < 10:
            print(f"    跳过 {inst['id']}: 采样太少 ({inst['n_samples']})")
            return

        out_dir = os.path.join(OUT_DIR, subdir)
        os.makedirs(out_dir, exist_ok=True)

        pcm = inst['pcm']
        loop_s = inst['loop']
        loop_e = inst['end']
        has_loop = inst['has_loop']

        # orig_pitch: GM 音色通常以 60 (C4) 为基准
        orig_pitch = 60

        out_samples = render_voice(pcm, loop_s, loop_e, has_loop, dur, rate, 60, orig_pitch)

        cn = inst['name'].replace(' ', '_').replace('(', '').replace(')', '')
        wav_path = os.path.join(out_dir, f"{inst['id']:03d}_{cn}_C4.wav")
        with wave.open(wav_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(struct.pack(f'<{len(out_samples)}h', *out_samples))
        print(f"    -> {wav_path} ({len(out_samples)} frames)")

    if do_wav:
        indices = [int(x) for x in args[args.index('--wav')+1:] if x.isdigit()]
        if not indices:
            indices = list(range(min(10, len(instruments))))
        print(f"\n=== 生成试听 WAV ({len(indices)} 个) ===")
        for idx in indices:
            if idx < len(instruments):
                gen_wav(instruments[idx])

    elif do_wav_all:
        print(f"\n=== 生成全部试听 WAV ({len(instruments)} 个) ===")
        for inst in instruments:
            gen_wav(inst)

    elif do_wav_range:
        print(f"\n=== 生成范围试听 WAV ({range_start}-{range_end}) ===")
        for inst in instruments:
            if range_start <= inst['id'] <= range_end:
                gen_wav(inst)

    elif do_export:
        indices = [int(x) for x in args[args.index('--export')+1:] if x.isdigit()]
        print(f"\n=== 导出原始 WAV ({len(indices)} 个) ===")
        for idx in indices:
            if idx < len(instruments):
                inst = instruments[idx]
                if inst['n_samples'] < 10:
                    continue
                out_dir = os.path.join(OUT_DIR, 'export')
                os.makedirs(out_dir, exist_ok=True)
                cn = inst['name'].replace(' ', '_').replace('(', '').replace(')', '')
                wav_path = os.path.join(out_dir, f"{idx:03d}_{cn}.wav")
                with wave.open(wav_path, 'w') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(rate)
                    wf.writeframes(struct.pack(f'<{len(inst["pcm"])}h', *inst['pcm']))
                kb = len(inst['pcm']) * 2 / 1024.0
                print(f"    -> {wav_path} ({kb:.1f}KB)")

    else:
        # 无参数, 只列表
        print(f"\n提示:")
        print(f"  python yrw801_extract.py --wav 0 1 2 3      # 生成试听")
        print(f"  python yrw801_extract.py --wav-all          # 生成全部")
        print(f"  python yrw801_extract.py --wav-range 0 127  # 旋律乐器")
        print(f"  python yrw801_extract.py --export 0 1 2     # 导出原始波形")

    print(f"\nDone!")


if __name__ == "__main__":
    main()
