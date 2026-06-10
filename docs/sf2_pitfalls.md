# SF2 (SoundFont2) 解析踩坑记录

## 工具链

- Python 3.9 + sf2utils (`pip install sf2utils`)
- MSYS2 自带 Python 3.12 没有pip，必须用 Windows Python 3.9
- 运行命令: `/c/Users/denjhang/AppData/Local/Programs/Python/Python39/python.exe`

## sf2utils 关键踩坑

### 1. 懒加载 raw_sample_data — 文件必须保持打开

`s.raw_sample_data` 不是在 `Sf2File(f)` 时读取的，而是**每次访问时从文件 seek+read**。如果 `with open()` 已关闭，访问 `raw_sample_data` 会抛 `ValueError: seek of closed file`。

**对策**: 所有需要 `raw_sample_data` 的操作必须在同一个 `with open(sf2_path, 'rb') as f:` 块内完成。不能先关闭文件再访问。

### 2. EOS 哨兵样本

SF2 文件最后一个 sample 的 name 是 `"EOS"` (End of Samples)，这不是真正的采样数据，而是 SoundFont 规范的结束标记。它没有 `start_loop`/`end_loop` 属性。

**对策**: 遍历 samples 时检查 `if s.name == 'EOS': break`，用 `hasattr(s, 'start_loop')` 保护。

### 3. Instrument 没有 zones 属性 — 用 bags

sf2utils 的 `Sf2Instrument` 没有 `.zones` 属性（这是其他库如 TinySoundFont 的叫法）。sf2utils 用的是 `.bags` (list of `Sf2Bag`)。

**sf2utils API**:
- `inst.bags` — 乐器区域的 bag 列表
- `bag.sample` — 关联的 Sf2Sample 对象 (或 None，全局 bag 无 sample)
- `bag.key_range` — `[lo, hi]` 或 None
- `bag.velocity_range` — `[lo, hi]` 或 None
- `bag.volume_envelope_attack/decay/sustain/release/hold` — 已计算好的秒数（cooked）
- `bag.cooked_loop_start/cooked_loop_end` — 已修正的循环点

### 4. sample 引用是对象不是索引

`bag.sample` 返回的是 `Sf2Sample` 对象引用，不是整数索引。需要用 `id(b.sample)` 做映射表查找对应的 sample index。

```python
sample_obj_to_idx = {id(s): i for i, s in enumerate(samples)}
sid = sample_obj_to_idx.get(id(b.sample))
```

### 5. Instrument bags 也可能需要文件打开

`inst.bags` 属性在某些 sf2utils 版本中也是延迟加载的，访问时可能需要文件打开。用 `try/except` 保护。

### 6. start 属性与 Sf2Sample.start 冲突

`Sf2Sample.start` 是一个方法（从 sf2parser 继承），不是 sample header 的 start 字段。但实际使用中它返回的是正确的整数值（sample header start index）。如果遇到问题，直接用 `s.smpl_offset + s.start` 等底层属性。

### 7. 打击乐 (Standard drum kit) 没有包络

Standard drum kit 的 bag 大多没有 envelope 参数（attack/decay/sustain/release 都是 None）。只有 Cymbal 等持续音打击乐有 decay。onshot 鼓 (Kick/Snare/HiHat) 没有任何包络。

## Loop 点踩坑

### 8. SF2 loop_start/loop_end 是相对索引

`Sf2Sample.start_loop` 和 `Sf2Sample.end_loop` 是**从该 sample 数据起始位置偏移 0 开始的索引**，不是 SF2 全局采样池的偏移。`raw_sample_data` 返回的就是从 offset 0 开始的该 sample 数据。

### 9. loop_start == loop_end — 无效 loop

很多 SF2 的 sample 标记了 `has_loop=True`，但 `start_loop == end_loop`（loop 长度为 0）。这不构成有效循环，PCM 播放时会触发除零或死循环。

**对策**: 播放端检查 `loop_end > loop_start` 才执行 loop wrap，否则当 oneshot 处理。

### 10. loop 点不连续 — loop click

**这是最常见的 SF2 质量问题。** 很多 SF2 文件的 loop_start 标记在静音区或波形跳变处，导致 loop_start 和 loop_end 处的采样值差异巨大（数千级别），播放时产生明显咔咔声。

**检测方法**: 比较 `pcm[loop_start]` 和 `pcm[loop_end]` 的绝对差值。差值 < 500 通常可接受，> 1000 一定有 click。

**修复方法**: `fix_loop_points()` — 在 loop_start ±200 采样范围内搜索与 loop_end 波形值最接近的点作为新 loop_start。实测 Marko.sf2 20+ 个坏 loop 全部可修到 diff < 100。

## 降采样后的 loop 点缩放

降采样后 loop 点必须按比例缩放:
```python
ratio = len(resampled) / len(original)
rs_loop_start = int(loop_start * ratio)
rs_loop_end = int(loop_end * ratio)
```

---

# SF2 音色库评测

测试环境: PC Python 仿真, 17640Hz 降采样, PCM float 模式, 默认包络 atk=10ms/dec=500ms/sus=30%/rel=300ms

## 1. Marko.sf2 — 不推荐

| 项目 | 数据 |
|------|------|
| 文件大小 | 184KB |
| 采样数 | 27 |
| 采样率 | 32000Hz 统一 |
| 乐器 | 钢琴、长笛、吉他、小提琴、人声合唱、管风琴、钢片琴等 |
| loop ok | ~2/25 |
| loop bad | ~23/25 |

**评价**: loop 点几乎全部损坏。Grand Piano 的 loop_start 标在静音区 (val=0)，loop_end 标在波形中间 (val=-6741)，差值 6741。只有 Flute 2 和 Clean Guitar 的 loop 可用。envelope 数据也大量缺失 (attack/decay 为 None)。**不推荐使用，典型的垃圾 SF2。**

## 2. 31_Minutos_SNES_Soundfont__Fanmade_.sf2 — 推荐

| 项目 | 数据 |
|------|------|
| 文件大小 | 406KB |
| 采样数 | 27 |
| 采样率 | 混合 (8448Hz~48000Hz) |
| 乐器 | Brass, Lead Guitar, Electric Bass, Strings, Nylon Guitar, Distorted Guitar 等 |
| loop ok | 9/12 |
| loop bad | 3/12 |

**评价**: loop 质量优秀。Brass/Lead Guitar/Electric Bass/Nylon Guitar/Strings/Crash Cymbal 的 loop_start 和 loop_end 完全相同 (diff=0)，无 click。采样较短 (0.1~0.9s)，loop 区域占比大。只有 Cloudness Synth/Sine Wave/Organ 三个 loop 不连续。适合做复古 8-bit 风格乐器采样。

**注意**: Sine Wave 的 loop_start=0，这是方波/正弦类乐器的常见做法，起点不一定有问题。

## 3. SMW_New_Version_.sf2 — 一般

| 项目 | 数据 |
|------|------|
| 文件大小 | 1.9MB |
| 采样数 | 45 |
| 采样率 | 8344Hz~102000Hz 混合 (极端!) |
| 乐器 | SMW piano, E.Piano, violin, trombone, sax, harp, banjo, guitar, square wave, 各种打击乐 |
| loop ok | 32/34 |
| loop bad | 2/34 |

**评价**: loop 质量好，但采样率极其混乱。fretlessbass 标称 102000Hz (明显错误，实际是 8-bit ADC 采样)。很多采样名是缩写或代号 (pncL, dddddL, ertyR)。大量 loop_start == loop_end 的无效 loop（标记了 loop 但实际无循环区域）。打击乐 kit 映射较完整 (kick/snare/hihat/bongo)。

**注意**: 一些采样 (fretlessbass, jazzguitar) 降采样到 17640Hz 后只有 ~170 个采样，loop 区域极短，音质很差。

## 4. Super_Nintendo_Unofficial_update.sf2 — 推荐 (量大)

| 项目 | 数据 |
|------|------|
| 文件大小 | 1.9MB |
| 采样数 | 167 |
| 乐器数 | 166 |
| 预设数 | 130 |
| 采样率 | 混合 (8000Hz~44100Hz) |
| loop ok | 83/123 |
| loop bad | 40/123 |

**评价**: 音色库最大最全。涵盖 SMW/SNES/FF/Zelda/Kirby/Donkey Kong/Mario RPG 等经典游戏的音色。好 loop 有 83 个，足够挑选。命名规范 (SMW_*, TA_*, MP_*, FF4_*, DKC_*)。打击乐完整。

**注意**: 约 1/3 的 loop 有问题，需要 fix_loop_points 修正。采样长度差异大 (100~30000+)，需要按 RAM 容量筛选。

## 5. General_Game_Boy_Advance_Soundfont.sf2 — 强烈推荐

| 项目 | 数据 |
|------|------|
| 文件大小 | 4.6MB |
| 采样数 | 204 |
| 乐器数 | 135 |
| 预设数 | 137 |
| 采样率 | 混合 (2000Hz~44100Hz)，集中在 10kHz~22kHz |
| loop ok | 115/154 |
| loop bad | 34/154 |
| oneshot | 50 |

**评价**: 量最大质最好。涵盖 GBA 标准音色集: 钢琴、风琴、吉他(清音/失真/尼龙/爵士)、贝斯(指弹/拍击/无品)、管乐(小号/长号/萨克斯/双簧管)、弦乐(小提琴/大提琴)、合成器(Square/Saw/Sweep Pad)、世界乐器(西塔/古琴/卡林巴/排箫)及完整打击乐套件。115 个 loop 完美连续。

**Top loop 精选**:
- Piccolo (63825 samples, loop 49572) — 超长 loop
- Space Voice (63337 samples, loop 43259) — 合成铺底音色
- 5th Saw Wave (31481 samples, loop 29338) — 锯齿波合成器
- Contrabass (43019 samples, loop 28616) — 低音弦乐 diff=0
- Goblin (46346 samples, loop 26717) — 特色音色
- Harmonica (48269 samples, loop 26164) — 口琴 diff=0
- Sweep Pad (73490 samples, loop 24882) — 合成垫底
- French Horn (32039 samples, loop 14027) — 圆号 diff=0
- Trumpet (22595 samples, loop 9431) — 小号 diff=2
- Church Organ 2 (23463 samples, loop 9504) — 管风琴 diff=0

**注意**: 34 个坏 loop 需 fix_loop_points。采样率分布散，大部分在 10~22kHz 之间降采样到 17640Hz 质量可接受。有两个重复文件 (同名和 (1) 后缀)，内容相同可删其一。

## 适配 STC32G 的建议

1. **采样率**: 目标 17640Hz，原始采样率越接近越好。高于 32000Hz 的降采样损失小，低于 16000Hz 的不要用
2. **采样长度**: ADPCM 编码后 1 byte = 2 samples，STM32 64KB Flash 可放 ~130000 samples。按 17640Hz 约 7.4 秒单音。实际多音色需更短
3. **loop 区域**: 优先选 loop 区域长的 (比例 >50%)，loop 延音质量直接决定音色好坏
4. **loop 修正**: fix_loop_points() 可自动修复大部分坏 loop，但仅限于 loop_start 附近有正确波形的情况
5. **推荐音色库**:
   - **首选** General_Game_Boy_Advance — 量最大质最好，204 采样 137 预设，115 个完美 loop
   - **备选** 31_Minutos_SNES — 质量好但量少 (27 采样)
   - **补充** Super_Nintendo_Unofficial — 量大但 1/3 loop 需修
   - **不推荐** Marko.sf2 (loop 全坏) / SMW_New_Version (采样率混乱)
