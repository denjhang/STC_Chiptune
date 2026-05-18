                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ISO C Compiler 
                                      3 ; Version 4.4.0 #14620 (MINGW32)
                                      4 ;--------------------------------------------------------
                                      5 	.module pwm_audio
                                      6 	.optsdcc -mmcs51 --model-small
                                      7 	
                                      8 ;--------------------------------------------------------
                                      9 ; Public variables in this module
                                     10 ;--------------------------------------------------------
                                     11 	.globl _TIM_Timer3_Config
                                     12 	.globl _P77
                                     13 	.globl _P76
                                     14 	.globl _P75
                                     15 	.globl _P74
                                     16 	.globl _P73
                                     17 	.globl _P72
                                     18 	.globl _P71
                                     19 	.globl _P70
                                     20 	.globl _P67
                                     21 	.globl _P66
                                     22 	.globl _P65
                                     23 	.globl _P64
                                     24 	.globl _P63
                                     25 	.globl _P62
                                     26 	.globl _P61
                                     27 	.globl _P60
                                     28 	.globl _P
                                     29 	.globl _F1
                                     30 	.globl _OV
                                     31 	.globl _RS0
                                     32 	.globl _RS1
                                     33 	.globl _F0
                                     34 	.globl _AC
                                     35 	.globl _CY
                                     36 	.globl _P57
                                     37 	.globl _P56
                                     38 	.globl _P55
                                     39 	.globl _P54
                                     40 	.globl _P53
                                     41 	.globl _P52
                                     42 	.globl _P51
                                     43 	.globl _P50
                                     44 	.globl _P47
                                     45 	.globl _P46
                                     46 	.globl _P45
                                     47 	.globl _P44
                                     48 	.globl _P43
                                     49 	.globl _P42
                                     50 	.globl _P41
                                     51 	.globl _P40
                                     52 	.globl _PX0
                                     53 	.globl _PT0
                                     54 	.globl _PX1
                                     55 	.globl _PT1
                                     56 	.globl _PS
                                     57 	.globl _PADC
                                     58 	.globl _PLVD
                                     59 	.globl _PPCA
                                     60 	.globl _P37
                                     61 	.globl _P36
                                     62 	.globl _P35
                                     63 	.globl _P34
                                     64 	.globl _P33
                                     65 	.globl _P32
                                     66 	.globl _P31
                                     67 	.globl _P30
                                     68 	.globl _EX0
                                     69 	.globl _ET0
                                     70 	.globl _EX1
                                     71 	.globl _ET1
                                     72 	.globl _ES
                                     73 	.globl _EADC
                                     74 	.globl _ELVD
                                     75 	.globl _EA
                                     76 	.globl _P27
                                     77 	.globl _P26
                                     78 	.globl _P25
                                     79 	.globl _P24
                                     80 	.globl _P23
                                     81 	.globl _P22
                                     82 	.globl _P21
                                     83 	.globl _P20
                                     84 	.globl _RI
                                     85 	.globl _TI
                                     86 	.globl _RB8
                                     87 	.globl _TB8
                                     88 	.globl _REN
                                     89 	.globl _SM2
                                     90 	.globl _SM1
                                     91 	.globl _SM0
                                     92 	.globl _P17
                                     93 	.globl _P16
                                     94 	.globl _P15
                                     95 	.globl _P14
                                     96 	.globl _P13
                                     97 	.globl _P12
                                     98 	.globl _P11
                                     99 	.globl _P10
                                    100 	.globl _IT0
                                    101 	.globl _IE0
                                    102 	.globl _IT1
                                    103 	.globl _IE1
                                    104 	.globl _TR0
                                    105 	.globl _TF0
                                    106 	.globl _TR1
                                    107 	.globl _TF1
                                    108 	.globl _P07
                                    109 	.globl _P06
                                    110 	.globl _P05
                                    111 	.globl _P04
                                    112 	.globl _P03
                                    113 	.globl _P02
                                    114 	.globl _P01
                                    115 	.globl _P00
                                    116 	.globl _RSTCFG
                                    117 	.globl _USBADR
                                    118 	.globl _IAP_TPS
                                    119 	.globl _USBCON
                                    120 	.globl _AUXINTIF
                                    121 	.globl _IP3H
                                    122 	.globl _USBDAT
                                    123 	.globl _CMPCR2
                                    124 	.globl _CMPCR1
                                    125 	.globl _DPH1
                                    126 	.globl _DPL1
                                    127 	.globl _DPS
                                    128 	.globl _P7M0
                                    129 	.globl _P7M1
                                    130 	.globl _IP3
                                    131 	.globl _ADCCFG
                                    132 	.globl _USBCLK
                                    133 	.globl _VRTRIM
                                    134 	.globl _P7
                                    135 	.globl _B
                                    136 	.globl _P6
                                    137 	.globl _ACC
                                    138 	.globl _T2L
                                    139 	.globl _T2H
                                    140 	.globl _T3L
                                    141 	.globl _T3H
                                    142 	.globl _T4L
                                    143 	.globl _T4H
                                    144 	.globl _T4T3M
                                    145 	.globl _PSW
                                    146 	.globl _SPDAT
                                    147 	.globl _SPCTL
                                    148 	.globl _SPSTAT
                                    149 	.globl _P6M0
                                    150 	.globl _P6M1
                                    151 	.globl _P5M0
                                    152 	.globl _P5M1
                                    153 	.globl _P5
                                    154 	.globl _IAP_CONTR
                                    155 	.globl _IAP_TRIG
                                    156 	.globl _IAP_CMD
                                    157 	.globl _IAP_ADDRL
                                    158 	.globl _IAP_ADDRH
                                    159 	.globl _IAP_DATA
                                    160 	.globl _WDT_CONTR
                                    161 	.globl _P4
                                    162 	.globl _ADC_RESL
                                    163 	.globl _ADC_RES
                                    164 	.globl _ADC_CONTR
                                    165 	.globl _P_SW2
                                    166 	.globl _SADEN
                                    167 	.globl _IP
                                    168 	.globl _IPH
                                    169 	.globl _IP2H
                                    170 	.globl _IP2
                                    171 	.globl _P4M0
                                    172 	.globl _P4M1
                                    173 	.globl _P3M0
                                    174 	.globl _P3M1
                                    175 	.globl _P3
                                    176 	.globl _IE2
                                    177 	.globl _TA
                                    178 	.globl _S3BUF
                                    179 	.globl _S3CON
                                    180 	.globl _WKTCH
                                    181 	.globl _WKTCL
                                    182 	.globl _SADDR
                                    183 	.globl _IE
                                    184 	.globl _P_SW1
                                    185 	.globl _BUS_SPEED
                                    186 	.globl _P2
                                    187 	.globl _IRTRIM
                                    188 	.globl _LIRTRIM
                                    189 	.globl _IRCBAND
                                    190 	.globl _S2BUF
                                    191 	.globl _S2CON
                                    192 	.globl _SBUF
                                    193 	.globl _SCON
                                    194 	.globl _P2M0
                                    195 	.globl _P2M1
                                    196 	.globl _P0M0
                                    197 	.globl _P0M1
                                    198 	.globl _P1M0
                                    199 	.globl _P1M1
                                    200 	.globl _P1
                                    201 	.globl _INTCLKO
                                    202 	.globl _AUXR
                                    203 	.globl _TH1
                                    204 	.globl _TH0
                                    205 	.globl _TL1
                                    206 	.globl _TL0
                                    207 	.globl _TMOD
                                    208 	.globl _TCON
                                    209 	.globl _PCON
                                    210 	.globl _S4BUF
                                    211 	.globl _S4CON
                                    212 	.globl _DPH
                                    213 	.globl _DPL
                                    214 	.globl _SP
                                    215 	.globl _P0
                                    216 	.globl _pwm_audio_init
                                    217 	.globl _pwm_audio_set_sample
                                    218 ;--------------------------------------------------------
                                    219 ; special function registers
                                    220 ;--------------------------------------------------------
                                    221 	.area RSEG    (ABS,DATA)
      000000                        222 	.org 0x0000
                           000080   223 _P0	=	0x0080
                           000081   224 _SP	=	0x0081
                           000082   225 _DPL	=	0x0082
                           000083   226 _DPH	=	0x0083
                           000084   227 _S4CON	=	0x0084
                           000085   228 _S4BUF	=	0x0085
                           000087   229 _PCON	=	0x0087
                           000088   230 _TCON	=	0x0088
                           000089   231 _TMOD	=	0x0089
                           00008A   232 _TL0	=	0x008a
                           00008B   233 _TL1	=	0x008b
                           00008C   234 _TH0	=	0x008c
                           00008D   235 _TH1	=	0x008d
                           00008E   236 _AUXR	=	0x008e
                           00008F   237 _INTCLKO	=	0x008f
                           000090   238 _P1	=	0x0090
                           000091   239 _P1M1	=	0x0091
                           000092   240 _P1M0	=	0x0092
                           000093   241 _P0M1	=	0x0093
                           000094   242 _P0M0	=	0x0094
                           000095   243 _P2M1	=	0x0095
                           000096   244 _P2M0	=	0x0096
                           000098   245 _SCON	=	0x0098
                           000099   246 _SBUF	=	0x0099
                           00009A   247 _S2CON	=	0x009a
                           00009B   248 _S2BUF	=	0x009b
                           00009D   249 _IRCBAND	=	0x009d
                           00009E   250 _LIRTRIM	=	0x009e
                           00009F   251 _IRTRIM	=	0x009f
                           0000A0   252 _P2	=	0x00a0
                           0000A1   253 _BUS_SPEED	=	0x00a1
                           0000A2   254 _P_SW1	=	0x00a2
                           0000A8   255 _IE	=	0x00a8
                           0000A9   256 _SADDR	=	0x00a9
                           0000AA   257 _WKTCL	=	0x00aa
                           0000AB   258 _WKTCH	=	0x00ab
                           0000AC   259 _S3CON	=	0x00ac
                           0000AD   260 _S3BUF	=	0x00ad
                           0000AE   261 _TA	=	0x00ae
                           0000AF   262 _IE2	=	0x00af
                           0000B0   263 _P3	=	0x00b0
                           0000B1   264 _P3M1	=	0x00b1
                           0000B2   265 _P3M0	=	0x00b2
                           0000B3   266 _P4M1	=	0x00b3
                           0000B4   267 _P4M0	=	0x00b4
                           0000B5   268 _IP2	=	0x00b5
                           0000B6   269 _IP2H	=	0x00b6
                           0000B7   270 _IPH	=	0x00b7
                           0000B8   271 _IP	=	0x00b8
                           0000B9   272 _SADEN	=	0x00b9
                           0000BA   273 _P_SW2	=	0x00ba
                           0000BC   274 _ADC_CONTR	=	0x00bc
                           0000BD   275 _ADC_RES	=	0x00bd
                           0000BE   276 _ADC_RESL	=	0x00be
                           0000C0   277 _P4	=	0x00c0
                           0000C1   278 _WDT_CONTR	=	0x00c1
                           0000C2   279 _IAP_DATA	=	0x00c2
                           0000C3   280 _IAP_ADDRH	=	0x00c3
                           0000C4   281 _IAP_ADDRL	=	0x00c4
                           0000C5   282 _IAP_CMD	=	0x00c5
                           0000C6   283 _IAP_TRIG	=	0x00c6
                           0000C7   284 _IAP_CONTR	=	0x00c7
                           0000C8   285 _P5	=	0x00c8
                           0000C9   286 _P5M1	=	0x00c9
                           0000CA   287 _P5M0	=	0x00ca
                           0000CB   288 _P6M1	=	0x00cb
                           0000CC   289 _P6M0	=	0x00cc
                           0000CD   290 _SPSTAT	=	0x00cd
                           0000CE   291 _SPCTL	=	0x00ce
                           0000CF   292 _SPDAT	=	0x00cf
                           0000D0   293 _PSW	=	0x00d0
                           0000D1   294 _T4T3M	=	0x00d1
                           0000D2   295 _T4H	=	0x00d2
                           0000D3   296 _T4L	=	0x00d3
                           0000D4   297 _T3H	=	0x00d4
                           0000D5   298 _T3L	=	0x00d5
                           0000D6   299 _T2H	=	0x00d6
                           0000D7   300 _T2L	=	0x00d7
                           0000E0   301 _ACC	=	0x00e0
                           0000E8   302 _P6	=	0x00e8
                           0000F0   303 _B	=	0x00f0
                           0000F8   304 _P7	=	0x00f8
                           0000A6   305 _VRTRIM	=	0x00a6
                           0000DC   306 _USBCLK	=	0x00dc
                           0000DE   307 _ADCCFG	=	0x00de
                           0000DF   308 _IP3	=	0x00df
                           0000E1   309 _P7M1	=	0x00e1
                           0000E2   310 _P7M0	=	0x00e2
                           0000E3   311 _DPS	=	0x00e3
                           0000E4   312 _DPL1	=	0x00e4
                           0000E5   313 _DPH1	=	0x00e5
                           0000E6   314 _CMPCR1	=	0x00e6
                           0000E7   315 _CMPCR2	=	0x00e7
                           0000EC   316 _USBDAT	=	0x00ec
                           0000EE   317 _IP3H	=	0x00ee
                           0000EF   318 _AUXINTIF	=	0x00ef
                           0000F4   319 _USBCON	=	0x00f4
                           0000F5   320 _IAP_TPS	=	0x00f5
                           0000FC   321 _USBADR	=	0x00fc
                           0000FF   322 _RSTCFG	=	0x00ff
                                    323 ;--------------------------------------------------------
                                    324 ; special function bits
                                    325 ;--------------------------------------------------------
                                    326 	.area RSEG    (ABS,DATA)
      000000                        327 	.org 0x0000
                           000080   328 _P00	=	0x0080
                           000081   329 _P01	=	0x0081
                           000082   330 _P02	=	0x0082
                           000083   331 _P03	=	0x0083
                           000084   332 _P04	=	0x0084
                           000085   333 _P05	=	0x0085
                           000086   334 _P06	=	0x0086
                           000087   335 _P07	=	0x0087
                           00008F   336 _TF1	=	0x008f
                           00008E   337 _TR1	=	0x008e
                           00008D   338 _TF0	=	0x008d
                           00008C   339 _TR0	=	0x008c
                           00008B   340 _IE1	=	0x008b
                           00008A   341 _IT1	=	0x008a
                           000089   342 _IE0	=	0x0089
                           000088   343 _IT0	=	0x0088
                           000090   344 _P10	=	0x0090
                           000091   345 _P11	=	0x0091
                           000092   346 _P12	=	0x0092
                           000093   347 _P13	=	0x0093
                           000094   348 _P14	=	0x0094
                           000095   349 _P15	=	0x0095
                           000096   350 _P16	=	0x0096
                           000097   351 _P17	=	0x0097
                           00009F   352 _SM0	=	0x009f
                           00009E   353 _SM1	=	0x009e
                           00009D   354 _SM2	=	0x009d
                           00009C   355 _REN	=	0x009c
                           00009B   356 _TB8	=	0x009b
                           00009A   357 _RB8	=	0x009a
                           000099   358 _TI	=	0x0099
                           000098   359 _RI	=	0x0098
                           0000A0   360 _P20	=	0x00a0
                           0000A1   361 _P21	=	0x00a1
                           0000A2   362 _P22	=	0x00a2
                           0000A3   363 _P23	=	0x00a3
                           0000A4   364 _P24	=	0x00a4
                           0000A5   365 _P25	=	0x00a5
                           0000A6   366 _P26	=	0x00a6
                           0000A7   367 _P27	=	0x00a7
                           0000AF   368 _EA	=	0x00af
                           0000AE   369 _ELVD	=	0x00ae
                           0000AD   370 _EADC	=	0x00ad
                           0000AC   371 _ES	=	0x00ac
                           0000AB   372 _ET1	=	0x00ab
                           0000AA   373 _EX1	=	0x00aa
                           0000A9   374 _ET0	=	0x00a9
                           0000A8   375 _EX0	=	0x00a8
                           0000B0   376 _P30	=	0x00b0
                           0000B1   377 _P31	=	0x00b1
                           0000B2   378 _P32	=	0x00b2
                           0000B3   379 _P33	=	0x00b3
                           0000B4   380 _P34	=	0x00b4
                           0000B5   381 _P35	=	0x00b5
                           0000B6   382 _P36	=	0x00b6
                           0000B7   383 _P37	=	0x00b7
                           0000BF   384 _PPCA	=	0x00bf
                           0000BE   385 _PLVD	=	0x00be
                           0000BD   386 _PADC	=	0x00bd
                           0000BC   387 _PS	=	0x00bc
                           0000BB   388 _PT1	=	0x00bb
                           0000BA   389 _PX1	=	0x00ba
                           0000B9   390 _PT0	=	0x00b9
                           0000B8   391 _PX0	=	0x00b8
                           0000C0   392 _P40	=	0x00c0
                           0000C1   393 _P41	=	0x00c1
                           0000C2   394 _P42	=	0x00c2
                           0000C3   395 _P43	=	0x00c3
                           0000C4   396 _P44	=	0x00c4
                           0000C5   397 _P45	=	0x00c5
                           0000C6   398 _P46	=	0x00c6
                           0000C7   399 _P47	=	0x00c7
                           0000C8   400 _P50	=	0x00c8
                           0000C9   401 _P51	=	0x00c9
                           0000CA   402 _P52	=	0x00ca
                           0000CB   403 _P53	=	0x00cb
                           0000CC   404 _P54	=	0x00cc
                           0000CD   405 _P55	=	0x00cd
                           0000CE   406 _P56	=	0x00ce
                           0000CF   407 _P57	=	0x00cf
                           0000D7   408 _CY	=	0x00d7
                           0000D6   409 _AC	=	0x00d6
                           0000D5   410 _F0	=	0x00d5
                           0000D4   411 _RS1	=	0x00d4
                           0000D3   412 _RS0	=	0x00d3
                           0000D2   413 _OV	=	0x00d2
                           0000D1   414 _F1	=	0x00d1
                           0000D0   415 _P	=	0x00d0
                           0000E8   416 _P60	=	0x00e8
                           0000E9   417 _P61	=	0x00e9
                           0000EA   418 _P62	=	0x00ea
                           0000EB   419 _P63	=	0x00eb
                           0000EC   420 _P64	=	0x00ec
                           0000ED   421 _P65	=	0x00ed
                           0000EE   422 _P66	=	0x00ee
                           0000EF   423 _P67	=	0x00ef
                           0000F8   424 _P70	=	0x00f8
                           0000F9   425 _P71	=	0x00f9
                           0000FA   426 _P72	=	0x00fa
                           0000FB   427 _P73	=	0x00fb
                           0000FC   428 _P74	=	0x00fc
                           0000FD   429 _P75	=	0x00fd
                           0000FE   430 _P76	=	0x00fe
                           0000FF   431 _P77	=	0x00ff
                                    432 ;--------------------------------------------------------
                                    433 ; overlayable register banks
                                    434 ;--------------------------------------------------------
                                    435 	.area REG_BANK_0	(REL,OVR,DATA)
      000000                        436 	.ds 8
                                    437 ;--------------------------------------------------------
                                    438 ; internal ram data
                                    439 ;--------------------------------------------------------
                                    440 	.area DSEG    (DATA)
                                    441 ;--------------------------------------------------------
                                    442 ; overlayable items in internal ram
                                    443 ;--------------------------------------------------------
                                    444 	.area	OSEG    (OVR,DATA)
                                    445 ;--------------------------------------------------------
                                    446 ; indirectly addressable internal ram data
                                    447 ;--------------------------------------------------------
                                    448 	.area ISEG    (DATA)
                                    449 ;--------------------------------------------------------
                                    450 ; absolute internal ram data
                                    451 ;--------------------------------------------------------
                                    452 	.area IABS    (ABS,DATA)
                                    453 	.area IABS    (ABS,DATA)
                                    454 ;--------------------------------------------------------
                                    455 ; bit data
                                    456 ;--------------------------------------------------------
                                    457 	.area BSEG    (BIT)
                                    458 ;--------------------------------------------------------
                                    459 ; paged external ram data
                                    460 ;--------------------------------------------------------
                                    461 	.area PSEG    (PAG,XDATA)
                                    462 ;--------------------------------------------------------
                                    463 ; uninitialized external ram data
                                    464 ;--------------------------------------------------------
                                    465 	.area XSEG    (XDATA)
                                    466 ;--------------------------------------------------------
                                    467 ; absolute external ram data
                                    468 ;--------------------------------------------------------
                                    469 	.area XABS    (ABS,XDATA)
                                    470 ;--------------------------------------------------------
                                    471 ; initialized external ram data
                                    472 ;--------------------------------------------------------
                                    473 	.area XISEG   (XDATA)
                                    474 	.area HOME    (CODE)
                                    475 	.area GSINIT0 (CODE)
                                    476 	.area GSINIT1 (CODE)
                                    477 	.area GSINIT2 (CODE)
                                    478 	.area GSINIT3 (CODE)
                                    479 	.area GSINIT4 (CODE)
                                    480 	.area GSINIT5 (CODE)
                                    481 	.area GSINIT  (CODE)
                                    482 	.area GSFINAL (CODE)
                                    483 	.area CSEG    (CODE)
                                    484 ;--------------------------------------------------------
                                    485 ; global & static initialisations
                                    486 ;--------------------------------------------------------
                                    487 	.area HOME    (CODE)
                                    488 	.area GSINIT  (CODE)
                                    489 	.area GSFINAL (CODE)
                                    490 	.area GSINIT  (CODE)
                                    491 ;--------------------------------------------------------
                                    492 ; Home
                                    493 ;--------------------------------------------------------
                                    494 	.area HOME    (CODE)
                                    495 	.area HOME    (CODE)
                                    496 ;--------------------------------------------------------
                                    497 ; code
                                    498 ;--------------------------------------------------------
                                    499 	.area CSEG    (CODE)
                                    500 ;------------------------------------------------------------
                                    501 ;Allocation info for local variables in function 'pwm_audio_init'
                                    502 ;------------------------------------------------------------
                                    503 ;sample_rate               Allocated to registers r4 r5 r6 r7 
                                    504 ;------------------------------------------------------------
                                    505 ;	src\pwm_audio.c:4: void pwm_audio_init(uint32_t sample_rate) {
                                    506 ;	-----------------------------------------
                                    507 ;	 function pwm_audio_init
                                    508 ;	-----------------------------------------
      0001F1                        509 _pwm_audio_init:
                           000007   510 	ar7 = 0x07
                           000006   511 	ar6 = 0x06
                           000005   512 	ar5 = 0x05
                           000004   513 	ar4 = 0x04
                           000003   514 	ar3 = 0x03
                           000002   515 	ar2 = 0x02
                           000001   516 	ar1 = 0x01
                           000000   517 	ar0 = 0x00
      0001F1 AC 82            [24]  518 	mov	r4,dpl
      0001F3 AD 83            [24]  519 	mov	r5,dph
                                    520 ;	src\pwm_audio.c:6: GPIO_P2_SetMode(GPIO_Pin_0, GPIO_Mode_Output_PP);
      0001F5 74 FE            [12]  521 	mov	a,#0xfe
      0001F7 55 96            [12]  522 	anl	a,_P2M0
      0001F9 44 01            [12]  523 	orl	a,#0x01
      0001FB F5 96            [12]  524 	mov	_P2M0,a
      0001FD 53 95 FE         [24]  525 	anl	_P2M1,#0xfe
                                    526 ;	src\pwm_audio.c:9: PWMA_SetPrescaler(0);
      000200 43 BA 80         [24]  527 	orl	_P_SW2,#0x80
      000203 90 FE D0         [24]  528 	mov	dptr,#0xfed0
      000206 E4               [12]  529 	clr	a
      000207 F0               [24]  530 	movx	@dptr,a
      000208 A3               [24]  531 	inc	dptr
      000209 F0               [24]  532 	movx	@dptr,a
      00020A 53 BA 7F         [24]  533 	anl	_P_SW2,#0x7f
                                    534 ;	src\pwm_audio.c:10: PWMA_SetPeriod(255);
      00020D 43 BA 80         [24]  535 	orl	_P_SW2,#0x80
      000210 90 FE D2         [24]  536 	mov	dptr,#0xfed2
      000213 E4               [12]  537 	clr	a
      000214 F0               [24]  538 	movx	@dptr,a
      000215 A3               [24]  539 	inc	dptr
      000216 14               [12]  540 	dec	a
      000217 F0               [24]  541 	movx	@dptr,a
      000218 53 BA 7F         [24]  542 	anl	_P_SW2,#0x7f
                                    543 ;	src\pwm_audio.c:13: PWMA_PWM1_ConfigOutputMode(PWM_OutputMode_PWM_HighIfLess);
      00021B 43 BA 80         [24]  544 	orl	_P_SW2,#0x80
      00021E 90 FE C8         [24]  545 	mov	dptr,#0xfec8
      000221 E0               [24]  546 	movx	a,@dptr
      000222 FB               [12]  547 	mov	r3,a
      000223 74 8F            [12]  548 	mov	a,#0x8f
      000225 5B               [12]  549 	anl	a,r3
      000226 44 60            [12]  550 	orl	a,#0x60
      000228 F0               [24]  551 	movx	@dptr,a
      000229 53 BA 7F         [24]  552 	anl	_P_SW2,#0x7f
                                    553 ;	src\pwm_audio.c:14: PWMA_PWM1_SetPortDirection(PWMA_PortDirOut);
      00022C 43 BA 80         [24]  554 	orl	_P_SW2,#0x80
      00022F 90 FE C8         [24]  555 	mov	dptr,#0xfec8
      000232 E0               [24]  556 	movx	a,@dptr
      000233 54 FC            [12]  557 	anl	a,#0xfc
      000235 F0               [24]  558 	movx	@dptr,a
      000236 53 BA 7F         [24]  559 	anl	_P_SW2,#0x7f
                                    560 ;	src\pwm_audio.c:17: PWMA_SetPinOutputState(PWM_Pin_1, HAL_State_ON);
      000239 43 BA 80         [24]  561 	orl	_P_SW2,#0x80
      00023C 90 FE B1         [24]  562 	mov	dptr,#0xfeb1
      00023F E0               [24]  563 	movx	a,@dptr
      000240 FB               [12]  564 	mov	r3,a
      000241 74 FE            [12]  565 	mov	a,#0xfe
      000243 5B               [12]  566 	anl	a,r3
      000244 44 01            [12]  567 	orl	a,#0x01
      000246 F0               [24]  568 	movx	@dptr,a
      000247 53 BA 7F         [24]  569 	anl	_P_SW2,#0x7f
                                    570 ;	src\pwm_audio.c:18: PWMA_SetOverallState(HAL_State_ON);
      00024A 43 BA 80         [24]  571 	orl	_P_SW2,#0x80
      00024D 90 FE DD         [24]  572 	mov	dptr,#0xfedd
      000250 E0               [24]  573 	movx	a,@dptr
      000251 FB               [12]  574 	mov	r3,a
      000252 74 7F            [12]  575 	mov	a,#0x7f
      000254 5B               [12]  576 	anl	a,r3
      000255 44 80            [12]  577 	orl	a,#0x80
      000257 F0               [24]  578 	movx	@dptr,a
      000258 53 BA 7F         [24]  579 	anl	_P_SW2,#0x7f
                                    580 ;	src\pwm_audio.c:21: PWMA_SetCounterDirection(PWM_CounterDirection_Up);
      00025B 43 BA 80         [24]  581 	orl	_P_SW2,#0x80
      00025E 90 FE C0         [24]  582 	mov	dptr,#0xfec0
      000261 E0               [24]  583 	movx	a,@dptr
      000262 54 EF            [12]  584 	anl	a,#0xef
      000264 F0               [24]  585 	movx	@dptr,a
      000265 53 BA 7F         [24]  586 	anl	_P_SW2,#0x7f
                                    587 ;	src\pwm_audio.c:22: PWMA_SetEdgeAlignment(PWM_EdgeAlignment_Side);
      000268 43 BA 80         [24]  588 	orl	_P_SW2,#0x80
      00026B 90 FE C0         [24]  589 	mov	dptr,#0xfec0
      00026E E0               [24]  590 	movx	a,@dptr
      00026F 54 9F            [12]  591 	anl	a,#0x9f
      000271 F0               [24]  592 	movx	@dptr,a
      000272 53 BA 7F         [24]  593 	anl	_P_SW2,#0x7f
                                    594 ;	src\pwm_audio.c:23: PWMA_SetCounterState(HAL_State_ON);
      000275 43 BA 80         [24]  595 	orl	_P_SW2,#0x80
      000278 90 FE C0         [24]  596 	mov	dptr,#0xfec0
      00027B E0               [24]  597 	movx	a,@dptr
      00027C FB               [12]  598 	mov	r3,a
      00027D 74 FE            [12]  599 	mov	a,#0xfe
      00027F 5B               [12]  600 	anl	a,r3
      000280 44 01            [12]  601 	orl	a,#0x01
      000282 F0               [24]  602 	movx	@dptr,a
      000283 53 BA 7F         [24]  603 	anl	_P_SW2,#0x7f
                                    604 ;	src\pwm_audio.c:26: TIM_Timer3_Config(HAL_State_ON, 0, sample_rate, HAL_State_ON);
      000286 8C 17            [24]  605 	mov	_TIM_Timer3_Config_PARM_3,r4
      000288 8D 18            [24]  606 	mov	(_TIM_Timer3_Config_PARM_3 + 1),r5
      00028A 75 16 00         [24]  607 	mov	_TIM_Timer3_Config_PARM_2,#0x00
      00028D 75 19 01         [24]  608 	mov	_TIM_Timer3_Config_PARM_4,#0x01
      000290 75 82 01         [24]  609 	mov	dpl, #0x01
                                    610 ;	src\pwm_audio.c:27: }
      000293 02 0B 6D         [24]  611 	ljmp	_TIM_Timer3_Config
                                    612 ;------------------------------------------------------------
                                    613 ;Allocation info for local variables in function 'pwm_audio_set_sample'
                                    614 ;------------------------------------------------------------
                                    615 ;sample                    Allocated to registers r7 
                                    616 ;duty                      Allocated to registers r7 r6 
                                    617 ;------------------------------------------------------------
                                    618 ;	src\pwm_audio.c:29: void pwm_audio_set_sample(int8_t sample) {
                                    619 ;	-----------------------------------------
                                    620 ;	 function pwm_audio_set_sample
                                    621 ;	-----------------------------------------
      000296                        622 _pwm_audio_set_sample:
                                    623 ;	src\pwm_audio.c:31: uint16_t duty = (uint16_t)((int16_t)sample + 128);
      000296 E5 82            [12]  624 	mov	a,dpl
      000298 FF               [12]  625 	mov	r7,a
      000299 33               [12]  626 	rlc	a
      00029A 95 E0            [12]  627 	subb	a,acc
      00029C FE               [12]  628 	mov	r6,a
      00029D 74 80            [12]  629 	mov	a,#0x80
      00029F 2F               [12]  630 	add	a, r7
      0002A0 FF               [12]  631 	mov	r7,a
      0002A1 E4               [12]  632 	clr	a
      0002A2 3E               [12]  633 	addc	a, r6
      0002A3 FE               [12]  634 	mov	r6,a
                                    635 ;	src\pwm_audio.c:32: PWMA_PWM1_SetCaptureCompareValue(duty);
      0002A4 43 BA 80         [24]  636 	orl	_P_SW2,#0x80
      0002A7 8E 05            [24]  637 	mov	ar5,r6
      0002A9 90 FE D5         [24]  638 	mov	dptr,#0xfed5
      0002AC ED               [12]  639 	mov	a,r5
      0002AD F0               [24]  640 	movx	@dptr,a
      0002AE A3               [24]  641 	inc	dptr
      0002AF EF               [12]  642 	mov	a,r7
      0002B0 F0               [24]  643 	movx	@dptr,a
      0002B1 53 BA 7F         [24]  644 	anl	_P_SW2,#0x7f
                                    645 ;	src\pwm_audio.c:33: }
      0002B4 22               [24]  646 	ret
                                    647 	.area CSEG    (CODE)
                                    648 	.area CONST   (CODE)
                                    649 	.area XINIT   (CODE)
                                    650 	.area CABS    (ABS,CODE)
