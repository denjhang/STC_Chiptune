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

### 🔲 待完成

| 阶段 | 内容 | 状态 |
|------|------|------|
| Timer 切音符 | Timer0/Timer3 ISR 在 P_SW2 开启时不触发，需排查 | 待修复 |
| ISR 波形驱动 | Timer ISR 驱动 PWM duty 更新失败（同上 P_SW2 问题） | 待修复 |
| UART 驱动 | TTL 串口接收 SCC 寄存器数据（USB-TTL 模块） | 待开发 |
| SCC 集成 | SCC 仿真器 + UART + PWM 音频输出完整集成 | 待开发 |
| WAV 播放 | 参考 demo 80 用 PWMB/PWMA 播放 WAV 采样 | 可选 |

---

## 已知问题

1. **Timer ISR 在 P_SW2 开启时不工作** — `P_SW2 |= 0x80` 保持开启时 Timer0/Timer3 ISR 均不触发或异常，原因待查。PWM 寄存器必须用 XFR 访问，但 Timer 不需要。临时方案：ISR 前关 P_SW2，进 ISR 后再开（未验证）。当前用 main loop 延时作为 workaround。
2. **stc8prog 波特率切换失败** — 芯片在 2400bps 可检测，切换到 115200bps 失败（Windows COM 口时序问题）。
3. **P5.4 PWM2N 互补通道无输出** — 同样配置方式在 P2.0 PWM1P 正常，P5.4 无声音，原因未明。
4. **FwLib IRAM 占用** — FwLib 编译进项目会占用大量 IRAM（仅 256B），必须用 `build_src_filter = +<main.c>` 限制只编译 main.c。后续集成 SCC/UART 时需要解决。

---

## 参考资源

- [FwLib_STC8](https://github.com/IOsetting/FwLib_STC8) — STC8H HAL 库（IOsetting）
- [STC8H8K64U 核心板资料](D:\BaiduNetdiskDownload\STC8H8K64核心板资料) — 官方 demo 代码 V9.6
- [YM2163-Midi](D:\working\vscode-projects\YM2163-Midi) — SCC 仿真器源码
