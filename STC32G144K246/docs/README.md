# STC32G144K246 固件

STC32G144K246 是 STC32G12K128 的升级型号（144KB Flash, 12-bit DAC, USB HID/CDC, 100-pin LQFP）。本项目把 12K128 的多音源合成器迁移过来，使用 USB CDC 通信 + 12-bit DAC 音频输出。

## 当前状态 (2026-06-21)

### USB CDC 纯源码 + DAC1 12-bit 音频输出 (里程碑) ✅

**usb_cdc_test 目录** — 独立可运行的完整固件：

1. **USB CDC 单串口** — 纯源码 USB 栈（无 LIB 依赖），COM24 虚拟串口
2. **DAC1 12-bit PGA1 Buffer** — P0.7 输出，音质远超 PWMB 8-bit
3. **AY8910 开机音** — C4/E4/G4 和弦 2 秒
4. **VGM 播放** — USB CDC 接收 AY 命令，vgm_player.py 通过 COM24 播放
5. **@STCISP# 自动下载** — STC-ISP 软件一键烧录，无需拔线
6. **环形缓冲** — RX1_Buffer 2048 字节，满时丢弃不越界不死机
7. **PRODUCTDESC** — "STC32G144K Chiptune"

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

### 主时钟: 60MHz (ISP 配置)

- 通过 STC-ISP 工具设置，代码不改主时钟
- USB 走独立 IRC48M，与主时钟无关

### usb_cdc_test 文件结构

| 文件 | 作用 |
|------|------|
| `src/main.c` | 入口: sys_init + DAC1 + AY8910 + Timer0 17640Hz + USB CDC + @STCISP# |
| `src/ay8910.c/h` | AY8910 音源芯片驱动 + render |
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
