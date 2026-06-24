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

