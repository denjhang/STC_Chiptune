# usb_cdc_test 移植进度

## 目标
将 STC 官方 88-USB-CDC 双串口纯源码移植到 STC32G144K246，替代 UART1 串口通信。

## 基准：主项目已验证
- PWMB CH1 → P0.0, 8-bit DAC 音频输出（60MHz PLL, ARR=255, CCR 动态写入）
- Timer0 ISR 1T 模式 17640Hz, 每 ISR 写 PWMB_CCR5L
- UART1 中断收发 VGM 命令

## 参考：88-USB-CDC 双串口
- 来源: `STC32G-DEMO-CODE-master/88-USB-CDC转双串口-根据串口波特率自动调整主频/`
- 已原样复制到 `usb_cdc_test/`（含 src/inc/ 子目录结构）
- 需要的额外文件: `src/comm/STC32G.H`（从 COMM/ 目录拷贝）
- 编译器: C251, `INCDIR(inc)` 指定头文件搜索路径
- 一键构建: `py -3 build.py`（compile → link → hex）
- 默认 24MHz IRC, 无 PLL, USB 走独立 IRC48M

## 验证记录

### ✅ Phase 1: 原样编译 + HEX 生成
- 9 个源文件 0 错 0 警编译通过
- code=5246, xdata=1082
- HEX 生成成功 (14834 bytes)

### ✅ Phase 2: 加 P2 流水灯 + PWMB + 主循环 (含 USB CDC)
- P2 流水灯: ✅ 正常
- USB CDC 双串口: ✅ 正常（电脑能枚举 2 个串口）
- PWMB P0.0: ❌ 只听到咔咔声，无方波

### ✅ Phase 3: 删实验箱特有 IO (DOWNLOAD/SVCC_E/LED_POWER)
- PWMB P0.0: 仍有咔咔 2 次（上电 + USB 枚举瞬间），无持续咔咔
- 结论: PWMB 本身可能没真正启动，咔咔是其他原因

### ✅ Phase 4: 最小验证 (无 USB/UART/Timer)
- 只保留: init + PWMB 438Hz 方波 + P2 流水灯
- PWMB P0.0: ✅ 能听到 438Hz 蜂鸣
- P2 流水灯: ✅ 正常
- **结论: PWMB 配置正确，问题出在与其他模块共存时**

### 🔲 Phase 5: 逐步加回模块 (下一步)
- 加回 Timer0 ISR → 验证 PWMB 不受中断影响
- 加回 usb_init + usb_isr → 验证 USB CDC 和 PWMB 共存
- 如果 PWMB 停声 → USB ISR 或 USB 时钟配置干扰 PWMB
- 如果正常 → Phase 2 的咔咔是实验箱 IO 操作引起的

## 关键发现
1. `INCDIR(inc)` 不是 `INCLUDE(inc)` — C251 用 INCDIR 指定 include 路径
2. C251/L251 有 WARNING 时 `rc != 0`，脚本判断失败不能看 rc，要看输出里的 `*** ERROR` / `FATAL`
3. 参考项目 88 的 `port.h` 定义 DOWNLOAD(P3.2)/SVCC_E(P4.0)/LED_POWER(P6.7) 是实验箱专用，144K246 板子上不可用
4. PWMB 单独跑没问题，共存有咔咔 → 待 Phase 5 定位

## 文件结构
```
usb_cdc_test/
├── build.py                    # 一键构建脚本
├── src/
│   ├── main.c                  # 主程序（Phase 4: 最小版）
│   ├── main_with_usb_cdc.bak   # Phase 2 备份（含完整 USB CDC）
│   ├── timer.c / timer.h       # Timer0 ISR（f1ms 标志）
│   ├── usb.c / usb.h           # USB 核心 + ISR (interrupt 25)
│   ├── usb_desc.c / .h         # USB 描述符（双 CDC 141 字节）
│   ├── usb_req_std.c / .h      # 标准请求处理
│   ├── usb_req_class.c / .h    # CDC 类请求（SET_LINE_CODING 等）
│   ├── usb_req_vendor.c / .h   # Vendor 请求
│   ├── uart.c / uart.h         # UART2/3 配置（CDC 透传目标）
│   ├── util.c / util.h         # 工具函数 (reverse2)
│   ├── config.h                # EP 使能/大小配置
│   ├── port.h                  # 实验箱引脚定义（144K246 上不可用）
│   ├── stc.h                   # 类型定义 + include 链
│   ├── comm/
│   │   └── STC32G.H           # 寄存器定义（与主项目一致）
│   └── build/
│       └── MAIN.hex            # 输出固件
└── 功能说明.txt                 # 参考项目说明
```
