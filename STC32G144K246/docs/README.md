# STC32G144K246 固件

STC32G144K246 是 STC32G12K128 的升级型号（144KB Flash, 12-bit DAC, USB HID/CDC, 100-pin LQFP）。本项目把 12K128 的多音源合成器迁移过来，使用 USB CDC 通信 + 12-bit DAC 音频输出。

## 当前状态 (2026-06-21)

### USB CDC 纯源码 + DAC1 12-bit + PLL 72MHz + 三音源 (里程碑) ✅

**usb_cdc_test 目录** — 独立可运行的完整固件：

1. **USB CDC 单串口** — 纯源码 USB 栈（无 LIB 依赖），COM24 虚拟串口
2. **PLL 72MHz 超频** — 24M HIRC → HPLL → 72MHz，USB 走独立 IRC48M 不受影响
3. **DAC1 12-bit PGA1 Buffer** — P0.7 输出，音质远超 PWMB 8-bit
4. **AY8910 + SN76489 + SCC(K051649) 三音源** — 同 ISR 混音，开机音 C4/E4/G4 和弦 2 秒
5. **VGM 播放** — USB CDC 接收 AY(0xA0)/SN(0x50)/SCC(0xD2) 命令，vgm_player.py 通过 COM24 播放
6. **@STCISP# 自动下载** — STC-ISP 软件一键烧录，续命匹配优先避免和 0x50 冲突
7. **环形缓冲** — RX1_Buffer 2048 字节，满时丢弃不越界不死机
8. **PRODUCTDESC** — "STC32G144K Chiptune"
9. **SCC 核心对齐 RPFM** — 全球首创在 STC32G 单片机上唱响 SCC，相位重置/共享波表/双精度 step

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

### usb_cdc_test 文件结构

| 文件 | 作用 |
|------|------|
| `src/main.c` | 入口: sys_init + DAC1 + AY8910/SN76489/SCC + Timer0 17640Hz + USB CDC + @STCISP# |
| `src/ay8910.c/h` | AY8910 音源芯片驱动 + render |
| `src/sn76489.c/h` | SN76489 (SegaVDP 变体) 仿真核心 + render |
| `src/scc.c/h` | SCC (K051649) 仿真核心 (对齐 RPFM, 双精度 step) + render |
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
