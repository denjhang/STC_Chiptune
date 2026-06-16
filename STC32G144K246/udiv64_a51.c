/* udiv64_a51.c - 64位无符号除法 (C251 SRC+ASM, LARGE 模式兼容)
 * 算法来自 STC32G ULDIV64.A51，参数全部通过 DR 寄存器传递
 *
 * 编译流程: C251 udiv64_a51.c LARGE SRC → A251 udiv64_a51.SRC → udiv64_a51.OBJ
 *
 * C251 PARM251 约定: long 参数通过 DR4, DR0 传递
 *   u32 udiv64_q(nH, nL, dH, dL)
 *   DR4=被除数高32位, DR0=被除数低32位
 *   通过 R stack 传: 除数高32位, 除数低32位
 *   返回: DR4:DR0 = 商(低32位在DR0)
 *
 * 由于 C251 前2个 long 参数用 DR4/DR0 传，后续参数上 stack 或固定段
 * 我们直接用 SRC+ASM 完全接管，避免段传参问题
 */

#pragma SRC

/* C 入口: 设置参数到寄存器，调用汇编除法
 * 返回商的低32位 */
u32 udiv64_q(u32 nH, u32 nL, u32 dH, u32 dL) {
    /* 通过 SRC 生成汇编后手写 */
#pragma ASM
    ; nH 在 DR4 (编译器分配), nL 在 DR0
    ; dH, dL 在栈上 (编译器通过固定段传)
    ; 但 SRC 模式下 C 变量映射到寄存器
    ; 我们直接用完整的内嵌汇编替代
    ; 这里先占位，后面在 SRC 文件中替换
    NOP
#pragma ENDASM
    return 0;
}
