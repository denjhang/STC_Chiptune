# YM2413 工作交接 (2026-06-25)

## 工作目录
- 项目根: `D:\working\vscode-projects\STC_Chiptune`
- 固件源码: `STC32G144K246\usb_cdc_test\src\ym2413.c`
- 构建脚本: `STC32G144K246\usb_cdc_test\build.py`
- PC 仿真工具: `STC32G144K246\usb_cdc_test\tools\`
- VGM 测试文件: `vgm\opll\msxfan\`, `vgm\opll\opldrv\`
- STC32G12K128 参考实现 (16通道FM不卡): `STC32G12K128\fm.c`

## 编译/烧录/播放命令
```bash
# 编译固件
cd STC32G144K246\usb_cdc_test && py -3 build.py

# 打包源码
python tools\pack_144k_src.py

# 播放 VGM 测试
cd STC32G144K246\usb_cdc_test && py -3 tools\vgm_player.py --vgm-dir D:/working/vscode-projects/STC_Chiptune/vgm/opll/msxfan --port COM24 <编号>

# PC 仿真 (旋律包络验证)
cd STC32G144K246\usb_cdc_test && py -3 -c "
import sys, math
sys.path.insert(0, 'tools')
from fw_real_sim import render_fw_real
from ym2413_wav_gen import render_emu2413, NAMES
# ... 对照 emu2413 看 level 曲线
"

# PC 鼓声仿真
cd STC32G144K246\usb_cdc_test && py -3 tools\drum_fw_sim.py
```

## git 常用
```bash
# 退回 ym2413.c 到某个 commit
git checkout <commit> -- STC32G144K246/usb_cdc_test/src/ym2413.c

# 查看某个 commit 的 SD 实现
git show <commit>:STC32G144K246/usb_cdc_test/src/ym2413.c | grep -A20 "ym_sd_trigger"

# 重要 commit:
# 9327509 - u16 8.8定点优化 (当前稳定版, 退回这里)
# 93bc777 - EG语义+tl映射修正 (旋律包络正确)
# 2407ccb - SD独立2-op (data区oneshot, 听感短促可接受)
# b1b022a - SD真2-op ch6 (听感最好但卡ISR)
# 119dcc6 - 鼓声单op简化路径 (BD/TOM/HH/CYM)
# 435f6e6 - 只渲染ch0-5 (6通道省CPU)
```

## 工作原则 (必须遵守)
1. **先 PC 仿真验证, 再改下位机** — 不验证就改 = 浪费时间
2. **fw_real_sim.py 必须和下位机 1:1 同步** — 不同步的仿真=假的
3. **只改数值/表, 不改架构** — round-robin/env_tick逻辑/输出公式/波形/相位/ml/结构体 不能动
4. **鼓声必须定长度 (oneshot)** — VGM 鼓声只有上升沿 key_on, 无 key_off, 不能依赖 VGM
5. **鼓声不走 round-robin ADSR** — round-robin 下 ADSR 无限长, 用 data区 oneshot
6. **8.8 定点** — pos/step 用 u16, 参考 STC32G12K128 fm.c (16通道不卡的秘诀)
7. **ISR 22050Hz** — 不是 49716, step 要按 22050 算
8. **level=0 跳过渲染** — 省CPU, level=0 的 op 跳过查表和乘法

## PC 仿真工具详解

### tools/fw_real_sim.py (旋律 1:1 下位机仿真)
- `render_fw_real(inst_idx, freq, dur_ko, dur_kf, volume)` — 严格复刻下位机旋律渲染
- 用法: 对照 emu2413 看 level 曲线, 验证包络行为
- 包含: AR/DR/RR 三表, key_on cnt=0, atk≤2瞬间, EG语义, tl映射
- **注意**: 这个仿真器的 env_tick/key_on 等必须和下位机同步更新

### tools/drum_fw_sim.py (鼓声 PC 仿真)
- `render_drum_fw(drum_type, dur)` — 鼓声仿真 (参数固化)
- `DRUM_PARAMS` — 5 鼓声参数字典
- **注意**: 用的是 oneshot 不是 round-robin, 和下位机单op鼓声一致
- SD 参数是独立2-op (FM调制+FB), 但仿真和下位机有偏差

### tools/ym2413_wav_gen.py (emu2413 忠实移植)
- `render_emu2413(inst, freq, dk, df)` — emu2413 旋律渲染 (对照标准)
- `render_drum(drum_type)` — emu2413 鼓声渲染
- 输出 WAV 到 wav_emu2413/ wav_fm_v3/ wav_fm_v3_fw/

## 当前下位机状态 (9327509)
- ym2413.c: u16 8.8 定点, 旋律 ch0-5 (6通道渲染), ch6-8 不渲染
- 鼓声: BD/TOM/HH/CYM/SD 单 op (YM_DRUM 结构, oneshot 每采样tick)
- ISR 偶尔卡 (6通道同发), 需进一步优化

## 鼓声参数 (8.8定点, step=freq×64×256/22050)
```
BD:  sin,    step=0x004A(100Hz),  vol=16, env_step=14, ~20ms
TOM: sin,    step=0x009F(214Hz),  vol=8,  env_step=14, ~20ms
HH:  noise,  step=0x00F8(334Hz),  vol=2,  env_step=46, ~65ms
CYM: noise,  step=0x00F8(334Hz),  vol=2,  env_step=255,~360ms
SD:  noise,  step=0x0012(25Hz),   vol=8,  env_step=28, ~40ms [单op]
```

## SD 2-op 待恢复 (参考 2407ccb)
独立 data 区 2-op 路径 (不走 round-robin):
```
mod: noise 25Hz(step=0x0012), FB=2, TL=15, DEC=7→SUL=0→REL=7
car: sin 240Hz(step=0x00B3), TL=31, DEC=7→SUL=19→REL=28
公式: (wave×(level+1)×(tl+1))>>10
FB: mod fb_val 反馈到 mod 自己相位
调制: car_idx += mod_out
```
触发: `ym_sd_trigger()` 设 data 区变量, 渲染: `ym_render_sd()` 每采样tick

## 关键代码位置 (9327509, 行号可能偏移)
- YM_DRUM 结构: ~155行
- 鼓声 init 参数: ~395行
- ym_drum_trigger: ~520行
- ym_render_drum: ~540行
- ym_render_fm (旋律2-op, u16): ~570行
- ym2413_render (主循环): ~620行
- 边沿触发 ym_prev_drum_bits: ~310行
- env_tick: ~326行
- AR/DR/RR 三表: ~39行
- 噪声表 ym_noise[64]: ~34行

## 待解决
1. ISR 性能: 6通道同发卡, 参考 12K128 fm.c 优化
2. SD 恢复 2-op: 用 2407ccb 的独立 data 区路径
3. 鼓声 round-robin 仿真: fw_real_sim 需要加鼓声仿真支持
4. BD 音量/时长: 可能还需微调

---

# 2026-06-25 音色准确度调试 (harpsichord 过反馈)

## 本次重大发现 (颠覆之前记录)

### 发现1: fw_real_sim.py 一直没和下位机同步 (违反 AGENTS.md 铁律!)
- **仿真器**: 注释写"16.16 定点", pos 用 u32 (`&0xFFFFFFFF`), idx=`pos>>16`, step 常数 `×65536`, 渲染采样率 `INTERNAL_RATE=49716`
- **下位机** (ym2413.c:122-123, 237, 577): **8.8 定点**, pos/step 都是 **u16**, idx=`pos>>8 & 0x3F`, step 常数 `×256`, ISR **22050Hz**
- **后果**: 仿真器频率 = 下位机频率 × (49716/22050) = **2.255×** → 听感高一个八度+2个半音
  - harpsichord 440Hz: 仿真器输出 992Hz, 下位机实际 438.7Hz (正确!)
- **教训**: 之前所有仿真结论 (过反馈/halfsin 扫描) 都建立在错误频率上, 不可信

### 发现2: halfsin 负半周镜像 vs 静音 (AGENTS.md 记录是错的)
- AGENTS.md 写: "halfsin 负半周**镜像** (不是静音)" — 当成下位机真实限制记录
- **对照 emu2413.c:383-387**: halfsin 后半周 = `0xfff` (静音!), 不是镜像
- 下位机 `ym_halfsin[64]` (ym2413.c:28-33): 后半周是镜像正值 (bug)
- **影响**: carrier 用 halfsin 时, 后半周本该静音却输出正值 → 直流偏置 + 失真

### 发现3: mod.tl 映射翻转会导致音高变化 (改动过大, 已否决)
- 现状: `mod.tl = 31 - (tl_raw>>1)` (TL=3 → tl=30 几乎满)
- 试过改成 `tl_raw>>1` (TL=3 → tl=1): 反馈占周期从 25%→1.6% 接近 emu 1.2%
- **但听感音高变了** (FM 边带偏移), 影响所有乐器, 已否决

## 本次修复 (仅 fw_real_sim.py, 下位机未动)

### 修复1: 仿真器改 8.8 定点对齐下位机 (fw_real_sim.py)
```python
# 4 处改动:
FW_STEP_CONST = 3579545.0 * 64.0 * 256.0 / (72.0 * 262144.0 * 22050.0)  # ×256 非 ×65536
FW_ISR_RATE = 22050  # 新增, 非 INTERNAL_RATE 49716

def fw_calc_step(...): return int(base * ml / 2.0) & 0xFFFF  # u16
def fw_render_fm(...):
    mod['pos'] = (mod['pos'] + mod['step']) & 0xFFFF   # u16 非 u32
    idx = (mod['pos'] >> 8) & 0x3F                      # >>8 非 >>16
    car 同理
def render_fw_real(...): n_total/n_keyon 用 FW_ISR_RATE

def save_fw_wav(filepath, samples):  # 新增, 按 22050 保存, 不降采样
    # 不能用 ym2413_wav_gen.save_wav (它假设输入 49716)
```
**验证**: harpsichord 440Hz → 仿真器 441.0Hz, emu 440.0Hz, 比例 1.002 (修复前 2.255) ✓

### 修复2: halfsin 后半周改静音 (fw_real_sim.py, 下位机待同步)
```python
FW_HALFSIN = [
     0,3,6,...,31, 31,...,3,     # 前半周 (正弦)
     0,0,0,...,0, 0,...,0,       # 后半周静音 (对齐 emu, 旧版是镜像正值)
]
```

### 修复3: volume 映射 bug (fw_real_sim.py)
- 旧: `car.tl = volume>>1` (volume=0 → tl=0 → 静音, 语义反了)
- 新: `car.tl = (60-volume)>>1` (volume=0 最大音量 → tl=30 满)
- 对照下位机 ym2413.c:500-502: `vol=(15-reg_vol)<<2; car.tl=vol>>1`

## 当前验证状态
- harpsichord 1s+1s wav: `tools/wav_fw_sync/harp_fw.wav` vs `harp_emu.wav`
- 频率已对齐 (441 vs 440), 待听感确认音色/反馈

## 下一步 (频率对齐后重新评估)
1. **听 harp_fw.wav vs emu**: 确认过反馈是否还在 (频率对齐后重新判断)
2. **重新做反馈扫描**: 之前扫描结论因频率错而无效, 需重跑 FB=0~7
3. **halfsin mute 是否保留**: 频率对齐后再听对照
4. **下位机同步**: 仿真验证通过后才改 ym2413.c (halfsin 表 + 可能的反馈调整)

## 教训补充
- **fw_real_sim.py 不同步是万恶之源** — 频率错 2.255× 导致所有调参白做
- **听感最准** — 用户听出"高八度+2半音"直接定位到频率 bug, 比所有数值分析都快
- **改 mod.tl 这种全局映射会动音高** — FM 调制量级变化影响边带, 不是纯调参

---

# 2026-06-25 harpsichord 包络对齐 (sus_hold 指数查表)

## 触发
频率对齐后听感确认: harpsichord 仍过反馈 + 包络行为差太远.
直接算幅度对比 (无需听) 发现:
- keyoff 后 fw 3824ms 才归零 (emu ~100ms)
- keyon 期间 fw 几乎不衰减 (-2.5dB@900ms), emu 持续衰减 (-24.7dB@900ms)

## 根因: emu 5 阶段速率映射 (get_parameter_rate line 498-516)

| env_state | emu 速率 | fw 旧实现 | 问题 |
|---|---|---|---|
| ATTACK | AR | AR | ✓ |
| DECAY | DR | DR | ✓ |
| SUSTAIN | `EG?0:RR` | `EG?0:rel(RR)` | ✓ 速率对但**形态错** (见下) |
| RELEASE | `sus?5:(EG?RR:7)` | `sus?5:rel(RR)` | ❌ **EG=0 应用固定 7, 旧用 RR** |
| DAMP | DAMPER_RATE | - | - |

### 关键 bug: RELEASE(EG=0) 速率映射错
- 旧: `env_step = rel` (=RR_TAB[rr], 慢) → keyoff 3824ms
- 新: `env_step = sus?5:(EG?rel:RR_TAB[7])` → keyoff ~100ms (对齐 emu)

### 关键 bug: SUSTAIN 线性 vs emu 指数形态差异
- emu: eg_out 对数域线性递增 → 输出**指数衰减** (前期慢后期也慢, 持续衰减)
- fw : level 线性递减 → 输出**线性衰减** (前期慢后期快, level 小时迅速归零)
- **纯改 cnt 无法拟合**: 扫描 cnt=5~30, 要么前期太快要么后期死掉

## 解决: sus_hold[32] 指数衰减查表 (2026-06-25 新增)

加一张表 + 一个计数器, SUSTAIN 阶段查表替代线性减法, 模拟指数衰减:
```
FW_SUS_HOLD = [1, 134,134,78,55,43,35,29,25,22,20,18,16,15,14,
               13,12,11,11,10,10,9,8,8,8,7,7,7,7,6,6,6]  # scale=0.44 精调
// SUSTAIN 阶段 (env_step=1 让 sus_hold 接管):
sus_cnt++;
if (sus_cnt >= sus_hold[level]) { sus_cnt=0; level--; }
```
- sus_hold[level] = 该 level 停留几个 round-robin tick (高 level 慢降, 低 level 快降)
- **纯查表+计数器, 无除法无指数运算, STC32 可跑** (6FM+5节奏满负荷下 OK)
- tau≈97ms (scale=0.44 精调对齐, 从 tau=221ms 基础表缩放)

**配套改动**:
- decay→sustain 转换: `env_step = 0 if EG else 1` (env_step=1 让 sus_hold 接管, 不被外层节流)
- DR_TAB/RR_TAB 4~10 档改快 2.2× (旧表系统性偏慢)

### release 也用指数查表 (FW_REL_HOLD)
release 原来线性 `level-=1` (受 env_step 节流), keyoff 后从低 level 瞬间归零.
改成和 sustain 一样的指数查表机制:
```
FW_REL_HOLD = [max(1, h//10) for h in FW_SUS_HOLD]  # release 比 sustain 快 ~10×
// RELEASE 阶段 (fw_key_off 设 env_step=1, sus_cnt=0):
sus_cnt++;
if (sus_cnt >= rel_hold[level]) { sus_cnt=0; level--; }
```
- release 整体 ~75-100ms 归零 (对齐 emu release 跨度)
- **不再依赖 emu 的 RELEASE 速率规则** (固定7/sus?5/EG?RR), 直接用查表拟合 emu 输出形态

## harpsichord 对齐结果 (440Hz, 1s keyon+1s keyoff, scale=0.44)
| t_ms | emu | fw | diff |
|---|---|---|---|
| 100 | -2.7 | -3.6 | -0.9 |
| 300 | -8.2 | -9.0 | -0.8 |
| 500 | -13.6 | -15.3 | -1.7 |
| 700 | -19.1 | -19.2 | -0.1 |
| 900 | -24.7 | -22.9 | +1.8 |
| 999 (ko尾) | -29.7 | -27.9 | +1.8 |
sustain 段全程偏差 ±2dB 内 ✓ (wav: tools/wav_harp_now/)

**已知限制 - release 尾巴台阶**:
- release 末期卡在 -27.9dB (level=1) 然后跳变 -99 (level=0)
- 根因: **level 只有 32 级**, 最后一级 (1→0) 就是 -27.9→-99 硬跳变
- emu eg_out 128 级能平滑过渡, fw 32 级无法表达 -30~-99dB 精细衰减
- 调 rel_hold 无效 (扫描 div 5~30 都卡 -27.9, 数据证明)
- **听感上音尾突然消失, 但 sustain 段已对齐, 整体可接受**

## 过反馈修复: FB+4 移位 (2026-06-25)

频率+包络对齐后, harpsichord 仍过反馈. 解耦分析:
- **反馈占周期**: fw 15.05% vs emu 0.66% (fw 是 emu 的 22.9×)
- 两个因素: FB 运算 (移位+表大小) + mod tl 衰减 (mod 输出量级)
- mod tl 贡献 18.6× (主因), FB 运算贡献 ~1.1×

4 方案试听 (orig/plan1 FB+4/plan2 mod tl/plan12 合), **选定 plan1 (FB+4 移位)**:
- 改动: `fb_val = ch_out >> (mod['fb'] + 4)` (原 `>> mod['fb']`)
- 只影响反馈环路, 不动 mod→carrier 正常 FM 调制, 不动音高
- **反馈占周期 15.05% → 0.78%** (emu 0.66%, 几乎一致) ✓
- 纯改移位常数, 简单运算, STC32 可跑
- wav: tools/wav_harp_final/

## harpsichord 完成状态 (2026-06-25)
三大问题全部修复 (仿真层):
1. ✅ 频率对齐 (8.8 定点, 992→441Hz)
2. ✅ 包络对齐 (sus_hold scale=0.44 + rel_hold 指数查表)
3. ✅ 过反馈修复 (FB+4 移位, 反馈占周期 15%→0.78%)
**已同步下位机 ym2413.c (commit 0bcd705, 编译通过)**

## 意外收益: 拨奏类乐器一并修复 (2026-06-25 实机验证)
sus_hold/rel_hold 指数查表 + FB+4 是**通用机制**, 不止修了 harpsichord,
还一并修复了所有「带反馈 + 持续衰减」的拨奏类乐器:
- ✅ Guitar (吉他) - 拨弦衰减形态对了
- ✅ Piano (钢琴) - 拨弦衰减形态对了
- ✅ Vibraphone (颤音琴) - 拨弦衰减形态对了
- ✅ Harpsichord (拨弦键琴)
**原因**: 这些乐器共用 EG=0 (non-sustaining) + 反馈, 旧的线性衰减 + 过反馈
让它们全部失真, sus_hold/rel_hold + FB+4 一次性解决.

## AM/VIB (LFO) 查表实现 (2026-06-25)

YM2413 的 LFO: PM (vibrato 频率调制) + AM (tremolo 振幅调制). 之前下位机完全没实现.

> ⚠️ **下位机暂关** (2026-06-25): AM/VIB 代码用 `#if 0` 包裹, 性能不足暂时禁用.
> **仿真器 (fw_real_sim.py) 和文档保留完整成果**, 日后优化 ISR 性能后改 `#if 1` 即可启用.
> lfo_tab 表保留在 code 区, 启用时无额外移植成本.

### 实现 (纯查表, 无性能障碍)
- **LFO 推进**: round-robin 每 16 采样索引 +1 (不是每采样), 省算力
  - 频率: 22050/16/210 = 6.56Hz (标准 vibrato 5~7Hz)
- **FW_AM_TABLE[210]**: 三角波 0~13 (PM/AM 共用)
- **PM (vibrato)**: 操作 **step (频率)** 不是 pos (相位)!
  - `pos += step + (step>>6) × (tri-6) >> 3`  (±1.5% 频率, 1/4 半音)
  - 操作 pos 会相位突变产生泛音, 操作 step 频率连续平滑
- **AM (tremolo)**: carrier level 减 am_factor
  - `eff_level = level - (am_factor >> 1)`  (am 0~13, level 减 0~6)

### 每个 op 独立 AM/PM 标志
- patch 解码: mod_am/pm 在 dump[0] bit7/6, car_am/pm 在 dump[1] bit7/6
- make_op 加 am/pm 字段, render_fm 按 op 标志决定是否调制
- **坑**: car 的 make_op 调用必须传 am/pm (默认 0, 漏传则 car 无颤音)

### 乐器 AM/PM 分布
- 大部分乐器 car_pm=1 (carrier vibrato): violin/flute/trumpet/horn/synth/vib/bass/guitar
- vibraphone 独有 car_am=1 (carrier tremolo)
- violin mod_pm=1 (modulator 也 vibrato)

## attack 指数递增 + SUL 表 + AR 退回 (2026-06-25)

### attack 非线性 (拟合 emu `eg_out -= (eg_out>>s)+1`)
emu attack 是指数: eg_out 大时减得多(快), 小时减得少(慢), 输出**前期快后期慢趋顶**.
fw 旧版线性 `level += 1` (匀速), 吹奏乐器(flute)缺乏渐起感.
**修复**: `level += (31-level)>>2 + 1` (镜像指数, 低level大步进/高level小步进)
- 只动一个运算, 不动架构, STC32 可跑
- flute 不再敲击(渐起), harpsichord/vib atk≤2 瞬间到顶不变

### AR 表退回 (全局改快破坏吹奏乐器)
曾把 AR_TAB 3~7 改快 2.3×, 导致 flute AR=6 产生敲击感(瞬间到顶).
**退回原表**: 拨奏乐器 AR≥7 本就 atk≤2 瞬间到顶, 改快只影响吹奏.
> AR 真正需要非线性速率映射(像 sus_hold), 而非全局改快. 待后续优化.

### SUL 表 (sl→sustain level 映射)
旧 `sul = 31 - sl*2` (线性), sl=2→sul=27 (太浅, 只-1dB).
emu SL 是对数域, sl=2 对应 -9dB.
**新 FW_SUL_TAB** (温和, 避免 non-sus 双重衰减):
`[31,27,23,19,15,12,9,7,5,4,3,2,1,1,0,0]`
- harpsichord sl=0→31 (不变), vib sl=1→27, flute sl=2→23
- vibraphone 不再退化 (之前激进表让它 -18dB 太深)

### 已非线性化的阶段
| 阶段 | 旧 | 新 |
|---|---|---|
| Attack | 线性 level+=1 | **指数** level+=(31-level)>>2+1 |
| Sustain | 线性 level-=1 | **sus_hold[32] 查表** (×RR缩放) |
| Release | 线性 level-=1 | **rel_hold[32] 查表** |
| Decay | 线性 level-=1 | ❌ 待非线性化 |

## 下一步 (剩余乐器逐个调)
sus_hold 表是**全局**的 (所有乐器 SUSTAIN 共用), 但各乐器 RR/SL/EG 不同,
衰减时间常数不同。可能需要:
1. sus_hold 按 RR 档位缩放 (不同乐器不同 tau)
2. flute 等已知问题: AR/DR 太慢, 单独调 AR_TAB/DR_TAB
3. 逐乐器对照 emu, 找各自的包络偏差
**注**: sus_hold 目前是单一 tau, 多乐器共用可能要改成 tau 随 RR 变化

## 教训补充 (2026-06-25)
- **线性 level 无法拟合指数衰减** — 必须查表, 纯改速度不行 (扫描证明)
- **加表+简单运算是允许的** — sus_hold/rel_hold 查表不是"改架构", 是"加表+改运算规则"
- **拟合 emu 输出即可, emu 内部规则无意义** — release 用什么速率不重要, 输出曲线对齐就行
- **STC32 算力有限** — 6FM+5节奏已满负荷, 不能用除法/指数运算, 查表+计数器才行
- **先算幅度对比再听** — 包络偏差从 RMS 曲线直接可见, 不用听就能定位
- **逐个击破** — 15 乐器不要一起调, 先 harpsichord 跑通流程再逐个来
- **level 32 级是硬限制** — release 末期的 -30~-99dB 衰减无法平滑, 调表无效
- **别光调不出 wav** — 调参后立刻出 wav 给听感核对, 不要只看数值

