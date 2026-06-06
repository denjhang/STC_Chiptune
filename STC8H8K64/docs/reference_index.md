# STC8H8K64U 参考代码索引

## 逐飞科技库

路径：`D:\working\vscode-projects\Reference_Project\STC-MCU\STC8H8K64_Library-master\`

### Demo 例程

`Example\`

| 例程 | 路径 | 内容 |
|------|------|------|
| LED Blink | `1-LED Blink Demo` | 基础 GPIO |
| GPIO Input | `2-GPIO Input Demo` | 输入检测 |
| EXTI | `3-EXTI Demo` | 外部中断 |
| Timer 中断 | `4-PIT Timer Interrupt Demo` | 周期定时 |
| ADC | `5-ADC Demo` | ADC 采样 |
| PWM | `6-PWM Demo` | PWM 输出 |
| 外部计数 | `10-External Count Demo` | 定时器计数 |
| EEPROM | `11-EEPROM Demo` | 片内 EEPROM |

---

## 配套例程（核心板）

路径：`D:\working\vscode-projects\STC_Chiptune\example\STC8H8K64U配套例程\`

| 例程 | 路径 | 内容 |
|------|------|------|
| LED | `1.LED-RUN` | 基础 GPIO |
| RGB LED | `2.RGB-LED` | PWM 调色 |
| 按键 | `3.KEY` | GPIO 输入 |
| 数码管 | `4.DIG` | 动态扫描 |
| 蜂鸣器 | `5.BUZZ` | GPIO bitbang 蜂鸣 |
| 串口收发 | `12.串口收发` | UART1 9600bps，`interrupt 4 using 1` |
| 红外遥控 | `11.红外遥控` | 外部中断 |
| 2.4G 通信 | `15.2.4G模块\程序` | NRF24L01 SPI |

---

## 官方 Demo（STC）

路径：`D:\working\vscode-projects\Reference_Project\STC-MCU\STC32G-DEMO-CODE-master\`
> 官方 demo 文件夹名虽为 STC32G，但 `D:\BaiduNetdiskDownload\STC8H8K64核心板资料` 下有 STC8H 对应版本。

STC8H 的官方 demo 也可参考之前项目中的：
`STC8H8K64/docs/FwLib_STC8-master/demo/`

| 例程 | 内容 |
|------|------|
| `pwm/pwm_dac_voice` | PWM DAC 语音播放（音频相关） |
| `pwm/pwm_2ch_complementary` | 双通道互补 PWM |
| `uart/uart1_timer1_tx` | UART1 Timer1 发送 |
| `uart/uart1_timer2_rx` | UART1 Timer2 接收 |
| `tim/timer0_timer_1t` | Timer0 1T 模式 |

---

## 关键配置备注

### UART1 串口（9600bps @11.0592MHz）

```c
SCON = 0x50;       // 8 位 UART
AUXR |= 0x40;      // Timer1 1T 模式
AUXR &= ~0x01;     // 串口1 用 Timer1
TMOD &= 0x0F;      // Timer1 模式
TL1 = 0xE0; TH1 = 0xFE;  // 9600 reload
ET1 = 0; TR1 = 1;
ES = 1; EA = 1;
```

### PWM DAC 音频（已验证）

- PWMA PWM1P **P2.0**
- `P_SW2 |= 0x80` 开 XFR 访问
- period=256（8-bit duty 分辨率），prescaler=0（43.2kHz 载波）
- `PWMA_PS |= 0x01` 选 P2.0 端口
- 波形表：32 点 sine/saw/tri/sq duty 值

### 已知问题

1. **P_SW2 与 Timer ISR 冲突** — 保持 `P_SW2 |= 0x80` 时 Timer ISR 不触发
2. **UART echo 乱码** — 最小 echo 测试有数据返回但乱码，PWM 集成未验证
3. **IRAM 仅 256B** — 必须 `build_src_filter = +<main.c>`
