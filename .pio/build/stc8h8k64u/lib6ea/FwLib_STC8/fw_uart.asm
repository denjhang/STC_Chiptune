;--------------------------------------------------------
; File Created by SDCC : free open source ISO C Compiler 
; Version 4.4.0 #14620 (MINGW32)
;--------------------------------------------------------
	.module fw_uart
	.optsdcc -mmcs51 --model-small
	
;--------------------------------------------------------
; Public variables in this module
;--------------------------------------------------------
	.globl __UART1_ConfigDynUart_PARM_3
	.globl __UART1_ConfigDynUart_PARM_2
	.globl _putchar
	.globl __UART1_ConfigDynUart
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
	.globl _UART4_ConfigOnTimer4_PARM_2
	.globl _UART4_ConfigOnTimer2_PARM_2
	.globl _UART3_ConfigOnTimer3_PARM_2
	.globl _UART3_ConfigOnTimer2_PARM_2
	.globl _UART2_Config_PARM_2
	.globl _UART1_Config9bitUart_PARM_3
	.globl _UART1_Config9bitUart_PARM_2
	.globl _UART1_Config8bitUart_PARM_3
	.globl _UART1_Config8bitUart_PARM_2
	.globl _UART_Timer_InitValueCalculate_PARM_3
	.globl _UART_Timer_InitValueCalculate_PARM_2
	.globl _UART_Timer_InitValueCalculate
	.globl _UART1_Config8bitUart
	.globl _UART1_Config9bitUart
	.globl _UART1_TxChar
	.globl _UART1_TxHex
	.globl _UART1_TxString
	.globl _UART2_Config
	.globl _UART2_TxChar
	.globl _UART2_TxHex
	.globl _UART2_TxString
	.globl _UART3_ConfigOnTimer2
	.globl _UART3_ConfigOnTimer3
	.globl _UART4_ConfigOnTimer2
	.globl _UART4_ConfigOnTimer4
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
_UART_Timer_InitValueCalculate_PARM_2:
	.ds 1
_UART_Timer_InitValueCalculate_PARM_3:
	.ds 4
_UART1_Config8bitUart_PARM_2:
	.ds 1
_UART1_Config8bitUart_PARM_3:
	.ds 4
_UART1_Config9bitUart_PARM_2:
	.ds 1
_UART1_Config9bitUart_PARM_3:
	.ds 4
_UART2_Config_PARM_2:
	.ds 4
_UART3_ConfigOnTimer2_PARM_2:
	.ds 4
_UART3_ConfigOnTimer3_PARM_2:
	.ds 4
_UART4_ConfigOnTimer2_PARM_2:
	.ds 4
_UART4_ConfigOnTimer4_PARM_2:
	.ds 4
;--------------------------------------------------------
; overlayable items in internal ram
;--------------------------------------------------------
	.area	OSEG    (OVR,DATA)
__UART1_ConfigDynUart_PARM_2:
	.ds 1
__UART1_ConfigDynUart_PARM_3:
	.ds 2
	.area	OSEG    (OVR,DATA)
	.area	OSEG    (OVR,DATA)
	.area	OSEG    (OVR,DATA)
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
;Allocation info for local variables in function 'UART_Timer_InitValueCalculate'
;------------------------------------------------------------
;_1TMode                   Allocated with name '_UART_Timer_InitValueCalculate_PARM_2'
;baudrate                  Allocated with name '_UART_Timer_InitValueCalculate_PARM_3'
;sysclk                    Allocated to registers r4 r5 r6 r7 
;value                     Allocated to registers r4 r5 r6 r7 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:20: int16_t UART_Timer_InitValueCalculate(uint32_t sysclk, HAL_State_t _1TMode, uint32_t baudrate)
;	-----------------------------------------
;	 function UART_Timer_InitValueCalculate
;	-----------------------------------------
_UART_Timer_InitValueCalculate:
	ar7 = 0x07
	ar6 = 0x06
	ar5 = 0x05
	ar4 = 0x04
	ar3 = 0x03
	ar2 = 0x02
	ar1 = 0x01
	ar0 = 0x00
	mov	r4,dpl
	mov	r5,dph
	mov	r6,b
	mov	r7,a
;	lib\FwLib_STC8\src\fw_uart.c:23: value = sysclk / (4 * baudrate);
	mov	a,_UART_Timer_InitValueCalculate_PARM_3
	add	a,_UART_Timer_InitValueCalculate_PARM_3
	mov	__divulong_PARM_2,a
	mov	a,(_UART_Timer_InitValueCalculate_PARM_3 + 1)
	rlc	a
	mov	(__divulong_PARM_2 + 1),a
	mov	a,(_UART_Timer_InitValueCalculate_PARM_3 + 2)
	rlc	a
	mov	(__divulong_PARM_2 + 2),a
	mov	a,(_UART_Timer_InitValueCalculate_PARM_3 + 3)
	rlc	a
	mov	(__divulong_PARM_2 + 3),a
	mov	a,__divulong_PARM_2
	add	a,__divulong_PARM_2
	mov	__divulong_PARM_2,a
	mov	a,(__divulong_PARM_2 + 1)
	rlc	a
	mov	(__divulong_PARM_2 + 1),a
	mov	a,(__divulong_PARM_2 + 2)
	rlc	a
	mov	(__divulong_PARM_2 + 2),a
	mov	a,(__divulong_PARM_2 + 3)
	rlc	a
	mov	(__divulong_PARM_2 + 3),a
;	lib\FwLib_STC8\src\fw_uart.c:24: if (!_1TMode)
	mov	dpl, r4
	mov	dph, r5
	mov	b, r6
	mov	a, r7
	lcall	__divulong
	mov	r4, dpl
	mov	r5, dph
	mov	r6, b
	mov	r7, a
	mov	a,_UART_Timer_InitValueCalculate_PARM_2
	jnz	00102$
;	lib\FwLib_STC8\src\fw_uart.c:25: value = value / 12;
	mov	__divulong_PARM_2,#0x0c
	clr	a
	mov	(__divulong_PARM_2 + 1),a
	mov	(__divulong_PARM_2 + 2),a
	mov	(__divulong_PARM_2 + 3),a
	mov	dpl, r4
	mov	dph, r5
	mov	b, r6
	mov	a, r7
	lcall	__divulong
	mov	r4, dpl
	mov	r5, dph
	mov	r6, b
	mov	r7, a
00102$:
;	lib\FwLib_STC8\src\fw_uart.c:26: if (value > 0xFFFF)
	clr	c
	mov	a,#0xff
	subb	a,r4
	mov	a,#0xff
	subb	a,r5
	clr	a
	subb	a,r6
	clr	a
	subb	a,r7
	jnc	00104$
;	lib\FwLib_STC8\src\fw_uart.c:27: return 0;
	mov	dptr,#0x0000
	ret
00104$:
;	lib\FwLib_STC8\src\fw_uart.c:29: return 0xFFFF - value + 1;
	clr	c
	clr	a
	subb	a,r4
	mov	dpl,a
	clr	a
	subb	a,r5
	mov	dph,a
;	lib\FwLib_STC8\src\fw_uart.c:30: }
	ret
;------------------------------------------------------------
;Allocation info for local variables in function '_UART1_ConfigDynUart'
;------------------------------------------------------------
;_1TMode                   Allocated with name '__UART1_ConfigDynUart_PARM_2'
;init                      Allocated with name '__UART1_ConfigDynUart_PARM_3'
;baudSource                Allocated to registers r7 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:36: void _UART1_ConfigDynUart(UART1_BaudSource_t baudSource, HAL_State_t _1TMode, int16_t init)
;	-----------------------------------------
;	 function _UART1_ConfigDynUart
;	-----------------------------------------
__UART1_ConfigDynUart:
	mov	r7, dpl
;	lib\FwLib_STC8\src\fw_uart.c:38: UART1_SetBaudSource(baudSource);
	mov	a,#0xfe
	anl	a,_AUXR
	mov	r6,a
	mov	ar5,r7
	mov	a,r5
	orl	a,r6
	mov	_AUXR,a
;	lib\FwLib_STC8\src\fw_uart.c:40: if (baudSource == UART1_BaudSource_Timer1)
	mov	a,r7
	jnz	00108$
;	lib\FwLib_STC8\src\fw_uart.c:42: TIM_Timer1_Set1TMode(_1TMode);
	mov	a,#0xbf
	anl	a,_AUXR
	mov	r7,a
	mov	a,__UART1_ConfigDynUart_PARM_2
	rr	a
	rr	a
	anl	a,#0xc0
	orl	a,r7
	mov	_AUXR,a
;	lib\FwLib_STC8\src\fw_uart.c:43: TIM_Timer1_SetMode(TIM_TimerMode_16BitAuto);
	anl	_TMOD,#0xcf
;	lib\FwLib_STC8\src\fw_uart.c:44: TIM_Timer1_SetInitValue(init >> 8, init & 0xFF);
	mov	_TH1,(__UART1_ConfigDynUart_PARM_3 + 1)
	mov	_TL1,__UART1_ConfigDynUart_PARM_3
;	lib\FwLib_STC8\src\fw_uart.c:45: TIM_Timer1_SetRunState(HAL_State_ON);
;	assignBit
	setb	_TR1
	ret
00108$:
;	lib\FwLib_STC8\src\fw_uart.c:51: TIM_Timer2_Set1TMode(_1TMode);
	mov	a,#0xfb
	anl	a,_AUXR
	mov	r7,a
	mov	a,__UART1_ConfigDynUart_PARM_2
	add	a,acc
	add	a,acc
	orl	a,r7
	mov	_AUXR,a
;	lib\FwLib_STC8\src\fw_uart.c:52: TIM_Timer2_SetInitValue(init >> 8, init & 0xFF);
	mov	_T2H,(__UART1_ConfigDynUart_PARM_3 + 1)
	mov	_T2L,__UART1_ConfigDynUart_PARM_3
;	lib\FwLib_STC8\src\fw_uart.c:53: TIM_Timer2_SetRunState(HAL_State_ON);
	mov	a,#0xef
	anl	a,_AUXR
	orl	a,#0x10
	mov	_AUXR,a
;	lib\FwLib_STC8\src\fw_uart.c:55: }
	ret
;------------------------------------------------------------
;Allocation info for local variables in function 'UART1_Config8bitUart'
;------------------------------------------------------------
;_1TMode                   Allocated with name '_UART1_Config8bitUart_PARM_2'
;baudrate                  Allocated with name '_UART1_Config8bitUart_PARM_3'
;baudSource                Allocated to registers r7 
;init                      Allocated to registers 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:56: void UART1_Config8bitUart(UART1_BaudSource_t baudSource, HAL_State_t _1TMode, uint32_t baudrate)
;	-----------------------------------------
;	 function UART1_Config8bitUart
;	-----------------------------------------
_UART1_Config8bitUart:
	mov	r7, dpl
;	lib\FwLib_STC8\src\fw_uart.c:59: SM0=0; SM1=1;
;	assignBit
	clr	_SM0
;	assignBit
	setb	_SM1
;	lib\FwLib_STC8\src\fw_uart.c:60: init = UART_Timer_InitValueCalculate(__SYSCLOCK, _1TMode, baudrate);
	mov	_UART_Timer_InitValueCalculate_PARM_2,_UART1_Config8bitUart_PARM_2
	mov	_UART_Timer_InitValueCalculate_PARM_3,_UART1_Config8bitUart_PARM_3
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 1),(_UART1_Config8bitUart_PARM_3 + 1)
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 2),(_UART1_Config8bitUart_PARM_3 + 2)
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 3),(_UART1_Config8bitUart_PARM_3 + 3)
	mov	dptr,#0xc000
	mov	b, #0xa8
	clr	a
	push	ar7
	lcall	_UART_Timer_InitValueCalculate
	mov	__UART1_ConfigDynUart_PARM_3,dpl
	mov	(__UART1_ConfigDynUart_PARM_3 + 1),dph
	pop	ar7
;	lib\FwLib_STC8\src\fw_uart.c:61: _UART1_ConfigDynUart(baudSource, _1TMode, init);
	mov	__UART1_ConfigDynUart_PARM_2,_UART1_Config8bitUart_PARM_2
	mov	dpl, r7
;	lib\FwLib_STC8\src\fw_uart.c:62: }
	ljmp	__UART1_ConfigDynUart
;------------------------------------------------------------
;Allocation info for local variables in function 'UART1_Config9bitUart'
;------------------------------------------------------------
;_1TMode                   Allocated with name '_UART1_Config9bitUart_PARM_2'
;baudrate                  Allocated with name '_UART1_Config9bitUart_PARM_3'
;baudSource                Allocated to registers r7 
;init                      Allocated to registers 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:64: void UART1_Config9bitUart(UART1_BaudSource_t baudSource, HAL_State_t _1TMode, uint32_t baudrate)
;	-----------------------------------------
;	 function UART1_Config9bitUart
;	-----------------------------------------
_UART1_Config9bitUart:
	mov	r7, dpl
;	lib\FwLib_STC8\src\fw_uart.c:67: SM0=1; SM1=1;
;	assignBit
	setb	_SM0
;	assignBit
	setb	_SM1
;	lib\FwLib_STC8\src\fw_uart.c:68: init = UART_Timer_InitValueCalculate(__SYSCLOCK, _1TMode, baudrate);
	mov	_UART_Timer_InitValueCalculate_PARM_2,_UART1_Config9bitUart_PARM_2
	mov	_UART_Timer_InitValueCalculate_PARM_3,_UART1_Config9bitUart_PARM_3
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 1),(_UART1_Config9bitUart_PARM_3 + 1)
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 2),(_UART1_Config9bitUart_PARM_3 + 2)
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 3),(_UART1_Config9bitUart_PARM_3 + 3)
	mov	dptr,#0xc000
	mov	b, #0xa8
	clr	a
	push	ar7
	lcall	_UART_Timer_InitValueCalculate
	mov	__UART1_ConfigDynUart_PARM_3,dpl
	mov	(__UART1_ConfigDynUart_PARM_3 + 1),dph
	pop	ar7
;	lib\FwLib_STC8\src\fw_uart.c:69: _UART1_ConfigDynUart(baudSource, _1TMode, init);
	mov	__UART1_ConfigDynUart_PARM_2,_UART1_Config9bitUart_PARM_2
	mov	dpl, r7
;	lib\FwLib_STC8\src\fw_uart.c:70: }
	ljmp	__UART1_ConfigDynUart
;------------------------------------------------------------
;Allocation info for local variables in function 'UART1_TxChar'
;------------------------------------------------------------
;dat                       Allocated to registers 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:72: void UART1_TxChar(char dat)
;	-----------------------------------------
;	 function UART1_TxChar
;	-----------------------------------------
_UART1_TxChar:
	mov	_SBUF,dpl
;	lib\FwLib_STC8\src\fw_uart.c:75: while(!TI);
00101$:
;	lib\FwLib_STC8\src\fw_uart.c:76: UART1_ClearTxInterrupt();
;	assignBit
	jbc	_TI,00118$
	sjmp	00101$
00118$:
;	lib\FwLib_STC8\src\fw_uart.c:77: }
	ret
;------------------------------------------------------------
;Allocation info for local variables in function 'UART1_TxHex'
;------------------------------------------------------------
;hex                       Allocated to registers r7 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:79: void UART1_TxHex(uint8_t hex)
;	-----------------------------------------
;	 function UART1_TxHex
;	-----------------------------------------
_UART1_TxHex:
;	lib\FwLib_STC8\src\fw_uart.c:81: UART1_TxChar(HEX_TABLE[hex >> 4]);
	mov	a,dpl
	mov	r7,a
	swap	a
	anl	a,#0x0f
	mov	dptr,#_HEX_TABLE
	movc	a,@a+dptr
	mov	dpl,a
	push	ar7
	lcall	_UART1_TxChar
	pop	ar7
;	lib\FwLib_STC8\src\fw_uart.c:82: UART1_TxChar(HEX_TABLE[hex & 0xF]);
	anl	ar7,#0x0f
	mov	r6,#0x00
	mov	a,r7
	add	a, #_HEX_TABLE
	mov	dpl,a
	mov	a,r6
	addc	a, #(_HEX_TABLE >> 8)
	mov	dph,a
	clr	a
	movc	a,@a+dptr
	mov	dpl,a
;	lib\FwLib_STC8\src\fw_uart.c:83: }
	ljmp	_UART1_TxChar
;------------------------------------------------------------
;Allocation info for local variables in function 'UART1_TxString'
;------------------------------------------------------------
;str                       Allocated to registers 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:85: void UART1_TxString(uint8_t *str)
;	-----------------------------------------
;	 function UART1_TxString
;	-----------------------------------------
_UART1_TxString:
	mov	r5, dpl
	mov	r6, dph
	mov	r7, b
;	lib\FwLib_STC8\src\fw_uart.c:87: while (*str) UART1_TxChar(*str++);
00101$:
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	lcall	__gptrget
	mov	r4,a
	jz	00104$
	mov	dpl,r4
	inc	r5
	cjne	r5,#0x00,00120$
	inc	r6
00120$:
	push	ar7
	push	ar6
	push	ar5
	lcall	_UART1_TxChar
	pop	ar5
	pop	ar6
	pop	ar7
	sjmp	00101$
00104$:
;	lib\FwLib_STC8\src\fw_uart.c:88: }
	ret
;------------------------------------------------------------
;Allocation info for local variables in function 'putchar'
;------------------------------------------------------------
;dat                       Allocated to registers r6 r7 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:90: int putchar(int dat) {
;	-----------------------------------------
;	 function putchar
;	-----------------------------------------
_putchar:
	mov	r6, dpl
	mov	r7, dph
;	lib\FwLib_STC8\src\fw_uart.c:91: UART1_WriteBuffer(dat);
	mov	_SBUF,r6
;	lib\FwLib_STC8\src\fw_uart.c:92: while(!TI);
00101$:
;	lib\FwLib_STC8\src\fw_uart.c:93: UART1_ClearTxInterrupt();
;	assignBit
	jbc	_TI,00118$
	sjmp	00101$
00118$:
;	lib\FwLib_STC8\src\fw_uart.c:94: return dat;
	mov	dpl, r6
	mov	dph, r7
;	lib\FwLib_STC8\src\fw_uart.c:95: }
	ret
;------------------------------------------------------------
;Allocation info for local variables in function 'UART2_Config'
;------------------------------------------------------------
;baudrate                  Allocated with name '_UART2_Config_PARM_2'
;_1TMode                   Allocated to registers r7 
;init                      Allocated to registers r5 r6 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:102: void UART2_Config(HAL_State_t _1TMode, uint32_t baudrate)
;	-----------------------------------------
;	 function UART2_Config
;	-----------------------------------------
_UART2_Config:
	mov	r7, dpl
;	lib\FwLib_STC8\src\fw_uart.c:106: init = UART_Timer_InitValueCalculate(__SYSCLOCK, _1TMode, baudrate);
	mov	_UART_Timer_InitValueCalculate_PARM_2,r7
	mov	_UART_Timer_InitValueCalculate_PARM_3,_UART2_Config_PARM_2
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 1),(_UART2_Config_PARM_2 + 1)
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 2),(_UART2_Config_PARM_2 + 2)
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 3),(_UART2_Config_PARM_2 + 3)
	mov	dptr,#0xc000
	mov	b, #0xa8
	clr	a
	push	ar7
	lcall	_UART_Timer_InitValueCalculate
	mov	r5, dpl
	mov	r6, dph
	pop	ar7
;	lib\FwLib_STC8\src\fw_uart.c:108: TIM_Timer2_Set1TMode(_1TMode);
	mov	a,#0xfb
	anl	a,_AUXR
	mov	r4,a
	mov	a,r7
	add	a,r7
	add	a,acc
	orl	a,r4
	mov	_AUXR,a
;	lib\FwLib_STC8\src\fw_uart.c:109: TIM_Timer2_SetInitValue(init >> 8, init & 0xFF);
	mov	_T2H,r6
	mov	_T2L,r5
;	lib\FwLib_STC8\src\fw_uart.c:110: TIM_Timer2_SetRunState(HAL_State_ON);
	mov	a,#0xef
	anl	a,_AUXR
	orl	a,#0x10
	mov	_AUXR,a
;	lib\FwLib_STC8\src\fw_uart.c:111: }
	ret
;------------------------------------------------------------
;Allocation info for local variables in function 'UART2_TxChar'
;------------------------------------------------------------
;dat                       Allocated to registers 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:113: void UART2_TxChar(char dat)
;	-----------------------------------------
;	 function UART2_TxChar
;	-----------------------------------------
_UART2_TxChar:
	mov	_S2BUF,dpl
;	lib\FwLib_STC8\src\fw_uart.c:116: while(!UART2_TxFinished());
00101$:
	mov	a,_S2CON
	jnb	acc.1,00101$
;	lib\FwLib_STC8\src\fw_uart.c:117: UART2_ClearTxInterrupt();
	anl	_S2CON,#0xfd
;	lib\FwLib_STC8\src\fw_uart.c:118: }
	ret
;------------------------------------------------------------
;Allocation info for local variables in function 'UART2_TxHex'
;------------------------------------------------------------
;hex                       Allocated to registers r7 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:120: void UART2_TxHex(uint8_t hex)
;	-----------------------------------------
;	 function UART2_TxHex
;	-----------------------------------------
_UART2_TxHex:
;	lib\FwLib_STC8\src\fw_uart.c:122: UART2_TxChar(HEX_TABLE[hex >> 4]);
	mov	a,dpl
	mov	r7,a
	swap	a
	anl	a,#0x0f
	mov	dptr,#_HEX_TABLE
	movc	a,@a+dptr
	mov	dpl,a
	push	ar7
	lcall	_UART2_TxChar
	pop	ar7
;	lib\FwLib_STC8\src\fw_uart.c:123: UART2_TxChar(HEX_TABLE[hex & 0xF]);
	anl	ar7,#0x0f
	mov	r6,#0x00
	mov	a,r7
	add	a, #_HEX_TABLE
	mov	dpl,a
	mov	a,r6
	addc	a, #(_HEX_TABLE >> 8)
	mov	dph,a
	clr	a
	movc	a,@a+dptr
	mov	dpl,a
;	lib\FwLib_STC8\src\fw_uart.c:124: }
	ljmp	_UART2_TxChar
;------------------------------------------------------------
;Allocation info for local variables in function 'UART2_TxString'
;------------------------------------------------------------
;str                       Allocated to registers 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:126: void UART2_TxString(uint8_t *str)
;	-----------------------------------------
;	 function UART2_TxString
;	-----------------------------------------
_UART2_TxString:
	mov	r5, dpl
	mov	r6, dph
	mov	r7, b
;	lib\FwLib_STC8\src\fw_uart.c:128: while (*str) UART2_TxChar(*str++);
00101$:
	mov	dpl,r5
	mov	dph,r6
	mov	b,r7
	lcall	__gptrget
	mov	r4,a
	jz	00104$
	mov	dpl,r4
	inc	r5
	cjne	r5,#0x00,00120$
	inc	r6
00120$:
	push	ar7
	push	ar6
	push	ar5
	lcall	_UART2_TxChar
	pop	ar5
	pop	ar6
	pop	ar7
	sjmp	00101$
00104$:
;	lib\FwLib_STC8\src\fw_uart.c:129: }
	ret
;------------------------------------------------------------
;Allocation info for local variables in function 'UART3_ConfigOnTimer2'
;------------------------------------------------------------
;baudrate                  Allocated with name '_UART3_ConfigOnTimer2_PARM_2'
;_1TMode                   Allocated to registers r7 
;init                      Allocated to registers r5 r6 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:136: void UART3_ConfigOnTimer2(HAL_State_t _1TMode, uint32_t baudrate)
;	-----------------------------------------
;	 function UART3_ConfigOnTimer2
;	-----------------------------------------
_UART3_ConfigOnTimer2:
	mov	r7, dpl
;	lib\FwLib_STC8\src\fw_uart.c:140: UART3_SetBaudSource(0x00);
	anl	_S3CON,#0xbf
;	lib\FwLib_STC8\src\fw_uart.c:141: init = UART_Timer_InitValueCalculate(__SYSCLOCK, _1TMode, baudrate);
	mov	_UART_Timer_InitValueCalculate_PARM_2,r7
	mov	_UART_Timer_InitValueCalculate_PARM_3,_UART3_ConfigOnTimer2_PARM_2
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 1),(_UART3_ConfigOnTimer2_PARM_2 + 1)
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 2),(_UART3_ConfigOnTimer2_PARM_2 + 2)
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 3),(_UART3_ConfigOnTimer2_PARM_2 + 3)
	mov	dptr,#0xc000
	mov	b, #0xa8
	clr	a
	push	ar7
	lcall	_UART_Timer_InitValueCalculate
	mov	r5, dpl
	mov	r6, dph
	pop	ar7
;	lib\FwLib_STC8\src\fw_uart.c:143: TIM_Timer2_Set1TMode(_1TMode);
	mov	a,#0xfb
	anl	a,_AUXR
	mov	r4,a
	mov	a,r7
	add	a,r7
	add	a,acc
	orl	a,r4
	mov	_AUXR,a
;	lib\FwLib_STC8\src\fw_uart.c:144: TIM_Timer2_SetInitValue(init >> 8, init & 0xFF);
	mov	_T2H,r6
	mov	_T2L,r5
;	lib\FwLib_STC8\src\fw_uart.c:145: TIM_Timer2_SetRunState(HAL_State_ON);
	mov	a,#0xef
	anl	a,_AUXR
	orl	a,#0x10
	mov	_AUXR,a
;	lib\FwLib_STC8\src\fw_uart.c:146: }
	ret
;------------------------------------------------------------
;Allocation info for local variables in function 'UART3_ConfigOnTimer3'
;------------------------------------------------------------
;baudrate                  Allocated with name '_UART3_ConfigOnTimer3_PARM_2'
;_1TMode                   Allocated to registers r7 
;init                      Allocated to registers r5 r6 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:148: void UART3_ConfigOnTimer3(HAL_State_t _1TMode, uint32_t baudrate)
;	-----------------------------------------
;	 function UART3_ConfigOnTimer3
;	-----------------------------------------
_UART3_ConfigOnTimer3:
	mov	r7, dpl
;	lib\FwLib_STC8\src\fw_uart.c:152: UART3_SetBaudSource(0x01);
	mov	a,#0xbf
	anl	a,_S3CON
	orl	a,#0x40
	mov	_S3CON,a
;	lib\FwLib_STC8\src\fw_uart.c:153: init = UART_Timer_InitValueCalculate(__SYSCLOCK, _1TMode, baudrate);
	mov	_UART_Timer_InitValueCalculate_PARM_2,r7
	mov	_UART_Timer_InitValueCalculate_PARM_3,_UART3_ConfigOnTimer3_PARM_2
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 1),(_UART3_ConfigOnTimer3_PARM_2 + 1)
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 2),(_UART3_ConfigOnTimer3_PARM_2 + 2)
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 3),(_UART3_ConfigOnTimer3_PARM_2 + 3)
	mov	dptr,#0xc000
	mov	b, #0xa8
	clr	a
	push	ar7
	lcall	_UART_Timer_InitValueCalculate
	mov	r5, dpl
	mov	r6, dph
	pop	ar7
;	lib\FwLib_STC8\src\fw_uart.c:155: TIM_Timer3_Set1TMode(_1TMode);
	mov	a,#0xfd
	anl	a,_T4T3M
	mov	r4,a
	mov	a,r7
	add	a,r7
	orl	a,r4
	mov	_T4T3M,a
;	lib\FwLib_STC8\src\fw_uart.c:156: TIM_Timer3_SetInitValue(init >> 8, init & 0xFF);
	mov	_T3H,r6
	mov	_T3L,r5
;	lib\FwLib_STC8\src\fw_uart.c:157: TIM_Timer3_SetRunState(HAL_State_ON);
	mov	a,#0xf7
	anl	a,_T4T3M
	orl	a,#0x08
	mov	_T4T3M,a
;	lib\FwLib_STC8\src\fw_uart.c:158: }
	ret
;------------------------------------------------------------
;Allocation info for local variables in function 'UART4_ConfigOnTimer2'
;------------------------------------------------------------
;baudrate                  Allocated with name '_UART4_ConfigOnTimer2_PARM_2'
;_1TMode                   Allocated to registers r7 
;init                      Allocated to registers r5 r6 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:165: void UART4_ConfigOnTimer2(HAL_State_t _1TMode, uint32_t baudrate)
;	-----------------------------------------
;	 function UART4_ConfigOnTimer2
;	-----------------------------------------
_UART4_ConfigOnTimer2:
	mov	r7, dpl
;	lib\FwLib_STC8\src\fw_uart.c:169: UART4_SetBaudSource(0x00);
	anl	_S4CON,#0xbf
;	lib\FwLib_STC8\src\fw_uart.c:170: init = UART_Timer_InitValueCalculate(__SYSCLOCK, _1TMode, baudrate);
	mov	_UART_Timer_InitValueCalculate_PARM_2,r7
	mov	_UART_Timer_InitValueCalculate_PARM_3,_UART4_ConfigOnTimer2_PARM_2
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 1),(_UART4_ConfigOnTimer2_PARM_2 + 1)
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 2),(_UART4_ConfigOnTimer2_PARM_2 + 2)
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 3),(_UART4_ConfigOnTimer2_PARM_2 + 3)
	mov	dptr,#0xc000
	mov	b, #0xa8
	clr	a
	push	ar7
	lcall	_UART_Timer_InitValueCalculate
	mov	r5, dpl
	mov	r6, dph
	pop	ar7
;	lib\FwLib_STC8\src\fw_uart.c:171: TIM_Timer2_Set1TMode(_1TMode);
	mov	a,#0xfb
	anl	a,_AUXR
	mov	r4,a
	mov	a,r7
	add	a,r7
	add	a,acc
	orl	a,r4
	mov	_AUXR,a
;	lib\FwLib_STC8\src\fw_uart.c:172: TIM_Timer2_SetInitValue(init >> 8, init & 0xFF);
	mov	_T2H,r6
	mov	_T2L,r5
;	lib\FwLib_STC8\src\fw_uart.c:173: TIM_Timer2_SetRunState(HAL_State_ON);
	mov	a,#0xef
	anl	a,_AUXR
	orl	a,#0x10
	mov	_AUXR,a
;	lib\FwLib_STC8\src\fw_uart.c:174: }
	ret
;------------------------------------------------------------
;Allocation info for local variables in function 'UART4_ConfigOnTimer4'
;------------------------------------------------------------
;baudrate                  Allocated with name '_UART4_ConfigOnTimer4_PARM_2'
;_1TMode                   Allocated to registers r7 
;init                      Allocated to registers r5 r6 
;------------------------------------------------------------
;	lib\FwLib_STC8\src\fw_uart.c:176: void UART4_ConfigOnTimer4(HAL_State_t _1TMode, uint32_t baudrate)
;	-----------------------------------------
;	 function UART4_ConfigOnTimer4
;	-----------------------------------------
_UART4_ConfigOnTimer4:
	mov	r7, dpl
;	lib\FwLib_STC8\src\fw_uart.c:180: UART4_SetBaudSource(0x01);
	mov	a,#0xbf
	anl	a,_S4CON
	orl	a,#0x40
	mov	_S4CON,a
;	lib\FwLib_STC8\src\fw_uart.c:181: init = UART_Timer_InitValueCalculate(__SYSCLOCK, _1TMode, baudrate);
	mov	_UART_Timer_InitValueCalculate_PARM_2,r7
	mov	_UART_Timer_InitValueCalculate_PARM_3,_UART4_ConfigOnTimer4_PARM_2
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 1),(_UART4_ConfigOnTimer4_PARM_2 + 1)
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 2),(_UART4_ConfigOnTimer4_PARM_2 + 2)
	mov	(_UART_Timer_InitValueCalculate_PARM_3 + 3),(_UART4_ConfigOnTimer4_PARM_2 + 3)
	mov	dptr,#0xc000
	mov	b, #0xa8
	clr	a
	push	ar7
	lcall	_UART_Timer_InitValueCalculate
	mov	r5, dpl
	mov	r6, dph
	pop	ar7
;	lib\FwLib_STC8\src\fw_uart.c:182: TIM_Timer4_Set1TMode(_1TMode);
	mov	a,#0xdf
	anl	a,_T4T3M
	mov	r4,a
	mov	a,r7
	swap	a
	rl	a
	anl	a,#0xe0
	orl	a,r4
	mov	_T4T3M,a
;	lib\FwLib_STC8\src\fw_uart.c:183: TIM_Timer4_SetInitValue(init >> 8, init & 0xFF);
	mov	_T4H,r6
	mov	_T4L,r5
;	lib\FwLib_STC8\src\fw_uart.c:184: TIM_Timer4_SetRunState(HAL_State_ON);
	mov	a,#0x7f
	anl	a,_T4T3M
	orl	a,#0x80
	mov	_T4T3M,a
;	lib\FwLib_STC8\src\fw_uart.c:185: }
	ret
	.area CSEG    (CODE)
	.area CONST   (CODE)
	.area XINIT   (CODE)
	.area CABS    (ABS,CODE)
