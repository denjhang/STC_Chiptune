# SF2 采样乐器精选

从多个 SF2 音色库提取、修复循环点、渲染试听后筛选的乐器列表。
所有采样已降采样至 17640Hz，存放在 `D:/working/vscode-projects/Reference_Project/STC-MCU/sf2_extract/` 下对应子目录。

## 音色库来源

| 库 | 路径 | 采样数 | 好 loop |
|---|------|--------|---------|
| SNES (31_Minutos) | `snes/` | 27 | 12 |
| GBA (Game Boy Advance) | `gba/` | 204 | 120 |
| SNES Unofficial | `snes_unofficial/` | 167 | 77 |
| microgm | `microgm/` | 343 | 51 |

## 全部候选 (25个, 按 ADPCM 从小到大)

| # | 乐器 | 来源 | 采样数 | PCM | ADPCM@17640 | orig_pitch |
|---|------|------|--------|------|-------------|------------|
| 1 | L_2 (Piano) | snes_unofficial #35 | 2328 | 4.5KB | 1.16KB | 40 |
| 2 | EB_257 (Slap Bass) | snes_unofficial #34 | 3669 | 7.2KB | 1.84KB | 26 |
| 3 | Shakuhachi 3 | microgm #211 | 3901 | 7.6KB | 1.95KB | 81 |
| 4 | SOM_8 (Oboe) | snes_unofficial #102 | 4021 | 7.9KB | 2.05KB | 28 |
| 5 | YC_33 (Trumpet) | snes_unofficial #45 | 4198 | 8.2KB | 2.13KB | 52 |
| 6 | Blow 1 | microgm #207 | 5153 | 10.1KB | 2.58KB | 60 |
| 7 | GT_9 (Oboe) | snes_unofficial #69 | 5468 | 10.7KB | 2.79KB | 21 |
| 8 | DKC2_27 (Strings) | snes_unofficial #50 | 6315 | 12.3KB | 3.21KB | 71 |
| 9 | SM_136 (Harp) | snes_unofficial #90 | 7373 | 14.4KB | 3.77KB | 73 |
| 10 | MP_95 (Guitar) | snes_unofficial #91 | 7444 | 14.5KB | 3.80KB | 40 |
| 11 | YC_25 (E.Piano) | snes_unofficial #44 | 9208 | 18.0KB | 4.60KB | 38 |
| 12 | FF4_5 (Pipe Organ) | snes_unofficial #47 | 11254 | 22.0KB | 5.74KB | 57 |
| 13 | DKC2_36 (E.Guitar) | snes_unofficial #51 | 11712 | 22.9KB | 5.86KB | 64 |
| 14 | DKC2_15 (Violin) | snes_unofficial #48 | 12806 | 25.0KB | 6.41KB | 64 |
| 15 | MMX_10 (Strings) | snes_unofficial #81 | 12559 | 24.5KB | 6.41KB | 52 |
| 16 | MMX_12 (Accordion) | snes_unofficial #82 | 12736 | 24.9KB | 6.50KB | 48 |
| 17 | SOM_6 (Voice) | snes_unofficial #101 | 13300 | 26.0KB | 6.79KB | 47 |
| 18 | SF_29 (Strings) | snes_unofficial #58 | 13723 | 26.8KB | 6.99KB | 48 |
| 19 | EB_174 (Sax) | snes_unofficial #30 | 15276 | 29.8KB | 7.64KB | 41 |
| 20 | Strings | snes #18 | 16640 | 32.5KB | 8.32KB | 63 |
| 21 | SM_54 (Voice) | snes_unofficial #87 | 19509 | 38.1KB | 9.96KB | 47 |
| 22 | FF3_15 (Voice) | snes_unofficial #96 | 20180 | 39.4KB | 10.30KB | 52 |
| 23 | FZ_9 (Tuba) | snes_unofficial #68 | 25933 | 50.7KB | 13.23KB | 50 |
| 24 | SOM_18 (Strings) | snes_unofficial #105 | 26299 | 51.4KB | 13.42KB | 50 |
| 25 | FF4_4 (Harp) | snes_unofficial #46 | 35280 | 68.9KB | 17.99KB | 57 |
| | **合计** | | **344298** | **672.3KB** | **172.1KB** | |

## 精选 (去重, 17个, ADPCM 91.9KB)

每组同类型只保留最小的一个，17 乐器覆盖 13 种音色类型。

| # | 乐器 | 来源 | 采样数 | PCM | ADPCM@17640 | orig_pitch |
|---|------|------|--------|------|-------------|------------|
| 1 | L_2 (Piano) | snes_unofficial #35 | 2328 | 4.5KB | 1.16KB | 40 |
| 2 | EB_257 (Slap Bass) | snes_unofficial #34 | 3669 | 7.2KB | 1.84KB | 26 |
| 3 | Shakuhachi 3 | microgm #211 | 3901 | 7.6KB | 1.95KB | 81 |
| 4 | SOM_8 (Oboe) | snes_unofficial #102 | 4021 | 7.9KB | 2.05KB | 28 |
| 5 | YC_33 (Trumpet) | snes_unofficial #45 | 4198 | 8.2KB | 2.13KB | 52 |
| 6 | Blow 1 | microgm #207 | 5153 | 10.1KB | 2.58KB | 60 |
| 7 | DKC2_27 (Strings) | snes_unofficial #50 | 6315 | 12.3KB | 3.21KB | 71 |
| 8 | SM_136 (Harp) | snes_unofficial #90 | 7373 | 14.4KB | 3.77KB | 73 |
| 9 | MP_95 (Guitar) | snes_unofficial #91 | 7444 | 14.5KB | 3.80KB | 40 |
| 10 | YC_25 (E.Piano) | snes_unofficial #44 | 9208 | 18.0KB | 4.60KB | 38 |
| 11 | FF4_5 (Pipe Organ) | snes_unofficial #47 | 11254 | 22.0KB | 5.74KB | 57 |
| 12 | DKC2_36 (E.Guitar) | snes_unofficial #51 | 11712 | 22.9KB | 5.86KB | 64 |
| 13 | DKC2_15 (Violin) | snes_unofficial #48 | 12806 | 25.0KB | 6.41KB | 64 |
| 14 | MMX_12 (Accordion) | snes_unofficial #82 | 12736 | 24.9KB | 6.50KB | 48 |
| 15 | SOM_6 (Voice) | snes_unofficial #101 | 13300 | 26.0KB | 6.79KB | 47 |
| 16 | EB_174 (Sax) | snes_unofficial #30 | 15276 | 29.8KB | 7.64KB | 41 |
| 17 | FZ_9 (Tuba) | snes_unofficial #68 | 25933 | 50.7KB | 13.23KB | 50 |
| | **合计** | | **183514** | **358.5KB** | **91.9KB** | |

去重去掉 8 个: GT_9(Oboe), SF_29/MMX_10/SOM_18/Strings(Strings), FF4_4(Harp), FF3_15/SM_54(Voice)

## 实际集成 (5个, ADPCM ~11.7KB)

从精选中筛选，原始 loop 接缝有问题的乐器通过 palindrome 构造救回。
Trumpet loop 太短 (12ms) ADPCM 状态无法闭合, Oboe2 与 Oboe 重复, 均删除。

| # | 乐器 | 来源 | 采样数 | orig_pitch | loop 方式 |
|---|------|------|--------|------------|-----------|
| 0 | Piano | snes_unofficial #35 | 2328 | 40 | 原始 (完美) |
| 1 | SlapBass | snes_unofficial #34 | 3669 | 26 | 原始 (完美) |
| 2 | Guitar | snes_unofficial #91 | 7444 | 40 | 原始 (完美) |
| 3 | Oboe (SOM_8) | snes_unofficial #102 | 4021 | 28 | Palindrome (救回) |
| 4 | Harp (SM_136) | snes_unofficial #90 | 7373 | 73 | Palindrome (偶然破音) |

## BRR 方案: 无状态编解码, 完美循环

ADPCM 有状态 (acc + step), loop 需要精确的状态闭合, 难以保证。
BRR (SNES SPC700) 是无状态压缩: 每 block 独立编解码, loop 只跳地址。

### BRR 格式 (参考 GME Spc_Dsp.cpp)

- 每 block 9 字节: 1 header + 8 data = 16 nibbles (16 samples)
- Header: [7:4]=scale (0-12), [3:2]=filter (0-3), [1]=loop, [0]=end
- 每 nibble = 4-bit signed (-8..7)
- Decode (GME bit-exact):
  ```
  shifts[0..15] right: 13,12,12,12,12,12,12,12,12,12,12,12,12,16,16,16
  shifts[16..31] left:  0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,11,11,11
  s = ((int16)nybbles >> right_shift) << left_shift  // uint16 截断
  // filter (header & 0x0C), p2 = prev2 >> 1
  // 0x4: s += p1>>1 + (-p1)>>5
  // 0x8: s += p1 - p2 + p2>>4 + (p1*-3)>>6
  // 0xC: s += p1 - p2 + (p1*-13)>>7 + (p2*3)>>4
  CLAMP16(s); s *= 2;
  ```
- Encode: `nib = sample >> (left_shift + 1)`, clamp -8..7

### filter=0 vs filter=2

| filter | 说明 | loop 无缝 | 音质 |
|--------|------|-----------|------|
| 0 | 无滤波, 真正无状态 | 完美 (seam=0) | 粗糙 (4-bit 量化噪声明显) |
| 2 | IIR 滤波, 有 p1/p2 状态 | 有咔哒 (状态跳变) | 较好 |

**filter=0 是唯一能保证无缝的方案**, 因为 filter=1/2/3 都依赖前两个样本的输出状态,
loop 回绕时 p1/p2 重置为 0 会导致 block 间跳变产生咔哒。

### Blow/Shakuhachi BRR 验证结果

两个乐器都能找到大量 seam=0 配置, attack 段最长可达 80ms:

| 乐器 | 最佳 attack | loop 长度 | filter | seam | RMS |
|------|-----------|---------|--------|------|-----|
| Blow | 80ms | 81ms | 0 | 0 | 22499 |
| Shakuhachi | 62ms | 61ms | 0 | 0 | 18902 |

### BRR 局限

- 4-bit 量化: round-trip max_err ~35000, rms ~15000 (16-bit scale)
- 音质粗糙, 但 chip-tune 风格可接受
- 动态范围: scale=12 时 decode peak = 7 * 4096 * 2 = 28672 (不是 32767)

### 待集成

BRR 解码器需要集成到 MCU firmware, 与现有 ADPCM 解码器并列:
- ADPCM 通道: 鼓声 (无 loop) + SF2 旋律乐器 (snapshot 回绕)
- BRR 通道: XI 旋律乐器 (filter=0, 无缝 loop)

## Bug 修复记录

### ADPCM loop_addr 基址偏移 (2026-06-11)

`sf2_rom.h` 中 `sf2_loop_start/loop_end` 是采样内部 nibble 偏移, 但 MCU 的 `addr` 是全局 nibble 地址。
Piano 的 `sf2_start=0` 碰巧没问题, Oboe/Harp 的 `sf2_start` 很大导致 loop 立刻触发回绕到错误 ROM 区域。
修复: `loop_addr = sf2_start[inst] + sf2_loop_start[inst]`

### ADPCM 插值溢出 (2026-06-11)

`s_prev - s_cur` (s16 差值最大 ~4094) 乘以 frac (u8) 溢出 s16。
修复: `(long)(s_cur - s_prev) * (long)frac >> 8`

### JEDI 表不一致 (2026-06-11)

Python 编码器用公式 `JEDI[step//16][nib]` 构建 JEDI 表, MCU 解码器用硬编码 `jedi_table[step+nib]`。
两种索引方式在 step 不是 16 倍数时值不同 (如 step=0 nib=2: Python=-10, MCU=+10)。
修复: gen_adpcm_rom.py 和 sf2_loop_sim.py 改用硬编码 JEDI_FLAT[784], 与 MCU jedi_table 完全一致。

### SF2 变频未生效 (2026-06-11)

SF2 note_on 路径 (0x15 + 0x33) 未设置 `pcm_pending_ch`, 导致 0x33 的 midi note 命令被跳过, step 保持 0。
修复: SF2 路径末尾加 `pcm_pending_ch = ch`。

### 当前状态 (5 乐器)

- Piano, SlapBass, Guitar, Oboe: 完美
- Harp: 偶然破音 (palindrome ADPCM 状态跳变 4117, 可用 ADSR 掩盖)

## 移除记录 (ADPCM 方案无法救回)

| 乐器 | 来源 | 问题 |
|------|------|------|
| Trumpet (YC_33) | snes_unofficial #45 | loop 太短 (12ms/214采样), ADPCM 状态无法闭合 → 删除 |
| Oboe2 (GT_9) | snes_unofficial #69 | 与 Oboe 重复 → 删除 |
| Blow 1 | microgm #207 | palindrome delta=127, 有咔哒 → 改用 BRR 方案 |
| Shakuhachi 3 | microgm #211 | palindrome delta=339, 有咔哒 → 改用 BRR 方案 |

## 发现: ADPCM 编码器 bug

Python 编码器用 `JEDI[step//16][nib]` 索引, MCU 解码器用 `JEDI_FLAT[step+nib]`。
两种索引方式在 step 不是 16 的倍数时给出不同值, 导致编码器和解码器状态不一致。
修复: 编码器改用 `JEDI_FLAT[step+nib]`。
详见 `tools/brr_test.py`。

## Loop 修复方法: Palindrome 构造

原始 SF2 的 loop_start/loop_end 处 PCM 幅值和斜率不匹配时，ADPCM 编码器在接缝处产生可闻咔哒。
snapshot 回绕只能修复漂移（每次循环误差累积），不能修复接缝处的初始跳变。

**Palindrome 方案** (参考 Polyphone):
1. 在采样中段找变化最小的连续段（差分绝对值之和最小）
2. 构造 palindrome: 正向段 + 反向段 (fwd + reverse(fwd[:-1]))
3. PCM 层面天然无缝: 反向结束值 = 正向起始值
4. ADPCM 层面: 编码器路径连续，palindrome 接缝处状态跳变小

**局限**: ADPCM 有状态编解码器，PCM 完美不代表 ADPCM 完美。
crossfade 可以改善 PCM 连续性但会改变编码路径。
Oboe/Harp 的 ADPCM 状态差足够小（delta=0/127）人耳不可闻；
Blow/Shakuhachi 差值过大（127/339）仍有可闻咔哒。
