#!/usr/bin/env python3
"""SF2 解包工具 - 提取采样 + 循环点 + 包络 + 音高映射
输出 WAV + JSON 映射 + C 头文件, 适配 STC32G ADPCM 采样引擎"""

import os, sys, struct, wave, math, warnings, json
warnings.filterwarnings('ignore')

try:
    from sf2utils.sf2parse import Sf2File
except ImportError:
    print("pip install sf2utils")
    sys.exit(1)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))

def resample(src_samples, src_rate, dst_rate):
    if src_rate == dst_rate:
        return list(src_samples)
    ratio = src_rate / dst_rate
    n = int(len(src_samples) / ratio)
    out = []
    for j in range(n):
        pos = j * ratio
        idx = int(pos)
        frac = pos - idx
        if idx + 1 < len(src_samples):
            val = src_samples[idx] * (1 - frac) + src_samples[idx + 1] * frac
        else:
            val = src_samples[min(idx, len(src_samples) - 1)]
        out.append(int(val))
    return out

def fix_loop_points(pcm, loop_start, loop_end, search_range=200):
    """在 loop_start 附近搜索与 loop_end 波形最连续的点, 消除 loop click"""
    if loop_end <= loop_start or loop_end >= len(pcm):
        return loop_start, loop_end
    target = pcm[loop_end]
    best_idx = loop_start
    best_diff = abs(pcm[loop_start] - target)
    lo = max(0, loop_start - search_range)
    hi = min(len(pcm) - 1, loop_start + search_range)
    for j in range(lo, hi + 1):
        d = abs(pcm[j] - target)
        if d < best_diff:
            best_diff = d
            best_idx = j
    return best_idx, loop_end

def main():
    if len(sys.argv) < 2:
        print("用法: python sf2_extract.py <sf2文件> [target_rate]")
        sys.exit(1)

    sf2_path = sys.argv[1]
    target_rate = int(sys.argv[2]) if len(sys.argv) > 2 else 17640

    wav_dir = os.path.join(OUT_DIR, 'wav')
    os.makedirs(wav_dir, exist_ok=True)

    # 所有操作必须在 with open() 内, sf2utils 懒加载 raw_sample_data
    print(f"加载 SF2: {sf2_path}")
    with open(sf2_path, 'rb') as f:
        sf = Sf2File(f)

        # 过滤掉 EOS 哨兵
        samples = [s for s in sf.samples if s.name != 'EOS']
        sample_obj_to_idx = {}
        for i, s in enumerate(samples):
            sample_obj_to_idx[id(s)] = i

        print(f"  Presets: {len(sf.presets)}")
        print(f"  Instruments: {len(sf.instruments)}")
        print(f"  Samples: {len(samples)} (excl EOS)")
        print(f"  目标采样率: {target_rate}Hz")
        print()

        # Pass 1: 导出 WAV
        print("=== 提取采样 WAV ===")
        sample_map = {}
        for i, s in enumerate(samples):
            has_loop = hasattr(s, 'start_loop') and hasattr(s, 'end_loop') and s.start_loop < s.end_loop
            clean_name = s.name.lstrip('-').replace(' ', '_')

            raw = s.raw_sample_data  # 必须在文件打开期间读取!
            src_samples = struct.unpack(f'<{len(raw)//2}h', raw)
            src_rate = s.sample_rate if hasattr(s, 'sample_rate') else 44100
            dst_samples = resample(src_samples, src_rate, target_rate)

            # 修正 loop 点: 缩放到降采样后, 再搜索连续点
            orig_total = len(src_samples)
            if has_loop and orig_total > 0:
                ratio = len(dst_samples) / orig_total
                rs_ls = int(s.start_loop * ratio)
                rs_le = int(s.end_loop * ratio)
                rs_ls = max(0, min(rs_ls, len(dst_samples) - 1))
                rs_le = max(0, min(rs_le, len(dst_samples)))
                rs_ls, rs_le = fix_loop_points(dst_samples, rs_ls, rs_le)
            else:
                rs_ls, rs_le = 0, 0

            wav_path = os.path.join(wav_dir, f'{i:02d}_{clean_name}.wav')
            with wave.open(wav_path, 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(target_rate)
                wf.writeframes(struct.pack(f'<{len(dst_samples)}h', *dst_samples))

            sample_map[i] = {
                'name': clean_name,
                'src_rate': src_rate,
                'orig_pitch': s.original_pitch if hasattr(s, 'original_pitch') else 60,
                'pitch_correction': s.pitch_correction if hasattr(s, 'pitch_correction') else 0,
                'loop_start': rs_ls,
                'loop_end': rs_le,
                'has_loop': has_loop,
                'n_samples': len(dst_samples),
                'duration': len(dst_samples) / target_rate,
            }
            loop_tag = f" loop={rs_ls}->{rs_le}" if has_loop else " ONESHOT"
            print(f"  {i:2d}: {s.name:20s} {src_rate}Hz->{target_rate}Hz {len(dst_samples)}s ({sample_map[i]['duration']:.2f}s){loop_tag}")

        # Pass 2: instrument 映射 (用 sf2utils 的 bags API)
        print("\n=== 乐器映射 ===")
        instrument_data = []
        for i, inst in enumerate(sf.instruments):
            clean_name = inst.name.lstrip('-').replace(' ', '_')
            zones_info = []

            try:
                bags = inst.bags
            except:
                continue

            for b in bags:
                if b.sample is None:
                    continue
                sid = sample_obj_to_idx.get(id(b.sample))
                if sid is None:
                    continue

                kr = b.key_range
                vr = b.velocity_range

                atk = b.volume_envelope_attack
                hold = b.volume_envelope_hold
                dec = b.volume_envelope_decay
                sus = b.volume_envelope_sustain
                rel = b.volume_envelope_release

                zone_info = {
                    'sample_id': sid,
                    'key_range': kr,
                    'vel_range': vr,
                    'attack': atk,
                    'hold': hold,
                    'decay': dec,
                    'sustain': sus,
                    'release': rel,
                }
                zones_info.append(zone_info)

                sn = sample_map[sid]['name'] if sid in sample_map else f's{sid}'
                kr_str = f"{kr[0]}-{kr[1]}" if kr else "all"
                atk_str = f"{atk*1000:.0f}ms" if atk is not None else "?"
                dec_str = f"{dec*1000:.0f}ms" if dec is not None else "?"
                sus_str = f"{sus:.0f}%" if sus is not None else "?"
                rel_str = f"{rel*1000:.0f}ms" if rel is not None else "?"
                print(f"  {i:2d} {inst.name:20s} -> {sn:20s} key={kr_str} vel={'?' if not vr else f'{vr[0]}-{vr[1]}'} atk={atk_str} dec={dec_str} sus={sus_str} rel={rel_str}")

            if zones_info:
                instrument_data.append({'name': clean_name, 'zones': zones_info})

    # 输出 JSON 映射文件 (给 PC 仿真用)
    json_path = os.path.join(OUT_DIR, 'sf2_mapping.json')
    mapping = {
        'target_rate': target_rate,
        'samples': {str(k): v for k, v in sample_map.items()},
        'instruments': instrument_data,
    }
    with open(json_path, 'w') as f:
        json.dump(mapping, f, indent=2)

    # 输出 C 头文件
    h_path = os.path.join(OUT_DIR, 'sf2_samples.h')
    with open(h_path, 'w') as f:
        f.write("/* SF2 采样索引表 - 由 sf2_extract.py 生成 */\n\n")
        f.write(f"#define SF2_SAMPLE_COUNT {len(sample_map)}\n")
        f.write(f"#define SF2_TARGET_RATE  {target_rate}\n\n")

        f.write("typedef struct {\n")
        f.write("    u16 loop_start;  /* loop sample index (resampled) */\n")
        f.write("    u16 loop_end;    /* loop sample index (resampled) */\n")
        f.write("    u8  has_loop;   /* 1=loop, 0=oneshot */\n")
        f.write("    u8  orig_pitch; /* original MIDI pitch */\n")
        f.write("    u8  pitch_cor;  /* pitch correction (semitones) */\n")
        f.write("    u8  reserved;\n")
        f.write("} SF2_SampleInfo;\n\n")

        f.write("static const SF2_SampleInfo code sf2_samples[SF2_SAMPLE_COUNT] = {\n")
        for i in range(len(sample_map)):
            s = sample_map[i]
            cn = s['name'][:15]
            f.write(f"    /* {i:2d}: {cn} */\n")
            f.write(f"    {{ {s['loop_start']}, {s['loop_end']}, {int(s['has_loop'])}, {s['orig_pitch']}, {s['pitch_correction']}, 0 }},\n")
        f.write("};\n\n")

        f.write(f"#define SF2_INSTRUMENT_COUNT {len(instrument_data)}\n\n")
        for inst in instrument_data:
            cn = inst['name'][:15]
            f.write(f"/* {cn} */\n")
            for zi, z in enumerate(inst['zones']):
                sid = z['sample_id']
                kr = z['key_range']
                atk_ms = z['attack'] * 1000 if z['attack'] is not None else 0
                dec_ms = z['decay'] * 1000 if z['decay'] is not None else 0
                sus_pct = z['sustain'] if z['sustain'] is not None else 100
                rel_ms = z['release'] * 1000 if z['release'] is not None else 0
                kr_lo = kr[0] if kr else 0
                kr_hi = kr[1] if kr else 127
                f.write(f"/*   zone {zi}: sample={sid} key={kr_lo}-{kr_hi} atk={atk_ms:.0f}ms dec={dec_ms:.0f}ms sus={sus_pct:.0f}% rel={rel_ms:.0f}ms */\n")

    print(f"\n输出:")
    print(f"  WAV: {wav_dir}/ ({len(sample_map)} files)")
    print(f"  JSON: {json_path}")
    print(f"  C头文件: {h_path}")
    print(f"\nDone!")

if __name__ == "__main__":
    main()
