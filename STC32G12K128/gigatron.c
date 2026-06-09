/* gigatron.c - Gigatron TTL 4ch 波形合成 (STC32G C251)
 * 移植自 Denjhang_Music_Player gigatron_emu.c
 * 核心: 4ch x 16-bit 相位累加器, 256 字节共享波形表, 8-bit DAC
 * 内置 FNUM 频率表, 上位机发 note index 直接查表
 */
#include "STC32G.H"
#include "gigatron.h"

/* FNUM 频率表: 95 条目 (8 八度 × 12 音 - 1), note 0=C1 .. 94=B8 */
static const u16 code gt_fnum[GT_NOTES] = {
    0x0045, 0x0049, 0x004d, 0x0052, 0x0056, 0x005c, 0x0061, 0x0067, 0x006d, 0x0073, 0x007a, 0x0081,
    0x0089, 0x0091, 0x009a, 0x00a3, 0x00ad, 0x00b7, 0x00c2, 0x00ce, 0x00da, 0x00e7, 0x00f4, 0x0103,
    0x0112, 0x0123, 0x0134, 0x0146, 0x015a, 0x016e, 0x0184, 0x019b, 0x01b3, 0x01cd, 0x01e9, 0x0206,
    0x0225, 0x0245, 0x0268, 0x028c, 0x02b3, 0x02dc, 0x0308, 0x0336, 0x0367, 0x039b, 0x03d2, 0x040c,
    0x0449, 0x048b, 0x04d0, 0x0519, 0x0567, 0x05b9, 0x0610, 0x066c, 0x06ce, 0x0735, 0x07a3, 0x0817,
    0x0893, 0x0915, 0x099f, 0x0a32, 0x0acd, 0x0b72, 0x0c20, 0x0cd8, 0x0d9c, 0x0e6b, 0x0f46, 0x102f,
    0x1125, 0x122a, 0x133f, 0x1464, 0x159a, 0x16e3, 0x183f, 0x19b1, 0x1b38, 0x1cd6, 0x1e8d, 0x205e,
    0x224b, 0x2455, 0x267e, 0x28c8, 0x2b34, 0x2dc6, 0x307f, 0x3361, 0x366f, 0x39ac, 0x3d1a
};

/* 波形表: 256 字节, 可自定义 */
static u8 gt_sound[256];

/* 通道状态 */
static struct {
    u16 osc;   /* 相位累加器 */
    u16 key;   /* 频率步进 */
    u8  wavX;  /* 波形 XOR */
    s8  wavA;  /* 幅度偏移 */
} gt_ch[GT_CHANS];

/* 活跃标志 (key != 0) */
static u8 gt_active;

void gt_init(void) {
    u8 i;
    u32 r = 0x12345678;
    /* 生成波形表: 每 4 项为一组 (noise/tri/pulse/saw) */
    for (i = 0; i < 64; i++) {
        r += r * 56465321UL + 456156321UL;
        gt_sound[i * 4 + 0] = (u8)(r & 63);
        gt_sound[i * 4 + 1] = (u8)(i < 32 ? 2 * i : (127 - 2 * i));
        gt_sound[i * 4 + 2] = (u8)(i < 32 ? 0 : 63);
        gt_sound[i * 4 + 3] = (u8)i;
    }
    for (i = 0; i < GT_CHANS; i++) {
        gt_ch[i].osc = 0;
        gt_ch[i].key = 0;
        gt_ch[i].wavX = 0;
        gt_ch[i].wavA = 0;
    }
    gt_active = 0;
}

void gt_wr(u8 addr, u8 dat) {
    u8 ch;
    u16 fnum;

    if (addr < 0x04) {
        /* ch0-3 note on/off: dat=note(0-94), 0xFF=off */
        ch = addr;
        if (dat == 0xFF || dat >= GT_NOTES) {
            gt_ch[ch].key = 0;
            gt_active &= ~(1 << ch);
        } else {
            fnum = gt_fnum[dat];
            gt_ch[ch].key = fnum * 4;
            gt_ch[ch].osc = 0;
            gt_active |= (1 << ch);
        }
    } else if (addr < 0x08) {
        /* 保留 */
    } else if (addr < 0x0C) {
        /* ch0-3 wavX */
        gt_ch[addr - 8].wavX = dat;
    } else if (addr < 0x10) {
        /* ch0-3 wavA */
        gt_ch[addr - 0x0C].wavA = (s8)dat;
    } else {
        /* 0x10-0xFF: 波形表写入 */
        gt_sound[addr] = dat;
    }
}

s16 gt_render(void) {
    u8 n, idx;
    s16 samp;
    s32 val;

    samp = 3;
    for (n = 0; n < GT_CHANS; n++) {
        if (!(gt_active & (1 << n))) continue;
        gt_ch[n].osc += gt_ch[n].key;

        idx = (u8)((gt_ch[n].osc >> 7) & 0xFC);
        idx ^= gt_ch[n].wavX;

        val = (s32)(u8)gt_sound[idx] + gt_ch[n].wavA;
        if (val & 0x80) val = 63;
        else val &= 0x3F;
        samp += (s16)val;
    }

    return samp - 131;
}

u8 gt_channel_mask(void) {
    return gt_active;
}
