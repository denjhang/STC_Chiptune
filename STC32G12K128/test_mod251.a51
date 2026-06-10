$MOD251
                NAME  UDIV64  

/**********************************************************************************************
 * void  udiv64(value1, value2, *pointer);
 *  *pointer = value1 / value2 或
 *  *pointer = value1 % value2
 *  64位 / 64位 --> 64位(8字节无符号整数除法)  
 *  64位 % 64位 --> 64位(8字节无符号整数取模)  

 *  用   途  ：STC32系列MCU
 *  作   者  ：许意义
 *  版   本  ：2.00 
 *  日   期  ：2023-2-4 

 **********************************************************************************************/
	
// 特殊功能寄存器和位
           DMAIR  DATA  0EDH
             ACC  DATA  0E0H
               B  DATA  0F0H
              SP  DATA  081H
             SPH  DATA  085H
             DPL  DATA  082H
             DPH  DATA  083H
            DPXL  DATA  084H
             PSW  DATA  0D0H
            PSW1  DATA  0D1H
               Z  BIT   0D1H.1
              OV  BIT   0D0H.2
               P  BIT   0D0H.0
              F0  BIT   0D0H.5
             RS1  BIT   0D0H.4
             RS0  BIT   0D0H.3
              AC  BIT   0D0H.6
              EA  BIT   0A8H.7
// 结束--特殊功能寄存器和位
 	
        ?PR?UDIV64?UDIV64  SEGMENT  CODE 
        ?DT?UDIV64?UDIV64  SEGMENT  DATA  OVERLAYABLE (UDIV64)  

        RSEG       ?DT?UDIV64?UDIV64
?DT?UDIV64?START_1   EQU  $
?UDIV64?BYTE    EQU  $
                   ORG  ?DT?UDIV64?START_1 + 0
?UDIV64_value1?040:    DSD  1		// 被加数/被减数/被乘数/被除数(高位双字),作临时变量用
?UDIV64_value2?041:    DSD  1		// 被加数/被减数/被乘数/被除数(低位双字),作临时变量用
?UDIV64_value3?042:    DSD  1		// 加数/减数/乘数/除数(高位双字)
?UDIV64_value4?043:    DSD  1		// 加数/减数/乘数/除数(低位双字)
?UDIV64_value5?044:    DS   1		// 求模/除法 标志 
?UDIV64_pointer?045:   DSD  1		// 计算结果回传指针 

PUBLIC        UDIV64 
PUBLIC        ?UDIV64?BYTE 
PUBLIC        UDIV64_1 

// void  UDIV64(long DR4,long DR0,long STC_value3?042,long STC_value4?043,long* STC_pointer?044)  
        RSEG       ?PR?UDIV64?UDIV64

UDIV64     PROC	 NEAR
// DR4:DR0 * (STC_value3?042):(STC_value4?043) --> *(STC_pointer?044) 
// DR4,DR0 / DR16,DR20 --> 商: DR24,DR20, 余数: DR4,DR0 
			MOV      DR16, ?UDIV64_value3?042 
			MOV      DR20, ?UDIV64_value4?043 
			SJMP	 DDIV_000
UDIV64_1 : 
			POP	 	 DR12
			MOV      ?UDIV64_pointer?045, DR12  
DDIV_000:   MOV      R10, #0x20
			CMP      DR16, #0	// 除数高位不为0,跳转
			JNE      DDIV_001
			CMP      DR4, #0	// 被除数高位不为0,跳转
			JNE      DDIV_002 
			MOV      DR4, DR0
	        MOV      DR0, DR20
	        MOV      DMAIR, #4		 // 出口: 余数 低双字DR0, 商: 低双字DR4	
	        MOV      DR20, DR4       // 规格化: 余数 DR4,DR0 商: DR24,DR20
			SUB      DR24, DR24
			SJMP	 DDIV_009

DDIV_001:   MOV      DR12, DR0		// 计算结果: 商(高位双字)为0
			MOV      DR0, DR4
			SUB      DR4, DR4
DDIV_003:   ADD      DR4, DR4
			ADD      DR0, DR0
			JNC      DDIV_004 
			INC      DR4, #1
DDIV_004:	ADD      DR12, DR12
			JNC      DDIV_005
			INC      DR0, #1
DDIV_005:   CMP      DR4, DR16
			JC       DDIV_008
			JNE      DDIV_006
			CMP      DR0, DR20
			JC       DDIV_008
DDIV_006:	SUB      DR4, DR16
			SUB      DR0, DR20
			JNC      DDIV_007
			DEC      DR4, #1
DDIV_007:	INC      DR12,#1
DDIV_008:   DEC      R10, #1
	        JNE      DDIV_003    // 出口: 余数 DR4,DR0 商: 低双字DR12
	        MOV      DR20, DR12      // 规格化: 余数 DR4,DR0 商: DR24,DR20
DDIV_009:	SUB      DR24, DR24
			SJMP	 DDIV_014 
	
DDIV_002:   MOV      DR12, DR20		 // 计算结果: 余数(高位双字)为0
	        MOV      DR20, DR0
			MOV      DR0, DR12
	        MOV      DMAIR, #4		 // 32位无符号除法
	        MOV      DR16, DR0       // 余数 送 DR16
			MOV      DR0, DR4        // 商 送 DR0
DDIV_010:   MOV		 DR24, DR16
			ADD      DR20, DR20
			JNC      DDIV_011 
			INC      DR16, #1
DDIV_011:	ADD      DR16, DR24
	        JC       DDIV_012
	        CMP      DR16, DR12
	        JC       DDIV_013 
DDIV_012:   SUB      DR16, DR12
	        INC      DR20, #0x01
DDIV_013:   DEC      R10, #1
	        JNE      DDIV_010       // 出口: 余数 低双字DR16, 商: DR0,DR20
	        MOV      DR24, DR0       // 规格化: 余数 DR4,DR0 商: DR24,DR20
			MOV      DR0, DR16
			SUB      DR4, DR4
DDIV_014:		
			MOV      DR16, ?UDIV64_pointer?045
			JNB      ACC.0, DDIV_016
			JNB      ACC.7, DDIV_015
	        SUB      DR12,DR12
	        SUB      DR12,DR20
	        MOV      DR20,DR12	
			MOV		 F0, C
	        SUB      DR12,DR12
	        SUB      DR12,DR24
	        MOV      DR24,DR12
			JNB      F0, DDIV_015 
			DEC 	 DR24, #1
DDIV_015:	MOV      @DR16, WR24
			MOV      @DR16+2, WR26
			MOV      @DR16+4, WR20
			MOV      @DR16+6, WR22
			ADD		 DR16,#8
DDIV_016:	JNB      ACC.1, DDIV_018
			JNB      ACC.6, DDIV_017
	        SUB      DR12,DR12
	        SUB      DR12,DR0
	        MOV      DR0,DR12	
			MOV		 F0, C
	        SUB      DR12,DR12
	        SUB      DR12,DR4
	        MOV      DR4,DR12
			JNB      F0, DDIV_017 
			DEC 	 DR4, #1
DDIV_017:	MOV      @DR16, WR4
			MOV      @DR16+2, WR6
			MOV      @DR16+4, WR0
			MOV      @DR16+6, WR2
DDIV_018:	RET			

			ENDP
			END
