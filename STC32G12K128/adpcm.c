/* adpcm.c - ADPCM 6ch 鼓声 + SF2 采样旋律乐器 (STC32G C251)
 * jedi_table 查表解码, 12-bit acc, 49 step
 *
 * 鼓声 (0xC0, data 0-5):
 *   note on: data = drum index 0-5, 播放到 end 自动停止
 *
 * SF2 旋律采样 (0xC0, data 16-25):
 *   note on: data = 16 + inst_idx(0-9), 下一条 0x33 发 midi note
 *   有 loop, ADSR 包络, pitch shift
 *   和 WT 共用音色模板 (0x10-0x14)
 *
 * 寄存器 (复用 WT 的 0xC0 前缀):
 *   0x15-0x1A: ch0-5 note on  (data: 0-5=鼓, 16+=SF2乐器)
 *   0x1B-0x20: ch0-5 note off
 *   0x21-0x26: ch0-5 volume   (0-31)
 *   0x27-0x2C: ch0-5 step hi
 *   0x2D-0x32: ch0-5 step lo
 *   0x33: midi note (紧跟 SF2 note on 之后, 24-95)
 */

#include "STC32G.H"
#include "adpcm.h"
#include "fmopn_2608rom.h"
#include "sf2_rom.h"

/* ========== jedi_table (49 x 16 = 784 s16) ========== */
static const s16 code jedi_table[784] = {
     2,     6,    10,    14,    18,    22,    26,    30,    -2,    -6,   -10,   -14,   -18,   -22,   -26,   -30,
     2,     6,    10,    14,    19,    23,    27,    31,    -2,    -6,   -10,   -14,   -19,   -23,   -27,   -31,
     2,     7,    11,    16,    21,    26,    30,    35,    -2,    -7,   -11,   -16,   -21,   -26,   -30,  -35,
     2,     7,    13,    18,    23,    28,    34,    39,    -2,    -7,   -13,   -18,   -23,   -28,  -34,  -39,
     2,     8,    14,    20,    25,    31,    37,    43,    -2,    -8,   -14,   -20,   -25,  -31,  -37,  -43,
     3,     9,    15,    21,    28,    34,    40,    46,    -3,    -9,   -15,   -21,   -28,  -34,  -40,  -46,
     3,    10,    17,    24,    31,    38,    45,    52,    -3,   -10,   -17,  -24,  -31,  -38,  -45,  -52,
     3,    11,    19,    27,    34,    42,    50,    58,    -3,   -11,  -19,   -27,  -34,  -42,  -50,  -58,
     4,    12,    21,    29,    38,    46,    55,    63,    -4,   -12,  -21,  -29,  -38,  -46,  -55,  -63,
     4,    13,    23,    32,    41,    50,    60,    69,    -4,   -13,  -23,   -32,  -41,  -50,  -60,  -69,
     5,    15,    25,    35,    46,    56,    66,    76,    -5,   -15,   -25,   -35,   -46,  -56,  -66,  -76,
     5,    16,    28,    39,    50,    61,    73,    84,    -5,   -16,  -28,  -39,  -50,  -61,  -73,  -84,
     6,    18,    31,    43,    56,    68,    81,    93,    -6,   -18,  -31,  -43,  -56,  -68,  -81,  -93,
     6,    20,    34,    48,    61,    75,    89,   103,    -6,   -20,  -34,  -48,  -61,  -75,  -89,  -103,
     7,    22,    37,    52,    67,    82,    97,   112,    -7,   -22,  -37,  -52,  -67,  -82,  -97,  -112,
     8,    24,    41,    57,    74,    90,   107,   123,    -8,   -24,  -41,  -57,  -74,  -90,  -107,  -123,
     9,    27,    45,    63,    82,   100,   118,   136,    -9,   -27,  -45,  -63,  -82,  -100,  -118,  -136,
    10,    30,    50,    70,    90,   110,   130,   150,   -10,  -30,  -50,  -70,  -90,  -110,  -130,  -150,
    11,    33,    55,    77,    99,   121,   143,   165,   -11,  -33,  -55,  -77,  -99,  -121,  -143,  -165,
    12,    36,    60,    84,   109,   133,   157,   181,   -12,  -36,  -60,  -84,  -109,  -133,  -157,  -181,
    13,    40,    66,    93,   120,   147,   173,   200,   -13,  -40,  -66,  -93,  -120,  -147,  -173,  -200,
    14,    44,    73,   103,   132,   162,   191,   221,   -14,  -44,  -73,  -103,  -132,  -162,  -191,  -221,
    16,    48,    81,   113,   146,   178,   211,   243,   -16,  -48,  -81,  -113,  -146,  -178,  -211,  -243,
    17,    53,    89,   125,   160,   196,   232,   268,   -17,  -53,  -89,  -125,  -160,  -196,  -232,  -268,
    19,    58,    98,   137,   176,   215,   255,   294,   -19,  -58,  -98,  -137,  -176,  -215,  -255,  -294,
    21,    64,   108,   151,   194,   237,   281,   324,   -21,  -64,  -108,  -151,  -194,  -237,  -281,  -324,
    23,    71,   118,   166,   213,   261,   308,   356,   -23,  -71,  -118,  -166,  -213,  -261,  -308,  -356,
    26,    78,   130,   182,   235,   287,   339,   391,   -26,  -78,  -130,  -182,  -235,  -287,  -339,  -391,
    28,    86,   143,   201,   258,   316,   373,   431,   -28,  -86,  -143,  -201,  -258,  -316,  -373,  -431,
    31,    94,   158,   221,   284,   347,   411,   474,   -31,  -94,  -158,  -221,  -284,  -347,  -411,  -474,
    34,   104,   174,   244,   313,   383,   453,   523,   -34,  -104,  -174,  -244,  -313,  -383,  -453,  -523,
    38,   115,   191,   268,   345,   422,   498,   575,   -38,  -115,  -191,  -268,  -345,  -422,  -498,  -575,
    42,   126,   210,   294,   379,   463,   547,   631,   -42,  -126,  -210,  -294,  -379,  -463,  -547,  -631,
    46,   139,   231,   324,   417,   510,   602,   695,   -46,  -139,  -231,  -324,  -417,  -510,  -602,  -695,
    51,   153,   255,   357,   459,   561,   663,   765,   -51,  -153,  -255,  -357,  -459,  -561,  -663,  -765,
    56,   168,   280,   392,   505,   617,   729,   841,   -56,  -168,  -280,  -392,  -505,  -617,  -729,  -841,
    61,   185,   308,   432,   555,   679,   802,   926,   -61,  -185,  -308,  -432,  -555,  -679,  -802,  -926,
    68,   204,   340,   476,   612,   748,   884,  1020,   -68,  -204,  -340,  -476,  -612,  -748,  -884, -1020,
    74,   224,   373,   523,   672,   822,   971,   1121,   -74,  -224,  -373,  -523,  -672,  -822,  -971, -1121,
    82,   246,   411,   575,   740,   904,   1069,  1233,   -82,  -246,  -411,  -575,  -740,  -904, -1069, -1233,
    90,   271,   452,   633,   814,   995,   1176,  1357,   -90,  -271,  -452,  -633,  -814,  -995, -1176, -1357,
    99,   298,   497,   696,   895,  1094,  1293,  1492,   -99,  -298,  -497,  -696,  -895, -1094, -1293, -1492,
   109,   328,   547,   766,   985,  1204,  1423,   1642,  -109,  -328,  -547,  -766,  -985, -1204, -1423, -1642,
   120,   361,   601,   842,  1083,  1324,  1564,  1805,  -120,  -361,  -601,  -842, -1083, -1324, -1564, -1805,
   132,   397,   662,   927,  1192,  1457,  1722,  1987,  -132,  -397,  -662,  -927, -1192, -1457, -1722, -1987,
   145,   437,   728,   1020,  1311,  1603,  1894,   2186,  -145,  -437,  -728, -1020, -1311, -1603, -1894, -2186,
   160,   480,   801,   1121,  1442,  1762,  2083,  2403,  -160,  -480,  -801, -1121, -1442, -1762, -2083, -2403,
   176,   529,   881,   1234,  1587,  1940,   2292,  2645,  -176,  -529,  -881, -1234, -1587, -1940, -2292, -2645,
   194,   582,   970,   1358,   1746,  2134,   2522,   2910,  -194,  -582,  -970, -1358, -1746, -2134, -2522, -2910,
};

static const s16 code adpcm_step_inc[8] = {
    -16, -16, -16, -16, 32, 80, 112, 144
};

/* ========== 鼓声 ROM 地址表 ========== */
static const u16 code drum_start[6] = {
    0x0000, 0x01AB, 0x040D, 0x0F20, 0x108E, 0x12F0
};

static const u16 code drum_len[6] = {
    854, 1219, 5670, 732, 1219, 244
};

static const u16 code drum_step[6] = {
    0x0100, 0x0100, 0x0080, 0x0100, 0x0080, 0x0080
};

/* ========== 包络速度表 (和 wt.c 一致) ========== */
static const u8 code pcm_env_cnt[16] = {
    0, 1, 2, 3, 4, 5, 7, 10, 13, 20, 29, 43, 64, 86, 128, 255
};

/* ========== 音色模板 (和 WT 共用 0x10-0x14 设置) ========== */
static struct {
    u8 atk, decy, sul, sus, rel;
} pcm_tone;

/* ========== 通道状态 ========== */
static struct {
    u16 addr;       /* nibble address */
    u16 end_addr;   /* end nibble address (drum: 停止; sf2: 不用, 用 loop) */
    u16 loop_addr;  /* loop start nibble address (sf2 only) */
    u16 loop_end;   /* loop end nibble address (sf2 only) */
    u8  cache;      /* cached ROM byte */
    s16 acc;        /* 12-bit accumulator (sign extended) */
    s16 adpcm_step; /* ADPCM step index (0..768) */
    u8  vol;
    u16 step;       /* 8.8 fixed point 步长 */
    u16 now_step;   /* 累加器 */
    s16 s_prev;     /* 上一个解码采样 (插值用) */
    s16 s_cur;      /* 当前解码采样 (插值用) */
    u8  active;
    u8  is_sf2;     /* 1=SF2旋律, 0=鼓声 */
    /* ADSR (sf2 旋律用, 和 wt_ch 一致) */
    u8  env_state;
    u8  env_cnt;
    u8  atk, decy, sul, sus, rel;
    u8  level;
    u8  env_step;
    u8  inst_idx;   /* SF2 乐器索引 */
} pcm_ch[PCM_CHANS];

static u8 pcm_active_mask;
static u8 pcm_wait_cnt;

/* SF2 note on 等待 midi note */
static u8 pcm_pending_ch;  /* 哪个通道在等 midi note */

/* ========== 解码一个 sample ========== */
static s16 pcm_decode_sample(u8 ch) {
    u8 nib;
    u16 rom_idx, step;
    s16 delta;

    if (!pcm_ch[ch].active) return 0;

    if (pcm_ch[ch].addr & 1) {
        nib = pcm_ch[ch].cache & 0x0F;
    } else {
        if (pcm_ch[ch].is_sf2) {
            rom_idx = pcm_ch[ch].addr >> 1;
            pcm_ch[ch].cache = SF2_ROM[rom_idx];
        } else {
            rom_idx = pcm_ch[ch].addr >> 1;
            pcm_ch[ch].cache = YM2608_ADPCM_ROM[rom_idx];
        }
        nib = (pcm_ch[ch].cache >> 4) & 0x0F;
    }
    pcm_ch[ch].addr++;

    /* SF2: loop 回绕, 重置 acc/step 防漂移 */
    if (pcm_ch[ch].is_sf2 && pcm_ch[ch].addr > pcm_ch[ch].loop_end) {
        pcm_ch[ch].addr = pcm_ch[ch].loop_addr;
        pcm_ch[ch].acc = sf2_loop_acc[pcm_ch[ch].inst_idx];
        pcm_ch[ch].adpcm_step = sf2_loop_step[pcm_ch[ch].inst_idx];
    }

    /* 鼓声: 播放到 end 停止 (SF2 有 loop 不走这里) */
    if (pcm_ch[ch].addr >= pcm_ch[ch].end_addr) {
        pcm_ch[ch].active = 0;
        pcm_active_mask &= ~(1 << ch);
        return 0;
    }

    step = pcm_ch[ch].adpcm_step;
    delta = jedi_table[step + nib];
    pcm_ch[ch].acc += delta;
    pcm_ch[ch].acc &= 0x0FFF;

    if (pcm_ch[ch].acc & 0x0800) {
        pcm_ch[ch].acc |= 0xF000;
    } else {
        pcm_ch[ch].acc &= 0x0FFF;
    }

    pcm_ch[ch].adpcm_step += adpcm_step_inc[nib & 7];
    if (pcm_ch[ch].adpcm_step < 0) pcm_ch[ch].adpcm_step = 0;
    if (pcm_ch[ch].adpcm_step > 768) pcm_ch[ch].adpcm_step = 768;

    return pcm_ch[ch].acc;
}

/* ========== ADSR 包络 tick (和 wt_env_tick 一致) ========== */
static void pcm_env_tick(u8 ch) {
    u8 cnt, step, lvl;

    cnt = pcm_ch[ch].env_cnt;
    step = pcm_ch[ch].env_step;
    if (cnt >= step) {
        pcm_ch[ch].env_cnt = cnt - step;
        return;
    }

    pcm_ch[ch].env_cnt = 250;
    lvl = pcm_ch[ch].level;

    switch (pcm_ch[ch].env_state) {
    case 1: /* attack */
        lvl++;
        if (lvl >= 31) {
            pcm_ch[ch].env_state = 2;
            pcm_ch[ch].env_step = pcm_ch[ch].decy;
        }
        pcm_ch[ch].level = lvl;
        break;
    case 2: /* decay */
        if (lvl > 0) lvl--;
        pcm_ch[ch].level = lvl;
        if (lvl == pcm_ch[ch].sul) {
            pcm_ch[ch].env_state = 3;
            pcm_ch[ch].env_step = pcm_ch[ch].sus;
        }
        break;
    case 3: /* sustain */
        if (lvl > 0) lvl--;
        pcm_ch[ch].level = lvl;
        if (lvl == 0) {
            pcm_ch[ch].step = 0;
            pcm_ch[ch].active = 0;
            pcm_active_mask &= ~(1 << ch);
        }
        break;
    case 4: /* release */
        if (lvl > 0) lvl--;
        pcm_ch[ch].level = lvl;
        if (lvl == 0) {
            pcm_ch[ch].step = 0;
            pcm_ch[ch].active = 0;
            pcm_active_mask &= ~(1 << ch);
        }
        break;
    }
}

/* ========== 公开函数 ========== */

void pcm_init(void) {
    u8 i;

    pcm_tone.atk = 14;
    pcm_tone.decy = 9;
    pcm_tone.sul = 13;
    pcm_tone.sus = 3;
    pcm_tone.rel = 7;

    for (i = 0; i < PCM_CHANS; i++) {
        pcm_ch[i].addr = 0;
        pcm_ch[i].end_addr = 0;
        pcm_ch[i].loop_addr = 0;
        pcm_ch[i].loop_end = 0;
        pcm_ch[i].cache = 0;
        pcm_ch[i].acc = 0;
        pcm_ch[i].adpcm_step = 0;
        pcm_ch[i].vol = 31;
        pcm_ch[i].step = drum_step[i];
        pcm_ch[i].now_step = 0;
        pcm_ch[i].s_prev = 0;
        pcm_ch[i].s_cur = 0;
        pcm_ch[i].active = 0;
        pcm_ch[i].is_sf2 = 0;
        pcm_ch[i].env_state = 0;
        pcm_ch[i].env_cnt = 0;
        pcm_ch[i].level = 0;
        pcm_ch[i].env_step = 0;
        pcm_ch[i].inst_idx = 0;
    }
    pcm_active_mask = 0;
    pcm_wait_cnt = 0;
    pcm_pending_ch = 0xFF;
}

void pcm_wr(u8 addr, u8 dat) {
    u8 ch, drum, inst;

    if (addr >= 0x15 && addr <= 0x1A) {
        ch = addr - 0x15;

        if (dat >= 16 && dat < 16 + SF2_INST_COUNT) {
            /* SF2 采样乐器: 播放 + loop */
            inst = dat - 16;
            pcm_ch[ch].is_sf2 = 1;
            pcm_ch[ch].inst_idx = inst;
            pcm_ch[ch].addr = sf2_start[inst];
            pcm_ch[ch].end_addr = sf2_start[inst] + sf2_nib_count[inst];
            pcm_ch[ch].loop_addr = sf2_start[inst] + sf2_loop_start[inst];
            pcm_ch[ch].loop_end = sf2_start[inst] + sf2_loop_end[inst];
            pcm_ch[ch].acc = 0;
            pcm_ch[ch].adpcm_step = 0;
            pcm_ch[ch].cache = 0;
            pcm_ch[ch].now_step = 0;
            pcm_ch[ch].s_prev = 0;
            pcm_ch[ch].s_cur = 0;
            pcm_ch[ch].active = 1;
            pcm_ch[ch].env_state = 3;  /* SF2 直接 sustain, 等 0x33 调参数 */
            pcm_ch[ch].level = 31;
            pcm_active_mask |= (1 << ch);
            pcm_pending_ch = ch;

        } else {
            /* 鼓声 */
            drum = dat % 6;
            pcm_ch[ch].is_sf2 = 0;
            pcm_ch[ch].addr = drum_start[drum] << 1;
            pcm_ch[ch].end_addr = pcm_ch[ch].addr + drum_len[drum];
            pcm_ch[ch].step = drum_step[drum];
            pcm_ch[ch].acc = 0;
            pcm_ch[ch].adpcm_step = 0;
            pcm_ch[ch].cache = 0;
            pcm_ch[ch].now_step = 0;
            pcm_ch[ch].s_prev = 0;
            pcm_ch[ch].s_cur = 0;
            pcm_ch[ch].active = 1;
            pcm_ch[ch].env_state = 0;
            pcm_ch[ch].level = 31;
            pcm_active_mask |= (1 << ch);
        }

    } else if (addr == 0x33) {
        /* SF2 midi note: step 已由 0x27/0x2D 写入, 这里只启动 ADSR */
        if (pcm_pending_ch < PCM_CHANS) {
            ch = pcm_pending_ch;
            {
                /* 应用 DSR: level=31 不缩放, 保持采样原始音量 */
                pcm_ch[ch].decy = pcm_tone.decy;
                pcm_ch[ch].sul  = pcm_tone.sul;
                pcm_ch[ch].sus  = pcm_tone.sus;
                pcm_ch[ch].rel  = pcm_tone.rel;
                pcm_ch[ch].env_state = 3;  /* 直接 sustain */
                pcm_ch[ch].env_cnt = 250;
                pcm_ch[ch].level = 31;
                pcm_ch[ch].env_step = pcm_ch[ch].sus;

                pcm_ch[ch].active = 1;
                pcm_active_mask |= (1 << ch);
            }
            pcm_pending_ch = 0xFF;
        }

    } else if (addr >= 0x1B && addr <= 0x20) {
        ch = addr - 0x1B;
        {
            if (pcm_ch[ch].env_state) {
                pcm_ch[ch].env_state = 4;  /* release */
                pcm_ch[ch].env_step = pcm_ch[ch].rel;
            } else {
                pcm_ch[ch].active = 0;
                pcm_active_mask &= ~(1 << ch);
            }
        }

    } else if (addr >= 0x21 && addr <= 0x26) {
        ch = addr - 0x21;
        pcm_ch[ch].vol = dat & 0x1F;

    } else if (addr >= 0x27 && addr <= 0x2C) {
        ch = addr - 0x27;
        pcm_ch[ch].step = ((u16)dat << 8) | (pcm_ch[ch].step & 0x00FF);

    } else if (addr >= 0x2D && addr <= 0x32) {
        ch = addr - 0x2D;
        pcm_ch[ch].step = (pcm_ch[ch].step & 0xFF00) | (u16)dat;

    } else if (addr == 0x10) {
        /* ADSR atk|dec (和 WT 共用) */
        pcm_tone.atk = pcm_env_cnt[(dat >> 4) & 0x0F];
        pcm_tone.decy = pcm_env_cnt[dat & 0x0F];

    } else if (addr == 0x11) {
        pcm_tone.sul = (dat >> 4) & 0x0F;
        pcm_tone.sul = pcm_tone.sul == 15 ? 0 : 31 - pcm_tone.sul * 2;
        pcm_tone.sus = pcm_env_cnt[dat & 0x0F];

    } else if (addr == 0x12) {
        pcm_tone.rel = pcm_env_cnt[dat & 0x0F];
    }
}

s16 pcm_render(void) {
    u8 ch, step_cnt;
    s16 total = 0;
    s16 out, frac;
    u8 vol;

    pcm_wait_cnt++;
    pcm_wait_cnt &= 0x03;

    for (ch = 0; ch < PCM_CHANS; ch++) {
        if (!pcm_ch[ch].active) continue;

        /* ADSR: 每 4 tick 更新一次包络 */
        if (pcm_ch[ch].env_state && (pcm_wait_cnt == 0)) {
            pcm_env_tick(ch);
        }

        pcm_ch[ch].now_step += pcm_ch[ch].step;
        if (pcm_ch[ch].now_step >= 0x0100) {
            step_cnt = pcm_ch[ch].now_step >> 8;
            pcm_ch[ch].now_step &= 0x00FF;
            do {
                pcm_ch[ch].s_prev = pcm_ch[ch].s_cur;
                pcm_ch[ch].s_cur = pcm_decode_sample(ch);
            } while (--step_cnt);
        }
        frac = pcm_ch[ch].now_step;
        if (frac > 0 && pcm_ch[ch].step < 0x0100) {
            out = pcm_ch[ch].s_prev + (s16)(((long)(pcm_ch[ch].s_cur - pcm_ch[ch].s_prev) * (long)frac) >> 8);
        } else {
            out = pcm_ch[ch].s_cur;
        }

        vol = pcm_ch[ch].vol;
        if (pcm_ch[ch].env_state) {
            out >>= 5;
            total += (s16)((long)out * vol * pcm_ch[ch].level >> 10);
        } else {
            out >>= 5;
            total += (s16)((long)out * vol >> 5);
        }
    }

    return total;
}

u8 pcm_channel_mask(void) {
    u8 mask = 0, i;
    for (i = 0; i < PCM_CHANS; i++) {
        if (pcm_ch[i].active) mask |= (1 << i);
    }
    return mask;
}
