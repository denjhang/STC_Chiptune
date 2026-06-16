/*--------------------------------------------------------------------------
DLONG.H

Prototypes for mathematic functions for C251 Version 4.
Copyright (c) 1995-2004 Keil Elektronik GmbH and Keil Software, Inc.
All rights reserved.
--------------------------------------------------------------------------*/

#pragma SAVE
#pragma PARM251

#ifndef _LONG64
#define _LONG64
typedef struct  {   signed long h;  	   // 可以按长字寻址,寻址双长字的高位
									unsigned long l; 	     // 可以按长字寻址,寻址双长字的低位
                }SLONGLONG;      //定义一个可以按长字寻址,寻址双长字的高位和低位的有符号双长字?

typedef struct  { unsigned long h;  	   // 可以按长字寻址,寻址双长字的高位
									unsigned long l; 	     // 可以按长字寻址,寻址双长字的低位
                }LONGLONG;       //定义一个可以按长字寻址,寻址双长字的高位和低位的无符号双长字?

#define WORD64(addr,dh,dl)   do{ addr##.##l = dl;  addr##.##h = dh; }while(0)   

#define MOV64(addr,addrs)    do{ addr##.##l = addrs##.##l; addr##.##h = addrs##.##h; }while(0)

#define  LADD64(a,b,c)        do{ add64 (a##.##h, a##.##l, b##.##h, b##.##l, (long far *)&##c##.##h); }while(0)
#define  LSUB64(a,b,c)        do{ sub64 (a##.##h, a##.##l, b##.##h, b##.##l, (long far *)&##c##.##h); }while(0)
#define  LMUL64(a,b,c)        do{ mul64 (a##.##h, a##.##l, b##.##h, b##.##l, (long far *)&##c##.##h); }while(0)
#define SLDIV64(a,b,c)        do{ sdiv64 (a##.##h, a##.##l, b##.##h, b##.##l, 1, (long far *)&##c##.##h); }while(0)
#define ULDIV64(a,b,c)        do{ udiv64 (a##.##h, a##.##l, b##.##h, b##.##l, 1, (unsigned long far *)&##c##.##h); }while(0)
#define SLMOD64(a,b,c)        do{ sdiv64 (a##.##h, a##.##l, b##.##h, b##.##l, 2, (long far *)&##c##.##h); }while(0)
#define ULMOD64(a,b,c)        do{ udiv64 (a##.##h, a##.##l, b##.##h, b##.##l, 2, (unsigned long far *)&##c##.##h); }while(0)
#define SLDIVm64(a,b,c)       do{ sdiv64 (a##.##h, a##.##l, b##.##h, b##.##l, 3, (long far *)&##c##.##h); }while(0)           // 返回商 和 余数(指针先指向商,后紧跟余数);
#define ULDIVm64(a,b,c)       do{ udiv64 (a##.##h, a##.##l, b##.##h, b##.##l, 3, (unsigned long far *)&##c##.##h); }while(0)  // 返回商 和 余数(指针先指向商,后紧跟余数);
#endif

extern void  add64 (long aH, long aL, long bH, long bL, long far *cp);
extern void  sub64 (long aH, long aL, long bH, long bL, long far *cp);
extern void  mul64 (long aH, long aL, long bH, long bL, long far *cp);
extern void sdiv64 (long aH, long aL, long bH, long bL, char c, long far *cp);   // c=0,返回商; c=1,返回余数; c=2,返回商 和 余数(指针先指向商,后紧跟余数);
extern void udiv64 (unsigned long aH, unsigned long aL, unsigned long bH, unsigned long bL, char c, unsigned long far *cp);  // c=0,返回商; c=1,返回余数; c=2,返回商 和 余数(指针先指向商,后紧跟余数); 


#pragma RESTORE