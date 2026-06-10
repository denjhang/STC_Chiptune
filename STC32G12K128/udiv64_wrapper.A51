;
; udiv64_wrapper.A51 - LARGE 模式调用 ULDIV64_HUGE 的 wrapper
;
; C 接口:
;   extern u32 call_udiv64_32(u32 dL);
;   被除数固定为 (54<<32)|2660761600 = 1789772<<17 = 234588995584
;   除数 = dL (32位, 高32位=0)
;   返回 32位商
;
; ULDIV64_HUGE 参数传递 (分析源码得出):
;   被除数: DR4(高32位):DR0(低32位) <- 寄存器
;   除数高32位: DATA段 value3 (DSD)
;   除数低32位: DATA段 value4 (DSD)
;   模式标志: DATA段 value5 (DS, 1字节)
;     bit0=1: 写商到buffer, bit1=1: 写余数到buffer
;     bit0=0,bit1=0: 不写buffer, 结果留在寄存器
;   结果buffer指针: DATA段 pointer (DSD, 4字节far pointer)
;
; 关键发现: 当 value5=0 时, ULDIV64 不写 buffer, 直接 ERET
; 64÷32 除法 (除数高32位=0) 走 DDIV_002 优化路径:
;   循环32次, DR20 = 商(32位), DR0 = 余数, DR4 = 0
;   我们只要商, 在 DR20 中!
;   不需要 pointer 和 buffer!
;
; 编译: A251.exe udiv64_wrapper.A51 $MODSRC

                NAME    UDIV64_WRAPPER

                EXTRN   UDIV64?         ; 来自 ULDIV64_HUGE.OBJ (FAR)

; ULDIV64_HUGE 的 DATA 段 (OVERLAYABLE, 必须与 .OBJ 一致)
                EXTRN   ?UDIV64_value3?042: DSD
                EXTRN   ?UDIV64_value4?043: DSD
                EXTRN   ?UDIV64_value5?044: DS

?PR?UDIV64_WRAPPER?UDIV64_WRAPPER SEGMENT ECODE
                RSEG    ?PR?UDIV64_WRAPPER?UDIV64_WRAPPER

;
; u32 call_udiv64_32(u32 dL)
; LARGE C251: arg1 -> DR4, return -> DR4
;
call_udiv64_32 PROC FAR

    ; 入口: DR4 = dL

    ; 保存 dL 到栈
    PUSH    DR4

    ; 设被除数: DR4 = 高32位 = 54 = 0x0036, DR0 = 低32位 = 0x9E980000
    MOV     R4, #36H            ; DR4 低字 = 0x0036
    MOV     R5, #0              ; DR4 高字 = 0x0000
    MOV     R0, #0              ; DR0 低字 = 0x0000
    MOV     R1, #0E98H          ; DR0 高字 = 0x9E98

    ; 除数高32位 = 0 -> value3
    MOV     ?UDIV64_value3?042, #0

    ; 除数低32位 = dL -> value4 (从栈恢复)
    POP     DR20
    MOV     ?UDIV64_value4?043, DR20

    ; 模式 = 0: 不写 buffer, 商留在寄存器 DR20
    MOV     ?UDIV64_value5?044, #0

    ; 保存 ULDIV64 破坏的寄存器
    PUSH    DR12
    PUSH    DR16
    PUSH    DR24

    ; 调用 ULDIV64_HUGE (FAR call)
    ; 入口: MOV DR16, value3; MOV DR20, value4; SJMP DDIV_000
    ; value3=0 -> CMP DR16,#0 -> JE; CMP DR4,#0(=54) -> JNE DDIV_002
    ; DDIV_002: 32位优化除法, 32次循环
    ; 返回: DR20=商, DR0=余数, DR4=0
    ECALL   UDIV64?

    ; 恢复寄存器
    POP     DR24
    POP     DR16
    POP     DR12

    ; 返回值: 商从 DR20 -> DR4
    MOV     DR4, DR20

    ERET

call_udiv64_32 ENDP

                END
