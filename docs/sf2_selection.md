# SF2 采样乐器精选

从多个 SF2 音色库提取、修复循环点、渲染试听后筛选的乐器列表。
所有采样已降采样至 17640Hz，存放在 `D:/working/vscode-projects/Reference_Project/STC-MCU/sf2_extract/` 下对应子目录。

## 音色库来源

| 库 | 路径 | 采样数 | 好 loop |
|---|------|--------|---------|
| SNES (31_Minutos) | `snes/` | 27 | 12 |
| GBA (Game Boy Advance) | `gba/` | 204 | 120 |
| SNES Unofficial | `snes_unofficial/` | 167 | 77 |
| microgm | `microgm/` | 343 | 51 |

## 全部候选 (25个, 按 ADPCM 从小到大)

| # | 乐器 | 来源 | 采样数 | PCM | ADPCM@17640 | orig_pitch |
|---|------|------|--------|------|-------------|------------|
| 1 | L_2 (Piano) | snes_unofficial #35 | 2328 | 4.5KB | 1.16KB | 40 |
| 2 | EB_257 (Slap Bass) | snes_unofficial #34 | 3669 | 7.2KB | 1.84KB | 26 |
| 3 | Shakuhachi 3 | microgm #211 | 3901 | 7.6KB | 1.95KB | 81 |
| 4 | SOM_8 (Oboe) | snes_unofficial #102 | 4021 | 7.9KB | 2.05KB | 28 |
| 5 | YC_33 (Trumpet) | snes_unofficial #45 | 4198 | 8.2KB | 2.13KB | 52 |
| 6 | Blow 1 | microgm #207 | 5153 | 10.1KB | 2.58KB | 60 |
| 7 | GT_9 (Oboe) | snes_unofficial #69 | 5468 | 10.7KB | 2.79KB | 21 |
| 8 | DKC2_27 (Strings) | snes_unofficial #50 | 6315 | 12.3KB | 3.21KB | 71 |
| 9 | SM_136 (Harp) | snes_unofficial #90 | 7373 | 14.4KB | 3.77KB | 73 |
| 10 | MP_95 (Guitar) | snes_unofficial #91 | 7444 | 14.5KB | 3.80KB | 40 |
| 11 | YC_25 (E.Piano) | snes_unofficial #44 | 9208 | 18.0KB | 4.60KB | 38 |
| 12 | FF4_5 (Pipe Organ) | snes_unofficial #47 | 11254 | 22.0KB | 5.74KB | 57 |
| 13 | DKC2_36 (E.Guitar) | snes_unofficial #51 | 11712 | 22.9KB | 5.86KB | 64 |
| 14 | DKC2_15 (Violin) | snes_unofficial #48 | 12806 | 25.0KB | 6.41KB | 64 |
| 15 | MMX_10 (Strings) | snes_unofficial #81 | 12559 | 24.5KB | 6.41KB | 52 |
| 16 | MMX_12 (Accordion) | snes_unofficial #82 | 12736 | 24.9KB | 6.50KB | 48 |
| 17 | SOM_6 (Voice) | snes_unofficial #101 | 13300 | 26.0KB | 6.79KB | 47 |
| 18 | SF_29 (Strings) | snes_unofficial #58 | 13723 | 26.8KB | 6.99KB | 48 |
| 19 | EB_174 (Sax) | snes_unofficial #30 | 15276 | 29.8KB | 7.64KB | 41 |
| 20 | Strings | snes #18 | 16640 | 32.5KB | 8.32KB | 63 |
| 21 | SM_54 (Voice) | snes_unofficial #87 | 19509 | 38.1KB | 9.96KB | 47 |
| 22 | FF3_15 (Voice) | snes_unofficial #96 | 20180 | 39.4KB | 10.30KB | 52 |
| 23 | FZ_9 (Tuba) | snes_unofficial #68 | 25933 | 50.7KB | 13.23KB | 50 |
| 24 | SOM_18 (Strings) | snes_unofficial #105 | 26299 | 51.4KB | 13.42KB | 50 |
| 25 | FF4_4 (Harp) | snes_unofficial #46 | 35280 | 68.9KB | 17.99KB | 57 |
| | **合计** | | **344298** | **672.3KB** | **172.1KB** | |

## 精选 (去重, 17个, ADPCM 91.9KB)

每组同类型只保留最小的一个，17 乐器覆盖 13 种音色类型。

| # | 乐器 | 来源 | 采样数 | PCM | ADPCM@17640 | orig_pitch |
|---|------|------|--------|------|-------------|------------|
| 1 | L_2 (Piano) | snes_unofficial #35 | 2328 | 4.5KB | 1.16KB | 40 |
| 2 | EB_257 (Slap Bass) | snes_unofficial #34 | 3669 | 7.2KB | 1.84KB | 26 |
| 3 | Shakuhachi 3 | microgm #211 | 3901 | 7.6KB | 1.95KB | 81 |
| 4 | SOM_8 (Oboe) | snes_unofficial #102 | 4021 | 7.9KB | 2.05KB | 28 |
| 5 | YC_33 (Trumpet) | snes_unofficial #45 | 4198 | 8.2KB | 2.13KB | 52 |
| 6 | Blow 1 | microgm #207 | 5153 | 10.1KB | 2.58KB | 60 |
| 7 | DKC2_27 (Strings) | snes_unofficial #50 | 6315 | 12.3KB | 3.21KB | 71 |
| 8 | SM_136 (Harp) | snes_unofficial #90 | 7373 | 14.4KB | 3.77KB | 73 |
| 9 | MP_95 (Guitar) | snes_unofficial #91 | 7444 | 14.5KB | 3.80KB | 40 |
| 10 | YC_25 (E.Piano) | snes_unofficial #44 | 9208 | 18.0KB | 4.60KB | 38 |
| 11 | FF4_5 (Pipe Organ) | snes_unofficial #47 | 11254 | 22.0KB | 5.74KB | 57 |
| 12 | DKC2_36 (E.Guitar) | snes_unofficial #51 | 11712 | 22.9KB | 5.86KB | 64 |
| 13 | DKC2_15 (Violin) | snes_unofficial #48 | 12806 | 25.0KB | 6.41KB | 64 |
| 14 | MMX_12 (Accordion) | snes_unofficial #82 | 12736 | 24.9KB | 6.50KB | 48 |
| 15 | SOM_6 (Voice) | snes_unofficial #101 | 13300 | 26.0KB | 6.79KB | 47 |
| 16 | EB_174 (Sax) | snes_unofficial #30 | 15276 | 29.8KB | 7.64KB | 41 |
| 17 | FZ_9 (Tuba) | snes_unofficial #68 | 25933 | 50.7KB | 13.23KB | 50 |
| | **合计** | | **183514** | **358.5KB** | **91.9KB** | |

去重去掉 8 个: GT_9(Oboe), SF_29/MMX_10/SOM_18/Strings(Strings), FF4_4(Harp), FF3_15/SM_54(Voice)
