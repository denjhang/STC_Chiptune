# ADPCM 打击乐器折腾记录

## 目标
在 STC32G12K128 上播放 YM2608 内置 8KB ROM 的 6 个打击乐器。

## YM2608 ADPCM 基础

### 硬件参数
- 时钟: 8MHz, freqbase = 8000000/144 ≈ 55555.6
- ch0-3 采样率: freqbase/3 ≈ **18518 Hz**
- ch4-5 采样率: freqbase/6 ≈ **9259 Hz**
- 我们的下位机 tick: **17640 Hz** (Timer0 ISR)

### ADPCM Type A 解码
- jedi_table: 49 steps × 16 nibbles = 784 个 s16 值
- step_inc: [-16,-16,-16,-16, 32,80,112,144]
- 12-bit accumulator, 带 wrap (不是 saturate)
- 符号扩展: bit11=1 时 |= ~0xFFF

### ROM 地址 (libvgm 权威来源, fmopn.c YM2608_ADPCM_ROM_addr[])
```
索引  名称         起始(字节)  结束(字节,含)  字节数   nibble数   采样率
0     Bass Drum    0x0000      0x01BF         448     896        18518
1     Snare Drum   0x01C0      0x043F         640     1280       18518
2     Top Cymbal   0x0440      0x1B7F         5952    11904      18518
3     High Hat     0x1B80      0x1CFF         384     768        18518
4     Tom Tom      0x1D00      0x1F7F         640     1280       9259
5     Rim Shot     0x1F80      0x1FFF         128     256        9259
```

**注意**: end 地址是包含的, 字节数 = end - start + 1。header 注释的长度不一定准确。

## 踩坑记录

### 1. 鼓映射搞错
最初把 0x0440 当成 HH，0x1B80 当成 TC。实际:
- 0x0440 = **Top Cymbal** (最长 6KB)
- 0x1B80 = **High Hat** (较短 384B)

### 2. ROM 地址边界不精确
header 文件注释的长度和 libvgm 地址不完全一致。以 libvgm 的 start/end 为准。
验证方法: 用 Python 解码每个鼓的 WAV，听边缘是否有其他鼓的声音混入。

### 3. 预处理脚本 nibble 计算双倍 bug
`adpcm_decode(rom_data, start_byte, length_bytes)` 内部会 `total_nibbles = length_bytes * 2`，
但调用处传的已经是 `nib_count = byte_len * 2`，导致解出 4 倍 sample。
修复: 传 `nib_count // 2`。

### 4. 跳采样不可行
直接跳过 ADPCM sample 不行 — ADPCM 解码是有状态的 (step/acc 依赖前一个 sample)，
跳过会导致解码完全错误。

### 5. 预处理写入 ROM 后再读回，数据可能被污染
`adpcm_preprocess.py` 生成新 header 覆盖原始 ROM。如果脚本读的是自己之前输出的
(已被污染的) ROM 而不是原始 ROM，会导致数据全零。每次预处理前必须 `git checkout` 恢复原始 ROM。

### 6. WAV 验证采样率问题
- 用 18518Hz 保存的 WAV 播放正常
- 用 17640Hz 保存的 WAV 会略快（5% 速度差异）
- div=2 的鼓用 sample-and-hold 拉伸到 17640Hz 会失真

## 最终方案: 上位机预处理

### 流程
1. `git checkout` 恢复原始 `fmopn_2608rom.h`
2. Python 解码原始 ROM ADPCM → PCM (按原始采样率)
3. 重采样到目标频率 (17640 或 8820Hz)
4. 重新 ADPCM 编码
5. 打包写入新的 `fmopn_2608rom.h`
6. 下位机所有鼓 SPT=1, 用 div 分频控制播放速度

### 分频策略
- BD/SD/HH: div=1, 数据重采样到 17640Hz, 每 tick 解码
- TC/TM/RS: div=2, 数据重采样到 8820Hz, 每 2 tick 解码
- ROM 总共 ~5KB, 远小于 8KB 上限 (STC32G 有 128KB Flash)

### 当前预处理后的 ROM 布局
```
鼓    偏移(字节)  字节数   nibble数  div
BD    0x0000      427     854       1
SD    0x01AB      610     1219      1
TC    0x040D      2835    5670      2
HH    0x0F20      366     732       1
TM    0x108E      610     1219      2
RS    0x12F0      122     244       2
```

### 下位机寄存器 (复用 WT 的 0xC0 UART 前缀)
```
0x15-0x1A: ch0-5 note on  (data = drum 0-5)
0x1B-0x20: ch0-5 note off
0x21-0x26: ch0-5 volume   (0-31)
```

### 下位机关键变量
- `drum_start[6]`: ROM 字节起始地址
- `drum_len[6]`: nibble 长度
- `drum_div[6]`: tick 分频 (1 或 2)
- channel struct: `div` + `div_cnt` 实现分频

### 待修复: 下位机播放仍有卡拉卡拉响
WAV roundtrip 验证全部正确，但下位机实际播放除 BD 外仍有噪音。
可能原因待查:
- 下位机 jedi_table 数据正确性
- 12-bit acc 符号扩展在下位机的实现
- ROM 数据编译到 const 段后读取是否正确
