# STC_Chiptune

STC32G12K128 多音源芯片合成器。通过 UART 接收命令，PWM 8-bit DAC 输出音频，实时模拟 6 种经典音源芯片 + ADPCM/BRR 采样。

> 在开源社区中，同类项目通常是**单芯片复刻**（如 Teensy Audio Shield 跑 YM2149，MSP430 跑 AY-3-8910）或**PC 端软件合成**（Blaargchip、Chiptune Baker）。把 6 种不同架构的音源核心（AY8910/SN76489/FM/WT/ADPCM/BRR）塞进同一颗 38MHz 单片机，共享同一个 17640Hz ISR 混音输出 — 这种"多音源芯片硬件实时合成"在开源项目中没有先例。本质上是一颗 **"芯片音乐博物馆"**，在廉价 8 位 MCU 上同时仿真 ZX Spectrum / SMS / OPLL / Game Boy / NES / SNES 的声音，横跨 1970-2020 年代数字音频历史。

**开发者**: Denjhang (硬件设计/系统架构), Claude (GLM-5) (固件开发/工具链/上位机)

## 目录

- [1. 硬件](#1-硬件)
  - [1.1 参数总览](#11-参数总览)
  - [1.2 引脚分配](#12-引脚分配)
  - [1.3 PWM DAC 输出原理](#13-pwm-dac-输出原理)
    - [为什么是 8-bit 而非 10-bit](#为什么是-8-bit-而非-10-bit)
- [2. 音源架构](#2-音源架构)
  - [2.1 活跃音源总览](#21-活跃音源总览)
  - [2.2 混音与处理](#22-混音与处理)
  - [2.3 AY8910 (YM2149)](#23-ay8910-ym2149)
  - [2.4 SN76489](#24-sn76489)
  - [2.5 FM 合成 (自定义 2-Op)](#25-fm-合成-自定义-2-op)
  - [2.6 Gigatron TTL 波形](#26-gigatron-ttl-波形)
  - [2.7 WT 波形表](#27-wt-波形表)
  - [2.8 ADPCM 采样](#28-adpcm-采样)
    - [ADPCM 解码原理](#adpcm-解码原理)
    - [鼓机序列播放器](#鼓机序列播放器-上位机)
    - [鼓声变调](#鼓声变调)
    - [SF2 乐器变调](#sf2-乐器变调)
    - [SF2 乐器 ADSR 模板](#sf2-乐器-adsr-模板)
    - [ADPCM 循环原理](#adpcm-循环原理)
    - [ADPCM ADSR 包络原理](#adpcm-adsr-包络原理)
  - [2.9 BRR 采样](#29-brr-采样)
    - [BRR 编码格式](#brr-编码格式)
    - [BRR 解码原理](#brr-解码原理-gme-spc_dspcpp-bit-exact)
    - [BRR 乐器 ADSR 模板](#brr-乐器-adsr-模板-14-乐器)
    - [BRR 循环原理](#brr-循环原理)
    - [变频原理](#变频原理)
  - [2.10 已放弃的音源](#210-已放弃的音源)
- [3. UART 协议](#3-uart-协议)
  - [3.1 通用命令](#31-通用命令)
  - [3.2 WT 寄存器](#32-wt-寄存器)
  - [3.3 FM 寄存器](#33-fm-寄存器)
  - [3.4 ADPCM 寄存器](#34-adpcm-寄存器)
  - [3.5 BRR 寄存器](#35-brr-寄存器)
- [4. 上位机工具](#4-上位机工具)
  - [4.1 VGM 播放器](#41-vgm-播放器)
  - [4.2 ADPCM 鼓声测试](#42-adpcm-鼓声测试)
  - [4.3 ADPCM 鼓机 (ini 驱动)](#43-adpcm-鼓机-ini-驱动)
  - [4.4 ADPCM 变频测试](#44-adpcm-变频测试)
  - [4.5 ADPCM 通道调试](#45-adpcm-通道调试)
  - [4.6 SF2 旋律测试](#46-sf2-旋律测试)
  - [4.7 SF2 变频扫频](#47-sf2-变频扫频)
  - [4.8 WT 扫频测试](#48-wt-扫频测试)
  - [4.9 BRR 扫频测试](#49-brr-扫频测试)
  - [4.10 离线工具](#410-离线工具)
  - [4.11 配置文件](#411-配置文件)
- [5. 工具链与编译](#5-工具链与编译)
  - [5.1 工具链](#51-工具链)
  - [5.2 编译步骤](#52-编译步骤)
  - [5.3 编译注意事项](#53-编译注意事项)
- [6. 目录结构](#6-目录结构)
- [7. 开发历程](#7-开发历程)
- [8. 参考项目与移植说明](#8-参考项目与移植说明)
  - [8.1 AY8910 — libvgm](#81-ay8910--libvgm)
  - [8.2 SN76489 — libvgm](#82-sn76489--libvgm)
  - [8.3 FM 合成 — ArduinoUnoTinyFmKeyboard](#83-fm-合成--arduinounotinyfmkeyboard)
  - [8.4 WT 波形表 — ArduinoUno WaveMemorySyns](#84-wt-波形表--arduinounowavememorysyns)
  - [8.5 Gigatron — Denjhang_Music_Player](#85-gigatron--denjhang_music_player)

---

## 1. 硬件

### 1.1 参数总览

| 参数 | 值 | 说明 |
|------|-----|------|
| MCU | STC32G12K128 | 32位 1T 8051 内核, 兼容 C251 指令集, 128KB Flash, 4KB SRAM + 8KB XRAM |
| 系统时钟 | 38 MHz | IRC 内部 RC (Fosc=38000000) |
| DAC 输出 | P2.0 (PWMA PWM1) | 8-bit PWM DAC, 载波 148kHz, 详见下方 |
| 采样率 | 17640 Hz | Timer0 ISR |
| 串口 | UART1 @ 115200 baud | Timer1, 2048 字节环形缓冲 |
| LED | P0 端口 | 8 位, 按活跃音源通道显示 |
| 任务调度 | 294 tick | ~60Hz 调用 process_uart(), 解析命令 |

### 1.2 引脚分配

| 引脚 | 功能 | 说明 |
|------|------|------|
| P2.0 | PWMA PWM1 → 音频输出 | 8-bit PWM DAC, 接 RC 低通滤波 + 运放 → 扬声器/耳机 |
| P1.6/P1.7 | UART1 TX/RX | 115200 baud, 接 USB-TTL |
| P0.0-P0.7 | LED 指示灯 | 8-bit, 按音源通道活跃状态显示 |
| P3.4/P3.5 | STC-ISP | 编程接口 (TXD2/RXD2) |

### 1.3 PWM DAC 输出原理

#### 硬件配置

使用 STC32G 内置高级 PWM 模块 (PWMA) 通道 1, 输出到 P2.0:

```
PWMA_ARR = 255          (8-bit 分辨率, 0-255)
PWMA_CCR1 = sample       (ISR 写入, 128=静音中点)
PWMA_PSC = 0             (无分频)
载波频率 = 38MHz / 256 = 148.4kHz
```

寄存器配置:
- `CCMR1 = 0x68` — PWM mode 1, 预装载使能
- `CCER1 = 0x05` — CH1 输出使能, 低电平有效
- `PS |= 0x01` — P2.0 映射到 PWM1 输出
- `BKR = 0x80` — 主输出使能

#### 音频输出链路

```
Timer0 ISR (17640Hz)
  → 6 种音源混音 → s16 mix (-128~+127)
  → out = 128 + mix → u8 (0~255)
  → PWMA_CCR1L = out (直接写比较寄存器)
  → P2.0 输出 148kHz PWM 方波
  → RC 低通滤波 (截止 < 10kHz)
  → 运放缓冲
  → 扬声器 / 耳机
```

#### 设计要点

- 8-bit 分辨率: 256 级, 信噪比 ~48dB, 够用于 chiptune 风格
- 载波 148kHz: 远高于音频 20kHz, 简单一阶 RC 即可滤除
- 静音偏置 128: PWM 占空比 50% = 无音频输出
- `OPTIMIZE(8, SPEED)`: Keil 最高优化, 确保 ISR 在 56.7us (17640Hz 周期) 内完成

#### 为什么是 8-bit 而非 10-bit

STC32G12K128 支持 HSPWM 高级 PWM, 理论上可将 ARR 从 255 提升到 1023 (10-bit), 动态范围从 48dB 提升到 60dB。但实测发现:

- **10-bit 底噪问题**: ARR=1023 时, PWM 载波频率 = 38MHz / 1024 ≈ **37kHz**, 落在可听范围上限边缘, 产生明显的超声波底噪 (低龄人可听见)
- **8-bit 无底噪**: ARR=255 时, 载波频率 = 38MHz / 256 ≈ **148kHz**, 远超人耳上限, 一阶 RC 即可完全滤除
- **PLL 方案不可行**: 要在 10-bit 下保持 ≥140kHz 载波, 需要 PLL 提供 144MHz 时钟, 但 STC32G12K128 的 38MHz IRC 不是 PLL 标准输入频率, 锁频不稳定
- **HSPWM 异步桥不可用**: 通过 HSPWMA_ADR/DAT 异步桥写寄存器会引入 `while(busy)` 等待, 在 17640Hz ISR 中阻塞导致尖叫音

**结论**: 8-bit + 38MHz 是当前硬件的最优解 — 分辨率与底噪的平衡点。要突破此限制需换 STC32G144K246 (硬件 DAC, 不走 PWM)。

## 2. 音源架构

### 2.1 活跃音源总览

| 音源 | 命令前缀 | 通道数 | 渲染频率 | 说明 |
|------|---------|--------|---------|------|
| **AY8910** (YM2149) | `0xA0` | 3 方波 + 噪声 + 包络 | 17640Hz | 完美, ZX Spectrum/MSX 曲目 |
| **SN76489** | `0x50` | 3 方波 + 噪声 | 17640Hz | Sega Master System, 3 种变体 |
| **FM** (自定义 2-Op) | `0x51` | 16 voice (32 op) | 17640Hz | 2-Operator FM, 6 种波形 |
| **YM2413** (OPLL) | VGM | 9 ch (旋律+rhythm) | 17640Hz | 寄存器级兼容, 15 内置音色 + 鼓声 |
| **Gigatron** | `0xB0` | 4 ch | 8820Hz | 4ch TTL 波形, 直接写 fnum |
| **WT** (Wavetable) | `0xC0` | 4 ch | 17640Hz | 14 种波形, ADSR 包络 |
| **ADPCM** | `0xC0` | 6 ch | 17640Hz | 鼓声 + SF2 旋律采样 |
| **BRR** | `0xC0` | 4 ch | 17640Hz | 14 乐器 BRR 旋律采样 (SNES DSP filter=0) |

### 2.2 混音与处理

Timer0 ISR 17640Hz 逐 tick 渲染所有活跃音源, 累加后 clamp 到 8-bit DAC:
```
mix = ay*1.5 + sn*0.75 + fm*1.5 + gt*1.5 + wt*1.5 + adpcm*1.5
clamp(-128, 127) → 128+offset → PWM
```

#### UART 处理

每 294 tick (~60Hz) 调用 `process_uart()`, 从 2048 字节环形缓冲解析命令。

### 2.3 AY8910 (YM2149)

参考芯片 YM2149 (AY-3-8910), 完美仿真。

#### 架构

- **3 方波通道 + 1 噪声通道**: 每通道 12-bit 频率 (reg 0/1, 2/3, 4/5), 4-bit 音量 (reg 8-10)
- **包络发生器**: 12-bit 频率 (reg 11/12), 4 种形状 (reg 13: hold/alternate/attack/continue)
- **噪声**: 可编程分频 (reg 6), 17-bit LFSR (`seed ^= 0x24000 if LSB, seed >>= 1`)
- **混合**: 每通道独立的音调屏蔽 + 噪声屏蔽 (reg 7)
- **音量表**: 32 级 (`ay_voltbl[32]`, 16 级 x2 对称)

#### 频率映射

`AY_CLK = 1789772 Hz` (NTSC), 24-bit 基数 `AY_BASE_INCR = 212779134`。
内部计数器每 tick 增加 base_incr, 取高 8 位作为步进量驱动方波/噪声计数器。

#### 渲染

每 tick: 方波翻转 → 噪声 LFSR → 包络步进 → 查表混音。
方波输出 = 音量 × 方波/噪声混合, 总输出 = 3 通道之和。

### 2.4 SN76489

参考芯片 SN76489 (Sega Master System), 支持 3 种硬件变体。

#### 架构

- **3 方波通道 + 1 噪声通道**: 每通道 10-bit 频率 (高 6 位 + 低 4 位分两次写入), 4-bit 音量
- **音量表**: 16 级 (`sn_voltbl[16]`, 对数衰减: 255→0)
- **噪声**: 可编程分频 (reg 6 低 2 位: /1, /2, /4, /8)

#### 3 种变体

| 变体 | 移位寄存器宽度 | Taps | 说明 |
|------|---------------|------|------|
| SN76489 (TI) | 15 bit | 0x0003 (bit0,1) | 原版 TI |
| Sega VDP (默认) | 16 bit | 0x0009 (bit0,3) | SMS/Game Gear |
| SN76489A | 17 bit | 0x000C (bit2,3) | Atari 变体 |

噪声 LFSR: 白噪声模式 (bit4=0) `fb = rng & 1`, 周期噪声模式 (bit4=1) `fb = (masked != 0) && (masked != taps)`。

#### 渲染

`SN_CLK = 3579545 Hz`, `SN_BASE_INCR = 212779193`, 同 AY 的 24-bit 计数器。
方波翻转 + 噪声, 输出 `>>2` 衰减。

#### 命令格式

VGM 标准 2 字节: 首字节 `0x80|reg`, 次字节数据。锁存机制: `dat & 0x80` 时更新 last_reg。

### 2.5 FM 合成 (自定义 2-Op)

自定义精简 2-Operator FM 合成核心, 参考 ArduinoUnoTinyFmKeyboard 适配 38MHz/17640Hz。

#### 架构

- **16 voice, 32 operator**: 每 voice = op1 (调制器) + op2 (载波器)
- **6 种波形** x 64 entries = 384 bytes (code 段):

| 索引 | 名称 | 特征 |
|------|------|------|
| 0 | tri | 三角波, 64 点 |
| 1 | clipsin | 削顶正弦, ±20 饱和 |
| 2 | rect | 矩形波, ±21 |
| 3 | sin | 标准正弦, ±31 |
| 4 | saw | 锯齿波, ±31 |
| 5 | abssin | 绝对值正弦 (全波整流) |

- **相位累加器**: 16-bit (8.8 定点), `pos += step`, `idx = (pos >> 8) & 0x3F`
- **波形查表**: `fm_waves[(wave_idx << 6) | idx]` — 位移代替乘法
- **频率**: MIDI C1-C9 (note 24-127), 104 条目, `step = freq * 16384 / 17640`

#### 2-Operator FM 算法

每个 voice 每采样周期:
1. **OP1 (调制器)**: `idx = (pos>>8 + fb_val) & 0x3F`, `wave = fm_waves[wi*64+idx]`
2. **OP1 包络**: `ch_out = wave * (level+1) * (tl+1) >> 10` — 移位代替除法
3. **OP1 反馈**: `fb_val = ch_out >> fb` (fb=0-7), 累积到下次相位
4. **OP2 (载波器)**: `idx = (pos>>8 + op1_ch_out) & 0x3F` — 调频核心
5. **OP2 输出**: 同 OP1 包络公式
6. **voice_out = op2_out**, 总输出 = sum(voice_out)

#### 音色模板 (reg 0x00-0x09, 全局共用)

| 寄存器 | 说明 |
|--------|------|
| 0x00 | 调制器 MULTI (0-15) |
| 0x01 | 载波器 MULTI (0-15) |
| 0x02 | 调制器 TL (0-31, 调制深度) |
| 0x03 | 载波器 TL (高5位) + 反馈 (低3位) |
| 0x04 | 调制器 AR\|DR (高4=atk, 低4=dec) |
| 0x05 | 载波器 AR\|DR |
| 0x06 | 调制器 SL\|RR (高4=sul, 低4=rel) |
| 0x07 | 载波器 SL\|RR |
| 0x08 | 调制器波形 (低3位, 0-5) |
| 0x09 | 载波器波形 (低3位, 0-5) |

Note On 时音色模板自动应用到两个 operator。`mul=0` 时 step = freq/2。

#### ADSR 包络

4 态: Attack → Decay → Sustain → Release。
速度表 `fm_env_cnt[16]` (0-255) 控制每级包络的 tick 间隔。
`env_cnt` 倒计数到 0 触发一级变化。level 范围 0-31。
Round-robin: `fm_wait_cnt & 0x0F`, 每个 tick 只更新 1 个 operator 的包络 (16 voice = 每 16 tick 轮一圈)。

#### 运算优化

- 8.8 定点相位, 位移取波形索引 (>>8, & 0x3F), 无浮点
- 位移查表 `(wave_idx << 6)` 代替乘法索引
- 包络 `>> 10` 代替 `/(31*31)` (误差 < 0.5%)
- Round-robin 包络 tick 分散 CPU 负载
- 反馈 `>> fb` (0-7) 一条移位指令

### 2.5b YM2413 (OPLL) FM 合成

Yamaha YM2413 (OPLL) 寄存器级兼容, 通过 VGM 解析播放。15 内置音色 + 用户音色 + rhythm mode 鼓声。

#### 架构 (s8 精简核心)

- **9 通道**, 每通道 = modulator + carrier (2-Operator FM)
- **64 点 s8 波形表** (±31): 正弦 (WS=0) + 半正弦 (WS=1, 负半周镜像)
- **相位累加器**: 16.16 定点 u32, `pos += step`, `idx = (pos>>16) & 0x3F`, blk-1 修正八度
- **输出公式**: `(wave × (level+1) × (tl+1)) >> 10`, 结果 s8, 最后 `<<1`
- **Round-robin**: 每 16 采样 tick 一个 operator 的包络

#### 包络 (level 0~31 线性, AR/DR/RR 三张查表)

- **AR/DR/RR 表**: 各 16 个 u8 值, 反推自 emu2413 attack/decay/release 全程时间
- **key_on**: env_cnt=0 立即开始; atk≤2 (AR≥7) 瞬间到顶跳过 attack
- **EG 语义**: EG=1 sustaining (保持 SL) / EG=0 non-sustaining (继续用 RR 降)
- **env_tick**: 加法计数器 `cnt < step ? cnt++ : 走包络`, 消除旧减法 reset 250 的累积误差

#### 音量映射

- reg 0x30-0x38 低 4 位 = volume (0=最大, 15=最小)
- `vol = (15-reg_vol) << 2`, `car.tl = vol >> 1` (vol=0 最大→tl=30 满输出)

#### PC 验证工具

- `tools/ym2413_wav_gen.py`: 忠实 emu2413 移植 (render_emu2413) + V3 s8 调参核心 (render_fm_v3)
- `tools/fw_real_sim.py`: 严格 1:1 下位机 PC 仿真 (render_fw_real), 改下位机前必须在此验证

### 2.6 Gigatron TTL 波形

参考 Gigatron TTL 计算机, 4ch 波形合成。

#### 架构

- **4 通道**: 共享 256 字节波形表 (可运行时自定义写入)
- **16-bit 相位累加器**: `osc += step`, `idx = (osc >> 7) & 0xFC`
- **fnum 直接写入**: 14-bit (7-bit fnumL + 7-bit fnumH), `step = key * 44 / 101`
- **波形选择**: `wavX` (XOR 掩码) + `wavA` (幅度偏移)
- **渲染频率**: 8820Hz (每 2 tick 渲染一次)

#### 波形表

初始化时伪随机生成 4 种波形, 每 4 字节一组: noise/tri/pulse/saw。
运行时可通过 addr 0x14-0xFF 自定义写入任意波形数据。

#### 渲染

每通道: `idx = (osc >> 7) & 0xFC ^ wavX`, `val = sound[idx] + wavA`, clamp 到 0-63。
4 通道求和 + 偏置 3, 输出 `samp - 131` 映射到 ±128。

### 2.7 WT 波形表

Wavetable 波形表合成器, 参考 fm.c 架构和 ArduinoUno_wavetable_synthesis。

#### 架构

- **4 通道**: 独立相位/包络/音量
- **14 种预置波形** x 128 entries = 1792 bytes (code 段):

| 索引 | 名称 | 特征 |
|------|------|------|
| 0 | sq12 | GB duty 12.5% 方波 |
| 1 | sq25 | GB duty 25% 方波 |
| 2 | pulse50 | 50% 方波 |
| 3 | sq75 | GB duty 75% 方波 |
| 4 | sin | 标准正弦, ±31 |
| 5 | clipsin | 削顶正弦, ±20 饱和 |
| 6 | abssin | 绝对值正弦 (全波整流) |
| 7 | halfsin | OPL3 Sin1: +sine/0 |
| 8 | qsin | OPL3 Sin3: sine/0/sine/0 |
| 9 | altsin | OPL3 Sin4: 2x freq +/-/0/0 |
| 10 | althalfsin | OPL3 Sin5: 2x freq +/0/0/0 |
| 11 | tri | 三角波 |
| 12 | saw | 锯齿波 |
| 13 | gb_dmg | DMG 默认 WaveRAM |

- **相位累加器**: 16-bit, `pos += step`, `idx = (pos >> 5) & 0x7F`
- **波形查表**: `wt_waves[(wave_idx << 7) | idx]` — 7-bit 位移代替乘法
- **频率**: MIDI C1-C9 (note 24-127), 104 条目, `step = freq * 8192 / 17640`
- **波形长度**: 可切换 32/64/128 (reg 0x14)

#### ADSR 包络

4 态: Attack → Decay → Sustain → Release。
速度表 `wt_env_cnt[16]` (同 FM)。
Round-robin: `wt_wait_cnt & 0x03`, 每 4 tick 轮一圈 (4 通道)。

#### 渲染

每通道: 波形查表 → 包络 → `ch_out = wave * (level+1) * (vol+1) >> 10` → 求和。
音色模板 (reg 0x10-0x13) 全局共用, Note On 时应用到通道。

### 2.8 ADPCM 采样

YM2608 ADPCM Type-A 解码, 49 级 JEDI 查表, 12-bit 累加器。

#### 编码格式

- **JEDI 查表**: `jedi_table[49][16]` = 784 x s16 (1568 bytes, code 段)
- **12-bit 累加器**: 每 2 nibble 更新, `acc = CLIP12(acc + table[nibble])`
- **步进表**: `adpcm_step_inc[8] = {-16,-16,-16,-16,32,80,112,144}`
- **8-bit 压缩比**: ~3.2:1
- **线性插值**: `s_prev + (s_cur - s_prev) * frac >> 8`

#### ADPCM 解码原理

YM2608 Type-A ADPCM (自适应差分脉冲编码调制):

1. **存储**: 每个采样用 4-bit nibble 表示, 2 nibble 打包进 1 byte (ROM 地址按 nibble 编址)
2. **查表**: 以当前 `adpcm_step` (0-768) 为行, nibble 值 (0-15) 为列, 查 `jedi_table[step + nibble]` 得到差值 delta
3. **累加**: 12-bit 累加器 `acc = CLIP12(acc + delta)`, bit11 符号扩展到 s16
4. **自适应**: `adpcm_step += adpcm_step_inc[nib & 7]`, clamp [0, 768] — 量化误差大时 step 增大 (下次量化范围更宽), 误差小时 step 缩小 (精度更高)
5. **输出**: acc 即解码后的 12-bit 采样值

特点: 压缩比高 (~3.2:1), 算法简单 (查表+累加, 无乘除), 适合 8-bit MCU。缺点是量化噪声随频率升高而增大 (step 只能描述趋势, 不能精确编码高频)。

#### 鼓声 (6种, one-shot, 无循环)

| ID | 名称 | 采样长 (bytes) | 基准 Step | 说明 |
|----|------|----------------|---------|------|
| 0 | BD (Bass Drum) | 854 | 0x0100 | 底鼓 |
| 1 | SD (Snare) | 1219 | 0x0100 | 军鼓 |
| 2 | CY (Cymbal) | 5670 | 0x0080 | 镲片 |
| 3 | HH (Hi-Hat) | 732 | 0x0100 | 踩镲 |
| 4 | TM (Tom) | 1219 | 0x0080 | 嗵鼓 |
| 5 | RS (Rimshot) | 244 | 0x0080 | 边击 |

- 变频: Python 端计算 `step = base_step * ratio`, 通过 0x27/0x2D 写入
- 鼓变频无上限 (无循环, ISR 无压力)
- 包络: env_state=0 (无 ADSR), `out>>5` 增益归一化, `total += out * vol >> 5`

#### 鼓机序列播放器 (上位机)

鼓机由上位机 Python 驱动, 从配置文件读取 MIDI 音高映射 + 鼓声序列:

- **drum.ini**: 全局配置 — MIDI 音高映射 (`bass=36`, `snare=38`...)、音量、别名 (`oh=x+closed_hihat`)
- **drum_patterns/*.ini**: 每个风格一个文件, 包含 `[info]` (BPM/bars/swing) 和 `[pattern]` (节拍序列)
- **节拍序列**: 每行一个 step, 可用别名 (如 `bass`, `oh`) 或 MIDI 音高数字, `.` 为空拍
- **Swing**: `swing=50` 为 16 分音符三连音延迟百分比, 实现摇摆节奏

```
python tools/adpcm_drumkit_pro.py           # 依次播放全部风格
python tools/adpcm_drumkit_pro.py 3          # 只播第 3 个
python tools/adpcm_drumkit_pro.py list       # 列出全部风格
```

#### 鼓声变调

通过 step 寄存器 (0x27/0x2D) 改变 ADPCM 采样播放速率, 实现鼓声变调:
- `step = base_step * 2^(semi/12)`, semi=半音偏移, base_step 为各鼓声原始值
- 例如底鼓 base_step=0x0100, 升一个八度: step=0x0200, 降一个八度: step=0x0080
- 无循环, 变频无算力上限
- step < 0x0100 时启用线性插值 (sub-sample interpolation), 音质更平滑

```
python tools/adpcm_pitch_test.py             # 6 种鼓声半音阶变调演示
```

#### SF2 旋律乐器 (5种, 有循环, DSR 包络)

| ID | 名称 | 采样长 (bytes) | 循环区间 (nibbles) |
|----|------|----------------|-------------------|
| 0 | Piano | 1164 | 1915→2127 |
| 1 | SlapBass | 1835 | 3017→3512 |
| 2 | Guitar | 3722 | 7080→7291 |
| 3 | Oboe | 2015 | 2425→2852 |
| 4 | Harp | 3187 | 3374→6372 |

- ROM: `SF2_ROM[11936]` (11.7 KB), 12-bit 归一化 ADPCM
- 包络: DSR only (无 Attack), note_on 直接 level=31, note_off 触发 release
- 变频: 通过 0x27/0x2D 写 step, 上限 0x0400 (有循环, C5 以上死机)
- 循环: loop 回绕时恢复 acc/adpcm_step 状态 (防漂移)

#### SF2 乐器变调

SF2 旋律乐器支持 pitch shift, 上位机计算 step:
- `step = 0x0100 * 2^(semi/12)`, semi = midi_note - orig_pitch (采样基准音高)
- step 范围限制 0x0020-0x0200 (0.125x ~ 2x 速率), 防止循环解码溢出
- 播放流程: 先发 `0x15+ch` (note on, data=16+inst_idx) → 写 step → 发 `0x33` (midi note, 触发 DSR)

#### SF2 乐器 ADSR 模板

5 种 SF2 乐器的 DSR 参数 (atk 不使用, 设为默认值):

| 乐器 | atk | dec | sul | sus | rel | 特征 |
|------|-----|-----|-----|-----|-----|------|
| Piano | 3 | 4 | 8 | 5 | 4 | 中等衰减, 中 sustain |
| SlapBass | 2 | 9 | 14 | 14 | 4 | 快衰减, 高 sustain (近保持) |
| Guitar | 2 | 5 | 7 | 7 | 6 | 均衡衰减, 中等释放 |
| Oboe | 3 | 5 | 7 | 7 | 7 | 类似 Guitar, 释放稍慢 |
| Harp | 2 | 6 | 7 | 7 | 6 | 均衡, 类似 Guitar |

#### ADPCM 通道分配

6 个通道复用: ch0-5 可同时播放鼓声或 SF2 旋律。
通过 data 范围区分:
- data 0-5: 鼓声
- data 16-25: SF2 乐器 (16+inst_idx, inst_idx 0-4)

#### ADSR 包络 (SF2 旋律 + WT 共用)

| 参数 | 地址 | 说明 |
|------|------|------|
| Attack | 0x10 高4位 | SF2 旋律不使用 (直接 level=31) |
| Decay | 0x10 低4位 | 衰减速度 |
| Sustain Level | 0x11 高4位 | 0-15 |
| Sustain | 0x11 低4位 | 持续速度 |
| Release | 0x12 | 释放速度 |

包络速度表: `pcm_env_cnt[16] = {0,1,2,3,4,5,7,10,13,20,29,43,64,86,128,255}`
Round-robin: 每 4 tick 轮一圈 (6 通道)。

#### ADPCM 循环原理

ADPCM 解码是有状态的 (12-bit acc + step index 随采样推进变化), 循环不能简单跳回地址。

**SF2 旋律乐器循环方式**:
- ROM 中预存每个乐器的 `loop_start`, `loop_end` (nibble 地址) 和 `loop_acc`, `loop_step` (循环起点的解码器状态)
- 播放指针超过 loop_end 时: `addr = loop_addr; acc = loop_acc; adpcm_step = loop_step`
- 恢复解码器状态后, 循环点处的波形完美衔接, 无 pop/click

**鼓声**: one-shot, 无循环, 播放到 end_addr 自动停止并释放通道。

#### ADPCM ADSR 包络原理

ADPCM/SF2/BRR 三者共用相同的 ADSR 架构 (env_state 有限状态机):

```
note_on → Attack(1) → Decay(2) → Sustain(3) → note_off → Release(4) → level=0 释放通道
```

**速度控制** (env_cnt/step 计数器机制):
- `env_step` = 当前阶段的衰减间隔 (从 env_cnt 表查得)
- 每包络 tick: `env_cnt -= env_step`; 若 env_cnt >= env_step 则跳过, 否则 level 变化一步
- 数值越大 = 间隔越短 = 衰减越快

**SF2 特殊行为**: note_on 直接进入 Sustain (无 Attack), Sustain 阶段 **保持** level 不变 (不衰减), 等 note_off 触发 Release。这是 SF2 旋律乐器的设计: 有循环点支撑, 适合无限延音。

**BRR 特殊行为**: 完整 ADSR (有 Attack), Sustain 阶段 **继续衰减到 0** (非保持), sus 控制衰减速度。所有乐器最终都会自动衰减到静音并释放通道, 无需手动 note_off。

### 2.9 BRR 采样 (SNES DSP filter=0)

BRR (Binary Resonance Representation) 4ch 旋律采样合成, 参考 GME Spc_Dsp.cpp bit-exact 实现。

#### 架构

- **4 通道**: 独立循环/频率/包络/音量
- **14 种乐器**: 从 YRW801 (OPL4) ROM XI 文件生成 (gen_brr_rom.py)
- **编码格式**: BRR filter=0 (无状态, 9 字节/block, 16 采样/block, ~56% 压缩)
- **采样率**: 17640Hz (MCU DAC 甜点)
- **GME 精确解码**: `s = ((nibble >> rs) << ls) * 2`, rs/ls 查表

#### BRR 编码格式

SNES SPC700 DSP 的 BRR (Binary Resonance Representation) 格式:

- **Block 结构**: 每个 block 9 字节 = 1 byte header + 8 byte data
- **Header**: 高 4 bit = `scale` (0-15, 量化阶数), bit3 = loop 标志 (本项目固定 filter=0, 此位不使用)
- **Data**: 8 bytes = 16 nibble (每个 nibble 4-bit signed, 编码 16 个采样)
- **压缩比**: 16-bit PCM → 4-bit nibble ≈ 4:1, 加 header 开销 ≈ 3.5:1
- **Filter**: filter=0 (本项目选用), 无状态, 每个采样独立解码, 无需前一采样的滤波器状态

#### BRR 解码原理 (GME Spc_Dsp.cpp bit-exact)

本项目采用 filter=0 (最简模式, 无状态滤波):

1. **提取 nibble**: 从 block 的 8 byte data 中, 按采样索引定位 byte pair 和 pair 内位置
   - `bp = sample_idx >> 2` (0-3: 第几个 byte pair)
   - `sp = sample_idx & 0x03` (0-3: pair 内第几个 nibble)
2. **符号扩展**: `nybbles <<= (sp << 4)`, 高 4 bit 符号扩展为 s16
3. **缩放**: `raw >>= rs` (右移消除 scale 量化), `s = raw << ls` (左移恢复动态范围)
4. **增益**: `s <<= 1` (*2 增益补偿), clamp [-32768, 32767]
5. **输出**: s 即解码后的 16-bit 采样值

shift 表 (16 级 scale):
- `brr_right_shift[16] = {13,12,12,...,16,16,16}` — scale 越大右移越多, 量化噪声越大
- `brr_left_shift[16] = {0,0,1,2,...,11,11,11,11}` — 左移补偿, scale 越大左移越多

**vs ADPCM 对比**:
| | ADPCM (YM2608) | BRR (SNES DSP) |
|--|----------------|----------------|
| 压缩单位 | nibble (4-bit) | block (9 bytes/16 samples) |
| 有状态 | 是 (acc + step) | 否 (filter=0) |
| 循环复杂度 | 需恢复 acc+step | 简单地址跳回 |
| 量化噪声 | 自适应 (低频好) | 固定 scale (平坦) |
| MCU 算力 | 查表+累加 (轻量) | 移位+查表 (轻量) |

#### 乐器列表

| # | 名称 | native_midi | ROM 大小 | 特征 |
|---|------|-----------|---------|------|
| 0 | AcPiano | 51 | 8289B | 明亮原声钢琴 (s2) |
| 1 | Violin | 45 | 1560B | 小提琴 |
| 2 | Strings | 42 | 4944B | 弦乐组 |
| 3 | Harp | 34 | 2256B | 竖琴 |
| 4 | Accordion | 38 | 1764B | 手风琴 |
| 5 | Organ | 63 | 648B | 管风琴 |
| 6 | Fretless | 46 | 1792B | 无品贝斯 |
| 7 | JazzGtr | 58 | 504B | 爵士吉他 |
| 8 | DistGtr | 59 | 576B | 失真吉他 |
| 9 | Celesta | 30 | 2904B | 钢片琴 |
| 10 | Flute | 42 | 1764B | 长笛 |
| 11 | Recorder | 43 | 3168B | 竖笛 |
| 12 | Oboe | 40 | 1404B | 双簧管 |
| 13 | Clarinet | 51 | 1344B | 单簧管 |

ROM 总计 ~23KB, 全部 seam=0 (完美循环)。

#### ADSR 包络

4 态: Attack → Decay → Sustain → Release。
速度表 `brr_env_cnt[16]` (同 FM/WT)。
Round-robin: 每 4 tick 轮一圈 (4 通道)。

**ADSR 直接控制音量**: `out * level >> 5`, 不经过 vol。

| 参数 | 地址 | 含义 |
|------|------|------|
| atk (高4) \| dec (低4) | 0x18 | attack/decay 速度 |
| sul (高4) \| sus (低4) | 0x19 | decay 终止目标 (sul*2=level) / sustain 衰减速度 |
| rel | 0x1A | release 速度 |

**关键行为**: sustain 阶段继续衰减到 0 (非保持), sus 控制衰减速度。level=0 自动释放通道。

#### BRR 乐器 ADSR 模板 (14 乐器)

按 ROM 乐器编号排序, 均已调试验证 (atk/dec/sul/sus/rel 范围 0-15, 索引 env_cnt[], 数值越大越快):

| # | 乐器 | atk | dec | sul | sus | rel | 特征 |
|---|------|-----|-----|-----|-----|-----|------|
| 0 | AcPiano | 13 | 3 | 2 | 4 | 4 | 瞬起音, 快衰减, 低终止, 中持续/释放 |
| 1 | Violin | 10 | 4 | 2 | 10 | 10 | 中起音, 慢衰减/持续/释放 (持续乐) |
| 2 | Strings | 10 | 4 | 2 | 10 | 10 | 同 Violin |
| 3 | Harp | 15 | 8 | 2 | 4 | 4 | 瞬起音, 中衰减, 类似钢琴 |
| 4 | Accordion | 7 | 3 | 8 | 4 | 4 | 中起音, 快衰减, 高终止 (保持感) |
| 5 | Organ | 5 | 6 | 12 | 6 | 5 | 慢起音, 中衰减, 高终止 (持续) |
| 6 | Fretless | 15 | 3 | 12 | 2 | 2 | 瞬起音, 快衰减, 高终止, 极快持续/释放 |
| 7 | JazzGtr | 15 | 3 | 12 | 2 | 2 | 同 Fretless |
| 8 | DistGtr | 15 | 8 | 2 | 4 | 4 | 瞬起音, 中衰减, 低终止 |
| 9 | Celesta | 15 | 10 | 6 | 2 | 2 | 瞬起音, 慢衰减, 中终止, 极快持续/释放 |
| 10 | Flute | 3 | 4 | 9 | 5 | 4 | 慢起音, 中衰减, 高终止 (持续) |
| 11 | Recorder | 10 | 4 | 2 | 10 | 10 | 中起音, 慢衰减/持续/释放 |
| 12 | Oboe | 10 | 4 | 2 | 10 | 10 | 同 Recorder |
| 13 | Clarinet | 10 | 4 | 2 | 10 | 10 | 同 Recorder |

持续乐器 (Violin/Strings/Organ/Flute/Recorder/Oboe/Clarinet): sul 低 + sus/rel 慢 → sustain 阶段缓慢衰减, 延音长。
弹拨乐器 (AcPiano/Harp/DistGtr): sul 低 + dec 快 → 短促衰减, 延音短。

#### BRR 循环原理

BRR filter=0 是无状态解码, 循环比 ADPCM 简单得多 — 只需跳回 block 地址, 无需恢复解码器状态。

**循环方式**: ROM 中每个乐器存储 `n_blocks` (总 block 数) 和 `loop_block` (循环起始 block)。播放指针到达末尾时:
```
if (block_idx >= n_blocks) block_idx = loop_block;
```
直接跳回, 下一采样继续从 loop_block 的 sample 0 解码, 波形无缝衔接。

**seam=0 验证**: ROM 生成时 (gen_brr_rom.py), 对每个乐器的循环点进行交叉淡出处理, 验证循环起止处的采样差值为 0 (seam=0), 确保无 pop/click。

**vs ADPCM 循环**: ADPCM 需要同时恢复 `acc` 和 `adpcm_step` 两个状态量才能无缝循环; BRR filter=0 无状态, 一个地址跳回就完成循环, 这也是本项目选择 BRR 而非 ADPCM 做旋律采样的原因之一。

#### 变频原理

变频通过改变采样播放速率实现, 所有采样模块共用同一机制:

**8.8 fixed-point step**: step 值的高 8 位 = 每采样周期推进几个采样, 低 8 位 = 小数部分 (用于线性插值)。
- `step = 0x0100` = 原速 (每 tick 推进 1.0 个采样)
- `step = 0x0200` = 2x 速 (高一个八度)
- `step = 0x0080` = 0.5x 速 (低一个八度)

**半音步进**: `step = 0x0100 * 2^(semi/12)`, 上位机 Python 计算后写入 MCU step 寄存器。
MCU 端也预存了 12 级半音查表 (`brr_semi_up[12]`, `brr_semi_dn[12]`), 可根据 midi note 差值直接查表乘以八度偏移。

**线性插值**: 当 step < 0x0100 (降调) 时, frac 部分用于相邻采样间线性插值:
`out = s_prev + (s_cur - s_prev) * frac >> 8`
避免降调时因采样跳步造成的锯齿噪声。

#### ROM 生成工具链

```
XI 文件 → resample 17640Hz → PCM crossfade → BRR encode → BRR crossfade → verify seam=0
```
详见 [docs/xi_brr_workflow.md](docs/xi_brr_workflow.md) 和 [docs/brr_adsr_debug.md](docs/brr_adsr_debug.md)。

### 2.10 已放弃的音源

以下 4 种音源在 STC8H8K64U 原型阶段实现, 迁移至 STC32G 后因资源/优先级考虑未启用。源码文件仍保留于 `STC32G12K128/` 目录, `main.c` 中 `#include` 已注释, UART 命令分支保留但无效。

| 音源 | 命令前缀 | 通道数 | 状态 | 放弃原因 |
|------|---------|--------|------|---------|
| **SCC** (Konami) | `0xD2` (4 字节) | 5 ch | 源码存在, 注释 | WT 完善后不再需要, 且 SCC 需 A51 汇编辅助 |
| **GB DMG** (Game Boy) | `0xB3` (3 字节) | 4 ch | 源码存在, 注释 | 功能与 WT sq12/sq25/sq75/gb_dmg 波形重叠 |
| **NES APU** (Ricoh 2A03) | `0xB4` (3 字节) | 2 脉冲+1 三角+1 噪声+1 DMC | 源码存在, 注释 | 与 AY8910/SN76489 功能重叠, CPU 开销大 |
| **SAA1099** (Philips) | `0xBD` (3 字节) | 6 ch + 2 噪声 | 源码存在, 注释 | 通道数需求不足, 与现有音源重叠, 见 SAA 失败记录 |

> 相关文件: `scc.c/h` `gb.c/h` `nes.c/h` `saa1099.c/h` (及对应的 `.LST` 编译输出)
> 相关工具: `tools/gen_scc_table.py` (SCC 步进查表生成, 历史遗留)

---

## 3. UART 协议

### 3.1 通用命令

| 命令 | 格式 | 校验 | ACK | 说明 |
|------|------|------|-----|------|
| SN76489 | `[0x50][data]` | 无 | 无 | 2 字节, 透明 |
| SN76489 变体 | `[0x52][variant]` | 无 | 无 | 0=SN76489 1=SegaVDP 2=SN76489A |
| AY8910 | `[0xA0][reg][data]` | 无 | 无 | 3 字节, 透明 |
| FM | `[0x51][addr][data][xor]` | XOR | 0xAA/0xFF | 4 字节 |
| Gigatron | `[0xB0][addr][data][xor]` | XOR | 丢弃 | 4 字节 |
| WT/ADPCM/BRR | `[0xC0][addr][data][xor]` | XOR | 0xAA/0xFF | 4 字节, addr 范围区分模块 |

### 3.2 WT 寄存器 (0xC0, addr 0x00-0x14)

WT 和 ADPCM/BRR 共用 0xC0 前缀, main.c 按 addr 范围路由: 0x00-0x14→WT, 0x15-0x33→ADPCM, 0x34-0x4F→BRR。

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

### 3.3 FM 寄存器 (0x51, addr 0x00-0x3F)

| 地址 | 说明 |
|------|------|
| 0x00-0x09 | 音色参数 (全局共用, 10 字节) |
| 0x10-0x1F | Note On voice 0-15 (data=MIDI note) |
| 0x20-0x2F | Note Off voice 0-15 |
| 0x30-0x3F | Volume override voice 0-15 (0-31) |

### 3.4 ADPCM 寄存器 (0xC0, addr 0x15-0x33)

| 地址 | 说明 |
|------|------|
| 0x15-0x1A | ch0-5 Note On (data: 0-5=鼓声, 16-25=SF2乐器) |
| 0x1B-0x20 | ch0-5 Note Off |
| 0x21-0x26 | ch0-5 Volume (0-31) |
| 0x27-0x2C | ch0-5 Step Hi (变频步进高位) |
| 0x2D-0x32 | ch0-5 Step Lo (变频步进低位) |
| 0x33 | MIDI Note (紧跟 SF2 Note On, 24-95) |

### 3.5 BRR 寄存器 (0xC0, addr 0x34-0x4F)

| 地址 | 说明 |
|------|------|
| 0x34-0x37 | ch0-3 Note On (data: 0-13=乐器索引) |
| 0x38-0x3B | ch0-3 Note Off |
| 0x3C-0x3F | ch0-3 Volume (0-31) |
| 0x40-0x43 | ch0-3 MIDI Note (24-127) |
| 0x44-0x47 | ch0-3 Step Hi (8.8 fp) |
| 0x48-0x4B | ch0-3 Step Lo (8.8 fp) |
| 0x4C | ADSR atk\|dec |
| 0x4D | ADSR sul\|sus |
| 0x4E | ADSR rel |

---

## 4. 上位机工具

所有串口工具默认 COM12 @ 115200 baud (可在脚本头部修改)。
依赖: `pip install pyserial`

### 4.1 VGM 播放器

```
python tools/vgm_player.py --list --vgm-dir vgm/ay8910     # 列出 AY8910 曲目
python tools/vgm_player.py 10 --vgm-dir vgm/ay8910          # 播放第 10 首
python tools/vgm_player.py --list --vgm-dir vgm/sn76489     # 列出 SN76489 曲目
python tools/vgm_player.py 16 --vgm-dir vgm/sn76489          # 播放第 16 首
python tools/vgm_player.py --list --vgm-dir vgm/opll        # 列出 FM 曲目
python tools/vgm_player.py <编号> --vgm-dir vgm/opll         # 播放 FM
python tools/vgm_player.py --fm-note 0 60                     # FM ch0 C4 单音
python tools/vgm_player.py --fm-scale                         # FM C1-C9 扫频
python tools/vgm_player.py --wt-scale                         # WT C2-C6 扫频
python tools/vgm_player.py --loop --vgm-dir vgm/ay8910       # 循环播放
python tools/vgm_player.py --speed 0.5 --vgm-dir vgm/ay8910  # 0.5x 变速
```

支持芯片: AY8910, SN76489, FM, WT, Gigatron。
参数: `--port COM3` `--baud 115200` `--dump 1` (十六进制转储命令流)

### 4.2 ADPCM 鼓声测试

```
python tools/adpcm_test.py                    # 14 种节奏风格全部播放
python tools/adpcm_test.py 3                  # 播放第 3 个风格
```

硬编码 14 种风格 (Modern/Rock/Pop/Funk/HipHop/Ballad/SlowRock/HardRock/Disco/DancePop/Trance/Jazz/Bossa/Square), 6 种鼓声 (BD/SD/CY/HH/TM/RS)。

### 4.3 ADPCM 鼓机 (ini 驱动)

```
python tools/adpcm_drumkit_pro.py             # 播放全部风格
python tools/adpcm_drumkit_pro.py 3          # 播放第 3 个
python tools/adpcm_drumkit_pro.py list       # 列出全部风格
```

从 `drum.ini` 读取 MIDI 映射 (35-81) + 别名 + 音量, 从 `drum_patterns/*.ini` 读取节奏序列。
支持 per-drum 音量、per-pattern 音量覆盖、swing 节拍。

### 4.4 ADPCM 变频测试

```
python tools/adpcm_pitch_test.py             # 6 鼓 C1→C8 变频扫频
python tools/adpcm_div_test.py               # 同鼓不同 step 对比
```

### 4.5 ADPCM 通道调试

```
python tools/adpcm_ch_test.py                 # 逐通道发声确认
python tools/adpcm_debug.py                   # 触发通道 + 读 channel mask
python tools/adpcm_led_test.py                 # 6 通道 LED 确认
```

### 4.6 SF2 旋律测试

```
python tools/sf2_test.py                      # 5 乐器依次原音播放
python tools/sf2_test.py piano 60             # 钢琴 C4
python tools/sf2_test.py all 60               # 所有乐器 C4
python tools/sf2_test.py chord                # 和弦测试
```

### 4.7 SF2 变频扫频

```
python tools/sf2_sweep.py                     # 所有乐器 C1→4x→C1
python tools/sf2_sweep.py piano               # 钢琴
python tools/sf2_pitch_test.py                # 鼓路径变频 (无 ADSR)
```

### 4.8 WT 扫频测试

```
python tools/wt_scale_test.py                 # 14 种波形 C2↔C6 循环扫频
python tools/wt_pcm_debug.py                  # WT+ADPCM 简单测试
```

### 4.9 BRR 扫频测试

```
python tools/brr_uart_test.py                 # 14 乐器扫频 (上行→下行, 4ch 轮转)
python tools/brr_uart_test.py 0               # 只测 AcPiano (按编号)
python tools/brr_uart_test.py violin           # 只测 Violin (按名称)
```

### 4.10 离线工具 (无需串口)

**SF2 采样处理链**:
```
python tools/sf2_extract.py                  # SF2 → WAV + JSON + C header
python tools/sf2_preview.py                  # PC 模拟 MCU ADPCM 解码 (含循环+变频)
python tools/sf2_verify.py                   # ADPCM 编解码往返验证
python tools/sf2_loop_sim.py                  # PC 模拟 MCU 循环回绕行为
python tools/sf2_player_sim.py <dir> [idx] [note] [dur]  # 完整 ADPCM 播放模拟
python tools/sf2_drum_test.py                  # SF2 乐器用鼓编码器验证
python tools/sf2_snese_sim.py                  # SNES SoundFont 预览 WAV
```

**ADPCM ROM 生成**:
```
python tools/gen_adpcm_rom.py                 # WAV → ADPCM ROM C header (sf2_rom.h)
python tools/adpcm_preprocess.py              # YM2608 原始鼓 → 重采样 17640Hz → ADPCM C header
python tools/adpcm_decode_wav.py               # ROM → WAV 解码验证
python tools/adpcm_interp_test.py             # PC 线性插值算法验证
python tools/adpcm_step_sim.py                 # PC 定点步进变频模拟
```

**循环搜索算法**:
```
python tools/adpcm_perfect_loop.py            # 最小方差 + 回文 + 交叉淡出自动寻环
python tools/fix_loop.py                      # 振幅+斜率匹配搜索更优 loop_end
python tools/polyphone_loop.py                 # 多点质量评分 + 交叉淡出烘焙
```

**BRR 格式 (SNES DSP)**:
```
python tools/brr_test.py                      # BRR 编解码验证 (GME Spc_Dsp 兼容)
python tools/brr_loop.py                      # BRR 块状循环模拟
python tools/gen_brr_rom.py                  # XI → BRR ROM C header 生成 (14 乐器)
python tools/brr_uart_test.py                 # BRR 14乐器扫频测试 (串口)
```

**XI 格式 (YRW801/OPL4 波形)**:
```
python tools/xi_parse.py --list               # 列出 XI 乐器
python tools/xi_parse.py --wav 0x10 0x16       # 导出 WAV
python tools/xi_demo.py                        # XI 乐器包络+循环预览
python tools/xi_adpcm_test.py                  # XI → ADPCM 循环测试
python tools/xi_brr_test.py                    # XI → BRR filter=0 循环测试
python tools/xi_crossfade_test.py              # XI 交叉淡出循环测试
python tools/yrw801_extract.py                 # YRW801 ROM 直接解析 + WAV 导出
```

**其他**:
```
python tools/piano_pitch_sweep.py             # Grand Piano C3 采样 C1-C8 扫频
python tools/gen_scc_table.py                 # SCC 步进查表生成 (STC8H 历史遗留)
```

### 4.11 配置文件

| 文件 | 说明 |
|------|------|
| `tools/drum.ini` | MIDI GM 35-81 鼓组映射 (drum_id + ratio) + 19 别名 + 全局音量 |
| `tools/drum_patterns/*.ini` | 14 个独立风格节奏序列 (bpm/bars/swing/vol) |

## 5. 工具链与编译

### 5.1 工具链

| 工具 | 版本/路径 | 说明 |
|------|---------|------|
| 编译器 | `D:/Keil_v5/C251/BIN/C251.exe` | Keil C251 (非 C51), STC32G 兼容 C251 指令集 |
| 链接器 | `D:/Keil_v5/C251/BIN/L251.exe` | C251 链接器 (非 BL51) |
| HEX 转换 | `D:/Keil_v5/C251/BIN/OH251.exe` | 输出 Intel HEX |
| 烧录 | STC-ISP | 手动烧录 (串口 P3.4/P3.5) |
| 上位机 | Python 3 + pyserial | 测试/播放工具 |

**为什么是 Keil C251 而非 SDCC/PIO**:

STC32G12K128 使用 32 位 1T 8051 内核，只有 Keil C251 支持其 C251 扩展指令集（32 位运算、32-bit 位移等）。`OPTIMIZE(8, SPEED)` 极限优化下的代码密度和执行效率远超 SDCC 对 8051 的支持。更重要的是 **Keil 允许命令行调用**（`C251.EXE` / `L251.EXE` / `OH251.EXE`），使得 Python → 编译 → hex 的全自动化流水线成为可能，这是本项目能走到 BRR 14 乐器 ROM 自动生成 + 编译 + 烧录的先决条件。SDCC 不支持 C251 扩展指令集，PIO 没有 Keil C251，在此平台上基本等于不可用。

### 5.2 编译选项

```
#pragma LARGE          — LARGE 内存模型 (xdata/XRAM)
#pragma OPTIMIZE(8, SPEED) — 最高优化等级, 优速
```

### 5.3 编译步骤

**方法一: 分步编译**
```bash
cd STC32G12K128
rm -f *.OBJ
D:/Keil_v5/C251/BIN/C251.exe ay8910.c "LARGE" "OPTIMIZE(8,SPEED)" "NOALIAS" 2>&1
D:/Keil_v5/C251/BIN/C251.exe sn76489.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1
D:/Keil_v5/C251/BIN/C251.exe fm.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1
D:/Keil_v5/C251/BIN/C251.exe gigatron.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1
D:/Keil_v5/C251/BIN/C251.exe wt.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1
D:/Keil_v5/C251/BIN/C251.exe adpcm.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1
D:/Keil_v5/C251/BIN/C251.exe brr.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1
D:/Keil_v5/C251/BIN/C251.exe main.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1
D:/Keil_v5/C251/BIN/L251.exe ay8910.OBJ,sn76489.OBJ,fm.OBJ,gigatron.OBJ,wt.OBJ,adpcm.OBJ,brr.OBJ,main.OBJ TO build/MAIN 2>&1
D:/Keil_v5/C251/BIN/OH251.exe build/MAIN HEXFILE\(build/MAIN.hex\) 2>&1
```

**方法二: 一行命令 (bash)**
```bash
cd STC32G12K128 && rm -f *.OBJ ; D:/Keil_v5/C251/BIN/C251.exe ay8910.c "LARGE" "OPTIMIZE(8,SPEED)" "NOALIAS" 2>&1 ; D:/Keil_v5/C251/BIN/C251.exe sn76489.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1 ; D:/Keil_v5/C251/BIN/C251.exe gigatron.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1 ; D:/Keil_v5/C251/BIN/C251.exe fm.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1 ; D:/Keil_v5/C251/BIN/C251.exe wt.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1 ; D:/Keil_v5/C251/BIN/C251.exe adpcm.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1 ; D:/Keil_v5/C251/BIN/C251.exe brr.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1 ; D:/Keil_v5/C251/BIN/C251.exe main.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1 ; D:/Keil_v5/C251/BIN/l251.exe ay8910.OBJ,sn76489.OBJ,fm.OBJ,gigatron.OBJ,wt.OBJ,adpcm.OBJ,brr.OBJ,main.OBJ TO build/MAIN 2>&1 ; D:/Keil_v5/C251/BIN/OH251.exe build/MAIN HEXFILE\(build/MAIN.hex\) 2>&1 ; echo "BUILD DONE"
```

### 5.4 编译注意事项

- 编译器是 `C251.EXE` (不是 C51), 链接器是 `L251.EXE` (不是 BL51)
- bash 下用 `;` 分隔命令, 不能用 `&&` — C251 WARNING 返回非零会中断 `&&`
- bash 下括号要加引号: `"LARGE"` `"OPTIMIZE(8,SPEED)"`
- HEX 参数括号要转义: `HEXFILE\(build/MAIN.hex\)`
- 必须先 `rm -f *.OBJ` 清理旧目标文件
- `WARNING C115/C153` 可忽略
- 输出: `build/MAIN.hex` → 用 STC-ISP 手动烧录

## 6. 目录结构

```
STC_Chiptune/
├── STC32G12K128/              # 固件 (Keil C251)
│   ├── main.c                # 主程序 (Timer0 ISR + UART + 混音 + LED)
│   ├── ay8910.c/h            # AY8910 仿真 (3ch+噪声+包络)
│   ├── sn76489.c/h           # SN76489 仿真 (3ch+噪声, 3变体)
│   ├── fm.c/h                # FM 2-Op 合成 (16 voice / 32 op / 6波形)
│   ├── gigatron.c/h          # Gigatron TTL 波形 (4ch, 256B共享表)
│   ├── wt.c/h                # Wavetable 合成 (4ch / 14波形 / ADSR)
│   ├── adpcm.c/h             # ADPCM 解码 (6ch: 鼓声+SF2旋律)
│   ├── brr.c/h               # BRR 4ch 旋律采样 (SNES DSP filter=0)
│   ├── brr_rom.h             # BRR ROM (14 乐器, ~23KB, seam=0)
│   ├── types.h               # 共享类型定义
│   ├── sf2_rom.h             # SF2 采样 ROM (5乐器, 11936B)
│   ├── fmopn_2608rom.h       # YM2608 ADPCM 鼓声 ROM + JEDI表
│   └── build/                # 编译输出 (MAIN.hex)
│
├── tools/                    # Python 上位机工具
│   ├── vgm_player.py         # VGM 播放器 (AY/SN/FM/WT/Gigatron)
│   ├── adpcm_test.py         # 鼓声节奏测试 (14风格硬编码)
│   ├── adpcm_drumkit.py      # 鼓机基础版
│   ├── adpcm_drumkit_pro.py  # 鼓机加强版 (ini驱动)
│   ├── adpcm_pitch_test.py   # 鼓变频扫频
│   ├── adpcm_div_test.py     # 鼓 step 对比测试
│   ├── adpcm_ch_test.py      # ADPCM 逐通道测试
│   ├── adpcm_debug.py        # ADPCM 通道 mask 调试
│   ├── adpcm_led_test.py     # ADPCM LED 测试
│   ├── gen_adpcm_rom.py      # WAV → ADPCM ROM C header 生成
│   ├── adpcm_preprocess.py   # YM2608 原始鼓重采样+编码
│   ├── adpcm_decode_wav.py   # ROM → WAV 解码验证
│   ├── adpcm_interp_test.py  # 线性插值算法验证
│   ├── adpcm_step_sim.py     # 定点步进变频模拟
│   ├── adpcm_perfect_loop.py # 自动寻环 (最小方差+回文+交叉淡出)
│   ├── adpcm_wav_test.py     # ADPCM 编解码实验
│   ├── fix_loop.py           # 搜索更优 loop_end
│   ├── polyphone_loop.py     # 多点质量评分寻环
│   ├── brr_test.py           # BRR 编解码验证 (SNES DSP)
│   ├── brr_loop.py           # BRR 块状循环模拟
│   ├── sf2_extract.py        # SF2 → WAV + JSON + C header
│   ├── sf2_test.py           # SF2 旋律硬件测试
│   ├── sf2_sweep.py          # SF2 变频扫频
│   ├── sf2_pitch_test.py     # SF2 鼓路径变频测试
│   ├── sf2_preview.py        # SF2 PC 模拟 (ADPCM+循环+变频)
│   ├── sf2_verify.py         # ADPCM 编解码往返验证
│   ├── sf2_loop_sim.py       # PC 循环回绕模拟
│   ├── sf2_player_sim.py     # 完整 ADPCM 播放模拟
│   ├── sf2_drum_test.py      # SF2 鼓编码器验证
│   ├── sf2_snese_sim.py      # SNES SoundFont 预览
│   ├── xi_parse.py           # YRW801 XI 解析+WAV导出
│   ├── xi_demo.py            # XI 乐器预览
│   ├── xi_adpcm_test.py      # XI → ADPCM 循环测试
│   ├── xi_brr_test.py        # XI → BRR filter=0 测试
│   ├── xi_crossfade_test.py  # XI 交叉淡出测试
│   ├── xi_brr_crossfade_test.py # XI BRR 交叉淡出测试
│   ├── yrw801_extract.py     # YRW801 ROM 解析+WAV导出
│   ├── piano_pitch_sweep.py  # Grand Piano C3 扫频
│   ├── wt_scale_test.py      # WT 14波形 C2↔C6 扫频
│   ├── wt_pcm_debug.py       # WT+ADPCM 简单测试
│   ├── gen_scc_table.py      # SCC 查表生成 (历史遗留)
│   ├── drum.ini              # MIDI 35-81 鼓组映射+别名+音量
│   └── drum_patterns/        # 14个风格独立节奏 ini
│
├── vgm/                      # VGM 曲目库
│   ├── ay8910/               # AY8910 (ZX Spectrum / MSX)
│   ├── sn76489/              # SN76489 (Sega Master System)
│   └── opll/                 # FM OPLL (YM2413)
│
├── docs/                     # 技术文档
├── README.md                 # 中文文档
└── README_EN.md              # English documentation
```

## 7. 开发历程

### 7.1 Phase 1-6: STC8H8K64U 时代

8051 (48MHz) 上的原型开发: SCC/AY8910/SN76489 仿真, GB/NES/SAA 失败尝试。
详见 git history。

### 7.2 Phase 7: 迁移 STC32G12K128

STC32G C251, 38MHz, 128KB Flash, 4KB SRAM + 8KB XRAM。
- 移植全部音源到 C251
- 新增 FM (自定义 2-Op) 16 voice 合成
- 新增 Gigatron 4ch TTL 波形
- SCC 剔除 (WT 完善, 不再需要)

### 7.3 Phase 8: ADPCM 采样

- 实现 YM2608 ADPCM Type-A 解码器 (JEDI 表, 12-bit acc)
- 从 SF2 音色库提取 5 种乐器 (Piano/SlapBass/Guitar/Oboe/Harp)
- 6 种鼓声 ROM (BD/SD/CY/HH/TM/RS)
- DSR 包络 (无 Attack, 避免 4-bit 量化破音)
- 鼓声变频: Python 端计算 step, MCU 不做计算
- SF2 变频上限 0x0400 (有循环, C5 以上 ISR 死机)
- 鼓变频无上限 (无循环, 无压力)

### 7.4 Phase 9: WT 波形扩充

- 14 种预置波形 (原 6 种 + 8 种 OPL3/GB 风格)
- 波形长度可切换 (32/64/128)
- C2↔C6 循环扫频测试

### 7.5 Phase 10: 鼓机系统

- 14 种节奏风格 (Modern/Rock/Pop/Funk/HipHop/Ballad/SlowRock/HardRock/Disco/DancePop/Trance/Jazz/Bossa/Square)
- ini 驱动: drum.ini (映射+别名+音量) + drum_patterns/ (独立风格)
- MIDI GM Percussion 35-81 全覆盖
- 19 个变频别名快捷键

### 7.6 Phase 11: BRR 旋律采样

- 实现 SNES DSP BRR filter=0 解码器 (GME Spcc_Dsp.cpp bit-exact)
- 从 YRW801 XI 文件生成 14 乐器 ROM (~23KB, 全部 seam=0)
- BRR ROM 生成链: resample → PCM crossfade → BRR encode → BRR crossfade → verify
- ADSR 包络 (参考 Arduino wavetable synth 实现)
- ADSR 调试修复 5 个 bug (路由范围/音量公式/sul映射/sustain行为/通道释放)
- 14 乐器 ADSR 模板调试验证 (钢琴/提琴/吉他/钢片琴等)
- 变频: 8.8 fixed-point step + 半音步进表, 上限 ~+6 半音

## 8. 参考项目与移植说明

本项目音源核心均移植自开源项目, 针对 STC32G12K128 (C251, 38MHz, 4KB SRAM, 8KB XRAM) 做了深度精简和适配。

### 8.1 AY8910 — 参考 libvgm (开源, BSD-3-Clause)

- **原作者**: Couriersud (libvgm), 基于 Ville Hallik / Michael Cuddy / Tatsuyuki Satoh / Fabrice Frances / Nicola Salmoria 的早期工作, 2008 年大幅重写
- **原始项目**: `D:\working\vscode-projects\Reference_Project\vgm_libs\libvgm-master\emu\cores\ay8910.c` + `ayintf.c`
- **原版规模**: ~1620 行 (`ay8910.c`) + 接口层 + 依赖 `EmuStructs.h / snddef.h / EmuCores.h` 等框架

**精简要点 (1620 行 → 230 行, 约 86% 代码量缩减)**:
- 去掉 DEV_DATA/DEV_DEF/DEVFUNC 全部框架接口, 改为直接函数调用 (`ay_wr()` / `ay_render()`)
- 去掉 I/O 端口 (AY8910 的 8-bit parallel port), 只保留纯音频寄存器 (0-15)
- 去掉通道混合 DAC 模型 (R-C 负载网络、内部阻抗 AY8910_INTERNAL_RESISTANCE=356 等精确模拟), 改为 32 级音量表直查
- 去掉浮点采样率重采样, 固定 17640Hz 输出, 频率基数预计算 (`AY_BASE_INCR`)
- 去掉立体声/声像/静音/选项位等高级功能
- 去掉 AY8930 扩展模式、YM2149 分频器选择等变体支持
- 包络保持完整 4 形状 (hold/alternate/attack/continue)

### 8.2 SN76489 — 参考 libvgm (开源, BSD-3-Clause)

- **原作者**: Maxim (2001-2002), 从 Delphi 原始实现转换, Charles MacDonald 修改用于 SMS Plus
- **原始项目**: `D:\working\vscode-projects\Reference_Project\vgm_libs\libvgm-master\emu\cores\sn76489.c` + `sn76489_private.h` + `sn764intf.c`
- **原版规模**: ~530 行 (`sn76489.c` + `sn76489_private.h`) + 接口层

**精简要点 (530 行 → 165 行, 约 69% 代码量缩减)**:
- 去掉 DEV_DATA/DEV_DEF 框架接口, 改为直接函数调用 (`sn_wr()` / `sn_render()`)
- 去掉浮点 `dClock` 频率跟踪, 改为预计算 `SN_BASE_INCR` 24-bit 定点基数
- 去掉方波 "oversampling" 中间位置计算 (IntermediatePos / FLT_MIN), 改为简单翻转
- 去掉 NeoGeoPocket 双芯片模式 (T6W28 connect)
- 去掉 GameGear 立体声写入 (GGStereoWrite)
- 去掉声像 (panning) / 静音 (mute) 接口
- 保留 3 种变体: SN76489 (TI 15-bit SR) / Sega VDP (16-bit, 默认) / SN76489A (17-bit), 比原版增加了第三种变体
- 音量表: 原版 16 级 (0-4096, MAME 标准), 精简为 16 级 (0-255, 适配 8-bit 输出)

### 8.3 FM 合成 — 参考 ArduinoUnoTinyFmKeyboard (开源)

- **原作者**: Keiji Katahira (ArduinoUnoTinyFmKeyboard, ATmega328P, 20MHz, 24kHz PWM)
- **原始项目**: `D:\working\vscode-projects\Reference_Project\STC-MCU\extracted\ArduinoUnoFMsynsynthesizer-master\ArduinoUnoTinyFmKeyboard\`
- **原版规模**: ~668 行 (`.ino` + `fmtone.cpp` + `fmtone.h`), C++ class 架构
- **原版**: 5 voice (10 op), ATmega328P, 20MHz, 24kHz, AVR Timer1 ISR, 4 种 PWM 引脚可选

**移植改动 (C++ class → C251 纯 C, 5 voice → 16 voice)**:
- C++ → 纯 C: `FmTone` class 拆为全局状态 + 函数 (`fm_wr()` / `fm_render()`)
- 音频: 6 种独立波形表 (`wave_sin[]` 等) → 合并单一数组 `fm_waves[384]`, 位移查表 `(wave_idx << 6) | idx`
- 波形: 6 种 (sin/clipsin/rect/tri/saw/abssin) 完全保留
- 频率表: PROGMEM `tone_freq[80]` (MIDI 36-115) → code 段 `fm_note_freq[104]` (MIDI 24-127, C1-C9)
- voice 数: 5 voice → 16 voice, operator 数 10 → 32
- 包络: `envelope_cnt[16]` 表完全保留, ADSR 逻辑一致
- 反馈: `fb=7 → fb=8` 补正 → 标准 `>> fb` (0-7), 原版做法过于 hacky
- 去掉 MIDI 解析 (Note On/Off/Program Change), 改为寄存器直写模式
- 去掉 poly/mono 模式切换、voice queue、velocity 映射
- 去掉 SysEx 音色编辑 (`sysEx.cpp` / `deftone.h`)
- 去掉硬件初始化 (AVR Timer PWM), 改为 ISR 回调 `fm_render()`
- 新增: 全局音色模板机制 (reg 0x00-0x09), Note On 自动 apply tone

### 8.4 WT 波形表 — 参考 ArduinoUno WaveMemorySyns (开源)

- **原作者**: Keiji Katahira (ArduinoUno_wavetable_synthesis, WaveMemorySyns)
- **原始项目**: `D:\working\vscode-projects\Reference_Project\STC-MCU\extracted\ArduinoUno_wavetable_synthesis-master\WaveMemorySyns\`
- **原版规模**: ~709 行 (`.ino` + `memtone.cpp` + `envtone.cpp` + headers), C++ class 架构
- **原版**: 4 ch, ATmega328P, 20MHz, 运行时可写波形表 (WaveMemoryEditor)

**移植改动 (C++ class → C251 纯 C, 可写 RAM → 固化 code 段)**:
- C++ → 纯 C: `MemTone` class 拆为全局状态 + 函数 (`wt_wr()` / `wt_render()`)
- 波形: 原版运行时可写 RAM 波形表 → 固化 14 种 128-entry 波形到 code 段 (1792 bytes), 不可运行时修改
- 波形数量: 原版 1 张可写表 → 14 种预置波形 (sq12/sq25/pulse50/sq75/sin/clipsin/abssin/halfsin/qsin/altsin/althalfsin/tri/saw/gb_dmg)
- 频率表: PROGMEM → code 段 `wt_note_freq[104]` (MIDI C1-C9)
- 包络: `envtone.cpp` 的 ADSR 独立对象 → 内联 round-robin tick (同 FM 架构)
- 去掉 MIDI 解析、Echo 效果 (`USE_ECHO`)
- 去掉运行时波形编辑 (WaveMemoryEditor / `set_value()`)
- 去掉 SysEx 接口 (`sysex.cpp`)
- 新增: 波形长度切换 (32/64/128), 音色模板机制

### 8.5 Gigatron — 移植自 Denjhang_Music_Player (自有项目)

- **原作者**: Denjhang
- **原始项目**: `D:\working\vscode-projects\YM2163-Midi\Denjhang_Music_Player_v16\src\windows\gigatron\gigatron_emu.c` + `gigatron_emu.h`
- **原版规模**: ~287 行 (`.c`), C, Windows WinMM 音频回调架构
- **原版**: 4ch, 44100Hz, 32-bit float 输出, 浮点 RatioCounter 采样率转换, 可选 4/6/8/12/16-bit 音频深度, DC offset 去除, 自定义波形表 + 原始波形表双表, 示波器

**移植改动 (Windows 音频 → 嵌入式 ISR 回调)**:
- 去掉 RatioCounter 浮点采样率转换 (`RC_SET_RATIO` / `RC_STEP`), 改为固定 8820Hz (每 2 tick 渲染一次)
- 去掉 521 scanline × 59.98Hz Gigatron 帧同步机制
- 去掉双波形表 (customWaveTable + soundTable), 只保留单一 256 字节波形表
- 去掉 bit depth 选择 (4/6/8/12/16-bit), 固定 s16 输出
- 去掉 DC offset 去除 (dc_alpha 滤波)
- 去掉 volume_scale 浮点缩放
- 去掉示波器 (scope) 功能
- 去掉 `GigatronState` 结构体, 改为 `static` 全局变量
- 去掉 `srand(time(NULL))` 随机种子, 改为固定种子 `r = 0x12345678` (确定性, 嵌入式无需每次不同)
- fnumH: 原版 `key *= 4` → 移植版 `step = key * 44 / 101` (适配 17640Hz 采样率)
- 核心算法完全一致: `idx = (osc>>7) & 0xFC ^ wavX`, `val = sound[idx] + wavA`, clamp 0-63
