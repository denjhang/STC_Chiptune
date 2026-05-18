                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ISO C Compiler 
                                      3 ; Version 4.4.0 #14620 (MINGW32)
                                      4 ;--------------------------------------------------------
                                      5 	.module scc
                                      6 	.optsdcc -mmcs51 --model-small
                                      7 	
                                      8 ;--------------------------------------------------------
                                      9 ; Public variables in this module
                                     10 ;--------------------------------------------------------
                                     11 	.globl _scc_write_PARM_3
                                     12 	.globl _scc_write_PARM_2
                                     13 	.globl _memset
                                     14 	.globl _scc_init_PARM_2
                                     15 	.globl _scc_init
                                     16 	.globl _scc_reset
                                     17 	.globl _scc_write
                                     18 	.globl _scc_render
                                     19 ;--------------------------------------------------------
                                     20 ; special function registers
                                     21 ;--------------------------------------------------------
                                     22 	.area RSEG    (ABS,DATA)
      000000                         23 	.org 0x0000
                                     24 ;--------------------------------------------------------
                                     25 ; special function bits
                                     26 ;--------------------------------------------------------
                                     27 	.area RSEG    (ABS,DATA)
      000000                         28 	.org 0x0000
                                     29 ;--------------------------------------------------------
                                     30 ; overlayable register banks
                                     31 ;--------------------------------------------------------
                                     32 	.area REG_BANK_0	(REL,OVR,DATA)
      000000                         33 	.ds 8
                                     34 ;--------------------------------------------------------
                                     35 ; internal ram data
                                     36 ;--------------------------------------------------------
                                     37 	.area DSEG    (DATA)
      000021                         38 _scc_init_PARM_2:
      000021                         39 	.ds 4
      000025                         40 _scc_reset_s_10000_32:
      000025                         41 	.ds 3
      000028                         42 _scc_render_s_10000_50:
      000028                         43 	.ds 3
      00002B                         44 _scc_render_mix_10000_51:
      00002B                         45 	.ds 2
      00002D                         46 _scc_render_i_10000_51:
      00002D                         47 	.ds 1
      00002E                         48 _scc_render_c_30000_53:
      00002E                         49 	.ds 3
      000031                         50 _scc_render_step_40000_54:
      000031                         51 	.ds 4
      000035                         52 _scc_render_sloc0_1_0:
      000035                         53 	.ds 3
      000038                         54 _scc_render_sloc1_1_0:
      000038                         55 	.ds 3
      00003B                         56 _scc_render_sloc2_1_0:
      00003B                         57 	.ds 4
                                     58 ;--------------------------------------------------------
                                     59 ; overlayable items in internal ram
                                     60 ;--------------------------------------------------------
                                     61 	.area	OSEG    (OVR,DATA)
      000062                         62 _scc_write_PARM_2:
      000062                         63 	.ds 1
      000063                         64 _scc_write_PARM_3:
      000063                         65 	.ds 1
      000064                         66 _scc_write_s_10000_36:
      000064                         67 	.ds 3
                                     68 ;--------------------------------------------------------
                                     69 ; indirectly addressable internal ram data
                                     70 ;--------------------------------------------------------
                                     71 	.area ISEG    (DATA)
                                     72 ;--------------------------------------------------------
                                     73 ; absolute internal ram data
                                     74 ;--------------------------------------------------------
                                     75 	.area IABS    (ABS,DATA)
                                     76 	.area IABS    (ABS,DATA)
                                     77 ;--------------------------------------------------------
                                     78 ; bit data
                                     79 ;--------------------------------------------------------
                                     80 	.area BSEG    (BIT)
                                     81 ;--------------------------------------------------------
                                     82 ; paged external ram data
                                     83 ;--------------------------------------------------------
                                     84 	.area PSEG    (PAG,XDATA)
                                     85 ;--------------------------------------------------------
                                     86 ; uninitialized external ram data
                                     87 ;--------------------------------------------------------
                                     88 	.area XSEG    (XDATA)
                                     89 ;--------------------------------------------------------
                                     90 ; absolute external ram data
                                     91 ;--------------------------------------------------------
                                     92 	.area XABS    (ABS,XDATA)
                                     93 ;--------------------------------------------------------
                                     94 ; initialized external ram data
                                     95 ;--------------------------------------------------------
                                     96 	.area XISEG   (XDATA)
                                     97 	.area HOME    (CODE)
                                     98 	.area GSINIT0 (CODE)
                                     99 	.area GSINIT1 (CODE)
                                    100 	.area GSINIT2 (CODE)
                                    101 	.area GSINIT3 (CODE)
                                    102 	.area GSINIT4 (CODE)
                                    103 	.area GSINIT5 (CODE)
                                    104 	.area GSINIT  (CODE)
                                    105 	.area GSFINAL (CODE)
                                    106 	.area CSEG    (CODE)
                                    107 ;--------------------------------------------------------
                                    108 ; global & static initialisations
                                    109 ;--------------------------------------------------------
                                    110 	.area HOME    (CODE)
                                    111 	.area GSINIT  (CODE)
                                    112 	.area GSFINAL (CODE)
                                    113 	.area GSINIT  (CODE)
                                    114 ;--------------------------------------------------------
                                    115 ; Home
                                    116 ;--------------------------------------------------------
                                    117 	.area HOME    (CODE)
                                    118 	.area HOME    (CODE)
                                    119 ;--------------------------------------------------------
                                    120 ; code
                                    121 ;--------------------------------------------------------
                                    122 	.area CSEG    (CODE)
                                    123 ;------------------------------------------------------------
                                    124 ;Allocation info for local variables in function 'scc_init'
                                    125 ;------------------------------------------------------------
                                    126 ;clock_hz                  Allocated with name '_scc_init_PARM_2'
                                    127 ;s                         Allocated to registers r5 r6 r7 
                                    128 ;tmp                       Allocated to registers r1 r2 r3 r4 
                                    129 ;------------------------------------------------------------
                                    130 ;	src\scc.c:4: void scc_init(scc_state_t *s, uint32_t clock_hz) {
                                    131 ;	-----------------------------------------
                                    132 ;	 function scc_init
                                    133 ;	-----------------------------------------
      0002B5                        134 _scc_init:
                           000007   135 	ar7 = 0x07
                           000006   136 	ar6 = 0x06
                           000005   137 	ar5 = 0x05
                           000004   138 	ar4 = 0x04
                           000003   139 	ar3 = 0x03
                           000002   140 	ar2 = 0x02
                           000001   141 	ar1 = 0x01
                           000000   142 	ar0 = 0x00
      0002B5 AD 82            [24]  143 	mov	r5, dpl
      0002B7 AE 83            [24]  144 	mov	r6, dph
      0002B9 AF F0            [24]  145 	mov	r7, b
                                    146 ;	src\scc.c:6: memset(s, 0, sizeof(*s));
      0002BB 8D 02            [24]  147 	mov	ar2,r5
      0002BD 8E 03            [24]  148 	mov	ar3,r6
      0002BF 8F 04            [24]  149 	mov	ar4,r7
      0002C1 75 62 00         [24]  150 	mov	_memset_PARM_2,#0x00
      0002C4 75 63 D3         [24]  151 	mov	_memset_PARM_3,#0xd3
      0002C7 75 64 00         [24]  152 	mov	(_memset_PARM_3 + 1),#0x00
      0002CA 8A 82            [24]  153 	mov	dpl, r2
      0002CC 8B 83            [24]  154 	mov	dph, r3
      0002CE 8C F0            [24]  155 	mov	b, r4
      0002D0 C0 07            [24]  156 	push	ar7
      0002D2 C0 06            [24]  157 	push	ar6
      0002D4 C0 05            [24]  158 	push	ar5
      0002D6 12 09 A7         [24]  159 	lcall	_memset
      0002D9 D0 05            [24]  160 	pop	ar5
      0002DB D0 06            [24]  161 	pop	ar6
      0002DD D0 07            [24]  162 	pop	ar7
                                    163 ;	src\scc.c:7: s->rate = 44100;
      0002DF 74 C8            [12]  164 	mov	a,#0xc8
      0002E1 2D               [12]  165 	add	a, r5
      0002E2 FA               [12]  166 	mov	r2,a
      0002E3 E4               [12]  167 	clr	a
      0002E4 3E               [12]  168 	addc	a, r6
      0002E5 FB               [12]  169 	mov	r3,a
      0002E6 8F 04            [24]  170 	mov	ar4,r7
      0002E8 8A 82            [24]  171 	mov	dpl,r2
      0002EA 8B 83            [24]  172 	mov	dph,r3
      0002EC 8C F0            [24]  173 	mov	b,r4
      0002EE 74 44            [12]  174 	mov	a,#0x44
      0002F0 12 0F 20         [24]  175 	lcall	__gptrput
      0002F3 A3               [24]  176 	inc	dptr
      0002F4 74 AC            [12]  177 	mov	a,#0xac
      0002F6 12 0F 20         [24]  178 	lcall	__gptrput
      0002F9 A3               [24]  179 	inc	dptr
      0002FA E4               [12]  180 	clr	a
      0002FB 12 0F 20         [24]  181 	lcall	__gptrput
      0002FE A3               [24]  182 	inc	dptr
      0002FF 12 0F 20         [24]  183 	lcall	__gptrput
                                    184 ;	src\scc.c:9: tmp = clock_hz >> 1;
      000302 E5 24            [12]  185 	mov	a,(_scc_init_PARM_2 + 3)
      000304 C3               [12]  186 	clr	c
      000305 13               [12]  187 	rrc	a
      000306 E5 23            [12]  188 	mov	a,(_scc_init_PARM_2 + 2)
      000308 13               [12]  189 	rrc	a
      000309 E5 22            [12]  190 	mov	a,(_scc_init_PARM_2 + 1)
      00030B 13               [12]  191 	rrc	a
      00030C FA               [12]  192 	mov	r2,a
      00030D E5 21            [12]  193 	mov	a,_scc_init_PARM_2
      00030F 13               [12]  194 	rrc	a
      000310 F9               [12]  195 	mov	r1,a
                                    196 ;	src\scc.c:10: s->clock_factor = tmp << (SCC_FREQ_BITS + 1);
      000311 74 CC            [12]  197 	mov	a,#0xcc
      000313 2D               [12]  198 	add	a, r5
      000314 FD               [12]  199 	mov	r5,a
      000315 E4               [12]  200 	clr	a
      000316 3E               [12]  201 	addc	a, r6
      000317 FE               [12]  202 	mov	r6,a
      000318 89 03            [24]  203 	mov	ar3,r1
      00031A EA               [12]  204 	mov	a,r2
      00031B CB               [12]  205 	xch	a,r3
      00031C 25 E0            [12]  206 	add	a,acc
      00031E CB               [12]  207 	xch	a,r3
      00031F 33               [12]  208 	rlc	a
      000320 FC               [12]  209 	mov	r4,a
      000321 79 00            [12]  210 	mov	r1,#0x00
      000323 7A 00            [12]  211 	mov	r2,#0x00
      000325 8D 82            [24]  212 	mov	dpl,r5
      000327 8E 83            [24]  213 	mov	dph,r6
      000329 8F F0            [24]  214 	mov	b,r7
      00032B E9               [12]  215 	mov	a,r1
      00032C 12 0F 20         [24]  216 	lcall	__gptrput
      00032F A3               [24]  217 	inc	dptr
      000330 EA               [12]  218 	mov	a,r2
      000331 12 0F 20         [24]  219 	lcall	__gptrput
      000334 A3               [24]  220 	inc	dptr
      000335 EB               [12]  221 	mov	a,r3
      000336 12 0F 20         [24]  222 	lcall	__gptrput
      000339 A3               [24]  223 	inc	dptr
      00033A EC               [12]  224 	mov	a,r4
                                    225 ;	src\scc.c:11: }
      00033B 02 0F 20         [24]  226 	ljmp	__gptrput
                                    227 ;------------------------------------------------------------
                                    228 ;Allocation info for local variables in function 'scc_reset'
                                    229 ;------------------------------------------------------------
                                    230 ;s                         Allocated with name '_scc_reset_s_10000_32'
                                    231 ;i                         Allocated to registers r4 
                                    232 ;------------------------------------------------------------
                                    233 ;	src\scc.c:13: void scc_reset(scc_state_t *s) {
                                    234 ;	-----------------------------------------
                                    235 ;	 function scc_reset
                                    236 ;	-----------------------------------------
      00033E                        237 _scc_reset:
      00033E 85 82 25         [24]  238 	mov	_scc_reset_s_10000_32,dpl
      000341 85 83 26         [24]  239 	mov	(_scc_reset_s_10000_32 + 1),dph
      000344 85 F0 27         [24]  240 	mov	(_scc_reset_s_10000_32 + 2),b
                                    241 ;	src\scc.c:15: for (i = 0; i < SCC_CHANS; i++) {
      000347 7C 00            [12]  242 	mov	r4,#0x00
      000349                        243 00102$:
                                    244 ;	src\scc.c:16: s->ch[i].counter = 0;
      000349 EC               [12]  245 	mov	a,r4
      00034A 75 F0 28         [24]  246 	mov	b,#0x28
      00034D A4               [48]  247 	mul	ab
      00034E FB               [12]  248 	mov	r3,a
      00034F 25 25            [12]  249 	add	a, _scc_reset_s_10000_32
      000351 F8               [12]  250 	mov	r0,a
      000352 E4               [12]  251 	clr	a
      000353 35 26            [12]  252 	addc	a, (_scc_reset_s_10000_32 + 1)
      000355 F9               [12]  253 	mov	r1,a
      000356 AA 27            [24]  254 	mov	r2,(_scc_reset_s_10000_32 + 2)
      000358 88 82            [24]  255 	mov	dpl,r0
      00035A 89 83            [24]  256 	mov	dph,r1
      00035C 8A F0            [24]  257 	mov	b,r2
      00035E E4               [12]  258 	clr	a
      00035F 12 0F 20         [24]  259 	lcall	__gptrput
      000362 A3               [24]  260 	inc	dptr
      000363 12 0F 20         [24]  261 	lcall	__gptrput
      000366 A3               [24]  262 	inc	dptr
      000367 12 0F 20         [24]  263 	lcall	__gptrput
      00036A A3               [24]  264 	inc	dptr
      00036B 12 0F 20         [24]  265 	lcall	__gptrput
                                    266 ;	src\scc.c:17: s->ch[i].frequency = 0;
      00036E EB               [12]  267 	mov	a,r3
      00036F 25 25            [12]  268 	add	a, _scc_reset_s_10000_32
      000371 F9               [12]  269 	mov	r1,a
      000372 E4               [12]  270 	clr	a
      000373 35 26            [12]  271 	addc	a, (_scc_reset_s_10000_32 + 1)
      000375 FA               [12]  272 	mov	r2,a
      000376 AB 27            [24]  273 	mov	r3,(_scc_reset_s_10000_32 + 2)
      000378 74 04            [12]  274 	mov	a,#0x04
      00037A 29               [12]  275 	add	a, r1
      00037B F8               [12]  276 	mov	r0,a
      00037C E4               [12]  277 	clr	a
      00037D 3A               [12]  278 	addc	a, r2
      00037E FE               [12]  279 	mov	r6,a
      00037F 8B 07            [24]  280 	mov	ar7,r3
      000381 88 82            [24]  281 	mov	dpl,r0
      000383 8E 83            [24]  282 	mov	dph,r6
      000385 8F F0            [24]  283 	mov	b,r7
      000387 E4               [12]  284 	clr	a
      000388 12 0F 20         [24]  285 	lcall	__gptrput
      00038B A3               [24]  286 	inc	dptr
      00038C 12 0F 20         [24]  287 	lcall	__gptrput
                                    288 ;	src\scc.c:18: s->ch[i].volume = 0;
      00038F 74 06            [12]  289 	mov	a,#0x06
      000391 29               [12]  290 	add	a, r1
      000392 FD               [12]  291 	mov	r5,a
      000393 E4               [12]  292 	clr	a
      000394 3A               [12]  293 	addc	a, r2
      000395 FE               [12]  294 	mov	r6,a
      000396 8B 07            [24]  295 	mov	ar7,r3
      000398 8D 82            [24]  296 	mov	dpl,r5
      00039A 8E 83            [24]  297 	mov	dph,r6
      00039C 8F F0            [24]  298 	mov	b,r7
      00039E E4               [12]  299 	clr	a
      00039F 12 0F 20         [24]  300 	lcall	__gptrput
                                    301 ;	src\scc.c:19: s->ch[i].key = 0;
      0003A2 74 07            [12]  302 	mov	a,#0x07
      0003A4 29               [12]  303 	add	a, r1
      0003A5 FD               [12]  304 	mov	r5,a
      0003A6 E4               [12]  305 	clr	a
      0003A7 3A               [12]  306 	addc	a, r2
      0003A8 FE               [12]  307 	mov	r6,a
      0003A9 8B 07            [24]  308 	mov	ar7,r3
      0003AB 8D 82            [24]  309 	mov	dpl,r5
      0003AD 8E 83            [24]  310 	mov	dph,r6
      0003AF 8F F0            [24]  311 	mov	b,r7
      0003B1 E4               [12]  312 	clr	a
      0003B2 12 0F 20         [24]  313 	lcall	__gptrput
                                    314 ;	src\scc.c:20: memset(s->ch[i].waveram, 0, SCC_WAVELEN);
      0003B5 74 08            [12]  315 	mov	a,#0x08
      0003B7 29               [12]  316 	add	a, r1
      0003B8 F9               [12]  317 	mov	r1,a
      0003B9 E4               [12]  318 	clr	a
      0003BA 3A               [12]  319 	addc	a, r2
      0003BB FA               [12]  320 	mov	r2,a
      0003BC 75 62 00         [24]  321 	mov	_memset_PARM_2,#0x00
      0003BF 75 63 20         [24]  322 	mov	_memset_PARM_3,#0x20
      0003C2 75 64 00         [24]  323 	mov	(_memset_PARM_3 + 1),#0x00
      0003C5 89 82            [24]  324 	mov	dpl, r1
      0003C7 8A 83            [24]  325 	mov	dph, r2
      0003C9 8B F0            [24]  326 	mov	b, r3
      0003CB C0 04            [24]  327 	push	ar4
      0003CD 12 09 A7         [24]  328 	lcall	_memset
      0003D0 D0 04            [24]  329 	pop	ar4
                                    330 ;	src\scc.c:15: for (i = 0; i < SCC_CHANS; i++) {
      0003D2 0C               [12]  331 	inc	r4
      0003D3 BC 05 00         [24]  332 	cjne	r4,#0x05,00119$
      0003D6                        333 00119$:
      0003D6 50 03            [24]  334 	jnc	00120$
      0003D8 02 03 49         [24]  335 	ljmp	00102$
      0003DB                        336 00120$:
                                    337 ;	src\scc.c:22: s->test = 0;
      0003DB 74 D1            [12]  338 	mov	a,#0xd1
      0003DD 25 25            [12]  339 	add	a, _scc_reset_s_10000_32
      0003DF FD               [12]  340 	mov	r5,a
      0003E0 E4               [12]  341 	clr	a
      0003E1 35 26            [12]  342 	addc	a, (_scc_reset_s_10000_32 + 1)
      0003E3 FE               [12]  343 	mov	r6,a
      0003E4 AF 27            [24]  344 	mov	r7,(_scc_reset_s_10000_32 + 2)
      0003E6 8D 82            [24]  345 	mov	dpl,r5
      0003E8 8E 83            [24]  346 	mov	dph,r6
      0003EA 8F F0            [24]  347 	mov	b,r7
      0003EC E4               [12]  348 	clr	a
      0003ED 12 0F 20         [24]  349 	lcall	__gptrput
                                    350 ;	src\scc.c:23: s->cur_reg = 0;
      0003F0 74 D2            [12]  351 	mov	a,#0xd2
      0003F2 25 25            [12]  352 	add	a, _scc_reset_s_10000_32
      0003F4 FD               [12]  353 	mov	r5,a
      0003F5 E4               [12]  354 	clr	a
      0003F6 35 26            [12]  355 	addc	a, (_scc_reset_s_10000_32 + 1)
      0003F8 FE               [12]  356 	mov	r6,a
      0003F9 AF 27            [24]  357 	mov	r7,(_scc_reset_s_10000_32 + 2)
      0003FB 8D 82            [24]  358 	mov	dpl,r5
      0003FD 8E 83            [24]  359 	mov	dph,r6
      0003FF 8F F0            [24]  360 	mov	b,r7
      000401 E4               [12]  361 	clr	a
                                    362 ;	src\scc.c:24: }
      000402 02 0F 20         [24]  363 	ljmp	__gptrput
                                    364 ;------------------------------------------------------------
                                    365 ;Allocation info for local variables in function 'scc_write'
                                    366 ;------------------------------------------------------------
                                    367 ;port                      Allocated with name '_scc_write_PARM_2'
                                    368 ;data                      Allocated with name '_scc_write_PARM_3'
                                    369 ;s                         Allocated with name '_scc_write_s_10000_36'
                                    370 ;offset                    Allocated to registers r7 
                                    371 ;ch                        Allocated to registers r7 
                                    372 ;------------------------------------------------------------
                                    373 ;	src\scc.c:26: void scc_write(scc_state_t *s, uint8_t port, uint8_t data) {
                                    374 ;	-----------------------------------------
                                    375 ;	 function scc_write
                                    376 ;	-----------------------------------------
      000405                        377 _scc_write:
      000405 85 82 64         [24]  378 	mov	_scc_write_s_10000_36,dpl
      000408 85 83 65         [24]  379 	mov	(_scc_write_s_10000_36 + 1),dph
      00040B 85 F0 66         [24]  380 	mov	(_scc_write_s_10000_36 + 2),b
                                    381 ;	src\scc.c:28: if (port & 1) {
      00040E E5 62            [12]  382 	mov	a,_scc_write_PARM_2
      000410 FC               [12]  383 	mov	r4,a
      000411 20 E0 03         [24]  384 	jb	acc.0,00221$
      000414 02 07 1E         [24]  385 	ljmp	00130$
      000417                        386 00221$:
                                    387 ;	src\scc.c:29: switch (port >> 1) {
      000417 EC               [12]  388 	mov	a,r4
      000418 C3               [12]  389 	clr	c
      000419 13               [12]  390 	rrc	a
      00041A FC               [12]  391 	mov  r4,a
      00041B 24 FA            [12]  392 	add	a,#0xff - 0x05
      00041D 50 01            [24]  393 	jnc	00222$
      00041F 22               [24]  394 	ret
      000420                        395 00222$:
      000420 EC               [12]  396 	mov	a,r4
      000421 2C               [12]  397 	add	a,r4
      000422 2C               [12]  398 	add	a,r4
      000423 90 04 27         [24]  399 	mov	dptr,#00223$
      000426 73               [24]  400 	jmp	@a+dptr
      000427                        401 00223$:
      000427 02 04 39         [24]  402 	ljmp	00102$
      00042A 02 05 33         [24]  403 	ljmp	00111$
      00042D 02 06 91         [24]  404 	ljmp	00122$
      000430 02 06 D2         [24]  405 	ljmp	00146$
      000433 02 04 39         [24]  406 	ljmp	00102$
      000436 02 07 08         [24]  407 	ljmp	00127$
                                    408 ;	src\scc.c:31: case 0x04: {
      000439                        409 00102$:
                                    410 ;	src\scc.c:32: offset = s->cur_reg;
      000439 74 D2            [12]  411 	mov	a,#0xd2
      00043B 25 64            [12]  412 	add	a, _scc_write_s_10000_36
      00043D FA               [12]  413 	mov	r2,a
      00043E E4               [12]  414 	clr	a
      00043F 35 65            [12]  415 	addc	a, (_scc_write_s_10000_36 + 1)
      000441 FB               [12]  416 	mov	r3,a
      000442 AC 66            [24]  417 	mov	r4,(_scc_write_s_10000_36 + 2)
      000444 8A 82            [24]  418 	mov	dpl,r2
      000446 8B 83            [24]  419 	mov	dph,r3
      000448 8C F0            [24]  420 	mov	b,r4
      00044A 12 0F C6         [24]  421 	lcall	__gptrget
      00044D FC               [12]  422 	mov	r4,a
                                    423 ;	src\scc.c:33: if (s->test & 0x40) return;
      00044E 74 D1            [12]  424 	mov	a,#0xd1
      000450 25 64            [12]  425 	add	a, _scc_write_s_10000_36
      000452 F9               [12]  426 	mov	r1,a
      000453 E4               [12]  427 	clr	a
      000454 35 65            [12]  428 	addc	a, (_scc_write_s_10000_36 + 1)
      000456 FA               [12]  429 	mov	r2,a
      000457 AB 66            [24]  430 	mov	r3,(_scc_write_s_10000_36 + 2)
      000459 89 82            [24]  431 	mov	dpl,r1
      00045B 8A 83            [24]  432 	mov	dph,r2
      00045D 8B F0            [24]  433 	mov	b,r3
      00045F 12 0F C6         [24]  434 	lcall	__gptrget
      000462 30 E6 01         [24]  435 	jnb	acc.6,00104$
      000465 22               [24]  436 	ret
      000466                        437 00104$:
                                    438 ;	src\scc.c:34: if (!s->mode_plus) {
      000466 74 D0            [12]  439 	mov	a,#0xd0
      000468 25 64            [12]  440 	add	a, _scc_write_s_10000_36
      00046A F9               [12]  441 	mov	r1,a
      00046B E4               [12]  442 	clr	a
      00046C 35 65            [12]  443 	addc	a, (_scc_write_s_10000_36 + 1)
      00046E FA               [12]  444 	mov	r2,a
      00046F AB 66            [24]  445 	mov	r3,(_scc_write_s_10000_36 + 2)
      000471 89 82            [24]  446 	mov	dpl,r1
      000473 8A 83            [24]  447 	mov	dph,r2
      000475 8B F0            [24]  448 	mov	b,r3
      000477 12 0F C6         [24]  449 	lcall	__gptrget
      00047A 60 03            [24]  450 	jz	00225$
      00047C 02 05 03         [24]  451 	ljmp	00109$
      00047F                        452 00225$:
                                    453 ;	src\scc.c:35: if (offset >= 0x60) {
      00047F BC 60 00         [24]  454 	cjne	r4,#0x60,00226$
      000482                        455 00226$:
      000482 40 4D            [24]  456 	jc	00106$
                                    457 ;	src\scc.c:36: s->ch[3].waveram[offset & 0x1f] = (int8_t)data;
      000484 74 78            [12]  458 	mov	a,#0x78
      000486 25 64            [12]  459 	add	a, _scc_write_s_10000_36
      000488 F9               [12]  460 	mov	r1,a
      000489 E4               [12]  461 	clr	a
      00048A 35 65            [12]  462 	addc	a, (_scc_write_s_10000_36 + 1)
      00048C FA               [12]  463 	mov	r2,a
      00048D AB 66            [24]  464 	mov	r3,(_scc_write_s_10000_36 + 2)
      00048F 74 08            [12]  465 	mov	a,#0x08
      000491 29               [12]  466 	add	a, r1
      000492 F9               [12]  467 	mov	r1,a
      000493 E4               [12]  468 	clr	a
      000494 3A               [12]  469 	addc	a, r2
      000495 FA               [12]  470 	mov	r2,a
      000496 8C 00            [24]  471 	mov	ar0,r4
      000498 53 00 1F         [24]  472 	anl	ar0,#0x1f
      00049B 7F 00            [12]  473 	mov	r7,#0x00
      00049D E8               [12]  474 	mov	a,r0
      00049E 29               [12]  475 	add	a, r1
      00049F F9               [12]  476 	mov	r1,a
      0004A0 EF               [12]  477 	mov	a,r7
      0004A1 3A               [12]  478 	addc	a, r2
      0004A2 FA               [12]  479 	mov	r2,a
      0004A3 AE 63            [24]  480 	mov	r6,_scc_write_PARM_3
      0004A5 89 82            [24]  481 	mov	dpl,r1
      0004A7 8A 83            [24]  482 	mov	dph,r2
      0004A9 8B F0            [24]  483 	mov	b,r3
      0004AB EE               [12]  484 	mov	a,r6
      0004AC 12 0F 20         [24]  485 	lcall	__gptrput
                                    486 ;	src\scc.c:37: s->ch[4].waveram[offset & 0x1f] = (int8_t)data;
      0004AF 74 A0            [12]  487 	mov	a,#0xa0
      0004B1 25 64            [12]  488 	add	a, _scc_write_s_10000_36
      0004B3 FA               [12]  489 	mov	r2,a
      0004B4 E4               [12]  490 	clr	a
      0004B5 35 65            [12]  491 	addc	a, (_scc_write_s_10000_36 + 1)
      0004B7 FB               [12]  492 	mov	r3,a
      0004B8 AD 66            [24]  493 	mov	r5,(_scc_write_s_10000_36 + 2)
      0004BA 74 08            [12]  494 	mov	a,#0x08
      0004BC 2A               [12]  495 	add	a, r2
      0004BD FA               [12]  496 	mov	r2,a
      0004BE E4               [12]  497 	clr	a
      0004BF 3B               [12]  498 	addc	a, r3
      0004C0 FB               [12]  499 	mov	r3,a
      0004C1 E8               [12]  500 	mov	a,r0
      0004C2 2A               [12]  501 	add	a, r2
      0004C3 FA               [12]  502 	mov	r2,a
      0004C4 EF               [12]  503 	mov	a,r7
      0004C5 3B               [12]  504 	addc	a, r3
      0004C6 FB               [12]  505 	mov	r3,a
      0004C7 8A 82            [24]  506 	mov	dpl,r2
      0004C9 8B 83            [24]  507 	mov	dph,r3
      0004CB 8D F0            [24]  508 	mov	b,r5
      0004CD EE               [12]  509 	mov	a,r6
      0004CE 02 0F 20         [24]  510 	ljmp	__gptrput
      0004D1                        511 00106$:
                                    512 ;	src\scc.c:39: s->ch[offset >> 5].waveram[offset & 0x1f] = (int8_t)data;
      0004D1 EC               [12]  513 	mov	a,r4
      0004D2 C4               [12]  514 	swap	a
      0004D3 03               [12]  515 	rr	a
      0004D4 54 07            [12]  516 	anl	a,#0x07
      0004D6 75 F0 28         [24]  517 	mov	b,#0x28
      0004D9 A4               [48]  518 	mul	ab
      0004DA 25 64            [12]  519 	add	a, _scc_write_s_10000_36
      0004DC FD               [12]  520 	mov	r5,a
      0004DD E4               [12]  521 	clr	a
      0004DE 35 65            [12]  522 	addc	a,(_scc_write_s_10000_36 + 1)
      0004E0 FE               [12]  523 	mov	r6,a
      0004E1 AF 66            [24]  524 	mov	r7,(_scc_write_s_10000_36 + 2)
      0004E3 74 08            [12]  525 	mov	a,#0x08
      0004E5 2D               [12]  526 	add	a, r5
      0004E6 FD               [12]  527 	mov	r5,a
      0004E7 E4               [12]  528 	clr	a
      0004E8 3E               [12]  529 	addc	a, r6
      0004E9 FE               [12]  530 	mov	r6,a
      0004EA 8C 02            [24]  531 	mov	ar2,r4
      0004EC 53 02 1F         [24]  532 	anl	ar2,#0x1f
      0004EF 7B 00            [12]  533 	mov	r3,#0x00
      0004F1 EA               [12]  534 	mov	a,r2
      0004F2 2D               [12]  535 	add	a, r5
      0004F3 FD               [12]  536 	mov	r5,a
      0004F4 EB               [12]  537 	mov	a,r3
      0004F5 3E               [12]  538 	addc	a, r6
      0004F6 FE               [12]  539 	mov	r6,a
      0004F7 AB 63            [24]  540 	mov	r3,_scc_write_PARM_3
      0004F9 8D 82            [24]  541 	mov	dpl,r5
      0004FB 8E 83            [24]  542 	mov	dph,r6
      0004FD 8F F0            [24]  543 	mov	b,r7
      0004FF EB               [12]  544 	mov	a,r3
      000500 02 0F 20         [24]  545 	ljmp	__gptrput
      000503                        546 00109$:
                                    547 ;	src\scc.c:42: s->ch[offset >> 5].waveram[offset & 0x1f] = (int8_t)data;
      000503 EC               [12]  548 	mov	a,r4
      000504 C4               [12]  549 	swap	a
      000505 03               [12]  550 	rr	a
      000506 54 07            [12]  551 	anl	a,#0x07
      000508 75 F0 28         [24]  552 	mov	b,#0x28
      00050B A4               [48]  553 	mul	ab
      00050C 25 64            [12]  554 	add	a, _scc_write_s_10000_36
      00050E FD               [12]  555 	mov	r5,a
      00050F E4               [12]  556 	clr	a
      000510 35 65            [12]  557 	addc	a,(_scc_write_s_10000_36 + 1)
      000512 FE               [12]  558 	mov	r6,a
      000513 AF 66            [24]  559 	mov	r7,(_scc_write_s_10000_36 + 2)
      000515 74 08            [12]  560 	mov	a,#0x08
      000517 2D               [12]  561 	add	a, r5
      000518 FD               [12]  562 	mov	r5,a
      000519 E4               [12]  563 	clr	a
      00051A 3E               [12]  564 	addc	a, r6
      00051B FE               [12]  565 	mov	r6,a
      00051C 53 04 1F         [24]  566 	anl	ar4,#0x1f
      00051F 7B 00            [12]  567 	mov	r3,#0x00
      000521 EC               [12]  568 	mov	a,r4
      000522 2D               [12]  569 	add	a, r5
      000523 FD               [12]  570 	mov	r5,a
      000524 EB               [12]  571 	mov	a,r3
      000525 3E               [12]  572 	addc	a, r6
      000526 FE               [12]  573 	mov	r6,a
      000527 AC 63            [24]  574 	mov	r4,_scc_write_PARM_3
      000529 8D 82            [24]  575 	mov	dpl,r5
      00052B 8E 83            [24]  576 	mov	dph,r6
      00052D 8F F0            [24]  577 	mov	b,r7
      00052F EC               [12]  578 	mov	a,r4
                                    579 ;	src\scc.c:44: break;
      000530 02 0F 20         [24]  580 	ljmp	__gptrput
                                    581 ;	src\scc.c:46: case 0x01: {
      000533                        582 00111$:
                                    583 ;	src\scc.c:47: offset = s->cur_reg;
      000533 74 D2            [12]  584 	mov	a,#0xd2
      000535 25 64            [12]  585 	add	a, _scc_write_s_10000_36
      000537 FD               [12]  586 	mov	r5,a
      000538 E4               [12]  587 	clr	a
      000539 35 65            [12]  588 	addc	a, (_scc_write_s_10000_36 + 1)
      00053B FE               [12]  589 	mov	r6,a
      00053C AF 66            [24]  590 	mov	r7,(_scc_write_s_10000_36 + 2)
      00053E 8D 82            [24]  591 	mov	dpl,r5
      000540 8E 83            [24]  592 	mov	dph,r6
      000542 8F F0            [24]  593 	mov	b,r7
      000544 12 0F C6         [24]  594 	lcall	__gptrget
                                    595 ;	src\scc.c:48: ch = offset >> 1;
      000547 FF               [12]  596 	mov	r7,a
      000548 C3               [12]  597 	clr	c
      000549 13               [12]  598 	rrc	a
      00054A FE               [12]  599 	mov	r6,a
                                    600 ;	src\scc.c:49: if (ch < SCC_CHANS) {
      00054B BE 05 00         [24]  601 	cjne	r6,#0x05,00228$
      00054E                        602 00228$:
      00054E 40 01            [24]  603 	jc	00229$
      000550 22               [24]  604 	ret
      000551                        605 00229$:
                                    606 ;	src\scc.c:50: if (offset & 1)
      000551 EF               [12]  607 	mov	a,r7
      000552 30 E0 47         [24]  608 	jnb	acc.0,00113$
                                    609 ;	src\scc.c:51: s->ch[ch].frequency = (s->ch[ch].frequency & 0x00FF) | ((uint16_t)(data & 0x0F) << 8);
      000555 EE               [12]  610 	mov	a,r6
      000556 75 F0 28         [24]  611 	mov	b,#0x28
      000559 A4               [48]  612 	mul	ab
      00055A 25 64            [12]  613 	add	a, _scc_write_s_10000_36
      00055C FC               [12]  614 	mov	r4,a
      00055D E4               [12]  615 	clr	a
      00055E 35 65            [12]  616 	addc	a,(_scc_write_s_10000_36 + 1)
      000560 FD               [12]  617 	mov	r5,a
      000561 AF 66            [24]  618 	mov	r7,(_scc_write_s_10000_36 + 2)
      000563 74 04            [12]  619 	mov	a,#0x04
      000565 2C               [12]  620 	add	a, r4
      000566 FC               [12]  621 	mov	r4,a
      000567 E4               [12]  622 	clr	a
      000568 3D               [12]  623 	addc	a, r5
      000569 FD               [12]  624 	mov	r5,a
      00056A 8C 82            [24]  625 	mov	dpl,r4
      00056C 8D 83            [24]  626 	mov	dph,r5
      00056E 8F F0            [24]  627 	mov	b,r7
      000570 12 0F C6         [24]  628 	lcall	__gptrget
      000573 FA               [12]  629 	mov	r2,a
      000574 A3               [24]  630 	inc	dptr
      000575 12 0F C6         [24]  631 	lcall	__gptrget
      000578 7B 00            [12]  632 	mov	r3,#0x00
      00057A A9 63            [24]  633 	mov	r1,_scc_write_PARM_3
      00057C 53 01 0F         [24]  634 	anl	ar1,#0x0f
      00057F 89 00            [24]  635 	mov	ar0,r1
      000581 88 01            [24]  636 	mov	ar1,r0
      000583 78 00            [12]  637 	mov	r0,#0x00
      000585 EA               [12]  638 	mov	a,r2
      000586 42 00            [12]  639 	orl	ar0,a
      000588 EB               [12]  640 	mov	a,r3
      000589 42 01            [12]  641 	orl	ar1,a
      00058B 8C 82            [24]  642 	mov	dpl,r4
      00058D 8D 83            [24]  643 	mov	dph,r5
      00058F 8F F0            [24]  644 	mov	b,r7
      000591 E8               [12]  645 	mov	a,r0
      000592 12 0F 20         [24]  646 	lcall	__gptrput
      000595 A3               [24]  647 	inc	dptr
      000596 E9               [12]  648 	mov	a,r1
      000597 12 0F 20         [24]  649 	lcall	__gptrput
      00059A 80 41            [24]  650 	sjmp	00114$
      00059C                        651 00113$:
                                    652 ;	src\scc.c:53: s->ch[ch].frequency = (s->ch[ch].frequency & 0x0F00) | data;
      00059C EE               [12]  653 	mov	a,r6
      00059D 75 F0 28         [24]  654 	mov	b,#0x28
      0005A0 A4               [48]  655 	mul	ab
      0005A1 25 64            [12]  656 	add	a, _scc_write_s_10000_36
      0005A3 FC               [12]  657 	mov	r4,a
      0005A4 E4               [12]  658 	clr	a
      0005A5 35 65            [12]  659 	addc	a,(_scc_write_s_10000_36 + 1)
      0005A7 FD               [12]  660 	mov	r5,a
      0005A8 AF 66            [24]  661 	mov	r7,(_scc_write_s_10000_36 + 2)
      0005AA 74 04            [12]  662 	mov	a,#0x04
      0005AC 2C               [12]  663 	add	a, r4
      0005AD FC               [12]  664 	mov	r4,a
      0005AE E4               [12]  665 	clr	a
      0005AF 3D               [12]  666 	addc	a, r5
      0005B0 FD               [12]  667 	mov	r5,a
      0005B1 8C 82            [24]  668 	mov	dpl,r4
      0005B3 8D 83            [24]  669 	mov	dph,r5
      0005B5 8F F0            [24]  670 	mov	b,r7
      0005B7 12 0F C6         [24]  671 	lcall	__gptrget
      0005BA A3               [24]  672 	inc	dptr
      0005BB 12 0F C6         [24]  673 	lcall	__gptrget
      0005BE FB               [12]  674 	mov	r3,a
      0005BF 7A 00            [12]  675 	mov	r2,#0x00
      0005C1 53 03 0F         [24]  676 	anl	ar3,#0x0f
      0005C4 A8 63            [24]  677 	mov	r0,_scc_write_PARM_3
      0005C6 79 00            [12]  678 	mov	r1,#0x00
      0005C8 E8               [12]  679 	mov	a,r0
      0005C9 42 02            [12]  680 	orl	ar2,a
      0005CB E9               [12]  681 	mov	a,r1
      0005CC 42 03            [12]  682 	orl	ar3,a
      0005CE 8C 82            [24]  683 	mov	dpl,r4
      0005D0 8D 83            [24]  684 	mov	dph,r5
      0005D2 8F F0            [24]  685 	mov	b,r7
      0005D4 EA               [12]  686 	mov	a,r2
      0005D5 12 0F 20         [24]  687 	lcall	__gptrput
      0005D8 A3               [24]  688 	inc	dptr
      0005D9 EB               [12]  689 	mov	a,r3
      0005DA 12 0F 20         [24]  690 	lcall	__gptrput
      0005DD                        691 00114$:
                                    692 ;	src\scc.c:54: s->ch[ch].counter &= 0xFFFF0000u;
      0005DD EE               [12]  693 	mov	a,r6
      0005DE 75 F0 28         [24]  694 	mov	b,#0x28
      0005E1 A4               [48]  695 	mul	ab
      0005E2 FF               [12]  696 	mov	r7,a
      0005E3 25 64            [12]  697 	add	a, _scc_write_s_10000_36
      0005E5 FC               [12]  698 	mov	r4,a
      0005E6 E4               [12]  699 	clr	a
      0005E7 35 65            [12]  700 	addc	a, (_scc_write_s_10000_36 + 1)
      0005E9 FD               [12]  701 	mov	r5,a
      0005EA AE 66            [24]  702 	mov	r6,(_scc_write_s_10000_36 + 2)
      0005EC 8C 82            [24]  703 	mov	dpl,r4
      0005EE 8D 83            [24]  704 	mov	dph,r5
      0005F0 8E F0            [24]  705 	mov	b,r6
      0005F2 12 0F C6         [24]  706 	lcall	__gptrget
      0005F5 A3               [24]  707 	inc	dptr
      0005F6 12 0F C6         [24]  708 	lcall	__gptrget
      0005F9 A3               [24]  709 	inc	dptr
      0005FA 12 0F C6         [24]  710 	lcall	__gptrget
      0005FD FA               [12]  711 	mov	r2,a
      0005FE A3               [24]  712 	inc	dptr
      0005FF 12 0F C6         [24]  713 	lcall	__gptrget
      000602 FB               [12]  714 	mov	r3,a
      000603 78 00            [12]  715 	mov	r0,#0x00
      000605 79 00            [12]  716 	mov	r1,#0x00
      000607 8C 82            [24]  717 	mov	dpl,r4
      000609 8D 83            [24]  718 	mov	dph,r5
      00060B 8E F0            [24]  719 	mov	b,r6
      00060D E8               [12]  720 	mov	a,r0
      00060E 12 0F 20         [24]  721 	lcall	__gptrput
      000611 A3               [24]  722 	inc	dptr
      000612 E9               [12]  723 	mov	a,r1
      000613 12 0F 20         [24]  724 	lcall	__gptrput
      000616 A3               [24]  725 	inc	dptr
      000617 EA               [12]  726 	mov	a,r2
      000618 12 0F 20         [24]  727 	lcall	__gptrput
      00061B A3               [24]  728 	inc	dptr
      00061C EB               [12]  729 	mov	a,r3
      00061D 12 0F 20         [24]  730 	lcall	__gptrput
                                    731 ;	src\scc.c:55: if (s->test & 0x20)
      000620 74 D1            [12]  732 	mov	a,#0xd1
      000622 25 64            [12]  733 	add	a, _scc_write_s_10000_36
      000624 F9               [12]  734 	mov	r1,a
      000625 E4               [12]  735 	clr	a
      000626 35 65            [12]  736 	addc	a, (_scc_write_s_10000_36 + 1)
      000628 FA               [12]  737 	mov	r2,a
      000629 AB 66            [24]  738 	mov	r3,(_scc_write_s_10000_36 + 2)
      00062B 89 82            [24]  739 	mov	dpl,r1
      00062D 8A 83            [24]  740 	mov	dph,r2
      00062F 8B F0            [24]  741 	mov	b,r3
      000631 12 0F C6         [24]  742 	lcall	__gptrget
      000634 30 E5 17         [24]  743 	jnb	acc.5,00118$
                                    744 ;	src\scc.c:56: s->ch[ch].counter = 0xFFFFFFFF;
      000637 8C 82            [24]  745 	mov	dpl,r4
      000639 8D 83            [24]  746 	mov	dph,r5
      00063B 8E F0            [24]  747 	mov	b,r6
      00063D 74 FF            [12]  748 	mov	a,#0xff
      00063F 12 0F 20         [24]  749 	lcall	__gptrput
      000642 A3               [24]  750 	inc	dptr
      000643 12 0F 20         [24]  751 	lcall	__gptrput
      000646 A3               [24]  752 	inc	dptr
      000647 12 0F 20         [24]  753 	lcall	__gptrput
      00064A A3               [24]  754 	inc	dptr
      00064B 02 0F 20         [24]  755 	ljmp	__gptrput
      00064E                        756 00118$:
                                    757 ;	src\scc.c:57: else if (s->ch[ch].frequency < 9)
      00064E EF               [12]  758 	mov	a,r7
      00064F 25 64            [12]  759 	add	a, _scc_write_s_10000_36
      000651 FD               [12]  760 	mov	r5,a
      000652 E4               [12]  761 	clr	a
      000653 35 65            [12]  762 	addc	a, (_scc_write_s_10000_36 + 1)
      000655 FE               [12]  763 	mov	r6,a
      000656 AF 66            [24]  764 	mov	r7,(_scc_write_s_10000_36 + 2)
      000658 74 04            [12]  765 	mov	a,#0x04
      00065A 2D               [12]  766 	add	a, r5
      00065B FA               [12]  767 	mov	r2,a
      00065C E4               [12]  768 	clr	a
      00065D 3E               [12]  769 	addc	a, r6
      00065E FB               [12]  770 	mov	r3,a
      00065F 8F 04            [24]  771 	mov	ar4,r7
      000661 8A 82            [24]  772 	mov	dpl,r2
      000663 8B 83            [24]  773 	mov	dph,r3
      000665 8C F0            [24]  774 	mov	b,r4
      000667 12 0F C6         [24]  775 	lcall	__gptrget
      00066A FA               [12]  776 	mov	r2,a
      00066B A3               [24]  777 	inc	dptr
      00066C 12 0F C6         [24]  778 	lcall	__gptrget
      00066F FB               [12]  779 	mov	r3,a
      000670 C3               [12]  780 	clr	c
      000671 EA               [12]  781 	mov	a,r2
      000672 94 09            [12]  782 	subb	a,#0x09
      000674 EB               [12]  783 	mov	a,r3
      000675 94 00            [12]  784 	subb	a,#0x00
      000677 40 01            [24]  785 	jc	00232$
      000679 22               [24]  786 	ret
      00067A                        787 00232$:
                                    788 ;	src\scc.c:58: s->ch[ch].counter |= ((1 << SCC_FREQ_BITS) - 1);
      00067A 8D 82            [24]  789 	mov	dpl,r5
      00067C 8E 83            [24]  790 	mov	dph,r6
      00067E 8F F0            [24]  791 	mov	b,r7
      000680 74 FF            [12]  792 	mov	a,#0xff
      000682 12 0F 20         [24]  793 	lcall	__gptrput
      000685 A3               [24]  794 	inc	dptr
      000686 12 0F 20         [24]  795 	lcall	__gptrput
      000689 A3               [24]  796 	inc	dptr
      00068A 12 0F 20         [24]  797 	lcall	__gptrput
      00068D A3               [24]  798 	inc	dptr
                                    799 ;	src\scc.c:60: break;
      00068E 02 0F 20         [24]  800 	ljmp	__gptrput
                                    801 ;	src\scc.c:62: case 0x02: {
      000691                        802 00122$:
                                    803 ;	src\scc.c:63: ch = s->cur_reg & 0x07;
      000691 74 D2            [12]  804 	mov	a,#0xd2
      000693 25 64            [12]  805 	add	a, _scc_write_s_10000_36
      000695 FD               [12]  806 	mov	r5,a
      000696 E4               [12]  807 	clr	a
      000697 35 65            [12]  808 	addc	a, (_scc_write_s_10000_36 + 1)
      000699 FE               [12]  809 	mov	r6,a
      00069A AF 66            [24]  810 	mov	r7,(_scc_write_s_10000_36 + 2)
      00069C 8D 82            [24]  811 	mov	dpl,r5
      00069E 8E 83            [24]  812 	mov	dph,r6
      0006A0 8F F0            [24]  813 	mov	b,r7
      0006A2 12 0F C6         [24]  814 	lcall	__gptrget
      0006A5 FD               [12]  815 	mov	r5,a
      0006A6 74 07            [12]  816 	mov	a,#0x07
      0006A8 5D               [12]  817 	anl	a,r5
      0006A9 FF               [12]  818 	mov	r7,a
                                    819 ;	src\scc.c:64: if (ch < SCC_CHANS)
      0006AA BF 05 00         [24]  820 	cjne	r7,#0x05,00233$
      0006AD                        821 00233$:
      0006AD 40 01            [24]  822 	jc	00234$
      0006AF 22               [24]  823 	ret
      0006B0                        824 00234$:
                                    825 ;	src\scc.c:65: s->ch[ch].volume = data & 0x0F;
      0006B0 EF               [12]  826 	mov	a,r7
      0006B1 75 F0 28         [24]  827 	mov	b,#0x28
      0006B4 A4               [48]  828 	mul	ab
      0006B5 25 64            [12]  829 	add	a, _scc_write_s_10000_36
      0006B7 FD               [12]  830 	mov	r5,a
      0006B8 E4               [12]  831 	clr	a
      0006B9 35 65            [12]  832 	addc	a,(_scc_write_s_10000_36 + 1)
      0006BB FE               [12]  833 	mov	r6,a
      0006BC AF 66            [24]  834 	mov	r7,(_scc_write_s_10000_36 + 2)
      0006BE 74 06            [12]  835 	mov	a,#0x06
      0006C0 2D               [12]  836 	add	a, r5
      0006C1 FD               [12]  837 	mov	r5,a
      0006C2 E4               [12]  838 	clr	a
      0006C3 3E               [12]  839 	addc	a, r6
      0006C4 FE               [12]  840 	mov	r6,a
      0006C5 E5 63            [12]  841 	mov	a,_scc_write_PARM_3
      0006C7 54 0F            [12]  842 	anl	a,#0x0f
      0006C9 8D 82            [24]  843 	mov	dpl,r5
      0006CB 8E 83            [24]  844 	mov	dph,r6
      0006CD 8F F0            [24]  845 	mov	b,r7
                                    846 ;	src\scc.c:66: break;
                                    847 ;	src\scc.c:69: for (ch = 0; ch < SCC_CHANS; ch++)
      0006CF 02 0F 20         [24]  848 	ljmp	__gptrput
      0006D2                        849 00146$:
      0006D2 7F 00            [12]  850 	mov	r7,#0x00
      0006D4                        851 00132$:
                                    852 ;	src\scc.c:70: s->ch[ch].key = (data >> ch) & 1;
      0006D4 EF               [12]  853 	mov	a,r7
      0006D5 75 F0 28         [24]  854 	mov	b,#0x28
      0006D8 A4               [48]  855 	mul	ab
      0006D9 25 64            [12]  856 	add	a, _scc_write_s_10000_36
      0006DB FC               [12]  857 	mov	r4,a
      0006DC E4               [12]  858 	clr	a
      0006DD 35 65            [12]  859 	addc	a,(_scc_write_s_10000_36 + 1)
      0006DF FD               [12]  860 	mov	r5,a
      0006E0 AE 66            [24]  861 	mov	r6,(_scc_write_s_10000_36 + 2)
      0006E2 74 07            [12]  862 	mov	a,#0x07
      0006E4 2C               [12]  863 	add	a, r4
      0006E5 FC               [12]  864 	mov	r4,a
      0006E6 E4               [12]  865 	clr	a
      0006E7 3D               [12]  866 	addc	a, r5
      0006E8 FD               [12]  867 	mov	r5,a
      0006E9 8F F0            [24]  868 	mov	b,r7
      0006EB 05 F0            [12]  869 	inc	b
      0006ED E5 63            [12]  870 	mov	a,_scc_write_PARM_3
      0006EF 80 02            [24]  871 	sjmp	00236$
      0006F1                        872 00235$:
      0006F1 C3               [12]  873 	clr	c
      0006F2 13               [12]  874 	rrc	a
      0006F3                        875 00236$:
      0006F3 D5 F0 FB         [24]  876 	djnz	b,00235$
      0006F6 54 01            [12]  877 	anl	a,#0x01
      0006F8 8C 82            [24]  878 	mov	dpl,r4
      0006FA 8D 83            [24]  879 	mov	dph,r5
      0006FC 8E F0            [24]  880 	mov	b,r6
      0006FE 12 0F 20         [24]  881 	lcall	__gptrput
                                    882 ;	src\scc.c:69: for (ch = 0; ch < SCC_CHANS; ch++)
      000701 0F               [12]  883 	inc	r7
      000702 BF 05 00         [24]  884 	cjne	r7,#0x05,00237$
      000705                        885 00237$:
      000705 40 CD            [24]  886 	jc	00132$
                                    887 ;	src\scc.c:71: break;
                                    888 ;	src\scc.c:72: case 0x05:
      000707 22               [24]  889 	ret
      000708                        890 00127$:
                                    891 ;	src\scc.c:73: s->test = data;
      000708 74 D1            [12]  892 	mov	a,#0xd1
      00070A 25 64            [12]  893 	add	a, _scc_write_s_10000_36
      00070C FD               [12]  894 	mov	r5,a
      00070D E4               [12]  895 	clr	a
      00070E 35 65            [12]  896 	addc	a, (_scc_write_s_10000_36 + 1)
      000710 FE               [12]  897 	mov	r6,a
      000711 AF 66            [24]  898 	mov	r7,(_scc_write_s_10000_36 + 2)
      000713 8D 82            [24]  899 	mov	dpl,r5
      000715 8E 83            [24]  900 	mov	dph,r6
      000717 8F F0            [24]  901 	mov	b,r7
      000719 E5 63            [12]  902 	mov	a,_scc_write_PARM_3
                                    903 ;	src\scc.c:75: }
      00071B 02 0F 20         [24]  904 	ljmp	__gptrput
      00071E                        905 00130$:
                                    906 ;	src\scc.c:77: s->cur_reg = data;
      00071E 74 D2            [12]  907 	mov	a,#0xd2
      000720 25 64            [12]  908 	add	a, _scc_write_s_10000_36
      000722 FD               [12]  909 	mov	r5,a
      000723 E4               [12]  910 	clr	a
      000724 35 65            [12]  911 	addc	a, (_scc_write_s_10000_36 + 1)
      000726 FE               [12]  912 	mov	r6,a
      000727 AF 66            [24]  913 	mov	r7,(_scc_write_s_10000_36 + 2)
      000729 8D 82            [24]  914 	mov	dpl,r5
      00072B 8E 83            [24]  915 	mov	dph,r6
      00072D 8F F0            [24]  916 	mov	b,r7
      00072F E5 63            [12]  917 	mov	a,_scc_write_PARM_3
                                    918 ;	src\scc.c:79: }
      000731 02 0F 20         [24]  919 	ljmp	__gptrput
                                    920 ;------------------------------------------------------------
                                    921 ;Allocation info for local variables in function 'scc_render'
                                    922 ;------------------------------------------------------------
                                    923 ;s                         Allocated with name '_scc_render_s_10000_50'
                                    924 ;mix                       Allocated with name '_scc_render_mix_10000_51'
                                    925 ;i                         Allocated with name '_scc_render_i_10000_51'
                                    926 ;c                         Allocated with name '_scc_render_c_30000_53'
                                    927 ;step                      Allocated with name '_scc_render_step_40000_54'
                                    928 ;offs                      Allocated to registers r4 r5 r6 
                                    929 ;smpl                      Allocated to registers r6 r7 
                                    930 ;sloc0                     Allocated with name '_scc_render_sloc0_1_0'
                                    931 ;sloc1                     Allocated with name '_scc_render_sloc1_1_0'
                                    932 ;sloc2                     Allocated with name '_scc_render_sloc2_1_0'
                                    933 ;------------------------------------------------------------
                                    934 ;	src\scc.c:81: int8_t scc_render(scc_state_t *s) {
                                    935 ;	-----------------------------------------
                                    936 ;	 function scc_render
                                    937 ;	-----------------------------------------
      000734                        938 _scc_render:
      000734 85 82 28         [24]  939 	mov	_scc_render_s_10000_50,dpl
      000737 85 83 29         [24]  940 	mov	(_scc_render_s_10000_50 + 1),dph
      00073A 85 F0 2A         [24]  941 	mov	(_scc_render_s_10000_50 + 2),b
                                    942 ;	src\scc.c:82: int16_t mix = 0;
      00073D E4               [12]  943 	clr	a
      00073E F5 2B            [12]  944 	mov	_scc_render_mix_10000_51,a
      000740 F5 2C            [12]  945 	mov	(_scc_render_mix_10000_51 + 1),a
                                    946 ;	src\scc.c:84: for (i = 0; i < SCC_CHANS; i++) {
      000742 74 CC            [12]  947 	mov	a,#0xcc
      000744 25 28            [12]  948 	add	a, _scc_render_s_10000_50
      000746 F5 38            [12]  949 	mov	_scc_render_sloc1_1_0,a
      000748 E4               [12]  950 	clr	a
      000749 35 29            [12]  951 	addc	a, (_scc_render_s_10000_50 + 1)
      00074B F5 39            [12]  952 	mov	(_scc_render_sloc1_1_0 + 1),a
      00074D 85 2A 3A         [24]  953 	mov	(_scc_render_sloc1_1_0 + 2),(_scc_render_s_10000_50 + 2)
      000750 74 C8            [12]  954 	mov	a,#0xc8
      000752 25 28            [12]  955 	add	a, _scc_render_s_10000_50
      000754 F5 35            [12]  956 	mov	_scc_render_sloc0_1_0,a
      000756 E4               [12]  957 	clr	a
      000757 35 29            [12]  958 	addc	a, (_scc_render_s_10000_50 + 1)
      000759 F5 36            [12]  959 	mov	(_scc_render_sloc0_1_0 + 1),a
      00075B 85 2A 37         [24]  960 	mov	(_scc_render_sloc0_1_0 + 2),(_scc_render_s_10000_50 + 2)
      00075E 75 2D 00         [24]  961 	mov	_scc_render_i_10000_51,#0x00
      000761                        962 00110$:
                                    963 ;	src\scc.c:85: scc_channel_t *c = &s->ch[i];
      000761 E5 2D            [12]  964 	mov	a,_scc_render_i_10000_51
      000763 75 F0 28         [24]  965 	mov	b,#0x28
      000766 A4               [48]  966 	mul	ab
      000767 25 28            [12]  967 	add	a, _scc_render_s_10000_50
      000769 F5 2E            [12]  968 	mov	_scc_render_c_30000_53,a
      00076B E4               [12]  969 	clr	a
      00076C 35 29            [12]  970 	addc	a,(_scc_render_s_10000_50 + 1)
      00076E F5 2F            [12]  971 	mov	(_scc_render_c_30000_53 + 1),a
      000770 85 2A 30         [24]  972 	mov	(_scc_render_c_30000_53 + 2),(_scc_render_s_10000_50 + 2)
                                    973 ;	src\scc.c:86: if (c->frequency > 8) {
      000773 74 04            [12]  974 	mov	a,#0x04
      000775 25 2E            [12]  975 	add	a, _scc_render_c_30000_53
      000777 FB               [12]  976 	mov	r3,a
      000778 E4               [12]  977 	clr	a
      000779 35 2F            [12]  978 	addc	a, (_scc_render_c_30000_53 + 1)
      00077B FC               [12]  979 	mov	r4,a
      00077C AD 30            [24]  980 	mov	r5,(_scc_render_c_30000_53 + 2)
      00077E 8B 82            [24]  981 	mov	dpl,r3
      000780 8C 83            [24]  982 	mov	dph,r4
      000782 8D F0            [24]  983 	mov	b,r5
      000784 12 0F C6         [24]  984 	lcall	__gptrget
      000787 FB               [12]  985 	mov	r3,a
      000788 A3               [24]  986 	inc	dptr
      000789 12 0F C6         [24]  987 	lcall	__gptrget
      00078C FC               [12]  988 	mov	r4,a
      00078D C3               [12]  989 	clr	c
      00078E 74 08            [12]  990 	mov	a,#0x08
      000790 9B               [12]  991 	subb	a,r3
      000791 E4               [12]  992 	clr	a
      000792 9C               [12]  993 	subb	a,r4
      000793 40 03            [24]  994 	jc	00157$
      000795 02 08 E4         [24]  995 	ljmp	00111$
      000798                        996 00157$:
                                    997 ;	src\scc.c:91: step = s->clock_factor / ((uint32_t)(c->frequency + 1) * s->rate);
      000798 85 38 82         [24]  998 	mov	dpl,_scc_render_sloc1_1_0
      00079B 85 39 83         [24]  999 	mov	dph,(_scc_render_sloc1_1_0 + 1)
      00079E 85 3A F0         [24] 1000 	mov	b,(_scc_render_sloc1_1_0 + 2)
      0007A1 12 0F C6         [24] 1001 	lcall	__gptrget
      0007A4 F5 3B            [12] 1002 	mov	_scc_render_sloc2_1_0,a
      0007A6 A3               [24] 1003 	inc	dptr
      0007A7 12 0F C6         [24] 1004 	lcall	__gptrget
      0007AA F5 3C            [12] 1005 	mov	(_scc_render_sloc2_1_0 + 1),a
      0007AC A3               [24] 1006 	inc	dptr
      0007AD 12 0F C6         [24] 1007 	lcall	__gptrget
      0007B0 F5 3D            [12] 1008 	mov	(_scc_render_sloc2_1_0 + 2),a
      0007B2 A3               [24] 1009 	inc	dptr
      0007B3 12 0F C6         [24] 1010 	lcall	__gptrget
      0007B6 F5 3E            [12] 1011 	mov	(_scc_render_sloc2_1_0 + 3),a
      0007B8 0B               [12] 1012 	inc	r3
      0007B9 BB 00 01         [24] 1013 	cjne	r3,#0x00,00158$
      0007BC 0C               [12] 1014 	inc	r4
      0007BD                       1015 00158$:
      0007BD 7E 00            [12] 1016 	mov	r6,#0x00
      0007BF 7F 00            [12] 1017 	mov	r7,#0x00
      0007C1 85 35 82         [24] 1018 	mov	dpl,_scc_render_sloc0_1_0
      0007C4 85 36 83         [24] 1019 	mov	dph,(_scc_render_sloc0_1_0 + 1)
      0007C7 85 37 F0         [24] 1020 	mov	b,(_scc_render_sloc0_1_0 + 2)
      0007CA 12 0F C6         [24] 1021 	lcall	__gptrget
      0007CD F5 62            [12] 1022 	mov	__mullong_PARM_2,a
      0007CF A3               [24] 1023 	inc	dptr
      0007D0 12 0F C6         [24] 1024 	lcall	__gptrget
      0007D3 F5 63            [12] 1025 	mov	(__mullong_PARM_2 + 1),a
      0007D5 A3               [24] 1026 	inc	dptr
      0007D6 12 0F C6         [24] 1027 	lcall	__gptrget
      0007D9 F5 64            [12] 1028 	mov	(__mullong_PARM_2 + 2),a
      0007DB A3               [24] 1029 	inc	dptr
      0007DC 12 0F C6         [24] 1030 	lcall	__gptrget
      0007DF F5 65            [12] 1031 	mov	(__mullong_PARM_2 + 3),a
      0007E1 8B 82            [24] 1032 	mov	dpl, r3
      0007E3 8C 83            [24] 1033 	mov	dph, r4
      0007E5 8E F0            [24] 1034 	mov	b, r6
      0007E7 EF               [12] 1035 	mov	a, r7
      0007E8 12 0F 58         [24] 1036 	lcall	__mullong
      0007EB 85 82 62         [24] 1037 	mov	__divulong_PARM_2,dpl
      0007EE 85 83 63         [24] 1038 	mov	(__divulong_PARM_2 + 1),dph
      0007F1 85 F0 64         [24] 1039 	mov	(__divulong_PARM_2 + 2),b
      0007F4 F5 65            [12] 1040 	mov	(__divulong_PARM_2 + 3),a
                                   1041 ;	src\scc.c:92: c->counter += step;
      0007F6 85 3B 82         [24] 1042 	mov	dpl, _scc_render_sloc2_1_0
      0007F9 85 3C 83         [24] 1043 	mov	dph, (_scc_render_sloc2_1_0 + 1)
      0007FC 85 3D F0         [24] 1044 	mov	b, (_scc_render_sloc2_1_0 + 2)
      0007FF E5 3E            [12] 1045 	mov	a, (_scc_render_sloc2_1_0 + 3)
      000801 12 09 42         [24] 1046 	lcall	__divulong
      000804 85 82 31         [24] 1047 	mov	_scc_render_step_40000_54,dpl
      000807 85 83 32         [24] 1048 	mov	(_scc_render_step_40000_54 + 1),dph
      00080A 85 F0 33         [24] 1049 	mov	(_scc_render_step_40000_54 + 2),b
      00080D F5 34            [12] 1050 	mov	(_scc_render_step_40000_54 + 3),a
      00080F 85 2E 82         [24] 1051 	mov	dpl,_scc_render_c_30000_53
      000812 85 2F 83         [24] 1052 	mov	dph,(_scc_render_c_30000_53 + 1)
      000815 85 30 F0         [24] 1053 	mov	b,(_scc_render_c_30000_53 + 2)
      000818 12 0F C6         [24] 1054 	lcall	__gptrget
      00081B FB               [12] 1055 	mov	r3,a
      00081C A3               [24] 1056 	inc	dptr
      00081D 12 0F C6         [24] 1057 	lcall	__gptrget
      000820 FA               [12] 1058 	mov	r2,a
      000821 A3               [24] 1059 	inc	dptr
      000822 12 0F C6         [24] 1060 	lcall	__gptrget
      000825 FE               [12] 1061 	mov	r6,a
      000826 A3               [24] 1062 	inc	dptr
      000827 12 0F C6         [24] 1063 	lcall	__gptrget
      00082A FF               [12] 1064 	mov	r7,a
      00082B E5 31            [12] 1065 	mov	a,_scc_render_step_40000_54
      00082D 2B               [12] 1066 	add	a, r3
      00082E FB               [12] 1067 	mov	r3,a
      00082F E5 32            [12] 1068 	mov	a,(_scc_render_step_40000_54 + 1)
      000831 3A               [12] 1069 	addc	a, r2
      000832 FA               [12] 1070 	mov	r2,a
      000833 E5 33            [12] 1071 	mov	a,(_scc_render_step_40000_54 + 2)
      000835 3E               [12] 1072 	addc	a, r6
      000836 FE               [12] 1073 	mov	r6,a
      000837 E5 34            [12] 1074 	mov	a,(_scc_render_step_40000_54 + 3)
      000839 3F               [12] 1075 	addc	a, r7
      00083A FF               [12] 1076 	mov	r7,a
      00083B 85 2E 82         [24] 1077 	mov	dpl,_scc_render_c_30000_53
      00083E 85 2F 83         [24] 1078 	mov	dph,(_scc_render_c_30000_53 + 1)
      000841 85 30 F0         [24] 1079 	mov	b,(_scc_render_c_30000_53 + 2)
      000844 EB               [12] 1080 	mov	a,r3
      000845 12 0F 20         [24] 1081 	lcall	__gptrput
      000848 A3               [24] 1082 	inc	dptr
      000849 EA               [12] 1083 	mov	a,r2
      00084A 12 0F 20         [24] 1084 	lcall	__gptrput
      00084D A3               [24] 1085 	inc	dptr
      00084E EE               [12] 1086 	mov	a,r6
      00084F 12 0F 20         [24] 1087 	lcall	__gptrput
      000852 A3               [24] 1088 	inc	dptr
      000853 EF               [12] 1089 	mov	a,r7
      000854 12 0F 20         [24] 1090 	lcall	__gptrput
                                   1091 ;	src\scc.c:93: if (c->key) {
      000857 74 07            [12] 1092 	mov	a,#0x07
      000859 25 2E            [12] 1093 	add	a, _scc_render_c_30000_53
      00085B FD               [12] 1094 	mov	r5,a
      00085C E4               [12] 1095 	clr	a
      00085D 35 2F            [12] 1096 	addc	a, (_scc_render_c_30000_53 + 1)
      00085F FE               [12] 1097 	mov	r6,a
      000860 AF 30            [24] 1098 	mov	r7,(_scc_render_c_30000_53 + 2)
      000862 8D 82            [24] 1099 	mov	dpl,r5
      000864 8E 83            [24] 1100 	mov	dph,r6
      000866 8F F0            [24] 1101 	mov	b,r7
      000868 12 0F C6         [24] 1102 	lcall	__gptrget
      00086B 60 77            [24] 1103 	jz	00111$
                                   1104 ;	src\scc.c:94: offs = (c->counter >> SCC_FREQ_BITS) & 0x1F;
      00086D 85 2E 82         [24] 1105 	mov	dpl,_scc_render_c_30000_53
      000870 85 2F 83         [24] 1106 	mov	dph,(_scc_render_c_30000_53 + 1)
      000873 85 30 F0         [24] 1107 	mov	b,(_scc_render_c_30000_53 + 2)
      000876 12 0F C6         [24] 1108 	lcall	__gptrget
      000879 A3               [24] 1109 	inc	dptr
      00087A 12 0F C6         [24] 1110 	lcall	__gptrget
      00087D A3               [24] 1111 	inc	dptr
      00087E 12 0F C6         [24] 1112 	lcall	__gptrget
      000881 FE               [12] 1113 	mov	r6,a
      000882 A3               [24] 1114 	inc	dptr
      000883 12 0F C6         [24] 1115 	lcall	__gptrget
      000886 FF               [12] 1116 	mov	r7,a
      000887 8E 04            [24] 1117 	mov	ar4,r6
      000889 8F 05            [24] 1118 	mov	ar5,r7
      00088B 53 04 1F         [24] 1119 	anl	ar4,#0x1f
                                   1120 ;	src\scc.c:95: smpl = (int16_t)c->waveram[offs] * c->volume;
      00088E E4               [12] 1121 	clr	a
      00088F 74 08            [12] 1122 	mov	a,#0x08
      000891 25 2E            [12] 1123 	add	a, _scc_render_c_30000_53
      000893 FA               [12] 1124 	mov	r2,a
      000894 E4               [12] 1125 	clr	a
      000895 35 2F            [12] 1126 	addc	a, (_scc_render_c_30000_53 + 1)
      000897 E4               [12] 1127 	clr	a
      000898 35 30            [12] 1128 	addc	a, (_scc_render_c_30000_53 + 2)
      00089A EC               [12] 1129 	mov	a,r4
      00089B 2A               [12] 1130 	add	a, r2
      00089C F9               [12] 1131 	mov	r1,a
      00089D E7               [12] 1132 	mov	a,@r1
      00089E FF               [12] 1133 	mov	r7,a
      00089F 33               [12] 1134 	rlc	a
      0008A0 95 E0            [12] 1135 	subb	a,acc
      0008A2 FE               [12] 1136 	mov	r6,a
      0008A3 74 06            [12] 1137 	mov	a,#0x06
      0008A5 25 2E            [12] 1138 	add	a, _scc_render_c_30000_53
      0008A7 FB               [12] 1139 	mov	r3,a
      0008A8 E4               [12] 1140 	clr	a
      0008A9 35 2F            [12] 1141 	addc	a, (_scc_render_c_30000_53 + 1)
      0008AB FC               [12] 1142 	mov	r4,a
      0008AC AD 30            [24] 1143 	mov	r5,(_scc_render_c_30000_53 + 2)
      0008AE 8B 82            [24] 1144 	mov	dpl,r3
      0008B0 8C 83            [24] 1145 	mov	dph,r4
      0008B2 8D F0            [24] 1146 	mov	b,r5
      0008B4 12 0F C6         [24] 1147 	lcall	__gptrget
      0008B7 FB               [12] 1148 	mov	r3,a
      0008B8 8B 62            [24] 1149 	mov	__mulint_PARM_2,r3
      0008BA 75 63 00         [24] 1150 	mov	(__mulint_PARM_2 + 1),#0x00
                                   1151 ;	src\scc.c:96: smpl >>= 4;
      0008BD 8F 82            [24] 1152 	mov	dpl, r7
      0008BF 8E 83            [24] 1153 	mov	dph, r6
      0008C1 12 0F 3B         [24] 1154 	lcall	__mulint
      0008C4 AE 82            [24] 1155 	mov	r6, dpl
      0008C6 E5 83            [12] 1156 	mov	a,dph
      0008C8 C4               [12] 1157 	swap	a
      0008C9 CE               [12] 1158 	xch	a,r6
      0008CA C4               [12] 1159 	swap	a
      0008CB 54 0F            [12] 1160 	anl	a,#0x0f
      0008CD 6E               [12] 1161 	xrl	a,r6
      0008CE CE               [12] 1162 	xch	a,r6
      0008CF 54 0F            [12] 1163 	anl	a,#0x0f
      0008D1 CE               [12] 1164 	xch	a,r6
      0008D2 6E               [12] 1165 	xrl	a,r6
      0008D3 CE               [12] 1166 	xch	a,r6
      0008D4 30 E3 02         [24] 1167 	jnb	acc.3,00160$
      0008D7 44 F0            [12] 1168 	orl	a,#0xfffffff0
      0008D9                       1169 00160$:
      0008D9 FF               [12] 1170 	mov	r7,a
                                   1171 ;	src\scc.c:97: mix += smpl;
      0008DA EE               [12] 1172 	mov	a,r6
      0008DB 25 2B            [12] 1173 	add	a, _scc_render_mix_10000_51
      0008DD F5 2B            [12] 1174 	mov	_scc_render_mix_10000_51,a
      0008DF EF               [12] 1175 	mov	a,r7
      0008E0 35 2C            [12] 1176 	addc	a, (_scc_render_mix_10000_51 + 1)
      0008E2 F5 2C            [12] 1177 	mov	(_scc_render_mix_10000_51 + 1),a
      0008E4                       1178 00111$:
                                   1179 ;	src\scc.c:84: for (i = 0; i < SCC_CHANS; i++) {
      0008E4 05 2D            [12] 1180 	inc	_scc_render_i_10000_51
      0008E6 74 FB            [12] 1181 	mov	a,#0x100 - 0x05
      0008E8 25 2D            [12] 1182 	add	a,_scc_render_i_10000_51
      0008EA 40 03            [24] 1183 	jc	00161$
      0008EC 02 07 61         [24] 1184 	ljmp	00110$
      0008EF                       1185 00161$:
                                   1186 ;	src\scc.c:101: if (mix > 127) mix = 127;
      0008EF AB 2B            [24] 1187 	mov	r3,_scc_render_mix_10000_51
      0008F1 AC 2C            [24] 1188 	mov	r4,(_scc_render_mix_10000_51 + 1)
      0008F3 C3               [12] 1189 	clr	c
      0008F4 74 7F            [12] 1190 	mov	a,#0x7f
      0008F6 9B               [12] 1191 	subb	a,r3
      0008F7 74 80            [12] 1192 	mov	a,#(0x00 ^ 0x80)
      0008F9 8C F0            [24] 1193 	mov	b,r4
      0008FB 63 F0 80         [24] 1194 	xrl	b,#0x80
      0008FE 95 F0            [12] 1195 	subb	a,b
      000900 50 06            [24] 1196 	jnc	00107$
      000902 75 2B 7F         [24] 1197 	mov	_scc_render_mix_10000_51,#0x7f
      000905 75 2C 00         [24] 1198 	mov	(_scc_render_mix_10000_51 + 1),#0x00
      000908                       1199 00107$:
                                   1200 ;	src\scc.c:102: if (mix < -128) mix = -128;
      000908 C3               [12] 1201 	clr	c
      000909 E5 2B            [12] 1202 	mov	a,_scc_render_mix_10000_51
      00090B 94 80            [12] 1203 	subb	a,#0x80
      00090D E5 2C            [12] 1204 	mov	a,(_scc_render_mix_10000_51 + 1)
      00090F 64 80            [12] 1205 	xrl	a,#0x80
      000911 94 7F            [12] 1206 	subb	a,#0x7f
      000913 50 06            [24] 1207 	jnc	00109$
      000915 75 2B 80         [24] 1208 	mov	_scc_render_mix_10000_51,#0x80
      000918 75 2C FF         [24] 1209 	mov	(_scc_render_mix_10000_51 + 1),#0xff
      00091B                       1210 00109$:
                                   1211 ;	src\scc.c:103: return (int8_t)mix;
      00091B 85 2B 82         [24] 1212 	mov	dpl,_scc_render_mix_10000_51
                                   1213 ;	src\scc.c:104: }
      00091E 22               [24] 1214 	ret
                                   1215 	.area CSEG    (CODE)
                                   1216 	.area CONST   (CODE)
                                   1217 	.area XINIT   (CODE)
                                   1218 	.area CABS    (ABS,CODE)
