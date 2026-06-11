#!/usr/bin/env python3
"""YRW801 (OPL4 Wave ROM) 解析 + 试听 WAV 生成

严格按照 ymf278b.c (libvgm) 实现:
  bits = (buf[0] & 0xC0) >> 6         0=8bit, 1=12bit, 2=16bit
  startaddr = buf[2] | (buf[1]<<8) | ((buf[0] & 0x3F) << 16)  22-bit
  loopaddr = buf[4] | (buf[3] << 8)   16-bit
  endaddr  = buf[6] | (buf[5] << 8)   16-bit 2's complement

渲染: 严格按照 ymf278b_pcm_update:
  pos (u16) + stepptr (u16) 分离
  stepptr += step; if stepptr >= 0x10000: pos = nextPos(pos, stepptr>>16); stepptr &= 0xFFFF
  sample = (getSample(pos) * (0x10000-stepptr) + getSample(nextPos(pos,1)) * stepptr) >> 16

用法:
    python yrw801_extract.py                          # 列出所有乐器
    python yrw801_extract.py --wav 0 1 2 3 4 5        # 生成指定乐器 C4 试听
    python yrw801_extract.py --wav-all                 # 生成全部 175 个乐器试听
    python yrw801_extract.py --wav-range 0 127        # 生成旋律乐器 0-127
    python yrw801_extract.py --export 0 1 2 3          # 导出精选乐器原始波形 WAV
"""

import struct, os, sys, wave

ROM_PATH = 'D:/working/vscode-projects/Reference_Project/vgm_libs/libvgm-master/emu/cores/yrw801.rom'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yrw801_out')

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


def get_sample(rom, bits, startaddr, pos):
    """ymf278b_getSample, bit-exact

    返回 INT16 (-32768..32767).
    C 中 sample 是 INT16, 高位自然带符号.
    Python 中需要手动 sign-extend: val >= 0x8000 则 val -= 0x10000
    """
    if bits == 0:
        v = rom[startaddr + pos] << 8
    elif bits == 1:
        addr = startaddr + ((pos >> 1) * 3)
        if pos & 1:
            v = (rom[addr + 2] << 8) | (rom[addr + 1] & 0xF0)
        else:
            v = (rom[addr] << 8) | ((rom[addr + 1] & 0x0F) << 4)
    elif bits == 2:
        addr = startaddr + (pos * 2)
        v = (rom[addr] << 8) | rom[addr + 1]
    else:
        return 0
    return v - 0x10000 if v >= 0x8000 else v


def next_pos(pos, step, endaddr, loopaddr):
    """ymf278b_nextPos, bit-exact

    pos += step
    if ((u32)pos + endaddr >= 0x10000): pos = pos + endaddr + loopaddr
    """
    pos = (pos + step) & 0xFFFF
    if (pos + endaddr) & 0xFFFF == 0 or (pos + endaddr) >= 0x10000:
        pos = (pos + endaddr + loopaddr) & 0xFFFF
    return pos


def parse_rom(rom_data):
    """解析 YRW801 ROM, 返回乐器列表"""
    instruments = []
    MAX_INST = 175
    n_inst = 0
    for idx in range(0, min(len(rom_data) - 12, MAX_INST * 12), 12):
        b = rom_data[idx:idx+12]
        bits = (b[0] & 0xC0) >> 6
        startaddr = b[2] | (b[1] << 8) | ((b[0] & 0x3F) << 16)
        loopaddr = (b[4] << 8) | b[3]
        endaddr = (b[6] << 8) | b[5]

        if bits > 2:
            break
        if startaddr >= len(rom_data):
            break

        n_inst += 1

    meta_end = n_inst * 12
    print(f"元数据表: {n_inst} 乐器, {meta_end} 字节")

    for idx in range(0, meta_end, 12):
        b = rom_data[idx:idx+12]
        bits = (b[0] & 0xC0) >> 6
        startaddr = b[2] | (b[1] << 8) | ((b[0] & 0x3F) << 16)
        loopaddr = (b[4] << 8) | b[3]
        endaddr = (b[6] << 8) | b[5]
        attack_reg = (b[8] >> 4) & 0xf
        decay1_reg = b[8] & 0xf
        decay2_reg = b[9] & 0xf
        decay_level = (b[9] >> 4) & 0xf
        release_reg = b[10] & 0xf
        key_rate_scale = (b[10] >> 4) & 0xf
        lfo_vib = b[7]
        lfo_amp = b[11] & 0xf

        if endaddr == 0:
            n_samples = min(0x10000, (len(rom_data) - startaddr) // (3 if bits == 1 else (2 if bits == 2 else 1)))
            has_loop = False
        else:
            n_samples = (0x10000 - endaddr) & 0xFFFF
            has_loop = loopaddr < n_samples

        inst_id = idx // 12
        if inst_id < 128:
            name = GM_NAMES[inst_id] if inst_id < len(GM_NAMES) else f"Melody {inst_id}"
        else:
            pid = inst_id - 128
            name = PERC_NAMES[pid] if pid < len(PERC_NAMES) else f"Perc {pid}"

        inst = {
            'id': inst_id,
            'name': name,
            'bits': bits,
            'startaddr': startaddr,
            'loopaddr': loopaddr,
            'endaddr': endaddr,
            'n_samples': n_samples,
            'has_loop': has_loop,
            'attack': attack_reg,
            'decay1': decay1_reg,
            'decay2': decay2_reg,
            'decay_level': decay_level,
            'release': release_reg,
            'key_rate_scale': key_rate_scale,
            'lfo_vib': lfo_vib,
            'lfo_amp': lfo_amp,
        }
        instruments.append(inst)

    return instruments


def render_voice(rom, inst, dur, rate, midi_note=60, orig_pitch=60):
    """严格按照 ymf278b_pcm_update 渲染

    ROM 采样率 = 22050Hz, YMF278B 以 44100Hz 输出, 内部 2x 上采样插值
    calcStep(0, 0) = 0x8000 -> 每 2 个输出 sample 前进 1 个 PCM sample

    pos (u16), stepptr (u16) 分离
    每帧: stepptr += step (u16.16 fixed-point)
          if stepptr >= 0x10000: pos = nextPos(pos, stepptr>>16); stepptr &= 0xFFFF
    sample = (getSample(pos) * (0x10000-stepptr) + getSample(nextPos(pos,1)) * stepptr) >> 16

    顺序: 先取样本 (插值), 再步进 (ymf278b_pcm_update line 818-856)
    """
    bits = inst['bits']
    startaddr = inst['startaddr']
    loopaddr = inst['loopaddr']
    endaddr = inst['endaddr']
    has_loop = inst['has_loop']

    semi = midi_note - orig_pitch
    # calcStep(OCT=0, FN=0) = 0x8000; 每半音 step *= 2^(1/12)
    step = int(0x8000 * (2.0 ** (semi / 12.0)))
    step = max(1, min(0xFFFFFF, step))

    n_frames = int(dur * rate)
    out = []

    pos = 0
    stepptr = 0
    note_off_time = dur * 0.8

    for i in range(n_frames):
        t = i / rate

        # 先取样本 (插值) — ymf278b_pcm_update line 818-819
        s0 = get_sample(rom, bits, startaddr, pos)
        next_p = next_pos(pos, 1, endaddr, loopaddr)
        s1 = get_sample(rom, bits, startaddr, next_p)
        sample = (s0 * (0x10000 - stepptr) + s1 * stepptr) >> 16

        # 再步进 — ymf278b_pcm_update line 851-856
        stepptr += step
        while stepptr >= 0x10000:
            pos = next_pos(pos, stepptr >> 16, endaddr, loopaddr)
            stepptr &= 0xFFFF

        # 自然 envelope: 快 attack, 柔和 sustain, 慢 release
        if t < 0.005:
            e = t / 0.005
        elif t < 0.05:
            e = 1.0 - 0.1 * ((t - 0.005) / 0.045)
        elif t < note_off_time:
            e = 0.9
        else:
            rel = (t - note_off_time) / (dur - note_off_time)
            e = max(0, 0.9 * (1.0 - rel * rel))

        out.append(max(-32768, min(32767, int(sample * e))))

    return out


def export_raw_pcm(rom, inst, rate):
    """导出原始 PCM (attack + loop), 16-bit signed WAV"""
    bits = inst['bits']
    startaddr = inst['startaddr']
    loopaddr = inst['loopaddr']
    endaddr = inst['endaddr']
    n_samples = inst['n_samples']

    pcm = []
    for j in range(n_samples):
        s = get_sample(rom, bits, startaddr, j)
        pcm.append(s if s < 0x8000 else s - 0x10000)
    return pcm


def main():
    print(f"加载 YRW801 ROM: {ROM_PATH}")
    with open(ROM_PATH, 'rb') as f:
        rom_data = f.read()
    print(f"  ROM 大小: {len(rom_data)} bytes ({len(rom_data)/1024/1024:.1f} MB)")

    instruments = parse_rom(rom_data)

    print(f"\n=== YRW801 乐器列表 ({len(instruments)} 个) ===\n")

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
        bits_str = ["8bit", "12bit", "16bit", "???"][inst['bits']]
        loop_tag = f" loop={inst['loopaddr']} end=0x{inst['endaddr']:04x}" if inst['has_loop'] else " ONESHOT"
        kb = inst['n_samples'] / 1024.0

        if pid < 128:
            print(f"  {pid:3d}: {inst['name']:25s} {bits_str:4s} {inst['n_samples']:6d}s ({kb:5.1f}KB){loop_tag} sa=0x{inst['startaddr']:06x} atk={inst['attack']} d1={inst['decay1']} d2={inst['decay2']} sl={inst['decay_level']} rel={inst['release']}")
        else:
            print(f"  {pid:3d}: {inst['name']:25s} {bits_str:4s} {inst['n_samples']:6d}s ({kb:5.1f}KB){loop_tag}")

    rate = 44100
    dur = 3.0

    def gen_wav(inst, subdir='wav'):
        if inst['n_samples'] < 10:
            print(f"    跳过 {inst['id']}: 采样太少 ({inst['n_samples']})")
            return

        out_dir = os.path.join(OUT_DIR, subdir)
        os.makedirs(out_dir, exist_ok=True)

        orig_pitch = 60
        out_samples = render_voice(rom_data, inst, dur, rate, 60, orig_pitch)

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
                pcm = export_raw_pcm(rom_data, inst, rate)
                cn = inst['name'].replace(' ', '_').replace('(', '').replace(')', '')
                wav_path = os.path.join(out_dir, f"{idx:03d}_{cn}.wav")
                with wave.open(wav_path, 'w') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(rate)
                    wf.writeframes(struct.pack(f'<{len(pcm)}h', *pcm))
                kb = len(pcm) * 2 / 1024.0
                print(f"    -> {wav_path} ({kb:.1f}KB)")

    else:
        print(f"\n提示:")
        print(f"  python yrw801_extract.py --wav 0 1 2 3      # 生成试听")
        print(f"  python yrw801_extract.py --wav-all          # 生成全部")
        print(f"  python yrw801_extract.py --wav-range 0 127  # 旋律乐器")
        print(f"  python yrw801_extract.py --export 0 1 2     # 导出原始波形")

    print(f"\nDone!")


if __name__ == "__main__":
    main()
