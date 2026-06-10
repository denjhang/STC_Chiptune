#include "..\System\os_link.h"

extern void pwma_dac_init(void);
extern void scc_init_func(void);
extern void test_start(void);

void init_hook(void)
{
	P0M0=0; P0M1=0;
	P1M0=0; P1M1=0;
	P2M0=0; P2M1=0;
	P3M0=0; P3M1=0;
	P4M0=0; P4M1=0;

	P0 = 0xFF;
	P35 = 1; P36 = 1; P37 = 1;
	P41 = 1; P42 = 1; P44 = 1; P45 = 1;

	AUXR = 0x00;
	P_SW2 = EAXFR;

	/* UART1: Timer1, 230400 baud, 1T mode */
	TMOD &= 0xF0;
	TMOD &= ~0x30;
	AUXR |= (1<<6);
	AUXR &= ~0x01;
	{
		unsigned long tmr;
		tmr = 65536UL - (SYSCFG_SYSCLK / 4) / 230400UL;
		TH1 = (unsigned char)(tmr / 256);
		TL1 = (unsigned char)(tmr % 256);
	}
	ET1 = 0;
	INTCLKO &= ~0x02;
	TR1 = 1;
	SCON = (SCON & 0x3f) | 0x40;
	ES = 1;
	REN = 1;
	P_SW1 &= 0x3f;

	/* INT0 priority 0 (for PendSV) */
	IPH &= ~PX0H;
	PX0 = 0;

	/* PWM DAC */
	pwma_dac_init();

	/* SCC init + boot melody */
	scc_init_func();
	test_start();
}
