# BRR ADSR 包络开发记录 (2026-06-16)

## 问题

BRR 4ch 旋律采样合成器 ADSR 包络长时间不工作，调试耗费大量时间。问题层层叠加：

### Bug 1: ADSR 命令未到达 brr_wr

ADSR 地址 0x18/0x19/0x1A 加上 BRR_BASE(0x34) = 0x4C/0x4D/0x4E，超出了 main.c 路由范围 0x34-0x47。ADSR 命令被当作 WT 处理，BRR 一直用 brr_init 默认值。

修复：main.c 路由范围扩大到 0x34-0x4F。

### Bug 2: 音量公式中 ADSR 无效

```c
// 原来: level 乘在 vol 之后, >>10 压缩到 3%
out * vol * level >> 10   // level=31 时 92, 无包络时 95, 几乎没区别
```

修复：ADSR 模式下 ADSR 完全控制音量，不经过 vol：
```c
if (env_state) out * level >> 5;
else           out * vol >> 5;
```

### Bug 3: sul 映射方向反

原 `brr_tone.sul = brr_tone.sul == 15 ? 31 : 31 - sul*2` 导致 sul=0 和 sul=15 结果一样都是 31。修复为 `sul * 2` 线性映射。

### Bug 4: sustain 阶段逻辑错误

最初实现：sustain 保持 level 不变（等 note_off 进 release）。导致所有音符无限延长。

参考 [参考项目](../../Reference_Project/STC-MCU/extracted/) 的 ISR_wave.S 实现，发现正确的 ADSR 行为是：

- **Attack**: level 0 → 31（速度由 atk 控制）
- **Decay**: level 31 → sul（速度由 dec 控制，sul 是衰减终止目标）
- **Sustain**: level sul → 0 **继续衰减**（速度由 sus 控制，不是保持！）
- **Release**: note_off 后 level → 0（速度由 rel 控制）

关键：**sustain 不是保持电平，而是继续衰减到 0**。sus 参数控制的是衰减速度，不是保持。这就是参考项目里 `sul = sul * 4`（衰减目标）而 `sus = env_cnt[index]`（衰减速度）的原因。

### Bug 5: level=0 时通道未释放

sustain 衰减到 0 后通道仍然 active，采样继续解码浪费 CPU。修复：所有阶段 level==0 时 goto env_kill 释放通道。

## 最终 ADSR 参数语义

| 参数 | 范围 | 含义 |
|------|------|------|
| atk  | 0-15 | attack 上升速度，env_cnt[atk] 越大越快 |
| dec  | 0-15 | decay 衰减速度，env_cnt[dec] 越大越快 |
| sul  | 0-15 | decay 衰减终止目标，sul*2 = level 值 (0=静音, 15=30≈满) |
| sus  | 0-15 | sustain 继续衰减速度，env_cnt[sus] 越大越快 |
| rel  | 0-15 | release 衰减速度，env_cnt[rel] 越大越快 |

env_cnt = [0, 1, 2, 3, 4, 5, 7, 10, 13, 20, 29, 43, 64, 86, 128, 255]

## 最终 ADSR_TEMPLATES (14 乐器)

按 ROM 乐器编号排序，均已调试验证：
```
 0 AcPiano:    (15, 3, 2, 4, 4)      瞬A + 快D + 低sul + 中S + 中R
 1 Violin:     (10, 4, 2, 10, 10)     中A + 中D + 低sul + 慢S + 慢R
 2 Strings:    (10, 4, 2, 10, 10)
 3 Harp:       (15, 8, 2, 4, 4)
 4 Accordion:  (7,  3, 8, 4, 4)
 5 Organ:      (5,  6, 12, 6, 5)
 6 Fretless:   (15, 3, 12, 2, 2)
 7 JazzGtr:    (15, 3, 12, 2, 2)
 8 DistGtr:    (15, 8, 2, 4, 4)
 9 Celesta:    (15, 10, 6, 2, 2)
10 Flute:      (3,  4, 9, 5, 4)
11 Recorder:   (10, 4, 2, 10, 10)
12 Oboe:       (10, 4, 2, 10, 10)
13 Clarinet:   (10, 4, 2, 10, 10)
```

## 关键文件

- `STC32G12K128/brr.c` — ADSR 包络逻辑
- `STC32G12K128/brr.h` — BRR 寄存器定义
- `STC32G12K128/brr_rom.h` — 14 乐器 ROM 数据
- `STC32G12K128/main.c` — UART 路由 (0xC0, 0x34-0x4F → brr_wr)
- `tools/brr_uart_test.py` — 扫频测试 + ADSR 模板
- `tools/gen_brr_rom.py` — BRR ROM 生成
- `docs/brr_uart_test_20260616.py` — 上位机测试脚本备份
