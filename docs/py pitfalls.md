# Python 上位机踩坑记录

## 1. 寄存器地址用 `|` 而非 `+` 导致通道路由错误

**现象**: ADPCM 鼓声测试时，6 个鼓声音都正常，但 LED 只有 2 个亮（P0.2 和 P0.4）。
反复触发测试 (`adpcm_led_test.py`) 也只有 2 个 LED 亮，怀疑固件只有 2 个物理通道。

**根因**: Python 端 `note_on(ser, 0x15 | ch, drum)` 用了位 OR 而非加法。
`0x15 = 0b00010101`，位 OR 只在不重叠的 bit 上等价加法。低 2 位已经有 1：
```
0x15 | 0 = 0x15 (ch0, 正确)
0x15 | 1 = 0x15 (ch1, 错误! 应该是 0x16)
0x15 | 2 = 0x17 (ch2, 正确)
0x15 | 3 = 0x17 (ch3, 错误! 应该是 0x18)
0x15 | 4 = 0x15 (ch4, 错误! 应该是 0x19)
0x15 | 5 = 0x15 (ch5, 错误! 应该是 0x1A)
```
所以 ch0/ch2/ch4 地址正确（恰好在 bit 不重叠的位置），ch1/ch3/ch5 地址被折叠到 ch0/ch2。
固件端 XOR 校验 `0xC0 ^ r ^ d ^ chk` 因此失败，发送 ACK_ERR (0xFF)，Python 端读不到 0xAA。

但鼓声全部正常——因为同一个鼓被反复触发到 ch0 和 ch2，短促的鼓声让人听不出区别。

**修复**:
```python
# 错误 (所有 0x15|ch, 0x1B|ch, 0x21|ch 都有问题)
def note_on(ser, ch, drum):
    pcm_send(ser, 0x15 | ch, drum)

# 正确
def note_on(ser, ch, drum):
    pcm_send(ser, 0x15 + ch, drum)
```

**影响文件**: `adpcm_test.py`, `adpcm_led_test.py`, `adpcm_ch_test.py`, `adpcm_debug.py`
所有 `note_on`、`note_off`、`set_vol` 函数。

**教训**: 寄存器地址是连续整数分配时，用 `+` 不要用 `|`。位 OR 只有在基地址低 bit 全为 0 时才等价加法（比如 `0x10 | ch` 就没问题）。

## 2. UART ACK 发送未等待导致连续命令丢失

**现象**: 快速连续发送多条带 ACK 的命令时，部分命令丢失。

**根因**: `uart_send_ack()` 原实现直接写 SBUF 不等前一条发完：
```c
// 错误: 连续调用会覆盖 SBUF
static void uart_send_ack(u8 ack) {
    SBUF = ack;
    B_TX1_Busy = 1;
}

// 正确: 等前一条发完
static void uart_send_ack(u8 ack) {
    while (B_TX1_Busy);
    SBUF = ack;
    B_TX1_Busy = 1;
}
```
`process_uart()` 的 `while` 循环一次 task tick 处理所有积压命令，每条都调 `uart_send_ack`。
如果 ACK 发送未完成就被下一条覆盖，Python 端 `ser.read(1)` 读到的 ACK 数量不对，
后续字节被当成 ACK 消费，协议错位。

**修复**: 加 `while (B_TX1_Busy)` 等待。

## 3. LED 刷新频率与鼓声持续时间不匹配

**现象**: ADPCM 鼓声播放正常，但 LED 几乎看不到闪烁（即使 `|` bug 修复后）。

**根因**: LED 刷新在 task tick (~60Hz, 每 16ms 一次) 里执行，而很多鼓声非常短：
```
BD: 854 nibbles / 17640Hz ≈ 48ms
SD: 1219 nibbles / 17640Hz ≈ 69ms
HH: 732 nibbles / 17640Hz ≈ 42ms
TC: 5670 nibbles / 8820Hz ≈ 642ms (div=2)
TM: 1219 nibbles / 8820Hz ≈ 276ms (div=2)
RS: 244 nibbles / 8820Hz ≈ 55ms (div=2)
```
RS 只有 55ms，LED 16ms 刷新一次，可能在 LED 刷新时鼓已经播完 `active` 被清零。
原来 `LED_EVERY=6`（~10Hz 刷新），更难捕捉。

**修复**: `LED_EVERY` 从 6 改为 1，LED 刷新频率从 ~10Hz 提升到 ~60Hz。

## 4. UART 调试输出不能在 process_uart 里同步发多字节

**现象**: 在 `process_uart()` 的 `0xC0` 分支里加 `SBUF = ...; while(B_TX1_Busy);` 发多个调试字节，
固件直接卡死。

**根因**: `process_uart()` 在 Timer0 ISR 里调用，ISR 里阻塞等待 UART 发送会占用太长时间，
导致后续 ISR 延迟、UART 接收溢出、系统卡死。

**教训**: ISR 里不能做阻塞多字节串口输出。如需调试，用单字节（如直接驱动 P0 LED）或
在外部任务中异步输出。

## 5. 编译必须全量重编译

**现象**: 只编译 `main.c` 后链接，报 `AY8910.OBJ NOT FOUND`。

**根因**: 编译命令开头 `rm -f *.OBJ` 删了所有 OBJ 文件，但后续只编译了 `main.c`，l251
需要所有模块的 OBJ 文件。

**教训**: `rm -f *.OBJ` 后必须重新编译所有源文件，不能只编译修改的那个。
或者不删 OBJ，只编译修改的文件让 l251 用旧的 OBJ 链接。
