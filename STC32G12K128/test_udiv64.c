/*
 * test_udiv64.c - 测试 ULDIV64_HUGE wrapper
 * LARGE 模式编译, 调用 A51 wrapper
 *
 * (54<<32)|2660761600 = 234588995584
 * / 8820 = 26597391
 * / 890820 = 263340
 * / 1 = 234588995584 (截断32位)
 */
#include <STC32G.H>

extern unsigned long call_udiv64_32(unsigned long dL);

volatile unsigned long result;

void main(void) {
    /* 测试1: 100/10 = 10 */
    result = call_udiv64_32(10);
    /* 预期: result = 234588995584/10 = 23458899558 (截断32位) */

    /* 测试2: 除以 8820 = 26597391 */
    result = call_udiv64_32(8820);

    /* 测试3: 除以 890820 = 263340 */
    result = call_udiv64_32(890820);

    /* 测试4: 除以 1 */
    result = call_udiv64_32(1);

    while (1);
}
