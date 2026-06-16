/* brr.c - BRR 4ch 旋律采样 (filter=0, SNES DSP 风格, STC32G C251)
 *
 * 算法 (GME Spc_Dsp.cpp bit-exact, filter=0):
 *   scale = header >> 4
 *   rs = brr_right_shift[scale]
 *   ls = brr_left_shift[scale]
 *   nyb = signed 4-bit (从 byte pair 提取, 4 个/block)
 *   s = ((nib >> rs) << ls), sign-extend, s *= 2
 *
 * filter=0 无状态, loop 回绕直接重置即可
 *
 * 频率步进: 8.8 fixed-point (和 adpcm 一致)
 *   per tick: now_step += step; advance = now_step >> 8
 *
 * 包络: ADSR (和 adpcm 共用 pcm_env_cnt 表)
 */

#include "STC32G.H"
#include "brr.h"
#include "brr_rom.h"

/* ========== GME shifts table (code 段) ========== */
static const u8 code brr_right_shift[16] = {
    13,12,12,12,12,12,12,12,12,12,12,12,13,16,16,16
};
static const u8 code brr_left_shift[16] = {
     0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,11,11,11
};

/* ========== 半音步进表 (8.8 fixed-point) ==========
 * brr_semi_up[k]   = 256 * 2^(k/12),   k=0..11
 * brr_semi_dn[k]   = 256 / 2^(k/12)
 */
static const u16 code brr_semi_up[12] = {
    256, 271, 287, 304, 322, 341, 362, 383, 406, 430, 455, 482
};
static const u16 code brr_semi_dn[12] = {
    256, 242, 228, 216, 203, 192, 181, 171, 161, 152, 144, 136
};

/* ========== 包络速度表 (和 adpcm.c 一致) ========== */
static const u8 code brr_env_cnt[16] = {
    0, 1, 2, 3, 4, 5, 7, 10, 13, 20, 29, 43, 64, 86, 128, 255
};

/* ========== 音色模板 ========== */
static struct {
    u8 atk, decy, sul, sus, rel;
} brr_tone;

/* ========== 通道状态 ========== */
static struct {
    u8  active;
    u8  inst_idx;
    u8  vol;
    u16 block_idx;     /* 当前 BRR block 索引 */
    u8  sample_in_block; /* 0-15 */
    u8  cache_scale;   /* 当前 block 的 scale */
    u8  cache_b0;      /* 缓存 4 个 byte pair (8 bytes) */
    u8  cache_b1;
    u8  cache_b2;
    u8  cache_b3;
    u8  cache_b4;
    u8  cache_b5;
    u8  cache_b6;
    u8  cache_b7;
    u8  block_cached;  /* 1=cache 有效 */
    u16 step;          /* 8.8 fixed-point 步长 */
    u16 now_step;
    s16 s_prev;        /* 线性插值 */
    s16 s_cur;
    /* ADSR */
    u8  env_state;
    u8  env_cnt;
    u8  loop_sustain;  /* 1=持续乐器 sustain 保持, 0=弹拨 sustain 衰减 */
    u8  atk, decy, sul, sus, rel;
    u8  level;
    u8  env_step;
} brr_ch[BRR_CHANS];

static u8 brr_active_mask;
static u8 brr_wait_cnt;

/* ========== 从 ROM 读 1 个采样 ==========
 * 不缓存整个 block, 每次按 byte pair 提取
 */
static s16 brr_decode_one(u8 inst_idx, u16 block_idx, u8 sample_idx) {
    const u8 code *p;
    u8 header, scale, rs, ls, bp, sp;
    u16 nybbles;
    s16 raw, s;

    p = brr_inst[inst_idx].blocks + (u16)(block_idx * 9);
    header = p[0];
    scale = header >> 4;
    if (scale > 15) scale = 15;
    rs = brr_right_shift[scale];
    ls = brr_left_shift[scale];
    bp = sample_idx >> 2;       /* 0-3: 哪个 byte pair */
    sp = sample_idx & 0x03;     /* 0-3: pair 内第几个 nybble */
    {
        u16 b0v, b1v;
        b0v = p[1 + bp*2];
        b1v = p[2 + bp*2];
        nybbles = (b0v << 8) | b1v;
    }
    /* GME 方式: 左移 sp*4 位把目标 nybble 推到 bit15-12, 取高4位符号扩展 */
    nybbles <<= (sp << 2);
    /* nybbles 高4位 = signed nibble (bit15-12) */
    raw = (s16)nybbles;         /* 符号扩展 */
    raw >>= rs;
    s = (s16)(((u16)raw) << ls);
    s <<= 1;   /* *2 */
    if (s > 32767) s = 32767;
    if (s < -32768) s = -32768;
    return s;
}

/* ========== advance 采样指针 (考虑 loop) ========== */
static void brr_advance(u8 ch) {
    const brr_inst_t code *inst;
    u16 blk;

    inst = &brr_inst[brr_ch[ch].inst_idx];
    blk = brr_ch[ch].block_idx;

    brr_ch[ch].sample_in_block++;
    if (brr_ch[ch].sample_in_block >= 16) {
        brr_ch[ch].sample_in_block = 0;
        blk++;
        if (blk >= inst->n_blocks) {
            blk = inst->loop_block;
        }
        brr_ch[ch].block_idx = blk;
        brr_ch[ch].block_cached = 0;
    }
}

/* ========== ADSR 包络 tick (和 adpcm 一致) ========== */
static void brr_env_tick(u8 ch) {
    u8 cnt, step, lvl;

    cnt = brr_ch[ch].env_cnt;
    step = brr_ch[ch].env_step;
    if (cnt >= step) {
        brr_ch[ch].env_cnt = cnt - step;
        return;
    }
    brr_ch[ch].env_cnt = 250;
    lvl = brr_ch[ch].level;

    switch (brr_ch[ch].env_state) {
    case 1: /* attack */
        lvl++;
        if (lvl >= 31) {
            brr_ch[ch].env_state = 2;
            brr_ch[ch].env_step = brr_ch[ch].decy;
        }
        brr_ch[ch].level = lvl;
        break;
    case 2: /* decay */
        if (lvl > 0) lvl--;
        brr_ch[ch].level = lvl;
        if (lvl <= brr_ch[ch].sul) {
            brr_ch[ch].env_state = 3;
            brr_ch[ch].env_step = brr_ch[ch].sus;
        }
        break;
    case 3: /* sustain: 继续衰减到 0, 速度由 sus 控制 */
        if (lvl > 0) lvl--;
        brr_ch[ch].level = lvl;
        if (lvl == 0) goto env_kill;
        break;
    case 4: /* release */
        if (lvl > 0) lvl--;
        brr_ch[ch].level = lvl;
        if (lvl == 0) goto env_kill;
        break;
    }
    return;
env_kill:
    brr_ch[ch].step = 0;
    brr_ch[ch].active = 0;
    brr_active_mask &= ~(1 << ch);
}

/* ========== 公开函数 ========== */

void brr_init(void) {
    u8 i;

    brr_tone.atk  = 14;
    brr_tone.decy = 9;
    brr_tone.sul  = 13;
    brr_tone.sus  = 3;
    brr_tone.rel  = 7;

    for (i = 0; i < BRR_CHANS; i++) {
        brr_ch[i].active = 0;
        brr_ch[i].inst_idx = 0;
        brr_ch[i].vol = 24;
        brr_ch[i].block_idx = 0;
        brr_ch[i].sample_in_block = 0;
        brr_ch[i].block_cached = 0;
        brr_ch[i].step = 0;
        brr_ch[i].now_step = 0;
        brr_ch[i].s_prev = 0;
        brr_ch[i].s_cur = 0;
        brr_ch[i].env_state = 0;
        brr_ch[i].env_cnt = 0;
        brr_ch[i].level = 0;
        brr_ch[i].env_step = 0;
        brr_ch[i].atk  = brr_tone.atk;
        brr_ch[i].decy = brr_tone.decy;
        brr_ch[i].sul  = brr_tone.sul;
        brr_ch[i].sus  = brr_tone.sus;
        brr_ch[i].rel  = brr_tone.rel;
    }
    brr_active_mask = 0;
    brr_wait_cnt = 0;
}

s16 brr_render(void) {
    u8 ch, step_cnt;
    s16 total = 0;
    s16 out, frac;
    u8 vol;

    brr_wait_cnt++;
    brr_wait_cnt &= 0x03;

    for (ch = 0; ch < BRR_CHANS; ch++) {
        if (!brr_ch[ch].active) continue;

        /* ADSR: 每 4 tick 更新一次 */
        if (brr_ch[ch].env_state && (brr_wait_cnt == 0)) {
            brr_env_tick(ch);
        }

        brr_ch[ch].now_step += brr_ch[ch].step;
        if (brr_ch[ch].now_step >= 0x0100) {
            step_cnt = brr_ch[ch].now_step >> 8;
            brr_ch[ch].now_step &= 0x00FF;
            do {
                brr_ch[ch].s_prev = brr_ch[ch].s_cur;
                brr_ch[ch].s_cur = brr_decode_one(brr_ch[ch].inst_idx,
                                                  brr_ch[ch].block_idx,
                                                  brr_ch[ch].sample_in_block);
                brr_advance(ch);
            } while (--step_cnt);
        }
        frac = brr_ch[ch].now_step;
        if (frac > 0 && brr_ch[ch].step < 0x0100) {
            out = brr_ch[ch].s_prev + (s16)(((long)(brr_ch[ch].s_cur - brr_ch[ch].s_prev) * (long)frac) >> 8);
        } else {
            out = brr_ch[ch].s_cur;
        }

        vol = brr_ch[ch].vol;
        if (brr_ch[ch].env_state) {
            out >>= 8;
            total += (s16)((long)out * brr_ch[ch].level >> 5);
        } else {
            out >>= 8;
            total += (s16)((long)out * vol >> 5);
        }
    }

    return total;
}

void brr_wr(u8 addr, u8 dat) {
    u8 ch;
    const brr_inst_t code *inst;
    s8 diff;
    u8 oct, r;
    u16 ratio;

    if (addr <= 0x03) {
        /* note on: ch0-3, dat = 0-13 乐器 */
        ch = addr;
        if (dat >= BRR_INST_COUNT) return;
        brr_ch[ch].inst_idx = dat;
        brr_ch[ch].block_idx = 0;
        brr_ch[ch].sample_in_block = 0;
        brr_ch[ch].block_cached = 0;
        brr_ch[ch].now_step = 0;
        brr_ch[ch].s_prev = 0;
        brr_ch[ch].s_cur = 0;
        brr_ch[ch].atk  = brr_tone.atk;
        brr_ch[ch].decy = brr_tone.decy;
        brr_ch[ch].sul  = brr_tone.sul;
        brr_ch[ch].sus  = brr_tone.sus;
        brr_ch[ch].rel  = brr_tone.rel;
        brr_ch[ch].env_cnt = 250;
        /* 所有乐器统一完整 ADSR, sustain 保持 (loop_sustain=1) */
        brr_ch[ch].loop_sustain = 1;
        brr_ch[ch].env_state = 1;
        brr_ch[ch].level = 0;
        brr_ch[ch].env_step = brr_ch[ch].atk;
        brr_ch[ch].active = 1;
        brr_active_mask |= (1 << ch);

    } else if (addr >= 0x04 && addr <= 0x07) {
        /* note off */
        ch = addr - 0x04;
        if (brr_ch[ch].env_state) {
            brr_ch[ch].env_state = 4;
            brr_ch[ch].env_step = brr_ch[ch].rel;
        } else {
            brr_ch[ch].active = 0;
            brr_active_mask &= ~(1 << ch);
        }

    } else if (addr >= 0x08 && addr <= 0x0B) {
        /* volume */
        ch = addr - 0x08;
        brr_ch[ch].vol = dat & 0x1F;

    } else if (addr >= 0x0C && addr <= 0x0F) {
        /* midi note: 根据 inst native_midi 计算半音差, 查表得 8.8 step */
        ch = addr - 0x0C;
        inst = &brr_inst[brr_ch[ch].inst_idx];
        diff = (s8)dat - (s8)inst->native_midi;
        if (diff >= 0) {
            oct = (u8)diff / 12;
            r   = (u8)diff % 12;
            ratio = brr_semi_up[r];
            brr_ch[ch].step = ratio << oct;
        } else {
            oct = (u8)(-diff) / 12;
            r   = (u8)(-diff) % 12;
            ratio = brr_semi_dn[r];
            brr_ch[ch].step = ratio >> oct;
        }

    } else if (addr >= 0x10 && addr <= 0x13) {
        /* step hi override */
        ch = addr - 0x10;
        brr_ch[ch].step = ((u16)dat << 8) | (brr_ch[ch].step & 0x00FF);

    } else if (addr >= 0x14 && addr <= 0x17) {
        /* step lo override */
        ch = addr - 0x14;
        brr_ch[ch].step = (brr_ch[ch].step & 0xFF00) | (u16)dat;

    } else if (addr == 0x18) {
        /* atk | decy */
        brr_tone.atk  = brr_env_cnt[(dat >> 4) & 0x0F];
        brr_tone.decy = brr_env_cnt[dat & 0x0F];

    } else if (addr == 0x19) {
        /* sus_level(高4) | sus_speed(低4) */
        /* sul: 0=衰减到静音, 15=满电平(level=30), 线性映射 sul*2 */
        brr_tone.sul = ((dat >> 4) & 0x0F) * 2;
        brr_tone.sus = brr_env_cnt[dat & 0x0F];

    } else if (addr == 0x1A) {
        /* rel */
        brr_tone.rel = brr_env_cnt[dat & 0x0F];
    }
}

u8 brr_channel_mask(void) {
    u8 mask = 0, i;
    for (i = 0; i < BRR_CHANS; i++) {
        if (brr_ch[i].active) mask |= (1 << i);
    }
    return mask;
}
