# STC32G12K128 - 项目进度

## 项目目标

基于 STC32G12K128（32 位 8051）开发复古芯片合成器，作为 STC8H8K64U 的升级方案。
更快的 CPU（24MHz vs 11MHz）、更大的 IRAM（4K vs 256B）、原生 USB CDC 支持。

## 进度

### ✅ 已完成

| 阶段 | 内容 | 日期 |
|------|------|------|
| 开发环境 | Keil C251 V5.60 CLI 构建（C251 + l251 + OH251） | 2025-06 |
| LED 闪烁 | P6.0 推挽输出，SMALL 内存模型，编译链接成功 | 2025-06 |

### 🔲 待完成

| 阶段 | 内容 | 状态 |
|------|------|------|
| UART 通信 | 串口收发测试 | 待开发 |
| PWM 音频 | 高级 PWM DAC 输出 | 待开发 |
| USB CDC | 利用原生 USB 做虚拟串口 | 可选 |
| 芯片仿真 | SCC/PSG 音源芯片仿真 | 待开发 |

---

## 已知问题

1. **cmd.exe 括号问题** — Keil C251 的带括号指令（如 `OPTIMIZE(7,SPEED)`）无法通过 cmd.exe 命令行传递，需用 `#pragma` 放在源码中。
2. **l251.exe 小写** — 链接器文件名为小写 `l251.exe`，在某些 shell 中 `ls *.EXE` 可能漏掉。
3. **COMPACT 模型缺库** — C251 V5.60 没有 `C2SC.LIB`，需用 `SMALL` 模型。
4. **UV4 工程需 STC Pack** — 直接用 `uvproj` 需要 STC-ISP 添加设备数据库，CLI 编译不需要。

---

## 参考资源

- [STC32G12K128 官方产品页](https://www.stcmicro.com/stc/stc32g12k128.html)
- [STC32G-DEMO-CODE (GitHub)](https://github.com/nickfox-taterli/STC32G-DEMO-CODE)
- [STC32G 技术参考手册](https://www.stcmicro.com/datasheet/stc32g-cn.pdf)
- [逐飞科技 STC32G 开源库](https://gitee.com/seekfree/STC32G12K128_Library)
- [Keil C251 命令行文档](https://developer.arm.com/documentation/101655/0961/Cx51-User-s-Guide/Compiling-Programs/Command-Prompt)
