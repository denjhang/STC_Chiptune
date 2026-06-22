# NES APU 集成进度 (2026-06-22)

NES APU (Ricoh 2A03) 是第五个集成进 STC32G144K 固件的音源。本文档记录 NES
从初版集成到 Deflemask DAC stream 支持的完整调试历程, 与
`GB_INTEGRATION_STATUS.md` 并列, 互不混入.

总览状态见 `README.md`, libvgm 完整命令表见 `docs/VGM_COMMAND_TABLE_libvgm.md`.

## 1. 目标

在 STC32G144K (72MHz, 12-bit DAC, USB CDC) 上软件模拟 NES APU 5 通道,
播放 NES VGM 文件, 音质对齐 libvgm.

## 2. 已完成

### 2.1 代码 (nes.c / nes.h)

- 5 通道: 2x 方波(包络+扫频) + 三角波 + 噪声 + DMC (1-bit delta 调制)
- DMC 采样缓冲 16KB, 覆盖 NES CPU memory $C000-$FFFF
- PAL/NTSC 双时钟自动适配 (运行时 `nes_set_clock`)
- 预存/流式混合策略 (DMC 数据 > 16KB 时自动流式)
- **Deflemask DAC stream (0x90-0x95) 支持** — 见 §4

### 2.2 libvgm 参考路径

- 仿真核心: `Reference_Project/vgm_libs/libvgm-master/emu/cores/nes_apu.c`
- DAC stream 引擎: `emu/dac_control.c` (Deflemask NES DAC 走这条路径)
- 命令分发: `player/vgmplayer_cmdhandler.cpp` (`Cmd_NES_Reg`, `Cmd_DACCtrl_*`)
- 完整命令表已固化: `docs/VGM_COMMAND_TABLE_libvgm.md`

### 2.3 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| NES_RATE | 22050.0 | 采样率 (nes.h) |
| NES_GETA_BITS | 24 | 定点小数位数 |
| nes_frame_div | 92 | `22050/240 ≈ 91.875`, NES frame counter 保持 240Hz |
| nes_dpcm_periods[16] | NTSC 表 | 每个 DMC bit 占用的 CPU 周期 |
| DMC buffer | 16384 字节 | 对应 $C000-$FFFF |

### 2.4 混音系数 (main.c ISR)

```c
mix = nes_squ[0].output + nes_squ[1].output;
mix += nes_tri.output * 3 / 4;
mix += nes_noi.output * 3 / 4;
mix += nes_dpcm.output;   // DMC/DAC 全幅 (±64)
```

## 3. NES APU 实现要点 (5 通道)

### 3.1 2x 方波 (pulse)

每通道 4 寄存器 (duty/env/vol, sweep, freq_lo, len/freq_hi):
- duty 4 模式 (12.5%/25%/50%/75%) 查表 `nes_duty_lut[4]`
- 软件包络: 15 级衰减, frame IRQ 触发
- 频率扫频: 由 reg[1] 的 shift/方向/周期控制

### 3.2 三角波

32 步波形查表, linear counter + length counter 双重 gating.

### 3.3 噪声

15-bit LFSR (mode 1=Sega VDP, mode 0=NES), `nes_noise_freq[16]` 频率表.

### 3.4 DMC (1-bit delta 调制)

- 每个 bit 按 `nes_dpcm_periods[reg0 & 0x0F]` 周期消耗
- bit=1 vol+=2, bit=0 vol-=2, vol 钳位 [0..127]
- 7-bit DAC 输出 (转 signed: vol - 64)
- 采样数据来源: `0x67 type=0xC2` NES CPU RAM write

## 4. Deflemask DAC stream 支持 (0x90-0x95)

### 4.1 根因 (关键, 防再次误判)

**Deflemask 导出的 NES VGM 不走标准 DMC 路径**, 而是用 **DAC stream 机制**:
- 不用 `0x67 type=0xC2` (NES CPU RAM write, 标准 DMC 采样)
- 不用 `0xB4 0x11` 直写 `$4011` 命令
- 而是用 **`0x90-0x95` DAC Stream Control 命令**:
  - `0x90` Setup: 绑定 stream → NES APU (chipType=0x14), 目标命令 `$4011`
  - `0x91` SetData: 绑定 PCM bank (bank 0)
  - `0x92` SetFreq: 设播放频率 (Deflemask 用 8000 / 11025 Hz)
  - `0x95` Play: 按 sound ID 播放 (sndID 索引 bank 里的 sound)
  - `0x94` Stop: 停止

libvgm 的 `dac_control.c` 引擎按 `freq/sampleRate` 比例, 自动从 PCM bank 取字节
调 `write8($4011, byte)`. 这是 **7-bit DAC 直写模式** (绕过 DMC 的 1-bit delta 调制).

PCM 数据格式: `0x67 type=0x00~0x3F` data block, 每个 block 是一个 sound, 按 sndID 顺序
追加到 bank. 字节是 **7-bit unsigned, 中心 ≈ 0x3F (63)**, 范围 0x1B-0x64.

### 4.2 第一次误判 (重要教训)

最初的 `nes_reg_stats.py` 只统计 `0xB4` 命令, 发现 feeblemask 完全没有 `$4011` 写入,
**错误结论**: "这首曲子不用 DMC/DAC, 纯靠方波+三角+噪声".

**真相**: 用基于 libvgm 完整命令表的审计器 (`vgm_cmd_audit.py`) 才发现:
- 316 次 `0x95 PLAY` 命令
- 7 个 PCM bank (`0x67 type=0x00`), 共 14463 字节
- DAC stream 走 `0x90-0x95`, `$4011` 由引擎自动写, 不进 `0xB4` 命令流

**教训**: VGM 命令解析必须用**完整命令表** (libvgm `vgmplayer_cmdhandler.cpp` 的
`_CMD_INFO[0x100]`), 不能只看部分命令. 已固化为 `docs/VGM_COMMAND_TABLE_libvgm.md`
和 `tools/vgm_cmd_audit.py`, 防再次误判.

### 4.3 改动 (全在 vgm_player.py, 不动 nes.c/main.c)

MCU 端 `nes.c` case 0x11 已够用 (`vol = val & 0x7F` → `output = vol - 64` 直接进 mix,
无需改固件).

**parse_vgm_header**:
- 收集 PCM bank (`0x67 type=0x00~0x3F`), 每个 block 是一个 sound, 返回 `pcm_banks`
- 修复 `0x90-0x95` 扫描长度 (之前当 1 字节跳过, 误吞后续命令)

**scan_vgm_stats**:
- 修复 `0x80-0x8F` (YM2612 DAC stream wait 是 `n` 不是 `n+1`, 独立 bug)
- `0x90-0x95` 按正确长度跳过 (0x90/0x91=5, 0x92=6, 0x93=11, 0x94=2, 0x95=5),
  不再误算为 wait (之前虚增 duration)

**新增 dac_tick(state, ser, samples)**:
- 按 `freq/44100` 比例, 在 samples 个 VGM sample 时间内逐字节取 PCM 数据
- 发 `[0xB4 0x11 byte]` 到 MCU
- 支持 loop (flags bit7)
- **关键: 每字节单独 `ser.write`** (不批量打包, 见下文)

**play_vgm 主循环**:
- 新增 `dac_state` 状态机 (active/freq/data/start/length/pos/loop/acc)
- 处理 `0x90/0x91/0x92/0x93/0x94/0x95`
- 每个 wait 命令 (0x61/0x62/0x63/0x70-0x7F/0x80-0x8F) 后调 `dac_tick(n)`
- loop 重启 (0x66 → loop_offset) 时重置 dac_state
- 进度条模仿 DMC 流式: `DAC [PCM] #N sndX/Y size [LOOP]`

### 4.4 关键 bug: 批量发送 vs 每字节一发

最初 dac_tick 用批量打包 (192 字节/包, 64 个命令合一次 `ser.write`), 实测 **PCM 鼓声
非常沙哑, 像缺采样**. 改回**每字节单独 `ser.write`** 后鼓声清晰.

**原因**: 批量发送时, 一个 wait 命令可能一次发几百字节, USB CDC 突发灌入下位机
RX buffer (2048 字节). 但下位机 `process_uart` (主循环) 与 `nes_render` (timer0 ISR
22050Hz) 共享 CPU, 突发数据来不及消费 → RX buffer 堆积 → **后续字节覆盖前面,
$4011 只收到最后一个值, 中间 PCM 字节丢失** → 鼓声欠采样沙哑.

每字节一发虽然 `ser.write` 调用次数多 (USB CDC 驱动会自动合包), 但给下位机充分时间
在两次 write 之间消费, 每个 `$4011` 字节都被应用 → 鼓声清晰.

**用户观察对比** (定位这个 bug 的关键线索):
- 批量版: 播放顺畅无卡顿 + 鼓声沙哑 = 字节没发够 (被覆盖)
- 每字节版: 略有卡顿 + 鼓声清晰 = 字节全部应用 (CDC/MCU 负载重但正确)

### 4.5 Dry-run 验证

```
feeblemask.vgm: 316 次 0x95 PLAY → 展开 404285 次 $4011 写入 ✓
ygo10.vgm:      422 次 0x95 PLAY → 9 sounds 全部正确触发 ✓
```

实测: PCM 鼓声清晰 (每字节一发是关键).

## 5. 早期调试记录 (NES APU trigger / $4015)

移植 libvgm 时照搬了它的两个 bug, 导致大量 NES 曲目无声:

**Bug A — 全通道无声 (Kirby 16 Crane Fever 等)**:
某些 VGM 文件**完全不写 $4015 status 寄存器**. libvgm 在 `device_reset_nesapu`
(line 901-902) 自动发 `$4015=0x00` 再 `$4015=0x0F` enable sq1/sq2/tri/noise,
我们的 `nes_init` 没做这个默认 enable → 通道全 disabled → 全曲无声.
修复: `nes_init` 末尾默认 enable sq1/sq2/tri/noise (DMC 不默认 enable).

**Bug B — noise 单通道无声 (Kirby 15 Cloud Level 等)**:
trigger 寄存器 ($4003/$4007/$400B/$400F) 写入时, libvgm 和我们都加了
`if (enabled)` 检查 — 但 NES 硬件文档明确: **length counter 加载独立于 $4015 enable**.
某些 VGM (如 Kirby 15) 的 $400F trigger 早于 $4015 enable, trigger 时 enabled=0
→ vbl_length 不设置 → 即使之后 enable 也无 length → 永久静音.
修复: square/triangle/noise trigger 移除 `if(enabled)` 检查, 总是加载 vbl_length.

**诊断方法**: dump VGM 命令流对比正常曲 (14) 和故障曲 (15/16), 发现 16 缺 $4015,
15 的 trigger 早于 $4015. 对照 libvgm `nes_apu.c` 源码找到 `device_reset` 的自动
enable 机制 (line 901-902). **教训: 移植时不能只看 update 函数, init/reset 函数
的隐式行为 (默认值、自动初始化) 同样关键, libvgm 把它藏在 device_reset 里容易漏**.

## 6. DMC 采样下发: 预存/流式混合策略

**核心约束**: MCU `nes_dmc_buf` 固定 16KB, 对应 NES CPU memory $C000-$FFFF.
但部分 VGM (如 Gimmick) 的 0xC2 块总量可达几十 KB 到几百 KB, 远超 16KB.

**自动选择模式** (vgm_player.py 按 0xC2 块总字节数判断):

| 总大小 | 模式 | 行为 |
|--------|------|------|
| ≤ 16KB | **预存** | 开播前一次性发完所有 0xC2 块, 主循环遇 0x67 直接跳过 |
| > 16KB | **流式** | 主循环遇 0x67 0xC2 实时分片下发 0xB6 到 MCU |

**实测覆盖** (vgm/nes/ 全目录扫描):
- 预存: Kirby 全套 (4K)、SMB3 全套 (4-8K)、Contra 全套 (16K)、Gimmick 08/10/14 (≤8K)
- 流式: Gimmick 大部分曲目 (20K~288K)、Gimmick 06/09/13/16/20 (20-36K)

**同地址覆盖语义**: VGM 的 0xC2 块按时间顺序写, 后写覆盖先写 — 符合真实 NES 语义.
预存按出现顺序逐块下发即自然实现 "后到的覆盖先到的"; 流式在主循环时间点下发, 时序更精确.

## 7. 被证伪的假设清单 (避免重复踩坑)

1. ❌ "feeblemask 不用 DMC/DAC" — 错, 用 DAC stream 走 `0x90-0x95`
2. ❌ "只统计 0xB4 就能判断 NES 用了什么" — 错, DAC stream 不走 0xB4
3. ❌ "批量发送更高效更好" — 错, 突发会导致下位机 buffer 堆积丢字节
4. ❌ "sample_rate 不匹配 (44100 vs 22050) 导致 bass" — 错, NES DAC 是保持型,
   2:1 oversampling 不影响音高, 真正原因是批量发送丢字节

## 8. 教训

1. **VGM 解析必须用完整命令表**. 不能只看部分命令就下结论. libvgm 命令表已固化到
   `docs/VGM_COMMAND_TABLE_libvgm.md`, 审计器在 `tools/vgm_cmd_audit.py`.

2. **DAC stream 的 PCM 字节必须每字节单独发**. 批量看似高效, 实际让下位机来不及
   消费, 字节被覆盖. 这是 USB CDC + 单核 MCU 的固有限制.

3. **用户观察对比是定位 bug 的金矿**. "顺畅但沙哑" vs "卡顿但清晰" 直接指向
   发送量问题, 比任何理论分析都快.

4. **Deflemask NES 的 DAC 是 7-bit 直写模式**, 不是 DMC 的 1-bit delta. nes.c case
   0x11 直接 `vol = val & 0x7F; output = vol - 64` 就是正确实现, 不需要 DMC 引擎参与.

5. **移植 libvgm 时 init/reset 的隐式行为容易漏**. device_reset_nesapu 自动发
   `$4015=0x0F` enable 通道, 不看源码根本不知道.

## 9. 当前状态与遗留问题

- ✅ 5 通道 (方波/三角/噪声/DMC) 完整, 对齐 libvgm
- ✅ Deflemask DAC stream (0x90-0x95) 支持, PCM 鼓声清晰
- ✅ PAL/NTSC 双时钟, 预存/流式混合策略
- ⚠️ **遗留**: 启用 DAC stream 后**播放非常不稳定** (节奏/卡顿), 待排查.
  怀疑每字节 `ser.write` 的 Python 端开销让上位机 budget 算法失准.

## 10. 关键文件路径速查

| 文件 | 作用 |
|------|------|
| `STC32G144K246/usb_cdc_test/src/nes.c` | NES APU 仿真核心 (5 通道) |
| `STC32G144K246/usb_cdc_test/src/nes.h` | NES 接口 + 常量 |
| `STC32G144K246/usb_cdc_test/tools/vgm_player.py` | VGM 播放 (含 DAC stream) |
| `STC32G144K246/usb_cdc_test/tools/vgm_cmd_audit.py` | 命令审计器 (完整命令表) |
| `STC32G144K246/usb_cdc_test/tools/nes_reg_stats.py` | NES 寄存器分布统计 |
| `docs/VGM_COMMAND_TABLE_libvgm.md` | libvgm 完整命令表参考 |
| `Reference_Project/vgm_libs/libvgm-master/emu/cores/nes_apu.c` | libvgm NES 参考 |
| `Reference_Project/vgm_libs/libvgm-master/emu/dac_control.c` | libvgm DAC stream 引擎参考 |

## 11. VGM 协议命令 (NES 相关, 完整表见 docs/VGM_COMMAND_TABLE_libvgm.md)

| 前缀 | 含义 | 格式 |
|------|------|------|
| 0xB4 | NES 寄存器写 | `[0xB4][reg][data]` (reg & 0x7F, bit7=chipID) |
| 0xB5 | NES 时钟下发 | `[0xB5][clk0..3]` (LE u32, NTSC=1789773/PAL=1662607) |
| 0xB6 | NES DMC 采样块 | `[0xB6][addr_lo][addr_hi][len≤32][data...]` |
| 0x67 type=0xC2 | NES CPU RAM write | `[0x67][0x66][0xC2][size:4][addr:2][data...]` |
| 0x67 type=0x00~0x3F | PCM bank (DAC stream) | `[0x67][0x66][type][size:4][data...]` |
| 0x90 | DAC stream Setup | `[0x90][streamID][chipType\|chipID][cmdHi][cmdLo]` |
| 0x91 | DAC stream SetData | `[0x91][streamID][bankID][stepSize][stepBase]` |
| 0x92 | DAC stream SetFreq | `[0x92][streamID][freq:4 LE]` |
| 0x93 | DAC stream Play (loc) | `[0x93][streamID][startOfs:4][pbMode][soundLen:4]` |
| 0x94 | DAC stream Stop | `[0x94][streamID]` |
| 0x95 | DAC stream Play (ID) | `[0x95][streamID][sndID:2 LE][flags]` |

## 12. 产物

- `STC32G144K246/usb_cdc_test/tools/vgm_player.py` (含 DAC stream 实现)
- `STC32G144K246/usb_cdc_test/tools/vgm_cmd_audit.py` (命令审计器)
- `STC32G144K246/usb_cdc_test/tools/nes_reg_stats.py` (寄存器统计)
- `docs/VGM_COMMAND_TABLE_libvgm.md` (libvgm 命令表参考)
- 源码包: `STC32G144K246_src_20260622_224347.zip`
