# STC32G12K128 开发环境

## 芯片参数

| 参数 | 值 |
|------|-----|
| 架构 | 32 位 8051（扩展数据总线） |
| 封装 | DIP-40 / LQFP32/48/64 |
| Flash | 128K |
| SRAM | 12K（IRAM 4K + XRAM 8K） |
| 默认主频 | 24MHz IRC（可软件调节） |
| 串口 | 4 路 UART + 2 路 CAN |
| USB | USB 2.0 FS（CDC/HID/MSC/WinUSB） |
| ADC | 12-bit |
| PWM | 高级 PWM × 8 + 高速 HSPWM × 4 |

## 开发环境：Keil C251 + CLI 自动构建

### 工具链

| 工具 | 路径 | 用途 |
|------|------|------|
| C251.EXE | `D:\Keil_v5\C251\BIN\` | 编译器 |
| l251.exe | `D:\Keil_v5\C251\BIN\` | 链接器（注意小写） |
| OH251.EXE | `D:\Keil_v5\C251\BIN\` | HEX 生成 |
| go.bat | 项目目录 | 一键编译脚本 |

### 编译流程

```
main.c  →  C251.EXE  →  main.OBJ  →  l251.exe  →  test  →  OH251.EXE  →  test.hex
              (编译)                    (链接)              (HEX生成)
```

一键编译：
```batch
cd STC32G12K128
go.bat
```

### 内存模型

| 模型 | #pragma | 默认数据段 | 运行库 | 说明 |
|------|---------|-----------|--------|------|
| SMALL | `SMALL` | edata（快速 XRAM） | C2SS.LIB | **推荐**，默认 1K 栈在 edata |
| COMPACT | `COMPACT` | xdata | C2SC.LIB | ⚠️ C251 未提供此库 |
| LARGE | `LARGE` | xdata/far | C2SL.LIB | 大数据模型 |

> 官方推荐 XSmall 模型（对应 `SMALL`），默认变量放在 edata（片上 XRAM 低 1K，CPU 直接寻址速度快）。

### 编译器指令

带括号的指令（如 `OPTIMIZE(7,SPEED)`）不能通过命令行传递（cmd.exe 会将 `()` 解析为分组操作符），必须放在 C 源文件中用 `#pragma`：

```c
#pragma SMALL           /* 内存模型 */
#pragma OPTIMIZE(7, SPEED)  /* 优化级别 7, 速度优先 */
#pragma CODE            /* ROM 代码 */
```

命令行只传不带括号的参数：
```batch
C251.EXE main.c SMALL BROWSE DEBUG
```

### 烧录

使用 **STC-ISP** 软件手动烧录（串口断电触发 ISP）。

---

## 目录结构

```
STC32G12K128/
├── main.c           # 源代码
├── STC32G.H         # 寄存器定义（来自官方 demo）
├── go.bat           # 一键编译脚本
├── test.uvproj      # Keil UV4 工程文件（备用，需安装 STC Pack）
├── test.hex         # 编译输出
├── docs/            # 技术文档
└── *_opts.rsp       # 编译器 response file（备用）
```

---

## 踩坑记录

### 1. l251.exe 是小写

链接器可执行文件名为小写 `l251.exe`，不是 `L251.EXE` 或 `LX51.EXE`（UV4 工程文件里写的是 `Lx51`，但实际文件是小写）。`ls *.EXE` 在 Windows 下默认大小写不敏感，但某些情况会漏掉。

### 2. cmd.exe 括号问题

cmd.exe 中 `()` 是分组操作符（用于 `if/for`），直接在命令行传递 `OPTIMIZE(7,SPEED)` 会被截断。解决方案：
- 用 `#pragma` 放在 `.c` 文件里（**推荐**）
- 用 response file `@opts.rsp`（但 C251 的 `@file` 只接受指令，源文件必须单独传）
- PowerShell 的 `--%` 停止解析（但 `@` 又变成 splatting 操作符）

### 3. COMPACT 模型缺库

C251 V5.60 的 LIB 目录没有 `C2SC.LIB`（COMPACT 模型库），只有 SMALL（C2S*）和 BANKING（C2B*）。使用 `SMALL` 模型替代。

### 4. UV4 工程需要 STC Pack

`test.uvproj` 里的 `DeviceId=63457` 需要先通过 STC-ISP 的"Keil 仿真设置"添加 STC32G 设备数据库才能用 UV4 IDE 打开。CLI 编译不需要。

---

## 参考

- [STC32G12K128 官方产品页](https://www.stcmicro.com/stc/stc32g12k128.html)
- [STC32G-DEMO-CODE (GitHub)](https://github.com/nickfox-taterli/STC32G-DEMO-CODE)
- [STC32G 技术参考手册](https://www.stcmicro.com/datasheet/stc32g-cn.pdf)
- [Keil C251 命令行文档](https://developer.arm.com/documentation/101655/0961/Cx51-User-s-Guide/Compiling-Programs/Command-Prompt)
- [逐飞科技 STC32G 开源库](https://gitee.com/seekfree/STC32G12K128_Library)
