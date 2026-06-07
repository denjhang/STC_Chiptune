# STC Chiptune - 项目进度

## 项目目标

基于 STC8H8K64U（DIP-40, 1T 8051）开发复古芯片合成器，通过 TTL 串口接收寄存器数据 → SCC 音频仿真 → PWM 音频输出。

> **通信方案：TTL 串口（UART）**。STC8H 没有出厂 USB CDC bootloader，自己写 USB bootloader 太复杂，放弃 USB CDC，回归最经典的 TTL 串口方案。通过 USB-TTL 模块（CH340/CP2102/FT232）连接 PC。

---

## 进度

### ✅ 已完成

| 阶段 | 内容 | 日期 |
|------|------|------|
| 硬件选型 | STC8H8K64U DIP-40，2 元 | 2025-06 |
| 开发环境 | PlatformIO + SDCC + FwLib_STC8 | 2025-06 |
| LED 心跳 | P3.4 GPIO 翻转，main loop 延时 | 2025-06 |
| ISP 烧录 | STC-ISP 手动烧录验证通过 | 2025-06 |
| stc8prog | 编译部署到 PlatformIO，芯片可检测但波特率切换失败 | 2025-06 |
| SCC 移植 | 从 YM2163-Midi 移植，预计算 step 优化，编译通过 | 2025-06 |
| IRAM 溢出 | `build_src_filter = +<main.c>` 解决 FwLib 占 IRAM 问题 | 2025-06 |
| PWM 音频 | PWMA PWM1 P2.0 方波音乐输出验证通过 | 2025-06 |
| Sine 波形 | PWM DAC 模式验证：172.8kHz 载波 + 32 点 sine 表 duty 调制 | 2025-06 |
| **Keil C51 切换** | SDCC 不兼容官方 STC8H.H（sfr/sbit 语法），切换到 Keil C51 | 2026-06-07 |
| **UART 修复** | Keil C51 + 官方 stc8h.h，115200 baud @22MHz echo 验证通过 | 2026-06-07 |
| **开发板适配** | LED 流水灯(P0)、RGB 变色(P3.5/6/7)、蜂鸣器(P1.6)、数码管(P4+P2) | 2026-06-07 |

### 🔲 待完成

| 阶段 | 内容 | 状态 |
|------|------|------|
| 蜂鸣器频率修复 | GPIO bitbang 嵌入 digit_scan 后频率偏高（超声波） | 待修复 |
| 数码管频率更新 | cur_freq 随音符变化但显示未同步刷新 | 待修复 |
| Timer 切音符 | Timer0/Timer3 ISR 在 P_SW2 开启时不触发，需排查 | 待修复 |
| SCC 集成 | SCC 仿真器 + UART + PWM 音频输出完整集成 | 待开发 |

---

## 工具链变更

### 之前：SDCC + PlatformIO

```
pio run → SDCC 编译 → firmware.hex
```

问题：SDCC 不支持 Keil 的 `sfr`/`sbit` 语法，官方 STC8H.H 无法使用。

### 现在：Keil C51（CLI）

```
go.bat → C51.exe 编译 → BL51.exe 链接 → OH51.exe 生成 hex
```

| 工具 | 路径 |
|------|------|
| 编译器 | `D:\Keil_v5\C51\BIN\C51.exe` |
| 链接器 | `D:\Keil_v5\C51\BIN\BL51.exe` |
| HEX 生成 | `D:\Keil_v5\C51\BIN\OH51.exe` |
| 串口测试 | Python pyserial（`import serial`） |

**编译命令**：`cd STC8H8K64 && go.bat`（Windows cmd）

**注意**：
- C51 输出的 .OBJ 在源文件同目录（`src/main.OBJ`），不是 build 目录
- `OPTIMIZE(8,SPEED)` 会优化空循环，需用 `volatile` 防止
- `using 1` 寄存器组切换在某些场景下有兼容性问题，官方 demo 不用

---

## 芯片配置

| 参数 | 值 |
|------|-----|
| 芯片 | STC8H8K64U |
| 内部 IRC | 22.1184MHz（用户设定，STC-ISP 自动校准） |
| UART 波特率 | 115200（Timer1 1T） |
| 编译器 | Keil C51 V9.52 |
| 头文件 | 官方 `stc8h.h` |

---

## 已知问题

1. **蜂鸣器频率偏高** — GPIO bitbang 循环内嵌入 digit_scan() 导致实际方波频率远超预期
2. **Timer ISR 在 P_SW2 开启时不工作** — `P_SW2 |= 0x80` 保持开启时 Timer0/Timer3 ISR 均不触发
3. **stc8prog 波特率切换失败** — 芯片在 2400bps 可检测，切换到 115200bps 失败

---

## 参考资源

- [FwLib_STC8](https://github.com/IOsetting/FwLib_STC8) — STC8H HAL 库（IOsetting）
- [STC8H8K64U 核心板资料](D:\BaiduNetdiskDownload\STC8H8K64核心板资料) — 官方 demo 代码 V9.6
- [YM2163-Midi](D:\working\vscode-projects\YM2163-Midi) — SCC 仿真器源码
