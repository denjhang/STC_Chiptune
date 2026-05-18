;--------------------------------------------------------
; File Created by SDCC : free open source ISO C Compiler 
; Version 4.4.0 #14620 (MINGW32)
;--------------------------------------------------------
	.module scc
	.optsdcc -mmcs51 --model-small
	
;--------------------------------------------------------
; Public variables in this module
;--------------------------------------------------------
	.globl _scc_write_PARM_3
	.globl _scc_write_PARM_2
	.globl _memset
	.globl _scc_init_PARM_2
	.globl _scc_init
	.globl _scc_reset
	.globl _scc_write
	.globl _scc_render
;--------------------------------------------------------
; special function registers
;--------------------------------------------------------
	.area RSEG    (ABS,DATA)
	.org 0x0000
;--------------------------------------------------------
; special function bits
;--------------------------------------------------------
	.area RSEG    (ABS,DATA)
	.org 0x0000
;--------------------------------------------------------
; overlayable register banks
;--------------------------------------------------------
	.area REG_BANK_0	(REL,OVR,DATA)
	.ds 8
;--------------------------------------------------------
; internal ram data
;--------------------------------------------------------
	.area DSEG    (DATA)
_scc_init_PARM_2:
	.ds 4
_scc_reset_s_10000_32:
	.ds 3
_scc_render_s_10000_50:
	.ds 3
_scc_render_mix_10000_51:
	.ds 2
_scc_render_i_10000_51:
	.ds 1
_scc_render_c_30000_53:
	.ds 3
_scc_render_step_40000_54:
	.ds 4
_scc_render_sloc0_1_0:
	.ds 3
_scc_render_sloc1_1_0:
	.ds 3
_scc_render_sloc2_1_0:
	.ds 4
;--------------------------------------------------------
; overlayable items in internal ram
;--------------------------------------------------------
	.area	OSEG    (OVR,DATA)
_scc_write_PARM_2:
	.ds 1
_scc_write_PARM_3:
	.ds 1
_scc_write_s_10000_36:
	.ds 3
;--------------------------------------------------------
; indirectly addressable internal ram data
;--------------------------------------------------------
	.area ISEG    (DATA)
;--------------------------------------------------------
; absolute internal ram data
;--------------------------------------------------------
	.area IABS    (ABS,DATA)
	.area IABS    (ABS,DATA)
;--------------------------------------------------------
; bit data
;--------------------------------------------------------
	.area BSEG    (BIT)
;--------------------------------------------------------
; paged external ram data
;--------------------------------------------------------
	.area PSEG    (PAG,XDATA)
;--------------------------------------------------------
; uninitialized external ram data
;--------------------------------------------------------
	.area XSEG    (XDATA)
;--------------------------------------------------------
; absolute external ram data
;--------------------------------------------------------
	.area XABS    (ABS,XDATA)
;--------------------------------------------------------
; initialized external ram data
;--------------------------------------------------------
	.area XISEG   (XDATA)
	.area HOME    (CODE)
	.area GSINIT0 (CODE)
	.area GSINIT1 (CODE)
	.area GSINIT2 (CODE)
	.area GSINIT3 (CODE)
	.area GSINIT4 (CODE)
	.area GSINIT5 (CODE)
	.area GSINIT  (CODE)
	.area GSFINAL (CODE)
	.area CSEG    (CODE)
;--------------------------------------------------------
; global & static initialisations
;--------------------------------------------------------
	.area HOME    (CODE)
	.area GSINIT  (CODE)
	.area GSFINAL (CODE)
	.area GSINIT  (CODE)
;--------------------------------------------------------
; Home
;--------------------------------------------------------
	.area HOME    (CODE)
	.area HOME    (CODE)
;--------------------------------------------------------
; code
;--------------------------------------------------------
	.area CSEG    (CODE)
;------------------------------------------------------------
;Allocation info for local variables in function 'scc_init'
;------------------------------------------------------------
;clock_hz                  Allocated with name '_scc_init_PARM_2'
;s                         Allocated to registers r5 r6 r7 
;tmp                       Allocated to registers r1 r2 r3 r4 
;------------------------------------------------------------
;	src\scc.c:4: void scc_init(scc_state_t *s, uint32_t clock_hz) {
;	-----------------------------------------
;	 function scc_init
;	-----------------------------------------
_scc_init:
	ar7 = 0x07
	ar6 = 0x06
	ar5 = 0x05
	ar4 = 0x04
	ar3 = 0x03
	ar2 = 0x02
	ar1 = 0x01
	ar0 = 0x00
	mov	r5, dpl
	mov	r6, dph
	mov	r7, b
;	src\scc.c:6: memset(s, 0, sizeof(*s));
	mov	ar2,r5
	mov	ar3,r6
	mov	ar4,r7
	mov	_memset_PARM_2,#0x00
	mov	_memset_PARM_3,#0xd3
	mov	(_memset_PARM_3 + 1),#0x00
	mov	dpl, r2
	mov	dph, r3
	mov	b, r4
	push	ar7
	push	ar6
	push	ar5
	lcall	_memset
	pop	ar5
	pop	ar6
	pop	ar7
;	src\scc.c:7: s->rate = 44100;
	mov	a,#0xc8
	add	a, r5
	mov	r2,a
	clr	a
	addc	a, r6
	mov	r3,a
	mov	ar4,r7
	mov	dpl,r2
	mov	dph,r3
	mov	b,r4
	mov	a,#0x44
	lcall	__gptrput
	inc	dptr
	mov	a,#0xac
	lcall	__gptrput
	inc	dptr
	clr	a
	lcall	__gptrput
	inc	dptr
	lcall	__gptrput
;	src\scc.c:9: tmp = clock_hz >> 1;
	mov	a,(_scc_init_PARM_2 + 3)
	clr	c
	rrc	a
	mov	a,(_scc_init_PARM_2 + 2)
	rrc	a
	mov	a,(_scc_init_PARM_2 + 1)
	rrc	a
	mov	r2,a
	mov	a,_scc_init_PARM_2
	rrc	a
	mov	r1,a
;	src\scc.c:10: s->clock_factor = tmp << (SCC_FREQ_BITS + 1);
	mov	a,#0xcc
	add	a, r5
	mov	r5,a
	clr	a
	addc	a, r6
	mov	r6,a
	mov	ar3,r1
	mov	a,r2
	xch	a,r3
	add	a,acc
	xch	a,r3
	rlc	a
	mov	r4,a
	mov	r1,#0x00
	mov	r2,#0x00
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	mov	a,r1
	lcall	__gptrput
	inc	dptr
	mov	a,r2
	lcall	__gptrput
	inc	dptr
	mov	a,r3
	lcall	__gptrput
	inc	dptr
	mov	a,r4
;	src\scc.c:11: }
	ljmp	__gptrput
;------------------------------------------------------------
;Allocation info for local variables in function 'scc_reset'
;------------------------------------------------------------
;s                         Allocated with name '_scc_reset_s_10000_32'
;i                         Allocated to registers r4 
;------------------------------------------------------------
;	src\scc.c:13: void scc_reset(scc_state_t *s) {
;	-----------------------------------------
;	 function scc_reset
;	-----------------------------------------
_scc_reset:
	mov	_scc_reset_s_10000_32,dpl
	mov	(_scc_reset_s_10000_32 + 1),dph
	mov	(_scc_reset_s_10000_32 + 2),b
;	src\scc.c:15: for (i = 0; i < SCC_CHANS; i++) {
	mov	r4,#0x00
00102$:
;	src\scc.c:16: s->ch[i].counter = 0;
	mov	a,r4
	mov	b,#0x28
	mul	ab
	mov	r3,a
	add	a, _scc_reset_s_10000_32
	mov	r0,a
	clr	a
	addc	a, (_scc_reset_s_10000_32 + 1)
	mov	r1,a
	mov	r2,(_scc_reset_s_10000_32 + 2)
	mov	dpl,r0
	mov	dph,r1
	mov	b,r2
	clr	a
	lcall	__gptrput
	inc	dptr
	lcall	__gptrput
	inc	dptr
	lcall	__gptrput
	inc	dptr
	lcall	__gptrput
;	src\scc.c:17: s->ch[i].frequency = 0;
	mov	a,r3
	add	a, _scc_reset_s_10000_32
	mov	r1,a
	clr	a
	addc	a, (_scc_reset_s_10000_32 + 1)
	mov	r2,a
	mov	r3,(_scc_reset_s_10000_32 + 2)
	mov	a,#0x04
	add	a, r1
	mov	r0,a
	clr	a
	addc	a, r2
	mov	r6,a
	mov	ar7,r3
	mov	dpl,r0
	mov	dph,r6
	mov	b,r7
	clr	a
	lcall	__gptrput
	inc	dptr
	lcall	__gptrput
;	src\scc.c:18: s->ch[i].volume = 0;
	mov	a,#0x06
	add	a, r1
	mov	r5,a
	clr	a
	addc	a, r2
	mov	r6,a
	mov	ar7,r3
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	clr	a
	lcall	__gptrput
;	src\scc.c:19: s->ch[i].key = 0;
	mov	a,#0x07
	add	a, r1
	mov	r5,a
	clr	a
	addc	a, r2
	mov	r6,a
	mov	ar7,r3
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	clr	a
	lcall	__gptrput
;	src\scc.c:20: memset(s->ch[i].waveram, 0, SCC_WAVELEN);
	mov	a,#0x08
	add	a, r1
	mov	r1,a
	clr	a
	addc	a, r2
	mov	r2,a
	mov	_memset_PARM_2,#0x00
	mov	_memset_PARM_3,#0x20
	mov	(_memset_PARM_3 + 1),#0x00
	mov	dpl, r1
	mov	dph, r2
	mov	b, r3
	push	ar4
	lcall	_memset
	pop	ar4
;	src\scc.c:15: for (i = 0; i < SCC_CHANS; i++) {
	inc	r4
	cjne	r4,#0x05,00119$
00119$:
	jnc	00120$
	ljmp	00102$
00120$:
;	src\scc.c:22: s->test = 0;
	mov	a,#0xd1
	add	a, _scc_reset_s_10000_32
	mov	r5,a
	clr	a
	addc	a, (_scc_reset_s_10000_32 + 1)
	mov	r6,a
	mov	r7,(_scc_reset_s_10000_32 + 2)
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	clr	a
	lcall	__gptrput
;	src\scc.c:23: s->cur_reg = 0;
	mov	a,#0xd2
	add	a, _scc_reset_s_10000_32
	mov	r5,a
	clr	a
	addc	a, (_scc_reset_s_10000_32 + 1)
	mov	r6,a
	mov	r7,(_scc_reset_s_10000_32 + 2)
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	clr	a
;	src\scc.c:24: }
	ljmp	__gptrput
;------------------------------------------------------------
;Allocation info for local variables in function 'scc_write'
;------------------------------------------------------------
;port                      Allocated with name '_scc_write_PARM_2'
;data                      Allocated with name '_scc_write_PARM_3'
;s                         Allocated with name '_scc_write_s_10000_36'
;offset                    Allocated to registers r7 
;ch                        Allocated to registers r7 
;------------------------------------------------------------
;	src\scc.c:26: void scc_write(scc_state_t *s, uint8_t port, uint8_t data) {
;	-----------------------------------------
;	 function scc_write
;	-----------------------------------------
_scc_write:
	mov	_scc_write_s_10000_36,dpl
	mov	(_scc_write_s_10000_36 + 1),dph
	mov	(_scc_write_s_10000_36 + 2),b
;	src\scc.c:28: if (port & 1) {
	mov	a,_scc_write_PARM_2
	mov	r4,a
	jb	acc.0,00221$
	ljmp	00130$
00221$:
;	src\scc.c:29: switch (port >> 1) {
	mov	a,r4
	clr	c
	rrc	a
	mov  r4,a
	add	a,#0xff - 0x05
	jnc	00222$
	ret
00222$:
	mov	a,r4
	add	a,r4
	add	a,r4
	mov	dptr,#00223$
	jmp	@a+dptr
00223$:
	ljmp	00102$
	ljmp	00111$
	ljmp	00122$
	ljmp	00146$
	ljmp	00102$
	ljmp	00127$
;	src\scc.c:31: case 0x04: {
00102$:
;	src\scc.c:32: offset = s->cur_reg;
	mov	a,#0xd2
	add	a, _scc_write_s_10000_36
	mov	r2,a
	clr	a
	addc	a, (_scc_write_s_10000_36 + 1)
	mov	r3,a
	mov	r4,(_scc_write_s_10000_36 + 2)
	mov	dpl,r2
	mov	dph,r3
	mov	b,r4
	lcall	__gptrget
	mov	r4,a
;	src\scc.c:33: if (s->test & 0x40) return;
	mov	a,#0xd1
	add	a, _scc_write_s_10000_36
	mov	r1,a
	clr	a
	addc	a, (_scc_write_s_10000_36 + 1)
	mov	r2,a
	mov	r3,(_scc_write_s_10000_36 + 2)
	mov	dpl,r1
	mov	dph,r2
	mov	b,r3
	lcall	__gptrget
	jnb	acc.6,00104$
	ret
00104$:
;	src\scc.c:34: if (!s->mode_plus) {
	mov	a,#0xd0
	add	a, _scc_write_s_10000_36
	mov	r1,a
	clr	a
	addc	a, (_scc_write_s_10000_36 + 1)
	mov	r2,a
	mov	r3,(_scc_write_s_10000_36 + 2)
	mov	dpl,r1
	mov	dph,r2
	mov	b,r3
	lcall	__gptrget
	jz	00225$
	ljmp	00109$
00225$:
;	src\scc.c:35: if (offset >= 0x60) {
	cjne	r4,#0x60,00226$
00226$:
	jc	00106$
;	src\scc.c:36: s->ch[3].waveram[offset & 0x1f] = (int8_t)data;
	mov	a,#0x78
	add	a, _scc_write_s_10000_36
	mov	r1,a
	clr	a
	addc	a, (_scc_write_s_10000_36 + 1)
	mov	r2,a
	mov	r3,(_scc_write_s_10000_36 + 2)
	mov	a,#0x08
	add	a, r1
	mov	r1,a
	clr	a
	addc	a, r2
	mov	r2,a
	mov	ar0,r4
	anl	ar0,#0x1f
	mov	r7,#0x00
	mov	a,r0
	add	a, r1
	mov	r1,a
	mov	a,r7
	addc	a, r2
	mov	r2,a
	mov	r6,_scc_write_PARM_3
	mov	dpl,r1
	mov	dph,r2
	mov	b,r3
	mov	a,r6
	lcall	__gptrput
;	src\scc.c:37: s->ch[4].waveram[offset & 0x1f] = (int8_t)data;
	mov	a,#0xa0
	add	a, _scc_write_s_10000_36
	mov	r2,a
	clr	a
	addc	a, (_scc_write_s_10000_36 + 1)
	mov	r3,a
	mov	r5,(_scc_write_s_10000_36 + 2)
	mov	a,#0x08
	add	a, r2
	mov	r2,a
	clr	a
	addc	a, r3
	mov	r3,a
	mov	a,r0
	add	a, r2
	mov	r2,a
	mov	a,r7
	addc	a, r3
	mov	r3,a
	mov	dpl,r2
	mov	dph,r3
	mov	b,r5
	mov	a,r6
	ljmp	__gptrput
00106$:
;	src\scc.c:39: s->ch[offset >> 5].waveram[offset & 0x1f] = (int8_t)data;
	mov	a,r4
	swap	a
	rr	a
	anl	a,#0x07
	mov	b,#0x28
	mul	ab
	add	a, _scc_write_s_10000_36
	mov	r5,a
	clr	a
	addc	a,(_scc_write_s_10000_36 + 1)
	mov	r6,a
	mov	r7,(_scc_write_s_10000_36 + 2)
	mov	a,#0x08
	add	a, r5
	mov	r5,a
	clr	a
	addc	a, r6
	mov	r6,a
	mov	ar2,r4
	anl	ar2,#0x1f
	mov	r3,#0x00
	mov	a,r2
	add	a, r5
	mov	r5,a
	mov	a,r3
	addc	a, r6
	mov	r6,a
	mov	r3,_scc_write_PARM_3
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	mov	a,r3
	ljmp	__gptrput
00109$:
;	src\scc.c:42: s->ch[offset >> 5].waveram[offset & 0x1f] = (int8_t)data;
	mov	a,r4
	swap	a
	rr	a
	anl	a,#0x07
	mov	b,#0x28
	mul	ab
	add	a, _scc_write_s_10000_36
	mov	r5,a
	clr	a
	addc	a,(_scc_write_s_10000_36 + 1)
	mov	r6,a
	mov	r7,(_scc_write_s_10000_36 + 2)
	mov	a,#0x08
	add	a, r5
	mov	r5,a
	clr	a
	addc	a, r6
	mov	r6,a
	anl	ar4,#0x1f
	mov	r3,#0x00
	mov	a,r4
	add	a, r5
	mov	r5,a
	mov	a,r3
	addc	a, r6
	mov	r6,a
	mov	r4,_scc_write_PARM_3
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	mov	a,r4
;	src\scc.c:44: break;
	ljmp	__gptrput
;	src\scc.c:46: case 0x01: {
00111$:
;	src\scc.c:47: offset = s->cur_reg;
	mov	a,#0xd2
	add	a, _scc_write_s_10000_36
	mov	r5,a
	clr	a
	addc	a, (_scc_write_s_10000_36 + 1)
	mov	r6,a
	mov	r7,(_scc_write_s_10000_36 + 2)
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	lcall	__gptrget
;	src\scc.c:48: ch = offset >> 1;
	mov	r7,a
	clr	c
	rrc	a
	mov	r6,a
;	src\scc.c:49: if (ch < SCC_CHANS) {
	cjne	r6,#0x05,00228$
00228$:
	jc	00229$
	ret
00229$:
;	src\scc.c:50: if (offset & 1)
	mov	a,r7
	jnb	acc.0,00113$
;	src\scc.c:51: s->ch[ch].frequency = (s->ch[ch].frequency & 0x00FF) | ((uint16_t)(data & 0x0F) << 8);
	mov	a,r6
	mov	b,#0x28
	mul	ab
	add	a, _scc_write_s_10000_36
	mov	r4,a
	clr	a
	addc	a,(_scc_write_s_10000_36 + 1)
	mov	r5,a
	mov	r7,(_scc_write_s_10000_36 + 2)
	mov	a,#0x04
	add	a, r4
	mov	r4,a
	clr	a
	addc	a, r5
	mov	r5,a
	mov	dpl,r4
	mov	dph,r5
	mov	b,r7
	lcall	__gptrget
	mov	r2,a
	inc	dptr
	lcall	__gptrget
	mov	r3,#0x00
	mov	r1,_scc_write_PARM_3
	anl	ar1,#0x0f
	mov	ar0,r1
	mov	ar1,r0
	mov	r0,#0x00
	mov	a,r2
	orl	ar0,a
	mov	a,r3
	orl	ar1,a
	mov	dpl,r4
	mov	dph,r5
	mov	b,r7
	mov	a,r0
	lcall	__gptrput
	inc	dptr
	mov	a,r1
	lcall	__gptrput
	sjmp	00114$
00113$:
;	src\scc.c:53: s->ch[ch].frequency = (s->ch[ch].frequency & 0x0F00) | data;
	mov	a,r6
	mov	b,#0x28
	mul	ab
	add	a, _scc_write_s_10000_36
	mov	r4,a
	clr	a
	addc	a,(_scc_write_s_10000_36 + 1)
	mov	r5,a
	mov	r7,(_scc_write_s_10000_36 + 2)
	mov	a,#0x04
	add	a, r4
	mov	r4,a
	clr	a
	addc	a, r5
	mov	r5,a
	mov	dpl,r4
	mov	dph,r5
	mov	b,r7
	lcall	__gptrget
	inc	dptr
	lcall	__gptrget
	mov	r3,a
	mov	r2,#0x00
	anl	ar3,#0x0f
	mov	r0,_scc_write_PARM_3
	mov	r1,#0x00
	mov	a,r0
	orl	ar2,a
	mov	a,r1
	orl	ar3,a
	mov	dpl,r4
	mov	dph,r5
	mov	b,r7
	mov	a,r2
	lcall	__gptrput
	inc	dptr
	mov	a,r3
	lcall	__gptrput
00114$:
;	src\scc.c:54: s->ch[ch].counter &= 0xFFFF0000u;
	mov	a,r6
	mov	b,#0x28
	mul	ab
	mov	r7,a
	add	a, _scc_write_s_10000_36
	mov	r4,a
	clr	a
	addc	a, (_scc_write_s_10000_36 + 1)
	mov	r5,a
	mov	r6,(_scc_write_s_10000_36 + 2)
	mov	dpl,r4
	mov	dph,r5
	mov	b,r6
	lcall	__gptrget
	inc	dptr
	lcall	__gptrget
	inc	dptr
	lcall	__gptrget
	mov	r2,a
	inc	dptr
	lcall	__gptrget
	mov	r3,a
	mov	r0,#0x00
	mov	r1,#0x00
	mov	dpl,r4
	mov	dph,r5
	mov	b,r6
	mov	a,r0
	lcall	__gptrput
	inc	dptr
	mov	a,r1
	lcall	__gptrput
	inc	dptr
	mov	a,r2
	lcall	__gptrput
	inc	dptr
	mov	a,r3
	lcall	__gptrput
;	src\scc.c:55: if (s->test & 0x20)
	mov	a,#0xd1
	add	a, _scc_write_s_10000_36
	mov	r1,a
	clr	a
	addc	a, (_scc_write_s_10000_36 + 1)
	mov	r2,a
	mov	r3,(_scc_write_s_10000_36 + 2)
	mov	dpl,r1
	mov	dph,r2
	mov	b,r3
	lcall	__gptrget
	jnb	acc.5,00118$
;	src\scc.c:56: s->ch[ch].counter = 0xFFFFFFFF;
	mov	dpl,r4
	mov	dph,r5
	mov	b,r6
	mov	a,#0xff
	lcall	__gptrput
	inc	dptr
	lcall	__gptrput
	inc	dptr
	lcall	__gptrput
	inc	dptr
	ljmp	__gptrput
00118$:
;	src\scc.c:57: else if (s->ch[ch].frequency < 9)
	mov	a,r7
	add	a, _scc_write_s_10000_36
	mov	r5,a
	clr	a
	addc	a, (_scc_write_s_10000_36 + 1)
	mov	r6,a
	mov	r7,(_scc_write_s_10000_36 + 2)
	mov	a,#0x04
	add	a, r5
	mov	r2,a
	clr	a
	addc	a, r6
	mov	r3,a
	mov	ar4,r7
	mov	dpl,r2
	mov	dph,r3
	mov	b,r4
	lcall	__gptrget
	mov	r2,a
	inc	dptr
	lcall	__gptrget
	mov	r3,a
	clr	c
	mov	a,r2
	subb	a,#0x09
	mov	a,r3
	subb	a,#0x00
	jc	00232$
	ret
00232$:
;	src\scc.c:58: s->ch[ch].counter |= ((1 << SCC_FREQ_BITS) - 1);
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	mov	a,#0xff
	lcall	__gptrput
	inc	dptr
	lcall	__gptrput
	inc	dptr
	lcall	__gptrput
	inc	dptr
;	src\scc.c:60: break;
	ljmp	__gptrput
;	src\scc.c:62: case 0x02: {
00122$:
;	src\scc.c:63: ch = s->cur_reg & 0x07;
	mov	a,#0xd2
	add	a, _scc_write_s_10000_36
	mov	r5,a
	clr	a
	addc	a, (_scc_write_s_10000_36 + 1)
	mov	r6,a
	mov	r7,(_scc_write_s_10000_36 + 2)
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	lcall	__gptrget
	mov	r5,a
	mov	a,#0x07
	anl	a,r5
	mov	r7,a
;	src\scc.c:64: if (ch < SCC_CHANS)
	cjne	r7,#0x05,00233$
00233$:
	jc	00234$
	ret
00234$:
;	src\scc.c:65: s->ch[ch].volume = data & 0x0F;
	mov	a,r7
	mov	b,#0x28
	mul	ab
	add	a, _scc_write_s_10000_36
	mov	r5,a
	clr	a
	addc	a,(_scc_write_s_10000_36 + 1)
	mov	r6,a
	mov	r7,(_scc_write_s_10000_36 + 2)
	mov	a,#0x06
	add	a, r5
	mov	r5,a
	clr	a
	addc	a, r6
	mov	r6,a
	mov	a,_scc_write_PARM_3
	anl	a,#0x0f
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
;	src\scc.c:66: break;
;	src\scc.c:69: for (ch = 0; ch < SCC_CHANS; ch++)
	ljmp	__gptrput
00146$:
	mov	r7,#0x00
00132$:
;	src\scc.c:70: s->ch[ch].key = (data >> ch) & 1;
	mov	a,r7
	mov	b,#0x28
	mul	ab
	add	a, _scc_write_s_10000_36
	mov	r4,a
	clr	a
	addc	a,(_scc_write_s_10000_36 + 1)
	mov	r5,a
	mov	r6,(_scc_write_s_10000_36 + 2)
	mov	a,#0x07
	add	a, r4
	mov	r4,a
	clr	a
	addc	a, r5
	mov	r5,a
	mov	b,r7
	inc	b
	mov	a,_scc_write_PARM_3
	sjmp	00236$
00235$:
	clr	c
	rrc	a
00236$:
	djnz	b,00235$
	anl	a,#0x01
	mov	dpl,r4
	mov	dph,r5
	mov	b,r6
	lcall	__gptrput
;	src\scc.c:69: for (ch = 0; ch < SCC_CHANS; ch++)
	inc	r7
	cjne	r7,#0x05,00237$
00237$:
	jc	00132$
;	src\scc.c:71: break;
;	src\scc.c:72: case 0x05:
	ret
00127$:
;	src\scc.c:73: s->test = data;
	mov	a,#0xd1
	add	a, _scc_write_s_10000_36
	mov	r5,a
	clr	a
	addc	a, (_scc_write_s_10000_36 + 1)
	mov	r6,a
	mov	r7,(_scc_write_s_10000_36 + 2)
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	mov	a,_scc_write_PARM_3
;	src\scc.c:75: }
	ljmp	__gptrput
00130$:
;	src\scc.c:77: s->cur_reg = data;
	mov	a,#0xd2
	add	a, _scc_write_s_10000_36
	mov	r5,a
	clr	a
	addc	a, (_scc_write_s_10000_36 + 1)
	mov	r6,a
	mov	r7,(_scc_write_s_10000_36 + 2)
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	mov	a,_scc_write_PARM_3
;	src\scc.c:79: }
	ljmp	__gptrput
;------------------------------------------------------------
;Allocation info for local variables in function 'scc_render'
;------------------------------------------------------------
;s                         Allocated with name '_scc_render_s_10000_50'
;mix                       Allocated with name '_scc_render_mix_10000_51'
;i                         Allocated with name '_scc_render_i_10000_51'
;c                         Allocated with name '_scc_render_c_30000_53'
;step                      Allocated with name '_scc_render_step_40000_54'
;offs                      Allocated to registers r4 r5 r6 
;smpl                      Allocated to registers r6 r7 
;sloc0                     Allocated with name '_scc_render_sloc0_1_0'
;sloc1                     Allocated with name '_scc_render_sloc1_1_0'
;sloc2                     Allocated with name '_scc_render_sloc2_1_0'
;------------------------------------------------------------
;	src\scc.c:81: int8_t scc_render(scc_state_t *s) {
;	-----------------------------------------
;	 function scc_render
;	-----------------------------------------
_scc_render:
	mov	_scc_render_s_10000_50,dpl
	mov	(_scc_render_s_10000_50 + 1),dph
	mov	(_scc_render_s_10000_50 + 2),b
;	src\scc.c:82: int16_t mix = 0;
	clr	a
	mov	_scc_render_mix_10000_51,a
	mov	(_scc_render_mix_10000_51 + 1),a
;	src\scc.c:84: for (i = 0; i < SCC_CHANS; i++) {
	mov	a,#0xcc
	add	a, _scc_render_s_10000_50
	mov	_scc_render_sloc1_1_0,a
	clr	a
	addc	a, (_scc_render_s_10000_50 + 1)
	mov	(_scc_render_sloc1_1_0 + 1),a
	mov	(_scc_render_sloc1_1_0 + 2),(_scc_render_s_10000_50 + 2)
	mov	a,#0xc8
	add	a, _scc_render_s_10000_50
	mov	_scc_render_sloc0_1_0,a
	clr	a
	addc	a, (_scc_render_s_10000_50 + 1)
	mov	(_scc_render_sloc0_1_0 + 1),a
	mov	(_scc_render_sloc0_1_0 + 2),(_scc_render_s_10000_50 + 2)
	mov	_scc_render_i_10000_51,#0x00
00110$:
;	src\scc.c:85: scc_channel_t *c = &s->ch[i];
	mov	a,_scc_render_i_10000_51
	mov	b,#0x28
	mul	ab
	add	a, _scc_render_s_10000_50
	mov	_scc_render_c_30000_53,a
	clr	a
	addc	a,(_scc_render_s_10000_50 + 1)
	mov	(_scc_render_c_30000_53 + 1),a
	mov	(_scc_render_c_30000_53 + 2),(_scc_render_s_10000_50 + 2)
;	src\scc.c:86: if (c->frequency > 8) {
	mov	a,#0x04
	add	a, _scc_render_c_30000_53
	mov	r3,a
	clr	a
	addc	a, (_scc_render_c_30000_53 + 1)
	mov	r4,a
	mov	r5,(_scc_render_c_30000_53 + 2)
	mov	dpl,r3
	mov	dph,r4
	mov	b,r5
	lcall	__gptrget
	mov	r3,a
	inc	dptr
	lcall	__gptrget
	mov	r4,a
	clr	c
	mov	a,#0x08
	subb	a,r3
	clr	a
	subb	a,r4
	jc	00157$
	ljmp	00111$
00157$:
;	src\scc.c:91: step = s->clock_factor / ((uint32_t)(c->frequency + 1) * s->rate);
	mov	dpl,_scc_render_sloc1_1_0
	mov	dph,(_scc_render_sloc1_1_0 + 1)
	mov	b,(_scc_render_sloc1_1_0 + 2)
	lcall	__gptrget
	mov	_scc_render_sloc2_1_0,a
	inc	dptr
	lcall	__gptrget
	mov	(_scc_render_sloc2_1_0 + 1),a
	inc	dptr
	lcall	__gptrget
	mov	(_scc_render_sloc2_1_0 + 2),a
	inc	dptr
	lcall	__gptrget
	mov	(_scc_render_sloc2_1_0 + 3),a
	inc	r3
	cjne	r3,#0x00,00158$
	inc	r4
00158$:
	mov	r6,#0x00
	mov	r7,#0x00
	mov	dpl,_scc_render_sloc0_1_0
	mov	dph,(_scc_render_sloc0_1_0 + 1)
	mov	b,(_scc_render_sloc0_1_0 + 2)
	lcall	__gptrget
	mov	__mullong_PARM_2,a
	inc	dptr
	lcall	__gptrget
	mov	(__mullong_PARM_2 + 1),a
	inc	dptr
	lcall	__gptrget
	mov	(__mullong_PARM_2 + 2),a
	inc	dptr
	lcall	__gptrget
	mov	(__mullong_PARM_2 + 3),a
	mov	dpl, r3
	mov	dph, r4
	mov	b, r6
	mov	a, r7
	lcall	__mullong
	mov	__divulong_PARM_2,dpl
	mov	(__divulong_PARM_2 + 1),dph
	mov	(__divulong_PARM_2 + 2),b
	mov	(__divulong_PARM_2 + 3),a
;	src\scc.c:92: c->counter += step;
	mov	dpl, _scc_render_sloc2_1_0
	mov	dph, (_scc_render_sloc2_1_0 + 1)
	mov	b, (_scc_render_sloc2_1_0 + 2)
	mov	a, (_scc_render_sloc2_1_0 + 3)
	lcall	__divulong
	mov	_scc_render_step_40000_54,dpl
	mov	(_scc_render_step_40000_54 + 1),dph
	mov	(_scc_render_step_40000_54 + 2),b
	mov	(_scc_render_step_40000_54 + 3),a
	mov	dpl,_scc_render_c_30000_53
	mov	dph,(_scc_render_c_30000_53 + 1)
	mov	b,(_scc_render_c_30000_53 + 2)
	lcall	__gptrget
	mov	r3,a
	inc	dptr
	lcall	__gptrget
	mov	r2,a
	inc	dptr
	lcall	__gptrget
	mov	r6,a
	inc	dptr
	lcall	__gptrget
	mov	r7,a
	mov	a,_scc_render_step_40000_54
	add	a, r3
	mov	r3,a
	mov	a,(_scc_render_step_40000_54 + 1)
	addc	a, r2
	mov	r2,a
	mov	a,(_scc_render_step_40000_54 + 2)
	addc	a, r6
	mov	r6,a
	mov	a,(_scc_render_step_40000_54 + 3)
	addc	a, r7
	mov	r7,a
	mov	dpl,_scc_render_c_30000_53
	mov	dph,(_scc_render_c_30000_53 + 1)
	mov	b,(_scc_render_c_30000_53 + 2)
	mov	a,r3
	lcall	__gptrput
	inc	dptr
	mov	a,r2
	lcall	__gptrput
	inc	dptr
	mov	a,r6
	lcall	__gptrput
	inc	dptr
	mov	a,r7
	lcall	__gptrput
;	src\scc.c:93: if (c->key) {
	mov	a,#0x07
	add	a, _scc_render_c_30000_53
	mov	r5,a
	clr	a
	addc	a, (_scc_render_c_30000_53 + 1)
	mov	r6,a
	mov	r7,(_scc_render_c_30000_53 + 2)
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	lcall	__gptrget
	jz	00111$
;	src\scc.c:94: offs = (c->counter >> SCC_FREQ_BITS) & 0x1F;
	mov	dpl,_scc_render_c_30000_53
	mov	dph,(_scc_render_c_30000_53 + 1)
	mov	b,(_scc_render_c_30000_53 + 2)
	lcall	__gptrget
	inc	dptr
	lcall	__gptrget
	inc	dptr
	lcall	__gptrget
	mov	r6,a
	inc	dptr
	lcall	__gptrget
	mov	r7,a
	mov	ar4,r6
	mov	ar5,r7
	anl	ar4,#0x1f
;	src\scc.c:95: smpl = (int16_t)c->waveram[offs] * c->volume;
	clr	a
	mov	a,#0x08
	add	a, _scc_render_c_30000_53
	mov	r2,a
	clr	a
	addc	a, (_scc_render_c_30000_53 + 1)
	clr	a
	addc	a, (_scc_render_c_30000_53 + 2)
	mov	a,r4
	add	a, r2
	mov	r1,a
	mov	a,@r1
	mov	r7,a
	rlc	a
	subb	a,acc
	mov	r6,a
	mov	a,#0x06
	add	a, _scc_render_c_30000_53
	mov	r3,a
	clr	a
	addc	a, (_scc_render_c_30000_53 + 1)
	mov	r4,a
	mov	r5,(_scc_render_c_30000_53 + 2)
	mov	dpl,r3
	mov	dph,r4
	mov	b,r5
	lcall	__gptrget
	mov	r3,a
	mov	__mulint_PARM_2,r3
	mov	(__mulint_PARM_2 + 1),#0x00
;	src\scc.c:96: smpl >>= 4;
	mov	dpl, r7
	mov	dph, r6
	lcall	__mulint
	mov	r6, dpl
	mov	a,dph
	swap	a
	xch	a,r6
	swap	a
	anl	a,#0x0f
	xrl	a,r6
	xch	a,r6
	anl	a,#0x0f
	xch	a,r6
	xrl	a,r6
	xch	a,r6
	jnb	acc.3,00160$
	orl	a,#0xfffffff0
00160$:
	mov	r7,a
;	src\scc.c:97: mix += smpl;
	mov	a,r6
	add	a, _scc_render_mix_10000_51
	mov	_scc_render_mix_10000_51,a
	mov	a,r7
	addc	a, (_scc_render_mix_10000_51 + 1)
	mov	(_scc_render_mix_10000_51 + 1),a
00111$:
;	src\scc.c:84: for (i = 0; i < SCC_CHANS; i++) {
	inc	_scc_render_i_10000_51
	mov	a,#0x100 - 0x05
	add	a,_scc_render_i_10000_51
	jc	00161$
	ljmp	00110$
00161$:
;	src\scc.c:101: if (mix > 127) mix = 127;
	mov	r3,_scc_render_mix_10000_51
	mov	r4,(_scc_render_mix_10000_51 + 1)
	clr	c
	mov	a,#0x7f
	subb	a,r3
	mov	a,#(0x00 ^ 0x80)
	mov	b,r4
	xrl	b,#0x80
	subb	a,b
	jnc	00107$
	mov	_scc_render_mix_10000_51,#0x7f
	mov	(_scc_render_mix_10000_51 + 1),#0x00
00107$:
;	src\scc.c:102: if (mix < -128) mix = -128;
	clr	c
	mov	a,_scc_render_mix_10000_51
	subb	a,#0x80
	mov	a,(_scc_render_mix_10000_51 + 1)
	xrl	a,#0x80
	subb	a,#0x7f
	jnc	00109$
	mov	_scc_render_mix_10000_51,#0x80
	mov	(_scc_render_mix_10000_51 + 1),#0xff
00109$:
;	src\scc.c:103: return (int8_t)mix;
	mov	dpl,_scc_render_mix_10000_51
;	src\scc.c:104: }
	ret
	.area CSEG    (CODE)
	.area CONST   (CODE)
	.area XINIT   (CODE)
	.area CABS    (ABS,CODE)
