# STC32G12K128 参考代码索引

## 逐飞科技库

路径：`D:\working\vscode-projects\Reference_Project\STC-MCU\STC32G12K128_Library-master\`

### 驱动源码

`Seekfree_STC32G12K128_Opensource_Library\Libraries\zf_driver\`

| 文件 | 功能 |
|------|------|
| `zf_driver_uart.c` | UART1~4 驱动，中断回调方式 |
| `zf_driver_pwm.c` | PWMA/PWMB 高级 PWM，XFR 宏操作 |
| `zf_driver_timer.c` | Timer0~4，周期中断封装 |
| `zf_driver_gpio.c` | GPIO 初始化 |
| `zf_driver_clock.c` | 系统时钟配置（支持 24/30/36/40MHz） |

### Demo 例程

`Example\Coreboard_Demo\`

| 例程 | 路径 | 内容 |
|------|------|------|
| E03 UART | `E03_uart_demo\user\main.c` | 串口收发 115200，fifo + 中断回调 |
| E05 PWM | `E05_pwm_demo\user\main.c` | PWM 呼吸灯，`pwm_init/pwm_set_duty` |
| E06 PIT | `E06_pit_demo\user\main.c` | Timer 周期中断，回调方式 |

---

## 官方 Demo（STC）

路径：`D:\working\vscode-projects\Reference_Project\STC-MCU\STC32G-DEMO-CODE-master\`

| 例程 | 路径 | 内容 |
|------|------|------|
| 串口1 中断 | `10-串口1中断模式与电脑收发测试` | UART1 ISR 收发 |
| 串口2/3/4 | `11~13-串口2~4中断模式` | 多串口配置 |
| 高级 PWM | `25-高级PWM1-PWM2-PWM3-PWM4` | PWMA 呼吸灯 |
| 高速 HSPWM | `68-高速HSPWM1~HSPWM4` | 高速 PWM 呼吸灯 |
| 互补 SPWM | `44-高级PWM输出两路互补SPWM` | SPWM 音频相关 |
| PWM 脉冲计数 | `80-高级PWM输出-周期可调-脉冲计数` | PWM 高级用法 |
| PWMA/PWMB 定时 | `87.1~87.2-利用高级PWMA+PWMB溢出中断做定时器` | PWM 溢出中断做定时 |
| USB CDC | `70-CDC协议范例` | USB 虚拟串口 |
| USB HID | `76-USB HID协议打印数据信息-可用于调试` | USB HID 调试输出 |
| UART 转 SPI | `77-USART1复用SPI` | USART1 复用 SPI 模式 |

---

## 关键配置差异（vs STC8H）

| 项目 | STC32G12K128 | STC8H8K64U |
|------|-------------|-----------|
| 波特率发生器 | **Timer2**（`AUXR \|= 0x15`） | Timer1（`AUXR \|= 0x40`） |
| 中断方式 | 函数指针回调 | 传统 `interrupt N` ISR |
| PWM 操作 | XFR 宏 `PWMX_XXX(pin)` | 直接写寄存器或 FwLib |
| XFR 访问 | `EAXFR=1` 必须 | `P_SW2 \|= 0x80` |
| 默认主频 | 24/30/36/40MHz 可选 | 11.0592MHz 固定 |
