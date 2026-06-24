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

### 3.1 音高计算 (精确, 8.8 定点)

writeReg 时算 **u16 8.8 定点** step, render 里只做加法:
```
step = fnum × 2^blk × YM_STEP_CONST × ml / 2   (结果 u16)
YM_STEP_CONST = 3579545 × 64 × 256 / (72 × 262144 × 22050)
render: pos = (pos + step) & 0xFFFF; idx = (pos >> 8) & 0x3F   (8.8, 一个周期=64×256=16384)
ISR: 22050Hz
```

**实测音高高一个八度**: blk 减 1 修正 (频率 ÷2). 不能动 step (会导致节奏错乱).

> ⚠️ **2026-06-25 勘误**: 本节旧版误写"u32 16.16 定点 / ×65536 / pos>>16",
> 实际下位机 (ym2413.c:122-123,237,577) 是 **u16 8.8 定点 / ×256 / pos>>8**.
> 这个错误描述曾导致 fw_real_sim.py 用错定点格式, 频率高 2.255× (见第 9 节).

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

WS=0: 正弦 (`ym_sin`), WS=1: 半正弦 (`ym_halfsin`).

> ⚠️ **2026-06-25 发现 bug**: 下位机 `ym_halfsin[64]` 负半周用了**镜像正值**
> (取绝对值), 但 emu2413.c:383-387 的 halfsin 负半周是**静音** (`0xfff`→输出0).
> 镜像正值导致 carrier 后半周本该静音却输出正值 → 直流偏置 + 失真.
> **修复**: 下位机 halfsin 后半周改 0 (待同步, 见第 9 节).
> 旧描述"产生八度叠加感"是误判 (实际是失真).

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

## 5. 当前状态 (2026-06-24, 5鼓声实现完成)

### 旋律
- ✅ 寄存器完整兼容 YM2413 (ch0-5, 6通道渲染)
- ✅ 音高正确 (blk-1 修正)
- ✅ 包络对齐 emu2413 (AR/DR/RR 三表 + EG语义 + key_on/env_tick修正)
- ✅ 音量正常 (car.tl 映射修正)
- ⚠️ **ISR 性能瓶颈: 6通道同发偶尔卡死, 是当前优化重点**
- ⚠️ ch6-8 不走旋律渲染 (留给鼓声/性能余量)

### 鼓声 (单 op 简化路径)
- ✅ BD: sin 100Hz, vol=16, ~20ms
- ✅ TOM: sin 214Hz (ml=5), vol=8, ~20ms
- ✅ HH: noise 334Hz, vol=2, ~65ms
- ✅ CYM: noise 334Hz, vol=2, ~360ms
- ⚠️ SD: noise 25Hz, vol=8, ~40ms (单op; 真2op听感好但卡ISR)
- ✅ 边沿触发 (reg 0x0E bit 0→1)
- ✅ oneshot (衰减完自动清除, 不占CPU)

### 性能现状
- ISR 22050Hz, 旋律只渲染 ch0-5 (6通道)
- 鼓声单 op 简化路径 (只有 active 时才有开销)
- **6通道同发仍偶尔卡死**, FM 渲染优化是下一步重点

### PC 验证工具
- `tools/ym2413_wav_gen.py`: 忠实 emu2413 移植 + V3 调参核心
- `tools/fw_real_sim.py`: 严格 1:1 下位机旋律仿真
- `tools/drum_fw_sim.py`: 鼓声 PC 仿真 (参数固化)

## 5.1 2026-06-25 包络+反馈重大修复 (拨奏类乐器一并修复)

### 发现的 bug
1. **fw_real_sim.py 一直没和下位机同步** — 仿真器用 16.16 定点(49716Hz),
   下位机是 8.8 定点(22050Hz), 频率高 2.255× (听感高八度+2半音). 已修.
2. **halfsin 负半周镜像 vs 静音** — 旧版镜像正值是 bug, emu 是静音. 已修.
3. **包络形态错** — fw 线性 level 衰减, emu 指数衰减, 纯改速度无法拟合.
4. **RELEASE 速率映射错** — EG=0 的 release 应更快.
5. **过反馈** — 反馈占周期 fw 15% vs emu 0.66% (22.9×).

### 修复方案 (已同步下位机 commit 0bcd705, 编译通过)
- **sus_hold[32] / rel_hold[32] 指数衰减查表**: SUSTAIN/RELEASE 用查表+计数器
  模拟指数衰减 (纯查表无除法, STC32 可跑). tau≈97ms (scale=0.44 实测对齐 emu).
- **FB+4 移位**: `fb_val = ch_out >> (fb+4)` 压低反馈环路, 反馈占周期 15%→0.78%.
- **DR_TAB/RR_TAB 4~10 档改快 2.2×**.
- **halfsin 后半周改静音**.

### 意外收益: 拨奏类乐器一并修复
sus_hold/rel_hold + FB+4 是**通用机制**, 不止修了 harpsichord, 还一并修复了
所有「带反馈 + 持续衰减」的拨奏类乐器 (实机验证):
- ✅ Guitar (吉他), Piano (钢琴), Vibraphone (颤音琴), Harpsichord (拨弦键琴)
- 原因: 这些乐器共用 EG=0 (non-sustaining) + 反馈, 旧的线性衰减+过反馈让它们
  全部失真, 新机制一次性解决.

### 仍待调
- flute 等吹奏类: AR/DR 可能偏慢 (sus_hold 单一 tau, 多乐器共用)
- sus_hold 可能需按 RR 档位缩放 (不同乐器不同 tau)
- 详细调试记录见 YM2413_HANDOFF.md

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

## 9. 2026-06-25 音色准确度调试 (harpsichord 过反馈)

### 9.1 触发: harpsichord 听感"过反馈音质差"

用户反馈 inst 11 (Harpsichord) 过反馈导致音质差, 要求对照 emu2413 对齐.
**正确流程**: 先 PC 仿真 (fw_real_sim.py) 对照 emu2413 → 定位偏差 → 只改表/参数
→ 同步仿真验证 → 再改下位机.

### 9.2 发现1: fw_real_sim.py 一直没和下位机同步 (万恶之源!)

这是本次最重大发现, **颠覆了之前所有仿真结论**:

| | 仿真器 (修复前) | 下位机 (ym2413.c 实际) |
|---|---|---|
| 定点 | 16.16 (注释写的) | **8.8** |
| pos 类型 | u32 (`&0xFFFFFFFF`) | **u16** |
| idx 取法 | `pos>>16 & 0x3F` | **`pos>>8 & 0x3F`** |
| step 常数 | `×65536` | **`×256`** |
| 渲染采样率 | `INTERNAL_RATE=49716` | **22050** |

**后果**: 仿真器频率 = 下位机 × (49716/22050) = **2.255×**
- harpsichord 440Hz: 仿真器输出 **992Hz** (听感高八度+2半音), 下位机实际 **438.7Hz** (正确!)
- 用户听感"高八度+2半音"直接定位, 比所有数值分析都快
- **之前关于"过反馈""halfsin"的扫描结论全部建立在错误频率上, 不可信**

**修复** (commit 16839d4, 仅 fw_real_sim.py):
```
FW_STEP_CONST: ×65536 → ×256
FW_ISR_RATE = 22050 (新增)
fw_calc_step: 返回 & 0xFFFF (u16)
fw_render_fm: pos & 0xFFFF, idx = pos>>8 (8.8)
render_fw_real: 用 FW_ISR_RATE 而非 INTERNAL_RATE
save_fw_wav: 新增, 按 22050 保存 (save_wav 假设 49716 会错)
```
**验证**: harpsichord 440Hz → 仿真器 **441.0Hz**, emu 440.0Hz, 比例 **1.002** ✓

### 9.3 发现2: halfsin 负半周镜像 vs 静音

AGENTS.md 和本文档 3.4 旧版都记录 "halfsin 负半周镜像 (取绝对值)", 当成下位机
真实限制. **对照 emu2413.c:383-387 发现是 bug**:
- emu: halfsin 后半周 = `0xfff` (静音)
- 下位机: halfsin 后半周 = 镜像正值 (全正)
- **影响**: carrier 用 halfsin (car_ws=1) 时, 后半周本该静音却输出正值 →
  直流偏置 + 谐波污染 → 听起来像"过反馈失真"

仿真修复: `FW_HALFSIN` 后半周改 0. **下位机 ym_halfsin 表待同步** (ym2413.c:28-33).

### 9.4 发现3: volume 映射 bug (仿真器)

fw_real_sim.py 旧版 `car.tl = volume>>1`, volume=0 → tl=0 → 输出恒为0 (静音).
对照下位机 ym2413.c:500-502: `vol=(15-reg_vol)<<2; car.tl=vol>>1`.
修复: `car.tl = (60-volume)>>1` (volume 语义对齐 emu: 0=最大音量).

### 9.5 被否决的方案: mod.tl 映射翻转

试过把 `mod.tl = 31-(tl_raw>>1)` 改成 `tl_raw>>1` (让 TL=3 时 mod 衰减增大).
反馈占周期从 25%→1.6% 接近 emu 1.2%, **但听感音高变了** (FM 边带偏移).
**否决**: 影响所有乐器的 mod 衰减特性, 不是纯调参, 改动过大.

### 9.6 当前状态

- ✅ 仿真器频率对齐 (441 vs 440Hz)
- ✅ halfsin mute 已在仿真层修复
- ✅ volume 映射已修
- ⚠️ **下位机未动** (halfsin 表 + 可能的反馈调整待仿真听感确认后才改)
- ⏳ 待听 `wav_fw_sync/harp_fw.wav` vs `harp_emu.wav` 确认音色

### 9.7 调参边界澄清 (用户强调)

- **可以改**: 表的数值 (halfsin/AR/DR/RR/ml_table), 简单参数, 简单运算规则
- **不能改**: 架构 (round-robin/env_tick 逻辑/输出公式/相位/ml/结构体)
- **PC 实验可以临时改任何东西** (如 patch 的 FB 值), 验证后再决定下位机怎么改
- **mod.tl 这种全局映射要慎改**: 会动 FM 边带 → 音高变化, 不算"纯调参"

## 10. 被证伪的假设 (2026-06-25 补充)

4. ❌ "fw_real_sim.py 已和下位机 1:1 同步" — **错!** 仿真器用了 16.16 定点
   (下位机是 8.8), 频率高 2.255×. 这是文档自身的错误描述 (旧 3.1 节) 传导到仿真的.
5. ❌ "halfsin 负半周取绝对值产生八度叠加感" — **错!** 那是失真, emu 是静音.
6. ❌ "harpsichord 过反馈" — **部分错**. 频率错 (992Hz) + halfsin 镜像双重误导,
   频率对齐后需重新判断反馈是否真的过强.

## 11. 教训 (2026-06-25 补充)

7. **文档描述必须和代码一致**. 旧 3.1 节写"16.16 定点"但代码是 8.8, 这个文档 bug
   传导到仿真器, 让所有调参白做. **改代码时同步改文档, 读文档时对照代码核实**.

8. **听感比数值分析快且准**. 用户听出"高八度+2半音"秒级定位频率 bug,
   而我做了 5 轮仿真扫描 (反馈/halfsin/mod.tl) 都没发现, 因为假设仿真器是对的.
   **仿真器本身不可信时, 数值结论全是假的**.

9. **"先修仿真器同步"是第一优先级**. 任何调参前必须确认仿真器 1:1 下位机,
   否则就是"在错误的地图上找路". 频率/定点格式/采样率是最容易不同步的地方.
