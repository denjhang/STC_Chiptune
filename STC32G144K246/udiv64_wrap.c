#include "long64.h"

unsigned long udiv64_calc(unsigned long ah, unsigned long al, unsigned long bh, unsigned long bl) {
    LONGLONG a, b, q;
    a.h = ah; a.l = al;
    b.h = bh; b.l = bl;
    ULDIV64(a, b, q);
    return q.l;
}
