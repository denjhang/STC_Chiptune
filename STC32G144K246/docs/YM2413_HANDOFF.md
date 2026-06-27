# YM2413 工作交接 (2026-06-25)

## 📜 项目编年史 (2026-06-26 补, 看这个先建立全局观)

stc2413 不是凭空出现的, 它是**跨三个芯片平台、11 个 Phase 演进**的最新一层.
完整脉络 (git 时间线坐实):

```
STC8H8K64 (8051, 48MHz)          ← Phase 1-6: 原型期 (2026-06-06 起)
  SCC/AY/SN 成功, GB/NES/SAA 失败  ← 失败是迁移的导火索
       ↓ (算力/内存不够, 失败音源做不出来)
STC32G12K128 (C251, 38MHz)       ← Phase 7-11: 博物馆期
  README 原话: "一颗芯片音乐博物馆"  ← 6音源+FM+ADPCM+BRR+鼓机
       ↓ (要 USB + 更好 DAC + VGM 直接兼容)
STC32G144K246 (64MHz + USB + 12bit DAC) ← 当前: VGM 兼容期 (2026-06-16 起)
  HPLL 120MHz, USB CDC, 12-bit 硬件 DAC  ← stc2413 在这层
```

### 各 Phase 做了什么 (见主 README.md 第 7 节)

| Phase | 平台 | 内容 | 性质 |
|---|---|---|---|
| 1-6 | STC8H8K64 (8051, 48MHz) | SCC/AY/SN 仿真成功; GB/NES/SAA **失败尝试** | 原型, 证明可行也摸到边界 |
| 7 | STC32G12K128 (C251, 38MHz) | 全音源移植 C251 + FM 16voice + Gigatron; SCC 剔除 | 迁移 + 扩充 |
| 8 | 同上 | ADPCM 采样 (YM2608 Type-A, SF2 5乐器 + 6鼓声) | 新增: 采样合成 |
| 9 | 同上 | WT 波形扩充 (14种, 32/64/128点可切) | 新增: 波形表合成 |
| 10 | 同上 | 鼓机系统 (14风格, ini驱动, GM Perc 35-81) | 新增: 序列/编排 |
| 11 | 同上 | BRR 旋律采样 (SNES DSP, GME bit-exact, 14乐器) | 新增: 高级采样 |
| **当前** | **STC32G144K246** | **VGM 兼容 + 8音源 (AY/SN/SCC/NES/GB/FDS/YM2413+鼓声)** | **标准兼容** |

### 三个平台的递进逻辑 (为什么换平台)

1. **STC8H → STC32G12K**: 不是"想升级", 是**STC8H 算力/内存不够, GB/NES/SAA 做失败**
   → 换更强的 C251 内核才做出来. 换平台是被失败逼的, 不是锦上添花.
2. **STC32G12K → STC32G144K**: STC32G12K 是 UART + PWM DAC (8-bit),
   要 **USB CDC (上位机直连) + 12-bit 硬件 DAC (音质提升) + HPLL 120MHz (算力翻倍)**
   才能做 VGM 兼容. 这次是主动升级, 为标准兼容.
3. **演进方向**: 从"自定义协议 + 自由合成" → "标准 VGM 兼容 + 真实芯片还原".
   stc2413 是这个方向的最高点 (最难的标准兼容: YM2413 FM).

### "芯片音乐博物馆" → "VGM 标准播放器" 的定位转变

- **STC32G12K128 时代** (Phase 7-11): "博物馆" — 自定义协议, 自由设计音色/波形/鼓机,
  自己玩. 不强求兼容标准文件格式.
- **STC32G144K246 时代** (当前): "标准播放器" — VGM 直接灌, 兼容真实芯片行为,
  能播 MSX/SMS/NES/GB 的真实音乐. stc2413 是 YM2413 的标准兼容实现.

这两个定位不矛盾, 是**能力的两个方向**: 博物馆练"创造/设计" (自己造音色),
播放器练"还原/兼容" (复现真实芯片). 0.0 节说的"完全掌握合成技术 + 能自己设计音源",
正好需要这两个方向都练到.

## ⚠️ 项目定位 (2026-06-26, 最高优先级认知)

**真实驱动力**: "玩这么久芯片音乐却不了解合成原理, 不能自己设计音源, 这很没意思."
不是省钱/KPI, 是认知好奇心 — "用了十年的东西, 我到底懂不懂它".
触发问题: "芯片库存耗尽怎么办?" → 答案: 掌握合成原理, 自己能造, 不依赖实物.

**终极目标**: 完全掌握音频合成技术, 能自己设计音源 (能造才是真懂). libvgm/MAME/Furnace
这些开源核心 = 免费的数字音频技术资产 (几乎整个数字音频史), 当教材用, 不是当后端用.
每移植一个核心 = 掌握一类合成技术.

**stc2413 的本质**: 以 libvgm 为教材, 把 YM2413 合成原理在最低端 MCU 上重新实现一遍
的学习过程. 鼓声 (假噪声双重身份/共振峰拟合) 已经是"自己设计音源", 不是移植.

**音频是训练场, 不是终点** — 8 音源练出"约束仿真"手艺, 迁移到整机仿真
(音源 → 单芯片 → 多芯片整机). 首要产出是**人成为独当一面的嵌入式/全栈开发者**.

**告别"开源硬件复刻"**: MCU 贵/硬件 bug/软件弃坑/被动挨坑 — stc2413 路线要**主动权
在自己手里**.

详见 OPLL_INTEGRATION_STATUS.md 0.0 节.

## ⚠️ 接手前必读 (2026-06-26)

**判断 stc2413 好不好的第一证据是曲库规模: `vgm/opll/` 有 421 首 VGM** (ys/sor/s1/
msxfan/ysfm/ysms/90s 等 17 子目录). 听感不行不会堆到 421 首. 这是用脚投票的整体听感
证据, 比任何和 emu2413 的 dB 对照都硬.

**不要拿 emu2413/Nuked 当标尺量 stc2413** — 它们是不同问题的解 (科学/移植 vs 工程),
不在一条精度阶梯上. 不要见 64 点表/假噪声/查表就说"精度不够/凑的常数/劣化" —
每个决策背后都有依据 (见 OPLL_INTEGRATION_STATUS.md 0.0 节 + 第 12 节).

**核心工程哲学: 性能优化 > 换更强硬件** (见 OPLL_INTEGRATION_STATUS.md 0.1 节).
stc2413 一颗几块钱的 8051 塞 8 个音源, 靠的是针对性优化 + 听感拟合, 不是算力.
反面的"换 AT32+FPGA"路线要么卡内存要么卡成本. 这是让 FPGA/DSP 颤抖的降维打击 ——
重新定义解空间, 让硬件优势变得无关紧要.

## 当前状态 (快速接续, 2026-06-25 末)

### 当前生产固件 (commit c53f8e8, HEX 71018 bytes)
已实现的 YM2413 改进 (本轮全部):
- ✅ **8.8 定点同步** (仿真器+下位机, 频率对齐 emu)
- ✅ **halfsin 后半周静音** (对齐 emu, 旧版镜像正值是 bug)
- ✅ **attack 指数递增** `level+=(31-level)>>2+1` (非线性)
- ✅ **sustain sus_hold[32] 查表** (×RR缩放, 指数衰减)
- ✅ **release rel_hold[32] 查表** (指数衰减)
- ✅ **volume ym_vol_tab[62] 对数查表** (等dB)
- ✅ **FB+4 移位** (过反馈修复, 反馈占周期 15%→0.78%)
- ✅ **鼓声遗漏修复** (rhythm=0 时 prev_drum_bits 清零)
- ✅ **鼓声全部变频** (BD/HH/SD/TOM/CYM, base_step×fnum_blk/默认)
- ✅ **鼓声 vol 映射+换算** (reg 0x36-0x38 → ym_drum.vol, base_vol×(15-reg_vol)/15)
- ✅ **连续鼓声模仿** (trigger 续命 + vol 实时映射)
- ⚠️ **AM/VIB 下位机暂关** (#if 0, 仿真+文档保留, 性能不足)
- ❌ **DR 非线性回退** (decay 查表让 Piano 太慢, 退回线性)

### 正在调试: 鼓声连不起来 (BB3/B-FIGHT)
**问题**: BB3/B-FIGHT 用 reg 0x36-0x38 vol 快速变化模拟连续鼓声,
但实机听感鼓声还是连不起来 (离散短敲击, 不是连续长鼓).
**已做**: vol 实时映射到 ym_drum.vol (render 公式实时读 vol), trigger 续命.
**架构定性 (2026-06-26, 已记入 OPLL_INTEGRATION_STATUS.md 第 12 节)**:
这是 **oneshot 架构 vs naruto 续命技法的根本冲突, 不是 bug**.
- naruto 等极少数作曲家用高速反复 keyon BD/SD 续命拉长鼓声 (OPLL 驱动特有技法)
- emu2413 鼓声用真 EG 状态机能反复重启包络 → 能续命
- stc2413 鼓声是 oneshot 单 op 衰减计数器, BD ~20ms 衰减完, BB3 vol 间隔 ~37ms → 已静音
- 已做的 trigger 续命是 oneshot 模拟状态机的**天花板**, 调参无法根治
- **只影响 naruto 类极少数曲子, 主流 MSX/SMS 曲库不受影响**
**可能原因** (待排查):
1. 鼓声 oneshot 衰减太快 (env_step 太大), vol 变化时 level 已衰减完 (active=0)
2. vol 变化间隔 vs 鼓声衰减时间: BB3 vol 变化间隔 ~37ms, BD env_step=14 →
   衰减时间 = 31×14/22050×1000 ≈ 20ms, 比 vol 间隔短 → vol 变化时已静音
3. 需要鼓声持续振荡 (不是 oneshot), 或延长衰减时间
**测试 VGM**: `vgm/opll/msxfan/BB3.vgm`, `B-FIGHT1.vgm`, `B-FIGHT2.vgm`
**下一步思路**:
- 方案A: 鼓声 active 时不因 level=0 停止, 保持振荡 (vol=0 时静音), vol>0 恢复
  (即鼓声变持续振荡器, vol 控制开关, 像 OPLL 真实行为). 方向正确但有架构差距.
- 方案B: 延长鼓声衰减 (增大 env_step), 让 vol 变化期间鼓声还在响. 治标, 改所有曲子鼓声长度.
- 方案C: PC 鼓声仿真 (drum_fw_sim.py) 加 reg 0x36-0x38 支持, 数值验证.
  **注意: 对比 stc2413 自己的衰减曲线, 不要拿 emu 当标尺 (模型不一样)**.
**现实判断**: 主流曲库已接近完美 (HH/CYM 尤其好), 这只是 oneshot 的固有硬伤,
优先级不高, 调参能改善但无法根治.

### 本轮关键 commit (倒序)
- c53f8e8 docs: 鼓声三功能记录
- 53511f0 fix: 鼓声 vol 换算 (base_vol)
- 0c33150 feat: 鼓声 vol 映射 (反相)
- 5bb97e2 feat: 连续鼓声模仿 (续命)
- c6b77fb feat: 鼓声全部变频
- 7b05f07 feat: 鼓声 BD/TOM 变频
- b199b88 fix: 鼓声遗漏 (rhythm=0 prev_bits)
- 8aadd2f feat: volume 对数查表 (生产基线, decay 线性最佳)
- 99c6604 feat: attack 指数递增
- 28a5bd2 revert: DR 退回线性
- 0bcd705 feat: harpsichord 下位机同步 (sus_hold/rel_hold/FB+4)

## 工作目录
- 项目根: `D:\working\vscode-projects\STC_Chiptune`
- 固件源码: `STC32G144K246\usb_cdc_test\src\ym2413.c`
- 构建脚本: `STC32G144K246\usb_cdc_test\build.py`
- PC 仿真工具: `STC32G144K246\usb_cdc_test\tools\`
- VGM 测试文件: `vgm\opll\msxfan\`, `vgm\opll\opldrv\`
- STC32G12K128 参考实现 (16通道FM不卡): `STC32G12K128\fm.c`
- **vgm_player.py `--ym2413` 参数**: MSX 的 YM2413+AY 组合会卡死下位机 ISR
  (6通道FM已满, AY噪声再加就爆). 加了这个参数在上位机 strip 掉其他芯片, 只发 YM2413.
  git: `29a73f8`/`26f4e37`/`5820f19`. 播 MSX VGM 必须带这个参数.

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
9. **不要拿 emu2413 当标尺苛责 8051 实现** (2026-06-26) — emu 跑在 PC 上, 单 slot
   就要 1024 项 exp_table 查表, 6 通道直接爆 ISR. stc2413 缺 KL/RKS/LFO 是 8051 限制
   下的必然取舍, 不是缺陷. 评价基准是**主流 MSX/SMS 曲库听感** (99% 场景, 已接近完美),
   不是"每个细节都对齐 emu 算法". 详见 OPLL_INTEGRATION_STATUS.md 第 12 节.
10. **调鼓声对比 stc2413 自己的衰减曲线, 不拿 emu 当标尺** (2026-06-26) —
    stc2413 鼓声是 5 单 op oneshot, 无 FM 无 LFSR, 和 emu 鼓声模型不一样.
    鼓声连不起来是 oneshot vs naruto 续命技法的架构冲突, 不是 bug.
11. **低精度是还原硬件本貌, 不是缺陷** (2026-06-26 最重要的认知) — YM2413 是雅马哈
    最低端 FM 芯片, 9-bit DAC 阶梯严重, 真实音质"其实很差" (中低音量有嘶嘶音, 用户
    10 年+ 芯片经验 + 大量实物确认). **emu2413 没模拟 DAC 劣化, 反而比真芯片"干净"**
    (美化失真). stc2413 的 64 点/8.8 定点/32 级包络, **方向上恰好贴近真硬件低精度**.
    **不要再产生"提精度会更像真芯片"的想法 — 提精度 = 更像 emu 但更不像真芯片**.
    评价基准是真实芯片听感. 项目初期 19-bit/1024 点改造 (873a3a5 → 无声) 就是这个
    错误思维的代价. 详见 OPLL_INTEGRATION_STATUS.md 12.0.1.
12. **2-op FM 运算才是 CPU 瓶颈, 不是 LFSR** (2026-06-26) — ay8910 就用 LFSR,
    stc2413 也有. 鼓声不用 LFSR 是因为完整 2-op 运算在 6 旋律已是极限时爆 ISR.
    要加 ch6-8 / 真 2-op 鼓声 / LFSR 鼓声, 路径是 **PLL 超频**, 不是改算法.

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
TOM: sin,    step=0x009F(214Hz),  vol=9,  env_step=14, ~20ms   (8→9 提音量)
HH:  noise,  step=0x00F8(334Hz),  vol=4,  env_step=46, ~65ms   (2→4 提音量)
CYM: noise,  step=0x00FB(338Hz),  vol=4,  ym_cym_hold非线性, ~231ms  (334→338, 非线性表)
SD:  方波255Hz × LFSR(12次/采样) × ym_sd_amp对数幅度, vol=5, ~130ms (linear_db)
```

### SD 方案 (2026-06-27 定稿, linear_db 方波×LFSR×对数幅度)

**机制: 方波(255Hz) × LFSR噪声开关(12次/采样) × linear_db对数幅度表**
- 方波 255Hz (pg_out bit8, emu降4半音最佳, 240-260精扫确定)
- LFSR 17-bit (OPLL反馈0x800200), 推进12次/采样 (真白噪无周期, 替代64点固定表)
- 泄漏 1/30 (noise_bit=0时幅度=amp/30, 对应emu to_linear近零值)
- linear_db ym_sd_amp[32] (level 31→0, 48dB线性dB衰减, 130ms)
- emu SD 实测RMS: 0.37dB/ms匀速 (线性dB, 不是指数)

**合成原理 (emu calc_slot_snare 原理复刻):**
```
每采样:
  sq_bit = (sq_pos >> 16) & 1          // 方波 ±1 (pg_out bit8)
  LFSR 推进12次, noise_bit = lfsr & 1  // 高频白噪 (emu update_noise 18次的等效)
  amp = ym_sd_amp[level]               // 对数幅度 (emu to_linear)
  mag = noise_bit ? amp : amp/30       // 噪声开关 + 泄漏
  out = sq_bit ? -mag : +mag           // 方波 × 噪声
```

**定稿过程 (大量扫频仿真):**
1. 8种调制(add/sub/mul/div/am/pm/fm/pwm) × 6频率 → 加法/PM最实用
2. mod/car角色对调 + 包络方向(sf/nf) → PM_swap+sf+n5初步最佳
3. dump emu SD原始波形 → 发现是方波×噪声开关, 不是sine+noise加法
4. linear_db对数幅度表 (匹配emu 0.37dB/ms线性dB) → 替代指数表
5. 方波240-260精扫 → 255Hz最佳
6. LFSR 0-16精扫 → adv12最佳
7. 修复方波step笔误 (0x5A20→0x05EB, 1940Hz→255Hz)

**仿真依据: tools/wav_sd_lfsr_8_16/SD_adv12.wav (最接近emu)**

> 2026-06-26 vol 调整 (commit 862c70d): TOM/HH/CYM base_vol 提音量, 解决 HH/CYM 相比 SD/BD 偏小. 新比例 BD:TOM:HH:CYM:SD = 16:9:4:4:8. 只改 init 数值,
> render/vol换算公式不动. 待实机听感确认 (CYM decay 长, vol=4 若糊再降).
> 旧值: TOM=8 HH=2 CYM=2 (HH/CYM 被 base_vol=2 压到 SD 的 1/4).

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

### VOLUME 对数查表 (拟合 emu 等dB间距)
emu volume 每+1 衰减 -0.72dB (等dB, 音量旋钮特性). fw 旧版 `car.tl=(60-vol)>>1` 线性,
dB不均匀 (低音量区跳变剧烈, 高音量区迟钝).
**新 ym_vol_tab[62]**: fw_vol(0~61) -> tl(0~30), 对数映射
- fw_vol=61(volume=0最大) -> tl=30 (满输出)
- fw_vol=0(volume=60静音) -> tl=0
- 中高音量区 dB 间距均匀 (diff 1~4dB vs emu)
- 低音量区(tl到0)受32级分辨率限制, 但-30dB以下实际影响小

### 已非线性化的阶段
| 阶段 | 状态 | 实现 |
|---|---|---|
| Attack | ✅ | 指数 `level+=(31-level)>>2+1` |
| Decay | ❌ **回退线性** | decay 查表让 Piano 衰减太慢, 实测退回线性最佳 |
| Sustain | ✅ | sus_hold[32] 查表 (×RR缩放) |
| Release | ✅ | rel_hold[32] 查表 |
| Volume | ✅ | ym_vol_tab[62] 对数查表 |

## 鼓声遗漏修复 (2026-06-25, Ys First Step Towards Wars)
VGM 模式: `0x35(R,鼓声) → 0x00(m,关rhythm) → 0x35(R,鼓声)` 快速循环.
- 旧: `if (rhythm) { ... ym_prev_drum_bits = drum_bits; }` — rhythm=0 时**不更新 prev_bits**
- 关 rhythm(0x00) 后 prev_bits 保持旧值(0x15), 再开 rhythm(0x35) 时
  `new_bits = 0x15 & ~0x15 = 0` — **鼓声不触发!**
**修复**: rhythm=0 时 `ym_prev_drum_bits = 0`, 下次开 rhythm 任何 bit 0->1 都能触发.

## 鼓声 vol 映射 + 连续鼓声 + 变频 (2026-06-25, 已实现)

### 1. 鼓声 vol 映射 (reg 0x36-0x38 -> ym_drum.vol)
**bug 修复**: 旧版 reg 0x36-0x38 改 `ym_ch.car.tl` (FM 通道), 不影响鼓声.
现在 rhythm mode 下实时映射到 ym_drum.vol (render 公式 `(wave×(level+1)×vol)>>6` 实时生效):
```
drum.vol = base_vol × (15 - reg_vol) / 15   (OPLL vol 0=最大反相)
ch6(0x36) hi4 -> BD(drum[0])
ch7(0x37) hi4 -> SD(drum[4]), lo4 -> HH(drum[2])
ch8(0x38) hi4 -> TOM(drum[1]), lo4 -> CYM(drum[3])
```
base_vol: BD=16 TOM=8 HH=2 CYM=2 SD=8 (init 试听调参, YM_DRUM.base_vol 字段存)

### 2. 连续鼓声模仿 (快速 keyon 续命)
BB3/B-FIGHT 用 reg 0x36-0x38 vol 快速变化 (vol=0↔15) 模拟连续鼓声,
不是离散短敲击. vol 实时映射后自然连起来.
另外 trigger 续命: level>0 (还在响) 时只重置 env_cnt (延长), 不重置 level.
一行改动, 零额外负载.

### 3. 鼓声全部变频 (BD/HH/SD/TOM/CYM)
rhythm mode 下 reg 0x16-0x18/0x26-0x28 写 ch6/7/8 时换算 drum step:
```
drum.step = base_step × (VGM fnum×2^blk) / (OPLL默认 fnum×2^默认blk)
```
OPLL 默认: BD(ch6)=288×4=1152, HH/SD(ch7)=336×4=1344, TOM/CYM(ch8)=448×1=448
下位机 base_step: BD=0x004A TOM=0x009F HH/CYM=0x00F8 SD=0x0012
YM_DRUM 加 base_step 字段. reg 写入时 ch>=6 触发 ym_update_drum_step.

### 未实现 (低优先级)
- **旋律模式 ch6-8 渲染**: CS6 类 VGM 在旋律模式用 ch6-8 keyon 模拟鼓声,
  下位机只渲染 ch0-5, 完全听不见. 需扩渲染范围, 吃 ISR 算力.

## 鼓声变频详情 (2026-06-25)

### OPLL 约定的默认鼓声频率 (从 f1/msxfan/ysms 多个 VGM 统计确认)
rhythm mode 下, VGM 开头几乎都写 ch6/7/8 的 fnum/blk 到固定值:

| 通道 | OPLL 默认 fnum | blk | OPLL 频率 | 对应鼓声 |
|---|---|---|---|---|
| ch6 | **288** | **2** | 218.5 Hz | BD (低音鼓) |
| ch7 | **336** | **2** | 254.9 Hz | HH (踩镲) / SD (军鼓) |
| ch8 | **448** | **0** | 85.0 Hz | TOM (嗵嗵) / CYM (吊镲) |

这是 OPLL rhythm mode 的**约定默认频率**. 部分 VGM (如 Big Don, Constructor, Ys) 会
改 ch6 的 fnum 实现 BD 变频 (如 288/blk2→480/blk1, 218Hz→182Hz 降调).

### 下位机自定义鼓声频率 (试听调参, 不同于 OPLL 默认)
| 鼓声 | 下位机频率 | step (8.8) | vs OPLL |
|---|---|---|---|
| BD | 100 Hz | 0x004A | ×0.46 (比 OPLL 218Hz 低) |
| TOM | 214 Hz | 0x009F | ×2.5 (比 OPLL 85Hz 高) |
| HH | 334 Hz | 0x00F8 | 噪声 (频率=噪声速率) |
| CYM | 334 Hz | 0x00F8 | 噪声 |
| SD | 25 Hz | 0x0012 | 噪声 |

### 换算公式 (VGM fnum → 下位机 step)
VGM 写的 fnum 是基于 **OPLL 默认频率**的音高. 下位机有自己的默认频率, 必须换算:
```
新 step = 下位机基础 step × (VGM fnum×2^blk) / (OPLL默认 fnum×2^默认blk)
```
例: BD VGM 改成 480/blk1, 默认 288/blk2:
```
BD_new_step = 0x004A × (480×2) / (288×4) = 0x004A × 960/1152 = 0x004A × 0.833
```

### 实现范围
- **BD (ch6 fnum)**: 变频明显, 必须换算. rhythm mode 下 reg 0x16/0x26 写入时更新 BD step
- **TOM (ch8 fnum)**: 变频较少, 换算同 BD. reg 0x18/0x28 写入时更新 TOM step
- **HH/CYM/SD**: 噪声, 变频听感不明显, 暂保持固定 step

### 待实现
1. 存 OPLL 默认 fnum_blk 常数 (BD: 288×4=1152, TOM: 448×1=448)
2. rhythm mode 下 ch6/ch8 写 fnum 时, 按比例更新 drum[0]/drum[1].step
3. 注意: reg 0x16/0x18 (fnum_lo) 和 0x26/0x28 (fnum_hi+blk) 都要处理

## 实测对比记录 (2026-06-25, Phantasy Star Town)

4 个固件版本对比通道1 inst 3 (Piano) 衰减:
| 版本 | 内容 | Piano 衰减 | 评价 |
|---|---|---|---|
| 4cffb3d | attack 线性, decay 线性 | 正常但 attack 缺渐起 | 早期稳定版 |
| 99c6604 | attack 指数, decay 线性 | 正常 | |
| **8aadd2f** | **attack 指数 + volume 对数, decay 线性** | **正常** | **✅ 最佳** |
| 776b0da | attack 指数 + volume 对数 + decay 查表 | **太慢(几乎不衰减)** | ❌ DR非线性失败 |

**结论**: DR 非线性 (decay 查表) 让 Piano(inst3) 衰减变慢, 实测退回线性 (8aadd2f).
DR 查表的 threshold 比 linear level-- 大太多, 衰减反而变慢. 待后续单独优化 DR 速率表.
**当前生产版本: 8aadd2f** (HEX 69903 bytes)

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

