# STC32G144K246 固件

STC32G144K246 是 STC32G12K128 的升级型号（144KB Flash, 12-bit DAC, USB HID/CDC, 100-pin LQFP）。本项目目标是把 STC32G12K128 的 14 乐器多音源合成器迁移过来，并加上 USB 通信能力。

## 当前状态 (2026-06-17)

### USB HID 永久下载模式 ✅

- **VID=0x34BF PID=0xFF01** (STC-ISP 自动下载默认 PID), product string `"STC USB HID"`, usage_page=0x0C (Consumer Control)
- 单 HID 接口, **EP1 IN + EP1 OUT, 64 字节**
- 回环测试 4 个用例全部 PASS（0..63 / 0xAA / 0x55 / 0xFF）
- **纯源码 USB 栈**, 无 LIB 依赖
- **`@STCISP#` 自动复位**: STC-ISP 工具一键触发, 无需拔线/按键

### DAC1 + Timer0 音频输出 ✅

- **DAC1 P0.7** 12-bit, PGA1 Buffer 模式 (PGA1_CR1=0x43, PGA1_CR2=0x04, DAC1_CR=0x41)
- **Timer0 1000Hz 中断** (1T 模式, MAIN_Fosc=64MHz ISP 配置) 翻转 DAC → 500Hz 方波试听
- DAC1_DIV=2 → 24M/(2*4) = 3MHz 刷新率

### 主时钟

- **64MHz HIRC** 通过 STC-ISP 烧录时配置 (IRCBAND/IRTRIM), **代码不动**
- USB 走独立 IRC48M (48MHz 内部 RC), 跟主时钟无关
- ⚠️ **不能代码切 HPLL 超频**: HPLL 切换瞬间会冲击 USB 模块, 导致设备管理器"代码 10 启动失败"

### 移植来源

`stc_hid-master` (https://gitee.com/) — STC32G 三合一 HID 键盘+鼠标+自定义通信。砍掉键盘/鼠标业务, 只保留自定义通信接口。

## 关键文件

| 文件 | 作用 |
|------|------|
| `main.c` | 入口: IRC48M + USB + DAC1 + Timer0 + 流水灯 + HID 回环 |
| `usb.c/h` | USB 寄存器抽象 + ISR + EP0 setup 状态机 |
| `usb_req_std.c/h` | 标准请求 (GET_DESCRIPTOR / SET_CONFIGURATION 等) |
| `usb_req_class.c/h` | HID 类请求 (GET_REPORT / SET_IDLE 等) + EP1 OUT 缓冲 + `@STCISP#` 扫描 |
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
C251.exe util.c "LARGE" "OPTIMIZE(8,SPEED)"
C251.exe usb.c "LARGE" "OPTIMIZE(8,SPEED)"
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

预期: 0 错误 2 警告 (L57: `usb_bulk_intr_in` 和 `key_reset_scan` 未调用, 无害)

## 烧录 (首次)

用 STC-ISP 工具, 通过串口烧录 `build/MAIN.hex`:
- 配置主时钟 IRCBAND/IRTRIM = **64MHz HIRC**
- 烧录后 USB 插上电脑, 设备管理器显示 VID=34BF PID=FF01

## 后续烧录 (HID 一键下载)

烧完用户代码后, MCU 就成了"永久 HID 下载器":

1. 打开 STC-ISP → 左侧 "收到用户命令后复位到ISP监控程序区"
2. 勾选 "下次使用HID接口进行ISP下载"
3. 加载新的 `build/MAIN.hex`
4. 点 "发送指令触发MCU复位并自动下载"
5. MCU 收到 `@STCISP#` → 复位进 ISP 监控区 → STC-ISP 自动识别 PID → 自动烧录 → 自动运行用户代码

**不用拔 USB, 不用短接 P3.2**。

## HID 回环测试

```bash
pip install hid            # cython-hidapi 0.15.0
python ../tools/hid_loopback_test.py
```

4 个用例: `0..63` / `0xAA` / `0x55` / `0xFF`, 全部 PASS。

## `@STCISP#` 自动复位实现

**关键: 扫描器必须放在 EP1 OUT 中断路径, 不是 EP0 SET_REPORT**

STC-ISP 工具发的 `@STCISP#` 走 HID Output Report → EP1 OUT 中断端点 (实测确认, 通过双探针诊断)。早期误以为走 EP0 SET_REPORT, 写了 `usb_class_ep0_out_done()` 钩子, 实际不触发。

正确实现 ([usb_req_class.c](../usb_req_class.c)):

```c
void usb_class_out_ep1()
{
    BYTE cnt;
    BYTE i;

    cnt = usb_bulk_intr_out(HidEp1OutBuffer, 1);
    if (cnt >= 8)
    {
        for (i = 0; i < 8; i++)
        {
            if (HidEp1OutBuffer[i] != (BYTE)stcisp_cmd[i]) break;
        }
        if (i == 8)
        {
            USBCON = 0x00;
            USBCLK = 0x00;
            IRC48MCR = 0x00;
            IAP_CONTR = 0x60;  /* 软件复位到 ISP 监控区 */
            while (1);
        }
    }
    if (cnt > 0)
    {
        HidEp1OutReady = 1;
    }
}
```

## P3.2 长按复位 (双保险, 默认禁用)

代码保留 `key_reset_scan()` (Timer0 1ms 调用), 但**主循环默认不调用**——因为 P3.2 准双向口浮空会被误判为按键按下, 导致上电 0.5 秒后自动进 ISP。

启用方法:
1. 硬件上 P3.2 接按键到 GND (+ 外部上拉)
2. `main.c` Timer0 ISR 里取消 `key_reset_scan()` 调用注释

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

- **OUT (主机 → MCU)**: USB ISR `usb_out_ep1()` → `usb_class_out_ep1()` → 把 FIFO1 数据搬到 `HidEp1OutBuffer[64]` + `HidEp1OutReady = 1` (同时扫描 `@STCISP#`)
- **IN (MCU → 主机)**: 主循环查询 `Usb1InBusy == 0` → `hid_send_ep1()` 直接写 FIFO1 + INIPRDY

### 7. USB 不能超频

HPLL 切换瞬间冲击 USB 模块内部状态机, 导致设备管理器"该设备无法启动 (代码 10)"。**用 STC-ISP 烧录时配置 64MHz HIRC 即可, 代码不动主时钟**。USB 走独立 IRC48M, 跟主时钟无关。

### 8. P3.2 浮空误触发

P3.2 准双向口浮空时, 弱上拉拉不动容性负载, 会被反复读到 0, `key_cnt` 累积达到阈值触发 `IAP_CONTR=0x60`, 表现为**上电 0.5 秒后自动进 ISP**。所以 `key_reset_scan()` 默认禁用, 等硬件接好按键再启用。

## 下一步

- [ ] 14 乐器合成器（从 STC32G12K128 移植）
- [ ] DAC1 改 8kHz/16kHz 采样率播放真实音频
- [ ] P3.2 接按键, 启用物理复位
