#!/usr/bin/env python3
"""XI 乐器试听: 包络 + 循环渲染

从 YRW801 XI 文件中选取 10 个代表性乐器，渲染 C4 试听 WAV。
"""
import struct, os, wave, math

XI_DIR = 'D:/working/vscode-projects/Reference_Project/STC-MCU/sootsound/0000_all_instruments/'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xi_out', 'demo')
os.makedirs(OUT_DIR, exist_ok=True)

OUT_RATE = 22050

PICKS = [
    '10_Drawbar_Organ.xi',
    '23_Fretless_Bass.xi',
    '16_Harmonica.xi',
    '1C_Muted_Guitar.xi',
    '4A_Recorder.xi',
    '6B_Koto.xi',
    '0D_Xylophone.xi',
    '5E_Halo_Pad_L0.xi',
    '4E_Whistle.xi',
    '0F_Dulcimer_L0.xi',
]


def parse_xi_pcm(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    if data[:21] != b'Extended Instrument: ':
        return None, None

    name = data[21:43].split(b'\x00')[0].decode('ascii', errors='replace')
    num_samples = struct.unpack_from('<H', data, 296)[0]
    vol_flags = data[266]
    vol_pts = data[258]
    vol_fade = struct.unpack_from('<H', data, 280)[0]

    # Vol envelope: 12 points, each (x:u16, y:u16) = 4 bytes
    ve_off = 66 + 96
    vol_env = []
    for j in range(12):
        x = struct.unpack_from('<H', data, ve_off + j*4)[0]
        y = struct.unpack_from('<H', data, ve_off + j*4 + 2)[0]
        vol_env.append((x, y))

    sh_off = 298
    so = sh_off
    slen = struct.unpack_from('<I', data, so)[0]
    lstart = struct.unpack_from('<I', data, so+4)[0]
    llen = struct.unpack_from('<I', data, so+8)[0]
    vol = data[so+12]
    fine = struct.unpack_from('b', data, so+13)[0]
    flags = data[so+14]
    relnote = struct.unpack_from('b', data, so+16)[0]

    is_16 = bool(flags & 0x10)
    loop_type = flags & 0x03
    n_samp = slen // 2 if is_16 else slen
    loop_s = lstart // 2 if is_16 else lstart
    loop_l = llen // 2 if is_16 else llen
    center_rate = 8363.0 * (2.0 ** ((relnote + fine / 128.0) / 12.0))

    pcm_off = sh_off + num_samples * 40
    pcm = []
    if is_16:
        acc = 0
        for i in range(n_samp):
            delta = struct.unpack_from('<h', data, pcm_off + i*2)[0]
            acc += delta
            pcm.append(max(-32768, min(32767, acc)))
    else:
        acc = 0
        for i in range(n_samp):
            delta = struct.unpack_from('b', data, pcm_off + i)[0]
            acc += delta
            pcm.append(max(-128, min(127, acc)) * 256)

    info = {
        'name': name, 'n_samples': n_samp,
        'loop_start': loop_s, 'loop_end': loop_s + loop_l,
        'has_loop': loop_type > 0,
        'center_rate': center_rate, 'relnote': relnote, 'fine': fine,
        'volume': vol,
        'vol_env_on': bool(vol_flags & 1),
        'vol_env': vol_env[:vol_pts],
        'vol_fade': vol_fade,
    }
    return info, pcm


def render(pcm, info, dur, rate, midi_note=60):
    n_pcm = len(pcm)
    loop_s = info['loop_start']
    loop_e = info['loop_end']
    has_loop = info['has_loop']
    loop_len = loop_e - loop_s if has_loop else 0
    vol = info['volume'] / 64.0

    # Pitch: native pitch at MIDI note (24 + relnote + fine/128)
    native_midi = 24 + info['relnote'] + info['fine'] / 128.0
    step = 2.0 ** ((midi_note - native_midi) / 12.0)

    # Envelope
    env_lut = None
    if info['vol_env_on'] and len(info['vol_env']) >= 2:
        tick_rate = 50.0
        n_ticks = int(dur * tick_rate)
        env_pts = info['vol_env']
        env_lut = []
        for t in range(n_ticks):
            seg = 0
            for j in range(len(env_pts)-1):
                if env_pts[j][0] <= t < env_pts[j+1][0]:
                    seg = j
                    break
            else:
                seg = len(env_pts) - 2
            x0, y0 = env_pts[seg]
            x1, y1 = env_pts[seg+1]
            frac = (t - x0) / max(1, x1 - x0)
            frac = max(0.0, min(1.0, frac))
            env_lut.append((y0 + (y1 - y0) * frac) / 64.0)

    n_frames = int(dur * rate)
    out = []
    pos = 0.0
    note_off = int(dur * 0.7 * rate)

    for i in range(n_frames):
        ipos = int(pos)
        if has_loop and loop_len > 0:
            while ipos >= loop_e:
                ipos = loop_s + (ipos - loop_s) % loop_len
        elif ipos >= n_pcm:
            out.append(0)
            pos += step
            continue

        frac_pos = pos - int(pos)
        p1 = ipos + 1
        if has_loop and p1 >= loop_e:
            p1 = loop_s
        elif p1 >= n_pcm:
            p1 = n_pcm - 1

        sample = pcm[ipos] + (pcm[p1] - pcm[ipos]) * frac_pos

        # Envelope
        if env_lut is not None:
            tick_idx = int(i / rate * 50.0)
            if tick_idx < len(env_lut):
                e = env_lut[tick_idx]
            else:
                e = env_lut[-1] if env_lut else 1.0
            if i > note_off:
                rel = (i - note_off) / max(1, n_frames - note_off)
                e *= max(0, 1.0 - rel)
        else:
            t_sec = i / rate
            if t_sec < 0.003:
                e = t_sec / 0.003
            elif i < note_off:
                e = 1.0
            else:
                rel = (i - note_off) / max(1, n_frames - note_off)
                e = max(0, 1.0 - rel * rel)

        out.append(max(-32768, min(32767, int(sample * e * vol))))
        pos += step

    return out


def main():
    for pick in PICKS:
        filepath = os.path.join(XI_DIR, pick)
        if not os.path.exists(filepath):
            print(f'  SKIP {pick}')
            continue

        info, pcm = parse_xi_pcm(filepath)
        if not info or not pcm:
            print(f'  FAIL {pick}')
            continue

        for note in [60, 72]:
            note_name = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
            nn = f'{note_name[note%12]}{note//12-1}'
            out = render(pcm, info, 3.0, OUT_RATE, midi_note=note)

            cn = pick.replace('.xi', '')
            wav_path = os.path.join(OUT_DIR, f'{cn}_{nn}.wav')
            with wave.open(wav_path, 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(OUT_RATE)
                wf.writeframes(struct.pack('<%dh' % len(out), *out))

            peak = max(abs(s) for s in out) if out else 0
            rms = (sum(s*s for s in out)/len(out))**0.5 if out else 0
            print(f'  {cn:30s} {nn:3s} {info["n_samples"]:6d}pts loop=[{info["loop_start"]}..{info["loop_end"]}] '
                  f'env={"ON" if info["vol_env_on"] else "auto"} peak={peak} rms={rms:.0f}')

    print(f'\nDone! WAV files in {OUT_DIR}')


if __name__ == '__main__':
    main()
