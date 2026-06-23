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

- **目标**：下位机 s8 核心（64 点 ±31 波形）通过**只改表**对齐 emu2413 包络行为，**严禁改架构**（不改 round-robin、不改 env_tick 逻辑、不改输出公式、不改波形/相位/ml/结构体）。
- **下位机真实限制**（da1cf8a 基线）：
  - 64 点 s8 波形，振幅 **±31**（不是 ±127）；halfsin 负半周**镜像**（不是静音）
  - ml_table `[1,2,4,6,8,10,12,14,16,18,20,22,24,24,24,24]`（和 emu 不同）
  - 相位 16.16 定点 u32，`pos>>16` 取索引，blk-1 修正八度
  - 包络 level(0~31) **线性**，env_cnt/env_step **u8**，round-robin 每 16 采样 tick 一个 op
  - 输出 `(wave × (level+1) × (tl+1)) >> 10`，结果 s8，最后 `<<1`
- **PC 仿真工具**：`tools/fw_real_sim.py`（render_fw_real，严格 1:1 忠实下位机所有限制）。先在此验证再改下位机。
- **已完成（commit 93f7cb6）**：AR/DR/RR 三张表替换 ym_env_cnt 单表，反推自 emu2413 attack/decay/release 全程时间。实测不死机、包络更接近、**音量偏小（待调）**。
- **当前问题**：音量偏小。注意 da1cf8a 原版音量在实机合适，偏差来自 PC emu2413 输出标定不同（±2042 vs 下位机 ±62），**不是下位机音量 bug**，需通过整体后处理放大对齐，不要改 `>>10`/`<<1` 输出公式。
- **教训**：之前 commit 873a3a5 的下位机改造（eg_out/LEVEL_GAIN/LFO/19-bit 相位）全部废弃——改了架构导致无声。下位机改动必须严格"只改表"。

## 项目常用命令

- 构建固件：`cd STC32G144K246/usb_cdc_test && py -3 build.py`
- 打包源码：`python tools/pack_144k_src.py`
- 播放 VGM：`cd STC32G144K246/usb_cdc_test && py -3 tools/vgm_player.py --vgm-dir D:/working/vscode-projects/STC_Chiptune/vgm/<子目录> --port COM24 <编号>`
- YM2413 WAV 生成：`cd STC32G144K246/usb_cdc_test && py -3 tools/ym2413_wav_gen.py`
