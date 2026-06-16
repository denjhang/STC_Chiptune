# STC32G144K246 固件

STC32G144K246 是 STC32G12K128 的升级型号（144KB Flash, 12-bit DAC, USB HID/CDC, 100-pin LQFP）。本项目目标是把 STC32G12K128 的 14 乐器多音源合成器迁移过来，并加上 USB 通信能力。

## 当前状态 (2026-06-17)

### USB HID 已稳定 (单接口)

- ** VID=0x34BF PID=0xFF0A**, product string `"STC USB HID"`, usage_page=0x0C (Consumer Control)
- 单 HID 接口, **EP1 IN + EP1 OUT, 64 字节**
- 回环测试 4 个用例全部 PASS（0..63 / 0xAA / 0x55 / 0xFF）
- **纯源码 USB 栈**, 无 LIB 依赖

### 移植来源

`stc_hid-master` (https://gitee.com/) — STC32G 三合一 HID 键盘+鼠标+自定义通信。砍掉键盘/鼠标业务, 只保留自定义通信接口。

## 关键文件

| 文件 | 作用 |
|------|------|
| `main.c` | 入口: IRC48M + USB + 流水灯 + HID 回环 |
| `usb.c/h` | USB 寄存器抽象 + ISR + EP0 setup 状态机 |
| `usb_req_std.c/h` | 标准请求 (GET_DESCRIPTOR / SET_CONFIGURATION 等) |
| `usb_req_class.c/h` | HID 类请求 (GET_REPORT / SET_IDLE 等) + EP1 OUT 缓冲 |
| `usb_req_vendor.c/h` | Vendor 请求 stub (返回 STALL) |
| `usb_desc.c/h` | 描述符: DEVICE / CONFIG / HID Report / 字符串 |
| `util.c/h` | `reverse2()` 字节序翻转 |
| `stc.h` | 统一类型头 (bit BOOL / BYTE / WORD / DWORD) |
| `config.h` | EP 配置宏 (`EN_EP1IN` / `EN_EP1OUT` / `EP1IN_SIZE=64`) |
| `STC32G.H` | 芯片寄存器定义 (来自 STC 官方) |

## 编译

```bash
cd STC32G144K246

# 1. 编译每个 .c
C251.exe usb.c "LARGE" "OPTIMIZE(8,SPEED)"
C251.exe util.c "LARGE" "OPTIMIZE(8,SPEED)"
C251.exe usb_req_std.c "LARGE" "OPTIMIZE(8,SPEED)"
C251.exe usb_req_class.c "LARGE" "OPTIMIZE(8,SPEED)"
C251.exe usb_req_vendor.c "LARGE" "OPTIMIZE(8,SPEED)"
C251.exe usb_desc.c "LARGE" "OPTIMIZE(8,SPEED)"
C251.exe main.c "LARGE" "OPTIMIZE(8,SPEED)"

# 2. 链接 (用响应文件, 因 CLASSES 带括号 bash 处理不了)
echo 'util.OBJ,usb.OBJ,usb_req_std.OBJ,usb_req_class.OBJ,usb_req_vendor.OBJ,usb_desc.OBJ,main.OBJ TO build/MAIN PRINT(build/MAIN.map) CASE CLASSES(HCONST(0x0-0xFFFFF),EDATA(0x0-0x3FFF),HDATA(0x0-0x3FFF))' > link.args
L251.exe @link.args

# 3. 生成 hex
OH251.exe build/MAIN "HEXFILE(build/MAIN.hex)"
```

预期: 0 错误 1 警告 (L57: usb_bulk_intr_in 未调用, 无害)

## 烧录

用 STC-ISP 工具烧录 `build/MAIN.hex` 到 STC32G144K246。**注意**：烧录时 USB 不能连接电脑（共用 P3.0/P3.1 引脚），需要通过 STC-ISP 的串口下载。

## HID 测试

```bash
pip install hid            # cython-hidapi 0.15.0
python ../tools/hid_loopback_test.py
```

## 踩坑记录

### 1. `delay_ms` 必须 `while (--i)`, 不能 `while (i)`

后者 `i` 没人改，永远为真 → 死循环，整 main 卡住，连流水灯都不走。

### 2. 头文件依赖关系

- `usb.c` 必须 `#include "util.h"`，否则 `reverse2` 调用点签名不一致 → 链接报 `UNRESOLVED EXTERNAL SYMBOL`
- `usb_req_std.c` 必须 `#include "usb_desc.h"` 和 `#include "usb_req_class.h"`，否则 `DESC_HIDREPORT` / `HIDREPORTDESC` / `PACKET0/1` 未定义

### 3. 中断号用符号 `USB_VECTOR` 不用数字 25

STC32G.H 已定义 `USB_VECTOR = 25`，直接写符号可读性强，且对其他 STC32G 芯片兼容。

### 4. USB 初始化序列 (main.c)

```c
IRC48MCR = 0x80;            // 启用内部 48MHz IRC, 专给 USB
while (!(IRC48MCR & 0x01)); // 等稳定
USBCLK = 0x00;              // USB 时钟不分频
USBCON = 0x90;              // ENUSB=1, DP/DM 使能
usb_init();                 // 写 POWER/INTR 寄存器, EUSB=1
EA = 1;                     // 开总中断
```

### 5. 为什么放弃官方 HID LIB

`stc_usb_hid_32g_xdata.LIB` 反复枚举不稳（插上 USB 后设备管理器每秒弹出/消失）。LIB 是黑盒无法调试。开源移植版所有 USB 寄存器操作、状态机分支都在源码里，错了能改，反而稳定。

### 6. EP1 数据流

- **OUT (主机 → MCU)**: USB ISR `usb_out_ep1()` → `usb_class_out_ep1()` → 把 FIFO1 数据搬到 `HidEp1OutBuffer[64]` + `HidEp1OutReady = 1`
- **IN (MCU → 主机)**: 主循环查询 `Usb1InBusy == 0` → `hid_send_ep1()` 直接写 FIFO1 + INIPRDY

## 下一步

- [ ] HPLL 120MHz 主时钟超频（已验证，参考 `main_cdc.c`）
- [ ] DAC1 P0.7 12-bit DAC + Timer0 ISR 音频输出
- [ ] 14 乐器合成器（从 STC32G12K128 移植）
- [ ] 自动 ISP 下载命令（`@STCISP#`）
