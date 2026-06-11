#!/usr/bin/env python3
"""YRW801 XI 乐器文件批量解析 + WAV 导出

基于 OpenMPT XMTools.h 的 XIInstrumentHeader 结构解析标准 XI 文件。
支持 delta-encoded 16-bit/8-bit PCM 解码 + 线性插值循环播放。

用法:
    python xi_parse.py                           # 列出所有乐器
    python xi_parse.py --wav 0x10 0x16           # 导出指定乐器 C4 试听
    python xi_parse.py --export 0x10 0x16        # 导出原始 16-bit PCM WAV
    python xi_parse.py --csv                     # 输出 CSV 统计表
"""

import struct, os, sys, wave, math, glob

XI_DIR = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sootsound/0000_all_instruments/'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xi_out')

# XM/XI standard: 8363 Hz at relnote=0, finetune=0 (corresponds to C-2 = MIDI 24)
XM_BASE_RATE = 8363
MIDI_BASE = 24  # C-2

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


def parse_xi(filepath):
    """Parse standard XI file (OpenMPT XIInstrumentHeader layout)"""
    with open(filepath, 'rb') as f:
        data = f.read()

    if data[:21] != b'Extended Instrument: ':
        return None

    name = data[21:43].split(b'\x00')[0].decode('ascii', errors='replace')
    tracker = data[44:64].split(b'\x00')[0].decode('ascii', errors='replace')
    version = struct.unpack_from('<H', data, 64)[0]

    # XMInstrument at offset 66 (230 bytes)
    off = 66
    sample_map = list(data[off:off+96])

    # Vol/Pan envelopes (24 u16 values each)
    ve_off = off + 96
    vol_env = [struct.unpack_from('<H', data, ve_off + j*2)[0] for j in range(24)]
    pe_off = ve_off + 48
    pan_env = [struct.unpack_from('<H', data, pe_off + j*2)[0] for j in range(24)]

    # Envelope params
    ep = pe_off + 48
    vol_pts = data[ep]; pan_pts = data[ep+1]
    vol_sus = data[ep+2]; vol_lp_s = data[ep+3]; vol_lp_e = data[ep+4]
    pan_sus = data[ep+5]; pan_lp_s = data[ep+6]; pan_lp_e = data[ep+7]
    vol_flags = data[ep+8]; pan_flags = data[ep+9]
    vib_type = data[ep+10]; vib_sweep = data[ep+11]
    vib_depth = data[ep+12]; vib_rate = data[ep+13]
    vol_fade = struct.unpack_from('<H', data, ep+14)[0]

    # numSamples at offset 296
    num_samples = struct.unpack_from('<H', data, 296)[0]

    # Sample headers (40 bytes each) at offset 298
    sh_off = 298
    samples = []
    for s in range(num_samples):
        so = sh_off + s * 40
        slen = struct.unpack_from('<I', data, so)[0]
        lstart = struct.unpack_from('<I', data, so+4)[0]
        llen = struct.unpack_from('<I', data, so+8)[0]
        vol = data[so+12]
        fine = struct.unpack_from('b', data, so+13)[0]
        flags = data[so+14]
        pan = data[so+15]
        relnote = struct.unpack_from('b', data, so+16)[0]
        sname = data[so+18:so+40].split(b'\x00')[0].decode('ascii', errors='replace')

        is_16 = bool(flags & 0x10)
        loop_type = flags & 0x03
        n_samp = slen // 2 if is_16 else slen

        # centerRate = 8363 * 2^((relnote + fine/128) / 12)
        center_rate = XM_BASE_RATE * (2.0 ** ((relnote + fine / 128.0) / 12.0))

        samples.append({
            'bytes': slen, 'n_samples': n_samp,
            'loop_start': lstart, 'loop_length': llen,
            'loop_end': lstart + llen,
            'has_loop': loop_type > 0, 'loop_type': loop_type,
            'is_16bit': is_16, 'relnote': relnote, 'fine': fine,
            'volume': vol, 'pan': pan, 'name': sname,
            'center_rate': center_rate,
        })

    # Decode all samples (delta -> absolute)
    sd_off = sh_off + num_samples * 40
    for s in samples:
        pcm = decode_sample(data, sd_off, s)
        s['pcm'] = pcm
        sd_off += s['bytes']

    return {
        'filename': os.path.basename(filepath),
        'name': name, 'tracker': tracker, 'version': version,
        'num_samples': num_samples,
        'vol_flags': vol_flags, 'pan_flags': pan_flags,
        'vol_pts': vol_pts, 'pan_pts': pan_pts,
        'vol_sus': vol_sus, 'vol_loop': (vol_lp_s, vol_lp_e),
        'vol_fade': vol_fade,
        'sample_map': sample_map,
        'samples': samples,
        'file_size': len(data),
    }


def decode_sample(data, offset, sample_info):
    """Decode delta-encoded PCM sample data"""
    is_16 = sample_info['is_16bit']
    n = sample_info['n_samples']
    pcm = []

    if is_16:
        acc = 0
        for i in range(n):
            delta = struct.unpack_from('<h', data, offset + i*2)[0]
            acc += delta
            pcm.append(max(-32768, min(32767, acc)))
    else:
        acc = 0
        for i in range(n):
            delta = struct.unpack_from('b', data, offset + i)[0]
            acc += delta
            pcm.append(max(-128, min(127, acc)) * 256)

    return pcm


def render_xi(inst, sample_idx=0, midi_note=60, dur=3.0, rate=44100):
    """Render XI instrument at given MIDI note with loop"""
    if sample_idx >= len(inst['samples']):
        return []

    s = inst['samples'][sample_idx]
    pcm = s['pcm']
    if not pcm:
        return []

    n_pcm = len(pcm)
    loop_start = s['loop_start'] // (2 if s['is_16bit'] else 1)
    loop_end = s['loop_end'] // (2 if s['is_16bit'] else 1)
    has_loop = s['has_loop']

    # Pitch: midi_note vs center_rate
    # center_rate maps to MIDI_BASE (C-2 = 24)
    # pitch_ratio = rate / center_rate * 2^((midi_note - MIDI_BASE) / 12)
    center = s['center_rate']
    target_freq = rate * (2.0 ** ((midi_note - MIDI_BASE) / 12.0))
    # Actually simpler: ratio of desired freq to center freq
    # step in samples per output sample:
    step = center / rate * (2.0 ** ((midi_note - MIDI_BASE) / 12.0))

    n_frames = int(dur * rate)
    out = []
    pos = 0.0
    note_off_time = dur * 0.8

    for i in range(n_frames):
        t = i / rate

        # Integer position
        ipos = int(pos)
        if has_loop and ipos >= loop_end:
            ipos = loop_start + (ipos - loop_start) % (loop_end - loop_start)
        elif not has_loop and ipos >= n_pcm:
            out.append(0)
            pos += step
            continue

        frac = pos - int(pos)
        p0 = ipos
        p1 = ipos + 1
        if has_loop and p1 >= loop_end:
            p1 = loop_start
        elif p1 >= n_pcm:
            p1 = n_pcm - 1

        sample = pcm[p0] + (pcm[p1] - pcm[p0]) * frac

        # Simple envelope
        if t < 0.005:
            e = t / 0.005
        elif t < note_off_time:
            e = 1.0
        else:
            rel = (t - note_off_time) / (dur - note_off_time)
            e = max(0, 1.0 - rel * rel)

        out.append(max(-32768, min(32767, int(sample * e * s['volume'] / 64))))
        pos += step

        # Loop
        if has_loop and pos >= loop_end:
            pos = loop_start + (pos - loop_start) % (loop_end - loop_start)

    return out


def write_wav(path, samples, rate=44100):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack('<%dh' % len(samples), *samples))


def main():
    files = sorted(glob.glob(os.path.join(XI_DIR, '*.xi')))
    print(f"Found {len(files)} XI files in {XI_DIR}")

    instruments = []
    for f in files:
        info = parse_xi(f)
        if info:
            instruments.append(info)

    args = sys.argv[1:]
    do_wav = '--wav' in args
    do_export = '--export' in args
    do_csv = '--csv' in args

    if do_csv:
        print("filename,name,num_samples,total_pcm_bytes,has_loop,vol_env_on,vol_pts,vol_fade")
        for inst in instruments:
            total = sum(s['bytes'] for s in inst['samples'])
            has_loop = any(s['has_loop'] for s in inst['samples'])
            print(f"{inst['filename']},{inst['name']},{inst['num_samples']},"
                  f"{total},{has_loop},{bool(inst['vol_flags']&1)},{inst['vol_pts']},{inst['vol_fade']}")
        return

    # List all
    for inst in instruments:
        total_kb = sum(s['bytes'] for s in inst['samples']) / 1024
        has_env = bool(inst['vol_flags'] & 1)
        has_loop = sum(1 for s in inst['samples'] if s['has_loop'])
        print(f"  {inst['filename']:50s} {inst['num_samples']:2d} samp {total_kb:7.1f}KB "
              f"env={has_env} loop={has_loop}/{inst['num_samples']}")

    if do_wav:
        indices = [int(x, 16) if x.startswith('0x') or x.startswith('0X') else int(x)
                   for x in args[args.index('--wav')+1:]
                   if not x.startswith('-')]
        print(f"\n=== 生成试听 WAV ({len(indices)} 个) ===")
        for idx in indices:
            if idx < len(instruments):
                inst = instruments[idx]
                for si in range(min(1, inst['num_samples'])):
                    out = render_xi(inst, si, midi_note=60, dur=3.0)
                    cn = inst['name'].replace(' ', '_').replace('(', '').replace(')', '')
                    wav_path = os.path.join(OUT_DIR, 'wav', f"{inst['filename'][:2]}_{cn}_C4.wav")
                    write_wav(wav_path, out)
                    print(f"    -> {wav_path}")

    elif do_export:
        indices = [int(x, 16) if x.startswith('0x') or x.startswith('0X') else int(x)
                   for x in args[args.index('--export')+1:]
                   if not x.startswith('-')]
        print(f"\n=== 导出原始 WAV ({len(indices)} 个) ===")
        for idx in indices:
            if idx < len(instruments):
                inst = instruments[idx]
                for si, s in enumerate(inst['samples']):
                    cn = inst['name'].replace(' ', '_').replace('(', '').replace(')', '')
                    wav_path = os.path.join(OUT_DIR, 'export',
                                            f"{inst['filename'][:2]}_{cn}_s{si}.wav")
                    write_wav(wav_path, s['pcm'], rate=int(s['center_rate']))
                    print(f"    -> {wav_path} ({len(s['pcm'])} samples, {s['center_rate']:.0f} Hz)")
    else:
        print(f"\n提示:")
        print(f"  python xi_parse.py --wav 0x10 0x16       # 生成 C4 试听")
        print(f"  python xi_parse.py --export 0x10 0x16     # 导出原始 PCM")
        print(f"  python xi_parse.py --csv                  # 输出 CSV 统计")


if __name__ == "__main__":
    main()
