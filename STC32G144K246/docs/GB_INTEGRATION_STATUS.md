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
  STC32G144K246/usb_cdc_test/tools/vgm_player.py ← GB 相关已完善 (0xB3 透传/0xF0 reset/GD3+clock 显示, 见 §14)
  STC32G144K246/usb_cdc_test/tools/gb_sim.py     ← Python GB 仿真器 (排查工具)

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

经过长时间排查, GB 从"卡死无声"到"正常出声"经过 **三个独立 bug** 的修复。
本章详细记录每个 bug 的**诊断推理流程** (而不只是结论), 包括走错的弯路和关键转折点,
作为后续移植其他音源 (FM OpN / C64 SID 等) 的参考。

---

### Bug 1: NR52 power-off memset 数据竞争

**症状**: 烧录初期版本, 播放 GB VGM 时下位机直接死机, 必须断电才能重新烧录。
py 端也跟着卡死 (USB CDC 串口阻塞)。

**排查路径**:
1. 症状是"死机要断电", 最像硬件异常或栈溢出, 但其他音源正常 → 排除通用问题
2. 审视 main.c 的 0xB3 命令处理, 发现 NR52=0 (power-off) 分支调用了 memset 清整个 SOUND 结构
3. SOUND 结构 43 字节 × 4 通道 = 172 字节, memset 在主循环 process_uart 里执行
4. **关键洞察**: Timer0 ISR (22050Hz) 每 45μs 打断一次主循环, ISR 里调 gb_render 读这些结构
5. 如果 memset 清到一半被 ISR 打断, gb_render 读到半清零的状态 → 行为未定义 → 可能死机

**根因**: 主循环的 memset 和 ISR 的 gb_render 对同一组 SOUND 结构存在数据竞争。
memset 不是原子的, 清到一半被 ISR 打断时结构处于不一致状态。

**修复**: NR52 power-off 分支不再 memset, 只清 4 个 on 标志 (单字节写, 原子安全):
```c
case NR52:
    if (!(val & 0x80)) {
        gb_snd1.on = 0;  /* 只清 on, 不 memset */
        gb_snd2.on = 0;
        gb_snd3.on = 0;
        gb_snd4.on = 0;
    }
```
真正的结构清零交给 gb_init() (0xF0 reset 命令), 那时 ISR 还没启动或已停 GB。

**教训**:
- MCU 上主循环和 ISR 共享的数据结构, 写操作必须考虑原子性
- memset 大结构是非原子的, ISR 随时可能读到半更新状态
- 单字节写 (u8) 在 8051 上是原子的, 多字节写必须关中断或用标志位同步

---

### Bug 2: 混音公式方向错误 (`<<6` 抄成 `>>4`)

**症状**: Bug 1 修复后不再死机, 流水灯正常, py 能正常播完, 但**完全无声** (扬声器绝对安静,
不是音量小, 是完全没声音)。其他音源正常。

**排查路径 (走了大弯路)**:
1. 第一反应怀疑 py 播放器没正确解析/发送 GB 命令 → dump VGM 字节, 逐条对比, **完全正确**
2. 怀疑下位机 0xB3 命令处理逻辑 → 对比 NES 的 0xB4 (工作正常), **代码结构一模一样**
3. 怀疑 gb_active 没置位 → 检查 main.c, **逻辑正确**
4. **关键转折: 写 Python 仿真器**。把 gb.c 的 gb_render/gb_update_state 等函数 1:1 翻译成 Python,
   喂真实 GB VGM 数据进去, 看 render() 输出什么
5. 仿真器驱动循环第一次写错 (budget 累积 bug), 修好后跑出来: **前 8000 采样非零率 10%, 最大幅度仅 12**
6. DAC 范围 ±2048, 幅度 12 = 满幅度的 0.6%, **物理上几乎听不见** (扬声器推不动)
7. 追踪幅度为什么这么小, 看 gb_render 的混音公式

**根因**: libvgm 原版 `gameboy_update` (gb.c:1188-1194):
```c
left  *= vol_left;
left <<= 6;       // pump up the volume (放大 64 倍)
```
移植时误抄成:
```c
mix_mono >>= 4;   // 缩小 16 倍 (方向完全相反!)
```
一来一回差 64×16 = **1024 倍**。signal=1, env=12, vol=7 的正常情形:
- libvgm: 12 × 7 × 64 = 5376 (满幅度)
- 我的移植: 24 × 7 / 16 = 10 (几乎听不见)

**验证**: 仿真器修复前后定量对比:
| 指标 | 修复前 (>>4) | 修复后 (<<6) |
|------|-------------|-------------|
| 非零采样率 | 10.1% | 74.3% |
| 最大幅度 | 12 | 2048 (满幅度) |
| 平均幅度 | 0.73 | 1100 |

**修复**: 对齐 libvgm, 同时把 mono 合并从"左右累加"改成"(left+right)/2 平均"避免双使能通道 2x 失真:
```c
mono = (left + right) / 2;                    // mono 合并
vol_avg = (vol_left + vol_right + 1) / 2;     // NR50 平均
mono *= vol_avg;
mono <<= 6;                                    // pump up (原误为 >>= 4)
```

**教训**:
- **仿真器是排查"代码逻辑对但实机不响"的核武器**。人眼盯代码容易漏, 仿真器能定量给出输出幅度
- `<<` 和 `>>` 看起来只差一个字符, 效果差 1024 倍, 这种错误代码审查很难发现
- 移植时每个算术运算都要对照原版逐字符核对, 尤其是移位方向

---

### Bug 3: ISR 超时饿死 USB CDC (最难, 排查时间最长)

**症状**: Bug 2 修复后, **py 播放 GB 时 ser.write() 永久阻塞, 不响应 Ctrl+C**。
流水灯正常 (Timer0 ISR 在跑)。其他音源 (AY/SN/SCC/NES) 完全正常。
烧旧版 12K128 的 gb.c (曾验证能出声) 移植过来也**同样卡死**。

**排查路径 (走了非常多弯路, 记录所有方向)**:

1. **怀疑 py 播放器 GB 命令发送 bug**:
   - 对比 NES (0xB4) 和 GB (0xB3) 的发送代码 → 完全一样 (`ser.write(data[pos-1:pos+2])`)
   - dump VGM 字节流 → 2744 条 0xB3 命令逐条正确
   - **写无串口模拟器**: 把 ser.write 替换成 FakeSer, 跑完整首歌 → 13.4s 正常跑完, 处理 5557 条命令
   - 结论: **播放器逻辑完全正确, py 卡死 100% 是 ser.write() 阻塞** (下位机不消费 USB 数据)

2. **怀疑下位机 0xB3 命令路径卡死**:
   - 对比 0xB3 和 0xB4 的 main.c 处理代码 → 一模一样 (break + 读 reg + 读 data + 调 wr)
   - 怀疑 gb_wr 内部死循环 → 检查 gb.c, 只有 switch + 简单赋值, 无循环
   - 怀疑 @STCISP# 序列误触发 → 流水灯正常证明没进 ISP

3. **怀疑 C251 overlay 优化数据竞争** (这个方向花了最久):
   - 看 MAIN.MAP, 发现 tm0_isr 和 process_uart 是两棵独立 overlay 子树
   - C251 linker 不知道 ISR 会异步打断 main, 把 gb_render 链和 gb_wr 链的局部变量 overlay 到相同地址
   - 加 NOOVERLAY 链接参数重编 → **烧录后仍然卡死** ❌ (假设证伪)
   - 教训: MAP 文件看起来"有问题"不代表是真因, 必须实测验证

4. **怀疑旧版 gb.c 能出声** (基线对照):
   - 把 STC32G12K128/gb.c (曾验证能出声) 原样移植到 usb_cdc_test, 只改 include
   - 烧录后 **同样卡死** ❌
   - 这个结果非常关键: 证明**问题不在 gb.c 代码本身, 而在集成环境** (12K128 和 144K246 的差异)

5. **关键转折: 二分法诊断**:
   - 既然新旧版 gb.c 都卡, 且 NES 不卡, 做一个确定性实验:
   - ISR 里注释掉 `if (gb_active) mix += gb_render();`, 改成 `(void)gb_active;`
   - **保留 gb_active 置位 + gb_wr 命令处理完整路径, 只是不调 render**
   - 烧录测试 → **py 立刻不卡了! 能正常播完响应 Ctrl+C**
   - 结论: **100% 证明是 gb_render() 函数本身在 ISR 里执行时间过长**, 和命令路径无关

6. **为什么 gb_render 耗时? 定量分析**:
   - 22050Hz 下, gb_render 每采样推进 incr ≈ 190 GB cycles
   - gb_update_wave 用 `while(cycles_left >= 2)` 逐 GB cycle 推进 freq_counter
   - 190 cycles / 2 = **95 次循环** 每采样
   - 每次循环体: `offset/2` 除法 + wave RAM 查表 + `level-1` 变量移位 + 多个条件分支
   - ISR 预算 = 1/22050 = **45μs**, gb_render 单独就耗 100-200μs → **超时 3-4 倍**
   - ISR 超时 → USB CDC 中断得不到执行时间 → RX1_Buffer 停止填充 → py write 永久阻塞

7. **关键洞察: 为什么 NES 5 通道不卡?**:
   - 用户一句反问: "为什么 NES 带 DMC 都能 5 通道完美播放, GB 才 4 通道就不行?"
   - 这句话直接逼出和 NES 的对比 (之前一直只盯 GB 自己)
   - 看 nes_update_square (nes.c:328-331):
     ```c
     while (chan->phaseacc >= freq) {
         chan->phaseacc -= freq;              // 减法
         chan->adder = (chan->adder + 1) & 0x0F;   // 加法 + 位运算
     }
     ```
   - **循环体只有减法 + 加法 + 位运算**, 没有除法/表查找/条件分支
   - NES cycles 81, freq 最小 8 → 循环最多 10 次
   - GB wave: 循环 95 次 × 重循环体 = NES 工作量的 **~50 倍**
   - 结论: 不是通道数问题, 是**算法效率问题**。NES 的 phaseacc 累加是 MCU 友好设计, GB 照搬 libvgm 逐 cycle 推进是 PC 思维

8. **第一次修复尝试 (guard 调小) 失败**:
   - 把 wave/noise 的 guard 从 4096 降到 48, 超出保留 cycles_left
   - **失败**: cycles_left 保留后下个采样累积更多, guard 再次打满, **雪崩式增长** → 永久打满 → 还是卡
   - 改成 guard=16 + 超出清零 (丢弃 cycles 防雪崩)
   - **py 不卡了, 但没声音**: guard 太小, cycles 全丢, wave/noise 完全不前进

9. **最终修复 (NES 风格 phaseacc)**:
   - 核心思路: 不逐 GB cycle 推进, 而是 cycles_left 当 phaseacc 累加, 达到一个完整波形周期才推进 offset
   - wave 一个 sample point 的周期 = `2 × (0x800 - frequency)` GB cycles
   - 190 cycles / period ≈ **5-10 次循环** (从 95 次降到 10 次, 和 NES 相当)
   - 循环体也优化: `offset/2` → `offset>>1`, level 用 `if/else` 代替变量移位
   - noise 的 LFSR 是顺序依赖无法公式化, 但 period 本来就大 (8~32768), 循环最多 24 次, guard=32 保底
   - square 本来就是公式法 (一次除法无循环), 不卡
   - **烧录测试: 终于出声!** ✅

**根因总结**: libvgm 为 PC (GHz 级 CPU) 设计, 逐 cycle 循环 95 次无所谓。
照搬到 72MHz MCU 的 45μs ISR 里就是灾难。必须像 NES 那样用 phaseacc 累加 + 轻循环体。

**教训 (最重要)**:
1. **移植 libvgm 到 MCU 不能照搬 PC 算法**。每个 update 函数必须评估: ISR 内循环次数 × 循环体重量
2. **遇到"代码逻辑对但实机卡死", 优先怀疑 ISR 执行时间**。用二分法 (注释掉可疑调用) 快速确诊
3. **遇到"A 音源行 B 音源不行", 立刻对比两者的实现差异** (循环结构/循环体重量), 比孤立排查 B 高效 10 倍
4. **用户的直觉反问往往是突破口**。"为什么 NES 行 GB 不行"直接定位了算法效率差异
5. **guard 调小是治标不治本**: 要么雪崩 (保留 cycles), 要么丢声 (清零 cycles)。必须从算法层面减少循环次数
6. **MAP 文件 / overlay 分析可能误导**: 看起来"有问题"的内存分配不一定是真因, 必须实测验证

---

### Bug 4: 混音削波失真 (大音量沙哑)

**症状**: Bug 3 修复出声后, 音质非常差——**音量越大越沙哑**, 小音量正常。

**排查路径**:
1. "音量大时失真"是典型**削波 (clipping)** 症状 → 直接看 DAC 输出幅度
2. 对比 NES 的 `nes_render` (nes.c:520-527): `mix = squ0+squ1+tri*3/4+noise*3/4+dmc/2; mix *= 1`
   NES render 返回**原始幅度**, 系数 ×1, 由 ISR 外层 `mix *= 8` 统一放大
3. 我的 `gb_render` 内部做了 `<<6` (×64, 对齐 libvgm pump up), ISR 再 ×8 = **×512**
4. GB 比 NES 响 64 倍, 大音量时 DAC 严重削波 → 沙哑

**根因**: 移植时只对齐了 libvgm 的 `<<6`, 没考虑 ISR 外层还有个统一的 `×8`。
libvgm 是最终输出 (直接写 16-bit 缓冲), 我们的 ISR 还要再放大, 两层叠加导致过量。

**修复**: gb_render 改成和 NES 一样的原始幅度输出, 让 ISR ×8 统一处理:
```c
mono = max(|left|, |right|);   // mono 合并 (见下)
mono *= vol_avg;                // NR50 主音量
mono >>= 2;                     // 衰减, 让 ISR ×8 后回到合理量级
```

**mono 合并策略演进** (三个阶段):
1. `(left+right)/2` 平均 → 单边使能的通道音量被砍半 ❌
2. `left+right` 求和 → 双使能时 +6dB 过响 ❌
3. **`max(|left|, |right|)`** → 单边/双边都全音量, NR51 只控制"有没有声"不控制"多大声" ✅

**教训**:
- 移植混音公式要看**完整信号链**: render 内部系数 × ISR 外层系数 = 总增益, 不能只看一层
- 单声道系统合并立体声, 取 max(|L|,|R|) 比平均/求和都合理: 不惩罚声像定位, 不叠加双使能

---

### Bug 5: 二次播放卡死 (py 重启后)

**症状**: playlist 内连续切歌不卡, 但 **py 进程重启后第二次播放 (单曲或 playlist) 必卡死**。
第一次播放正常 (下位机刚上电或刚烧录)。

**排查路径**:
1. playlist 内切歌不卡 = 0xF0 reset 机制本身工作
2. py 重启后第二次卡 = **开播前 GB 状态不干净**
3. 对比两次播放的差异: 第一次下位机刚上电, GB 是 `gb_init()` 干净初始值;
   第二次下位机没断电, GB 停留上一首播完的脏状态 (cycles_left / noise_lfsr 残留)
4. 看单曲模式 py 代码: `mute_all()` 只在 `finally` (退出时) 发 0xF0, **开播前没发**
5. playlist 的 `mute_all_chips()` 在每首歌之间发, 所以 playlist 内切歌不卡;
   但 py 重启后第一首歌开播前没发 → 脏状态 → 卡死

**根因**: py 单曲模式 `play_vgm()` 开播前没发 0xF0 reset。
下位机 GB 带着脏的 cycles_left/lfsr, 第一组 trigger 命令进来后循环爆 guard → ISR 超时。

**修复** (py 端, 固件不用改): `play_vgm()` 开头加 0xF0:
```python
ser.write(bytes([0xF0]))
time.sleep(0.02)
```

**教训**:
- **状态机的"开始"和"结束"必须对称**: 结束时 reset 了, 开始时也要 reset
- py 重启 ≠ 下位机复位, 下位机状态会跨 py 进程保留
- 排查"第一次行第二次不行"类问题: 对比两次的差异 (上电状态 vs 残留状态), 缩小到状态初始化

---

## 13. GB ISR 极致优化 (2026-06-22, 命令密集卡顿消除)

Bug 3-5 修复后 GB 能正常出声, 但**音符指令一多就卡顿** (尤其 fast-forward 段落、
64 首 playlist 连播)。根因不是逻辑错误, 而是 **gb_render 在 ISR 里执行时间过长**,
命令密集时 (gb_wr 在主循环频繁打断 ISR) ISR 抢不到时间片。

### 优化思路: 对齐 NES/AY/SN/SCC 四个已优化音源

这四个音源在 22050Hz ISR 下都能流畅运行, 必有共同的 MCU 友好模式。
逐个精读它们的 render/update 函数, 提炼模式表:

| 模式 | NES | AY | SN | SCC | GB 优化前 |
|------|-----|----|----|-----|---------|
| 热路径存储 | xdata+data 分离 | static | static | **data 热路径** | static (未区分) |
| 相位类型 | u16 phaseacc | u16 count | u16 count | u32 cnt | **s32 cycles_left** ❌ |
| 除法 | 无 (freq 预算) | 无 | 无 | 无 (step 预算) | **u32/8192 真除法** ❌ |
| 循环 | while 体极轻 | 无循环 | 无循环 | 无循环公式法 | wave/noise while ❌ |
| 查表 | duty/noise/period 全 const | voltbl | voltbl | wav[][] | wave_duty 仅 square |

关键发现: **NES 用 u16 phaseacc, AY/SN 根本不循环, SCC 用公式法无循环**。
GB 用 s32 有符号 + u32 真除法 + while 循环, 每一项都是性能反模式。

### 8 项优化 (每项都对齐某个已优化音源的模式)

#### 1. frame sequencer 除法改位移 (最大单项收益)
`FRAME_CYCLES = 8192 = 2^13`, 所有 `cycles / FRAME_CYCLES` 改 `cycles >> 13`,
`cycles & (FRAME_CYCLES-1)` 改 `cycles & 0x1FFF`。涉及 gb_update_state 3 处 u32 除法,
每处省 ~20 机器周期 (C251 u32 除法调库函数, 很慢)。**对齐 NES: NES 原本就没除法**。

#### 2. noise 改 AY 风格 Galois LFSR (用户确认可简化)
原 noise 用 Fibonacci LFSR 的 while 循环逐次移位 (guard=32)。改成 AY8910 的 noise_scaler 思路:
单次 if 判断 + Galois 多项式异或 (`rng >>= 1; if(rng&1) rng ^= 0x6000`),
guard 32→8。**对齐 AY8910: AY 的噪声就是单步 Galois LFSR**。
听感接近 AY 噪声 (用户认可), 和原 DMG 有差异但不影响音乐识别。

#### 3. wave 保持 phaseacc (用户确认)
Bug 3 修复时已改成 phaseacc 风格 (period = 2×distance, 循环 ~5-10 次, 体轻)。
本次只同步 distance 字段 + level 用 if/else 代替变量移位。**已对齐 NES, 无需进一步改**。

#### 4. square distance 预计算
原 render 里每次算 `0x800 - frequency`。改成切频时 (NR13/NR14/NR23/NR24 写入)
预存到 `snd->distance` 字段, render 里直接读。**对齐 NES: NES 在 nes_wr 里就算好 freq 存结构**。

#### 5. cycles_left s32→s16
每采样 GB cycles ~190, s16 范围 ±32767 足够。s16 比 s32 内存访问减半。**对齐 NES u16 phaseacc**。

#### 6. 结构瘦身
- `cycles_left` s32→s16 (-2 字节 × 4 通道)
- `duty_count` u32→u8 (本就 &0x07, -3 字节 × 4 通道)
- 删 `sample_reading` / `current_sample` / `frequency_counter` (调试/冗余字段)
SOUND 从 ~43 字节 → ~32 字节, 4 通道省 ~44 字节 xdata, 访问更快。

#### 7. gb_base_count 入 data 段
render 每采样必访的 `gb_base_count` 加 `data` 关键字, 放内部 RAM 直接寻址 (1 机器周期)。
其他 SOUND/SOUNDC 结构较大 (~40B×4=160B), 全放 data 会和 SCC/USB 挤爆 (L107 OVERFLOW),
故留 xdata。**对齐 SCC: SCC 的 scc_cnt/scc_step_val 也在 data 段**。

#### 8. frame sequencer 跨 frame 不双倍调用
原 gb_update_state 跨 frame 边界时: 先用 cycles_current_frame 调 4 个 update,
再用剩余 cycles 再调 4 个 update = **8 次 update 调用**。
改成: 通道用完整 cycles 一次 update (省一半), frame 边界的 length/sweep/envelope tick
仍按 step 触发。听感差异极小 (相位推进差几个 cycle), 性能省一半。

### 编译结果对比

| 指标 | 优化前 | 优化后 | 变化 |
|------|--------|--------|------|
| code | 16787 | 16622 | **-165** |
| xdata | 21244 | 21207 | **-37** |
| data | 68.5 | 72.5 | +4 (gb_base_count 入 data) |
| HEX | 48600 | 47806 | **-794** |

### 仿真验证 (gb_sim.py 同步更新后)

喂真实 GB VGM, 30000 采样统计:
- 非零率: 74.3% → 73.8% (持平)
- 最大幅度: 2048 → 2048 (一致)
- 平均幅度: 1099 → 1073 (-2%, noise 简化的微小差异, 听感无感知)

### 实机验证

- 64 首 GB playlist (DQ3 等) 连续播放不卡顿
- 命令密集段落 (23775 条 0xB3 的 Overture) 流畅
- 音质和优化前一致

### 教训

1. **移植 libvgm 到 MCU 要逐函数评估 ISR 开销**: 循环次数 × 循环体重量 × 调用频率
2. **2 的幂用位移**: FRAME_CYCLES=8192=2^13 这种用 >>13 代替除法, u32 除法在 C251 上调库函数极慢
3. **MCU 友好的相位推进是 phaseacc 累加 + 轻循环体** (NES/AY/SN/SCC 共通模式),
   不是逐 cycle 循环 (libvgm 的 PC 思维)
4. **热路径标量入 data 段**, 大结构留 xdata (data 段只有 256B, 全放会溢出)
5. **结构体字段类型选最小够用** (s32→s16, u32→u8), 减少内存带宽
6. **寄存器写入时预计算** (distance/freq), render 里直接读, 避免重复运算

---

### 被证伪的假设清单 (避免重复踩坑)

| # | 假设 | 证伪方式 | 结果 |
|---|------|---------|------|
| 1 | C251 overlay 导致 gb_wr/gb_render 数据竞争 | 加 NOOVERLAY 链接, 烧录测试 | 仍卡死 ❌ |
| 2 | VGM_CMD_LEN 表把 0xB3 误设为 4 字节导致命令错位 | 分析 GB VGM 命令流 | 无未知命令, 不影响 ❌ |
| 3 | @STCISP# 序列误触发进 ISP | 观察流水灯 | 正常, 证明没复位 ❌ |
| 4 | py 播放器 GB 命令发送 bug | 写无串口模拟器跑完整首 | 13.4s 正常跑完 ❌ |
| 5 | guard 调小 (4096→48→16) 能解决 ISR 超时 | 烧录测试 | 雪崩卡死 或 丢声 ❌ |
| 6 | 旧版 12K128 gb.c 移植能绕过问题 | 原样移植烧录 | 同样卡死 ❌ |
| 7 | 命令密度过高塞满 USB buffer | 对比 NES 字节率 | NES 540B/s > GB 307B/s 都正常 ❌ |

**共同特征**: 这些假设都指向"命令路径/通信/编译器"方向, 而真因是**算法效率**。
下次遇到类似问题, 先用二分法确诊是不是 ISR 耗时, 再看算法循环次数。

---

### 最终 gb.c 关键参数

```
GB_CLOCK     = 4194304 Hz
GB_GETA_BITS = 24
GB_BASE_INCR = 3191326266  (4194304 × 2^24 / 22050, 超 LONG_MAX 但 u32 内)
每采样 incr  ≈ 190 GB cycles

wave 通道 (NES 风格 phaseacc):
  period     = 2 × distance = 2 × (0x800 - frequency) GB cycles
  循环次数   ≈ 190 / period ≈ 5-10 次 (原 libvgm 逐 cycle = 95 次)
  guard      = 32

noise 通道 (AY 风格 Galois LFSR, 单次异或移位):
  period     = noise_div[reg&7] << (reg>>4)  = 8 ~ 32768 GB cycles
  循环次数   ≈ 190 / 8 = 24 次 (最坏)
  guard      = 8 (循环体极轻, 不需大 guard)

square 通道 (公式法, 无循环):
  distance   = 0x800 - frequency (切频时预计算存结构)
  counter    = 1 + (cyc - distance) / distance   (一次 u16 除法)
  每采样调用 = 1 次 (无循环)
```

### 产物
- `src/build/MAIN.hex` — GB ISR 优化后版本 (47806 bytes, 较优化前 -794)
- `tools/gb_sim.py` — Python GB 仿真器 (排查 Bug 2/3 + 优化验证工具, 不参与编译)

---

## 14. py 端 GD3/clock 显示完善 (2026-06-22)

GB ISR 优化完成后, 实机播放时发现 py 端显示信息有问题:
- GD3 只显示 `? - title` (字段大量错位)
- 纯 GB 曲目误显 `NES clock: 1789773 Hz (NTSC)` (该曲根本没 NES 音源)

### Bug 6: GD3 字段错位 (漏读 magic+version, 过滤空字段)

**症状**: tales/03 Harmonious Moment.vgm 显示成
```
  Track: ?  [Harmonious Moment]      ← title 错, game 跑到 title
  System: Game Boy                    ← system 跑到 game 位对了一半
  Author: 2000-11-10                  ← date 跑到 author
  Date: gbs2vgm by Claude & Denjhang  ← comment 跑到 date
```

**根因 (两个 bug 叠加)**:

1. **漏读 GD3 tag 头的 8 字节**: GD3 tag 结构是 `[magic 'Gd3 '][version u32][tag_len u32][utf16 数据]`,
   数据从 offset+12 开始。之前代码 `struct.unpack_from('<I', data, gd3_off)[0]` 直接读 offset 处的 4 字节
   当 tag_len, 实际读到的是 magic `'Gd3 '` = `0x47643320`, 被当成 5 亿字节的 tag_len,
   字段解析从完全错误的位置开始。

2. **过滤空字段导致索引错位**: jp 字段经常是空字符串, `if f.strip('\x00')` 把它们全过滤掉,
   后面的字段往前挪, 索引全错。

**修复** (对齐 libvgm `vgmplayer.cpp` GetTagData, line 428-467):
```python
if magic == b'Gd3 ':                           # 检查 magic
    tag_ver = struct.unpack_from('<I', data, gd3_off+4)[0]
    if 0x100 <= tag_ver < 0x200:               # version 校验 (libvgm 要求)
        tag_len = struct.unpack_from('<I', data, gd3_off+8)[0]
        text = data[gd3_off+12:gd3_off+12+tag_len].decode('utf-16-le')
        fields = text.split('\x00')            # 不过滤空! jp 字段常空
```

**GD3 标准 11 字段** (libvgm `_TAG_TYPE_LIST`, `_TAG_COUNT=11`):
```
0/1: TITLE / TITLE-JPN        (曲名 英/日)
2/3: GAME / GAME-JPN          (游戏名 英/日)
4/5: SYSTEM / SYSTEM-JPN      (系统名 英/日)
6/7: ARTIST / ARTIST-JPN      (作曲 英/日)
8:   DATE                     (发布日期 YYYY.MM.DD)
9:   ENCODED_BY               (VGM 作者/ripper)
10:  COMMENT                  (注释/备注, 如 gbs2vgm 转换信息)
```
之前以为只有 10 字段, 漏了最后的 COMMENT (gbs2vgm 转换信息就在这里)。

**验证** (标准 tales 文件):
```
title  : 'Harmonious Moment'
game   : 'Tales of Phantasia - Narikiri Dungeon'
system : 'Game Boy'
author : 'M. Sakuraba, S. Tamura, T. Aida'
date   : '2000-11-10'
ripper : 'CaitSith2'                         ← ENCODED_BY
comment: 'gbs2vgm by Claude & Denjhang'      ← COMMENT
```

### Bug 7: clock 误显 (NES clock 强制默认 + 不按命令过滤)

**症状**: 纯 GB 曲目显示 `NES clock: 1789773 Hz (NTSC)`, 误导用户以为有 NES 音源。

**根因**:
1. NES clock 解析时 `if nes_clock == 0: nes_clock = 1789773` — header 0x84=0 时强制填 NTSC 默认
2. 显示时无条件打印 NES clock, 不检查该曲是否真有 NES 命令

**修复** (按命令统计过滤):
```python
nes_clk = hdr.get('nes_clock') or 0
if stats['nes'] > 0:                    # 仅当有 NES 命令时才显示/下发
    if nes_clk == 0: nes_clk = 1789773  # 无 header clock 才默认 NTSC
    ser.write(bytes([0xB5]) + ...)      # 0xB5 也只在 NES 曲发

gb_clk = hdr.get('gb_clock') or 0
if stats['gb'] > 0 and gb_clk:          # 仅当有 GB 命令时显示
    print(f"  GB clock: {gb_clk} Hz (DMG)")
```

附带: header 偏移加 VGM version 守护 (`ver >= 0x161` 才读 0x80 GB clock,
`ver >= 0x160` 才读 0x84 NES clock), 避免低版本 VGM 越界读 GD3 数据。

### 教训

1. **文件格式解析必须对照官方实现**: GD3 结构 libvgm `vgmplayer.cpp` 写得清清楚楚,
   自己猜结构 (漏 magic+version) 必错。下次涉及 VGM/SF2/IT 等格式, 第一时间查参考实现。
2. **不要过滤分隔符产生的空字段**: `\x00` 分隔的字段里空值是合法的 (jp 经常空),
   `if f.strip()` 过滤会破坏索引对齐。
3. **别自己造术语**: GD3 字段名 libvgm `_TAG_TYPE_LIST` 有标准 (TITLE/.../COMMENT),
   照着叫, 不要把 COMMENT 说成"工具签名"这种非标准词。
4. **条件显示要基于实际内容**: clock 显示前先检查命令统计 (`stats['nes'] > 0`),
   不要无条件显示某个字段 (尤其当它有"默认值"时, 默认值会伪装成真实数据)。
- 本文档 §12 — 完整诊断推理流程 (供后续移植其他音源参考)

---

## 15. RC 高通滤波器 (2026-06-22, gbsplay 对比 + DMG 隔直电容模拟)

Bug 8 (square duty) 修复后, Pokemon New Bark Town 的 12.5% duty 通道仍有嗡嗡/破音.
用户直觉认为 libvgm 的 GB 核心音质不如 gbsplay, 指引对比 gbsplay 源码.

### gbsplay vs libvgm 对比

参考源: `Reference_Project/vgm_libs/modizer-master/libs/gbsplay/gbsplay/gbhw.c`

关键发现 — **gbsplay 实现了 RC 高通滤波器** (gbhw.c line 684-696):
```c
/*
 * RC High-pass & DC decoupling filter. Gameboy
 * Classic uses 1uF and 510 Ohms in series,
 * followed by 10K Ohms pot to ground between
 * CPU output and amplifier input, which gives a
 * cutoff frequency of 15.14Hz.
 */
l_out = (l_smpl - l_cap) >> 16;
l_cap = l_smpl - l_out * cap_factor;
```

模拟 DMG 真机硬件: CPU 输出经 **1μF 电容 + 510Ω + 10KΩ 电位器**到放大器, 截止 **15.14Hz**.
这个硬件高通的作用:
1. **隔直** — 消除 duty 不对称的直流 (12.5% duty 的 signal 序列 {-1×7,+1} 平均 -0.75)
2. **衰减次声波** (<15Hz 人耳听不见的波动)

**libvgm 没做这个高通** — 直接输出 `signal × env` 给 DAC, 直流分量原样保留.
外部电容救不了 (数字直流不是缓慢漂移, 是信号本身的固定偏移).
这是 gbsplay 音质比 libvgm 干净的根本原因.

### duty 直流分量的数学分析

| Duty | signal 序列 | 平均值 | env=15 时直流 |
|------|------------|--------|--------------|
| 12.5% | {-1×7, +1} | -0.75 | **-11.25** |
| 25%   | {+1, -1×6, +1} | -0.5 | -7.5 |
| 50%   | {+1, -1×4, +1×3} | 0 | 0 |
| 75%   | {-1, +1×6, -1} | +0.5 | +7.5 |

Pokemon New Bark Town 的 CH1 用 12.5% duty, 直流 -11.25 × vol(7) × ISR(×8/8) = -79.
DAC 被推离中点 79, 负向动态范围只剩 1969 (正常 2048), 叠加其他通道易削波破音.
低频段 (Pokemon CH1 有 49% 音符 <200Hz) 听感是 "嗡嗡脉冲".

### 实现要点

标准一阶 RC 高通差分方程: `y[n] = α × (y[n-1] + x[n] - x[n-1])`
- α = RC/(RC+dt) = 0.99570436 (fc=15.14Hz, fs=22050Hz)
- Q16 定点 α = 65254

**关键坑: 信号必须放大到 Q16 再滤波**. 否则小信号整数截断导致衰减失效:
```c
// 错误 (小信号衰减失效):
y = (65254 * (hp_y + mono - hp_x)) >> 16;
// mono=-100 时: 65254×-100/65536 = -99.55 → 截断 -99, 只衰减 1, 永远收敛不了

// 正确 (Q16 放大):
in_q16 = mono << 16;
y_q16 = (65254 * (hp_y + in_q16 - hp_x)) >> 16;
// mono=-100 → in_q16=-6553600, 精确小数衰减, 正确收敛
```

### 验证

仿真 (gb_sim.py, 跑 5000 采样, 取后 3000 稳态):
| Duty | 加高通前平均 | 加高通后平均 | 消除率 |
|------|------------|------------|--------|
| 12.5% | -10.6 | **-0.47** | 95.6% |
| 50% | -0.6 | -0.51 | (本来就小) |

纯直流 -100 输入: 1159 采样 (52ms, 5τ) 后衰减到 -1, 消除 99%.

### CPU 开销

每采样 1 次 s32 乘法 + 几次加减, 约 2-3 机器周期 (< 0.1μs), 相比 gb_render 整体几十 μs 完全可忽略.

### gbsplay 的其他复杂度 (我们不需要)

gbsplay 用**冲激响应积分器** (impulse buffer): 逐 GB cycle 把信号 delta 累加, 缓冲满后
做冲激响应卷积生成采样. 这是 band-limited synthesis (抗混叠). 但因为我们已经按 22050Hz
用 phaseacc 降采样, 不需要冲激响应. **只加 RC 高通就够了** — 它解决了核心的直流问题.

### 教训

1. **移植音源核心要多方对比**: libvgm 不是唯一参考, gbsplay (GB) 等专门播放器往往有更精确
   的硬件模拟. 音质不好时找同类播放器对比.
2. **硬件的模拟前端很重要**: DMG 的隔直电容不是 "可选优化", 是硬件固有特性.
   libvgm 省略它导致音质下降 — 这是移植时要补回来的.
3. **一阶 IIR 高通的定点实现要放大信号**: Q16 系数对小信号 (绝对值 < 1000) 截断严重,
   必须 `x << 16` 放大后滤波再 `>> 16` 还原. 否则衰减失效.
4. **用户直觉往往是突破口**: "libvgm 的 GB 核心音质不如 gbsplay" 这句话直接指引找到 RC 高通.
