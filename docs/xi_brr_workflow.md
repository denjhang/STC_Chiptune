# YRW801 XI 乐器 → BRR ROM 工作流

## 概述

从 YRW801 (OPL4) ROM 解包的 XI 乐器文件出发，经过重采样、crossfade 修复、BRR 编码，
生成可在 STC32G 上无缝循环播放的 ROM 数据。

目标采样率: **17640Hz** (MCU DAC 甜点)
编码格式: **BRR filter=0** (4-bit 无状态, 9 字节/block, 16 采样/block)

## XI 文件来源

SootSound 工具包将 YRW801 ROM 的 175 个 GM 乐器解包为标准 FastTracker II XI 格式:
```
D:\working\vscode-projects\Reference_Project\STC-MCU\sootsound\0000_all_instruments\
```
共 230 个 XI 文件 (175 个 ROM 乐器 + 多 layer 拆分)。

## XI 文件格式 (OpenMPT XIInstrumentHeader)

```
offset 0:   signature[21]  "Extended Instrument: "
offset 21:  name[22]
offset 43:  eof            0x1A
offset 44:  trackerName[20]
offset 64:  version        u16 LE (0x0102)
offset 66:  XMInstrument (230 bytes):
  +66:  sampleMap[96]
  +162: volEnv[24]         12 个 (x:u16, y:u16) 对
  +210: panEnv[24]
  +258: volPts(u8), panPts(u8), volSus(u8), volLoopStart(u8), volLoopEnd(u8)
  +263: panSus, panLoopStart, panLoopEnd, volFlags, panFlags
  +268: vibType, vibSweep, vibDepth, vibRate
  +272: volFade(u16)
offset 296: numSamples     u16 LE  ← 关键! 和 XM 不同位置
offset 298: sample headers (numSamples × 40 bytes):
  +0:  length(u32)        字节长度
  +4:  loopStart(u32)     字节偏移
  +8:  loopLength(u32)
  +12: vol(u8)            0-64
  +13: finetune(i8)       -128..+127 (1/128 半音)
  +14: flags(u8)          bit0=forward loop, bit1=bidi, bit4=16bit
  +16: relnote(i8)        相对音高 (半音)
  +18: name[22]
  然后: delta-encoded PCM (16-bit 或 8-bit)
```

**注意**: XI 和 XM 的 InstrumentHeader 结构不同!
XM: numSamples 在 offset 27; XI: numSamples 在 offset 296。

### centerRate

```
centerRate = 8363 * 2^((relnote + finetune/128) / 12)
```
relnote=0, finetune=0 → 8363 Hz (对应 MIDI C-2 = note 24)

### PCM 解码

delta 编码, 需要累加还原:
```python
acc = 0
for i in range(n_samples):
    acc += read_delta()  # 16-bit or 8-bit
    pcm[i] = clamp(acc)
```

## 工作流

### Step 1: 重采样到 17640Hz

线性插值重采样。loop_start/loop_end 按比例换算:
```python
ratio = len(pcm_17640) / len(pcm_original)
loop_s = int(original_loop_start * ratio)
loop_e = int(original_loop_end * ratio)
```

### Step 2: PCM crossfade 修复 loop 接缝

重采样后 PCM 波形变化, 原始 loop 点不再连续。
crossfade 策略: 只改 tail (loop_e 前若干采样渐变到 loop_s 的值), head 不动。

```python
def crossfade_tail(pcm, loop_s, loop_e, fade_len):
    target = pcm[loop_s]
    for i in range(fade_len):
        t = (i + 1) / fade_len
        idx = loop_e - fade_len + i
        pcm[idx] = int(pcm[idx] * (1 - t) + target * t)
```

fade_len = loop 长度的 10%, 至少 8 采样, 至多 64。

### Step 3: BRR filter=0 编码

- loop_start 对齐到 16 采样边界
- 每 16 个采样一个 block, 每块自动选 scale (auto_scale)
- loop 起点 block 设置 loop flag (header bit 1)

```python
# encode
scale = auto_scale(block_pcm)
nib = sample >> (LEFT_SHIFT[scale] + 1)  # 4-bit 量化
# decode (filter=0)
s = ((int16(nybbles) >> RIGHT_SHIFT[scale]) & 0xFFFF) << LEFT_SHIFT[scale]
s *= 2  # BRR 输出增益
```

GME Spc_Dsp.cpp shifts 表:
```
RIGHT_SHIFT = [13,12,12,12,12,12,12,12,12,12,12,12,13,16,16,16]
LEFT_SHIFT  = [ 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,11,11,11]
```

### Step 4: BRR 层 crossfade 修复

BRR 4-bit 量化引入新的误差, PCM 层修好的接缝在 BRR 编码后又断了。
需要额外一轮修复:
1. 解码所有 BRR block → 得到真实解码值
2. 在解码值上 crossfade (tail → loop_start)
3. 重编码受影响的 block

**关键**: filter=0 无状态, 改一个 block 不影响邻居, 所以可以局部重编码。
这是 BRR 方案成功的核心原因。

### Step 5: 验证 seam=0

验证 BRR 解码后 loop 边界首尾采样差值为 0。

## 精选乐器 (15个, 全部 PERFECT)

筛选条件: 有循环, centerRate 不太高 (避免 4x+ 降采样导致 attack 失真)。

| # | 乐器 | centerRate | 原始PCM | 17640 PCM | BRR | 降采样比 |
|---|------|-----------|---------|-----------|-----|---------|
| 1 | Electric Piano | 53342Hz | 15.5KB | 5.1KB | 1.5KB | 3.0x |
| 2 | Violin | 28206Hz | 2.4KB | 1.5KB | 0.4KB | 1.6x |
| 3 | Strings | 24063Hz | 23.9KB | 17.5KB | 4.9KB | 1.4x |
| 4 | Harp | 14874Hz | 2.8KB | 3.3KB | 0.9KB | 0.8x |
| 5 | Accordion | 18817Hz | 2.6KB | 2.4KB | 0.7KB | 1.1x |
| 6 | Church Organ | 79923Hz | 5.3KB | 1.2KB | 0.3KB | 4.5x |
| 7 | Fretless Bass | 30032Hz | 4.4KB | 2.6KB | 0.7KB | 1.7x |
| 8 | Jazz Guitar | 60037Hz | 1.9KB | 0.6KB | 0.2KB | 3.4x |
| 9 | Distortion Guitar | 62695Hz | 2.6KB | 0.7KB | 0.2KB | 3.6x |
| 10 | Celesta | 12015Hz | 6.9KB | 10.2KB | 2.9KB | 0.7x |
| 11 | Flute | 24031Hz | 3.3KB | 2.4KB | 0.7KB | 1.4x |
| 12 | Recorder | 25072Hz | 5.8KB | 4.1KB | 1.2KB | 1.4x |
| 13 | Oboe | 20894Hz | 2.0KB | 1.7KB | 0.5KB | 1.2x |
| 14 | Clarinet | 39424Hz | 3.4KB | 1.5KB | 0.4KB | 2.2x |
| | **合计** | | | **63.1KB** | **16.5KB** | |

BRR 总计 **16.5KB**, 128KB Flash 轻松容纳, 还有约 50KB 余量给鼓声 ADPCM。

**排除**: Acoustic Grand Piano (centerRate=80212Hz, 4.5x 降采样, attack 瞬态严重失真咔咔)。

## 为什么 ADPCM 不行, BRR 行

| | ADPCM (YM2608) | BRR filter=0 |
|--|----------------|--------------|
| 状态 | 有 (acc + step_idx) | 无 |
| 修改 loop 尾部 | 状态链连锁反应, 不可控 | 改哪修哪, 不影响邻居 |
| crossfade 后重编码 | 全部重编, 状态可能不闭合 | 局部重编, 保证无缝 |
| 采样率 | 0.5 字节/采样 | 0.5625 字节/采样 |

ADPCM 的状态链是致命问题:
- PCM crossfade 修好了 → ADPCM 编码后又有缝 (状态链传播)
- BRR crossfade 修好了 → 重编码那几个 block 就行 (无状态, 局部修复)
- ADPCM 强制状态重置 → 整个 loop 波形被破坏 (acc=0/step=0 ≠ 实际状态)

## 折腾历程

1. **ADPCM 朴素模式**: 状态连续流过 loop 边界 → 缝很大
2. **ADPCM 重置模式**: loop 边界 acc=0 step=0 → 整个 loop 波形错误
3. **PCM crossfade + ADPCM**: PCM 层无缝了, ADPCM 编码后又断了
4. **PCM crossfade + BRR**: PCM 层无缝了, BRR 量化又引入新缝
5. **PCM crossfade + BRR + BRR crossfade**: 两层修复, 全部 PERFECT

关键突破: BRR filter=0 的无状态特性让"先编码再修"成为可能。

## 工具

- `tools/xi_parse.py` — XI 文件批量解析, JSON catalog + WAV 导出
- `tools/xi_demo.py` — 代表性乐器 C4/C5 试听渲染
- `tools/xi_brr_crossfade_test.py` — **最终方案**: 重采样 + crossfade + BRR + crossfade
- `tools/xi_brr_test.py` — BRR 基础测试 (无 crossfade, 大部分有缝)
- `tools/xi_adpcm_test.py` — ADPCM 循环测试 (失败)
- `tools/xi_crossfade_test.py` — PCM crossfade 测试

## 输出

- `tools/xi_out/brr_crossfade/pcm/` — crossfade PCM WAV (参考)
- `tools/xi_out/brr_crossfade/brr/` — BRR 解码 WAV (最终效果)
- `tools/xi_out/compare/` — native vs PCM vs BRR 对比
- `tools/xi_out/brr_test/pcm_native/` — 原始 centerRate 渲染 (参考)

## MCU 集成待做

- BRR 解码器 (C, filter=0, ~20 行核心代码)
- ROM 数据格式: 每 block 9 字节, loop_block 索引
- 播放: step = centerRate/17640 * pitchMultiplier, 按 16.16 fixed-point 步进
- 包络: attack 5ms, sustain, quadratic release (现有方案)
