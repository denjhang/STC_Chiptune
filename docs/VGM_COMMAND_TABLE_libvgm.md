# VGM 命令完整表 (libvgm 权威版)

> 来源: `Reference_Project/vgm_libs/libvgm-master/player/vgmplayer_cmdhandler.cpp`
> 的 `_CMD_INFO[0x100]` 表 + `Cmd_*` 函数实现。
> **此文件是项目参考, 不要删除** —— 上位机解析器必须按此表语义解析。

## 命令格式约定

每个命令的结构是 `{chipType, paramLen, handler}`，其中：
- `chipType` = 该命令对应的芯片类型 (0xFF = 无/特殊)
- `paramLen` = 命令**参数字节数** (不含命令字节本身)
  - 例: `0x50 SN76489` paramLen=2 → 总长 = 1(cmd) + 2 = 3 字节? **错!**
  - 实际 libvgm 的 paramLen 包含 cmd 字节本身: `0x50` paramLen=2 → cmd(1) + data(1) = 2 字节总长
  - 验证: `0x51 YM2413` paramLen=3 → cmd(1)+reg(1)+data(1) = 3 ✓
  - 验证: `0x62` paramLen=1 → 只有 cmd 字节 ✓
  - **所以 paramLen == 总命令长度 (含 cmd)**

## 完整命令表 (0x00 - 0xFF)

### 0x00 - 0x2F: 无效/保留
全部 `Cmd_invalid` 或 `Cmd_unknown`。

### 0x30 - 0x3F (paramLen=2)
| cmd | 芯片 | 说明 |
|-----|------|------|
| 0x30 | SN76489 | SN76489 register write (2nd chip) |
| 0x31 | AY8910 | AY8910 stereo mask |
| 0x32 | MSM5205 | MSM5205 register write |
| 0x3F | SN76489 | GameGear stereo mask (2nd chip) |

### 0x40 - 0x4F (paramLen=3,除 0x4F/0x50=2)
| cmd | 芯片 | 说明 |
|-----|------|------|
| 0x40 | Mikey | Ofs8_Data8 |
| 0x41 | K007232 | register write |
| 0x42 | K005289 | Ofs4_Data12 |
| 0x4F | SN76489 | GameGear stereo mask (paramLen=2) |

### 0x50 - 0x5F (paramLen=2 或 3)
| cmd | paramLen | 芯片 | 说明 |
|-----|----------|------|------|
| 0x50 | 2 | SN76489 | SN76489 register write `[0x50][data]` |
| 0x51 | 3 | YM2413 | `[0x51][reg][data]` |
| 0x52 | 3 | YM2612 port A | `[0x52][reg][data]` |
| 0x53 | 3 | YM2612 port B | `[0x53][reg][data]` |
| 0x54 | 3 | YM2151 | `[0x54][reg][data]` |
| 0x55 | 3 | YM2203 | `[0x55][reg][data]` |
| 0x56 | 3 | YM2608 port A | `[0x56][reg][data]` |
| 0x57 | 3 | YM2608 port B | `[0x57][reg][data]` |
| 0x58 | 3 | YM2610 port A | `[0x58][reg][data]` |
| 0x59 | 3 | YM2610 port B | `[0x59][reg][data]` |
| 0x5A | 3 | YM3812 (OPL2) | `[0x5A][reg][data]` |
| 0x5B | 3 | YM3526 (OPL) | `[0x5B][reg][data]` |
| 0x5C | 3 | Y8950 | `[0x5C][reg][data]` |
| 0x5D | 3 | YMZ280 | `[0x5D][reg][data]` |
| 0x5E | 3 | YMF262 (OPL3) port A | `[0x5E][reg][data]` |
| 0x5F | 3 | YMF262 (OPL3) port B | `[0x5F][reg][data]` |

### 0x60 - 0x6F (wait / data block)
| cmd | paramLen | 说明 |
|-----|----------|------|
| 0x61 | 3 | wait N samples (2 字节 LE): `[0x61][lo][hi]` |
| 0x62 | 1 | wait 735 samples (1/60 秒, NTSC frame) |
| 0x63 | 1 | wait 882 samples (1/50 秒, PAL frame) |
| 0x66 | 1 | **end of sound data** (终止/loop) |
| 0x67 | 变长 | **data block**: `[0x67][0x66][type][size:4 LE][data...]` |
| 0x68 | 0x0C | PCM RAM write: `[0x68][0x66][type][dbPos:3][wrtAddr:3][dataLen:3]` |

### 0x70 - 0x7F (paramLen=1, 短等待)
`0x7n` = wait `(n+1)` samples (1..16)。例: 0x70=wait 1, 0x7F=wait 16。

### 0x80 - 0x8F (paramLen=1, YM2612 PCM bank 流式)
`0x8n` = 从 PCM data block 0 取下一字节写到 YM2612 $2A, 然后 wait `n` samples。
配合 0xE0 (set YM2612 PCM offset) 使用。

### 0x90 - 0x95 (DAC Stream Control, 关键!)
| cmd | paramLen | 说明 |
|-----|----------|------|
| 0x90 | 5 | Setup Chip: `[0x90][streamID][chipType\|chipID][cmdHi][cmdLo]` |
| 0x91 | 5 | Set Data Bank: `[0x91][streamID][bankID][mode][cmd]` |
| 0x92 | 6 | Set Frequency: `[0x92][streamID][freq:4 LE]` |
| 0x93 | 0x0B | Play Data (location): `[0x93][streamID][startOfs:4][pbMode][soundLen:4]` |
| 0x94 | 2 | Stop: `[0x94][streamID]` (0xFF = stop all) |
| 0x95 | 5 | Play Data Block: `[0x95][streamID][sndID:2 LE][flags]` |

**NES APU DAC stream 用 0x90-0x95** —— Deflemask 的 NES DAC 通常走这条路径!
0x90 设置目标芯片 = NES APU (chipType=0x14), 目标命令 = $4011 写入。

### 0xA0 - 0xAF (paramLen=3, 第二片芯片)
| cmd | 芯片 |
|-----|------|
| 0xA0 | AY8910 (2nd) |
| 0xA1 - 0xAF | 各 YM 第二片 |

### 0xB0 - 0xBF (paramLen=3)
| cmd | 芯片 | 说明 |
|-----|------|------|
| 0xB0 | RF5C68 | `[0xB0][ofs\|chipID][data]` |
| 0xB1 | RF5C164 | |
| 0xB2 | PWM | Ofs4_Data12 |
| 0xB3 | **GameBoy DMG** | `[0xB3][reg][data]` (reg & 0x7F, bit7=chipID) |
| 0xB4 | **NES APU** | `[0xB4][reg][data]` (reg & 0x7F, bit7=chipID) |
| 0xB5 | YMW258 (MultiPCM) | |
| 0xB6 | uPD7759 | |
| 0xB7 | OKIM6258 | |
| 0xB8 | OKIM6295 | |
| 0xB9 | HuC6280 | |
| 0xBA | K053260 | |
| 0xBB | Pokey | |
| 0xBC | **WonderSwan** | `[0xBC][reg][data]` (写入时 reg \| 0x80) |
| 0xBD | **SAA1099** | `[0xBD][addr][data]` |
| 0xBE | ES5506 | |
| 0xBF | GA20 | |

### 0xC0 - 0xCF (paramLen=4 或 5)
| cmd | paramLen | 芯片 | 说明 |
|-----|----------|------|------|
| 0xC0 | 4 | SegaPCM | mem write `[0xC0][ofsLo][ofsHi\|chipID][data]` |
| 0xC1 | 4 | RF5C68 | mem write |
| 0xC2 | 4 | RF5C164 | mem write |
| 0xC3 | 4 | YMW258 | set bank |
| 0xC4 | 4 | QSound | `[0xC4][dataHi][dataLo][ofs]` |
| 0xC5 | 4 | SCSP | Ofs16_Data8 |
| 0xC6 | 4 | WonderSwan | mem write |
| 0xC7 | 4 | VSU-VUE (Virtual Boy) | |
| 0xC8 | 4 | X1-010 | |

### 0xD0 - 0xD6 (paramLen=4)
| cmd | 芯片 | 说明 |
|-----|------|------|
| 0xD0 | YMF278B | Port_Reg8_Data8 |
| 0xD1 | YMF271 | |
| 0xD2 | **K051649 (SCC1)** | `[0xD2][port\|chipID][reg][data]` |
| 0xD3 | K054539 | |
| 0xD4 | C140 | |
| 0xD5 | ES5503 | Port_Ofs8_Data8 |
| 0xD6 | ES5506 | Ofs8_Data16 |

### 0xE0 - 0xE1 (paramLen=5)
| cmd | 说明 |
|-----|------|
| 0xE0 | set YM2612 PCM data offset: `[0xE0][ofs:4 LE]` |
| 0xE1 | C352 register write |

### 0xE2 - 0xFF
全部 `Cmd_unknown` (paramLen=5)。

## NES APU 寄存器写入 (0xB4) — libvgm Cmd_NES_Reg 语义

```cpp
UINT8 ofs = fData[0x01] & 0x7F;   // reg 的 bit7 = chipID (第 2 片 NES)
// FDS remap (Famicom Disk System):
if (ofs == 0x3F) ofs = 0x23;                    // FDS I/O enable
else if ((ofs & 0xE0) == 0x20)                  // $4020-$403F
    ofs = 0x80 | (ofs & 0x1F);                  // remap 到内部 $80+
cDev->write8(dataPtr, ofs, fData[0x02]);
```

**普通 NES APU 寄存器 ($4000-$4017)**: reg 直接 = 内部 offset, 无 remap。

## data block (0x67) type 字段含义

来源: `Cmd_DataBlock` (line 681-802):

- `type & 0xC0`:
  - `0x00` = 未压缩 PCM/RAM/ROM data block
  - `0x40` = 压缩 data block
  - `0x80` = ROM/RAM write (用 `_VGM_ROM_CHIPS` 表)
  - `0xC0` = RAM write (用 `_VGM_RAM_CHIPS` 表)

### ROM/RAM write (type 0x80-0xBF) — `_VGM_ROM_CHIPS[0x40]`:
```
80 SegaPCM        81 YM2608 ADPCM-B   82 YM2610 ADPCM-A   83 YM2610 ADPCM-B
84 YMF278B ROM    85 YMF271            86 YMZ280B          87 YMF278B RAM
88 Y8950 DeltaT   89 YMW258            8A uPD7759          8B OKIM6295
8C K054539        8D C140              8E K053260          8F QSound
90 ES5506         91 X1-010            92 C352             93 GA20
94 K007232
```
格式: `[0x67][0x66][type][size:4 LE][memSize:4][dataOfs:4][data...]`

### RAM write (type 0xC0-0xFF) — `_VGM_RAM_CHIPS[0x40]`:
```
C0 RF5C68         C1 RF5C164           C2 NES APU          C3 K005289
E0 SCSP           E1 ES5503
```
**`type=0xC2` = NES APU RAM write!**
- bit5 (0x20) = 0: 16-bit addressing: `[addr:2 LE][data...]`
- bit5 (0x20) = 1: 32-bit addressing: `[addr:4 LE][data...]`

**对 NES APU, RAM write (0xC2) 就是写入 CPU 内存 ($C000-$FFFF) 的 DMC 采样数据。**
这正是 vgm_player.py 里 `nes_dmc_blocks` 的来源。

## PCM RAM write (0x68) — Cmd_PcmRamWrite

```cpp
UINT8 dbType = fData[0x02] & 0x7F;
UINT8 chipType = _VGM_BANK_CHIPS[dbType];  // dbType=0x07 -> NES APU
```
`_VGM_BANK_CHIPS[0x07] = 0x14` (NES APU)
格式: `[0x68][0x66][type][dbPos:3 LE][wrtAddr:3 LE][dataLen:3 LE]`
意思: 从 PCM bank 的 dbPos 位置取 dataLen 字节, 写到芯片 RAM 的 wrtAddr。

## DAC Stream Control (0x90-0x95) — NES DAC 的另一条路径

Deflemask NES 的 DAC 可能走 0x90-0x95:
1. `0x90 Setup`: 指定 streamID → NES APU (chipType=0x14), 命令号 = $4011 写
2. `0x91 SetData`: 绑定 PCM bank
3. `0x92 SetFreq`: 设置播放采样率
4. `0x93/0x95 PlayData`: 开始按频率从 bank 取样写 $4011
5. `0x94 Stop`: 停止

libvgm 内部 `dac_control` 会按设定频率自动从 PCM bank 取字节调 `write8($4011, byte)`。

## 解析器必须支持的命令 (NES APU 相关)

| 命令 | 用途 | vgm_player.py 当前是否支持 |
|------|------|---------------------------|
| 0xB4 | NES 寄存器写 ($4000-$4017) | ✅ 支持 (含 reg&0x7F 隐式) |
| 0x67 type=0xC2 | NES CPU RAM 写 (DMC 采样) | ✅ 支持 (nes_dmc_blocks) |
| 0x68 type=0x07 | PCM RAM write → NES | ❌ 不支持 |
| 0x90-0x95 | DAC Stream → NES $4011 | ❌ 不支持 |

**这首 feeblemask.vgm 需要确认走哪条路径。**
