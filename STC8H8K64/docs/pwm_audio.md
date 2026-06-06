# PWMA 音频输出技术文档

## 硬件配置

- 芯片：STC8H8K64U（DIP-40，11.0592MHz IRC）
- 输出引脚：**P2.0**（PWMA PWM1P 主通道）
- 音频负载：蜂鸣器/小喇叭（串联 ~100Ω 电阻）

---

## PWMA 关键要点

### 1. XFR 访问必须开启

PWMA 所有寄存器都在扩展 SFR 空间（XFR），访问前必须设置：

```c
P_SW2 |= 0x80;  // 开启 XFR 访问
// ... 操作 PWMA 寄存器 ...
P_SW2 &= ~0x80; // 可选：关闭 XFR
```

FwLib 的宏内部自带 `SFRX_ON()/SFRX_OFF()`，但如果直接操作寄存器（如官方 demo 风格），必须手动开启。

**注意：** 保持 `P_SW2 |= 0x80` 不关闭时，Timer3 ISR 可能不触发（原因未明）。

### 2. PWMA 时钟源

PWMA 直接使用 SYSCLK（1T 模式），**不是 12T**。这是和 Timer（默认 12T）的关键区别。

```
Fpwm = SYSCLK / (PSCR + 1) / (ARR + 1)      // 边沿对齐
Fpwm = SYSCLK / (PSCR + 1) / ARR / 2        // 中心对齐
```

### 3. 频率计算示例

SYSCLK = 11,059,200 Hz，prescaler = 23（÷24）：

| 音符 | 频率(Hz) | ARR 值 | 实际频率 |
|------|----------|--------|----------|
| C4   | 262      | 1759   | 262 Hz   |
| D4   | 294      | 1567   | 294 Hz   |
| E4   | 330      | 1396   | 330 Hz   |
| G4   | 392      | 1176   | 392 Hz   |
| A4   | 440      | 1047   | 440 Hz   |
| B4   | 494      | 933    | 494 Hz   |

ARR 范围 933~1759，全部在 16-bit 内。

### 4. 初始化顺序（参照官方 demo）

```c
P_SW2 |= 0x80;

// 1. 先关闭所有输出
PWMA_ENO  = 0x00;
PWMA_CCER1 = 0x00;
PWMA_CCER2 = 0x00;

// 2. 设置通道模式：PWM 模式 1 + 预装载使能
PWMA_CCMR1 = 0x68;  // OC1M=110 (PWM mode 1), OC1PE=1

// 3. 使能输出通道和极性
PWMA_CCER1 = 0x05;  // CC1E=1, CC1P=0, CC1NE=1, CC1NP=0

// 4. 设置周期和占空比
PWMA_ARRH = (uint8_t)(period >> 8);
PWMA_ARRL = (uint8_t)(period);
PWMA_CCR1H = (uint8_t)((period / 2) >> 8);
PWMA_CCR1L = (uint8_t)(period / 2);

// 5. 设置预分频
PWMA_PSCRH = 0;
PWMA_PSCRL = 23;  // ÷24

// 6. 端口选择
PWMA_PS = (PWMA_PS & ~0x03) | 0x01;  // PWM1_2 → P2.0/P2.1

// 7. 使能输出引脚
PWMA_ENO = 0x01;  // ENO1P

// 8. 启动
PWMA_BKR = 0x80;  // 主输出使能
PWMA_CR1 = 0x01;  // 计数器使能，边沿对齐
```

### 5. 动态修改频率

直接写 ARR 和 CCR1 寄存器即可改变输出频率：

```c
void set_note(uint16_t per) {
    PWMA_ARRH  = (uint8_t)(per >> 8);
    PWMA_ARRL  = (uint8_t)(per);
    PWMA_CCR1H = (uint8_t)((per / 2) >> 8);
    PWMA_CCR1L = (uint8_t)(per / 2);
}
```

如果开启了 `OC1PE`（预装载），修改在下一个周期生效，无毛刺。

---

## PWM 通道与引脚映射

### PWMA 端口选择（PWMA_PS）

| PWM_PS 值 | PWM1 (P/N) | PWM2 (P/N) | PWM3 (P/N) | PWM4 (P/N) |
|-----------|------------|------------|------------|------------|
| 0x00      | P1.0/P1.1  | P1.2/P5.4/P1.3 | P1.4/P1.5  | P1.6/P1.7  |
| 0x01      | **P2.0/P2.1** | P2.2/P2.3  | P2.4/P2.5  | P2.6/P2.7  |
| 0x02      | P6.0/P6.1  | P6.2/P6.3  | P6.4/P6.5  | P6.6/P6.7  |
| 0x03      | —          | —          | —          | P3.4/P3.3  |

### PWMB 端口选择（PWMB_PS）

| PWMB_PS 值 | PWM5 | PWM6 | PWM7 | PWM8 |
|-----------|------|------|------|------|
| 0x00      | P2.0 | P2.1 | P2.2 | P2.3 |
| 0x01      | P1.7 | P5.4 | P3.3 | P3.4 |

### 引脚输出使能（PWMA_ENO）

| Bit | 含义 |
|-----|------|
| 0   | ENO1P |
| 1   | ENO1N |
| 2   | ENO2P |
| 3   | ENO2N |
| 4   | ENO3P |
| 5   | ENO3N |
| 6   | ENO4P |
| 7   | ENO4N |

---

## 波形合成（DAC 模式）

### 原理

将 PWM 作为高速 DAC 使用：固定载波频率（超声波范围），动态调制 duty cycle 来逼近目标波形。

### 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 载波频率 | 172.8kHz | period=64, prescaler=0, 远超人耳 |
| Duty 分辨率 | 6-bit (0~63) | period=64 |
| 波形表 | 32 点 uint8_t | 直接存 duty 值 |
| 音频频率 | ~300~600Hz | 由 main loop 步进速度控制 |

### 载波频率选择

- **14.4kHz**（period=32, prescaler=23）：可听到载波噪音 ❌
- **86kHz**（period=128, prescaler=0）：仍有毛刺 ❌
- **172.8kHz**（period=64, prescaler=0）：超声波，无噪音 ✅

### 波形表格式

直接存 uint8_t duty 值（0~63），避免 ISR 内做 int8→duty 转换（SDCC 8051 符号扩展可能有问题）。

```c
static uint8_t __code sine_table[32] = {
    32,36,40,44,47,50,53,55,
    56,55,53,50,47,44,40,36,
    32,28,24,20,17,14,11, 9,
     8, 9,11,14,17,20,24,28
};
```

### 已知限制

- **Timer ISR 驱动失败**：Timer0/Timer3 ISR 在 `P_SW2 |= 0x80` 保持开启时不触发或异常，原因未明。当前用 main loop 延时驱动，无法同时做其他任务。
- **无 RC 滤波器**：直接接喇叭，理论上 172kHz 载波人耳听不到，但某些压电蜂鸣器可能有开关噪声。
- **音量调制**：ISR 内 16-bit 除法导致性能问题，需用查表或移位近似。

---

## 踩坑记录

### Timer3 freq1t 参数导致超声波

`TIM_Timer3_Config` 第一个参数 `freq1t`：
- `HAL_State_ON` → 1T 模式（SYSCLK 直接），频率比预期高 12 倍
- `HAL_State_OFF` → 12T 模式（SYSCLK/12），传统 8051 定时器行为

**错误：** 用 `HAL_State_ON` + period=262，实际频率 42kHz（超声波）
**正确：** 用 `HAL_State_OFF` + period=262，实际频率 3.5kHz

### PWMA prescaler=0 导致超声波

PWMA 始终 1T 模式，prescaler=0 时 PWM 时钟 = SYSCLK = 11MHz。
- period=1047（A4 目标值）→ 实际频率 11MHz/1048 ≈ **10.5kHz**（超声波）
- 需要 prescaler=23（÷24）→ 11MHz/24/1048 ≈ **440Hz** ✓

### P5.4 互补通道无输出

PWM2N 在 P5.4（`PWMA_PWM2_AlterPort_P12P54_P13`），配置了 `PWMA_ENO |= PWM_Pin_2N` 但无音频输出。
P2.0 PWM1P 主通道同样配置正常工作。原因未明，建议使用主通道（P）引脚。

### main loop 切音符 vs Timer ISR

当前 Timer3 ISR 内切换 PWM 频率不工作（可能与 `P_SW2` 状态冲突），workaround 是在 main loop 延时循环中切换。后续需排查 ISR 中 XFR 访问问题。

---

## 参考

- 官方 demo：`STC8H8K64U-DEMO-CODE-V9.6/23-高级PWM1-PWM2-PWM3-PWM4`
- 官方 WAV 播放：`STC8H8K64U-DEMO-CODE-V9.6/80-播放WAV-8K采样率-8bit采样-PWM5-P1.7`
- FwLib_STC8 PWM 头文件：`lib/FwLib_STC8/include/fw_pwm.h`
