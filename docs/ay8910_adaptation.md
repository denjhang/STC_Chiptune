# AY8910 仿真器适配文档

## 概述

AY8910 (AY-3-8910 / YM2149) 仿真器集成到 STC8H8K64U (8051, 48MHz) 平台，
与 SCC 合成器共存，支持 VGM 双芯片播放。

## 架构

```
Timer0 ISR (22050Hz)
  ├── AY 渲染 (每次 tick)
  ├── SCC 渲染 (每 2 tick = 11025Hz)
  └── 混音 → PWM DAC (P2.0)
```

## AY8910 硬件模型

### 通道配置
- 3 个方波通道 (A, B, C)
- 1 个噪声通道 (17-bit LFSR)
- 1 个硬件包络发生器 (16 级，4-bit 控制)

### 寄存器映射

| 寄存器 | 功能 |
|--------|------|
| R0/R1 | CH.A 频率 (12-bit: lo + hi<<8) |
| R2/R3 | CH.B 频率 |
| R4/R5 | CH.C 频率 |
| R6    | 噪声频率 (5-bit) |
| R7    | 混合器 (bit0-2: 音调屏蔽, bit3-5: 噪声屏蔽) |
| R8-R10| 通道音量 (bit0-3: 固定音量, bit4: 包络启用) |
| R11/R12| 包络频率 (16-bit) |
| R13   | 包络形状 (bit3: continue, bit2: attack, bit1: alternate, bit0: hold) |

### 关键参数
- **AY 时钟**: 1789772 Hz (SCC_CLOCK / 2)
- **采样率**: 22050 Hz
- **base_incr**: `1789772 * (1<<24) / 8 / 22050 = 170223307`

## 包络模型 (libvgm 实现)

包络是 AY8910 最复杂的功能，直接影响 bass 音色。

### 状态变量
```
env_step    - 包络步进 (0x00~0x0F, 递减，到 0xFF 时触发周期结束)
env_attack  - attack 方向 (0 或 0x0F, 被 XOR 翻转)
env_pause   - 包络暂停 (hold 后停止递减)
env_continue/alternate/hold - 控制包络形状
```

### 包络音量计算
```c
vol_idx = env_step ^ env_attack;   // 范围 0~15
vol_val = ay_voltbl[vol_idx];       // 查表得到 DAC 值
```

### 包络形状解析 (R13)

R13 写入时:
```
env_pause = 0
env_step  = attack ? 0 : 0x0F      // attack=1 从 0 上升, attack=0 从 15 下降
```

每衰减一个周期 (env_count >= env_freq):
```
env_step--
if (env_step == 0xFF):              // 下溢 = 周期结束
  if (hold):
    if (alternate) env_attack ^= 0x0F
    env_pause = 1
    env_step = 0
  else:
    if (alternate && env_step & 0x10) env_attack ^= 0x0F
    env_step = 0x0F
```

### 常见形状

| R13 | continue | attack | alternate | hold | 行为 |
|-----|----------|--------|-----------|------|------|
| 0   | 0        | 0      | 0         | 0    | 下降↑↑↑ (循环) |
| 4   | 0        | 1      | 0         | 0    | 上升↑↑↑ (循环) |
| 8   | 1        | 0      | 0         | 0    | 下降一次后循环 |
| 10  | 1        | 0       | 1         | 0    | 锯齿波 |
| 12  | 1        | 1      | 0         | 0    | 三角波 |
| 14  | 1        | 1      | 1         | 0    | 反三角 |

## 噪声模型

17-bit LFSR, 每噪声周期翻转:
```c
if (noise_seed & 1) noise_seed ^= 0x24000;
noise_seed >>= 1;
```
使用 noise_scaler 做 2 分频 (每 2 个噪声 tick 才移位一次)。

## 内存布局

### code 段 (Flash)
- `ay_voltbl[32]` - 16 级音量表 (成对重复)
- `ay_regmsk[16]` - 寄存器写掩码

### xdata 段 (外部 RAM)
- `ay_reg[16]` - 寄存器
- `ay_count[3]`, `ay_freq_lo/hi[3]`, `ay_edge[3]` - 通道状态
- `ay_tmask[3]`, `ay_nmask[3]`, `ay_volume[3]` - 通道控制
- `ay_env_*` - 包络状态
- `ay_noise_*` - 噪声状态
- `ay_base_count` - 基础计数器

## 音量表

AY-3-8910 标准音量表 (非线性, 近似对数):
```c
0x00, 0x00, 0x03, 0x03, 0x04, 0x04, 0x06, 0x06,
0x09, 0x09, 0x0D, 0x0D, 0x12, 0x12, 0x1D, 0x1D,
0x22, 0x22, 0x37, 0x37, 0x4D, 0x4D, 0x62, 0x62,
0x82, 0x82, 0xA6, 0xA6, 0xD0, 0xD0, 0xFF, 0xFF
```

## 踩坑记录

1. **时钟频率必须 /2**: AY8910 标准时钟是 SCC 时钟的一半 (1789772 Hz vs 3579545 Hz)。
   使用全时钟会导致音高偏高一个八度。

2. **包络启用是 bit4 (0x10)**: 不是 bit5 (0x20)。
   emu2149 的实现在 bit5，但 libvgm 的权威实现在 bit4。
   VGM 文件中的 AY 数据使用 bit4。

3. **包络模型用 libvgm 的 env_step 递减模型**: emu2149 的 env_ptr (0-31 范围)
   会导致叠加包络时音量超过 15，产生失真。正确做法是 env_step XOR attack，
   结果范围始终在 0~15。

4. **44100Hz ISR 太快**: STC8H 8051 核心无法在 44100Hz 下同时运行 AY+SCC 渲染。
   22050Hz 是稳定的上限。

5. **base_incr 计算要精确**: `CLK * (1<<24) / 8 / RATE`，务必用 32-bit 算术。

## 参考实现

- **emu2149**: `D:\working\vscode-projects\Reference_Project\RP2350-Reference\msx-picoverse-public-main\2350\software\explorer.pio\pico\explorer\emu2149.c`
  嵌入式优化版本，基础参考
- **libvgm ay8910**: `D:\working\vscode-projects\Reference_Project\vgm_libs\libvgm-master\emu\cores\ay8910.c`
  权威实现，包络模型以此为准

## VGM 协议

```
[0xA0][reg][data]  → AY8910 写寄存器 (3 字节)
[0xD2][port][reg][data] → SCC 写寄存器 (4 字节)
```

Python 端 `tools/vgm_player.py` 解析 VGM 文件，按节拍发送命令，
固件端 `process_uart()` 在 ISR 软件分频的 60Hz 任务中处理。
