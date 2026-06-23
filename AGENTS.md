# 项目记忆

## 打包/发布规则

- **源码打包必须用 `tools/pack_144k_src.py`**，不要自己用 `zipfile` 临时打包。
  - 用法：`python tools/pack_144k_src.py`
  - 输出：项目根目录 `STC32G144K246_src_{YYYYMMDD_HHMMSS}.zip`
  - 排除：`build/`、`__pycache__/`、`.git/`、`*.OBJ/.o/.exe/.lst/.map/.bak`
- **zip 文件被 .gitignore 忽略，不要 `git add -f` 强制加入**。打包产物是本地备份，不进 git。

## 不要动的文件

- **`备忘录.txt`** 是用户的私人笔记，绝对不要修改/追加。需要记录的事项写入本文件（`AGENTS.md`）。

## 关键路径

- **VGM 文件库**：`D:/working/vscode-projects/STC_Chiptune/vgm/`
  - 子目录：`ay8910/`、`sn76489/`、`scc/`、`nes/`（含 `gimmick/`、`kirby/`、`kkstar/`、`Battletoads/` 等）、`gb/`、`ws/`、`opll/opldrv/`（YM2413）
- **固件源码**：`STC32G144K246/usb_cdc_test/src/`（main.c, nes.c, gb.c, ay8910.c, sn76489.c, scc.c, ym2413.c, usb.c）
- **构建脚本**：`STC32G144K246/usb_cdc_test/build.py`
- **上位机工具**：`STC32G144K246/usb_cdc_test/tools/`（vgm_player.py, gb_sim.py, stc32_hid_flash.py）
- **YM2413 调参工具**：`STC32G144K246/usb_cdc_test/tools/ym2413_wav_gen.py`
  - 含忠实 emu2413 移植（render_emu2413 + EmuRhythm 鼓声）和 V3 s8 调参核心（render_fm_v3）
  - WAV 输出：`tools/wav_emu2413/`（参考，20 个）+ `tools/wav_fm_v3/`（V3，15 个）

## YM2413 下位机调参记录

### 正确流程（必须遵守）
1. **先在 PC 仿真验证**（`tools/fw_real_sim.py`），对照 emu2413 逐个乐器看 level 曲线
2. **fw_real_sim.py 必须和下位机 1:1 同步**——改下位机任何东西，仿真同步改、同步验证
3. **只改数值/表**，不改架构（round-robin/env_tick 逻辑/输出公式/波形/相位/ml/结构体）
4. PC 验证通过再改下位机，编译通过再烧录

### 下位机真实限制（da1cf8a 基线）
- 64 点 s8 波形，振幅 **±31**；halfsin 负半周**镜像**（不是静音）
- ml_table `[1,2,4,6,8,10,12,14,16,18,20,22,24,24,24,24]`（和 emu 不同）
- 相位 16.16 定点 u32，`pos>>16` 取索引，blk-1 修正八度
- 包络 level(0~31) **线性**，env_cnt/env_step **u8**，round-robin 每 16 采样 tick 一个 op
- 输出 `(wave × (level+1) × (tl+1)) >> 10`，结果 s8，最后 `<<1`

### 当前状态（commit 93bc777，实测最佳）
通过只改数值/表修复了以下问题，实机听感最接近 emu2413：
- **AR/DR/RR 三张表**（commit 93f7cb6）：替换 ym_env_cnt 单表，反推自 emu2413 速率
- **key_on env_cnt=0**（commit 1f45584）：消除 attack 启动延迟（旧值 250 导致延迟 4000 采样）
- **env_tick 加法计数器**（commit 1f45584）：修正旧减法 reset 250 的累积误差
- **AR≥7 瞬间到顶**（commit d84dee0）：atk≤2 时跳过 attack，解决 round-robin 精度下限
- **EG 语义修正**（commit 93bc777）：EG=1 sustaining 保持 / EG=0 non-sustaining 继续降（之前写反了）
- **car.tl 映射修正**（commit 93bc777）：`tl = vol>>1`（之前 `31-vol>>1` 写反，导致最大音量时输出极小）

### EG 语义（对齐 emu2413 get_parameter_rate）
- **EG=1 = sustaining**：sustain 阶段保持 SL 不降（step=0）
- **EG=0 = non-sustaining**：sustain 阶段继续用 RR 速率下降

### 教训
- commit 873a3a5 的下位机改造（eg_out/LEVEL_GAIN/LFO/19-bit 相位）全部废弃——改了架构导致无声
- PC 仿真必须严格同步下位机，否则验证结果是假的（fw_real_sim.py 早期没同步导致反复试错）

## 项目常用命令

- 构建固件：`cd STC32G144K246/usb_cdc_test && py -3 build.py`
- 打包源码：`python tools/pack_144k_src.py`
- 播放 VGM：`cd STC32G144K246/usb_cdc_test && py -3 tools/vgm_player.py --vgm-dir D:/working/vscode-projects/STC_Chiptune/vgm/<子目录> --port COM24 <编号>`
- YM2413 WAV 生成：`cd STC32G144K246/usb_cdc_test && py -3 tools/ym2413_wav_gen.py`
