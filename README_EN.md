# STC_Chiptune

Multi-source chiptune synthesizer on STC32G12K128. Receives commands via UART, outputs audio through 8-bit PWM DAC, emulating 6 classic sound chips + ADPCM sampling in real time.

**Developers**: Denjhang (hardware design / system architecture), Claude (GLM-5) (firmware / toolchain / host tools)

## Table of Contents

- [1. Hardware](#1-hardware)
  - [1.1 Overview](#11-overview)
  - [1.2 Pin Assignment](#12-pin-assignment)
  - [1.3 PWM DAC Output](#13-pwm-dac-output)
    - [Why 8-bit not 10-bit](#why-8-bit-not-10-bit)
- [2. Sound Source Architecture](#2-sound-source-architecture)
  - [2.1 Active Sources Overview](#21-active-sources-overview)
  - [2.2 Mixing & Processing](#22-mixing--processing)
  - [2.3 AY8910 (YM2149)](#23-ay8910-ym2149)
  - [2.4 SN76489](#24-sn76489)
  - [2.5 FM Synthesis (Custom 2-Op)](#25-fm-synthesis-custom-2-op)
  - [2.6 Gigatron TTL Waveform](#26-gigatron-ttl-waveform)
  - [2.7 WT Wavetable](#27-wt-wavetable)
  - [2.8 ADPCM Sampling](#28-adpcm-sampling)
    - [ADPCM Decode Principle](#adpcm-decode-principle)
    - [Drum Machine Sequencer](#drum-machine-sequencer)
    - [Drum Pitch Shift](#drum-pitch-shift)
    - [SF2 Pitch Shift](#sf2-pitch-shift)
    - [SF2 Instrument ADSR Templates](#sf2-instrument-adsr-templates)
    - [ADPCM Loop Principle](#adpcm-loop-principle)
    - [ADPCM ADSR Envelope Principle](#adpcm-adsr-envelope-principle)
  - [2.9 BRR Sampling (SNES DSP filter=0)](#29-brr-sampling-snes-dsp-filter0)
    - [BRR Encoding Format](#brr-encoding-format)
    - [BRR Decode Principle](#brr-decode-principle-gme-spc_dspcpp-bit-exact)
    - [BRR Instrument ADSR Templates](#brr-instrument-adsr-templates-14-instruments)
    - [BRR Loop Principle](#brr-loop-principle)
    - [Pitch Shift Principle](#pitch-shift-principle)
  - [2.10 Abandoned Sound Sources](#210-abandoned-sound-sources)
- [3. UART Protocol](#3-uart-protocol)
  - [3.1 General Commands](#31-general-commands)
  - [3.2 WT Registers](#32-wt-registers)
  - [3.3 FM Registers](#33-fm-registers)
  - [3.4 ADPCM Registers](#34-adpcm-registers)
  - [3.5 BRR Registers](#35-brr-registers)
- [4. Host Tools](#4-host-tools)
  - [4.1 VGM Player](#41-vgm-player)
  - [4.2 ADPCM Drum Tests](#42-adpcm-drum-tests)
  - [4.3 ADPCM Drum Machine (ini-driven)](#43-adpcm-drum-machine-ini-driven)
  - [4.4 ADPCM Pitch Shift Tests](#44-adpcm-pitch-shift-tests)
  - [4.5 ADPCM Channel Debug](#45-adpcm-channel-debug)
  - [4.6 SF2 Melody Tests](#46-sf2-melody-tests)
  - [4.7 SF2 Pitch Sweep](#47-sf2-pitch-sweep)
  - [4.8 WT Sweep Test](#48-wt-sweep-test)
  - [4.9 BRR Sweep Test](#49-brr-sweep-test)
  - [4.10 Offline Tools](#410-offline-tools)
  - [4.11 Config Files](#411-config-files)
- [5. Toolchain & Build](#5-toolchain--build)
  - [5.1 Toolchain](#51-toolchain)
  - [5.2 Build Options](#52-build-options)
  - [5.3 Build Steps](#53-build-steps)
  - [5.4 Build Notes](#54-build-notes)
- [6. Directory Structure](#6-directory-structure)
- [7. Development History](#7-development-history)
- [8. Reference Projects & Porting Notes](#8-reference-projects--porting-notes)
  - [8.1 AY8910 — libvgm](#81-ay8910--libvgm)
  - [8.2 SN76489 — libvgm](#82-sn76489--libvgm)
  - [8.3 FM Synthesis — ArduinoUnoTinyFmKeyboard](#83-fm-synthesis--arduinounotinyfmkeyboard)
  - [8.4 WT Wavetable — ArduinoUno WaveMemorySyns](#84-wt-wavetable--arduinounowavememorysyns)
  - [8.5 Gigatron — Denjhang_Music_Player](#85-gigatron--denjhang_music_player)

---

## 1. Hardware

### 1.1 Overview

| Parameter | Value | Description |
|-----------|-------|-------------|
| MCU | STC32G12K128 | 32-bit 1T 8051 core, C251 compatible, 128KB Flash, 4KB SRAM + 8KB XRAM |
| System Clock | 38 MHz | IRC internal RC (Fosc=38000000) |
| DAC Output | P2.0 (PWMA PWM1) | 8-bit PWM DAC, carrier 148kHz, see below |
| Sample Rate | 17640 Hz | Timer0 ISR |
| Serial | UART1 @ 115200 baud | Timer1, 2048-byte ring buffer |
| LED | P0 port | 8-bit, displays active sound source channels |
| Task Scheduler | 294 ticks | ~60Hz calls process_uart(), parses commands |

### 1.2 Pin Assignment

| Pin | Function | Description |
|-----|----------|-------------|
| P2.0 | PWMA PWM1 -> Audio Out | 8-bit PWM DAC, RC low-pass filter + op-amp -> speaker/headphone |
| P1.6/P1.7 | UART1 TX/RX | 115200 baud, connect to USB-TTL |
| P0.0-P0.7 | LED indicators | 8-bit, displays active sound source channel status |
| P3.4/P3.5 | STC-ISP | Programming interface (TXD2/RXD2) |

### 1.3 PWM DAC Output

#### Hardware Configuration

Uses STC32G built-in advanced PWM module (PWMA) channel 1, output to P2.0:

```
PWMA_ARR = 255          (8-bit resolution, 0-255)
PWMA_CCR1 = sample       (written by ISR, 128 = silence center)
PWMA_PSC = 0             (no prescaler)
Carrier frequency = 38MHz / 256 = 148.4kHz
```

Register configuration:
- `CCMR1 = 0x68` - PWM mode 1, preload enable
- `CCER1 = 0x05` - CH1 output enable, active-low
- `PS |= 0x01` - P2.0 mapped to PWM1 output
- `BKR = 0x80` - Main output enable

#### Audio Output Chain

```
Timer0 ISR (17640Hz)
  -> 6 sound sources mixed -> s16 mix (-128~+127)
  -> out = 128 + mix -> u8 (0~255)
  -> PWMA_CCR1L = out (write directly to compare register)
  -> P2.0 outputs 148kHz PWM square wave
  -> RC low-pass filter (cutoff < 10kHz)
  -> Op-amp buffer
  -> Speaker / Headphone
```

#### Design Notes

- 8-bit resolution: 256 levels, ~48dB SNR, sufficient for chiptune style
- Carrier 148kHz: well above 20kHz audio, simple 1st-order RC suffices to filter
- Silence bias 128: PWM duty 50% = no audio output
- `OPTIMIZE(8, SPEED)`: Keil max optimization, ensures ISR completes within 56.7us (17640Hz period)

#### Why 8-bit not 10-bit

STC32G12K128 supports HSPWM (High-Speed PWM) that could theoretically increase ARR from 255 to 1023 (10-bit), improving dynamic range from 48dB to 60dB. However, testing revealed:

- **10-bit noise floor**: ARR=1023 gives carrier = 38MHz / 1024 = **37kHz**, right at the edge of audible range, producing noticeable ultrasonic noise floor (young people can hear it)
- **8-bit is clean**: ARR=255 gives carrier = 38MHz / 256 = **148kHz**, well above human hearing, a simple 1st-order RC filter completely removes it
- **PLL not feasible**: To maintain >=140kHz carrier at 10-bit, PLL must provide 144MHz clock, but STC32G12K128's 38MHz IRC is not a standard PLL input frequency, PLL lock is unstable
- **HSPWM async bridge unusable**: Writing via HSPWMA_ADR/DAT async bridge introduces `while(busy)` waits that block inside the 17640Hz ISR, causing audio glitches

**Conclusion**: 8-bit + 38MHz is the optimal balance for this hardware. To break this limitation, upgrade to STC32G144K246 (hardware DAC, no PWM involved).

## 2. Sound Source Architecture

### 2.1 Active Sources Overview

| Source | Command Prefix | Channels | Render Rate | Description |
|--------|---------------|----------|-------------|-------------|
| **AY8910** (YM2149) | `0xA0` | 3 square + noise + envelope | 17640Hz | Perfect, ZX Spectrum/MSX tunes |
| **SN76489** | `0x50` | 3 square + noise | 17640Hz | Sega Master System, 3 variants |
| **FM** (custom 2-Op) | `0x51` | 16 voice (32 op) | 17640Hz | 2-Operator FM, 6 waveforms |
| **Gigatron** | `0xB0` | 4 ch | 8820Hz | 4ch TTL waveform, direct fnum write |
| **WT** (Wavetable) | `0xC0` | 4 ch | 17640Hz | 14 waveforms, ADSR envelope |
| **ADPCM** | `0xC0` | 6 ch | 17640Hz | Drums + SF2 melodic samples |
| **BRR** | `0xC0` | 4 ch | 17640Hz | 14 instruments BRR melodic samples (SNES DSP filter=0) |

### 2.2 Mixing & Processing

Timer0 ISR at 17640Hz renders all active sources every tick, sums and clamps to 8-bit DAC:
```
mix = ay*1.5 + sn*0.75 + fm*1.5 + gt*1.5 + wt*1.5 + adpcm*1.5 + brr*1.5
clamp(-128, 127) -> 128+offset -> PWM
```

#### UART Processing

Every 294 ticks (~60Hz) calls `process_uart()`, parses commands from 2048-byte ring buffer.

### 2.3 AY8910 (YM2149)

Reference chip YM2149 (AY-3-8910), faithful emulation.

#### Architecture

- **3 square wave channels + 1 noise channel**: 12-bit frequency per channel (reg 0/1, 2/3, 4/5), 4-bit volume (reg 8-10)
- **Envelope generator**: 12-bit frequency (reg 11/12), 4 shapes (reg 13: hold/alternate/attack/continue)
- **Noise**: programmable divider (reg 6), 17-bit LFSR (`seed ^= 0x24000 if LSB, seed >>= 1`)
- **Mixing**: per-channel independent tone mask + noise mask (reg 7)
- **Volume table**: 32 levels (`ay_voltbl[32]`, 16 levels x2 symmetric)

#### Frequency Mapping

`AY_CLK = 1789772 Hz` (NTSC), 24-bit base `AY_BASE_INCR = 212779134`.
Internal counter increments by base_incr each tick, high 8 bits used as step to drive square/noise counters.

#### Rendering

Each tick: square wave toggle -> noise LFSR -> envelope step -> table lookup mix.
Square output = volume x square/noise mix, total = sum of 3 channels.

### 2.4 SN76489

Reference chip SN76489 (Sega Master System), supports 3 hardware variants.

#### Architecture

- **3 square wave channels + 1 noise channel**: 10-bit frequency per channel (high 6 + low 4 bits written separately), 4-bit volume
- **Volume table**: 16 levels (`sn_voltbl[16]`, logarithmic decay: 255->0)
- **Noise**: programmable divider (reg 6 low 2 bits: /1, /2, /4, /8)

#### 3 Variants

| Variant | Shift Register Width | Taps | Description |
|---------|----------------------|------|-------------|
| SN76489 (TI) | 15 bit | 0x0003 (bit0,1) | Original TI |
| Sega VDP (default) | 16 bit | 0x0009 (bit0,3) | SMS/Game Gear |
| SN76489A | 17 bit | 0x000C (bit2,3) | Atari variant |

Noise LFSR: white noise mode (bit4=0) `fb = rng & 1`, periodic noise mode (bit4=1) `fb = (masked != 0) && (masked != taps)`.

#### Rendering

`SN_CLK = 3579545 Hz`, `SN_BASE_INCR = 212779193`, same 24-bit counter as AY.
Square wave toggle + noise, output `>>2` attenuation.

#### Command Format

VGM standard 2-byte: first byte `0x80|reg`, second byte data. Latch mechanism: `dat & 0x80` updates last_reg.

### 2.5 FM Synthesis (Custom 2-Op)

Custom lightweight 2-Operator FM synthesis core, adapted from ArduinoUnoTinyFmKeyboard for 38MHz/17640Hz.

#### Architecture

- **16 voice, 32 operator**: each voice = op1 (modulator) + op2 (carrier)
- **6 waveforms** x 64 entries = 384 bytes (code segment):

| Index | Name | Characteristics |
|-------|------|----------------|
| 0 | tri | Triangle, 64 points |
| 1 | clipsin | Clipped sine, +/-20 saturation |
| 2 | rect | Rectangle, +/-21 |
| 3 | sin | Standard sine, +/-31 |
| 4 | saw | Sawtooth, +/-31 |
| 5 | abssin | Absolute sine (full-wave rectified) |

- **Phase accumulator**: 16-bit (8.8 fixed point), `pos += step`, `idx = (pos >> 8) & 0x3F`
- **Waveform lookup**: `fm_waves[(wave_idx << 6) | idx]` - bit shift instead of multiply
- **Frequency**: MIDI C1-C9 (note 24-127), 104 entries, `step = freq * 16384 / 17640`

#### 2-Operator FM Algorithm

Per voice per sample period:
1. **OP1 (modulator)**: `idx = (pos>>8 + fb_val) & 0x3F`, `wave = fm_waves[wi*64+idx]`
2. **OP1 envelope**: `ch_out = wave * (level+1) * (tl+1) >> 10` - shift instead of divide
3. **OP1 feedback**: `fb_val = ch_out >> fb` (fb=0-7), accumulated for next phase
4. **OP2 (carrier)**: `idx = (pos>>8 + op1_ch_out) & 0x3F` - FM core
5. **OP2 output**: same envelope formula as OP1
6. **voice_out = op2_out**, total = sum(voice_out)

#### Tone Template (reg 0x00-0x09, global)

| Register | Description |
|----------|-------------|
| 0x00 | Modulator MULTI (0-15) |
| 0x01 | Carrier MULTI (0-15) |
| 0x02 | Modulator TL (0-31, modulation depth) |
| 0x03 | Carrier TL (high 5 bits) + Feedback (low 3 bits) |
| 0x04 | Modulator AR\|DR (high 4=atk, low 4=dec) |
| 0x05 | Carrier AR\|DR |
| 0x06 | Modulator SL\|RR (high 4=sul, low 4=rel) |
| 0x07 | Carrier SL\|RR |
| 0x08 | Modulator waveform (low 3 bits, 0-5) |
| 0x09 | Carrier waveform (low 3 bits, 0-5) |

Tone template auto-applied to both operators on Note On. `mul=0` -> step = freq/2.

#### ADSR Envelope

4 states: Attack -> Decay -> Sustain -> Release.
Speed table `fm_env_cnt[16]` (0-255) controls tick interval per envelope level.
`env_cnt` counts down to 0 triggering one level change. Level range 0-31.
Round-robin: `fm_wait_cnt & 0x0F`, each tick updates only 1 operator's envelope (16 voice = full cycle every 16 ticks).

#### Computational Optimizations

- 8.8 fixed-point phase, bit-shift for waveform index (>>8, & 0x3F), no floating point
- Bit-shift table lookup `(wave_idx << 6)` instead of multiply index
- Envelope `>> 10` instead of `/(31*31)` (error < 0.5%)
- Round-robin envelope tick distributes CPU load
- Feedback `>> fb` (0-7) single shift instruction

### 2.6 Gigatron TTL Waveform

Reference: Gigatron TTL computer, 4ch waveform synthesis.

#### Architecture

- **4 channels**: shared 256-byte waveform table (customizable at runtime)
- **16-bit phase accumulator**: `osc += step`, `idx = (osc >> 7) & 0xFC`
- **fnum direct write**: 14-bit (7-bit fnumL + 7-bit fnumH), `step = key * 44 / 101`
- **Waveform selection**: `wavX` (XOR mask) + `wavA` (amplitude offset)
- **Render rate**: 8820Hz (renders every 2 ticks)

#### Waveform Table

Pseudo-randomly generated at init: 4 waveforms, 4 bytes per group: noise/tri/pulse/saw.
Customizable at runtime via addr 0x14-0xFF.

#### Rendering

Per channel: `idx = (osc >> 7) & 0xFC ^ wavX`, `val = sound[idx] + wavA`, clamp to 0-63.
4 channels summed + bias 3, output `samp - 131` mapped to +/-128.

### 2.7 WT Wavetable

Wavetable synthesis, adapted from fm.c architecture and ArduinoUno_wavetable_synthesis.

#### Architecture

- **4 channels**: independent phase/envelope/volume
- **14 preset waveforms** x 128 entries = 1792 bytes (code segment):

| Index | Name | Characteristics |
|-------|------|----------------|
| 0 | sq12 | GB duty 12.5% square |
| 1 | sq25 | GB duty 25% square |
| 2 | pulse50 | 50% square |
| 3 | sq75 | GB duty 75% square |
| 4 | sin | Standard sine, +/-31 |
| 5 | clipsin | Clipped sine, +/-20 saturation |
| 6 | abssin | Absolute sine (full-wave rectified) |
| 7 | halfsin | OPL3 Sin1: +sine/0 |
| 8 | qsin | OPL3 Sin3: sine/0/sine/0 |
| 9 | altsin | OPL3 Sin4: 2x freq +/-/0/0 |
| 10 | althalfsin | OPL3 Sin5: 2x freq +/0/0/0 |
| 11 | tri | Triangle |
| 12 | saw | Sawtooth |
| 13 | gb_dmg | DMG default WaveRAM |

- **Phase accumulator**: 16-bit, `pos += step`, `idx = (pos >> 5) & 0x7F`
- **Waveform lookup**: `wt_waves[(wave_idx << 7) | idx]` - 7-bit shift instead of multiply
- **Frequency**: MIDI C1-C9 (note 24-127), 104 entries, `step = freq * 8192 / 17640`
- **Wave length**: switchable 32/64/128 (reg 0x14)

#### ADSR Envelope

4 states: Attack -> Decay -> Sustain -> Release.
Speed table `wt_env_cnt[16]` (same as FM).
Round-robin: `wt_wait_cnt & 0x03`, full cycle every 4 ticks (4 channels).

#### Rendering

Per channel: waveform lookup -> envelope -> `ch_out = wave * (level+1) * (vol+1) >> 10` -> sum.
Tone template (reg 0x10-0x13) shared globally, applied to channel on Note On.

### 2.8 ADPCM Sampling

YM2608 ADPCM Type-A decode, 49-level JEDI lookup, 12-bit accumulator.

#### Encoding Format

- **JEDI lookup**: `jedi_table[49][16]` = 784 x s16 (1568 bytes, code segment)
- **12-bit accumulator**: updated every 2 nibbles, `acc = CLIP12(acc + table[nibble])`
- **Step table**: `adpcm_step_inc[8] = {-16,-16,-16,-16,32,80,112,144}`
- **8-bit compression ratio**: ~3.2:1
- **Linear interpolation**: `s_prev + (s_cur - s_prev) * frac >> 8`

#### ADPCM Decode Principle

YM2608 Type-A ADPCM (Adaptive Differential Pulse Code Modulation):

1. **Storage**: Each sample encoded as 4-bit nibble, 2 nibbles packed per byte (ROM addressed by nibble)
2. **Lookup**: Uses current `adpcm_step` (0-768) as row, nibble value (0-15) as column, looks up `jedi_table[step + nibble]` for delta
3. **Accumulate**: 12-bit accumulator `acc = CLIP12(acc + delta)`, bit11 sign-extends to s16
4. **Adaptive**: `adpcm_step += adpcm_step_inc[nib & 7]`, clamped [0, 768] — large quantization error increases step (wider range next time), small error decreases step (higher precision)
5. **Output**: acc is the decoded 12-bit sample value

Pros: High compression (~3.2:1), simple algorithm (table lookup + accumulate, no multiply/divide), ideal for 8-bit MCU. Cons: quantization noise increases with frequency (step can only capture trends, not encode high-freq precisely).

#### Drum Machine Sequencer (Host-driven)

The drum machine is host-driven by Python, reading MIDI mapping + drum sequences from config files:

- **drum.ini**: Global config — MIDI pitch mapping (`bass=36`, `snare=38`...), volume, aliases (`oh=x+closed_hihat`)
- **drum_patterns/*.ini**: One file per style, with `[info]` (BPM/bars/swing) and `[pattern]` (beat sequence)
- **Beat sequence**: One step per line, using aliases (`bass`, `oh`) or MIDI pitch numbers, `.` for rest
- **Swing**: `swing=50` = 16th-note triplet delay percentage, creates swing feel

```
python tools/adpcm_drumkit_pro.py           # Play all styles
python tools/adpcm_drumkit_pro.py 3          # Play style #3
python tools/adpcm_drumkit_pro.py list       # List all styles
```

#### Drum Pitch Shift

Drum pitch shift via step register (0x27/0x2D) changes ADPCM playback rate:
- `step = base_step * 2^(semi/12)`, semi = semitone offset, base_step = original value per drum
- E.g. Bass Drum base_step=0x0100, up one octave: step=0x0200, down one octave: step=0x0080
- No loop, no CPU limit on pitch shift range
- When step < 0x0100, linear interpolation enabled (sub-sample), smoother quality

```
python tools/adpcm_pitch_test.py             # 6 drums semitone pitch sweep
```

#### SF2 Melodic Instruments (5 types, looped, DSR envelope)

#### Drums (6 types, one-shot, no loop)

| ID | Name | Sample Length (bytes) | Base Step | Description |
|----|------|----------------------|-----------|-------------|
| 0 | BD (Bass Drum) | 854 | 0x0100 | Kick drum |
| 1 | SD (Snare) | 1219 | 0x0100 | Snare drum |
| 2 | CY (Cymbal) | 5670 | 0x0080 | Cymbal |
| 3 | HH (Hi-Hat) | 732 | 0x0100 | Hi-hat |
| 4 | TM (Tom) | 1219 | 0x0080 | Tom |
| 5 | RS (Rimshot) | 244 | 0x0080 | Rimshot |

- Pitch shift: Python computes `step = base_step * ratio`, writes via 0x27/0x2D
- Drum pitch shift has no upper limit (no loop, no ISR pressure)
- Envelope: env_state=0 (no ADSR), `out>>5` gain normalization, `total += out * vol >> 5`

#### SF2 Melodic Instruments (5 types, looped, DSR envelope)

| ID | Name | Sample Length (bytes) | Loop Range (nibbles) |
|----|------|----------------------|----------------------|
| 0 | Piano | 1164 | 1915->2127 |
| 1 | SlapBass | 1835 | 3017->3512 |
| 2 | Guitar | 3722 | 7080->7291 |
| 3 | Oboe | 2015 | 2425->2852 |
| 4 | Harp | 3187 | 3374->6372 |

- ROM: `SF2_ROM[11936]` (11.7 KB), 12-bit normalized ADPCM
- Envelope: DSR only (no Attack), note_on sets level=31 directly, note_off triggers release
- Pitch shift: via 0x27/0x2D, upper limit 0x0400 (loop present, C5+ causes crash)
- Loop: loop wrap restores acc/adpcm_step state (prevents drift)

#### SF2 Pitch Shift

SF2 melodic instruments support pitch shift, computed by host:
- `step = 0x0100 * 2^(semi/12)`, semi = midi_note - orig_pitch (sample base pitch)
- Step range clamped 0x0020-0x0200 (0.125x ~ 2x rate), prevents loop decode overflow
- Play sequence: send `0x15+ch` (note on, data=16+inst_idx) -> write step -> send `0x33` (midi note, triggers DSR)

#### SF2 Instrument ADSR Templates

DSR parameters for 5 SF2 instruments (atk unused, set to default):

| Instrument | atk | dec | sul | sus | rel | Characteristics |
|------------|-----|-----|-----|-----|-----|----------------|
| Piano | 3 | 4 | 8 | 5 | 4 | Medium decay, mid sustain |
| SlapBass | 2 | 9 | 14 | 14 | 4 | Fast decay, high sustain (near-hold) |
| Guitar | 2 | 5 | 7 | 7 | 6 | Balanced, medium release |
| Oboe | 3 | 5 | 7 | 7 | 7 | Similar to Guitar, slightly slower release |
| Harp | 2 | 6 | 7 | 7 | 6 | Balanced, similar to Guitar |

#### ADPCM Channel Assignment

6 channels multiplexed: ch0-5 can play drums or SF2 melody simultaneously.
Distinguished by data range:
- data 0-5: drums
- data 16-25: SF2 instruments (16+inst_idx, inst_idx 0-4)

#### ADSR Envelope (SF2 melody + WT shared)

| Parameter | Address | Description |
|-----------|---------|-------------|
| Attack | 0x10 high 4 bits | SF2 melody does not use (direct level=31) |
| Decay | 0x10 low 4 bits | Decay speed |
| Sustain Level | 0x11 high 4 bits | 0-15 |
| Sustain | 0x11 low 4 bits | Sustain speed |
| Release | 0x12 | Release speed |

Speed table: `pcm_env_cnt[16] = {0,1,2,3,4,5,7,10,13,20,29,43,64,86,128,255}`
Round-robin: full cycle every 4 ticks (6 channels).

#### ADPCM Loop Principle

ADPCM decode is stateful (12-bit acc + step index change with each sample), so looping cannot simply jump back to an address.

**SF2 melodic instrument looping**:
- ROM stores `loop_start`, `loop_end` (nibble addresses) and `loop_acc`, `loop_step` (decoder state at loop point) per instrument
- When play pointer exceeds loop_end: `addr = loop_addr; acc = loop_acc; adpcm_step = loop_step`
- Restoring decoder state ensures perfect waveform continuity at loop point, no pop/click

**Drums**: one-shot, no loop, auto-stops at end_addr and releases channel.

#### ADPCM ADSR Envelope Principle

ADPCM/SF2/BRR share the same ADSR architecture (env_state finite state machine):

```
note_on -> Attack(1) -> Decay(2) -> Sustain(3) -> note_off -> Release(4) -> level=0 release channel
```

**Speed control** (env_cnt/step counter mechanism):
- `env_step` = decay interval for current stage (looked up from env_cnt table)
- Each envelope tick: `env_cnt -= env_step`; if env_cnt >= env_step, skip; otherwise level changes by one step
- Larger value = shorter interval = faster decay

**SF2 special behavior**: note_on enters Sustain directly (no Attack), Sustain stage **holds** level unchanged (no decay), waits for note_off to trigger Release. This suits SF2 melodic instruments with loop points for infinite sustain.

**BRR special behavior**: Full ADSR (has Attack), Sustain stage **continues decaying to 0** (not holding), sus controls decay speed. All instruments eventually auto-decay to silence and release channel, no manual note_off needed.

### 2.9 BRR Sampling (SNES DSP filter=0)

BRR (Binary Resonance Representation) 4ch melodic sample synthesis, GME Spc_Dsp.cpp bit-exact implementation.

#### Architecture

- **4 channels**: independent loop/frequency/envelope/volume
- **14 instruments**: generated from YRW801 (OPL4) ROM XI files (gen_brr_rom.py)
- **Encoding**: BRR filter=0 (stateless, 9 bytes/block, 16 samples/block, ~56% compression)
- **Sample rate**: 17640Hz (MCU DAC sweet spot)
- **GME bit-exact decode**: `s = ((nibble >> rs) << ls) * 2`, rs/ls table lookup

#### BRR Encoding Format

SNES SPC700 DSP BRR (Binary Resonance Representation):

- **Block structure**: each block = 1 byte header + 8 bytes data (9 bytes total)
- **Header**: high 4 bits = `scale` (0-15, quantization level), bit3 = loop flag (unused in this project, filter=0)
- **Data**: 8 bytes = 16 nibbles (each 4-bit signed, encoding 16 samples)
- **Compression**: 16-bit PCM -> 4-bit nibble = ~4:1, plus header overhead = ~3.5:1
- **Filter**: filter=0 (chosen for this project), stateless, each sample decoded independently, no previous-sample filter state needed

#### BRR Decode Principle (GME Spc_Dsp.cpp bit-exact)

This project uses filter=0 (simplest mode, stateless):

1. **Extract nibble**: From block's 8-byte data, locate byte pair and position by sample index
   - `bp = sample_idx >> 2` (0-3: which byte pair)
   - `sp = sample_idx & 0x03` (0-3: which nibble within pair)
2. **Sign-extend**: `nybbles <<= (sp << 4)`, high 4 bits sign-extend to s16
3. **Scale**: `raw >>= rs` (right-shift removes scale quantization), `s = raw << ls` (left-shift restores dynamic range)
4. **Gain**: `s <<= 1` (*2 gain compensation), clamp [-32768, 32767]
5. **Output**: s is the decoded 16-bit sample value

Shift tables (16 scale levels):
- `brr_right_shift[16] = {13,12,12,...,16,16,16}` — higher scale = more right-shift = more quantization noise
- `brr_left_shift[16] = {0,0,1,2,...,11,11,11,11}` — higher scale = more left-shift = compensation

**vs ADPCM comparison**:
| | ADPCM (YM2608) | BRR (SNES DSP) |
|--|----------------|----------------|
| Compression unit | nibble (4-bit) | block (9 bytes/16 samples) |
| Stateful | Yes (acc + step) | No (filter=0) |
| Loop complexity | Must restore acc+step | Simple address jump |
| Quantization noise | Adaptive (good at low freq) | Fixed scale (flat) |
| MCU computation | Table lookup+accumulate (light) | Shift+table lookup (light) |

#### Instrument List

| # | Name | native_midi | ROM Size | Characteristics |
|---|------|-----------|---------|----------------|
| 0 | AcPiano | 51 | 8289B | Bright piano (s2) |
| 1 | Violin | 45 | 1560B | Violin |
| 2 | Strings | 42 | 4944B | String section |
| 3 | Harp | 34 | 2256B | Harp |
| 4 | Accordion | 38 | 1764B | Accordion |
| 5 | Organ | 63 | 648B | Pipe organ |
| 6 | Fretless | 46 | 1792B | Fretless bass |
| 7 | JazzGtr | 58 | 504B | Jazz guitar |
| 8 | DistGtr | 59 | 576B | Distortion guitar |
| 9 | Celesta | 30 | 2904B | Celesta |
| 10 | Flute | 42 | 1764B | Flute |
| 11 | Recorder | 43 | 3168B | Recorder |
| 12 | Oboe | 40 | 1404B | Oboe |
| 13 | Clarinet | 51 | 1344B | Clarinet |

ROM total ~23KB, all seam=0 (perfect loop).

#### ADSR Envelope

4 states: Attack -> Decay -> Sustain -> Release.
Speed table `brr_env_cnt[16]` (same as FM/WT).
Round-robin: every 4 ticks (4 channels).

**ADSR directly controls volume**: `out * level >> 5`, bypasses vol.

| Parameter | Address | Meaning |
|-----------|---------|---------|
| atk (high 4) \| dec (low 4) | 0x18 | attack/decay speed |
| sul (high 4) \| sus (low 4) | 0x19 | decay target (sul*2=level) / sustain decay speed |
| rel | 0x1A | release speed |

**Key behavior**: sustain stage continues decaying to 0 (not holding), sus controls decay speed. level=0 auto-releases channel.

#### BRR Instrument ADSR Templates (14 instruments)

Sorted by ROM instrument number, all tuned and verified (atk/dec/sul/sus/rel range 0-15, indexes env_cnt[], larger = faster):

| # | Instrument | atk | dec | sul | sus | rel | Characteristics |
|---|-----------|-----|-----|-----|-----|-----|----------------|
| 0 | AcPiano | 13 | 3 | 2 | 4 | 4 | Instant attack, fast decay, low target, mid sustain/release |
| 1 | Violin | 10 | 4 | 2 | 10 | 10 | Mid attack, slow decay/sustain/release (sustained) |
| 2 | Strings | 10 | 4 | 2 | 10 | 10 | Same as Violin |
| 3 | Harp | 15 | 8 | 2 | 4 | 4 | Instant attack, mid decay, similar to piano |
| 4 | Accordion | 7 | 3 | 8 | 4 | 4 | Mid attack, fast decay, high target (sustain feel) |
| 5 | Organ | 5 | 6 | 12 | 6 | 5 | Slow attack, mid decay, high target (sustained) |
| 6 | Fretless | 15 | 3 | 12 | 2 | 2 | Instant attack, fast decay, high target, fast sustain/release |
| 7 | JazzGtr | 15 | 3 | 12 | 2 | 2 | Same as Fretless |
| 8 | DistGtr | 15 | 8 | 2 | 4 | 4 | Instant attack, mid decay, low target |
| 9 | Celesta | 15 | 10 | 6 | 2 | 2 | Instant attack, slow decay, mid target, very fast sustain/release |
| 10 | Flute | 3 | 4 | 9 | 5 | 4 | Slow attack, mid decay, high target (sustained) |
| 11 | Recorder | 10 | 4 | 2 | 10 | 10 | Mid attack, slow decay/sustain/release |
| 12 | Oboe | 10 | 4 | 2 | 10 | 10 | Same as Recorder |
| 13 | Clarinet | 10 | 4 | 2 | 10 | 10 | Same as Recorder |

Sustained instruments (Violin/Strings/Organ/Flute/Recorder/Oboe/Clarinet): low sul + slow sus/rel -> sustain stage decays slowly, long sustain.
Plucked instruments (AcPiano/Harp/DistGtr): low sul + fast dec -> short decay, short sustain.

#### BRR Loop Principle

BRR filter=0 is stateless decode, looping is much simpler than ADPCM — just jump back to block address, no need to restore decoder state.

**Loop method**: ROM stores `n_blocks` (total blocks) and `loop_block` (loop start block) per instrument. When play pointer reaches end:
```
if (block_idx >= n_blocks) block_idx = loop_block;
```
Simply jumps back, next sample continues decoding from loop_block sample 0, waveform seamless.

**seam=0 verification**: ROM generation (gen_brr_rom.py) applies crossfade at loop points, verifies loop start/end sample difference = 0 (seam=0), ensuring no pop/click.

**vs ADPCM loop**: ADPCM must restore both `acc` and `adpcm_step` state variables for seamless loop; BRR filter=0 is stateless, one address jump completes the loop. This is why BRR was chosen over ADPCM for melodic sampling.

#### Pitch Shift Principle

Pitch shift by changing sample playback rate, shared by all sampling modules:

**8.8 fixed-point step**: high 8 bits = samples advanced per tick, low 8 bits = fractional part (linear interpolation).
- `step = 0x0100` = original speed (1.0 sample per tick)
- `step = 0x0200` = 2x speed (one octave up)
- `step = 0x0080` = 0.5x speed (one octave down)

**Semitone stepping**: `step = 0x0100 * 2^(semi/12)`, host Python computes then writes to MCU step register.
MCU also stores 12-level semitone lookup tables (`brr_semi_up[12]`, `brr_semi_dn[12]`), can directly look up by midi note difference times octave offset.

**Linear interpolation**: When step < 0x0100 (down-pitch), frac part interpolates between adjacent samples:
`out = s_prev + (s_cur - s_prev) * frac >> 8`
Prevents锯齿 noise from step skipping during down-pitch.

#### ROM Generation Toolchain

```
XI file -> resample 17640Hz -> PCM crossfade -> BRR encode -> BRR crossfade -> verify seam=0
```
See [docs/xi_brr_workflow.md](docs/xi_brr_workflow.md) and [docs/brr_adsr_debug.md](docs/brr_adsr_debug.md).

### 2.10 Abandoned Sound Sources

The following 4 sound sources were implemented during the STC8H8K64U prototype phase but were not enabled after migrating to STC32G. Source files remain in the `STC32G12K128/` directory; `#include` directives in `main.c` are commented out, and UART command branches are reserved but inactive.

| Source | Command Prefix | Channels | Status | Reason for Removal |
|--------|---------------|----------|--------|---------------------|
| **SCC** (Konami) | `0xD2` (4 bytes) | 5 ch | Source exists, commented out | No longer needed after WT matured; SCC required A51 assembly |
| **GB DMG** (Game Boy) | `0xB3` (3 bytes) | 4 ch | Source exists, commented out | Functionality overlaps with WT sq12/sq25/sq75/gb_dmg waveforms |
| **NES APU** (Ricoh 2A03) | `0xB4` (3 bytes) | 2 pulse+1 tri+1 noise+1 DMC | Source exists, commented out | Overlaps with AY8910/SN76489, high CPU overhead |
| **SAA1099** (Philips) | `0xBD` (3 bytes) | 6 ch + 2 noise | Source exists, commented out | Insufficient channel demand, overlaps with existing sources |

> Related files: `scc.c/h` `gb.c/h` `nes.c/h` `saa1099.c/h` (and corresponding `.LST` build outputs)
> Related tool: `tools/gen_scc_table.py` (SCC step lookup table generation, legacy)

---

## 3. UART Protocol

### 3.1 General Commands

| Command | Format | Checksum | ACK | Description |
|---------|--------|---------|-----|-------------|
| SN76489 | `[0x50][data]` | None | None | 2 bytes, transparent |
| SN76489 variant | `[0x52][variant]` | None | None | 0=SN76489 1=SegaVDP 2=SN76489A |
| AY8910 | `[0xA0][reg][data]` | None | None | 3 bytes, transparent |
| FM | `[0x51][addr][data][xor]` | XOR | 0xAA/0xFF | 4 bytes |
| Gigatron | `[0xB0][addr][data][xor]` | XOR | Discard | 4 bytes |
| WT/ADPCM/BRR | `[0xC0][addr][data][xor]` | XOR | 0xAA/0xFF | 4 bytes, addr range routes to module |

### 3.2 WT Registers (0xC0, addr 0x00-0x14)

WT and ADPCM/BRR share 0xC0 prefix, main.c routes by addr range: 0x00-0x14->WT, 0x15-0x33->ADPCM, 0x34-0x4F->BRR.

| Address | Description |
|---------|-------------|
| 0x00-0x03 | ch0-3 Note On (data=MIDI note 24-127) |
| 0x04-0x07 | ch0-3 Note Off |
| 0x08-0x0B | ch0-3 Volume (0-31) |
| 0x10 | ADSR attack\|decay |
| 0x11 | ADSR sustain_level\|sustain |
| 0x12 | ADSR release |
| 0x13 | Wave select (0-13) |
| 0x14 | Wave length (0=32, 1=64, 2=128) |

### 3.3 FM Registers (0x51, addr 0x00-0x3F)

| Address | Description |
|---------|-------------|
| 0x00-0x09 | Tone parameters (global, 10 bytes) |
| 0x10-0x1F | Note On voice 0-15 (data=MIDI note) |
| 0x20-0x2F | Note Off voice 0-15 |
| 0x30-0x3F | Volume override voice 0-15 (0-31) |

### 3.4 ADPCM Registers (0xC0, addr 0x15-0x33)

| Address | Description |
|---------|-------------|
| 0x15-0x1A | ch0-5 Note On (data: 0-5=drum, 16-25=SF2 instrument) |
| 0x1B-0x20 | ch0-5 Note Off |
| 0x21-0x26 | ch0-5 Volume (0-31) |
| 0x27-0x2C | ch0-5 Step Hi (pitch shift high byte) |
| 0x2D-0x32 | ch0-5 Step Lo (pitch shift low byte) |
| 0x33 | MIDI Note (follows SF2 Note On, 24-95) |

### 3.5 BRR Registers (0xC0, addr 0x34-0x4F)

| Address | Description |
|---------|-------------|
| 0x34-0x37 | ch0-3 Note On (data: 0-13=instrument index) |
| 0x38-0x3B | ch0-3 Note Off |
| 0x3C-0x3F | ch0-3 Volume (0-31) |
| 0x40-0x43 | ch0-3 MIDI Note (24-127) |
| 0x44-0x47 | ch0-3 Step Hi (8.8 fp) |
| 0x48-0x4B | ch0-3 Step Lo (8.8 fp) |
| 0x4C | ADSR atk\|dec |
| 0x4D | ADSR sul\|sus |
| 0x4E | ADSR rel |

---

## 4. Host Tools

All serial tools default to COM12 @ 115200 baud (change at script header).
Dependency: `pip install pyserial`

### 4.1 VGM Player

```
python tools/vgm_player.py --list --vgm-dir vgm/ay8910     # List AY8910 tunes
python tools/vgm_player.py 10 --vgm-dir vgm/ay8910          # Play #10
python tools/vgm_player.py --list --vgm-dir vgm/sn76489     # List SN76489 tunes
python tools/vgm_player.py 16 --vgm-dir vgm/sn76489          # Play #16
python tools/vgm_player.py --list --vgm-dir vgm/opll        # List FM tunes
python tools/vgm_player.py <N> --vgm-dir vgm/opll           # Play FM
python tools/vgm_player.py --fm-note 0 60                     # FM ch0 C4 single note
python tools/vgm_player.py --fm-scale                         # FM C1-C9 sweep
python tools/vgm_player.py --wt-scale                         # WT C2-C6 sweep
python tools/vgm_player.py --loop --vgm-dir vgm/ay8910       # Loop play
python tools/vgm_player.py --speed 0.5 --vgm-dir vgm/ay8910  # 0.5x speed
```

Supported chips: AY8910, SN76489, FM, WT, Gigatron.
Options: `--port COM3` `--baud 115200` `--dump 1` (hex dump command stream)

### 4.2 ADPCM Drum Tests

```
python tools/adpcm_test.py                    # 14 rhythm styles, all play
python tools/adpcm_test.py 3                  # Play style #3
```

Hardcoded 14 styles. 6 drums (BD/SD/CY/HH/TM/RS).

### 4.3 ADPCM Drum Machine (ini-driven)

```
python tools/adpcm_drumkit_pro.py             # Play all styles
python tools/adpcm_drumkit_pro.py 3          # Play style #3
python tools/adpcm_drumkit_pro.py list       # List all styles
```

Reads MIDI mapping (35-81) + aliases + volume from `drum.ini`, rhythm sequences from `drum_patterns/*.ini`.
Supports per-drum volume, per-pattern volume override, swing timing.

### 4.4 ADPCM Pitch Shift Tests

```
python tools/adpcm_pitch_test.py             # 6 drums C1->C8 pitch sweep
python tools/adpcm_div_test.py               # Same drum, different step values
```

### 4.5 ADPCM Channel Debug

```
python tools/adpcm_ch_test.py                 # Per-channel sound confirmation
python tools/adpcm_debug.py                   # Trigger channels + read channel mask
python tools/adpcm_led_test.py                 # 6-channel LED confirmation
```

### 4.6 SF2 Melody Tests

```
python tools/sf2_test.py                      # 5 instruments play in sequence
python tools/sf2_test.py piano 60             # Piano C4
python tools/sf2_test.py all 60               # All instruments C4
python tools/sf2_test.py chord                # Chord test
```

### 4.7 SF2 Pitch Sweep

```
python tools/sf2_sweep.py                     # All instruments C1->4x->C1
python tools/sf2_sweep.py piano               # Piano only
python tools/sf2_pitch_test.py                # Drum path pitch (no ADSR)
```

### 4.8 WT Sweep Test

```
python tools/wt_scale_test.py                 # 14 waveforms C2<->C6 loop sweep
python tools/wt_pcm_debug.py                  # WT+ADPCM simple test
```

### 4.9 BRR Sweep Test

```
python tools/brr_uart_test.py                 # 14 instruments sweep (up->down, 4ch round-robin)
python tools/brr_uart_test.py 0               # Test AcPiano only (by index)
python tools/brr_uart_test.py violin           # Test Violin only (by name)
```

### 4.9 Offline Tools (no serial required)

**SF2 sampling pipeline**:
```
python tools/sf2_extract.py                  # SF2 -> WAV + JSON + C header
python tools/sf2_preview.py                  # PC simulates MCU ADPCM decode (loop+pitch)
python tools/sf2_verify.py                   # ADPCM encode-decode roundtrip verification
python tools/sf2_loop_sim.py                  # PC simulates MCU loop wraparound
python tools/sf2_player_sim.py <dir> [idx] [note] [dur]  # Full ADPCM playback sim
python tools/sf2_drum_test.py                  # SF2 instruments with drum encoder verify
python tools/sf2_snese_sim.py                  # SNES SoundFont preview WAV
```

**ADPCM ROM generation**:
```
python tools/gen_adpcm_rom.py                 # WAV -> ADPCM ROM C header (sf2_rom.h)
python tools/adpcm_preprocess.py              # YM2608 raw drums -> resample 17640Hz -> ADPCM C header
python tools/adpcm_decode_wav.py               # ROM -> WAV decode verification
python tools/adpcm_interp_test.py             # PC linear interpolation algorithm verify
python tools/adpcm_step_sim.py                 # PC fixed-point step pitch sim
```

**Loop search algorithms**:
```
python tools/adpcm_perfect_loop.py            # Min variance + palindrome + crossfade auto-loop
python tools/fix_loop.py                      # Amplitude+slope matching better loop_end search
python tools/polyphone_loop.py                 # Multi-point quality scoring + crossfade baking
```

**BRR format (SNES DSP)**:
```
python tools/brr_test.py                      # BRR encode/decode verification (GME Spc_Dsp compliant)
python tools/brr_loop.py                      # BRR block-based loop simulation
python tools/gen_brr_rom.py                  # XI -> BRR ROM C header generation (14 instruments)
python tools/brr_uart_test.py                 # BRR 14-instrument sweep test (serial)
```

**XI format (YRW801/OPL4 waveforms)**:
```
python tools/xi_parse.py --list               # List XI instruments
python tools/xi_parse.py --wav 0x10 0x16       # Export WAV
python tools/xi_demo.py                        # XI instrument envelope+loop preview
python tools/xi_adpcm_test.py                  # XI -> ADPCM loop test
python tools/xi_brr_test.py                    # XI -> BRR filter=0 loop test
python tools/xi_crossfade_test.py              # XI crossfade loop test
python tools/xi_brr_crossfade_test.py          # XI BRR crossfade test
python tools/yrw801_extract.py                 # YRW801 ROM parse + WAV export
```

**Other**:
```
python tools/piano_pitch_sweep.py             # Grand Piano C3 sample C1-C8 sweep
python tools/gen_scc_table.py                 # SCC step lookup table generation (legacy)
```

### 4.10 Config Files

| File | Description |
|------|-------------|
| `tools/drum.ini` | MIDI GM 35-81 drum mapping (drum_id + ratio) + 19 aliases + global volume |
| `tools/drum_patterns/*.ini` | 14 independent style rhythm sequences (bpm/bars/swing/vol) |

## 5. Toolchain & Build

### 5.1 Toolchain

| Tool | Version/Path | Description |
|------|-------------|-------------|
| Compiler | `D:/Keil_v5/C251/BIN/C251.exe` | Keil C251 (not C51), STC32G C251 compatible |
| Linker | `D:/Keil_v5/C251/BIN/L251.exe` | C251 linker (not BL51) |
| HEX convert | `D:/Keil_v5/C251/BIN/OH251.exe` | Outputs Intel HEX |
| Flashing | STC-ISP | Manual flash (serial P3.4/P3.5) |
| Host tools | Python 3 + pyserial | Test/playback tools |

### 5.2 Build Options

```
#pragma LARGE          - LARGE memory model (xdata/XRAM)
#pragma OPTIMIZE(8, SPEED) - Maximum optimization, speed priority
```

### 5.3 Build Steps

**Step-by-step**:
```bash
cd STC32G12K128
rm -f *.OBJ
D:/Keil_v5/C251/BIN/C251.exe ay8910.c "LARGE" "OPTIMIZE(8,SPEED)" "NOALIAS" 2>&1
D:/Keil_v5/C251/BIN/C251.exe sn76489.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1
D:/Keil_v5/C251/BIN/C251.exe gigatron.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1
D:/Keil_v5/C251/BIN/C251.exe fm.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1
D:/Keil_v5/C251/BIN/C251.exe wt.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1
D:/Keil_v5/C251/BIN/C251.exe adpcm.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1
D:/Keil_v5/C251/BIN/C251.exe brr.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1
D:/Keil_v5/C251/BIN/C251.exe main.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1
D:/Keil_v5/C251/BIN/L251.exe ay8910.OBJ,sn76489.OBJ,gigatron.OBJ,fm.OBJ,wt.OBJ,adpcm.OBJ,brr.OBJ,main.OBJ TO build/MAIN 2>&1
D:/Keil_v5/C251/BIN/OH251.exe build/MAIN HEXFILE\(build/MAIN.hex\) 2>&1
```

**One-liner (bash)**:
```bash
cd STC32G12K128 && rm -f *.OBJ ; D:/Keil_v5/C251/BIN/C251.exe ay8910.c "LARGE" "OPTIMIZE(8,SPEED)" "NOALIAS" 2>&1 ; D:/Keil_v5/C251/BIN/C251.exe sn76489.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1 ; D:/Keil_v5/C251/BIN/C251.exe gigatron.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1 ; D:/Keil_v5/C251/BIN/C251.exe fm.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1 ; D:/Keil_v5/C251/BIN/C251.exe wt.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1 ; D:/Keil_v5/C251/BIN/C251.exe adpcm.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1 ; D:/Keil_v5/C251/BIN/C251.exe main.c "LARGE" "OPTIMIZE(8,SPEED)" 2>&1 ; D:/Keil_v5/C251/BIN/L251.exe ay8910.OBJ,sn76489.OBJ,gigatron.OBJ,fm.OBJ,wt.OBJ,adpcm.OBJ,main.OBJ TO build/MAIN 2>&1 ; D:/Keil_v5/C251/BIN/OH251.exe build/MAIN HEXFILE\(build/MAIN.hex\) 2>&1 ; echo "BUILD DONE"
```

### 5.4 Build Notes

- Compiler is `C251.EXE` (not C51), linker is `L251.EXE` (not BL51)
- In bash, separate commands with `;` not `&&` - C251 WARNING returns non-zero exit code breaking `&&`
- Quote parentheses in bash: `"LARGE"` `"OPTIMIZE(8,SPEED)"`
- Escape HEX param parentheses: `HEXFILE\(build/MAIN.hex\)`
- Must `rm -f *.OBJ` first to clean stale object files
- `WARNING C115/C153` can be ignored
- Output: `build/MAIN.hex` -> flash with STC-ISP

## 6. Directory Structure

```
STC_Chiptune/
├── STC32G12K128/              # Firmware (Keil C251)
│   ├── main.c                # Main (Timer0 ISR + UART + mixing + LED)
│   ├── ay8910.c/h            # AY8910 emulation (3ch+noise+envelope)
│   ├── sn76489.c/h           # SN76489 emulation (3ch+noise, 3 variants)
│   ├── fm.c/h                # FM 2-Op synth (16 voice / 32 op / 6 waveforms)
│   ├── gigatron.c/h          # Gigatron TTL waveform (4ch, 256B shared table)
│   ├── wt.c/h                # Wavetable synth (4ch / 14 waveforms / ADSR)
│   ├── adpcm.c/h             # ADPCM decode (6ch: drums+SF2 melody)
│   ├── brr.c/h               # BRR 4ch melodic samples (SNES DSP filter=0)
│   ├── brr_rom.h             # BRR ROM (14 instruments, ~23KB, seam=0)
│   ├── types.h               # Shared type definitions
│   ├── sf2_rom.h             # SF2 sample ROM (5 instruments, 11936B)
│   ├── fmopn_2608rom.h       # YM2608 ADPCM drum ROM + JEDI table
│   └── build/                # Build output (MAIN.hex)
│
├── tools/                    # Python host tools
│   ├── vgm_player.py         # VGM player (AY/SN/FM/WT/Gigatron)
│   ├── adpcm_test.py         # Drum rhythm test (14 styles hardcoded)
│   ├── adpcm_drumkit.py      # Drum machine basic
│   ├── adpcm_drumkit_pro.py  # Drum machine enhanced (ini-driven)
│   ├── adpcm_pitch_test.py   # Drum pitch sweep
│   ├── adpcm_div_test.py     # Drum step comparison test
│   ├── adpcm_ch_test.py      # ADPCM per-channel test
│   ├── adpcm_debug.py        # ADPCM channel mask debug
│   ├── adpcm_led_test.py     # ADPCM LED test
│   ├── gen_adpcm_rom.py      # WAV -> ADPCM ROM C header generator
│   ├── adpcm_preprocess.py   # YM2608 raw drum resample+encode
│   ├── adpcm_decode_wav.py   # ROM -> WAV decode verify
│   ├── adpcm_interp_test.py  # Linear interpolation algorithm verify
│   ├── adpcm_step_sim.py    # Fixed-point step pitch sim
│   ├── adpcm_perfect_loop.py # Auto loop finder (min variance+palindrome+crossfade)
│   ├── adpcm_wav_test.py    # ADPCM encode/decode experiment
│   ├── fix_loop.py           # Search better loop_end
│   ├── polyphone_loop.py     # Multi-point quality score loop finder
│   ├── brr_test.py           # BRR encode/decode verify (SNES DSP)
│   ├── brr_loop.py           # BRR block-based loop simulation
│   ├── gen_brr_rom.py        # XI -> BRR ROM C header generation
│   ├── brr_uart_test.py      # BRR 14-instrument sweep test (serial)
│   ├── sf2_extract.py        # SF2 -> WAV + JSON + C header
│   ├── sf2_test.py           # SF2 melody hardware test
│   ├── sf2_sweep.py          # SF2 pitch sweep
│   ├── sf2_pitch_test.py     # SF2 drum path pitch test
│   ├── sf2_preview.py        # SF2 PC sim (ADPCM+loop+pitch)
│   ├── sf2_verify.py         # ADPCM encode-decode roundtrip verify
│   ├── sf2_loop_sim.py       # PC loop wraparound sim
│   ├── sf2_player_sim.py     # Full ADPCM playback sim
│   ├── sf2_drum_test.py      # SF2 drum encoder verify
│   ├── sf2_snese_sim.py      # SNES SoundFont preview
│   ├── xi_parse.py           # YRW801 XI parse+WAV export
│   ├── xi_demo.py            # XI instrument preview
│   ├── xi_adpcm_test.py      # XI -> ADPCM loop test
│   ├── xi_brr_test.py        # XI -> BRR filter=0 test
│   ├── xi_crossfade_test.py  # XI crossfade loop test
│   ├── xi_brr_crossfade_test.py # XI BRR crossfade test
│   ├── yrw801_extract.py     # YRW801 ROM parse+WAV export
│   ├── piano_pitch_sweep.py  # Grand Piano C3 sweep
│   ├── wt_scale_test.py      # WT 14 waveform C2<->C6 sweep
│   ├── wt_pcm_debug.py       # WT+ADPCM simple test
│   ├── gen_scc_table.py      # SCC lookup table generation (legacy)
│   ├── drum.ini              # MIDI 35-81 drum mapping+aliases+volume
│   └── drum_patterns/        # 14 independent style rhythm ini files
│
├── vgm/                      # VGM tune library
│   ├── ay8910/               # AY8910 (ZX Spectrum / MSX)
│   ├── sn76489/              # SN76489 (Sega Master System)
│   └── opll/                 # FM OPLL (YM2413)
│
├── docs/                     # Technical documentation
├── README.md                 # Chinese documentation
└── README_EN.md              # English documentation
```

## 7. Development History

### 7.1 Phase 1-6: STC8H8K64U Era

Prototype on 8051 (48MHz): SCC/AY8910/SN76489 emulation, GB/NES/SAA failed attempts.
See git history.

### 7.2 Phase 7: Migrate to STC32G12K128

STC32G C251, 38MHz, 128KB Flash, 4KB SRAM + 8KB XRAM.
- Ported all sound sources to C251
- Added FM (custom 2-Op) 16 voice synthesis
- Added Gigatron 4ch TTL waveform
- SCC removed (WT matured, no longer needed)

### 7.3 Phase 8: ADPCM Sampling

- Implemented YM2608 ADPCM Type-A decoder (JEDI table, 12-bit acc)
- Extracted 5 instruments from SF2 soundfont (Piano/SlapBass/Guitar/Oboe/Harp)
- 6 drum ROMs (BD/SD/CY/HH/TM/RS)
- DSR envelope (no Attack, avoids 4-bit quantization click)
- Drum pitch shift: Python computes step, MCU does not calculate
- SF2 pitch shift upper limit 0x0400 (loop present, C5+ causes crash)
- Drum pitch shift no limit (no loop, no pressure)

### 7.4 Phase 9: WT Waveform Expansion

- 14 preset waveforms (original 6 + 8 OPL3/GB style)
- Waveform length switchable (32/64/128)
- C2<->C6 loop sweep test

### 7.5 Phase 10: Drum Machine System

- 14 rhythm styles (Modern/Rock/Pop/Funk/HipHop/Ballad/SlowRock/HardRock/Disco/DancePop/Trance/Jazz/Bossa/Square)
- ini-driven: drum.ini (mapping+aliases+volume) + drum_patterns/ (independent styles)
- MIDI GM Percussion 35-81 full coverage
- 19 pitch shift alias shortcuts

### 7.6 Phase 11: BRR Melodic Sampling

- Implemented SNES DSP BRR filter=0 decoder (GME Spcc_Dsp.cpp bit-exact)
- 14 instruments from YRW801 ROM XI files (Piano/Violin/Strings/Harp/Accordion/Organ/Fretless/JazzGtr/DistGtr/Celesta/Flute/Recorder/Oboe/Clarinet)
- BRR ROM generation pipeline: resample -> PCM crossfade -> BRR encode -> BRR crossfade -> verify
- ADSR envelope (4-state, 14 instrument templates tuned and verified)
- ADSR debug: 5 bugs fixed (route range/volume formula/sul mapping/sustain behavior/channel release)
- 8-bit PWM DAC: tested HSPWM 10-bit, reverted due to audible ultrasonic noise floor (37kHz carrier)

## 8. Reference Projects & Porting Notes

All sound source cores are ported from open-source projects, deeply simplified and adapted for STC32G12K128 (C251, 38MHz, 4KB SRAM, 8KB XRAM).

### 8.1 AY8910 — Reference: libvgm (Open Source, BSD-3-Clause)

- **Original author**: Couriersud (libvgm), based on earlier work by Ville Hallik / Michael Cuddy / Tatsuyuki Satoh / Fabrice Frances / Nicola Salmoria, major rewrite in 2008
- **Original project**: `D:\working\vscode-projects\Reference_Project\vgm_libs\libvgm-master\emu\cores\ay8910.c` + `ayintf.c`
- **Original scale**: ~1620 lines (`ay8910.c`) + interface layer + dependencies `EmuStructs.h / snddef.h / EmuCores.h` framework

**Simplification (1620 lines -> 230 lines, ~86% code reduction)**:
- Removed DEV_DATA/DEV_DEF/DEVFUNC framework interface, replaced with direct function calls (`ay_wr()` / `ay_render()`)
- Removed I/O ports (AY8910's 8-bit parallel port), kept only audio registers (0-15)
- Removed channel mixing DAC model (R-C load network, internal impedance AY8910_INTERNAL_RESISTANCE=356 precise simulation), replaced with 32-level volume table direct lookup
- Removed floating-point sample rate resampling, fixed 17640Hz output, pre-computed frequency base (`AY_BASE_INCR`)
- Removed stereo/panning/mute/option bits and other advanced features
- Removed AY8930 extended mode, YM2149 divider selection variant support
- Envelope: kept all 4 shapes (hold/alternate/attack/continue)

### 8.2 SN76489 — Reference: libvgm (Open Source, BSD-3-Clause)

- **Original author**: Maxim (2001-2002), converted from original Delphi implementation, Charles MacDonald modified for SMS Plus
- **Original project**: `D:\working\vscode-projects\Reference_Project\vgm_libs\libvgm-master\emu\cores\sn76489.c` + `sn76489_private.h` + `sn764intf.c`
- **Original scale**: ~530 lines (`sn76489.c` + `sn76489_private.h`) + interface layer

**Simplification (530 lines -> 165 lines, ~69% code reduction)**:
- Removed DEV_DATA/DEV_DEF framework interface, replaced with direct function calls (`sn_wr()` / `sn_render()`)
- Removed floating-point `dClock` frequency tracking, replaced with pre-computed `SN_BASE_INCR` 24-bit fixed-point base
- Removed square wave "oversampling" intermediate position calculation (IntermediatePos / FLT_MIN), replaced with simple toggle
- Removed NeoGeoPocket dual-chip mode (T6W28 connect)
- Removed GameGear stereo write (GGStereoWrite)
- Removed panning/mute interfaces
- Kept 3 variants: SN76489 (TI 15-bit SR) / Sega VDP (16-bit, default) / SN76489A (17-bit), added 3rd variant beyond original
- Volume table: original 16 levels (0-4096, MAME standard), simplified to 16 levels (0-255, adapted for 8-bit output)

### 8.3 FM Synthesis — Reference: ArduinoUnoTinyFmKeyboard (Open Source)

- **Original author**: Keiji Katahira (ArduinoUnoTinyFmKeyboard, ATmega328P, 20MHz, 24kHz PWM)
- **Original project**: `D:\working\vscode-projects\Reference_Project\STC-MCU\extracted\ArduinoUnoFMsynsynthesizer-master\ArduinoUnoTinyFmKeyboard\`
- **Original scale**: ~668 lines (`.ino` + `fmtone.cpp` + `fmtone.h`), C++ class architecture
- **Original**: 5 voice (10 op), ATmega328P, 20MHz, 24kHz, AVR Timer1 ISR, 4 PWM pin options

**Porting changes (C++ class -> C251 pure C, 5 voice -> 16 voice)**:
- C++ -> pure C: `FmTone` class split into global state + functions (`fm_wr()` / `fm_render()`)
- Audio: 6 separate waveform tables (`wave_sin[]` etc.) -> merged single array `fm_waves[384]`, shift-based lookup `(wave_idx << 6) | idx`
- Waveforms: 6 types (sin/clipsin/rect/tri/saw/abssin) fully preserved
- Frequency table: PROGMEM `tone_freq[80]` (MIDI 36-115) -> code segment `fm_note_freq[104]` (MIDI 24-127, C1-C9)
- Voice count: 5 voice -> 16 voice, operator count 10 -> 32
- Envelope: `envelope_cnt[16]` table fully preserved, ADSR logic identical
- Feedback: `fb=7 -> fb=8` correction -> standard `>> fb` (0-7), original approach too hacky
- Removed MIDI parsing (Note On/Off/Program Change), replaced with register direct-write mode
- Removed poly/mono mode switching, voice queue, velocity mapping
- Removed SysEx tone editing (`sysEx.cpp` / `deftone.h`)
- Removed hardware init (AVR Timer PWM), replaced with ISR callback `fm_render()`
- Added: global tone template mechanism (reg 0x00-0x09), Note On auto-applies tone

### 8.4 WT Wavetable — Reference: ArduinoUno WaveMemorySyns (Open Source)

- **Original author**: Keiji Katahira (ArduinoUno_wavetable_synthesis, WaveMemorySyns)
- **Original project**: `D:\working\vscode-projects\Reference_Project\STC-MCU\extracted\ArduinoUno_wavetable_synthesis-master\WaveMemorySyns\`
- **Original scale**: ~709 lines (`.ino` + `memtone.cpp` + `envtone.cpp` + headers), C++ class architecture
- **Original**: 4 ch, ATmega328P, 20MHz, runtime-writable waveform table (WaveMemoryEditor)

**Porting changes (C++ class -> C251 pure C, writable RAM -> fixed code segment)**:
- C++ -> pure C: `MemTone` class split into global state + functions (`wt_wr()` / `wt_render()`)
- Waveforms: original runtime-writable RAM table -> 14 fixed 128-entry waveforms in code segment (1792 bytes), not runtime-modifiable
- Waveform count: original 1 writable table -> 14 preset waveforms (sq12/sq25/pulse50/sq75/sin/clipsin/abssin/halfsin/qsin/altsin/althalfsin/tri/saw/gb_dmg)
- Frequency table: PROGMEM -> code segment `wt_note_freq[104]` (MIDI C1-C9)
- Envelope: `envtone.cpp` ADSR independent object -> inline round-robin tick (same architecture as FM)
- Removed MIDI parsing, Echo effect (`USE_ECHO`)
- Removed runtime waveform editing (WaveMemoryEditor / `set_value()`)
- Removed SysEx interface (`sysex.cpp`)
- Added: waveform length switching (32/64/128), tone template mechanism

### 8.5 Gigatron — Ported from Denjhang_Music_Player (Own Project)

- **Original author**: Denjhang
- **Original project**: `D:\working\vscode-projects\YM2163-Midi\Denjhang_Music_Player_v16\src\windows\gigatron\gigatron_emu.c` + `gigatron_emu.h`
- **Original scale**: ~287 lines (`.c`), C, Windows WinMM audio callback architecture
- **Original**: 4ch, 44100Hz, 32-bit float output, floating-point RatioCounter sample rate conversion, selectable 4/6/8/12/16-bit audio depth, DC offset removal, dual waveform table + original table, oscilloscope

**Porting changes (Windows audio -> embedded ISR callback)**:
- Removed RatioCounter floating-point sample rate conversion (`RC_SET_RATIO` / `RC_STEP`), replaced with fixed 8820Hz (renders every 2 ticks)
- Removed 521 scanline x 59.98Hz Gigatron frame sync mechanism
- Removed dual waveform table (customWaveTable + soundTable), kept single 256-byte waveform table
- Removed bit depth selection (4/6/8/12/16-bit), fixed s16 output
- Removed DC offset removal (dc_alpha filter)
- Removed volume_scale floating-point scaling
- Removed oscilloscope (scope) functionality
- Removed `GigatronState` struct, replaced with `static` global variables
- Removed `srand(time(NULL))` random seed, replaced with fixed seed `r = 0x12345678` (deterministic, embedded needs no random variation)
- fnumH: original `key *= 4` -> ported `step = key * 44 / 101` (adapted for 17640Hz sample rate)
- Core algorithm identical: `idx = (osc>>7) & 0xFC ^ wavX`, `val = sound[idx] + wavA`, clamp 0-63
