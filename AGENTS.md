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
  - 子目录：`ay8910/`、`sn76489/`、`scc/`、`nes/`（含 `gimmick/`、`kirby/`、`kkstar/`、`Battletoads/` 等）、`gb/`、`ws/`
- **固件源码**：`STC32G144K246/usb_cdc_test/src/`（main.c, nes.c, gb.c, ay8910.c, sn76489.c, scc.c, usb.c）
- **构建脚本**：`STC32G144K246/usb_cdc_test/build.py`
- **上位机工具**：`STC32G144K246/usb_cdc_test/tools/`（vgm_player.py, gb_sim.py, stc32_hid_flash.py）

## 项目常用命令

- 构建固件：`cd STC32G144K246/usb_cdc_test && py -3 build.py`
- 打包源码：`python tools/pack_144k_src.py`
- 播放 VGM：`cd STC32G144K246/usb_cdc_test && py -3 tools/vgm_player.py --vgm-dir D:/working/vscode-projects/STC_Chiptune/vgm/<子目录> --port COM24 <编号>`
