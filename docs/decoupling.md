# 仿真核心解耦文档

## 架构

```
src/
├── types.h       — 共享类型定义 (u8/u16/u32/s8/s16)
├── ay8910.h/c    — AY8910 仿真核心
├── scc.h/c       — SCC 仿真核心 (待剥离)
├── sn76489.h/c   — SN76489 仿真核心 (待添加)
└── main.c        — ISR + UART + 混音 + 初始化
```

## 模块接口规范

每个仿真核心模块提供 3 个函数：

```c
void xxx_init(void);        // 初始化状态
void xxx_wr(u8 reg, u8 val); // 写寄存器
s16 xxx_render(void);        // 渲染一帧，返回有符号混音值
```

- `xxx_wr()` 由 `process_uart()` 在 ISR 任务中调用
- `xxx_render()` 由 Timer0 ISR 直接调用
- 模块内部状态用 `static` 隐藏，外部只通过上述 3 个接口访问

## 类型定义

`types.h` 提供共享类型，所有模块通过 `#include "types.h"` 引入。

## Keil C51 多文件编译

```bash
# 1. 分别编译每个 .c
C51.exe src/ay8910.c OPTIMIZE(8,SPEED) INCDIR(include,src)
C51.exe src/scc.c     OPTIMIZE(8,SPEED) INCDIR(include,src)
C51.exe src/main.c    OPTIMIZE(8,SPEED) INCDIR(include,src)

# 2. 链接所有 .OBJ
BL51.exe src/ay8910.OBJ,src/scc.OBJ,src/main.OBJ TO build/main

# 3. 生成 HEX
OH51.exe build/main
```

关键点:
- `INCDIR(include,src)` — 同时搜索 include/ 和 src/ 目录
- 每个模块的 .c 必须先编译为 .OBJ，再一起链接
- BL51 的输入顺序不影响结果

## 已验证

- AY8910 剥离测试通过，AY 曲目正常播放
- WARNING L15 (MULTIPLE CALL TO SEGMENT) 可忽略，因为 ay_wr 在 ISR 和 main 中都被调用
