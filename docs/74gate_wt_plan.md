# 74系列门电路 WT 合成器计划

## 目标

用 74 系列逻辑门 + SRAM + ROM 搭建最简 WT 波形表合成器，不依赖 MCU。

## 工具链

- **Verilog 编写**: 任意编辑器
- **综合**: [Yosys](https://github.com/YosysHQ/yosys) + [yosys74](https://github.com/roughengineer/yosys74) (74系列门库)
- **仿真**: [Icarus Verilog](https://github.com/steveicarus/iverilog) + GTKWave
- **流程**: Verilog → Yosys 综合到 74xx 网表 → Icarus Verilog 仿真验证 → 手动布线/原理图

## WT 核心逻辑

```
每 CLK 周期:
  ACC += STEP          // 16-bit 相位累加器
  ADDR = ACC[15:8]     // 高 8 位作为 ROM 地址
  OUT  = ROM[ADDR]     // 查表输出
  DAC  = R-2R(OUT)     // 8-bit DAC
```

## 硬件估算 (单通道)

| 功能 | 元件 | 数量 |
|------|------|------|
| 相位累加器 (16-bit ADD+REG) | 74HC283 x4 + 74HC574 x1 | 5 |
| 波形 ROM | 28C64 (8Kx8 EEPROM) | 1 |
| 时钟振荡 | 晶振 + 74HC04 | 1 |
| DAC | R-2R 电阻网络 (9个电阻) | - |
| 低通滤波 | RC 滤波 | - |
| **合计** | | **7 颗 IC** |

## 元件映射 (Verilog → 74 门)

| Verilog 构造 | 74 系列实现 |
|-------------|------------|
| `always @(posedge clk) reg <= val` | 74HC574 (8-bit 锁存) |
| `assign sum = a + b` | 74HC283 (4-bit 加法器) |
| `rom[addr]` | 28C64 / 28C256 (EEPROM) |
| `sram[addr]` | HM62256 (32Kx8 SRAM) |
| `assign y = a & b` | 74HC08 (AND 门) |
| `assign y = a \| b` | 74HC32 (OR 门) |
| `assign y = ~a` | 74HC04 (NOT 门) |
| `assign y = sel ? a : b` | 74HC157 (MUX) |
| 计数器 | 74HC161 (4-bit 同步计数器) |

## 开发步骤

1. 搭建工具链 (Yosys + Icarus Verilog + yosys74)
2. 写 WT 核心 Verilog (相位累加器 + ROM 查表)
3. Icarus Verilog testbench 验证输出波形
4. Yosys 综合到 74xx 网表，确认资源用量
5. 扩展: 多通道、包络、频率控制接口
6. 面包板/PCB 原型验证

## 状态

规划阶段，待工具链搭建后开始。
