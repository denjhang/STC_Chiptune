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

## YM2413 V3 调参记录

- **目标**：下位机 s8 核心（≤128 点 s8 波形）通过调参/改表对齐 emu2413 的音量和包络行为，**不重写、不改波形形状**。
- **当前状态（commit 8671f30）**：15/15 音色 RMS 偏差 < 0.32dB，听感几乎一致（仅音质差异）。
- **调参要点**：
  - `LEVEL_GAIN` 表：直接采样 emu2413 的 `eg_out → lookup_exp_table` 输出（eg=0→2042），不要用平滑 dB→线性。
  - mod 输出 `>>6`（peak=4086，匹配 emu mod 不做 `>>1`）；car 输出 `>>7`（peak=2042，匹配 emu car 做 `>>1`）。
  - tll 直接加到 eg_out（dB 域相加），不要用独立的 TL_ATTEN 衰减表。
  - LFO 查表：PM（pm_table 加相位增量）+ AM（am_table 加 eg_out）。
  - 波形表（64 点 s8 正弦/halfsin）保持原样——固件实测听感已接近原版。
- **关键发现**：emu2413 的 `lookup_exp_table` 是 7 级阶梯（不是平滑映射），载波经它变换后近似梯形/方波；这是 s8 正弦无法完全复制的，靠 LEVEL_GAIN 采样表补偿即可。
- **下位机移植提示**：V3 调参结果可直接套用到 `src/ym2413.c`——主要是改 LEVEL_GAIN 表内容 + mod/car 移位量 + 加 LFO 查表 + tll 加到 eg。当前 `ym2413.c` 用的是旧标定（`>>10`/`>>4` + LEVEL_GAIN 平滑），需更新。

## 项目常用命令

- 构建固件：`cd STC32G144K246/usb_cdc_test && py -3 build.py`
- 打包源码：`python tools/pack_144k_src.py`
- 播放 VGM：`cd STC32G144K246/usb_cdc_test && py -3 tools/vgm_player.py --vgm-dir D:/working/vscode-projects/STC_Chiptune/vgm/<子目录> --port COM24 <编号>`
- YM2413 WAV 生成：`cd STC32G144K246/usb_cdc_test && py -3 tools/ym2413_wav_gen.py`
