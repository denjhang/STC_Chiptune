# STC32G144K246 固件

STC32G144K246 是 STC32G12K128 的升级型号（144KB Flash, 12-bit DAC, USB HID/CDC, 100-pin LQFP）。本项目把 12K128 的多音源合成器迁移过来，使用 USB CDC 通信 + 12-bit DAC 音频输出。

## 当前状态 (2026-06-21)

### USB CDC 纯源码 + DAC1 12-bit + PLL 72MHz + 五音源 (NES 完美) ✅

**usb_cdc_test 目录** — 独立可运行的完整固件：

1. **USB CDC 单串口** — 纯源码 USB 栈（无 LIB 依赖），COM24 虚拟串口
2. **PLL 72MHz 超频** — 24M HIRC → HPLL → 72MHz，USB 走独立 IRC48M 不受影响
3. **DAC1 12-bit PGA1 Buffer** — P0.7 输出，音质远超 PWMB 8-bit
4. **AY8910 + SN76489 + SCC(K051649) + NES APU + GB DMG 六音源** — 同 ISR 混音，开机音 C4/E4/G4 和弦 2 秒
5. **VGM 播放** — USB CDC 接收 AY(0xA0)/SN(0x50)/SCC(0xD2)/NES(0xB4)/NES-DMC(0xB6)/GB(0xB3)/Reset(0xF0) 命令，vgm_player.py 通过 COM24 播放
6. **@STCISP# 自动下载** — STC-ISP 软件一键烧录，续命匹配优先避免和 0x50 冲突
7. **环形缓冲** — RX1_Buffer 2048 字节，满时丢弃不越界不死机
8. **PRODUCTDESC** — "STC32G144K Chiptune"
9. **SCC 核心对齐 RPFM** — 全球首创在 STC32G 单片机上唱响 SCC，相位重置/共享波表/双精度 step
10. **NES APU 5 通道完美** — 2x 方波(包络+扫频, 对齐 libvgm Delek 修复) + 三角 + 噪声 + DMC (16KB 采样缓冲覆盖 $C000-$FFFF)
11. **AY8910 envelope 对齐 libvgm** — env_step 从 0x0F 递减 + attack 用 4-bit mask (0x00/0x0F)，修复渐强/渐弱反向导致的漏音
12. **全局采样率 22050Hz** — 四音源 base_incr 全部对齐（曾试 44100 因 DAC 精度限制回退）
13. **Playlist 模式** — 顺序播放整个目录，n/b/q 键切歌，--loop N 循环

### AY8910 Envelope 修复要点

对齐 libvgm ay8910.c 的两个关键点：

1. **env_step 初始值** — 写 reg 13 时总是设 0x0F（不管 attack/decay），attack 位只控制方向
   - 原代码 `attack ? 0 : 0x0F` 导致 attack 模式第一个周期从 0 开始，方向反向
2. **attack 类型** — 4-bit mask（0x00 或 0x0F），不是单 bit
   - `env_volume = env_step ^ attack`，attack=0x0F 时 XOR 翻转 4 位实现渐强
   - 原代码 attack=0/1，`0x0F ^ 1 = 0x0E`（错），渐强渐弱方向都错

漏音根因：envelope 模式（reg8/9/10 bit4=1）的通道，attack 第一周期从静音反向跳到大音量，听起来像"漏了音头"。

### NES APU 完美播放要点

- **5 通道**: 2x 方波（包络+扫频）+ 三角波 + 噪声 + DMC（1-bit delta 调制）
- **DMC 采样缓冲 16KB** — 覆盖 NES CPU memory $C000-$FFFF 完整范围
  - kirby / kkstar 等 VGM 的采样常存 $F000+，4KB buffer 会丢弃
- **方波 freq_limit (Delek 修复)** — sweep 关闭时用 `freq_limit[7]`（不限制）
  - 原实现直接用 `regs[1]&7`，导致 sweep 关闭的方波被 `freq_limit[0]=8` 卡死 → 低音无声
- **Sweep 两个方波都跑** — 对齐 libvgm，不区分 channel
- **PAL/NTSC 双时钟自动适配** — vgm_player 读 header 0x84 下发 0xB5
- **frame_div = 92** — `22050/240 ≈ 91.875`，NES frame counter 保持 240Hz

### DAC1 + PGA1 Buffer 配置

```
DAC1_DIV = 2          // 60MHz / (2*4) = 7.5MHz 刷新
PGA1_CR1 = 0x43       // MSEL=Buffer, OSEL=P0.7, NSEL=P0.5, PSEL=DAC1O
PGA1_CR2 = 0x04       // GSEL=1, OE=1
DAC1_CR  = 0x41       // 使能 + 触发输出
```

- 输出引脚: **P0.7**（不是 P0.0）
- P0.5/P0.7 需高阻（OPA 引脚）
- 每次 ISR 写 `DAC1_DAT` 后必须写 `DAC1_CR = 0x41` 触发
- 静音时持续输出 2048（中点），避免 POP 声
- 硬件建议 P0.7 加 3K + 220pF RC 滤波

### 主时钟: 72MHz PLL

- 代码配置 PLL：24M HIRC → /5 → 4.8M → ×60 → 288M → /2 → 144M → CLKDIV=2 → 72M
- **PLL 切换必须在 usb_init() 之前**，否则冲击 USB 模块
- USB 走独立 IRC48M，与主时钟无关

### 采样率与 incr 计算公式

全局采样率 **22050Hz**（Timer0 ISR + DAC 输出频率）。曾尝试 44100Hz 但音质提升不明显（受限于 12-bit DAC 精度），且 ISR 压力大容易卡音，故回退。

各音源用 24-bit 定点小数累加器（`base_count += base_incr; incr = base_count >> 24`）把芯片时钟归一化到采样率。**修改采样率时必须同步更新 incr 常量**，否则音调会变。

计算公式：

```
base_incr = chip_clock × 2^24 / sample_rate
```

| 音源 | chip_clock | sample_rate | base_incr | 定义位置 |
|------|-----------|-------------|-----------|---------|
| AY8910 | 1789772 Hz (NTSC) | 22050 | 170223307 | `ay8910.h` AY_BASE_INCR (硬编码) |
| NES APU | 1789773 (NTSC) / 1662607 (PAL) | 22050 | 运行时算 | `nes.c` nes_set_clock() 用 NES_RATE |
| GB DMG | 4194304 Hz | 22050 | 3191326266 | `gb.h` GB_BASE_INCR (硬编码, 超 LONG_MAX 但 u32 内) |
| SCC | (vgm_player 下发) | — | — | scc.c 内部 step |
| SN76489 | (vgm_player 下发) | — | — | sn76489.c 内部 |

**修改采样率的完整步骤**（例如 22050 → X）：

1. `main.c`: `SAMPLE_RATE` → X
2. `main.c`: `BOOT_NOTE_TICKS` = X × 2（保持 2 秒开机音）
3. `main.c`: `led_tick >= 22050` → `>= X`（保持 1 秒 LED 翻转）
4. `ay8910.h`: `AY_BASE_INCR` = `1789772 × 2^24 / X`
5. `nes.h`: `NES_RATE` → `X.0`
6. `nes.c`: `nes_frame_div >= 92` → `>= X/240`（NES frame counter 240Hz）
7. Python 验证：`py -3 -c "print(int(1789772 * (1<<24) / X))"`

### usb_cdc_test 文件结构

| 文件 | 作用 |
|------|------|
| `src/main.c` | 入口: sys_init + DAC1 + AY8910/SN76489/SCC + Timer0 17640Hz + USB CDC + @STCISP# |
| `src/ay8910.c/h` | AY8910 音源芯片驱动 + render |
| `src/sn76489.c/h` | SN76489 (SegaVDP 变体) 仿真核心 + render |
| `src/scc.c/h` | SCC (K051649) 仿真核心 (对齐 RPFM, 双精度 step) + render |
| `src/nes.c/h` | NES APU 仿真核心 (4 通道: 2x方波+三角+噪声) + PAL/NTSC 双时钟 |
| `src/gb.c/h` | GameBoy DMG 仿真核心 (对齐 libvgm gb.c, 4 通道: 2x方波+波形+噪声) |
| `src/usb.c` | USB 寄存器操作 + ISR + EP4 OUT 环形缓冲写入 |
| `src/usb_desc.c/h` | USB 描述符（CDC 单串口, VID=34BF PID=FF0A） |
| `src/usb_req_class.c` | CDC 类请求 (LineCoding / SerialState) |
| `src/usb_req_std.c` | 标准请求 |
| `src/usb_req_vendor.c` | Vendor 请求 (STALL) |
| `src/inc/stc.h` | 统一类型定义 + GPIO 模式宏 |
| `src/inc/config.h` | EP 端点配置 (EP2IN + EP4IN + EP4OUT) |
| `src/comm/STC32G.H` | 完整版芯片寄存器定义（含 DAC1/PGA1 far 指针） |
| `src/util.c` | reverse2() 字节序翻转 |
| `tools/vgm_player.py` | VGM 播放脚本，默认 COM24 |

### 编译

```bash
cd STC32G144K246/usb_cdc_test
py -3 build.py
```

输出: `src/build/MAIN.hex`

### 烧录

1. STC-ISP 打开 `src/build/MAIN.hex`，配置主时钟 60MHz
2. 首次手动上电复位烧录
3. 后续通过 STC-ISP "收到用户命令后复位到ISP监控程序区" 自动下载

### 播放 VGM

```bash
cd STC32G144K246/usb_cdc_test
py -3 tools\vgm_player.py --list --vgm-dir ..\..\vgm\ay8910
py -3 tools\vgm_player.py 2 --vgm-dir ..\..\vgm\ay8910
```

## 踩坑记录

### CDC 比 UART 稳定

USB Bulk 有硬件 CRC16 + 自动重传，不会丢字节。UART 丢一个字节会导致后续命令错位（听起来乱音），CDC 要丢就丢整条命令不会错位。

### RX1_Buffer 环形缓冲

原代码 `RX1_Buffer[RX1_Cnt++]` 无边界检查，AY 命令密度高时 ~2 秒填满 2048 字节越界覆盖其他变量导致死机。改为环形缓冲后满时丢弃新字节。

### DAC1 必须用 PGA1 Buffer

DAC1 不能直接输出引脚，必须通过 PGA1 Buffer 放大后输出到 P0.7。直接写 DAC1_CR=0x80 无声，必须 0x41（使能+触发）。

### STC32G.H 完整版冲突

完整版 include 了 stdio.h/string.h/main() 宏，和 C251 编译冲突。需注释掉 stdio.h/string.h 和 main() 宏。

### @STCISP# 和 SN76489 0x50 命令冲突

`@STCISP#` 第 7 字节 `'P'` = 0x50，与 SN76489 VGM 命令前缀 0x50 完全相同。原代码先判 0xA0/0x50 再判 @STCISP#，导致 isp_match 走到 6 之后，`'P'` 被 SN 分支截走，连带吞掉 `'#'`，复位命令永远匹配不完整。

修复：`process_uart()` 改成 `isp_match > 0` 时优先走 @STCISP# 续命分支，只有 `isp_match == 0` 才允许处理 0xA0/0x50 音源命令。

### SCC (K051649) 对齐 RPFM 实现要点

STC8H/STC32G12K 老版 SCC 仿真音高不准，直接参考 RPFM (github RPFM 项目) 重新实现。关键差异：

1. **切频重置相位** — 写 frequency 时 `counter &= 0xFFFF0000u`，避免相位不连续产生咔哒声
2. **test bit 0x20/0x1F** — 实现 test register 的 reset 位 (`counter = 0xFFFFFFFF`)
3. **SCC 共享波表** — 模式下 offset 0x60-0x7F 同时写 ch3+ch4 (硬件共享 bank 3)
4. **wave RAM 用 int8_t** — 直接带符号，去掉运行时 `>=128` 判断
5. **双精度 step 计算** — `((double)1789772 * 131072) / ((freq+1) * 17640)`，等价 RPFM 的 64-bit 整数除法，分子 2^37.77 在 double 52-bit 尾数内完全精确。旧整数宏 `(1789772/17640)*131072` 因整数除法截断丢 0.6% 精度，听感偏低
6. **signed 运算陷阱** — `(s16)wave * (u16)vol` 会被 C 的 usual arithmetic conversions 提升为 unsigned，负半周波形丢失符号变成大正值，累加后 `*8` 严重削顶。必须全用 `s16` 运算

### VGM 协议命令字节

| 前缀 | 芯片 | 格式 |
|------|------|------|
| 0xA0 | AY8910 | `[0xA0][reg][data]` |
| 0x50 | SN76489 | `[0x50][data]` |
| 0xD2 | SCC K051649 | `[0xD2][port][reg][data]` |
| 0xB3 | GB DMG | `[0xB3][reg][data]` |
| 0xB4 | NES APU | `[0xB4][reg][data]` |
| 0xB5 | NES 时钟下发 | `[0xB5][clk0..3]` (LE u32, NTSC=1789773/PAL=1662607) |
| 0xB6 | NES DMC 采样块 | `[0xB6][addr_lo][addr_hi][len≤32][data...]` |
| 0xB7 | AY/YM2149 时钟下发 | `[0xB7][clk0..3]` (LE u32, 已处理 chipFlags /2 分频器) |
| 0xF0 | 全音源 reset | `[0xF0]` (调各 *_init + 清 active) |

### AY8910 / YM2149 时钟与 chipFlags (2026-06-22)

AY_CLK 不再硬编码, 改 `ay_set_clock(u32 hz)` 运行时切换 (对齐 nes_set_clock).
固件 main.c 加自定义 0xB7 命令, py 解析 VGM header 的 AY clock + chipFlags 后下发.

**关键: YM2149 的 chipFlags bit4 (0x10) = PIN26_LOW = 内置 /2 分频器** (ayintf.h:32):
- VGM header 里 chipType @0x78 (0x10=YM2149, 0x00=AY-3-8910)
- chipFlags @0x79, **bit4=0x10** (不是 bit0!) = /2 分频器使能, 实际 clock 减半, 音高低八度
- clock 偏移 v1.50/v1.70 不同: @0x40 (v1.50) / @0x74 (v1.70), 两个都试取非零

坑: 之前误用 bit0 导致 Demodulation (chipFlags=0x01) 被误降八度. 必须查 ayintf.h
的 #define YM2149_PIN26_LOW 0x10, 不能凭名字猜 (PIN26_LOW 听起来像 bit0, 实际 bit4).

实测:
- Gimmick (NES+YM2149): clock=1789773, chipFlags=0x11 (bit4=1) → effective 894886, 降八度 ✓
- Demodulation (ZX Spectrum AY): clock=1773400, chipFlags=0x01 (bit4=0) → 1773400, 原音高 ✓



SCC port 字段语义（RPFM 对齐）:
- port=0x00 写波形 bank (offset 由 reg 决定)
- port=0x01 写频率 bank
- port=0x02 写音量 bank
- port=0x03 写 key register (data bit0-4 = ch0-4 keyon/off)
- port=0x05 写 test register

### SCC 静音命令的正确写法

参考真实 VGM 文件结尾序列（如 `vgm/scc/11 Stage Clear.vgz` 解压后）:

```
d2 03 00 00    ← port=3 key bank, reg=0, data=0: 全 5 通道 keyoff
```

注意 port 和 reg 不能反。错误写法 `[0xD2, 0x00, 0x03, 0x00]` 会把 reg=0x03 解释成波形 bank 的 offset，写波形数据而不是 key register，无法静音。

vgm_player.py finally 块已对齐真实 VGM 序列。

### NES APU 实现要点

参考 libvgm `nes_apu.c` 移植，4 通道混音：

1. **2x 方波 (pulse)** — 每通道 4 寄存器 (duty/env/vol, sweep, freq_lo, len/freq_hi)
   - duty 4 模式 (12.5%/25%/50%/75%) 查表 `nes_duty_lut[4]`
   - 软件包络: 15 级衰减，frame IRQ 触发
   - 频率扫频: 由 reg[1] 的 shift/方向/周期控制
2. **三角波** — 32 步波形查表，linear counter + length counter 双重 gating
3. **噪声** — 15-bit LFSR (mode 1=Sega VDP, mode 0=NES), `nes_noise_freq[16]` 频率表
4. **frame counter** — 每 74 个采样触发一次 do_frame（≈240Hz NTSC）

**PAL/NTSC 双时钟**: VGM header 0x84 存 NES 时钟 (bit31 为逆位标记，低 31 位为实际 Hz)
- NTSC: 1789773 Hz (Naruto/RMMDK/FSTRUCKS)
- PAL: 1662607 Hz 或野档 1652098 Hz (Smurfs)
- 两者比值 ≈ 1.0835，相当于 1.4 个半音

**实现**:
- 固件 `nes_set_clock(u32 hz)` 用 `(double)hz * 2^24 / 17640` 算出 `nes_base_incr`
- vgm_player.py 解析 header 0x84 后，开播前发 `[0xB5][clk0..3]` 下发时钟
- 默认 NTSC 1789773，可被 0xB5 覆盖
- STC32G FPU 的 double 精度足够，PAL/NTSC 切换无缝

**混音系数** (main.c ISR):
```
mix = nes_squ[0].output + nes_squ[1].output
mix += nes_tri.output * 3 / 4
mix += nes_noi.output * 3 / 4
mix *= 4   ← 总放大后和 AY/SN/SCC 量级匹配
```

**NES 静音**: `[0xB4, 0x15, 0x00]` 即 $4015 status = 0，硬件级关闭 4 通道。真实 VGM 不显式静音,只流到结尾结束,但我们用标准 status 寄存器关闭是最干净的做法。

### NES APU trigger / $4015 排查记录 (2026-06-22)

移植 libvgm 时照搬了它的两个 bug, 导致大量 NES 曲目无声:

**Bug A — 全通道无声 (Kirby 16 Crane Fever 等)**:
某些 VGM 文件**完全不写 $4015 status 寄存器**。libvgm 在 `device_reset_nesapu`
(line 901-902) 自动发 `$4015=0x00` 再 `$4015=0x0F` enable sq1/sq2/tri/noise,
我们的 `nes_init` 没做这个默认 enable → 通道全 disabled → 全曲无声.
修复: `nes_init` 末尾默认 enable sq1/sq2/tri/noise (DMC 不默认 enable).

**Bug B — noise 单通道无声 (Kirby 15 Cloud Level 等)**:
trigger 寄存器 ($4003/$4007/$400B/$400F) 写入时, libvgm 和我们都加了
`if (enabled)` 检查 — 但 NES 硬件文档明确: **length counter 加载独立于 $4015 enable**.
某些 VGM (如 Kirby 15) 的 $400F trigger 早于 $4015 enable, trigger 时 enabled=0
→ vbl_length 不设置 → 即使之后 enable 也无 length → 永久静音.
修复: square/triangle/noise trigger 移除 `if(enabled)` 检查, 总是加载 vbl_length.

**诊断方法**: dump VGM 命令流对比正常曲 (14) 和故障曲 (15/16), 发现 16 缺 $4015,
15 的 trigger 早于 $4015. 对照 libvgm `nes_apu.c` 源码找到 `device_reset` 的自动
enable 机制 (line 901-902). **教训: 移植时不能只看 update 函数, init/reset 函数
的隐式行为 (默认值、自动初始化) 同样关键, libvgm 把它藏在 device_reset 里容易漏**.

### NES APU 已知限制

NES APU 已完整支持 5 通道 (含 DMC 16KB 采样缓冲), 无已知限制。

### GB DMG 实现要点 (对齐 libvgm gb.c)

参考 libvgm `emu/cores/gb.c` (Wilbert Pol, Anthony Kruize, BSD-3-Clause) 完整重写。原 `STC32G12K128/gb.c` 未经验证, 弃用。4 通道:

1. **方波 1 (CH1)** — duty + 包络 + 频率扫频 (NR10-14), 唯一带 sweep 的通道
2. **方波 2 (CH2)** — duty + 包络 (NR21-24)
3. **波形 CH3** — 32 个 4-bit 自定义采样, 从 Wave RAM (AUD3W0-0xF) 读 (NR30-34)
4. **噪声 CH4** — 15-bit LFSR, 多项式分频器 + 包络 (NR41-44)

**核心数据**:
- GB 主时钟 4.194304 MHz, 64 cycles/sample 归一化
- Frame sequencer: `clock/8192 = 512 Hz`, 8 步循环 (length/sweep/envelope)
- 频率公式: `Hz = 131072 / (2048 - gb_freq)` (与 AY/NES 不同的换算)
- 方波周期: `(2048 - freq) << 2` cycles, 每周期 8 个 duty 采样

**GB_BASE_INCR 计算**: `4194304 × 2^24 / 22050 = 3191326266` (超 LONG_MAX 但 u32 范围内)

**混音系数** (main.c ISR): `mix += gb_render()` 直接累加, gb_render() 内部已做主音量+均值+钳位。

**VGM 协议**: `[0xB3][reg][data]` 直接透传 GB 寄存器写。reg 字段是 GB IO 偏移 (NR10=0x00, NR52=0x16, AUD3W0=0x20..0x2F)。

**GB 静音**: `[0xB3, 0x16, 0x00]` 即 NR52=0 关闭 APU (DMG 模式下复位所有通道寄存器)。

**混音公式** (对齐 libvgm `gameboy_update`, mono 合并):
- `mono = (left + right) / 2` (左右平均, 避免双使能通道 2x 失真)
- `mono *= (vol_left + vol_right + 1) / 2` (NR50 平均主音量)
- `mono <<= 6` (pump up, 同 libvgm `left <<= 6`)
- ⚠️ 之前误抄成 `>>= 4` (缩小 16 倍) 导致几乎无声, 修正后幅度正常

**ISR 性能优化 (关键! 72MHz STC32G 上 GB 出声的核心)**:
- **问题**: libvgm 原版 `gb_update_wave` 用 `while(cycles_left >= 2)` 逐 GB cycle 推进 freq_counter,
  22050Hz 下每采样 cycles=190 → **95 次循环**; 每次循环体有 `offset/2` 除法 + level 缩放 → ISR 严重超时
  (45μs 预算超 3-4 倍), 饿死 USB CDC 中断 → py `ser.write()` 永久阻塞 (不响应 Ctrl+C)
- **对比 NES**: `nes_update_square` 循环体只有 `phaseacc -= freq; adder++` (无除法/表查找),
  循环次数 = `cycles/freq` ≈ 10 次, 所以 NES 5 通道不卡
- **修复**: wave 改 NES 风格 phaseacc — `cycles_left` 累加到 `period = 2×(0x800-frequency)` 才推进 offset,
  循环次数从 95 降到 ~10 次; 循环体用 `>>1` 代替 `/2`, level 用 if/else 代替变量移位
- **noise**: period 已是 GB cycles (8~32768), 循环最多 ~24 次, guard=32 保底
- **square**: 本来就是公式法 (一次除法, 无循环), 不卡
- **混音**: main.c ISR `mix += gb_render()`, 外层 `mix *= 8` 统一增益 (GB 已做 `<<6`, 削顶由钳位处理)

**移植注意 (C251 C89)**:
- 所有局部变量声明必须在 block 开头 (C251 默认 C89, 不支持 mixed declarations)
- `data` 是 C251 保留字 (内部 RAM 段), 参数名必须用 `val`
- mono 简化: libvgm 拆 left/right 是因为 GB 扬声器双声道, 我们没有, 直接 left+right 累加后用 NR50 平均主音量
- 简化 DMG-only: 不实现 CGB-04 波形 RAM corrupt 和 mute mask
