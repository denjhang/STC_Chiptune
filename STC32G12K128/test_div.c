#include <STC32G.H>
#include "long64.h"

LONGLONG a, b, q;

void main(void) {
    WORD64(a, 100UL, 0UL);
    WORD64(b, 3UL, 0UL);
    ULDIV64(a, b, q);
    while(1);
}
