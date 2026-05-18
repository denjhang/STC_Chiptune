# 项目概述

基于 STC8H8K64U 开发复古芯片仿真器，通过串口调试和下发寄存器数据，单片机 PWM 输出音频。

---

# 硬件选型：STC8H8K64U

## 选择理由

- 原生 DIP-40 封装，直接插面包板使用
- 8K XRAM + 256 IRAM，64K Flash
- 1T 8051 架构
- **硬件乘法/除法器**，运算能力秒杀同级别所有 8051 芯片
- PlatformIO `intel_mcs51` 平台已内置支持（board = STC8H8K64U）
- 价格约 2 元，性价比极高（对比 ATmega1284P 约 40 元）

## PlatformIO 配置

```ini
[env:stc8h8k64u]
platform = intel_mcs51
board = STC8H8K64U
```

## 技术参数

| 参数 | 值 |
|------|-----|
| 架构 | 1T 8051 |
| 封装 | DIP-40（原生） |
| Flash | 64K |
| XRAM | 8K |
| IRAM | 256B |
| 默认晶振 | 11.0592 MHz |
| 上传协议 | stcgal（stc8 模式） |

## 备选方案（已排除）

| 方案 | 排除原因 |
|------|---------|
| ATmega1284P | DIP-40 性能最强但价格约 40 元，性价比低 |
| STC12C5A60S2 | DIP-40 但只有 1280B RAM，太小 |
| STC32G | 32 位 ARM Cortex-M0+，但 PlatformIO 不支持 |
