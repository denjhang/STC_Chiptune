# YM2413 (OPLL) FM 合成芯片集成进度 (2026-06-24 更新)

Yamaha YM2413 (OPLL) 是第八个集成进 STC32G144K 固件的音源芯片
(继 AY8910/SN76489/SCC/NES APU/GB DMG/NES FDS 之后).

总览状态见 `README.md`.

## 0. 背景: YM2413 是什么

YM2413 是雅马哈 1983 年的 **2-operator FM 合成芯片 (OPLL)**:
- 9 通道旋律 + 5 鼓 (rhythm mode)
- 每 operator: phase generator + envelope generator (AR/DR/SL/RR)
- 16 内置音色 + 1 用户音色
- AM/PM LFO (颤音/震音)
- 用于 MSX, Sega Master System, ColecoVision 等

**和 FDS 的区别**: FDS 是频率调制 (查表+加法), YM2413 是**真正的雅马哈式 FM**
(sin 相位调制). 但本实现用**极简线性 FM** 替代, 不做 dB 域 log/exp.

## 1. 为什么不能直接移植 emu2413.c

libvgm 的 `emu2413.c` (1629 行) 完整移植到 C251 后:
- **卡死** — 18 operator × 60+ mul/sample 在 ISR 里太慢, 主循环饿死
- **tll_table[128][64][4] = 128KB** — 远超 xdata 64KB
- 需要 rate converter (sinc/blackman/浮点) — C251 不支持

**结论**: 必须用极简 FM 核心.

## 2. 极简 FM 方案 (参考 STC32G12K128 fm.c)

**核心设计** (参考项目 `STC32G12K128/fm.c`):
- **64 点 s8 波形表** (-31..31), 不是 1024 点 log 域
- **线性 FM**: OP1 输出直接加到 OP2 的相位索引 (`idx += ch_out`)
- **ADSR 查表**: `ym_env_cnt[16]` 速度表, round-robin 每 16 tick 更新一个通道
- **跳过静音通道**: `if (!key_on && env==0) continue`

**寄存器兼容** (关键): 完整 YM2413 寄存器解析, 解码后映射到极简参数:
- `0x00-0x07`: 用户音色 → mod_ml/car_ml/TL/FB/AR/DR/SL/RR/EG/WS
- `0x10-0x18`: f-number 低 8 位
- `0x20-0x28`: fnum-hi/block/sus/key-on
- `0x30-0x38`: instrument/volume
- `0x0E`: rhythm mode + drum key-on

## 3. 实现细节

### 3.1 音高计算 (精确)

writeReg 时算 u32 16.16 定点 step, render 里只做加法:
```
step = fnum × 2^blk × YM_STEP_CONST × ml / 2
YM_STEP_CONST = 3579545 × 64 × 65536 / (72 × 262144 × 22050)
render: pos += step; idx = (pos >> 16) & 0x3F
```

**实测音高高一个八度**: blk 减 1 修正 (频率 ÷2). 不能动 step (会导致节奏错乱).

### 3.2 ADSR 行为对齐 YM2413 (2026-06-24 修正)

**EG 语义** (对齐 emu2413 get_parameter_rate, 之前版本写反了):
| 行为 | YM2413 规格 | 极简实现 |
|------|------------|----------|
| Sustain (**EG=1**) | **保持 SL** (sustaining) | step=0 → env_tick 不降 |
| Sustain (**EG=0**) | **继续降到 0** (non-sustaining) | step=rel → 继续减 level |
| Release (sus=1) | 固定速率 5 | env_step=ym_rr_tab[5] |
| Release (sus=0) | 速率 RR | env_step=rel |
| Attack (AR=0) | 不启动 | env_state=0 |
| Attack (AR≥7) | 瞬间到顶 | atk≤2 → level=31 直接 decay |

**AR/DR/RR 三张表** (commit 93f7cb6, 替换旧 ym_env_cnt 单表):
- `ym_ar_tab[16]` = `[0,116,58,29,14,7,4,2,1,1,1,1,1,1,1,1]`
- `ym_dr_tab[16]` = `[0,255,255,175,88,44,22,11,6,3,1,1,1,1,1,1]`
- `ym_rr_tab[16]` = `[0,255,255,255,170,85,42,21,11,5,3,1,1,1,1,1]`
- 反推自 emu2413 attack/decay/release 全程时间 (round-robin 16采样/tick)

**env_tick 加法计数器** (commit 1f45584):
- 旧: `cnt >= step ? cnt -= step : cnt=250+走包络` (减法, reset 250 有累积误差)
- 新: `cnt < step ? cnt++ : cnt=0+走包络` (加法, step 真正代表周期)

**key_on env_cnt=0** (commit 1f45584): 消除 attack 启动延迟 (旧值 250 导致延迟 4000 采样).

**car.tl 映射** (commit 93bc777): `tl = vol>>1` (之前 `31-vol>>1` 写反, 导致最大音量时输出极小).

**sus_flag 只影响 carrier** (对齐 emu2413 set_sus_flag line 672:
modulator 的 type&1==0, sus_flag 永远不设).

### 3.3 音色 dump 解码 (dumpToPatch)

完全对齐 emu2413 `EOPLL_dumpToPatch` (line 1442):
```
dump[0]: mod AM(7) PM(6) EG(5) KR(4) ML(3-0)
dump[1]: car AM(7) PM(6) EG(5) KR(4) ML(3-0)
dump[2]: mod KL(7-6) TL(5-0)
dump[3]: car KL(7-6) car_WS(4) mod_WS(3) FB(2-0)
dump[4]: mod AR(7-4) DR(3-0)
dump[5]: car AR(7-4) DR(3-0)
dump[6]: mod SL(7-4) RR(3-0)
dump[7]: car SL(7-4) RR(3-0)
```

### 3.4 WS 波形选择

WS=0: 正弦 (`ym_sin`), WS=1: 半正弦/abssin (`ym_halfsin`, 负半周取绝对值).
产生八度叠加感.

### 3.5 鼓声方案 (单 op 简化路径, commit 7ff3348)

鼓声用独立 YM_DRUM 结构 (单 op), 不走 2-op FM, 开销约为旋律一半。
oneshot: 边沿触发 (reg 0x0E bit 0→1), 每采样 tick 包络, 衰减完自动清除。

| 鼓声 | 波形 | 频率 | env_step | 衰减时间 | 状态 |
|------|------|------|----------|---------|------|
| BD | sin | 100Hz | 16 | ~10ms | ⚠️ 音量/长度待调 |
| TOM | sin | 214Hz (ml=5) | 16 | ~10ms | ⚠️ 待调 |
| SD | noise | 25Hz | 28 | ~20ms | ⚠️ 单op (真2op听感好但卡ISR) |
| HH | noise | 755Hz | 46 | ~29ms | ✅ 正常 |
| CYM | noise | 755Hz | 255 | ~150ms | ✅ 正常 |

- 噪声表: `ym_noise[64]` (64 点假随机 ±31)
- 边沿触发: `ym_prev_drum_bits` 检测 reg 0x0E bit 0→1
- 渲染: `ym_render_drum(idx)`, 单 op 查表×level, 无 FM 调制
- 旋律只渲染 ch0-5 (6通道), 为鼓声腾 ISR 余量
- PC 工具: `tools/drum_fw_sim.py`

**SD 真 2-op 记录** (commit 65ceab9, 已废弃但听感最佳):
- SD 走 ch6 的 ym_render_fm (真 2-op FM): mod=noise(25Hz,FB=2) 调制 car=sin(240Hz)
- 双包络: noise 快衰减先消失, sine 慢尾巴 (对齐 PC sd_fm_swap_n50)
- **听感非常好**, 但 rhythm mode 时相当于 7 通道 (6旋律+SD), ISR 偶尔卡死
- 简化 2-op (data区独立变量) 听感不如真 2-op
- 未来优化 ISR 性能后可恢复真 2-op SD

### 3.6 资源占用

- xdata: ~37KB (含 FM 结构 + sin 表)
- HEX: ~66KB
- 0 ERROR

## 4. 调试记录

### 4.1 完整 emu2413 移植 → 卡死

第一版完整移植 emu2413.c (18 operator, 60+ mul/sample, tll_table 128KB).
编译通过但**播放时上位机卡死, 下位无声**. 根因: ISR 太慢导致主循环饿死.

### 4.2 极简 FM 核心 → 能响

参考 STC32G12K128 fm.c 重写:
- 64 点 s8 表 + 线性 FM + ADSR 查表
- 寄存器完整兼容 YM2413
- HEX 81KB → 64KB

### 4.3 音高高一个八度

step 公式正确, 但整体高一个八度.
**根因**: blk 直接用, 但 64 点表和 1024 点表的精度差异导致.
**修复**: ym_update_step 里 `if (blk > 0) blk--;`.
**注意**: 不能动 step 本身 (/2 会导致节奏错乱, 因 step 同时影响相位累积和节奏).

### 4.4 包络行为对齐

对照 YM2413 规格书 + emu2413 源码, 修复 6 个 ADSR 行为差异
(EG type / sus_flag / AR=0,15 / release 速率).

## 5. 当前状态 (2026-06-24, commit 93bc777, 实测最佳)

- ✅ 寄存器完整兼容 YM2413
- ✅ 音高完全正确 (blk-1 修正)
- ✅ 音色接近 (15 个内置乐器, 实机听感最接近 emu2413)
- ✅ ADSR 行为对齐 (EG 语义修正: EG=1 保持 / EG=0 继续降)
- ✅ 音量正常 (car.tl 映射修正, 最大音量满输出)
- ✅ attack 响应接近弹奏乐器 (AR≥7 瞬间到顶)
- ✅ WS 波形选择 (sin / halfsin)
- ⚠️ **鼓声未实现** (rhythm mode ch6/7/8 跳过)
- ⚠️ EG=0 音色 sustain 下降斜率比 emu 稍快 (可继续微调 DR 表)

### PC 验证工具
- `tools/ym2413_wav_gen.py`: 忠实 emu2413 移植 (render_emu2413) + V3 s8 调参核心
- `tools/fw_real_sim.py`: **严格 1:1 下位机 PC 仿真** (render_fw_real), 改下位机前必须在此验证

### 正确流程 (必须遵守)
1. 先在 PC 仿真验证 (fw_real_sim.py), 对照 emu2413 逐个乐器看 level 曲线
2. fw_real_sim.py 必须和下位机 1:1 同步
3. 只改数值/表, 不改架构 (round-robin/env_tick 逻辑/输出公式/波形/相位/ml/结构体)
4. PC 验证通过再改下位机, 编译通过再烧录

## 6. 被证伪的假设

1. ❌ "完整 emu2413.c 能直接移植到 C251" — 错, 128KB tll_table + ISR 太慢
2. ❌ "step /2 能降八度" — 错, 破坏节奏. 用 blk-1 才对
3. ❌ "sus_flag 同时影响 mod 和 car" — 错, 只影响 carrier (type&1 判断)

## 7. 教训

1. **极简不是偷工, 是换实现方式**. 64 点 s8 线性 FM 能达到"音色大体接近",
   不需要完整的 dB 域 log/exp 运算. 参考 12k128 fm.c 的设计.

2. **音高修正要改源头 (blk), 不是改结果 (step)**. step 同时影响相位和节奏,
   改 step 会连锁破坏节奏.

3. **寄存器兼容是底线**. FM 核心可以极简, 但寄存器解析必须 100% 兼容,
   否则 VGM 文件无法正确播放.

4. **PC 仿真必须和下位机 1:1 同步** (2026-06-24 教训).
   早期 fw_real_sim.py 没同步下位机的 env_tick/key_on/EG 逻辑, 导致 PC 验证
   结果不可信, 反复试错浪费大量时间. 改下位机任何东西, 仿真必须同步改.

5. **"只改表"包括数值 bug** (2026-06-24 教训). EG 语义写反、car.tl 映射写反、
   env_cnt 初始值荒谬, 这些都是"改数值"能修的, 不要因为"只改表"就不碰.
   但 round-robin/env_tick 逻辑/输出公式/波形/相位 这些是架构, 不能动.

6. **不要在 PC 上用 emu 精度假装验证下位机** (2026-06-24 教训).
   之前的 render_fm_v3/render_fm_v3_fw 偷用了 emu 的 ±127 波形/19-bit 相位/
   LEVEL_GAIN 查表/LFO, 生成的 WAV 和 emu 当然几乎相同, 但对下位机毫无意义.
   真正的验证必须用 render_fw_real (忠实下位机限制).

## 8. 关键文件

| 文件 | 作用 |
|------|------|
| `src/ym2413.h` | 接口 |
| `src/ym2413.c` | 极简 FM 核心 + 寄存器解析 (s8 核心, AR/DR/RR 三表) |
| `tools/ym2413_wav_gen.py` | PC: 忠实 emu2413 移植 + V3 s8 调参核心 |
| `tools/fw_real_sim.py` | PC: **严格 1:1 下位机仿真**, 改下位机前必须在此验证 |
| `vgm/opll/opldrv/` | naruto 的 YM2413 测试曲 (Patch Slide Test) |
| `vgm/opll/msxfan/` | MSX Fan 杂志 YM2413 音乐 |
| `STC32G12K128/fm.c` | 极简 FM 参考实现 (ArduinoUnoTinyFmKeyboard 移植) |
