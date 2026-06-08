# STC_Chiptune

STC8H8K64U 多音源芯片合成器。通过 UART 串口接收 VGM 命令，PWM 8-bit DAC 输出音频，实时模拟经典 PSG 音源芯片。

## 硬件

| 参数 | 值 | 说明 |
|------|-----|------|
| MCU | STC8H8K64U (DIP-40) | 1T 8051, 8K XRAM + 256 IRAM, 64K Flash |
| 系统时钟 | 48 MHz | IRC 内部 RC，STC-ISP 设定 |
| DAC 输出 | P2.0 (PWMA PWM1) | 8-bit, 载波 48MHz/256 = 187.5kHz |
| 采样率 | 17640 Hz | Timer0 ISR, 1T 模式 |
| 串口 | UART1 @ 115200 baud | Timer1, 2048 字节环形缓冲 |
| LED | P0 端口 | 8 位跑马灯 |

### ISR 时序预算

- 48MHz / 17640Hz = **2721 机器周期/tick**
- AY + SN 每 tick 渲染 (17640Hz)
- SCC/GB/NES 每 4 tick 渲染 (4410Hz)
- UART 处理每 294 tick (~60Hz) 由主循环 `process_uart()` 执行

## 音源芯片状态

### 稳定

| 芯片 | VGM 命令 | 通道 | 时钟 | 渲染频率 | 说明 |
|------|---------|------|------|---------|------|
| AY8910 (YM2149) | `0xA0` | 3 方波 + 噪声 + 包络 | 1789772 Hz | 17640Hz | 完美，测试多首 ZX Spectrum 曲目无误 |
| SN76489 | `0x50` | 3 方波 + 噪声 | 3579545 Hz | 17640Hz | 基本稳定，偶有错音，支持 3 种变体自动检测 |

### 可用但勉强

| 芯片 | VGM 命令 | 通道 | 时钟 | 渲染频率 | 说明 |
|------|---------|------|------|---------|------|
| SCC (KONAMI) | `0xD2` | 5 波形 | 3579545 Hz | 4410Hz | 可发声，偶有卡顿，步进预计算优化 |

### 失败 (8051 ISR 性能不足)

| 芯片 | 通道 | 失败原因 |
|------|------|---------|
| SAA1099 | 6 方波 + 噪声 | 合成逻辑过重，频率计数方式复杂 (freq^0x1FF, octave shift)，ISR 超时 |
| GB DMG | 2 方波 + 波形 + 噪声 | wave 通道需逐 cycle 模拟 (while 循环 2 cycles/step)，吃光 ISR 时间 |
| NES APU | 2 方波 + 三角 + 噪声 | phase accumulator while 循环过重 (低频时数百次迭代)，卡第一音 |
| WS (WonderSwan) | 4 方波 + 噪声 + 波形 | 未实际尝试，预估与 GB/NES 同等问题 |

**根本原因**: AY8910/SN76489 用简单的计数器翻转 (counter-flip) 生成波形，每 tick 仅加减比较操作，开销极低。GB wave/NES triangle/SAA1099 的合成需要逐采样点迭代 (while/for 循环)，单通道即吃光 ISR 的 2721 周期预算。

## UART 协议

| 命令 | 格式 | 说明 |
|------|------|------|
| SCC 写入 | `[0xD2][port][reg][data]` | 4 字节 |
| AY8910 写入 | `[0xA0][reg][data]` | 3 字节 |
| SN76489 写入 | `[0x50][data]` | 2 字节 |
| SN76489 变体 | `[0x51][variant]` | 2 字节, 0=SN76489/1=SegaVDP/2=SN76489A |
| GB DMG 写入 | `[0xB3][reg][data]` | 3 字节 (代码保留，不可用) |
| NES APU 写入 | `[0xB4][reg][data]` | 3 字节 (代码保留，不可用) |

## 上位机

```
python tools/vgm_player.py --list                    # 列出曲目
python tools/vgm_player.py 1 --baud 115200          # 播放第 1 首
python tools/vgm_player.py "Vampire" --baud 115200   # 按名称搜索
python tools/vgm_player.py 1 --speed 1.5 --loop     # 1.5x 速度循环
python tools/vgm_player.py --vgm-dir vgm/ay8910 1   # 指定目录
python tools/vgm_player.py --dump 1                  # 导出 VGM 命令
```

## 编译

```bash
cd STC8H8K64
D:/Keil_v5/C51/BIN/C51.exe src/ay8910.c "OPTIMIZE(8,SPEED)" "INCDIR(include,src)"
D:/Keil_v5/C51/BIN/C51.exe src/scc.c "OPTIMIZE(8,SPEED)" "INCDIR(include,src)"
D:/Keil_v5/C51/BIN/C51.exe src/sn76489.c "OPTIMIZE(8,SPEED)" "INCDIR(include,src)"
D:/Keil_v5/C51/BIN/C51.exe src/gb.c "OPTIMIZE(8,SPEED)" "INCDIR(include,src)"
D:/Keil_v5/C51/BIN/C51.exe src/nes.c "OPTIMIZE(8,SPEED)" "INCDIR(include,src)"
D:/Keil_v5/C51/BIN/C51.exe src/main.c "OPTIMIZE(8,SPEED)" "INCDIR(include,src)"
D:/Keil_v5/C51/BIN/BL51.exe src/ay8910.OBJ,src/scc.OBJ,src/sn76489.OBJ,src/gb.OBJ,src/nes.OBJ,src/main.OBJ TO build/MAIN
D:/Keil_v5/C51/BIN/OH51.exe build/MAIN
cp build/MAIN.hex ../firmware.hex
```

## 目录结构

```
STC_Chiptune/
├── STC8H8K64/
│   ├── src/              # 源码
│   │   ├── main.c        # 主程序 (ISR + UART + 混音)
│   │   ├── ay8910.c/h    # AY8910 仿真 (稳定)
│   │   ├── scc.c/h       # SCC 仿真 (include/) (勉强)
│   │   ├── sn76489.c/h   # SN76489 仿真 (src/) (基本稳定)
│   │   ├── gb.c/h        # GB DMG 仿真 (性能不足)
│   │   └── nes.c/h       # NES APU 仿真 (性能不足)
│   ├── include/          # 公共头文件 (stc8h.h, types.h, scc.h)
│   ├── build/            # 编译输出
│   ├── docs/             # 技术文档 + FwLib_STC8 + stc8prog
│   └── lib/              # FwLib_STC8 HAL
├── tools/
│   └── vgm_player.py    # Python VGM 播放器 (解析+串口+节拍控制)
├── vgm/                  # VGM 曲目文件
│   ├── ay8910/
│   ├── sn76489/
│   ├── gb/
│   ├── nes/
│   └── saa1099/
├── firmware.hex          # 最新固件
└── README.md
```

## 开发历程

### Phase 1: 硬件验证 (2025)

**目标**: 在 STC8H8K64U 上验证 PWM DAC 音频输出

- 选定 STC8H8K64U (DIP-40, 1T 8051, 48MHz, ~2 元) 作为目标芯片
- 初期尝试 SDCC 编译器，发现不兼容官方 `stc8h.h`（`sfr`/`sbit` 语法差异），切换到 **Keil C51**
- 参考官方 WAV 播放器 demo (`80-播放WAV-8K采样率-8bit采样-PWM5-P1.7`)，实现 PWMA PWM1 → P2.0 DAC 输出
- 验证正弦波/方波/锯齿波/三角波合成 + 音量衰减包络
- Timer0 ISR 驱动采样，初始 8kHz，后提升至 16kHz
- UART1 echo 测试通过，确认串口通信可用

**关键收获**: P_SW2 |= 0x80 全局保持开启（参考官方 demo），加速 PWM 寄存器访问；Keil C51 的 `OBJECT()` 参数无效，OBJ 始终输出到源目录

### Phase 2: SCC 仿真器 (2025)

**目标**: 移植 KONAMI SCC 音源芯片仿真器

- 参考 emu2149/RPFM，从零移植 SCC 到 Keil C51
- SCC 核心: 5 通道波形，32 字节波形表，16-bit 相位累加器
- **步进预计算优化**: `scc_wr()` 时预计算 step (`BASE_INCR * freq >> 16`)，ISR 中仅做 `phase += step`，避免实时除法
- 采样率从 11025Hz → 8820Hz → **4410Hz** 逐步降低以减轻 ISR 压力
- 开发 Python `vgm_player.py` 上位机，解析 VGM 文件，提取 `0xD2` 命令通过串口发送
- Python 控制节拍 (perf_counter 累积模式)，固件仅做寄存器写入
- **瓶颈**: SCC 4410Hz 勉强可用，17640Hz 直接卡死

### Phase 3: AY8910 仿真器 (2025)

**目标**: 集成 AY-3-8910 (YM2149) 仿真器

- 参考 emu2149 (MIT, Nyan Cat 作者)，移植到 8051
- AY8910 核心: 3 方波通道 + 噪声 + 包络，12-bit 频率，16 级对数音量
- 时钟 1789772 Hz (NTSC)，render @ 17640Hz，累加器采样率转换
- **关键修正**:
  - 时钟频率 /2 修正（YM2149 兼容模式），修复音高偏高一个八度
  - 包络启用标志 bit4 (非 bit5)
  - 包络模型对齐 libvgm 实现
- 开机测试音: AY C4/E4/G4 和弦 + 包络衰减
- **22050Hz 双采样率 → 统一 17640Hz**: 简化架构，AY/SN 同频率渲染

### Phase 4: SN76489 仿真器 (2025)

**目标**: 集成 TI SN76489 仿真器（Sega Master System 音源）

- SN76489 核心: 3 方波 + 噪声，10-bit 频率，16-bit LFSR 噪声
- 时钟 3579545 Hz，内部 /16 分频，render @ 17640Hz
- **三变体自动检测**: SN76489 (15-bit LFSR, taps=0x03) / Sega VDP (16-bit, taps=0x09) / SN76489A (17-bit, taps=0x0C)
- VGM header 0x28/0x2A 字段自动识别变体，通过 `0x51` 命令下发固件

### Phase 5: 代码重构 (2025)

- AY8910 从 main.c 剥离为独立模块 (ay8910.c/h)
- SCC 从 main.c 剥离为独立模块 (scc.c → include/scc.h)
- 统一 `types.h` (u8/u16/u32/s8/s16)
- 添加芯片 `active` 开关（收到命令才 render，避免空转）

### Phase 6: 失败尝试 (2025-2026)

#### SAA1099 (Philips)
- 6 方波 + 噪声，频率计数方式复杂 (`freq^0x1FF` as limit, octave shift)
- 在 4410Hz 分频下 `incr << octave` 导致计数器跳跃太大
- 结果: 只发 "re do re do" 两音 + 噪声，音高完全错误
- **代码已移除**

#### GB DMG (Game Boy)
- 4 通道: 2 方波 + wave(32-step 波形) + 噪声
- wave 通道需要逐 cycle 模拟 (while 循环, 每 tick 2 cycles)
- GB 内部时钟 4194304 Hz，/64 = 65536 Hz tick rate
- 在 4410Hz 渲染时，每帧需处理 ~15 ticks × 32 steps = 480 次 while 迭代
- 尝试多种优化: for 循环替代 while、per-tick 64 cycle 方式、降低采样率
- 结果: 无声音 → 超低音 → 音符错乱，最终放弃

#### NES APU (Nintendo)
- 4 通道 (无 DMC): 2 方波(包络+扫频) + 三角波 + 噪声
- 参考 libvgm nes_apu.c，整数累加器替代 float phaseacc
- 时钟 1789773 Hz (NTSC)，render @ 4410Hz (tick_div=4)
- 方波/三角波的 phase accumulator while 循环，低频时 freq 很小，单次渲染需数百次迭代
- 结果: 卡第一音，ISR 直接超时

**结论**: 8051 @ 48MHz 的 ISR 性能上限约等于 AY8910 + SN76489 同时渲染。更复杂的音源 (GB/NES/SAA) 需要更强的 MCU (ARM Cortex-M0+ 以上)。

### 技术参数汇总

| 参数 | 值 |
|------|-----|
| MCU 系统时钟 | 48 MHz (IRC) |
| Timer0 | 1T 模式, reload = 65536 - 48000000/17640 = 65263 |
| Timer0 ISR 频率 | 17640 Hz |
| Timer1 | UART1 波特率发生器, 1T 模式 |
| UART1 波特率 | 115200 (TH1 = (65536 - 48M/4/115200) / 256) |
| PWM 载波 | 48 MHz / (PSCR=0+1) / (ARR=255+1) = 187.5 kHz |
| PWM 分辨率 | 8 bit (ARR=255) |
| UART 缓冲 | 2048 字节环形缓冲 |
| TASK_DIVIDER | 294 (~60Hz 主循环处理 UART) |
| AY 时钟 | 1789772 Hz, GETA_BITS=24, BASE_INCR=212779134 |
| SN 时钟 | 3579545 Hz, 内部 /16 |
| SCC 步进基准 | 53084160 (3579545 * 2^16 / 4410) |
| ISR 预算 | ~2721 机器周期/tick |
