# NES APU 集成进度 (2026-06-22)

NES APU (Ricoh 2A03) 是第五个集成进 STC32G144K 固件的音源。本文档记录 NES
从初版集成到 Deflemask DAC stream 支持的完整调试历程, 与
`GB_INTEGRATION_STATUS.md` 并列, 互不混入.

总览状态见 `README.md`, libvgm 完整命令表见 `docs/VGM_COMMAND_TABLE_libvgm.md`.

## 0. 背景: 为什么 NES PCM 路径特别多

NES APU (Ricoh 2A03, 1983) 是所有已集成音源里**PCM/DMC 路径最复杂**的.
其他芯片 (AY8910/SN76489/GB DMG/SCC) 几乎都是单一寄存器写路径, 唯独 NES
有 **5 条** PCM/DMC 命令入口. 这不是 2A03 设计超前, 而是**硬件双机制 +
VGM 格式 20 年演化 + ripper 各自为政**三者叠加的结果.

### 0.1 硬件层面只有两种 PCM 机制

NES 产生 PCM 声音, 硬件上只有两种方式:

1. **DMC 通道 (硬件 DMA 引擎)** — 从 CPU 内存 ($C000-$FFFF) 读采样, 按设定频率
   ($4010), 1-bit delta 解调 (bit=1 vol+=2, bit=0 vol-=2), 输出到 7-bit DAC
2. **$4011 直写 (软件)** — CPU 直接写 7-bit 值到 DAC 寄存器, 绕过 DMC 引擎

所有 VGM 命令路径都是这两种硬件机制的"软件包装".

### 0.2 五条 VGM 路径的真实分工

| VGM 路径 | 硬件机制 | 谁产生的 | 为什么存在 |
|----------|----------|----------|-----------|
| `0x67 type=0xC2` | DMC (硬件引擎) | NSF ripper (Festalon/nestrong) | **最古老**. NSF 文件本身在 NES 内存里跑, ripper 直接 dump 内存里的 DMC 采样块 |
| `0x68 type=0x07` | DMC (硬件引擎) | 同上, 但 ripper 想优化文件大小 | 把重复采样放 PCM bank, 用 0x68 动态拷贝到 RAM (省空间). up-nes 的 bank 23168 字节复用填满 16KB 就是这个思路 |
| `0xB4 0x11` 直写 | $4011 直写 | 极少数 ripper | 直接 dump 每个采样点, 最暴力但最忠实 (文件巨大) |
| `0x90-0x95` DAC stream | $4011 直写 | **Deflemask** (现代 tracker) | Deflemask 用软件混音器生成 PCM, 不走 DMC 硬件引擎, 因为它要支持任意采样率 + 多采样叠加, DMC 引擎做不到 |
| `0x80-0x8F` | $4011 直写 | YM2612 沿用 | 同样的 DAC stream 机制, 本来给 YM2612 设计, NES 借用 |

### 0.3 为什么这么多兔子洞

三个原因叠加:

**① NES 的 DMC 通道设计很"硬核"**:
- 只支持 1-bit delta 编码 (采样必须预处理成 delta 格式)
- 采样率固定 16 档 ($4010 低 4 位查表)
- 只能从 CPU 内存读 (不能直接流式输入)
- 容量受限于 RAM 寻址 (16KB 窗口)

导致很多音乐软件不愿用 DMC 硬件引擎, 转而用 $4011 直写 (更灵活). Deflemask 典型.

**② VGM 格式是"事后"记录, 不是"为 NES 设计"**:
VGM 最初为 Sega Mega Drive (YM2612) 设计, 后来陆续加芯片支持. 每次加新芯片,
ripper 作者**复用现有机制**或**发明新命令**, 没有统一规划:
- NSF ripper 用了 `0x67` data block (已有机制)
- Deflemask 用了 `0x90-0x95` DAC stream (给 YM2612 发明的, NES 借用)
- 有人想省空间发明了 `0x68` PCM RAM write

**③ libvgm 必须兼容所有历史 ripper**:
libvgm 作为通用播放器, 不能挑食 — 所有 ripper 产生的 VGM 都得能播. 所以
`_CMD_INFO[0x100]` 表塞满各种命令, 每条路径都得支持. 这就是"超多入口"的原因.

### 0.4 对比其他芯片 (为什么它们没这么多兔子洞)

| 芯片 | PCM 通道 | VGM 路径数 | 原因 |
|------|----------|-----------|------|
| AY8910 | 无 | 1 (`0xA0`) | 纯合成, 无采样播放 |
| SN76489 | 无 | 1 (`0x50`) | 同上 |
| GB DMG | 无 (CH3 是波形 RAM, 不是 PCM) | 1 (`0xB3`) | 32×4-bit 波形表, 固定长度 |
| SCC | 无 | 1 (`0xD2`) | 32×8-bit 波形表, 类似 GB |
| YM2612 | 有 DAC | 2 (`0x80-0x8F` + `0x90-0x95`) | ripper 较统一 |
| **NES APU** | **有 DMC + $4011** | **5** | **既有硬件 DMC, 又支持 $4011 直写, ripper 各玩各的** |

### 0.5 DMC 和 PCM 能否同时输出?

**能, 这是 NES 的正常用法.** 2A03 的 5 个通道**同时、独立**输出, 在 DAC 求和:
```
mix = SQ1 + SQ2 + TRI + NOISE + DMC
```
libvgm `nes_apu.c` 的 `nesapu_update` 每帧调用所有 5 个通道的 update 后累加.
feeblemask 就是典型: SQ1+SQ2+TRI+NOISE (旋律) + PCM 鼓声同时输出.

**唯一约束**: $4011 直写和 DMC 引擎**共享同一个 DAC** (都改 `vol` 值), 不能真正
"叠加"而是"抢". DMC 引擎每 bit 才改一次 vol (±2), $4011 直写立即改, 两者交替
更新同一个 vol, 输出是它们的混合轨迹. Deflemask 用 $4011 直写时通常 $4015 bit4=0
(关 DMC 引擎), 避免冲突.

### 0.6 一句话总结

> NES 的 PCM 路径多, 不是因为 2A03 设计超前, 而是因为它**同时支持硬件 DMC 和
> 软件 $4011 直写**, 再加上 VGM 格式 20 年演化中不同 ripper 各自为政, 把这两种
> 硬件机制包装出了 N 种命令组合.

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
- 采样数据来源 (三条路径, 详见 §4 和 §4.6):
  - `0x67 type=0xC2` 内联 NES RAM write (标准 DMC)
  - `0x67 type=0x07` + `0x68` PCM RAM write (从 PCM bank 拷贝)
  - `0x67 type=0x00` + `0x90-0x95` DAC stream (py 展开 `$4011` 直写, 绕过 DMC 引擎)

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

### 4.4 关键架构: 下位机 8KB PCM ring buffer + 虚拟水位流控 (最终方案)

**迭代历程** (三个版本, 前两个都失败):

| 版本 | 方案 | 问题 |
|------|------|------|
| v1 批量 | dac_tick 批量打包 192 字节/包, `0xB4 0x11 byte` 直写 $4011 | 鼓声沙哑 — USB CDC 突发灌入下位机 RX buffer (2048), process_uart 来不及消费, 字节被覆盖丢失 |
| v2 每字节 | 每字节单独 `ser.write`, 让下位机有充分时间消费 | 鼓声清晰但播放不稳定 — Python ser.write 开销 88% CPU (11025 次/秒), budget 算法追不上 |
| **v3 ring buffer** | **下位机 8KB PCM ring + 上位机批量 + 虚拟水位** | **既清晰又稳定** ✓ |

**矛盾根源**: 上位机直接控制 $4011 时序 → 批量则丢字节, 逐个则 Python 慢.
**解法**: 把时序控制权交给下位机 — 上位机只管灌 ring buffer, 下位机 render 按真实节奏消费.

**v3 架构** (参考 RPFM `ring_buf.h` + `protocol.h` BUF_LVL/STATUS_BUF_HIGH):

```
上位机 dac_tick (升采样到 22050, 虚拟水位限流, 批量 0xB8)
    ↓ USB CDC (64 字节/包)
下位机 main.c 0xB8 → nes_pcm_push(byte) → 8KB ring [head++]
                                              ↓
下位机 timer0 ISR @ 22050Hz → nes_render() → nes_pcm_pop → nes_dpcm.vol
                                              (ring 空则保持, zero-order hold)
```

**下位机改动** (nes.h / nes.c / main.c):
- `nes_pcm_ring[8192]` (xdata, 2^N 回绕), `nes_pcm_head`/`nes_pcm_tail` (data 段, volatile)
- `nes_pcm_push(byte)`: ring 满则丢弃 (保护节奏, PCM 连续流丢几字节听不出)
- `nes_render` 末尾: DMC 不 active 时 (`!nes_dpcm.active && head != tail`) pop 一个字节写 `vol`
- 新命令 `0xB8 [byte]` (2 字节): push 到 ring

**上位机改动** (vgm_player.py dac_tick):
- **升采样到 22050** (NES_RENDER_RATE): `push_acc += samples * 22050 / 44100`
  - 源字节按 `freq/render_rate` 比例推进 (零阶保持: freq=11025 → 每 2 个 push 推进 1 字节, 重复 2 次)
- **虚拟水位流控**: `virtual_level = pushed_total - elapsed*22050`
  - `> NES_PCM_WATER_HIGH (75% = 6144)` 就 break, 让下位机消费
  - 不需要下位机反馈 (EP4IN IN 方向未启用发送), 上位机自己估算
- **批量打包**: 64 字节/包 (32 个 `0xB8 byte` 命令), `ser.write` 从 11025/秒 降到 ~700/秒
- 命令从 `0xB4 0x11 byte` (3 字节) 改为 `0xB8 byte` (2 字节), **带宽省 33%**

**编译**: xdata 29414 (28.7KB / 64KB), 0 ERROR.
**实测**: feeblemask PCM 鼓声清晰 + 播放稳定 ✓

### 4.5 Dry-run 验证

```
feeblemask.vgm: 316 次 0x95 PLAY → push 887230 字节 (57.6s, 15395/s) ✓
ygo10.vgm:      422 次 0x95 PLAY → 9 sounds 全部正确触发 ✓
```

实测: PCM 鼓声清晰 + 播放稳定 (ring buffer + 虚拟水位是最终方案).

### 4.6 第三条路径: 0x68 PCM RAM write (up-nes2/5)

up-nes2-v0.613-1800.vgm / up-nes5-v0.613-dpcm.vgm 走**第三条 DMC 路径**, 既不是
标准 `0x67 type=0xC2`, 也不是 Deflemask `0x90-0x95` DAC stream:

- **`0x67 type=0x07`** — PCM data block, 数据进 PCM bank 7 (与 type=0x00 同机制,
  type 低 6 位 = bank_id)
- **`0x68 type=0x07`** — PCM RAM write, 从 bank 7 的 `dbPos` 取 `dataLen` 字节,
  写到 NES CPU RAM 的 `wrtAddr` (就是 DMC 采样数据)
- 后续 `$4010/$4012/$4013 + $4015 bit4` 标准 DMC 触发 (MCU DMC 引擎 1-bit delta)

**三条 DMC 路径对照**:

| 路径 | PCM 数据来源 | 应用方式 | 代表文件 |
|------|-------------|----------|----------|
| 1. 标准 DMC | `0x67 type=0xC2` 内联 NES RAM write | `$4015 bit4` trigger DMC 引擎 | Kirby/Gimmick |
| 2. DAC stream | `0x67 type=0x00` + `0x90-0x95` | py 展开 `$4011` 直写 (7-bit DAC) | feeblemask/ygo10 |
| 3. PCM RAM write | `0x67 type=0x07` + `0x68` | `$4015 bit4` trigger DMC 引擎 | **up-nes2/up-nes5** |

**实现** (vgm_player.py play_vgm 主循环加 0x68 分支):
- 从 `pcm_banks[type]` 的 `dbPos` 取 `dataLen` 字节
- **回绕读取** (对齐 libvgm `Cmd_PcmRamWrite` line 819-832):
  libvgm 只检查 `dbPos < size`, 不检查 `dbPos + dataLen`. up-nes 的 bank 7 仅
  23168 字节, 但 0x68 要从 dbPos=20480 读 16384 字节 (到 36864, 越界 13696).
  libvgm 直接传指针让 romWrite 读越界内存 (C++ 未定义行为), 我们用
  `(dbPos + i) % bank_size` 回绕模拟, NES DMC 不在乎具体内容.
- 用 `0xB6` 下发到 MCU `nes_dmc_buf[wrtAddr - 0xC000]` (复用 dmc_send_block)
- 下位机无需改动 (0xB6 命令早支持, DMC 引擎早完整)

**0x68 命令格式** (12 字节):
```
[0x68][0x66][type][dbPos:3 LE][wrtAddr:3 LE][dataLen:3 LE]
```
pos 消费 0x68 后, `data[pos+0]=0x66, data[pos+1]=type,
data[pos+2..4]=dbPos, data[pos+5..7]=wrtAddr, data[pos+8..10]=dataLen`.

**踩坑**: 第一次实现时偏移整体 +1 (误以为 pos 还指向 0x68), dry-run 0 字节下发.
修正后 up-nes2/5 各下发 16384 字节到 `$C000` ✓.

**0x68 dataLen==0 的特殊语义** (libvgm line 822-823):
```cpp
if (! dataLen) dataLen += 0x01000000;  // 0 → 16MB (读到 bank 末尾)
```
我们也做了同样处理.

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

**关键发现 (2026-06-23)**: 所有已测 VGM 的 DMC 块地址都在 `$C000-$E000` (12KB 范围),
**16KB buffer 足够, 不需要扩 nes_dmc_buf**. bank 切换 = 同地址覆盖 (按时序),
DMC 引擎随机地址读 `nes_dmc_buf` 不受影响.

### 6.1 流式异步发送队列 (2026-06-23, 解决切 bank 卡顿)

**问题**: 之前流式模式遇 `0x67 0xC2` 时 `dmc_send_block` **同步发整块** (4-8KB),
阻塞 budget 循环 → 切 bank 时 PCM/寄存器命令发不出去 → 节奏卡顿.

**方案** (复用 PCM ring 虚拟水位思路, 只改上位机, 不动固件):
- 遇 `0x67 0xC2` / `0x68` 时拆成 **256B chunks** 推入 `dmc_send_queue` (不阻塞)
- budget 每轮主循环从队列发 **512B** (2 chunks), 与 PCM/寄存器命令交替发送
- 播放结束清空队列剩余 (防 speed 过快没发完)

**为什么不需要扩 buffer**: 所有 DMC 地址在 12KB 窗口内, 16KB `nes_dmc_buf` 够.
bank 切换是地址覆盖, 不是 buffer 不够. 真正问题是发送时机 (同步阻塞), 不是容量.

**实测** (czy_tego 184KB):
- 发送速率 1715 B/s >> DMC 消费速率 ~400 B/s (最快 `$4010=0xF`)
- 队列不堆积, 切 bank 数据提前到位 (最短切换窗口 1.287s, 8KB/80ms 远够)
- dry-run: 184320/184320 字节 **100% 发送** ✓

## 7. 被证伪的假设清单 (避免重复踩坑)

1. ❌ "feeblemask 不用 DMC/DAC" — 错, 用 DAC stream 走 `0x90-0x95`
2. ❌ "只统计 0xB4 就能判断 NES 用了什么" — 错, DAC stream 不走 0xB4
3. ❌ "批量发送更高效更好" — 错, 突发会导致下位机 buffer 堆积丢字节
4. ❌ "sample_rate 不匹配 (44100 vs 22050) 导致 bass" — 错, NES DAC 是保持型,
   2:1 oversampling 不影响音高, 真正原因是批量发送丢字节
5. ❌ "DMC 切 bank 卡顿是 buffer 不够" — 错, 所有地址在 12KB 窗口内, 真正原因是
   上位机同步发送阻塞 budget, 异步队列解决

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
- ✅ **三条 DMC 路径全部支持**:
  - `0x67 type=0xC2` 标准 DMC (Kirby/Gimmick)
  - `0x90-0x95` Deflemask DAC stream (feeblemask/ygo10)
  - `0x68` PCM RAM write (up-nes2/up-nes5)
- ✅ PAL/NTSC 双时钟, 预存/流式混合策略
- ✅ **8KB PCM ring buffer + 虚拟水位流控** (DAC stream 鼓声清晰 + 播放稳定)
- ✅ **DMC 流式异步发送队列** (切 bank 不卡顿, czy_tego 184KB 100% 发送)
- 无已知遗留问题

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
| 0xB8 | NES PCM ring push (DAC stream) | `[0xB8][byte]` (push 到 8KB ring, render @ 22050Hz pop) |
| 0x67 type=0xC2 | NES CPU RAM write | `[0x67][0x66][0xC2][size:4][addr:2][data...]` |
| 0x67 type=0x00~0x3F | PCM bank (DAC stream / 0x68 源) | `[0x67][0x66][type][size:4][data...]` |
| 0x68 | PCM RAM write (NES type=0x07) | `[0x68][0x66][type][dbPos:3][wrtAddr:3][dataLen:3]` |
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
