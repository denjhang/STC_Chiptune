/* gigatron.c - Gigatron TTL 4ch 波形合成 (STC32G C251)
 * 移植自 Denjhang_Music_Player gigatron_emu.c
 * 核心: 4ch x 16-bit 相位累加器, 256 字节共享波形表, 8-bit DAC
 * 上位机直接写 fnumL/fnumH, 支持滑音/颤音
 */
#include "STC32G.H"
#include "gigatron.h"

/* 波形表: 256 字节, 可自定义 */
static u8 gt_sound[256];

/* 通道状态 */
static struct {
    u16 osc;   /* 相位累加器 */
    u16 key;   /* 原始 fnum */
    u16 step;  /* 预计算步进 = key * 44 / 101 */
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

    if (addr < 0x04) {
        /* ch0-3 fnumL: key = (key & 0xFF80) | (dat & 0x7F) */
        ch = addr;
        gt_ch[ch].key = (gt_ch[ch].key & 0xFF80) | (dat & 0x7F);
        if (gt_ch[ch].key) gt_active |= (1 << ch);
    } else if (addr < 0x08) {
        /* ch0-3 fnumH: key = (key & 0x7F) | (dat << 7), 预计算 step */
        ch = addr - 4;
        gt_ch[ch].key = (gt_ch[ch].key & 0x7F) | ((u16)(dat & 0x7F) << 7);
        gt_ch[ch].step = (u16)((u32)gt_ch[ch].key * 44 / 101);
        if (gt_ch[ch].key) {
            gt_ch[ch].osc = 0;
            gt_active |= (1 << ch);
        }
    } else if (addr < 0x0C) {
        /* ch0-3 wavX */
        gt_ch[addr - 8].wavX = dat;
    } else if (addr < 0x10) {
        /* ch0-3 wavA */
        gt_ch[addr - 0x0C].wavA = (s8)dat;
    } else if (addr < 0x14) {
        /* 0x10-0x13: ch0-3 note off (key=0) */
        ch = addr - 0x10;
        gt_ch[ch].key = 0;
        gt_ch[ch].step = 0;
        gt_active &= ~(1 << ch);
    } else {
        /* 0x14-0xFF: 波形表写入 */
        gt_sound[addr] = dat;
    }
}

s16 gt_render(void) {
    u8 idx;
    s16 samp, val;

    samp = 3;

    /* ch0 */
    if (gt_active & 0x01) {
        gt_ch[0].osc += gt_ch[0].step;
        idx = (u8)(gt_ch[0].osc >> 7) & 0xFC ^ gt_ch[0].wavX;
        val = (s16)(u8)gt_sound[idx] + gt_ch[0].wavA;
        if (val & 0x80) val = 63; else val &= 0x3F;
        samp += val;
    }
    /* ch1 */
    if (gt_active & 0x02) {
        gt_ch[1].osc += gt_ch[1].step;
        idx = (u8)(gt_ch[1].osc >> 7) & 0xFC ^ gt_ch[1].wavX;
        val = (s16)(u8)gt_sound[idx] + gt_ch[1].wavA;
        if (val & 0x80) val = 63; else val &= 0x3F;
        samp += val;
    }
    /* ch2 */
    if (gt_active & 0x04) {
        gt_ch[2].osc += gt_ch[2].step;
        idx = (u8)(gt_ch[2].osc >> 7) & 0xFC ^ gt_ch[2].wavX;
        val = (s16)(u8)gt_sound[idx] + gt_ch[2].wavA;
        if (val & 0x80) val = 63; else val &= 0x3F;
        samp += val;
    }
    /* ch3 */
    if (gt_active & 0x08) {
        gt_ch[3].osc += gt_ch[3].step;
        idx = (u8)(gt_ch[3].osc >> 7) & 0xFC ^ gt_ch[3].wavX;
        val = (s16)(u8)gt_sound[idx] + gt_ch[3].wavA;
        if (val & 0x80) val = 63; else val &= 0x3F;
        samp += val;
    }

    return samp - 131;
}

u8 gt_channel_mask(void) {
    return gt_active;
}
