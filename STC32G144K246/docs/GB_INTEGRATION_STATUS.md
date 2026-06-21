# GB DMG 集成进度 (2026-06-21)

切换到 zcode 前的完整上下文快照。读完此文档即可继续 GB 调试，不需要回看对话历史。

---

## 1. 目标

把 GameBoy DMG APU 加入 STC32G144K246 usb_cdc_test 固件，作为第 6 个音源 (前 5 个: AY/SN/SCC/NES/已稳定)。

## 2. 已完成

### 2.1 代码 (已编译通过, 0 ERROR, 4 pre-existing WARNING)

| 文件 | 改动 |
|------|------|
| [src/gb.h](../usb_cdc_test/src/gb.h) | **新建**. GB_CLOCK=4194304Hz, GB_BASE_INCR=3191326266 (24-bit 累加器归一化到 22050Hz) |
| [src/gb.c](../usb_cdc_test/src/gb.c) | **新建**. 从 libvgm `emu/cores/gb.c` 完整重写, 4 通道 (方波1+扫频, 方波2, 波形 RAM, 噪声 LFSR), frame sequencer 8 步 512Hz |
| [src/main.c](../usb_cdc_test/src/main.c) | include gb.h / gb_active flag / gb_init() 启动 / ISR mix / 0xB3 命令 / 0xF0 reset 复位 |
| [build.py](../usb_cdc_test/build.py) | SOURCES 加入 "gb" |
| [docs/README.md](README.md) | 五音源→六音源, incr 表加 GB 行, VGM 协议加 0xB3, 新增 GB 实现要点章节 |

### 2.2 libvgm 参考路径

- 权威源码: `D:\working\vscode-projects\Reference_Project\vgm_libs\libvgm-master\emu\cores\gb.c` (1342 行, BSD-3-Clause, by Wilbert Pol, Anthony Kruize)
- 弃用: `STC32G12K128/gb.c` (554 行, 用户明确说"未经验证")

### 2.3 关键参数

```
GB_CLOCK     = 4194304 Hz        (GB CPU 主时钟)
GB_GETA_BITS = 24                (24-bit 定点累加器)
GB_BASE_INCR = 3191326266 UL     (= 4194304 × 2^24 / 22050, 超 LONG_MAX 但 u32 内)
每采样 incr   ≈ 190 cycles       (= 4194304 / 22050)
FRAME_CYCLES = 8192              (frame sequencer 步进, 512 Hz)
```

### 2.4 VGM 协议

| 命令 | 含义 | 格式 |
|------|------|------|
| 0xB3 | GB 寄存器写 | `[0xB3][reg][data]`, reg 是 GB IO 偏移 (NR10=0x00..NR52=0x16, AUD3W0=0x20..0x2F) |
| 0xF0 | 全音源 reset | 调用 sn_init/ay_init/scc_init/nes_init/**gb_init**, 清 active 标志 |

GB 静音通过 NR52=0: `[0xB3, 0x16, 0x00]` (固件内不再 memset, 只清 on 标志)。

## 3. 当前确认的问题 ⚠️

### 3.1 下位机死机 (严重, 需断电才能重新下载)

**症状**: 用户测试 GB VGM 播放时下位机死机, 必须断电才能恢复烧录。py 端也跟着卡死 (因为 USB CDC 串口阻塞)。

**已修复一处**: NR52 power-off 分支原先在主循环 `process_uart` 里 memset 整个 SOUND 结构 (4 通道 × 43 字节), 和 Timer0 ISR 的 `gb_render` / `gb_update_*` 存在数据竞争。改成只清 `on` 标志, 真正清零交给 `gb_init()` (0xF0 reset)。

**尚未验证**: 上述修复是否彻底解决死机。需要断电后烧录新 HEX 测试。

**未排除的其他可能根因** (按可能性排序):

1. **ISR 时间预算超限** — 6 个音源 render 同在 Timer0 ISR (22050Hz = 45μs 预算)。GB 的 `gb_update_state` 跨 frame 时会一次性调 4 个 channel update, 每个 channel 又有 while 循环。虽然有 `guard < 4096` 上限, 但单采样最多 ~95 次迭代 × 4 通道仍可能超时
2. **`gb_ctrl.cycles |= 7 * FRAME_CYCLES`** — NR52 power-on 时 cycles 大跳到 57344, 首次 `gb_update_state` 时的 `cycles_current_frame` 行为需验证
3. **USB CDC 缓冲压力** — GB VGM 命令密度极高 (一首 10 秒曲子 2744 条 0xB3), RX1_Buffer (2048 字节环形) 可能被瞬间填满, 但理论上满时丢弃不会死机
4. **`gb_snd3.cycles_left = -6`** — NR34 key-on 时给 wave 通道一个负值延迟, 这个 s32 负值在后续 `+= cycles` 后才变正, 期间 `while (cycles_left >= 2)` 不会进循环, 应该安全

### 3.2 py 端目前对 GB 的处理 (vgm_player.py)

**已经够用**:
- `0xB3` 在 `play_vgm()` line 378 已透传 (`ser.write(data[pos-1:pos+2])`)
- `scan_vgm_stats()` line 180 已统计 GB 命令数
- `dump_vgm()` line 217 已打印 GB 命令
- `parse_vgm_header()` line 143 扫 0x67 数据块时把 0xB3 当 3 字节命令跳过

**不需要的改动**:
- GB 时钟下发 ❌ — GB DMG 时钟固定 4194304Hz, 不像 NES 有 NTSC/PAL, 硬编码在 `gb.h`
- GB 波形 RAM 下发 ❌ — 真实 GB VGM (Spring in Your Step) 没有 0x67 type=0xC5 数据块, 用默认波形即可

**可能需要的改动** (待定):
- GB 曲目开播前发一个显式 reset (`0xF0`)? 目前依赖 playlist 模式切歌时自动 reset, 单曲播放不会 reset
- 播放结束静音 GB (`[0xB3, 0x16, 0x00]`)? 防止下首歌有 GB 残留

## 4. 验证过的真实 GB VGM 数据

文件: `vgm/gb/01 Spring in Your Step.vgz`

```
magic      : b'Vgm '
version    : 0x161 (VGM 1.61)
gb_clock   : 4194304 Hz (header 0x80)
nes_clock  : 0 (header 0x84, 无)
data_off  : 192 (相对偏移 140 + 0x34)
eof        : 12331
0x67 blocks: 0 (无数据块)
0xB3 命令  : 2744 条
播放时长   : 10.8 秒
GB reg 范围: 0x00-0x2F (无越界)
```

VGM 1.61 的 data_off 字段 (header 0x34) 是**相对偏移**, 实际位置 = `0x34 + 值`。第一次分析时算错了, 误以为开头全是 0x00 padding。

## 5. 调试 GB 时调用的工具和命令

### 5.1 解压 .vgz 看字节布局

```bash
py -3 -c "
import gzip, struct
with open('vgm/gb/01 Spring in Your Step.vgz', 'rb') as f: raw = f.read()
data = gzip.decompress(raw)
print('size:', len(data))
print('version:', hex(struct.unpack_from('<I', data, 0x08)[0]))
print('gb_clock:', struct.unpack_from('<I', data, 0x80)[0])
rel = struct.unpack_from('<I', data, 0x34)[0]
abs_off = rel + 0x34
print(f'data_off abs: {abs_off}')
print('first 32 bytes:', ' '.join(f'{b:02X}' for b in data[abs_off:abs_off+32]))
"
```

### 5.2 扫整曲统计命令分布

```bash
py -3 -c "
import gzip, struct
with open('vgm/gb/01 Spring in Your Step.vgz', 'rb') as f: raw = f.read()
data = gzip.decompress(raw)
data_off = struct.unpack_from('<I', data, 0x34)[0] + 0x34
end = struct.unpack_from('<I', data, 0x04)[0] + 4
pos = data_off
cmd_count = {}
while pos < end:
    b = data[pos]
    cmd_count[b] = cmd_count.get(b, 0) + 1
    if b == 0x66: break
    elif b == 0x67:
        sz = struct.unpack_from('<I', data, pos + 3)[0] & 0x7FFFFFFF
        pos += 7 + sz
    elif b in (0xA0, 0x51, 0xB3, 0xB4, 0xBD): pos += 3
    elif b == 0x50: pos += 2
    elif b == 0xD2: pos += 4
    elif b == 0x61: pos += 3
    elif b in (0x62, 0x63): pos += 1
    elif 0x70 <= b <= 0x9F: pos += 1
    else: pos += 1
print('top:', sorted(cmd_count.items(), key=lambda x: -x[1])[:10])
"
```

### 5.3 验证 base_incr 计算

```bash
py -3 -c "print(int(4194304 * (1<<24) / 22050))"  # = 3191326266
py -3 -c "print(3191326266 >> 24)"  # = 190 cycles/sample
```

### 5.4 编译

```bash
cd STC32G144K246/usb_cdc_test
py -3 build.py
```

输出: `src/build/MAIN.hex` (当前 48297 bytes)

### 5.5 播放 GB 测试

```bash
cd STC32G144K246/usb_cdc_test
py -3 tools\vgm_player.py --list --vgm-dir ..\..\vgm\gb
py -3 tools\vgm_player.py 1 --vgm-dir ..\..\vgm\gb
```

## 6. 待办 (按优先级)

1. **[关键]** 用户断电后烧录新 HEX, 先测 AY 曲子 (回归测试), 再测 GB 曲子, 确认下位机死机是否解决
2. 若仍死机: 关键怀疑 ISR 时间预算。可临时把 `mix *= 8` 改成 `mix *= 4` (降低增益不影响死机), 或暂时注释掉 ISR 里的 `if (gb_active) mix += gb_render();` 确认是否 GB 引起
3. 若 GB 能播但有杂音/卡音: 检查 frame sequencer 时序, 对照 libvgm `gameboy_update` (line 1133)
4. py 端: 在 `play_vgm` 开头加 `ser.write(bytes([0xF0]))` 显式 reset, 确保每次播放从干净状态开始 (当前只在 playlist 切歌时 reset)
5. GB 静音收尾: 在 `play_vgm` 结束前发 `[0xB3, 0x16, 0x00]` (NR52=0)
6. 全部稳定后 commit, 打包 zip, 更新 README 截图

## 7. C251 编译器踩坑记录 (gb.c 开发时遇到)

1. **C89 严格模式** — 不支持 mixed declarations. 所有局部变量声明必须在 block 开头, 否则 `ERROR C25 syntax error`
2. **`data` 是保留字** — 指内部 RAM 段 (direct addressing). 参数名用 `data` 会触发 `ERROR C25 syntax error near 'data'`. 改用 `val`
3. **`static` 前向声明** — 原版 nes.c 风格 `static void foo(...);` 在 C251 里有时解析异常, 推荐直接按依赖顺序定义函数
4. **u8 循环计数器上限** — nes.c 当年死机 bug 就是 `for(i=0; i<4096; i++)` 用 `u8 i` → 死循环. gb.c 没有这种循环, 但 `while` 循环必须加 `guard < 4096` 护栏防止 ISR 卡死

## 8. 当前 HEX 信息

- 路径: [src/build/MAIN.hex](../usb_cdc_test/src/build/MAIN.hex)
- 大小: 48297 bytes
- Program Size: data=68.5 edata+hdata=256 xdata=21239 const=379 code=16900
- 编译时间: 2026-06-21
- 未 commit (等用户烧录验证后再提交)

## 9. 关键文件路径速查

```
固件:
  STC32G144K246/usb_cdc_test/src/gb.c           ← 新建
  STC32G144K246/usb_cdc_test/src/gb.h           ← 新建
  STC32G144K246/usb_cdc_test/src/main.c         ← 改 (ISR/0xB3/0xF0)
  STC32G144K246/usb_cdc_test/build.py           ← 改 (SOURCES)
  STC32G144K246/usb_cdc_test/src/build/MAIN.hex ← 重新编译产物

文档:
  STC32G144K246/docs/README.md                  ← 改 (六音源章节)
  STC32G144K246/docs/GB_INTEGRATION_STATUS.md   ← 本文件

工具:
  STC32G144K246/usb_cdc_test/tools/vgm_player.py ← 暂未改 GB 相关

参考:
  Reference_Project/vgm_libs/libvgm-master/emu/cores/gb.c  ← libvgm 原版
  STC32G12K128/gb.c                                          ← 弃用 (未验证)

VGM 测试文件:
  vgm/gb/*.vgz   (10 首, Kirby's Dream Land)
```

## 10. GB 文件结构速查 (libvgm gb.c 对齐)

### 10.1 SOUND 结构 (43 字节, C251 1-byte 对齐)

```c
typedef struct {
    u8  reg[5];              // 寄存器原始值 (NR10-14 / NR21-24 / ...)
    u8  on;                  // 通道是否开启
    u8  channel;             // 通道号 1/2/3/4
    u8  length;              // 长度计数器
    u8  length_mask;         // 长度掩码 (0x3F 或 0xFF)
    u8  length_counting;     // 长度计数是否激活
    u8  length_enabled;      // NRx4 bit6 写入后是否启用长度
    s32 cycles_left;         // 剩余 cycles (跨采样累积小数部分)
    s8  duty;                // 方波 duty 索引 0-3
    u8  envelope_enabled;    // 包络是否激活
    s8  envelope_value;      // 当前音量 0-15
    s8  envelope_direction;  // 1=渐强, -1=渐弱
    u8  envelope_time;       // 包络周期
    u8  envelope_count;      // 包络计数器
    s8  signal;              // 当前波形输出值 (-1/+1 或波形采样)
    u16 frequency;           // 11-bit 频率
    u16 frequency_counter;   // 频率计数器
    u8  sweep_enabled;       // 扫频激活 (仅 CH1)
    u8  sweep_neg_mode_used; // 扫频负方向已使用 (禁止再切正)
    u8  sweep_shift;         // 扫频移位
    s8  sweep_direction;     // +1/-1
    u8  sweep_time;          // 扫频周期
    u8  sweep_count;         // 扫频计数器
    u8  level;               // CH3 输出电平 (NR32 bit5-6)
    u8  offset;              // CH3 波形偏移 (0-31)
    u32 duty_count;          // duty 步进计数器
    s8  current_sample;      // CH3 当前采样值
    u8  sample_reading;      // CH3 正在读波形 RAM
    u8  noise_short;         // CH4 7-bit LFSR 模式
    u16 noise_lfsr;          // CH4 15-bit LFSR 状态
} SOUND;
```

### 10.2 关键函数

- `gb_init()` — memset 所有结构, 设通道号/长度掩码, 写默认 DMG 波形 RAM, `gb_ctrl.on = 1`
- `gb_wr(reg, val)` — 波形 RAM 直接写; 其他走 `gb_sound_w_internal`
- `gb_sound_w_internal(offset, val)` — switch 处理 NR10-NR52
- `gb_render()` — 每采样调用一次, 推进 frame sequencer + 4 通道 update + 混音
- `gb_update_square/wave/noise` — 单通道 update, 有 `guard < 4096` 上限防 ISR 卡死
- `gb_update_state(cycles)` — frame sequencer 8 步调度 (length/sweep/envelope)
- `gb_tick_length/sweep/envelope` — frame sequencer 触发的计数器递减

### 10.3 frame sequencer 8 步 (按 gb_ctrl.cycles / FRAME_CYCLES & 7)

| step | 动作 |
|------|------|
| 0 | length (所有 4 通道) |
| 1 | - |
| 2 | sweep (CH1) + length |
| 3 | - |
| 4 | length |
| 5 | - |
| 6 | sweep (CH1) + length |
| 7 | envelope (CH1/CH2/CH4) |

## 11. 切换到 zcode 后的第一步建议

1. 先读本文件了解全貌
2. 等用户反馈烧录新 HEX 后是否还死机
3. 如果死机解决: commit + 测更多 GB 曲子 + 完善 py 端
4. 如果仍死机: 按 §3.1 "未排除的其他可能根因" 逐项排查, 首要怀疑 ISR 时间预算

---

## 12. 最终修复记录 (2026-06-21, GB 成功出声)

经过长时间排查, GB 从"卡死无声"到"正常出声"经过 **三个独立 bug** 的修复:

### Bug 1: NR52 power-off memset 数据竞争 (已修复)
- **症状**: 早期版本下位机死机需断电
- **根因**: NR52=0 时在主循环 memset 整个 SOUND 结构, 和 Timer0 ISR 的 gb_render 数据竞争
- **修复**: NR52 power-off 只清 on 标志, 真正清零交给 gb_init() (0xF0 reset)

### Bug 2: 混音公式方向错误 (已修复)
- **症状**: 不卡死但完全无声 (DAC 几乎只剩量化噪声)
- **根因**: libvgm 的 `<<6` (放大 64 倍) 被误抄成 `>>4` (缩小 16 倍), 一来一回差 1024 倍
- **验证**: Python 仿真器 (tools/gb_sim.py) 喂真实 VGM, 修复前平均幅度 0.73, 修复后 1100
- **修复**: `mono = (left+right)/2; mono *= vol_avg; mono <<= 6` (对齐 libvgm pump up)
- **教训**: 仿真器是排查"代码对但实机不响"的利器, 能定量验证 render 输出

### Bug 3: ISR 超时饿死 USB CDC (已修复, 最难定位)
- **症状**: py 播放 GB 时 `ser.write()` 永久阻塞, 不响应 Ctrl+C; 流水灯正常; 其他音源正常
- **诊断关键**: 二分法 — ISR 注释掉 `gb_render()` 调用后 py 立刻不卡 → 100% 证明是 render 耗时
- **根因**: libvgm 原版 `gb_update_wave` 用 `while(cycles_left >= 2)` 逐 GB cycle 推进,
  22050Hz 下每采样循环 **95 次**, 循环体含除法/表查找 → ISR 超 45μs 预算 3-4 倍 → USB CDC 中断饿死
- **对比 NES**: `nes_update_square` 循环体只有减法+加法, 循环 ~10 次, 所以 NES 5 通道不卡
- **修复**: wave 改 NES 风格 phaseacc (cycles_left 累加到 period 才推进), 循环 95→10 次;
  循环体用 `>>1` 代替 `/2`, level 用 if/else 代替变量移位
- **教训**: 移植 libvgm 到 MCU 不能照搬 PC 算法, 必须评估 ISR 内循环次数和循环体重量

### 被证伪的假设 (避免重复踩坑)
1. ❌ C251 overlay 优化导致 gb_wr/gb_render 数据竞争 — 加 `NOOVERLAY` 链接无效
2. ❌ VGM_CMD_LEN 表把 0xB3 误设为 4 字节 — GB VGM 没有未知命令, 不影响
3. ❌ @STCISP# 序列误触发 — 流水灯正常证明没复位
4. ❌ py 播放器命令发送 bug — 模拟运行证明播放器逻辑 13.4s 正常跑完
5. ❌ guard 上限调小 (4096→48→16) — 治标不治本, cycles 丢失导致无声或雪崩
6. ❌ 旧版 12K128 gb.c 移植 — 同样卡死 (旧版 render 也是逐 cycle 循环)

### 最终 gb.c 关键参数
```
GB_CLOCK     = 4194304 Hz
GB_GETA_BITS = 24
GB_BASE_INCR = 3191326266  (4194304 × 2^24 / 22050)
每采样 incr  ≈ 190 GB cycles
wave period  = 2 × (0x800 - frequency) GB cycles
wave 循环次数 ≈ 190 / period ≈ 5-10 次 (可控)
noise period = 8 ~ 32768 GB cycles
noise 循环次数 ≈ 190 / 8 = 24 次 (最坏, guard=32 保底)
```

### 产物
- `src/build/MAIN.hex` — GB 出声版本
- `tools/gb_sim.py` — Python GB 仿真器 (排查工具, 不参与编译)
