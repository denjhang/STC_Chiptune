# STC_Chiptune

基于 STC 单片机的复古芯片合成器项目。通过 TTL 串口接收控制命令，PWM 输出音频，模拟经典 PSG/SCC 音源芯片。

## 目录结构

```
STC_Chiptune/
├── STC8H8K64/          # STC8H8K64U (DIP-40, 1T 8051, 11MHz)
│   ├── src/main.c       # 主程序（UART echo + PWM DAC 音频合成）
│   ├── include/          # 头文件
│   ├── tools/            # Python 上位机工具
│   ├── docs/             # 技术文档、demo 参考
│   ├── lib/              # FwLib_STC8 HAL 库
│   └── platformio.ini    # PlatformIO 配置
├── STC32G12K128/        # STC32G12K128 (32位 8051, Keil C251)
│   ├── main.c           # LED 闪烁测试
│   ├── STC32G.H         # 寄存器定义
│   ├── go.bat            # Keil C251 一键编译
│   └── docs/             # 开发环境文档
└── README.md
```

## 当前状态

- **STC8H8K64**: PWM DAC 音频合成已验证（sine/saw/tri/sq 波形 + 音量衰减），UART echo 测试通过，UART+PWM 集成待调试
- **STC32G12K128**: Keil C251 构建环境搭建完成，LED 闪烁编译通过
