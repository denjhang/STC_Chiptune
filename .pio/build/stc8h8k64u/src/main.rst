                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ISO C Compiler 
                                      3 ; Version 4.4.0 #14620 (MINGW32)
                                      4 ;--------------------------------------------------------
                                      5 	.module main
                                      6 	.optsdcc -mmcs51 --model-small
                                      7 	
                                      8 ;--------------------------------------------------------
                                      9 ; Public variables in this module
                                     10 ;--------------------------------------------------------
                                     11 	.globl _main
                                     12 	.globl _timer3_isr
                                     13 	.globl _uart1_isr
                                     14 	.globl _pwm_audio_set_sample
                                     15 	.globl _pwm_audio_init
                                     16 	.globl _uart_init
                                     17 	.globl _scc_render
                                     18 	.globl _scc_write
                                     19 	.globl _scc_init
                                     20 	.globl _P77
                                     21 	.globl _P76
                                     22 	.globl _P75
                                     23 	.globl _P74
                                     24 	.globl _P73
                                     25 	.globl _P72
                                     26 	.globl _P71
                                     27 	.globl _P70
                                     28 	.globl _P67
                                     29 	.globl _P66
                                     30 	.globl _P65
                                     31 	.globl _P64
                                     32 	.globl _P63
                                     33 	.globl _P62
                                     34 	.globl _P61
                                     35 	.globl _P60
                                     36 	.globl _P
                                     37 	.globl _F1
                                     38 	.globl _OV
                                     39 	.globl _RS0
                                     40 	.globl _RS1
                                     41 	.globl _F0
                                     42 	.globl _AC
                                     43 	.globl _CY
                                     44 	.globl _P57
                                     45 	.globl _P56
                                     46 	.globl _P55
                                     47 	.globl _P54
                                     48 	.globl _P53
                                     49 	.globl _P52
                                     50 	.globl _P51
                                     51 	.globl _P50
                                     52 	.globl _P47
                                     53 	.globl _P46
                                     54 	.globl _P45
                                     55 	.globl _P44
                                     56 	.globl _P43
                                     57 	.globl _P42
                                     58 	.globl _P41
                                     59 	.globl _P40
                                     60 	.globl _PX0
                                     61 	.globl _PT0
                                     62 	.globl _PX1
                                     63 	.globl _PT1
                                     64 	.globl _PS
                                     65 	.globl _PADC
                                     66 	.globl _PLVD
                                     67 	.globl _PPCA
                                     68 	.globl _P37
                                     69 	.globl _P36
                                     70 	.globl _P35
                                     71 	.globl _P34
                                     72 	.globl _P33
                                     73 	.globl _P32
                                     74 	.globl _P31
                                     75 	.globl _P30
                                     76 	.globl _EX0
                                     77 	.globl _ET0
                                     78 	.globl _EX1
                                     79 	.globl _ET1
                                     80 	.globl _ES
                                     81 	.globl _EADC
                                     82 	.globl _ELVD
                                     83 	.globl _EA
                                     84 	.globl _P27
                                     85 	.globl _P26
                                     86 	.globl _P25
                                     87 	.globl _P24
                                     88 	.globl _P23
                                     89 	.globl _P22
                                     90 	.globl _P21
                                     91 	.globl _P20
                                     92 	.globl _RI
                                     93 	.globl _TI
                                     94 	.globl _RB8
                                     95 	.globl _TB8
                                     96 	.globl _REN
                                     97 	.globl _SM2
                                     98 	.globl _SM1
                                     99 	.globl _SM0
                                    100 	.globl _P17
                                    101 	.globl _P16
                                    102 	.globl _P15
                                    103 	.globl _P14
                                    104 	.globl _P13
                                    105 	.globl _P12
                                    106 	.globl _P11
                                    107 	.globl _P10
                                    108 	.globl _IT0
                                    109 	.globl _IE0
                                    110 	.globl _IT1
                                    111 	.globl _IE1
                                    112 	.globl _TR0
                                    113 	.globl _TF0
                                    114 	.globl _TR1
                                    115 	.globl _TF1
                                    116 	.globl _P07
                                    117 	.globl _P06
                                    118 	.globl _P05
                                    119 	.globl _P04
                                    120 	.globl _P03
                                    121 	.globl _P02
                                    122 	.globl _P01
                                    123 	.globl _P00
                                    124 	.globl _RSTCFG
                                    125 	.globl _USBADR
                                    126 	.globl _IAP_TPS
                                    127 	.globl _USBCON
                                    128 	.globl _AUXINTIF
                                    129 	.globl _IP3H
                                    130 	.globl _USBDAT
                                    131 	.globl _CMPCR2
                                    132 	.globl _CMPCR1
                                    133 	.globl _DPH1
                                    134 	.globl _DPL1
                                    135 	.globl _DPS
                                    136 	.globl _P7M0
                                    137 	.globl _P7M1
                                    138 	.globl _IP3
                                    139 	.globl _ADCCFG
                                    140 	.globl _USBCLK
                                    141 	.globl _VRTRIM
                                    142 	.globl _P7
                                    143 	.globl _B
                                    144 	.globl _P6
                                    145 	.globl _ACC
                                    146 	.globl _T2L
                                    147 	.globl _T2H
                                    148 	.globl _T3L
                                    149 	.globl _T3H
                                    150 	.globl _T4L
                                    151 	.globl _T4H
                                    152 	.globl _T4T3M
                                    153 	.globl _PSW
                                    154 	.globl _SPDAT
                                    155 	.globl _SPCTL
                                    156 	.globl _SPSTAT
                                    157 	.globl _P6M0
                                    158 	.globl _P6M1
                                    159 	.globl _P5M0
                                    160 	.globl _P5M1
                                    161 	.globl _P5
                                    162 	.globl _IAP_CONTR
                                    163 	.globl _IAP_TRIG
                                    164 	.globl _IAP_CMD
                                    165 	.globl _IAP_ADDRL
                                    166 	.globl _IAP_ADDRH
                                    167 	.globl _IAP_DATA
                                    168 	.globl _WDT_CONTR
                                    169 	.globl _P4
                                    170 	.globl _ADC_RESL
                                    171 	.globl _ADC_RES
                                    172 	.globl _ADC_CONTR
                                    173 	.globl _P_SW2
                                    174 	.globl _SADEN
                                    175 	.globl _IP
                                    176 	.globl _IPH
                                    177 	.globl _IP2H
                                    178 	.globl _IP2
                                    179 	.globl _P4M0
                                    180 	.globl _P4M1
                                    181 	.globl _P3M0
                                    182 	.globl _P3M1
                                    183 	.globl _P3
                                    184 	.globl _IE2
                                    185 	.globl _TA
                                    186 	.globl _S3BUF
                                    187 	.globl _S3CON
                                    188 	.globl _WKTCH
                                    189 	.globl _WKTCL
                                    190 	.globl _SADDR
                                    191 	.globl _IE
                                    192 	.globl _P_SW1
                                    193 	.globl _BUS_SPEED
                                    194 	.globl _P2
                                    195 	.globl _IRTRIM
                                    196 	.globl _LIRTRIM
                                    197 	.globl _IRCBAND
                                    198 	.globl _S2BUF
                                    199 	.globl _S2CON
                                    200 	.globl _SBUF
                                    201 	.globl _SCON
                                    202 	.globl _P2M0
                                    203 	.globl _P2M1
                                    204 	.globl _P0M0
                                    205 	.globl _P0M1
                                    206 	.globl _P1M0
                                    207 	.globl _P1M1
                                    208 	.globl _P1
                                    209 	.globl _INTCLKO
                                    210 	.globl _AUXR
                                    211 	.globl _TH1
                                    212 	.globl _TH0
                                    213 	.globl _TL1
                                    214 	.globl _TL0
                                    215 	.globl _TMOD
                                    216 	.globl _TCON
                                    217 	.globl _PCON
                                    218 	.globl _S4BUF
                                    219 	.globl _S4CON
                                    220 	.globl _DPH
                                    221 	.globl _DPL
                                    222 	.globl _SP
                                    223 	.globl _P0
                                    224 ;--------------------------------------------------------
                                    225 ; special function registers
                                    226 ;--------------------------------------------------------
                                    227 	.area RSEG    (ABS,DATA)
      000000                        228 	.org 0x0000
                           000080   229 _P0	=	0x0080
                           000081   230 _SP	=	0x0081
                           000082   231 _DPL	=	0x0082
                           000083   232 _DPH	=	0x0083
                           000084   233 _S4CON	=	0x0084
                           000085   234 _S4BUF	=	0x0085
                           000087   235 _PCON	=	0x0087
                           000088   236 _TCON	=	0x0088
                           000089   237 _TMOD	=	0x0089
                           00008A   238 _TL0	=	0x008a
                           00008B   239 _TL1	=	0x008b
                           00008C   240 _TH0	=	0x008c
                           00008D   241 _TH1	=	0x008d
                           00008E   242 _AUXR	=	0x008e
                           00008F   243 _INTCLKO	=	0x008f
                           000090   244 _P1	=	0x0090
                           000091   245 _P1M1	=	0x0091
                           000092   246 _P1M0	=	0x0092
                           000093   247 _P0M1	=	0x0093
                           000094   248 _P0M0	=	0x0094
                           000095   249 _P2M1	=	0x0095
                           000096   250 _P2M0	=	0x0096
                           000098   251 _SCON	=	0x0098
                           000099   252 _SBUF	=	0x0099
                           00009A   253 _S2CON	=	0x009a
                           00009B   254 _S2BUF	=	0x009b
                           00009D   255 _IRCBAND	=	0x009d
                           00009E   256 _LIRTRIM	=	0x009e
                           00009F   257 _IRTRIM	=	0x009f
                           0000A0   258 _P2	=	0x00a0
                           0000A1   259 _BUS_SPEED	=	0x00a1
                           0000A2   260 _P_SW1	=	0x00a2
                           0000A8   261 _IE	=	0x00a8
                           0000A9   262 _SADDR	=	0x00a9
                           0000AA   263 _WKTCL	=	0x00aa
                           0000AB   264 _WKTCH	=	0x00ab
                           0000AC   265 _S3CON	=	0x00ac
                           0000AD   266 _S3BUF	=	0x00ad
                           0000AE   267 _TA	=	0x00ae
                           0000AF   268 _IE2	=	0x00af
                           0000B0   269 _P3	=	0x00b0
                           0000B1   270 _P3M1	=	0x00b1
                           0000B2   271 _P3M0	=	0x00b2
                           0000B3   272 _P4M1	=	0x00b3
                           0000B4   273 _P4M0	=	0x00b4
                           0000B5   274 _IP2	=	0x00b5
                           0000B6   275 _IP2H	=	0x00b6
                           0000B7   276 _IPH	=	0x00b7
                           0000B8   277 _IP	=	0x00b8
                           0000B9   278 _SADEN	=	0x00b9
                           0000BA   279 _P_SW2	=	0x00ba
                           0000BC   280 _ADC_CONTR	=	0x00bc
                           0000BD   281 _ADC_RES	=	0x00bd
                           0000BE   282 _ADC_RESL	=	0x00be
                           0000C0   283 _P4	=	0x00c0
                           0000C1   284 _WDT_CONTR	=	0x00c1
                           0000C2   285 _IAP_DATA	=	0x00c2
                           0000C3   286 _IAP_ADDRH	=	0x00c3
                           0000C4   287 _IAP_ADDRL	=	0x00c4
                           0000C5   288 _IAP_CMD	=	0x00c5
                           0000C6   289 _IAP_TRIG	=	0x00c6
                           0000C7   290 _IAP_CONTR	=	0x00c7
                           0000C8   291 _P5	=	0x00c8
                           0000C9   292 _P5M1	=	0x00c9
                           0000CA   293 _P5M0	=	0x00ca
                           0000CB   294 _P6M1	=	0x00cb
                           0000CC   295 _P6M0	=	0x00cc
                           0000CD   296 _SPSTAT	=	0x00cd
                           0000CE   297 _SPCTL	=	0x00ce
                           0000CF   298 _SPDAT	=	0x00cf
                           0000D0   299 _PSW	=	0x00d0
                           0000D1   300 _T4T3M	=	0x00d1
                           0000D2   301 _T4H	=	0x00d2
                           0000D3   302 _T4L	=	0x00d3
                           0000D4   303 _T3H	=	0x00d4
                           0000D5   304 _T3L	=	0x00d5
                           0000D6   305 _T2H	=	0x00d6
                           0000D7   306 _T2L	=	0x00d7
                           0000E0   307 _ACC	=	0x00e0
                           0000E8   308 _P6	=	0x00e8
                           0000F0   309 _B	=	0x00f0
                           0000F8   310 _P7	=	0x00f8
                           0000A6   311 _VRTRIM	=	0x00a6
                           0000DC   312 _USBCLK	=	0x00dc
                           0000DE   313 _ADCCFG	=	0x00de
                           0000DF   314 _IP3	=	0x00df
                           0000E1   315 _P7M1	=	0x00e1
                           0000E2   316 _P7M0	=	0x00e2
                           0000E3   317 _DPS	=	0x00e3
                           0000E4   318 _DPL1	=	0x00e4
                           0000E5   319 _DPH1	=	0x00e5
                           0000E6   320 _CMPCR1	=	0x00e6
                           0000E7   321 _CMPCR2	=	0x00e7
                           0000EC   322 _USBDAT	=	0x00ec
                           0000EE   323 _IP3H	=	0x00ee
                           0000EF   324 _AUXINTIF	=	0x00ef
                           0000F4   325 _USBCON	=	0x00f4
                           0000F5   326 _IAP_TPS	=	0x00f5
                           0000FC   327 _USBADR	=	0x00fc
                           0000FF   328 _RSTCFG	=	0x00ff
                                    329 ;--------------------------------------------------------
                                    330 ; special function bits
                                    331 ;--------------------------------------------------------
                                    332 	.area RSEG    (ABS,DATA)
      000000                        333 	.org 0x0000
                           000080   334 _P00	=	0x0080
                           000081   335 _P01	=	0x0081
                           000082   336 _P02	=	0x0082
                           000083   337 _P03	=	0x0083
                           000084   338 _P04	=	0x0084
                           000085   339 _P05	=	0x0085
                           000086   340 _P06	=	0x0086
                           000087   341 _P07	=	0x0087
                           00008F   342 _TF1	=	0x008f
                           00008E   343 _TR1	=	0x008e
                           00008D   344 _TF0	=	0x008d
                           00008C   345 _TR0	=	0x008c
                           00008B   346 _IE1	=	0x008b
                           00008A   347 _IT1	=	0x008a
                           000089   348 _IE0	=	0x0089
                           000088   349 _IT0	=	0x0088
                           000090   350 _P10	=	0x0090
                           000091   351 _P11	=	0x0091
                           000092   352 _P12	=	0x0092
                           000093   353 _P13	=	0x0093
                           000094   354 _P14	=	0x0094
                           000095   355 _P15	=	0x0095
                           000096   356 _P16	=	0x0096
                           000097   357 _P17	=	0x0097
                           00009F   358 _SM0	=	0x009f
                           00009E   359 _SM1	=	0x009e
                           00009D   360 _SM2	=	0x009d
                           00009C   361 _REN	=	0x009c
                           00009B   362 _TB8	=	0x009b
                           00009A   363 _RB8	=	0x009a
                           000099   364 _TI	=	0x0099
                           000098   365 _RI	=	0x0098
                           0000A0   366 _P20	=	0x00a0
                           0000A1   367 _P21	=	0x00a1
                           0000A2   368 _P22	=	0x00a2
                           0000A3   369 _P23	=	0x00a3
                           0000A4   370 _P24	=	0x00a4
                           0000A5   371 _P25	=	0x00a5
                           0000A6   372 _P26	=	0x00a6
                           0000A7   373 _P27	=	0x00a7
                           0000AF   374 _EA	=	0x00af
                           0000AE   375 _ELVD	=	0x00ae
                           0000AD   376 _EADC	=	0x00ad
                           0000AC   377 _ES	=	0x00ac
                           0000AB   378 _ET1	=	0x00ab
                           0000AA   379 _EX1	=	0x00aa
                           0000A9   380 _ET0	=	0x00a9
                           0000A8   381 _EX0	=	0x00a8
                           0000B0   382 _P30	=	0x00b0
                           0000B1   383 _P31	=	0x00b1
                           0000B2   384 _P32	=	0x00b2
                           0000B3   385 _P33	=	0x00b3
                           0000B4   386 _P34	=	0x00b4
                           0000B5   387 _P35	=	0x00b5
                           0000B6   388 _P36	=	0x00b6
                           0000B7   389 _P37	=	0x00b7
                           0000BF   390 _PPCA	=	0x00bf
                           0000BE   391 _PLVD	=	0x00be
                           0000BD   392 _PADC	=	0x00bd
                           0000BC   393 _PS	=	0x00bc
                           0000BB   394 _PT1	=	0x00bb
                           0000BA   395 _PX1	=	0x00ba
                           0000B9   396 _PT0	=	0x00b9
                           0000B8   397 _PX0	=	0x00b8
                           0000C0   398 _P40	=	0x00c0
                           0000C1   399 _P41	=	0x00c1
                           0000C2   400 _P42	=	0x00c2
                           0000C3   401 _P43	=	0x00c3
                           0000C4   402 _P44	=	0x00c4
                           0000C5   403 _P45	=	0x00c5
                           0000C6   404 _P46	=	0x00c6
                           0000C7   405 _P47	=	0x00c7
                           0000C8   406 _P50	=	0x00c8
                           0000C9   407 _P51	=	0x00c9
                           0000CA   408 _P52	=	0x00ca
                           0000CB   409 _P53	=	0x00cb
                           0000CC   410 _P54	=	0x00cc
                           0000CD   411 _P55	=	0x00cd
                           0000CE   412 _P56	=	0x00ce
                           0000CF   413 _P57	=	0x00cf
                           0000D7   414 _CY	=	0x00d7
                           0000D6   415 _AC	=	0x00d6
                           0000D5   416 _F0	=	0x00d5
                           0000D4   417 _RS1	=	0x00d4
                           0000D3   418 _RS0	=	0x00d3
                           0000D2   419 _OV	=	0x00d2
                           0000D1   420 _F1	=	0x00d1
                           0000D0   421 _P	=	0x00d0
                           0000E8   422 _P60	=	0x00e8
                           0000E9   423 _P61	=	0x00e9
                           0000EA   424 _P62	=	0x00ea
                           0000EB   425 _P63	=	0x00eb
                           0000EC   426 _P64	=	0x00ec
                           0000ED   427 _P65	=	0x00ed
                           0000EE   428 _P66	=	0x00ee
                           0000EF   429 _P67	=	0x00ef
                           0000F8   430 _P70	=	0x00f8
                           0000F9   431 _P71	=	0x00f9
                           0000FA   432 _P72	=	0x00fa
                           0000FB   433 _P73	=	0x00fb
                           0000FC   434 _P74	=	0x00fc
                           0000FD   435 _P75	=	0x00fd
                           0000FE   436 _P76	=	0x00fe
                           0000FF   437 _P77	=	0x00ff
                                    438 ;--------------------------------------------------------
                                    439 ; overlayable register banks
                                    440 ;--------------------------------------------------------
                                    441 	.area REG_BANK_0	(REL,OVR,DATA)
      000000                        442 	.ds 8
                                    443 ;--------------------------------------------------------
                                    444 ; overlayable bit register bank
                                    445 ;--------------------------------------------------------
                                    446 	.area BIT_BANK	(REL,OVR,DATA)
      000020                        447 bits:
      000020                        448 	.ds 1
                           008000   449 	b0 = bits[0]
                           008100   450 	b1 = bits[1]
                           008200   451 	b2 = bits[2]
                           008300   452 	b3 = bits[3]
                           008400   453 	b4 = bits[4]
                           008500   454 	b5 = bits[5]
                           008600   455 	b6 = bits[6]
                           008700   456 	b7 = bits[7]
                                    457 ;--------------------------------------------------------
                                    458 ; internal ram data
                                    459 ;--------------------------------------------------------
                                    460 	.area DSEG    (DATA)
                                    461 ;--------------------------------------------------------
                                    462 ; overlayable items in internal ram
                                    463 ;--------------------------------------------------------
                                    464 ;--------------------------------------------------------
                                    465 ; Stack segment in internal ram
                                    466 ;--------------------------------------------------------
                                    467 	.area SSEG
      000067                        468 __start__stack:
      000067                        469 	.ds	1
                                    470 
                                    471 ;--------------------------------------------------------
                                    472 ; indirectly addressable internal ram data
                                    473 ;--------------------------------------------------------
                                    474 	.area ISEG    (DATA)
                                    475 ;--------------------------------------------------------
                                    476 ; absolute internal ram data
                                    477 ;--------------------------------------------------------
                                    478 	.area IABS    (ABS,DATA)
                                    479 	.area IABS    (ABS,DATA)
                                    480 ;--------------------------------------------------------
                                    481 ; bit data
                                    482 ;--------------------------------------------------------
                                    483 	.area BSEG    (BIT)
                                    484 ;--------------------------------------------------------
                                    485 ; paged external ram data
                                    486 ;--------------------------------------------------------
                                    487 	.area PSEG    (PAG,XDATA)
                                    488 ;--------------------------------------------------------
                                    489 ; uninitialized external ram data
                                    490 ;--------------------------------------------------------
                                    491 	.area XSEG    (XDATA)
      000001                        492 _scc:
      000001                        493 	.ds 211
      0000D4                        494 _rx_state:
      0000D4                        495 	.ds 1
      0000D5                        496 _rx_buf:
      0000D5                        497 	.ds 2
                                    498 ;--------------------------------------------------------
                                    499 ; absolute external ram data
                                    500 ;--------------------------------------------------------
                                    501 	.area XABS    (ABS,XDATA)
                                    502 ;--------------------------------------------------------
                                    503 ; initialized external ram data
                                    504 ;--------------------------------------------------------
                                    505 	.area XISEG   (XDATA)
                                    506 	.area HOME    (CODE)
                                    507 	.area GSINIT0 (CODE)
                                    508 	.area GSINIT1 (CODE)
                                    509 	.area GSINIT2 (CODE)
                                    510 	.area GSINIT3 (CODE)
                                    511 	.area GSINIT4 (CODE)
                                    512 	.area GSINIT5 (CODE)
                                    513 	.area GSINIT  (CODE)
                                    514 	.area GSFINAL (CODE)
                                    515 	.area CSEG    (CODE)
                                    516 ;--------------------------------------------------------
                                    517 ; interrupt vector
                                    518 ;--------------------------------------------------------
                                    519 	.area HOME    (CODE)
      000000                        520 __interrupt_vect:
      000000 02 00 A1         [24]  521 	ljmp	__sdcc_gsinit_startup
      000003 32               [24]  522 	reti
      000004                        523 	.ds	7
      00000B 32               [24]  524 	reti
      00000C                        525 	.ds	7
      000013 32               [24]  526 	reti
      000014                        527 	.ds	7
      00001B 32               [24]  528 	reti
      00001C                        529 	.ds	7
      000023 02 00 FD         [24]  530 	ljmp	_uart1_isr
      000026                        531 	.ds	5
      00002B 32               [24]  532 	reti
      00002C                        533 	.ds	7
      000033 32               [24]  534 	reti
      000034                        535 	.ds	7
      00003B 32               [24]  536 	reti
      00003C                        537 	.ds	7
      000043 32               [24]  538 	reti
      000044                        539 	.ds	7
      00004B 32               [24]  540 	reti
      00004C                        541 	.ds	7
      000053 32               [24]  542 	reti
      000054                        543 	.ds	7
      00005B 32               [24]  544 	reti
      00005C                        545 	.ds	7
      000063 32               [24]  546 	reti
      000064                        547 	.ds	7
      00006B 32               [24]  548 	reti
      00006C                        549 	.ds	7
      000073 32               [24]  550 	reti
      000074                        551 	.ds	7
      00007B 32               [24]  552 	reti
      00007C                        553 	.ds	7
      000083 32               [24]  554 	reti
      000084                        555 	.ds	7
      00008B 32               [24]  556 	reti
      00008C                        557 	.ds	7
      000093 32               [24]  558 	reti
      000094                        559 	.ds	7
      00009B 02 01 7B         [24]  560 	ljmp	_timer3_isr
                                    561 ;--------------------------------------------------------
                                    562 ; global & static initialisations
                                    563 ;--------------------------------------------------------
                                    564 	.area HOME    (CODE)
                                    565 	.area GSINIT  (CODE)
                                    566 	.area GSFINAL (CODE)
                                    567 	.area GSINIT  (CODE)
                                    568 	.globl __sdcc_gsinit_startup
                                    569 	.globl __sdcc_program_startup
                                    570 	.globl __start__stack
                                    571 	.globl __mcs51_genXINIT
                                    572 	.globl __mcs51_genXRAMCLEAR
                                    573 	.globl __mcs51_genRAMCLEAR
                                    574 	.area GSFINAL (CODE)
      0000FA 02 00 9E         [24]  575 	ljmp	__sdcc_program_startup
                                    576 ;--------------------------------------------------------
                                    577 ; Home
                                    578 ;--------------------------------------------------------
                                    579 	.area HOME    (CODE)
                                    580 	.area HOME    (CODE)
      00009E                        581 __sdcc_program_startup:
      00009E 02 01 C3         [24]  582 	ljmp	_main
                                    583 ;	return from main will return to caller
                                    584 ;--------------------------------------------------------
                                    585 ; code
                                    586 ;--------------------------------------------------------
                                    587 	.area CSEG    (CODE)
                                    588 ;------------------------------------------------------------
                                    589 ;Allocation info for local variables in function 'uart1_isr'
                                    590 ;------------------------------------------------------------
                                    591 ;	src\main.c:12: void uart1_isr(void) __interrupt(4) {
                                    592 ;	-----------------------------------------
                                    593 ;	 function uart1_isr
                                    594 ;	-----------------------------------------
      0000FD                        595 _uart1_isr:
                           000007   596 	ar7 = 0x07
                           000006   597 	ar6 = 0x06
                           000005   598 	ar5 = 0x05
                           000004   599 	ar4 = 0x04
                           000003   600 	ar3 = 0x03
                           000002   601 	ar2 = 0x02
                           000001   602 	ar1 = 0x01
                           000000   603 	ar0 = 0x00
      0000FD C0 20            [24]  604 	push	bits
      0000FF C0 E0            [24]  605 	push	acc
      000101 C0 F0            [24]  606 	push	b
      000103 C0 82            [24]  607 	push	dpl
      000105 C0 83            [24]  608 	push	dph
      000107 C0 07            [24]  609 	push	(0+7)
      000109 C0 06            [24]  610 	push	(0+6)
      00010B C0 05            [24]  611 	push	(0+5)
      00010D C0 04            [24]  612 	push	(0+4)
      00010F C0 03            [24]  613 	push	(0+3)
      000111 C0 02            [24]  614 	push	(0+2)
      000113 C0 01            [24]  615 	push	(0+1)
      000115 C0 00            [24]  616 	push	(0+0)
      000117 C0 D0            [24]  617 	push	psw
      000119 75 D0 00         [24]  618 	mov	psw,#0x00
                                    619 ;	src\main.c:13: if (RI) {
                                    620 ;	src\main.c:14: RI = 0;
                                    621 ;	assignBit
      00011C 10 98 02         [24]  622 	jbc	_RI,00127$
      00011F 80 38            [24]  623 	sjmp	00104$
      000121                        624 00127$:
                                    625 ;	src\main.c:15: rx_buf[rx_state++] = SBUF;
      000121 90 00 D4         [24]  626 	mov	dptr,#_rx_state
      000124 E0               [24]  627 	movx	a,@dptr
      000125 FF               [12]  628 	mov	r7,a
      000126 04               [12]  629 	inc	a
      000127 F0               [24]  630 	movx	@dptr,a
      000128 EF               [12]  631 	mov	a,r7
      000129 24 D5            [12]  632 	add	a, #_rx_buf
      00012B F5 82            [12]  633 	mov	dpl,a
      00012D E4               [12]  634 	clr	a
      00012E 34 00            [12]  635 	addc	a, #(_rx_buf >> 8)
      000130 F5 83            [12]  636 	mov	dph,a
      000132 E5 99            [12]  637 	mov	a,_SBUF
      000134 F0               [24]  638 	movx	@dptr,a
                                    639 ;	src\main.c:16: if (rx_state >= 2) {
      000135 90 00 D4         [24]  640 	mov	dptr,#_rx_state
      000138 E0               [24]  641 	movx	a,@dptr
      000139 FF               [12]  642 	mov	r7,a
      00013A BF 02 00         [24]  643 	cjne	r7,#0x02,00128$
      00013D                        644 00128$:
      00013D 40 1A            [24]  645 	jc	00104$
                                    646 ;	src\main.c:17: scc_write(&scc, rx_buf[0], rx_buf[1]);
      00013F 90 00 D5         [24]  647 	mov	dptr,#_rx_buf
      000142 E0               [24]  648 	movx	a,@dptr
      000143 F5 62            [12]  649 	mov	_scc_write_PARM_2,a
      000145 90 00 D6         [24]  650 	mov	dptr,#(_rx_buf + 0x0001)
      000148 E0               [24]  651 	movx	a,@dptr
      000149 F5 63            [12]  652 	mov	_scc_write_PARM_3,a
      00014B 90 00 01         [24]  653 	mov	dptr,#_scc
      00014E 75 F0 00         [24]  654 	mov	b, #0x00
      000151 12 04 05         [24]  655 	lcall	_scc_write
                                    656 ;	src\main.c:18: rx_state = 0;
      000154 90 00 D4         [24]  657 	mov	dptr,#_rx_state
      000157 E4               [12]  658 	clr	a
      000158 F0               [24]  659 	movx	@dptr,a
      000159                        660 00104$:
                                    661 ;	src\main.c:21: if (TI) {
                                    662 ;	src\main.c:22: TI = 0;
                                    663 ;	assignBit
      000159 10 99 02         [24]  664 	jbc	_TI,00130$
      00015C 80 00            [24]  665 	sjmp	00107$
      00015E                        666 00130$:
      00015E                        667 00107$:
                                    668 ;	src\main.c:24: }
      00015E D0 D0            [24]  669 	pop	psw
      000160 D0 00            [24]  670 	pop	(0+0)
      000162 D0 01            [24]  671 	pop	(0+1)
      000164 D0 02            [24]  672 	pop	(0+2)
      000166 D0 03            [24]  673 	pop	(0+3)
      000168 D0 04            [24]  674 	pop	(0+4)
      00016A D0 05            [24]  675 	pop	(0+5)
      00016C D0 06            [24]  676 	pop	(0+6)
      00016E D0 07            [24]  677 	pop	(0+7)
      000170 D0 83            [24]  678 	pop	dph
      000172 D0 82            [24]  679 	pop	dpl
      000174 D0 F0            [24]  680 	pop	b
      000176 D0 E0            [24]  681 	pop	acc
      000178 D0 20            [24]  682 	pop	bits
      00017A 32               [24]  683 	reti
                                    684 ;------------------------------------------------------------
                                    685 ;Allocation info for local variables in function 'timer3_isr'
                                    686 ;------------------------------------------------------------
                                    687 ;sample                    Allocated to registers 
                                    688 ;------------------------------------------------------------
                                    689 ;	src\main.c:26: void timer3_isr(void) __interrupt(19) {
                                    690 ;	-----------------------------------------
                                    691 ;	 function timer3_isr
                                    692 ;	-----------------------------------------
      00017B                        693 _timer3_isr:
      00017B C0 20            [24]  694 	push	bits
      00017D C0 E0            [24]  695 	push	acc
      00017F C0 F0            [24]  696 	push	b
      000181 C0 82            [24]  697 	push	dpl
      000183 C0 83            [24]  698 	push	dph
      000185 C0 07            [24]  699 	push	(0+7)
      000187 C0 06            [24]  700 	push	(0+6)
      000189 C0 05            [24]  701 	push	(0+5)
      00018B C0 04            [24]  702 	push	(0+4)
      00018D C0 03            [24]  703 	push	(0+3)
      00018F C0 02            [24]  704 	push	(0+2)
      000191 C0 01            [24]  705 	push	(0+1)
      000193 C0 00            [24]  706 	push	(0+0)
      000195 C0 D0            [24]  707 	push	psw
      000197 75 D0 00         [24]  708 	mov	psw,#0x00
                                    709 ;	src\main.c:27: int8_t sample = scc_render(&scc);
      00019A 90 00 01         [24]  710 	mov	dptr,#_scc
      00019D 75 F0 00         [24]  711 	mov	b, #0x00
      0001A0 12 07 34         [24]  712 	lcall	_scc_render
                                    713 ;	src\main.c:28: pwm_audio_set_sample(sample);
      0001A3 12 02 96         [24]  714 	lcall	_pwm_audio_set_sample
                                    715 ;	src\main.c:29: }
      0001A6 D0 D0            [24]  716 	pop	psw
      0001A8 D0 00            [24]  717 	pop	(0+0)
      0001AA D0 01            [24]  718 	pop	(0+1)
      0001AC D0 02            [24]  719 	pop	(0+2)
      0001AE D0 03            [24]  720 	pop	(0+3)
      0001B0 D0 04            [24]  721 	pop	(0+4)
      0001B2 D0 05            [24]  722 	pop	(0+5)
      0001B4 D0 06            [24]  723 	pop	(0+6)
      0001B6 D0 07            [24]  724 	pop	(0+7)
      0001B8 D0 83            [24]  725 	pop	dph
      0001BA D0 82            [24]  726 	pop	dpl
      0001BC D0 F0            [24]  727 	pop	b
      0001BE D0 E0            [24]  728 	pop	acc
      0001C0 D0 20            [24]  729 	pop	bits
      0001C2 32               [24]  730 	reti
                                    731 ;------------------------------------------------------------
                                    732 ;Allocation info for local variables in function 'main'
                                    733 ;------------------------------------------------------------
                                    734 ;	src\main.c:31: void main(void) {
                                    735 ;	-----------------------------------------
                                    736 ;	 function main
                                    737 ;	-----------------------------------------
      0001C3                        738 _main:
                                    739 ;	src\main.c:32: rx_state = 0;
      0001C3 90 00 D4         [24]  740 	mov	dptr,#_rx_state
      0001C6 E4               [12]  741 	clr	a
      0001C7 F0               [24]  742 	movx	@dptr,a
                                    743 ;	src\main.c:33: uart_init(BAUD_RATE);
      0001C8 90 C2 00         [24]  744 	mov	dptr,#0xc200
      0001CB 75 F0 01         [24]  745 	mov	b, #0x01
      0001CE 12 09 1F         [24]  746 	lcall	_uart_init
                                    747 ;	src\main.c:34: scc_init(&scc, __CONF_FOSC);
      0001D1 E4               [12]  748 	clr	a
      0001D2 F5 21            [12]  749 	mov	_scc_init_PARM_2,a
      0001D4 75 22 C0         [24]  750 	mov	(_scc_init_PARM_2 + 1),#0xc0
      0001D7 75 23 A8         [24]  751 	mov	(_scc_init_PARM_2 + 2),#0xa8
      0001DA F5 24            [12]  752 	mov	(_scc_init_PARM_2 + 3),a
      0001DC 90 00 01         [24]  753 	mov	dptr,#_scc
      0001DF F5 F0            [12]  754 	mov	b,a
      0001E1 12 02 B5         [24]  755 	lcall	_scc_init
                                    756 ;	src\main.c:35: pwm_audio_init(44100);
      0001E4 90 AC 44         [24]  757 	mov	dptr,#0xac44
      0001E7 E4               [12]  758 	clr	a
      0001E8 F5 F0            [12]  759 	mov	b,a
      0001EA 12 01 F1         [24]  760 	lcall	_pwm_audio_init
                                    761 ;	src\main.c:36: EA = 1;
                                    762 ;	assignBit
      0001ED D2 AF            [12]  763 	setb	_EA
                                    764 ;	src\main.c:38: while (1) {
      0001EF                        765 00102$:
                                    766 ;	src\main.c:40: }
      0001EF 80 FE            [24]  767 	sjmp	00102$
                                    768 	.area CSEG    (CODE)
                                    769 	.area CONST   (CODE)
                                    770 	.area XINIT   (CODE)
                                    771 	.area CABS    (ABS,CODE)
