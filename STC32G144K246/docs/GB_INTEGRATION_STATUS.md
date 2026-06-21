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
  period     = 2 × (0x800 - frequency) GB cycles
  循环次数   ≈ 190 / period ≈ 5-10 次 (原 libvgm 逐 cycle = 95 次)
  guard      = 32

noise 通道 (保留 LFSR 逐次移位):
  period     = divisor[reg&7] << (reg>>4)  = 8 ~ 32768 GB cycles
  循环次数   ≈ 190 / 8 = 24 次 (最坏)
  guard      = 32

square 通道 (公式法, 无循环):
  distance   = 0x800 - frequency_counter
  counter    = 1 + cycles / distance   (一次除法)
  每采样调用 = 1 次 (无循环)
```

### 产物
- `src/build/MAIN.hex` — GB 出声版本 (48270 bytes)
- `tools/gb_sim.py` — Python GB 仿真器 (排查 Bug 2 的工具, 不参与编译)
- 本文档 §12 — 完整诊断推理流程 (供后续移植其他音源参考)
