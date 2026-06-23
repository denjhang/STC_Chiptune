# FDS (Famicom Disk System) 音源芯片集成进度 (2026-06-23)

NES FDS 是第六个集成进 STC32G144K 固件的音源芯片 (继 AY8910/SN76489/SCC/NES APU/GB DMG).
本文档记录 FDS 从选型到移植的完整过程.

总览状态见 `README.md`, libvgm 完整命令表见 `docs/VGM_COMMAND_TABLE_libvgm.md`.

## 0. 背景: FDS 是什么 FM

FDS 是**任天堂 1986 年为 Famicom Disk System 自制**的 FM 音源芯片.
和雅马哈 YM2413 的 FM **完全不同机制**:

| 维度 | FDS | YM2413 |
|------|-----|--------|
| 调制类型 | 频率/相位调制 (查表+加法) | 正弦波相位调制 (sin×sin) |
| 载波波形 | **任意 64 步波形** (自定义 6-bit) | 固定正弦波 |
| 调制器波形 | 3-bit 表 (8 种斜率) | 固定正弦波 |
| 运算量 | 加法 + 查表 | sin 查表 + 乘法 × 2 operator |
| 通道数 | 1 | 9 (+5 鼓) |
| ROM 需求 | 无 (波形 RAM 运行时写) | 8KB 音色 ROM |
| RAM 需求 | ~0.5KB | ~10KB |

**FDS 计算量小** (加法+查表, 没有 sin 乘法), **非常适合 STC32G**.

## 1. 选型对比 (为什么选 FDS)

| 芯片 | FM? | ROM | RAM | 难度 |
|------|-----|-----|-----|------|
| **FDS** | 频率调制 (轻量) | 无 | 0.5KB | ★★☆ |
| SAA1099 | 无 | 无 | 0.5KB | ★★☆ |
| HuC6280 | 无 | 小波形 | 1KB | ★★☆ |
| WonderSwan | 无 | 无 | **64KB!** | ❌ |
| YM2413 | FM (重) | 8KB | 10KB | ★★★★★ |

FDS 和 SAA1099 都最现实, 但 FDS 的 FM 调制更有趣 (挑战性).

## 2. 实现细节

### 2.1 文件结构

| 文件 | 作用 |
|------|------|
| `src/fds.h` | 接口 (fds_init/wr/set_clock/render) |
| `src/fds.c` | Tick (调制器+载波+包络) + Write ($4040-$408A) + Render (RC 滤波) |

### 2.2 核心: Tick 函数 (移植自 np_nes_fds.c)

FDS 的 FM 合成流程 (每采样):
1. **clock envelopes** (2 个 ramp 包络: EVOL 音量 + EMOD 调制增益)
2. **clock modulator**: 推进 phase, 查 TMOD 波形表, BIAS 表累加 mod_pos
3. **clock carrier**: mod_pos × EMOD → 改变载波瞬时频率 → 推进 phase → 读 TWAV 波形
4. **RC 低通滤波** (cutoff 2000Hz)

### 2.3 C251 适配

- `calloc/malloc` → xdata 静态变量 (~0.5KB)
- `exp()` → RC 常量预计算硬编码 (rc_k=2322, rc_l=1774, @22050Hz)
- `bool` → u8, INT32 → s32
- `RATIO_CNTR` → nes.c 同款 base_count/base_incr 24-bit 定点

### 2.4 VGM 命令路由 (关键, 容易出错)

FDS 和 NES APU **共用 0xB4 命令**, libvgm `Cmd_NES_Reg` 做 FDS remap:

```
VGM reg 0x00-0x17 → NES APU
VGM reg 0x3F      → FDS $4023 (master I/O)
VGM reg 0x20-0x3E → FDS, remap 成 0x80|(reg&0x1F) → nesintf → NES_FDS_Write(0x4080+)
VGM reg 0x40-0x8A → FDS $4040-$408A 直接
```

下位机 main.c 0xB4 分支路由:
```c
u8 ofs = r & 0x7F;
if (ofs <= 0x17) nes_wr(ofs, d);         // NES APU
else {
    fds_active = 1;
    if (ofs == 0x3F) fds_wr(0x23, d);     // $4023
    else if (ofs >= 0x20 && ofs <= 0x3E) fds_wr(0x80 | (ofs & 0x1F), d);  // remap
    else if (ofs >= 0x40 && ofs <= 0x8A) fds_wr(ofs, d);                  // 直接
}
```

## 3. 调试记录

### 3.1 Bug: 路由错误导致无声

**症状**: Arumana no Kiseki 播放正常但无声.

**根因**: fds_wr 把 `0x80-0x9F` 全部 return 了. 但 VGM reg 0x20-0x3E 经
remap 成 0x80|(reg&0x1F), 对应 FDS $4080-$408A 寄存器 (音量/频率/包络/调制).
全部被忽略 → 无声.

**修复**: 去掉 0x80-0x9F 的 return, 让 0x80-0x8A 走 switch case ($4080-$408A).

### 3.2 Bug: 包络不正确 (Zelda)

**症状**: Zelda 01 Title BGM 的 FDS 声音包络不对 (没有渐强渐弱).

**根因**: `fds_init` 设 `master_env_speed = 0`. 但 Tick 函数里
`master_env_speed != 0` 才跑包络.

**关键**: FDS BIOS reset **自动写 $408A = 0xE8** (master envelope speed).
很多游戏 (如 Zelda) 不显式写 $408A, 依赖 BIOS 默认值. 如果设 0, 包络永远不跑.

**修复**: `fds_init` 设 `master_env_speed = 0xE8` (对齐 libvgm device_reset line 226+236).

## 4. 增益调整

FDS 输出范围大, 和其他音源混音时容易饱和. 调整历程:
- `/4`: 音量减半 (饱和压低其他通道)
- `/8`: 仍偏大
- `/16`: 略好
- `/32`: 最终值 (和其他音源平衡)

SCC 也调整: `/2` → `/4`.

## 5. 编译信息

- xdata: 29998 → 30410 (FDS 结构体 ~0.5KB)
- HEX: 55417 字节
- 0 ERROR

## 6. 测试 VGM

- `vgm/fds/good/Zelda_no_Densetsu/` (10 曲, Zelda FDS)
- `vgm/fds/Arumana/` (12 曲, Arumana no Kiseki)
- 其他: Bio Miracle, Metroid, Dracula II 等

## 7. 被证伪的假设

1. ❌ "FDS reg 0x80-0x9F 是 $4020-$403F, 未用可忽略" — 错, 是 $4080-$408A remap
2. ❌ "master_env_speed 初始值 0 即可" — 错, BIOS 默认 0xE8

## 8. 教训

1. **移植时 init/reset 的隐式行为容易漏**. FDS BIOS reset 自动写 $408A=0xE8,
   不看 device_reset 源码根本不知道. (和 NES APU 的 $4015 自动 enable 同类问题)
2. **VGM 命令路由要多看一层**. libvgm Cmd_NES_Reg remap + nesintf 再映射,
   不看 nesintf.c 只看 vgmplayer_cmdhandler.cpp 会漏.
