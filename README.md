# STC_Chiptune

STC32G12K128 多音源芯片合成器。通过 UART 接收命令，PWM 8-bit DAC 输出音频，实时模拟 6 种音源芯片 + ADPCM 采样。

## 硬件

| 参数 | 值 | 说明 |
|------|-----|------|
| MCU | STC32G12K128 | 1T 251, 128K Flash, 10K SRAM + 8K XRAM |
| 系统时钟 | 35 MHz | IRC 内部 RC |
| DAC 输出 | P2.0 (PWMA PWM1) | 8-bit, 载波 35MHz/256 = 136.7kHz |
| 采样率 | 17640 Hz | Timer0 ISR |
| 串口 | UART1 @ 115200 baud | Timer1, 2048 字节环形缓冲 |
| LED | P0 端口 | 8 位, 按活跃音源通道显示 |

## 音源架构

### 活跃音源 (6种)

| 音源 | 命令前缀 | 通道数 | 渲染频率 | 说明 |
|------|---------|--------|---------|------|
| **AY8910** (YM2149) | `0xA0` | 3 方波 + 噪声 + 包络 | 17640Hz | 完美, ZX Spectrum/MSX 曲目 |
| **SN76489** | `0x50` | 3 方波 + 噪声 | 17640Hz | Sega Master System, 3 种变体 |
| **FM** (YM2413/OPLL) | `0x51` | 9 ch (6旋律+3节奏) | 17640Hz | 2-Operator FM, 6 种波形 |
| **Gigatron** | `0xB0` | 4 ch | 8820Hz | 4ch 波形, 直接写 fnum |
| **WT** (Wavetable) | `0xC0` | 4 ch | 17640Hz | 14 种波形, ADSR 包络 |
| **ADPCM** | `0xC0` | 6 ch | 17640Hz | 鼓声 + SF2 旋律采样 |

### 混音

Timer0 ISR 17640Hz 逐 tick 渲染所有活跃音源, 累加后 clamp 到 8-bit DAC:
```
mix = ay*1.5 + sn*0.75 + fm*1.5 + gt*1.5 + wt*1.5 + adpcm*1.5
clamp(-128, 127) → 128+offset → PWM
```

### UART 处理

每 294 tick (~60Hz) 调用 `process_uart()`, 从 2048 字节环形缓冲解析命令。

## UART 协议

### 通用命令

| 命令 | 格式 | 校验 | ACK | 说明 |
|------|------|------|-----|------|
| SN76489 | `[0x50][data]` | 无 | 无 | 2 字节, 透明 |
| SN76489 变体 | `[0x52][variant]` | 无 | 无 | 0=SN76489 1=SegaVDP 2=SN76489A |
| AY8910 | `[0xA0][reg][data]` | 无 | 无 | 3 字节, 透明 |
| FM | `[0x51][addr][data][xor]` | XOR | 0xAA/0xFF | 4 字节 |
| Gigatron | `[0xB0][addr][data][xor]` | XOR | 丢弃 | 4 字节 |
| WT/ADPCM | `[0xC0][addr][data][xor]` | XOR | 0xAA/0xFF | 4 字节 |

### FM 寄存器 (0x51 后跟)

| 地址 | 说明 |
|------|------|
| 0x00-0x09 | 音色参数 (全局共用, 10 字节) |
| 0x10-0x18 | Note On voice 0-8 (data=MIDI note) |
| 0x20-0x28 | Note Off voice 0-8 |
| 0x30-0x38 | Volume override voice 0-8 (0-15) |

### WT 寄存器 (0xC0, addr 0x00-0x14)

| 地址 | 说明 |
|------|------|
| 0x00-0x03 | ch0-3 Note On (data=MIDI note 24-127) |
| 0x04-0x07 | ch0-3 Note Off |
| 0x08-0x0B | ch0-3 Volume (0-31) |
| 0x10 | ADSR attack\|decay |
| 0x11 | ADSR sustain_level\|sustain |
| 0x12 | ADSR release |
| 0x13 | Wave select (0-13) |
| 0x14 | Wave length (0=32, 1=64, 2=128) |

### ADPCM 寄存器 (0xC0, addr 0x15-0x33)

| 地址 | 说明 |
|------|------|
| 0x15-0x1A | ch0-5 Note On (data: 0-5=鼓声, 16-25=SF2乐器) |
| 0x1B-0x20 | ch0-5 Note Off |
| 0x21-0x26 | ch0-5 Volume (0-31) |
| 0x27-0x2C | ch0-5 Step Hi (变频步进高位) |
| 0x2D-0x32 | ch0-5 Step Lo (变频步进低位) |
| 0x33 | MIDI Note (紧跟 SF2 Note On, 24-95) |

## ADPCM 音源详解

### 编码格式

YM2608 ADPCM Type-A:
- 49 级 JEDI 查表解码 (`jedi_table[49][16]`, 784 x s16)
- 12-bit 累加器, 每 2 nibble 更新: `acc = CLIP12(acc + table[nibble])`
- 步进表 `adpcm_step_inc[8]`: `-16,-16,-16,-16,32,80,112,144`
- 8-bit 压缩比 (~3.2:1)

### 鼓声 (6种, one-shot, 无循环)

| ID | 名称 | 采样长 | 基准 Step | 变频范围 |
|----|------|--------|---------|---------|
| 0 | BD (Bass Drum) | 854 B | 0x0100 | 无上限 |
| 1 | SD (Snare) | 1219 B | 0x0100 | 无上限 |
| 2 | CY (Cymbal) | 5670 B | 0x0080 | 无上限 |
| 3 | HH (Hi-Hat) | 732 B | 0x0100 | 无上限 |
| 4 | TM (Tom) | 1219 B | 0x0080 | 无上限 |
| 5 | RS (Rimshot) | 244 B | 0x0080 | 无上限 |

- 变频: Python 端计算 `step = base_step * ratio`, 通过 0x27/0x2D 写入
- 鼓变频无上限 (无循环, ISR 无压力)
- SF2 旋律变频上限 0x0400 (有循环, C5 以上死机)
- 包络: env_state=0 (无 ADSR), out>>5 增益归一化

### SF2 旋律乐器 (5种, 有循环, DSR 包络)

| ID | 名称 | 采样长 | 循环区间 |
|----|------|--------|---------|
| 0 | Piano | 1164 B | 1915→2127 |
| 1 | SlapBass | 1835 B | 3017→3512 |
| 2 | Guitar | 3722 B | 7080→7291 |
| 3 | Oboe | 2015 B | 2425→2852 |
| 4 | Harp | 3187 B | 3374→6372 |

- ROM: `SF2_ROM[11936]` (11.7 KB), 12-bit 归一化 ADPCM
- 包络: DSR only (无 Attack), note_on 直接 level=31, note_off 触发 release
- 变频: 通过 0x27/0x2D 写 step, 上限 0x0400
- 循环: loop 回绕时恢复 acc/adpcm_step 状态

### ADPCM 通道分配

6 个通道复用: ch0-5 可同时播放鼓声或 SF2 旋律。
鼓声和 SF2 旋律共用 0xC0 前缀, 通过 data 范围区分:
- data 0-5: 鼓声
- data 16-25: SF2 乐器 (16+inst_idx, inst_idx 0-4)

### ADSR 包络 (SF2 旋律 + WT 共用)

| 参数 | 地址 | 说明 |
|------|------|------|
| Attack | 0x10 高4位 | SF2 旋律不使用 (直接 level=31, 避免 Attack 量化破音) |
| Decay | 0x10 低4位 | 衰减速度 |
| Sustain Level | 0x11 高4位 | 0-15 |
| Sustain | 0x11 低4位 | 持续速度 |
| Release | 0x12 | 释放速度 |

包络速度表: `pcm_env_cnt[16] = {0,1,2,3,4,5,7,10,13,20,29,43,64,86,128,255}`

## WT 音源详解

- 14 种预置波形 (code 段, 14x128 = 1792 bytes):
  `sq12, sq25, pulse50, sq75, sin, clipsin, abssin, halfsin, qsin, altsin, althalfsin, tri, saw, gb_dmg`
- 4 通道, 128 字节波形表, 相位累加器
- ADSR 包络 (与 ADPCM 共用音色模板)
- 波形长度可切换: 32/64/128

## FM 音源详解

- 9 通道 (6 旋律 + 3 节奏), 模拟 YM2413/OPLL
- 2-Operator FM: op1→op2→voice_out, 支持反馈
- 64 字节正弦表, 6 种波形
- ADSR 包络 (独立实现, 4 态)
- 音色通过 0x00-0x09 写入 10 字节参数

## 上位机工具

### VGM 播放

```
python tools/vgm_player.py --list --vgm-dir vgm/ay8910     # 列出曲目
python tools/vgm_player.py 10 --vgm-dir vgm/ay8910 --baud 115200
python tools/vgm_player.py --list --vgm-dir vgm/sn76489    # 列出曲目
python tools/vgm_player.py 16 --vgm-dir vgm/sn76489 --baud 115200
python tools/vgm_player.py --list --vgm-dir vgm/opll       # 列出曲目
python tools/vgm_player.py <编号> --vgm-dir vgm/opll --baud 115200
python tools/vgm_player.py --fm-note 0 60 --baud 115200   # FM ch0 C4
python tools/vgm_player.py --fm-scale --baud 115200       # FM 扫频 C1-C9
python tools/vgm_player.py --wt-scale --baud 115200       # WT 扫频
```

### ADPCM 鼓声测试

```
python tools/adpcm_test.py                    # 14 种风格全部播放
python tools/adpcm_test.py 3                  # 播放第 3 个风格
```

### ADPCM 鼓机加强版 (ini 驱动)

```
python tools/adpcm_drumkit_pro.py             # 播放全部风格
python tools/adpcm_drumkit_pro.py 3          # 播放第 3 个
python tools/adpcm_drumkit_pro.py list       # 列出全部风格
```

### ADPCM 旋律测试

```
python tools/sf2_test.py                      # 5 乐器依次原音
python tools/sf2_test.py piano 60             # 钢琴 C4
python tools/sf2_test.py all 60               # 所有乐器 C4
python tools/sf2_test.py chord                # 和弦
```

### ADPCM 变频扫频

```
python tools/sf2_sweep.py                     # 所有乐器 C1→4x→C1
python tools/sf2_sweep.py piano               # 钢琴
```

### WT 扫频

```
python tools/wt_scale_test.py                 # 14 种波形 C2↔C6 循环
```

### 鼓变频映射

- `tools/drum.ini` — MIDI 35-81 鼓组映射 (drum_id + ratio) + 别名 + 音量
- `tools/drum_patterns/` — 14 个独立风格 ini (Modern/Rock/Pop/Funk/HipHop/Ballad/SlowRock/HardRock/Disco/DancePop/Trance/Jazz/Bossa/Square)

## 编译 (Keil C251)

```bash
cd STC32G12K128
D:/Keil_v5/C251/BIN/C251.exe ay8910.c
D:/Keil_v5/C251/BIN/C251.exe sn76489.c
D:/Keil_v5/C251/BIN/C251.exe fm.c
D:/Keil_v5/C251/BIN/C251.exe gigatron.c
D:/Keil_v5/C251/BIN/C251.exe wt.c
D:/Keil_v5/C251/BIN/C251.exe adpcm.c
D:/Keil_v5/C251/BIN/C251.exe main.c
D:/Keil_v5/C251/BIN/L251.exe ay8910.OBJ,sn76489.OBJ,fm.OBJ,gigatron.OBJ,wt.OBJ,adpcm.OBJ,main.OBJ TO build/MAIN
```

## 目录结构

```
STC_Chiptune/
├── STC32G12K128/
│   ├── main.c              # 主程序 (ISR + UART + 混音)
│   ├── ay8910.c/h         # AY8910 仿真
│   ├── sn76489.c/h        # SN76489 仿真
│   ├── fm.c/h             # FM OPLL 仿真
│   ├── gigatron.c/h       # Gigatron 仿真
│   ├── wt.c/h             # Wavetable 合成 (14波形)
│   ├── adpcm.c/h          # ADPCM 解码 (鼓声+SF2)
│   ├── sf2_rom.h           # SF2 采样 ROM (5乐器, 11.7KB)
│   ├── fmopn_2608rom.h     # FM 波形/乐器 ROM
│   ├── jedi_table.h        # (included in adpcm.c)
│   └── build/              # 编译输出
├── tools/
│   ├── vgm_player.py       # VGM 播放器
│   ├── adpcm_test.py       # 鼓声节奏测试 (14风格)
│   ├── adpcm_drumkit_pro.py # 鼓机加强版 (ini驱动)
│   ├── drum.ini             # 鼓组映射+别名+音量
│   ├── drum_patterns/       # 14个风格独立ini
│   ├── sf2_test.py         # SF2 旋律测试
│   ├── sf2_sweep.py        # SF2 变频扫频
│   ├── sf2_extract.py      # SF2 提取工具
│   ├── adpcm_pitch_test.py # 鼓变频测试
│   └── wt_scale_test.py    # WT 扫频测试
├── vgm/                    # VGM 曲目
│   ├── ay8910/
│   ├── sn76489/
│   └── opll/
├── docs/                   # 技术文档
└── README.md
```

## 开发历程

### Phase 1-6: STC8H8K64U 时代

8051 (48MHz) 上的原型开发: SCC/AY8910/SN76489 仿真, GB/NES/SAA 失败尝试。
详见 git history。

### Phase 7: 迁移 STC32G12K128

STC32G C251, 35MHz, 128K Flash, 10K SRAM + 8K XRAM。
- 移植全部音源到 C251
- 新增 FM (OPLL) 9ch 合成
- 新增 Gigatron 4ch 波形
- SCC 剔除 (WT 完善, 不再需要)

### Phase 8: ADPCM 采样

- 实现 YM2608 ADPCM Type-A 解码器 (JEDI 表, 12-bit acc)
- 从 SF2 音色库提取 5 种乐器 (Piano/SlapBass/Guitar/Oboe/Harp)
- 6 种鼓声 ROM (BD/SD/CY/HH/TM/RS)
- DSR 包络 (无 Attack, 避免 4-bit 量化破音)
- 鼓声变频: Python 端计算 step, MCU 不做计算
- SF2 变频上限 0x0400 (有循环, C5 以上 ISR 死机)
- 鼓变频无上限 (无循环, 无压力)

### Phase 9: WT 波形扩充

- 14 种预置波形 (原 6 种 + 8 种 OPL3/GB 风格)
- 波形长度可切换 (32/64/128)
- C2↔C6 循环扫频测试

### Phase 10: 鼓机系统

- 14 种节奏风格 (Modern/Rock/Pop/Funk/HipHop/Ballad/SlowRock/HardRock/Disco/DancePop/Trance/Jazz/Bossa/Square)
- ini 驱动: drum.ini (映射+别名+音量) + drum_patterns/ (独立风格)
- MIDI GM Percussion 35-81 全覆盖
- 19 个变频别名快捷键
