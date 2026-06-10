/* adpcm.c - ADPCM 打击乐器 6ch (STC32G C251)
 * YM2608 内置 8KB ROM, 6 鼓: BD/SD/HH/TC/TM/RS
 * jedi_table 查表解码, 12-bit acc, 49 step
 *
 * 寄存器 (复用 WT 的 0xC0 前缀):
 *   0x15-0x1A: ch0-5 note on  (data = drum 0-5)
 *   0x1B-0x20: ch0-5 note off
 *   0x21-0x26: ch0-5 volume   (0-31)
 */

#include "STC32G.H"
#include "adpcm.h"
#include "fmopn_2608rom.h"

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
     4,    13,    23,    32,    41,    50,    60,    69,    -4,   -13,  -23,  -32,  -41,  -50,  -60,  -69,
     5,    15,    25,    35,    46,    56,    66,    76,    -5,   -15,  -25,  -35,  -46,  -56,  -66,  -76,
     5,    16,    28,    39,    50,    61,    73,    84,    -5,   -16,  -28,  -39,  -50,  -61,  -73,  -84,
     6,    18,    31,    43,    56,    68,    81,    93,    -6,   -18,  -31,  -43,  -56,  -68,  -81,  -93,
     6,    20,    34,    48,    61,    75,    89,   103,    -6,   -20,  -34,  -48,  -61,  -75,  -89,  -103,
     7,    22,    37,    52,    67,    82,    97,   112,    -7,   -22,  -37,  -52,  -67,  -82,  -97,  -112,
     8,    24,    41,    57,    74,    90,   107,   123,    -8,   -24,  -41,  -57,  -74,  -90,  -107,  -123,
     9,    27,    45,    63,    82,   100,   118,   136,    -9,   -27,  -45,  -63,   -82,  -100,  -118,  -136,
    10,    30,    50,    70,    90,   110,   130,   150,   -10,  -30,  -50,  -70,   -90,  -110,  -130,  -150,
    11,    33,    55,    77,    99,   121,   143,   165,   -11,  -33,  -55,  -77,   -99,  -121,  -143,  -165,
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
    74,   224,   373,   523,   672,   822,   971,  1121,   -74,  -224,  -373,  -523,  -672,  -822,  -971, -1121,
    82,   246,   411,   575,   740,   904,   1069,  1233,   -82,  -246,  -411,  -575,  -740,  -904, -1069, -1233,
    90,   271,   452,   633,   814,   995,  1176,  1357,   -90,  -271,  -452,  -633,  -814,  -995, -1176, -1357,
    99,   298,   497,   696,   895,  1094,  1293,  1492,   -99,  -298,  -497,  -696,  -895, -1094, -1293, -1492,
   109,   328,   547,   766,   985,  1204,  1423,  1642,  -109,  -328,  -547,  -766,  -985, -1204, -1423, -1642,
   120,   361,   601,   842,  1083,  1324,  1564,  1805,  -120,  -361,  -601,  -842, -1083, -1324, -1564, -1805,
   132,   397,   662,   927,  1192,  1457,  1722,  1987,  -132,  -397,  -662,  -927, -1192, -1457, -1722, -1987,
   145,   437,   728,   1020,  1311,  1603,  1894,  2186,  -145,  -437,  -728, -1020, -1311, -1603, -1894, -2186,
   160,   480,   801,   1121,  1442,  1762,  2083,  2403,  -160,  -480,  -801, -1121, -1442, -1762, -2083, -2403,
   176,   529,   881,   1234,  1587,  1940,  2292,  2645,  -176,  -529,  -881, -1234, -1587, -1940, -2292, -2645,
   194,   582,   970,  1358,  1746,  2134,  2522,  2910,  -194,  -582,  -970, -1358, -1746, -2134, -2522, -2910,
};

/* ========== step_inc ========== */
static const s16 code adpcm_step_inc[8] = {
    -16, -16, -16, -16, 32, 80, 112, 144
};

/* ========== ROM 地址表 ========== */
static const u16 code drum_start[6] = {
    0x0000,  /* BD */
    0x01AB,  /* SD */
    0x040D,  /* TC */
    0x0F20,  /* HH */
    0x108E,  /* TM */
    0x12F0   /* RS */
};

/* 每鼓的 nibble 数 */
static const u16 code drum_len[6] = {
    854,     /* BD */
    1219,    /* SD */
    5670,    /* TC */
    732,     /* HH */
    1219,    /* TM */
    244      /* RS */
};

/* 预设步长 (8.8 fixed point): 0x100=原速, 0x080=半速 */
static const u16 code drum_step[6] = {
    0x0100,  /* BD: 原速 17640Hz */
    0x0100,  /* SD: 原速 17640Hz */
    0x0080,  /* TC: 半速 8820Hz */
    0x0100,  /* HH: 原速 17640Hz */
    0x0080,  /* TM: 半速 8820Hz */
    0x0080   /* RS: 半速 8820Hz */
};

/* 通道状态 */
static struct {
    u16 addr;      /* nibble address */
    u16 end_addr;  /* end nibble address */
    u8  cache;     /* cached ROM byte */
    s16 acc;       /* 12-bit accumulator (sign extended) */
    s16 adpcm_step;/* ADPCM step index (0..768) */
    u8  vol;
    u16 step;      /* 8.8 fixed point 步长 */
    u16 now_step;  /* 累加器 */
    s16 s_prev;    /* 上一个解码采样 (插值用) */
    s16 s_cur;     /* 当前解码采样 (插值用) */
    u8  active;
} pcm_ch[PCM_CHANS];

static u8 pcm_active_mask;

/* ========== 解码一个 sample (返回 acc, 不带音量) ========== */
static s16 pcm_decode_sample(u8 ch) {
    u8 nib;
    u16 rom_idx, step;
    s16 delta;

    if (!pcm_ch[ch].active) return 0;

    /* 读取 nibble */
    if (pcm_ch[ch].addr & 1) {
        nib = pcm_ch[ch].cache & 0x0F;
    } else {
        rom_idx = pcm_ch[ch].addr >> 1;
        pcm_ch[ch].cache = YM2608_ADPCM_ROM[rom_idx];
        nib = (pcm_ch[ch].cache >> 4) & 0x0F;
    }
    pcm_ch[ch].addr++;

    /* 结束检测 */
    if (pcm_ch[ch].addr >= pcm_ch[ch].end_addr) {
        pcm_ch[ch].active = 0;
        pcm_active_mask &= ~(1 << ch);
        return 0;
    }

    /* 查 jedi_table: adpcm_step + nib */
    step = pcm_ch[ch].adpcm_step;
    delta = jedi_table[step + nib];
    pcm_ch[ch].acc += delta;
    pcm_ch[ch].acc &= 0x0FFF;

    /* 12-bit 符号扩展 */
    if (pcm_ch[ch].acc & 0x0800) {
        pcm_ch[ch].acc |= 0xF000;
    } else {
        pcm_ch[ch].acc &= 0x0FFF;
    }

    /* 更新 step */
    pcm_ch[ch].adpcm_step += adpcm_step_inc[nib & 7];
    if (pcm_ch[ch].adpcm_step < 0) pcm_ch[ch].adpcm_step = 0;
    if (pcm_ch[ch].adpcm_step > 768) pcm_ch[ch].adpcm_step = 768;

    return pcm_ch[ch].acc;
}

/* ========== 公开函数 ========== */

void pcm_init(void) {
    u8 i;
    for (i = 0; i < PCM_CHANS; i++) {
        pcm_ch[i].addr = 0;
        pcm_ch[i].end_addr = 0;
        pcm_ch[i].cache = 0;
        pcm_ch[i].acc = 0;
        pcm_ch[i].adpcm_step = 0;
        pcm_ch[i].vol = 31;
        pcm_ch[i].step = drum_step[i];
        pcm_ch[i].now_step = 0;
        pcm_ch[i].s_prev = 0;
        pcm_ch[i].s_cur = 0;
        pcm_ch[i].active = 0;
    }
    pcm_active_mask = 0;
}

void pcm_wr(u8 addr, u8 dat) {
    u8 ch, drum;

    if (addr >= 0x15 && addr <= 0x1A) {
        ch = addr - 0x15;
        drum = dat % 6;

        pcm_ch[ch].addr = drum_start[drum] << 1;
        pcm_ch[ch].end_addr = pcm_ch[ch].addr + drum_len[drum];
        pcm_ch[ch].acc = 0;
        pcm_ch[ch].adpcm_step = 0;
        pcm_ch[ch].cache = 0;
        pcm_ch[ch].now_step = 0;
        pcm_ch[ch].s_prev = 0;
        pcm_ch[ch].s_cur = 0;
        pcm_ch[ch].active = 1;
        pcm_active_mask |= (1 << ch);
        /* 不重置 step, 保留 set_step 设的值 */

    } else if (addr >= 0x1B && addr <= 0x20) {
        ch = addr - 0x1B;
        pcm_ch[ch].active = 0;
        pcm_active_mask &= ~(1 << ch);

    } else if (addr >= 0x21 && addr <= 0x26) {
        ch = addr - 0x21;
        pcm_ch[ch].vol = dat & 0x1F;
    } else if (addr >= 0x27 && addr <= 0x2C) {
        /* step 高字节: step = (dat << 8) | low_byte */
        ch = addr - 0x27;
        pcm_ch[ch].step = ((u16)dat << 8) | (pcm_ch[ch].step & 0x00FF);
    } else if (addr >= 0x2D && addr <= 0x32) {
        /* step 低字节: step = (high_byte << 8) | dat */
        ch = addr - 0x2D;
        pcm_ch[ch].step = (pcm_ch[ch].step & 0xFF00) | (u16)dat;
    }
}

s16 pcm_render(void) {
    u8 ch;
    u8 step_cnt;
    s16 total = 0;
    s16 out, frac;

    for (ch = 0; ch < PCM_CHANS; ch++) {
        if (!pcm_ch[ch].active) continue;
        pcm_ch[ch].now_step += pcm_ch[ch].step;
        if (pcm_ch[ch].now_step >= 0x0100) {
            step_cnt = pcm_ch[ch].now_step >> 8;
            pcm_ch[ch].now_step &= 0x00FF;
            do {
                pcm_ch[ch].s_prev = pcm_ch[ch].s_cur;
                pcm_ch[ch].s_cur = pcm_decode_sample(ch);
            } while (--step_cnt);
        }
        /* 线性插值 (ymdeltat.c ElSemi style), 仅 step < 0x100 时有效 */
        frac = pcm_ch[ch].now_step;
        if (frac > 0 && pcm_ch[ch].step < 0x0100) {
            out = pcm_ch[ch].s_prev + (pcm_ch[ch].s_cur - pcm_ch[ch].s_prev) * frac / 256;
        } else {
            out = pcm_ch[ch].s_cur;
        }
        total += (s16)((long)out * pcm_ch[ch].vol >> 10);
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
