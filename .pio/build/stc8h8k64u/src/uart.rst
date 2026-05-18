                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ISO C Compiler 
                                      3 ; Version 4.4.0 #14620 (MINGW32)
                                      4 ;--------------------------------------------------------
                                      5 	.module uart
                                      6 	.optsdcc -mmcs51 --model-small
                                      7 	
                                      8 ;--------------------------------------------------------
                                      9 ; Public variables in this module
                                     10 ;--------------------------------------------------------
                                     11 	.globl _UART1_TxChar
                                     12 	.globl _UART1_Config8bitUart
                                     13 	.globl _P77
                                     14 	.globl _P76
                                     15 	.globl _P75
                                     16 	.globl _P74
                                     17 	.globl _P73
                                     18 	.globl _P72
                                     19 	.globl _P71
                                     20 	.globl _P70
                                     21 	.globl _P67
                                     22 	.globl _P66
                                     23 	.globl _P65
                                     24 	.globl _P64
                                     25 	.globl _P63
                                     26 	.globl _P62
                                     27 	.globl _P61
                                     28 	.globl _P60
                                     29 	.globl _P
                                     30 	.globl _F1
                                     31 	.globl _OV
                                     32 	.globl _RS0
                                     33 	.globl _RS1
                                     34 	.globl _F0
                                     35 	.globl _AC
                                     36 	.globl _CY
                                     37 	.globl _P57
                                     38 	.globl _P56
                                     39 	.globl _P55
                                     40 	.globl _P54
                                     41 	.globl _P53
                                     42 	.globl _P52
                                     43 	.globl _P51
                                     44 	.globl _P50
                                     45 	.globl _P47
                                     46 	.globl _P46
                                     47 	.globl _P45
                                     48 	.globl _P44
                                     49 	.globl _P43
                                     50 	.globl _P42
                                     51 	.globl _P41
                                     52 	.globl _P40
                                     53 	.globl _PX0
                                     54 	.globl _PT0
                                     55 	.globl _PX1
                                     56 	.globl _PT1
                                     57 	.globl _PS
                                     58 	.globl _PADC
                                     59 	.globl _PLVD
                                     60 	.globl _PPCA
                                     61 	.globl _P37
                                     62 	.globl _P36
                                     63 	.globl _P35
                                     64 	.globl _P34
                                     65 	.globl _P33
                                     66 	.globl _P32
                                     67 	.globl _P31
                                     68 	.globl _P30
                                     69 	.globl _EX0
                                     70 	.globl _ET0
                                     71 	.globl _EX1
                                     72 	.globl _ET1
                                     73 	.globl _ES
                                     74 	.globl _EADC
                                     75 	.globl _ELVD
                                     76 	.globl _EA
                                     77 	.globl _P27
                                     78 	.globl _P26
                                     79 	.globl _P25
                                     80 	.globl _P24
                                     81 	.globl _P23
                                     82 	.globl _P22
                                     83 	.globl _P21
                                     84 	.globl _P20
                                     85 	.globl _RI
                                     86 	.globl _TI
                                     87 	.globl _RB8
                                     88 	.globl _TB8
                                     89 	.globl _REN
                                     90 	.globl _SM2
                                     91 	.globl _SM1
                                     92 	.globl _SM0
                                     93 	.globl _P17
                                     94 	.globl _P16
                                     95 	.globl _P15
                                     96 	.globl _P14
                                     97 	.globl _P13
                                     98 	.globl _P12
                                     99 	.globl _P11
                                    100 	.globl _P10
                                    101 	.globl _IT0
                                    102 	.globl _IE0
                                    103 	.globl _IT1
                                    104 	.globl _IE1
                                    105 	.globl _TR0
                                    106 	.globl _TF0
                                    107 	.globl _TR1
                                    108 	.globl _TF1
                                    109 	.globl _P07
                                    110 	.globl _P06
                                    111 	.globl _P05
                                    112 	.globl _P04
                                    113 	.globl _P03
                                    114 	.globl _P02
                                    115 	.globl _P01
                                    116 	.globl _P00
                                    117 	.globl _RSTCFG
                                    118 	.globl _USBADR
                                    119 	.globl _IAP_TPS
                                    120 	.globl _USBCON
                                    121 	.globl _AUXINTIF
                                    122 	.globl _IP3H
                                    123 	.globl _USBDAT
                                    124 	.globl _CMPCR2
                                    125 	.globl _CMPCR1
                                    126 	.globl _DPH1
                                    127 	.globl _DPL1
                                    128 	.globl _DPS
                                    129 	.globl _P7M0
                                    130 	.globl _P7M1
                                    131 	.globl _IP3
                                    132 	.globl _ADCCFG
                                    133 	.globl _USBCLK
                                    134 	.globl _VRTRIM
                                    135 	.globl _P7
                                    136 	.globl _B
                                    137 	.globl _P6
                                    138 	.globl _ACC
                                    139 	.globl _T2L
                                    140 	.globl _T2H
                                    141 	.globl _T3L
                                    142 	.globl _T3H
                                    143 	.globl _T4L
                                    144 	.globl _T4H
                                    145 	.globl _T4T3M
                                    146 	.globl _PSW
                                    147 	.globl _SPDAT
                                    148 	.globl _SPCTL
                                    149 	.globl _SPSTAT
                                    150 	.globl _P6M0
                                    151 	.globl _P6M1
                                    152 	.globl _P5M0
                                    153 	.globl _P5M1
                                    154 	.globl _P5
                                    155 	.globl _IAP_CONTR
                                    156 	.globl _IAP_TRIG
                                    157 	.globl _IAP_CMD
                                    158 	.globl _IAP_ADDRL
                                    159 	.globl _IAP_ADDRH
                                    160 	.globl _IAP_DATA
                                    161 	.globl _WDT_CONTR
                                    162 	.globl _P4
                                    163 	.globl _ADC_RESL
                                    164 	.globl _ADC_RES
                                    165 	.globl _ADC_CONTR
                                    166 	.globl _P_SW2
                                    167 	.globl _SADEN
                                    168 	.globl _IP
                                    169 	.globl _IPH
                                    170 	.globl _IP2H
                                    171 	.globl _IP2
                                    172 	.globl _P4M0
                                    173 	.globl _P4M1
                                    174 	.globl _P3M0
                                    175 	.globl _P3M1
                                    176 	.globl _P3
                                    177 	.globl _IE2
                                    178 	.globl _TA
                                    179 	.globl _S3BUF
                                    180 	.globl _S3CON
                                    181 	.globl _WKTCH
                                    182 	.globl _WKTCL
                                    183 	.globl _SADDR
                                    184 	.globl _IE
                                    185 	.globl _P_SW1
                                    186 	.globl _BUS_SPEED
                                    187 	.globl _P2
                                    188 	.globl _IRTRIM
                                    189 	.globl _LIRTRIM
                                    190 	.globl _IRCBAND
                                    191 	.globl _S2BUF
                                    192 	.globl _S2CON
                                    193 	.globl _SBUF
                                    194 	.globl _SCON
                                    195 	.globl _P2M0
                                    196 	.globl _P2M1
                                    197 	.globl _P0M0
                                    198 	.globl _P0M1
                                    199 	.globl _P1M0
                                    200 	.globl _P1M1
                                    201 	.globl _P1
                                    202 	.globl _INTCLKO
                                    203 	.globl _AUXR
                                    204 	.globl _TH1
                                    205 	.globl _TH0
                                    206 	.globl _TL1
                                    207 	.globl _TL0
                                    208 	.globl _TMOD
                                    209 	.globl _TCON
                                    210 	.globl _PCON
                                    211 	.globl _S4BUF
                                    212 	.globl _S4CON
                                    213 	.globl _DPH
                                    214 	.globl _DPL
                                    215 	.globl _SP
                                    216 	.globl _P0
                                    217 	.globl _uart_init
                                    218 	.globl _uart_send
                                    219 	.globl _uart_rx_ready
                                    220 ;--------------------------------------------------------
                                    221 ; special function registers
                                    222 ;--------------------------------------------------------
                                    223 	.area RSEG    (ABS,DATA)
      000000                        224 	.org 0x0000
                           000080   225 _P0	=	0x0080
                           000081   226 _SP	=	0x0081
                           000082   227 _DPL	=	0x0082
                           000083   228 _DPH	=	0x0083
                           000084   229 _S4CON	=	0x0084
                           000085   230 _S4BUF	=	0x0085
                           000087   231 _PCON	=	0x0087
                           000088   232 _TCON	=	0x0088
                           000089   233 _TMOD	=	0x0089
                           00008A   234 _TL0	=	0x008a
                           00008B   235 _TL1	=	0x008b
                           00008C   236 _TH0	=	0x008c
                           00008D   237 _TH1	=	0x008d
                           00008E   238 _AUXR	=	0x008e
                           00008F   239 _INTCLKO	=	0x008f
                           000090   240 _P1	=	0x0090
                           000091   241 _P1M1	=	0x0091
                           000092   242 _P1M0	=	0x0092
                           000093   243 _P0M1	=	0x0093
                           000094   244 _P0M0	=	0x0094
                           000095   245 _P2M1	=	0x0095
                           000096   246 _P2M0	=	0x0096
                           000098   247 _SCON	=	0x0098
                           000099   248 _SBUF	=	0x0099
                           00009A   249 _S2CON	=	0x009a
                           00009B   250 _S2BUF	=	0x009b
                           00009D   251 _IRCBAND	=	0x009d
                           00009E   252 _LIRTRIM	=	0x009e
                           00009F   253 _IRTRIM	=	0x009f
                           0000A0   254 _P2	=	0x00a0
                           0000A1   255 _BUS_SPEED	=	0x00a1
                           0000A2   256 _P_SW1	=	0x00a2
                           0000A8   257 _IE	=	0x00a8
                           0000A9   258 _SADDR	=	0x00a9
                           0000AA   259 _WKTCL	=	0x00aa
                           0000AB   260 _WKTCH	=	0x00ab
                           0000AC   261 _S3CON	=	0x00ac
                           0000AD   262 _S3BUF	=	0x00ad
                           0000AE   263 _TA	=	0x00ae
                           0000AF   264 _IE2	=	0x00af
                           0000B0   265 _P3	=	0x00b0
                           0000B1   266 _P3M1	=	0x00b1
                           0000B2   267 _P3M0	=	0x00b2
                           0000B3   268 _P4M1	=	0x00b3
                           0000B4   269 _P4M0	=	0x00b4
                           0000B5   270 _IP2	=	0x00b5
                           0000B6   271 _IP2H	=	0x00b6
                           0000B7   272 _IPH	=	0x00b7
                           0000B8   273 _IP	=	0x00b8
                           0000B9   274 _SADEN	=	0x00b9
                           0000BA   275 _P_SW2	=	0x00ba
                           0000BC   276 _ADC_CONTR	=	0x00bc
                           0000BD   277 _ADC_RES	=	0x00bd
                           0000BE   278 _ADC_RESL	=	0x00be
                           0000C0   279 _P4	=	0x00c0
                           0000C1   280 _WDT_CONTR	=	0x00c1
                           0000C2   281 _IAP_DATA	=	0x00c2
                           0000C3   282 _IAP_ADDRH	=	0x00c3
                           0000C4   283 _IAP_ADDRL	=	0x00c4
                           0000C5   284 _IAP_CMD	=	0x00c5
                           0000C6   285 _IAP_TRIG	=	0x00c6
                           0000C7   286 _IAP_CONTR	=	0x00c7
                           0000C8   287 _P5	=	0x00c8
                           0000C9   288 _P5M1	=	0x00c9
                           0000CA   289 _P5M0	=	0x00ca
                           0000CB   290 _P6M1	=	0x00cb
                           0000CC   291 _P6M0	=	0x00cc
                           0000CD   292 _SPSTAT	=	0x00cd
                           0000CE   293 _SPCTL	=	0x00ce
                           0000CF   294 _SPDAT	=	0x00cf
                           0000D0   295 _PSW	=	0x00d0
                           0000D1   296 _T4T3M	=	0x00d1
                           0000D2   297 _T4H	=	0x00d2
                           0000D3   298 _T4L	=	0x00d3
                           0000D4   299 _T3H	=	0x00d4
                           0000D5   300 _T3L	=	0x00d5
                           0000D6   301 _T2H	=	0x00d6
                           0000D7   302 _T2L	=	0x00d7
                           0000E0   303 _ACC	=	0x00e0
                           0000E8   304 _P6	=	0x00e8
                           0000F0   305 _B	=	0x00f0
                           0000F8   306 _P7	=	0x00f8
                           0000A6   307 _VRTRIM	=	0x00a6
                           0000DC   308 _USBCLK	=	0x00dc
                           0000DE   309 _ADCCFG	=	0x00de
                           0000DF   310 _IP3	=	0x00df
                           0000E1   311 _P7M1	=	0x00e1
                           0000E2   312 _P7M0	=	0x00e2
                           0000E3   313 _DPS	=	0x00e3
                           0000E4   314 _DPL1	=	0x00e4
                           0000E5   315 _DPH1	=	0x00e5
                           0000E6   316 _CMPCR1	=	0x00e6
                           0000E7   317 _CMPCR2	=	0x00e7
                           0000EC   318 _USBDAT	=	0x00ec
                           0000EE   319 _IP3H	=	0x00ee
                           0000EF   320 _AUXINTIF	=	0x00ef
                           0000F4   321 _USBCON	=	0x00f4
                           0000F5   322 _IAP_TPS	=	0x00f5
                           0000FC   323 _USBADR	=	0x00fc
                           0000FF   324 _RSTCFG	=	0x00ff
                                    325 ;--------------------------------------------------------
                                    326 ; special function bits
                                    327 ;--------------------------------------------------------
                                    328 	.area RSEG    (ABS,DATA)
      000000                        329 	.org 0x0000
                           000080   330 _P00	=	0x0080
                           000081   331 _P01	=	0x0081
                           000082   332 _P02	=	0x0082
                           000083   333 _P03	=	0x0083
                           000084   334 _P04	=	0x0084
                           000085   335 _P05	=	0x0085
                           000086   336 _P06	=	0x0086
                           000087   337 _P07	=	0x0087
                           00008F   338 _TF1	=	0x008f
                           00008E   339 _TR1	=	0x008e
                           00008D   340 _TF0	=	0x008d
                           00008C   341 _TR0	=	0x008c
                           00008B   342 _IE1	=	0x008b
                           00008A   343 _IT1	=	0x008a
                           000089   344 _IE0	=	0x0089
                           000088   345 _IT0	=	0x0088
                           000090   346 _P10	=	0x0090
                           000091   347 _P11	=	0x0091
                           000092   348 _P12	=	0x0092
                           000093   349 _P13	=	0x0093
                           000094   350 _P14	=	0x0094
                           000095   351 _P15	=	0x0095
                           000096   352 _P16	=	0x0096
                           000097   353 _P17	=	0x0097
                           00009F   354 _SM0	=	0x009f
                           00009E   355 _SM1	=	0x009e
                           00009D   356 _SM2	=	0x009d
                           00009C   357 _REN	=	0x009c
                           00009B   358 _TB8	=	0x009b
                           00009A   359 _RB8	=	0x009a
                           000099   360 _TI	=	0x0099
                           000098   361 _RI	=	0x0098
                           0000A0   362 _P20	=	0x00a0
                           0000A1   363 _P21	=	0x00a1
                           0000A2   364 _P22	=	0x00a2
                           0000A3   365 _P23	=	0x00a3
                           0000A4   366 _P24	=	0x00a4
                           0000A5   367 _P25	=	0x00a5
                           0000A6   368 _P26	=	0x00a6
                           0000A7   369 _P27	=	0x00a7
                           0000AF   370 _EA	=	0x00af
                           0000AE   371 _ELVD	=	0x00ae
                           0000AD   372 _EADC	=	0x00ad
                           0000AC   373 _ES	=	0x00ac
                           0000AB   374 _ET1	=	0x00ab
                           0000AA   375 _EX1	=	0x00aa
                           0000A9   376 _ET0	=	0x00a9
                           0000A8   377 _EX0	=	0x00a8
                           0000B0   378 _P30	=	0x00b0
                           0000B1   379 _P31	=	0x00b1
                           0000B2   380 _P32	=	0x00b2
                           0000B3   381 _P33	=	0x00b3
                           0000B4   382 _P34	=	0x00b4
                           0000B5   383 _P35	=	0x00b5
                           0000B6   384 _P36	=	0x00b6
                           0000B7   385 _P37	=	0x00b7
                           0000BF   386 _PPCA	=	0x00bf
                           0000BE   387 _PLVD	=	0x00be
                           0000BD   388 _PADC	=	0x00bd
                           0000BC   389 _PS	=	0x00bc
                           0000BB   390 _PT1	=	0x00bb
                           0000BA   391 _PX1	=	0x00ba
                           0000B9   392 _PT0	=	0x00b9
                           0000B8   393 _PX0	=	0x00b8
                           0000C0   394 _P40	=	0x00c0
                           0000C1   395 _P41	=	0x00c1
                           0000C2   396 _P42	=	0x00c2
                           0000C3   397 _P43	=	0x00c3
                           0000C4   398 _P44	=	0x00c4
                           0000C5   399 _P45	=	0x00c5
                           0000C6   400 _P46	=	0x00c6
                           0000C7   401 _P47	=	0x00c7
                           0000C8   402 _P50	=	0x00c8
                           0000C9   403 _P51	=	0x00c9
                           0000CA   404 _P52	=	0x00ca
                           0000CB   405 _P53	=	0x00cb
                           0000CC   406 _P54	=	0x00cc
                           0000CD   407 _P55	=	0x00cd
                           0000CE   408 _P56	=	0x00ce
                           0000CF   409 _P57	=	0x00cf
                           0000D7   410 _CY	=	0x00d7
                           0000D6   411 _AC	=	0x00d6
                           0000D5   412 _F0	=	0x00d5
                           0000D4   413 _RS1	=	0x00d4
                           0000D3   414 _RS0	=	0x00d3
                           0000D2   415 _OV	=	0x00d2
                           0000D1   416 _F1	=	0x00d1
                           0000D0   417 _P	=	0x00d0
                           0000E8   418 _P60	=	0x00e8
                           0000E9   419 _P61	=	0x00e9
                           0000EA   420 _P62	=	0x00ea
                           0000EB   421 _P63	=	0x00eb
                           0000EC   422 _P64	=	0x00ec
                           0000ED   423 _P65	=	0x00ed
                           0000EE   424 _P66	=	0x00ee
                           0000EF   425 _P67	=	0x00ef
                           0000F8   426 _P70	=	0x00f8
                           0000F9   427 _P71	=	0x00f9
                           0000FA   428 _P72	=	0x00fa
                           0000FB   429 _P73	=	0x00fb
                           0000FC   430 _P74	=	0x00fc
                           0000FD   431 _P75	=	0x00fd
                           0000FE   432 _P76	=	0x00fe
                           0000FF   433 _P77	=	0x00ff
                                    434 ;--------------------------------------------------------
                                    435 ; overlayable register banks
                                    436 ;--------------------------------------------------------
                                    437 	.area REG_BANK_0	(REL,OVR,DATA)
      000000                        438 	.ds 8
                                    439 ;--------------------------------------------------------
                                    440 ; internal ram data
                                    441 ;--------------------------------------------------------
                                    442 	.area DSEG    (DATA)
                                    443 ;--------------------------------------------------------
                                    444 ; overlayable items in internal ram
                                    445 ;--------------------------------------------------------
                                    446 ;--------------------------------------------------------
                                    447 ; indirectly addressable internal ram data
                                    448 ;--------------------------------------------------------
                                    449 	.area ISEG    (DATA)
                                    450 ;--------------------------------------------------------
                                    451 ; absolute internal ram data
                                    452 ;--------------------------------------------------------
                                    453 	.area IABS    (ABS,DATA)
                                    454 	.area IABS    (ABS,DATA)
                                    455 ;--------------------------------------------------------
                                    456 ; bit data
                                    457 ;--------------------------------------------------------
                                    458 	.area BSEG    (BIT)
                                    459 ;--------------------------------------------------------
                                    460 ; paged external ram data
                                    461 ;--------------------------------------------------------
                                    462 	.area PSEG    (PAG,XDATA)
                                    463 ;--------------------------------------------------------
                                    464 ; uninitialized external ram data
                                    465 ;--------------------------------------------------------
                                    466 	.area XSEG    (XDATA)
                                    467 ;--------------------------------------------------------
                                    468 ; absolute external ram data
                                    469 ;--------------------------------------------------------
                                    470 	.area XABS    (ABS,XDATA)
                                    471 ;--------------------------------------------------------
                                    472 ; initialized external ram data
                                    473 ;--------------------------------------------------------
                                    474 	.area XISEG   (XDATA)
                                    475 	.area HOME    (CODE)
                                    476 	.area GSINIT0 (CODE)
                                    477 	.area GSINIT1 (CODE)
                                    478 	.area GSINIT2 (CODE)
                                    479 	.area GSINIT3 (CODE)
                                    480 	.area GSINIT4 (CODE)
                                    481 	.area GSINIT5 (CODE)
                                    482 	.area GSINIT  (CODE)
                                    483 	.area GSFINAL (CODE)
                                    484 	.area CSEG    (CODE)
                                    485 ;--------------------------------------------------------
                                    486 ; global & static initialisations
                                    487 ;--------------------------------------------------------
                                    488 	.area HOME    (CODE)
                                    489 	.area GSINIT  (CODE)
                                    490 	.area GSFINAL (CODE)
                                    491 	.area GSINIT  (CODE)
                                    492 ;--------------------------------------------------------
                                    493 ; Home
                                    494 ;--------------------------------------------------------
                                    495 	.area HOME    (CODE)
                                    496 	.area HOME    (CODE)
                                    497 ;--------------------------------------------------------
                                    498 ; code
                                    499 ;--------------------------------------------------------
                                    500 	.area CSEG    (CODE)
                                    501 ;------------------------------------------------------------
                                    502 ;Allocation info for local variables in function 'uart_init'
                                    503 ;------------------------------------------------------------
                                    504 ;baud                      Allocated to registers 
                                    505 ;------------------------------------------------------------
                                    506 ;	src\uart.c:4: void uart_init(uint32_t baud) {
                                    507 ;	-----------------------------------------
                                    508 ;	 function uart_init
                                    509 ;	-----------------------------------------
      00091F                        510 _uart_init:
                           000007   511 	ar7 = 0x07
                           000006   512 	ar6 = 0x06
                           000005   513 	ar5 = 0x05
                           000004   514 	ar4 = 0x04
                           000003   515 	ar3 = 0x03
                           000002   516 	ar2 = 0x02
                           000001   517 	ar1 = 0x01
                           000000   518 	ar0 = 0x00
      00091F 85 82 45         [24]  519 	mov	_UART1_Config8bitUart_PARM_3,dpl
      000922 85 83 46         [24]  520 	mov	(_UART1_Config8bitUart_PARM_3 + 1),dph
      000925 85 F0 47         [24]  521 	mov	(_UART1_Config8bitUart_PARM_3 + 2),b
      000928 F5 48            [12]  522 	mov	(_UART1_Config8bitUart_PARM_3 + 3),a
                                    523 ;	src\uart.c:5: UART1_Config8bitUart(UART1_BaudSource_Timer2, HAL_State_ON, baud);
      00092A 75 44 01         [24]  524 	mov	_UART1_Config8bitUart_PARM_2,#0x01
      00092D 75 82 01         [24]  525 	mov	dpl, #0x01
                                    526 ;	src\uart.c:6: }
      000930 02 0C B5         [24]  527 	ljmp	_UART1_Config8bitUart
                                    528 ;------------------------------------------------------------
                                    529 ;Allocation info for local variables in function 'uart_send'
                                    530 ;------------------------------------------------------------
                                    531 ;data                      Allocated to registers 
                                    532 ;------------------------------------------------------------
                                    533 ;	src\uart.c:8: void uart_send(uint8_t data) {
                                    534 ;	-----------------------------------------
                                    535 ;	 function uart_send
                                    536 ;	-----------------------------------------
      000933                        537 _uart_send:
                                    538 ;	src\uart.c:9: UART1_TxChar(data);
                                    539 ;	src\uart.c:10: }
      000933 02 0D 17         [24]  540 	ljmp	_UART1_TxChar
                                    541 ;------------------------------------------------------------
                                    542 ;Allocation info for local variables in function 'uart_rx_ready'
                                    543 ;------------------------------------------------------------
                                    544 ;	src\uart.c:12: uint8_t uart_rx_ready(void) {
                                    545 ;	-----------------------------------------
                                    546 ;	 function uart_rx_ready
                                    547 ;	-----------------------------------------
      000936                        548 _uart_rx_ready:
                                    549 ;	src\uart.c:13: return RI ? 1 : 0;
      000936 30 98 04         [24]  550 	jnb	_RI,00103$
      000939 7F 01            [12]  551 	mov	r7,#0x01
      00093B 80 02            [24]  552 	sjmp	00104$
      00093D                        553 00103$:
      00093D 7F 00            [12]  554 	mov	r7,#0x00
      00093F                        555 00104$:
      00093F 8F 82            [24]  556 	mov	dpl,r7
                                    557 ;	src\uart.c:14: }
      000941 22               [24]  558 	ret
                                    559 	.area CSEG    (CODE)
                                    560 	.area CONST   (CODE)
                                    561 	.area XINIT   (CODE)
                                    562 	.area CABS    (ABS,CODE)
