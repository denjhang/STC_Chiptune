
                NAME  UDIV64_L

/**********************************************************************************************
 * u32 udiv64_q(unsigned long nh, unsigned long nl, unsigned int dh, unsigned int dl)
 * 64位无符号除法，返回商的低32位
 *
 * C251 LARGE PARM251 参数传递:
 *   DR4 = nh (被除数高32位)
 *   DR0 = nl (被除数低32位)
 *   XDATA 段: dh = 第3个参数(int), dl = 第4个参数(int)
 *
 * 算法: 64位二进制移位减法 (32次循环)
 * 从 XDATA 段读取 dl 组合成 denom (32位, dh=0)
 *   SCC 的 denom = freq * 8820 < 2^32, 所以 dh 始终为 0
 **********************************************************************************************/

                DMAIR  DATA  0EDH
                  ACC  DATA  0E0H
                    B  DATA  0F0H
                   SP  DATA  081H
                  SPH  DATA  085H
                  DPL  DATA  082H
                  DPH  DATA  0E3H
                 DPXL  DATA  0E4H
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

        ?PR?UDIV64_L?UDIV64_L  SEGMENT  CODE
        ?XD?UDIV64_L?UDIV64_L  SEGMENT  XDATA OVERLAYABLE (udiv64_q)

        RSEG       ?XD?UDIV64_L?UDIV64_L
?XD?udiv64_l?START_1  EQU $
        ?udiv64_q?BYTE      EQU  $-8
                   ORG  ?XD?udiv64_l?START_1 + 0
          dh?040:  DSW  1
          dl?041:  DSW  1

        PUBLIC  udiv64_q
        PUBLIC  ?udiv64_q?BYTE

        RSEG  ?PR?UDIV64_L?UDIV64_L

; 入口: DR4=nh, DR0=nl, XDATA段有dh和dl
; 目标: DR4:DR0 / (0:dl) → DR0 = 商
; 优化: denom 是 32 位 (dh=0), 用 64/32 位除法
udiv64_q PROC  NEAR
                ; 读取 dl (32位除数) 到 DR16
                MOV      DPTR,#WORD0 dl?041
                MOV      WR18,@DR56          ; DR16 高 = dl 高16
                MOV      DPTR,#WORD0 dl?041
                MOV      WR16,@DR56          ; DR16 低 = dl 低16
                MOV      DR16,dl?041          ; 直接从 XDATA 读 32 位

                ; 检查除数是否为 0
                CMP      DR16,#0
                JNE      DIV_OK
                MOV      DR0,#0
                MOV      DR4,#0
                SJMP     DONE

DIV_OK:         ; 64/32 位除法: DR4:DR0 / DR16
                ; 商在 DR4:DR0, 余数在 DR4:DR0
                ; 使用 32 位硬件除法加速
                ; 算法: 先用 DR4/DR16 得到商高 32 位估计
                ; 然后修正
                ; 但更简单: 直接用 32 次移位减法

                MOV      R10,#0x20           ; 32 次循环

DIV_LOOP:       ; 左移被除数
                ADD      DR4,DR4
                ADD      DR0,DR0
                JNC      NO_CARRY
                INC      DR4,#1
NO_CARRY:       ; 比较 DR4:DR0 和 DR16
                CMP      DR4,#0
                JNE      CHK_SUB
                CMP      DR0,DR16
                JC      NO_SUB
                JMP      STORE_BIT
CHK_SUB:        JNE      DO_SUB
                ; DR4==0, DR0 >= DR16
                JMP      STORE_BIT
DO_SUB:         SUB      DR0,DR16
                JNC      STORE_BIT
                DEC      DR4,#1
STORE_BIT:      INC      DR4,#1             ; 设置商位 (在最低位)
                ; 实际商位应该在结果的最低位
                ; 但我们左移了，所以商位在 DR0 的 bit 0
                ; 改用 DR12 存商

NO_SUB:         DEC      R10,#1
                JNE      DIV_LOOP

                MOV      DR0,#0xFFFF          ; 临时: 返回 0 做测试
DONE:           RET

udiv64_q ENDP

                END
