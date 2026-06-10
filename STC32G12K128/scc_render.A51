;
; scc_render.A51 - SCC 渲染函数 (C251 汇编加速版)
;
; C 接口: u8 scc_render(void);
; 返回: 8-bit 混合输出 (128为中心)
;
; 5 通道展开, 直接用固定偏移访问 xdata
; 寄存器使用:
;   WR6  = mix (累加器)
;   DR28 = scc_cnt[i] + scc_step_val[i] (临时)
;   DR0  = scc_cnt[i] (读回)
;   R4   = offs (wave index)
;   R3   = vol
;   R2   = b (wave sample)
;   WR10 = tmp (signed sample * vol)
;
; 编译: A251.exe scc_render.A51 $MODSRC

                NAME    SCC_RENDER

; xdata 变量 (在 scc.c 中定义)
                EXTRN   WORD0(scc_step_val): WORD   ; u32[5]
                EXTRN   WORD0(scc_cnt): WORD        ; u32[5]
                EXTRN   WORD0(scc_key): BYTE        ; u8[5]
                EXTRN   WORD0(scc_vol): BYTE        ; u8[5]
                EXTRN   WORD0(scc_wav): BYTE        ; u8[5][32]

?PR?SCC_RENDER?SCC_RENDER SEGMENT CODE
                RSEG    ?PR?SCC_RENDER?SCC_RENDER

; ========== 通道处理宏 ==========
; 参数: %1=通道号(0-4)
; xdata 偏移: step_val = %1*4, cnt = %1*4, key = %1, vol = %1
;             wav = %1*32
; 使用寄存器: R2(offs), R3(vol), R2(b), WR10(tmp)
;           DR0/DR28(64位操作), WR6(mix)

CH_OUT   MACRO   ch
        LOCAL   ch_skip
        ; 1. 检查 scc_step_val[ch] > 0
        MOV      DPTR, #(scc_step_val + ch * 4)
        MOV      DR28, @DR56          ; 读 step_val (32位)
        CMP      DR28, #0
        JZ       ch_skip

        ; 2. scc_cnt[ch] += scc_step_val[ch]
        MOV      DPTR, #(scc_cnt + ch * 4)
        MOV      DR0, @DR56           ; 读 cnt (32位)
        ADD      DR0, DR28            ; cnt += step
        MOV      @DR56, DR0           ; 写回 cnt

        ; 3. 检查 scc_key[ch]
        MOV      DPTR, #(scc_key + ch)
        MOVX     A, @DPTR
        JZ       ch_skip

        ; 4. offs = (cnt >> 16) & 0x1F
        ;    DR0 = cnt, R1=高字, offs = R1 & 0x1F
        MOV      R2, R1
        ANL      R2, #01FH

        ; 5. vol = scc_vol[ch]
        MOV      DPTR, #(scc_vol + ch)
        MOVX     A, @DPTR
        MOV      R3, A

        ; 6. b = scc_wav[ch][offs]
        ;    wav 基址 + ch*32 + offs
        MOV      DPL, #LOW (scc_wav + ch * 32)
        MOV      DPH, #HIGH(scc_wav + ch * 32)
        MOV      A, R2
        ADD      A, DPL
        MOV      DPL, A
        MOV      A, DPH
        ADDC     A, #0
        MOV      DPH, A
        MOVX     A, @DPTR
        MOV      R2, A                ; R2 = b

        ; 7. signed sample * vol >> 4
        ;    if b >= 128: tmp = -((256-b)*vol >> 4)
        ;    else:        tmp = (b*vol) >> 4
        CMP      R2, #080H
        JC       ch%1_pos

        ; 负半波: tmp = -(((256 - b) * vol) >> 4)
        MOVZ     WR10, R2
        MOV      WR0, #0100H
        SUB      WR0, WR10            ; WR0 = 256 - b
        MOVZ     WR10, R3
        MUL      WR10, WR0            ; WR10 = (256-b)*vol
        SRL      WR10                 ; >> 1
        SRL      WR10                 ; >> 2
        SRL      WR10                 ; >> 3
        SRL      WR10                 ; >> 4
        ; negate
        XRL      WR10, WR10           ; WR10 = 0
        SUB      WR10, WR10           ; WR10 = -WR10
        SJMP     ch%1_mix

ch%1_pos:
        ; 正半波: tmp = (b * vol) >> 4
        MOV      R11, R2
        MUL      R11, R3              ; WR10 = b * vol
        MOV      WR10, WR10
        SRL      WR10
        SRL      WR10
        SRL      WR10
        SRL      WR10

ch%1_mix:
        ADD      WR6, WR10            ; mix += tmp

ch_skip:
        ENDM

; ========== 主函数 ==========
scc_render PROC

        ; mix = 0
        XRL      WR6, WR6

        ; 5 通道展开
        CH_OUT   0
        CH_OUT   1
        CH_OUT   2
        CH_OUT   3
        CH_OUT   4

        ; clamp: if mix > 127, mix = 127
        CMP      WR6, #07FH
        JSLE     clamp_neg
        MOV      WR6, #07FH

clamp_neg:
        ; if mix < -128, mix = -128
        CMP      WR6, #0FF80H
        JSGE     done
        MOV      WR6, #0FF80H

done:
        ; return 128 + (u8)mix
        MOVZ     WR10, R7             ; WR10 = low byte of mix
        ADD      WR10, #080H
        MOV      R7, R11              ; 返回值在 R7

        RET

scc_render ENDP

                END
