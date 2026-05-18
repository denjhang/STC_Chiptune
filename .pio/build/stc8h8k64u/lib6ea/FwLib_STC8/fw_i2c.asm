;--------------------------------------------------------
; File Created by SDCC : free open source ISO C Compiler 
; Version 4.4.0 #14620 (MINGW32)
;--------------------------------------------------------
	.module fw_i2c
	.optsdcc -mmcs51 --model-small
	
;--------------------------------------------------------
; Public variables in this module
;--------------------------------------------------------
	.globl _I2C_Read16BitAddr_PARM_4
	.globl _I2C_Read16BitAddr_PARM_3
	.globl _I2C_Read16BitAddr_PARM_2
	.globl _I2C_Write16BitAddr_PARM_4
	.globl _I2C_Write16BitAddr_PARM_3
	.globl _I2C_Write16BitAddr_PARM_2
	.globl _I2C_Read_PARM_4
	.globl _I2C_Read_PARM_3
	.globl _I2C_Read_PARM_2
	.globl _I2C_Write_PARM_4
	.globl _I2C_Write_PARM_3
	.globl _I2C_Write_PARM_2
	.globl _P77
	.globl _P76
	.globl _P75
	.globl _P74
	.globl _P73
	.globl _P72
	.globl _P71
	.globl _P70
	.globl _P67
	.globl _P66
	.globl _P65
	.globl _P64
	.globl _P63
	.globl _P62
	.globl _P61
	.globl _P60
	.globl _P
	.globl _F1
	.globl _OV
	.globl _RS0
	.globl _RS1
	.globl _F0
	.globl _AC
	.globl _CY
	.globl _P57
	.globl _P56
	.globl _P55
	.globl _P54
	.globl _P53
	.globl _P52
	.globl _P51
	.globl _P50
	.globl _P47
	.globl _P46
	.globl _P45
	.globl _P44
	.globl _P43
	.globl _P42
	.globl _P41
	.globl _P40
	.globl _PX0
	.globl _PT0
	.globl _PX1
	.globl _PT1
	.globl _PS
	.globl _PADC
	.globl _PLVD
	.globl _PPCA
	.globl _P37
	.globl _P36
	.globl _P35
	.globl _P34
	.globl _P33
	.globl _P32
	.globl _P31
	.globl _P30
	.globl _EX0
	.globl _ET0
	.globl _EX1
	.globl _ET1
	.globl _ES
	.globl _EADC
	.globl _ELVD
	.globl _EA
	.globl _P27
	.globl _P26
	.globl _P25
	.globl _P24
	.globl _P23
	.globl _P22
	.globl _P21
	.globl _P20
	.globl _RI
	.globl _TI
	.globl _RB8
	.globl _TB8
	.globl _REN
	.globl _SM2
	.globl _SM1
	.globl _SM0
	.globl _P17
	.globl _P16
	.globl _P15
	.globl _P14
	.globl _P13
	.globl _P12
	.globl _P11
	.globl _P10
	.globl _IT0
	.globl _IE0
	.globl _IT1
	.globl _IE1
	.globl _TR0
	.globl _TF0
	.globl _TR1
	.globl _TF1
	.globl _P07
	.globl _P06
	.globl _P05
	.globl _P04
	.globl _P03
	.globl _P02
	.globl _P01
	.globl _P00
	.globl _RSTCFG
	.globl _USBADR
	.globl _IAP_TPS
	.globl _USBCON
	.globl _AUXINTIF
	.globl _IP3H
	.globl _USBDAT
	.globl _CMPCR2
	.globl _CMPCR1
	.globl _DPH1
	.globl _DPL1
	.globl _DPS
	.globl _P7M0
	.globl _P7M1
	.globl _IP3
	.globl _ADCCFG
	.globl _USBCLK
	.globl _VRTRIM
	.globl _P7
	.globl _B
	.globl _P6
	.globl _ACC
	.globl _T2L
	.globl _T2H
	.globl _T3L
	.globl _T3H
	.globl _T4L
	.globl _T4H
	.globl _T4T3M
	.globl _PSW
	.globl _SPDAT
	.globl _SPCTL
	.globl _SPSTAT
	.globl _P6M0
	.globl _P6M1
	.globl _P5M0
	.globl _P5M1
	.globl _P5
	.globl _IAP_CONTR
	.globl _IAP_TRIG
	.globl _IAP_CMD
	.globl _IAP_ADDRL
	.globl _IAP_ADDRH
	.globl _IAP_DATA
	.globl _WDT_CONTR
	.globl _P4
	.globl _ADC_RESL
	.globl _ADC_RES
	.globl _ADC_CONTR
	.globl _P_SW2
	.globl _SADEN
	.globl _IP
	.globl _IPH
	.globl _IP2H
	.globl _IP2
	.globl _P4M0
	.globl _P4M1
	.globl _P3M0
	.globl _P3M1
	.globl _P3
	.globl _IE2
	.globl _TA
	.globl _S3BUF
	.globl _S3CON
	.globl _WKTCH
	.globl _WKTCL
	.globl _SADDR
	.globl _IE
	.globl _P_SW1
	.globl _BUS_SPEED
	.globl _P2
	.globl _IRTRIM
	.globl _LIRTRIM
	.globl _IRCBAND
	.globl _S2BUF
	.globl _S2CON
	.globl _SBUF
	.globl _SCON
	.globl _P2M0
	.globl _P2M1
	.globl _P0M0
	.globl _P0M1
	.globl _P1M0
	.globl _P1M1
	.globl _P1
	.globl _INTCLKO
	.globl _AUXR
	.globl _TH1
	.globl _TH0
	.globl _TL1
	.globl _TL0
	.globl _TMOD
	.globl _TCON
	.globl _PCON
	.globl _S4BUF
	.globl _S4CON
	.globl _DPH
	.globl _DPL
	.globl _SP
	.globl _P0
	.globl _I2C_Write
	.globl _I2C_Read
	.globl _I2C_Write16BitAddr
	.globl _I2C_Read16BitAddr
;--------------------------------------------------------
; special function registers
;--------------------------------------------------------
	.area RSEG    (ABS,DATA)
	.org 0x0000
_P0	=	0x0080
_SP	=	0x0081
_DPL	=	0x0082
_DPH	=	0x0083
_S4CON	=	0x0084
_S4BUF	=	0x0085
_PCON	=	0x0087
_TCON	=	0x0088
_TMOD	=	0x0089
_TL0	=	0x008a
_TL1	=	0x008b
_TH0	=	0x008c
_TH1	=	0x008d
_AUXR	=	0x008e
_INTCLKO	=	0x008f
_P1	=	0x0090
_P1M1	=	0x0091
_P1M0	=	0x0092
_P0M1	=	0x0093
_P0M0	=	0x0094
_P2M1	=	0x0095
_P2M0	=	0x0096
_SCON	=	0x0098
_SBUF	=	0x0099
_S2CON	=	0x009a
_S2BUF	=	0x009b
_IRCBAND	=	0x009d
_LIRTRIM	=	0x009e
_IRTRIM	=	0x009f
_P2	=	0x00a0
_BUS_SPEED	=	0x00a1
_P_SW1	=	0x00a2
_IE	=	0x00a8
_SADDR	=	0x00a9
_WKTCL	=	0x00aa
_WKTCH	=	0x00ab
_S3CON	=	0x00ac
_S3BUF	=	0x00ad
_TA	=	0x00ae
_IE2	=	0x00af
_P3	=	0x00b0
_P3M1	=	0x00b1
_P3M0	=	0x00b2
_P4M1	=	0x00b3
_P4M0	=	0x00b4
_IP2	=	0x00b5
_IP2H	=	0x00b6
_IPH	=	0x00b7
_IP	=	0x00b8
_SADEN	=	0x00b9
_P_SW2	=	0x00ba
_ADC_CONTR	=	0x00bc
_ADC_RES	=	0x00bd
_ADC_RESL	=	0x00be
_P4	=	0x00c0
_WDT_CONTR	=	0x00c1
_IAP_DATA	=	0x00c2
_IAP_ADDRH	=	0x00c3
_IAP_ADDRL	=	0x00c4
_IAP_CMD	=	0x00c5
_IAP_TRIG	=	0x00c6
_IAP_CONTR	=	0x00c7
_P5	=	0x00c8
_P5M1	=	0x00c9
_P5M0	=	0x00ca
_P6M1	=	0x00cb
_P6M0	=	0x00cc
_SPSTAT	=	0x00cd
_SPCTL	=	0x00ce
_SPDAT	=	0x00cf
_PSW	=	0x00d0
_T4T3M	=	0x00d1
_T4H	=	0x00d2
_T4L	=	0x00d3
_T3H	=	0x00d4
_T3L	=	0x00d5
_T2H	=	0x00d6
_T2L	=	0x00d7
_ACC	=	0x00e0
_P6	=	0x00e8
_B	=	0x00f0
_P7	=	0x00f8
_VRTRIM	=	0x00a6
_USBCLK	=	0x00dc
_ADCCFG	=	0x00de
_IP3	=	0x00df
_P7M1	=	0x00e1
_P7M0	=	0x00e2
_DPS	=	0x00e3
_DPL1	=	0x00e4
_DPH1	=	0x00e5
_CMPCR1	=	0x00e6
_CMPCR2	=	0x00e7
_USBDAT	=	0x00ec
_IP3H	=	0x00ee
_AUXINTIF	=	0x00ef
_USBCON	=	0x00f4
_IAP_TPS	=	0x00f5
_USBADR	=	0x00fc
_RSTCFG	=	0x00ff
;--------------------------------------------------------
; special function bits
;--------------------------------------------------------
	.area RSEG    (ABS,DATA)
	.org 0x0000
_P00	=	0x0080
_P01	=	0x0081
_P02	=	0x0082
_P03	=	0x0083
_P04	=	0x0084
_P05	=	0x0085
_P06	=	0x0086
_P07	=	0x0087
_TF1	=	0x008f
_TR1	=	0x008e
_TF0	=	0x008d
_TR0	=	0x008c
_IE1	=	0x008b
_IT1	=	0x008a
_IE0	=	0x0089
_IT0	=	0x0088
_P10	=	0x0090
_P11	=	0x0091
_P12	=	0x0092
_P13	=	0x0093
_P14	=	0x0094
_P15	=	0x0095
_P16	=	0x0096
_P17	=	0x0097
_SM0	=	0x009f
_SM1	=	0x009e
_SM2	=	0x009d
_REN	=	0x009c
_TB8	=	0x009b
_RB8	=	0x009a
_TI	=	0x0099
_RI	=	0x0098
_P20	=	0x00a0
_P21	=	0x00a1
_P22	=	0x00a2
_P23	=	0x00a3
_P24	=	0x00a4
_P25	=	0x00a5
_P26	=	0x00a6
_P27	=	0x00a7
_EA	=	0x00af
_ELVD	=	0x00ae
_EADC	=	0x00ad
_ES	=	0x00ac
_ET1	=	0x00ab
_EX1	=	0x00aa
_ET0	=	0x00a9
_EX0	=	0x00a8
_P30	=	0x00b0
_P31	=	0x00b1
_P32	=	0x00b2
_P33	=	0x00b3
_P34	=	0x00b4
_P35	=	0x00b5
_P36	=	0x00b6
_P37	=	0x00b7
_PPCA	=	0x00bf
_PLVD	=	0x00be
_PADC	=	0x00bd
_PS	=	0x00bc
_PT1	=	0x00bb
_PX1	=	0x00ba
_PT0	=	0x00b9
_PX0	=	0x00b8
_P40	=	0x00c0
_P41	=	0x00c1
_P42	=	0x00c2
_P43	=	0x00c3
_P44	=	0x00c4
_P45	=	0x00c5
_P46	=	0x00c6
_P47	=	0x00c7
_P50	=	0x00c8
_P51	=	0x00c9
_P52	=	0x00ca
_P53	=	0x00cb
_P54	=	0x00cc
_P55	=	0x00cd
_P56	=	0x00ce
_P57	=	0x00cf
_CY	=	0x00d7
_AC	=	0x00d6
_F0	=	0x00d5
_RS1	=	0x00d4
_RS0	=	0x00d3
_OV	=	0x00d2
_F1	=	0x00d1
_P	=	0x00d0
_P60	=	0x00e8
_P61	=	0x00e9
_P62	=	0x00ea
_P63	=	0x00eb
_P64	=	0x00ec
_P65	=	0x00ed
_P66	=	0x00ee
_P67	=	0x00ef
_P70	=	0x00f8
_P71	=	0x00f9
_P72	=	0x00fa
_P73	=	0x00fb
_P74	=	0x00fc
_P75	=	0x00fd
_P76	=	0x00fe
_P77	=	0x00ff
;--------------------------------------------------------
; overlayable register banks
;--------------------------------------------------------
	.area REG_BANK_0	(REL,OVR,DATA)
	.ds 8
;--------------------------------------------------------
; internal ram data
;--------------------------------------------------------
	.area DSEG    (DATA)
;--------------------------------------------------------
; overlayable items in internal ram
;--------------------------------------------------------
	.area	OSEG    (OVR,DATA)
_I2C_Write_PARM_2:
	.ds 1
_I2C_Write_PARM_3:
	.ds 3
_I2C_Write_PARM_4:
	.ds 2
	.area	OSEG    (OVR,DATA)
_I2C_Read_PARM_2:
	.ds 1
_I2C_Read_PARM_3:
	.ds 3
_I2C_Read_PARM_4:
	.ds 2
	.area	OSEG    (OVR,DATA)
_I2C_Write16BitAddr_PARM_2:
	.ds 2
_I2C_Write16BitAddr_PARM_3:
	.ds 3
_I2C_Write16BitAddr_PARM_4:
	.ds 2
	.area	OSEG    (OVR,DATA)
_I2C_Read16BitAddr_PARM_2:
	.ds 2
_I2C_Read16BitAddr_PARM_3:
	.ds 3
_I2C_Read16BitAddr_PARM_4:
	.ds 2
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
;Allocation info for local variables in function 'I2C_Write'
;------------------------------------------------------------
;memAddr                   Allocated with name '_I2C_Write_PARM_2'
;dat                       Allocated with name '_I2C_Write_PARM_3'
;size                      Allocated with name '_I2C_Write_PARM_4'
;devAddr                   Allocated to registers r7 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_i2c.c:18: uint8_t I2C_Write(uint8_t devAddr, uint8_t memAddr, uint8_t *dat, uint16_t size)
;	-----------------------------------------
;	 function I2C_Write
;	-----------------------------------------
_I2C_Write:
	ar7 = 0x07
	ar6 = 0x06
	ar5 = 0x05
	ar4 = 0x04
	ar3 = 0x03
	ar2 = 0x02
	ar1 = 0x01
	ar0 = 0x00
	mov	r7, dpl
;	lib\FwLib_STC8\src\fw_i2c.c:20: SFRX_ON();
	orl	_P_SW2,#0x80
;	lib\FwLib_STC8\src\fw_i2c.c:21: I2C_MasterStart();
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x01
	movx	@dptr,a
00101$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00101$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:22: I2C_MasterSendData(devAddr & 0xFE);
	anl	ar7,#0xfe
	mov	dptr,#0xfe86
	mov	a,r7
	movx	@dptr,a
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x02
	movx	@dptr,a
00104$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00104$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:23: I2C_MasterRxAck();
	dec	dpl
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x03
	movx	@dptr,a
00110$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00110$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:24: I2C_MasterSendData(memAddr);
	mov	dptr,#0xfe86
	mov	a,_I2C_Write_PARM_2
	movx	@dptr,a
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x02
	movx	@dptr,a
00113$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00113$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:25: I2C_MasterRxAck();
	dec	dpl
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x03
	movx	@dptr,a
00119$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00119$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:26: while(size--)
	mov	r5,_I2C_Write_PARM_3
	mov	r6,(_I2C_Write_PARM_3 + 1)
	mov	r7,(_I2C_Write_PARM_3 + 2)
	mov	r3,_I2C_Write_PARM_4
	mov	r4,(_I2C_Write_PARM_4 + 1)
00131$:
	mov	ar1,r3
	mov	ar2,r4
	dec	r3
	cjne	r3,#0xff,00253$
	dec	r4
00253$:
	mov	a,r1
	orl	a,r2
	jz	00133$
;	lib\FwLib_STC8\src\fw_i2c.c:28: I2C_MasterSendData(*dat++);
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	lcall	__gptrget
	mov	r2,a
	inc	dptr
	mov	r5,dpl
	mov	r6,dph
	mov	dptr,#0xfe86
	mov	a,r2
	movx	@dptr,a
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r2,a
	mov	a,#0xf0
	anl	a,r2
	orl	a,#0x02
	movx	@dptr,a
00122$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00122$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:29: I2C_MasterRxAck();
	dec	dpl
	movx	a,@dptr
	mov	r2,a
	mov	a,#0xf0
	anl	a,r2
	orl	a,#0x03
	movx	@dptr,a
00128$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00128$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
	sjmp	00131$
00133$:
;	lib\FwLib_STC8\src\fw_i2c.c:31: I2C_MasterStop();
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x06
	movx	@dptr,a
00134$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00134$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:32: SFRX_OFF();
	anl	_P_SW2,#0x7f
;	lib\FwLib_STC8\src\fw_i2c.c:33: return HAL_OK;
	mov	dpl, #0x00
;	lib\FwLib_STC8\src\fw_i2c.c:34: }
	ret
;------------------------------------------------------------
;Allocation info for local variables in function 'I2C_Read'
;------------------------------------------------------------
;memAddr                   Allocated with name '_I2C_Read_PARM_2'
;buf                       Allocated with name '_I2C_Read_PARM_3'
;size                      Allocated with name '_I2C_Read_PARM_4'
;devAddr                   Allocated to registers r7 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_i2c.c:36: uint8_t I2C_Read(uint8_t devAddr, uint8_t memAddr, uint8_t *buf, uint16_t size)
;	-----------------------------------------
;	 function I2C_Read
;	-----------------------------------------
_I2C_Read:
	mov	r7, dpl
;	lib\FwLib_STC8\src\fw_i2c.c:38: SFRX_ON();
	orl	_P_SW2,#0x80
;	lib\FwLib_STC8\src\fw_i2c.c:39: I2C_MasterStart();
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x01
	movx	@dptr,a
00101$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00101$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:40: I2C_MasterSendData(devAddr & 0xFE);
	mov	a,#0xfe
	anl	a,r7
	mov	dptr,#0xfe86
	movx	@dptr,a
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x02
	movx	@dptr,a
00104$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00104$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:41: I2C_MasterRxAck();
	dec	dpl
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x03
	movx	@dptr,a
00110$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00110$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:42: I2C_MasterSendData(memAddr);
	mov	dptr,#0xfe86
	mov	a,_I2C_Read_PARM_2
	movx	@dptr,a
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x02
	movx	@dptr,a
00113$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00113$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:43: I2C_MasterRxAck();
	dec	dpl
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x03
	movx	@dptr,a
00119$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00119$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:44: I2C_MasterStart();
	dec	dpl
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x01
	movx	@dptr,a
00122$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00122$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:45: I2C_MasterSendData(devAddr | 0x01);
	orl	ar7,#0x01
	mov	dptr,#0xfe86
	mov	a,r7
	movx	@dptr,a
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x02
	movx	@dptr,a
00125$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00125$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:46: I2C_MasterRxAck();
	dec	dpl
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x03
	movx	@dptr,a
00131$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00131$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:47: while(size--)
	mov	r5,_I2C_Read_PARM_3
	mov	r6,(_I2C_Read_PARM_3 + 1)
	mov	r7,(_I2C_Read_PARM_3 + 2)
	mov	r3,_I2C_Read_PARM_4
	mov	r4,(_I2C_Read_PARM_4 + 1)
00152$:
	mov	ar1,r3
	mov	ar2,r4
	dec	r3
	cjne	r3,#0xff,00331$
	dec	r4
00331$:
	mov	a,r1
	orl	a,r2
	jnz	00332$
	ljmp	00154$
00332$:
;	lib\FwLib_STC8\src\fw_i2c.c:49: I2C_SendMasterCmd(I2C_MasterCmd_Recv);
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r2,a
	mov	a,#0xf0
	anl	a,r2
	orl	a,#0x04
	movx	@dptr,a
00134$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00134$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:50: *buf++ = I2CRXD;
	mov	dptr,#0xfe87
	movx	a,@dptr
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	lcall	__gptrput
	inc	dptr
	mov	r5,dpl
	mov	r6,dph
;	lib\FwLib_STC8\src\fw_i2c.c:51: if (size == 0)
	mov	a,r3
	orl	a,r4
	jnz	00146$
;	lib\FwLib_STC8\src\fw_i2c.c:53: I2C_MasterNAck();
	mov	dptr,#0xfe82
	movx	a,@dptr
	orl	a,#0x01
	movx	@dptr,a
	dec	dpl
	movx	a,@dptr
	mov	r2,a
	mov	a,#0xf0
	anl	a,r2
	orl	a,#0x05
	movx	@dptr,a
00137$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00137$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:57: I2C_MasterAck();
	sjmp	00152$
00146$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xfe
	movx	@dptr,a
	dec	dpl
	movx	a,@dptr
	mov	r2,a
	mov	a,#0xf0
	anl	a,r2
	orl	a,#0x05
	movx	@dptr,a
00143$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00143$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
	ljmp	00152$
00154$:
;	lib\FwLib_STC8\src\fw_i2c.c:60: I2C_MasterStop();
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x06
	movx	@dptr,a
00155$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00155$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:61: SFRX_OFF();
	anl	_P_SW2,#0x7f
;	lib\FwLib_STC8\src\fw_i2c.c:62: return HAL_OK;
	mov	dpl, #0x00
;	lib\FwLib_STC8\src\fw_i2c.c:63: }
	ret
;------------------------------------------------------------
;Allocation info for local variables in function 'I2C_Write16BitAddr'
;------------------------------------------------------------
;memAddr                   Allocated with name '_I2C_Write16BitAddr_PARM_2'
;dat                       Allocated with name '_I2C_Write16BitAddr_PARM_3'
;size                      Allocated with name '_I2C_Write16BitAddr_PARM_4'
;devAddr                   Allocated to registers r7 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_i2c.c:65: uint8_t I2C_Write16BitAddr(uint8_t devAddr, uint16_t memAddr, uint8_t *dat, uint16_t size)
;	-----------------------------------------
;	 function I2C_Write16BitAddr
;	-----------------------------------------
_I2C_Write16BitAddr:
	mov	r7, dpl
;	lib\FwLib_STC8\src\fw_i2c.c:67: SFRX_ON();
	orl	_P_SW2,#0x80
;	lib\FwLib_STC8\src\fw_i2c.c:68: I2C_MasterStart();
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x01
	movx	@dptr,a
00101$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00101$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:69: I2C_MasterSendData(devAddr & 0xFE);
	anl	ar7,#0xfe
	mov	dptr,#0xfe86
	mov	a,r7
	movx	@dptr,a
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x02
	movx	@dptr,a
00104$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00104$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:70: I2C_MasterRxAck();
	dec	dpl
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x03
	movx	@dptr,a
00110$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00110$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:71: I2C_MasterSendData(memAddr >> 8);
	mov	r7,(_I2C_Write16BitAddr_PARM_2 + 1)
	mov	dptr,#0xfe86
	mov	a,r7
	movx	@dptr,a
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x02
	movx	@dptr,a
00113$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00113$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:72: I2C_MasterRxAck();
	dec	dpl
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x03
	movx	@dptr,a
00119$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00119$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:73: I2C_MasterSendData(memAddr & 0xFF);
	mov	r7,_I2C_Write16BitAddr_PARM_2
	mov	dptr,#0xfe86
	mov	a,r7
	movx	@dptr,a
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x02
	movx	@dptr,a
00122$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00122$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:74: I2C_MasterRxAck();
	dec	dpl
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x03
	movx	@dptr,a
00128$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00128$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:75: while(size--)
	mov	r5,_I2C_Write16BitAddr_PARM_3
	mov	r6,(_I2C_Write16BitAddr_PARM_3 + 1)
	mov	r7,(_I2C_Write16BitAddr_PARM_3 + 2)
	mov	r3,_I2C_Write16BitAddr_PARM_4
	mov	r4,(_I2C_Write16BitAddr_PARM_4 + 1)
00140$:
	mov	ar1,r3
	mov	ar2,r4
	dec	r3
	cjne	r3,#0xff,00288$
	dec	r4
00288$:
	mov	a,r1
	orl	a,r2
	jz	00142$
;	lib\FwLib_STC8\src\fw_i2c.c:77: I2C_MasterSendData(*dat++);
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	lcall	__gptrget
	mov	r2,a
	inc	dptr
	mov	r5,dpl
	mov	r6,dph
	mov	dptr,#0xfe86
	mov	a,r2
	movx	@dptr,a
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r2,a
	mov	a,#0xf0
	anl	a,r2
	orl	a,#0x02
	movx	@dptr,a
00131$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00131$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:78: I2C_MasterRxAck();
	dec	dpl
	movx	a,@dptr
	mov	r2,a
	mov	a,#0xf0
	anl	a,r2
	orl	a,#0x03
	movx	@dptr,a
00137$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00137$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
	sjmp	00140$
00142$:
;	lib\FwLib_STC8\src\fw_i2c.c:80: I2C_MasterStop();
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x06
	movx	@dptr,a
00143$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00143$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:81: SFRX_OFF();
	anl	_P_SW2,#0x7f
;	lib\FwLib_STC8\src\fw_i2c.c:82: return HAL_OK;
	mov	dpl, #0x00
;	lib\FwLib_STC8\src\fw_i2c.c:83: }
	ret
;------------------------------------------------------------
;Allocation info for local variables in function 'I2C_Read16BitAddr'
;------------------------------------------------------------
;memAddr                   Allocated with name '_I2C_Read16BitAddr_PARM_2'
;buf                       Allocated with name '_I2C_Read16BitAddr_PARM_3'
;size                      Allocated with name '_I2C_Read16BitAddr_PARM_4'
;devAddr                   Allocated to registers r7 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_i2c.c:85: uint8_t I2C_Read16BitAddr(uint8_t devAddr, uint16_t memAddr, uint8_t *buf, uint16_t size)
;	-----------------------------------------
;	 function I2C_Read16BitAddr
;	-----------------------------------------
_I2C_Read16BitAddr:
	mov	r7, dpl
;	lib\FwLib_STC8\src\fw_i2c.c:87: SFRX_ON();
	orl	_P_SW2,#0x80
;	lib\FwLib_STC8\src\fw_i2c.c:88: I2C_MasterStart();
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x01
	movx	@dptr,a
00101$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00101$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:89: I2C_MasterSendData(devAddr & 0xFE);
	mov	a,#0xfe
	anl	a,r7
	mov	dptr,#0xfe86
	movx	@dptr,a
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x02
	movx	@dptr,a
00104$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00104$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:90: I2C_MasterRxAck();
	dec	dpl
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x03
	movx	@dptr,a
00110$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00110$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:91: I2C_MasterSendData(memAddr >> 8);
	mov	r6,(_I2C_Read16BitAddr_PARM_2 + 1)
	mov	dptr,#0xfe86
	mov	a,r6
	movx	@dptr,a
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x02
	movx	@dptr,a
00113$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00113$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:92: I2C_MasterRxAck();
	dec	dpl
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x03
	movx	@dptr,a
00119$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00119$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:93: I2C_MasterSendData(memAddr & 0xFF);
	mov	r6,_I2C_Read16BitAddr_PARM_2
	mov	dptr,#0xfe86
	mov	a,r6
	movx	@dptr,a
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x02
	movx	@dptr,a
00122$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00122$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:94: I2C_MasterRxAck();
	dec	dpl
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x03
	movx	@dptr,a
00128$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00128$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:95: I2C_MasterStart();
	dec	dpl
	movx	a,@dptr
	mov	r6,a
	mov	a,#0xf0
	anl	a,r6
	orl	a,#0x01
	movx	@dptr,a
00131$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00131$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:96: I2C_MasterSendData(devAddr | 0x01);
	orl	ar7,#0x01
	mov	dptr,#0xfe86
	mov	a,r7
	movx	@dptr,a
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x02
	movx	@dptr,a
00134$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00134$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:97: I2C_MasterRxAck();
	dec	dpl
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x03
	movx	@dptr,a
00140$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00140$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:98: while(size--)
	mov	r5,_I2C_Read16BitAddr_PARM_3
	mov	r6,(_I2C_Read16BitAddr_PARM_3 + 1)
	mov	r7,(_I2C_Read16BitAddr_PARM_3 + 2)
	mov	r3,_I2C_Read16BitAddr_PARM_4
	mov	r4,(_I2C_Read16BitAddr_PARM_4 + 1)
00161$:
	mov	ar1,r3
	mov	ar2,r4
	dec	r3
	cjne	r3,#0xff,00366$
	dec	r4
00366$:
	mov	a,r1
	orl	a,r2
	jnz	00367$
	ljmp	00163$
00367$:
;	lib\FwLib_STC8\src\fw_i2c.c:100: I2C_SendMasterCmd(I2C_MasterCmd_Recv);
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r2,a
	mov	a,#0xf0
	anl	a,r2
	orl	a,#0x04
	movx	@dptr,a
00143$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00143$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:101: *buf++ = I2CRXD;
	mov	dptr,#0xfe87
	movx	a,@dptr
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	lcall	__gptrput
	inc	dptr
	mov	r5,dpl
	mov	r6,dph
;	lib\FwLib_STC8\src\fw_i2c.c:102: if (size == 0)
	mov	a,r3
	orl	a,r4
	jnz	00155$
;	lib\FwLib_STC8\src\fw_i2c.c:104: I2C_MasterNAck();
	mov	dptr,#0xfe82
	movx	a,@dptr
	orl	a,#0x01
	movx	@dptr,a
	dec	dpl
	movx	a,@dptr
	mov	r2,a
	mov	a,#0xf0
	anl	a,r2
	orl	a,#0x05
	movx	@dptr,a
00146$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00146$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:108: I2C_MasterAck();
	sjmp	00161$
00155$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xfe
	movx	@dptr,a
	dec	dpl
	movx	a,@dptr
	mov	r2,a
	mov	a,#0xf0
	anl	a,r2
	orl	a,#0x05
	movx	@dptr,a
00152$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00152$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
	ljmp	00161$
00163$:
;	lib\FwLib_STC8\src\fw_i2c.c:111: I2C_MasterStop();
	mov	dptr,#0xfe81
	movx	a,@dptr
	mov	r7,a
	mov	a,#0xf0
	anl	a,r7
	orl	a,#0x06
	movx	@dptr,a
00164$:
	mov	dptr,#0xfe82
	movx	a,@dptr
	jnb	acc.6,00164$
	mov	dptr,#0xfe82
	movx	a,@dptr
	anl	a,#0xbf
	movx	@dptr,a
;	lib\FwLib_STC8\src\fw_i2c.c:112: SFRX_OFF();
	anl	_P_SW2,#0x7f
;	lib\FwLib_STC8\src\fw_i2c.c:113: return HAL_OK;
	mov	dpl, #0x00
;	lib\FwLib_STC8\src\fw_i2c.c:114: }
	ret
	.area CSEG    (CODE)
	.area CONST   (CODE)
	.area XINIT   (CODE)
	.area CABS    (ABS,CODE)
