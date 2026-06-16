#include "stc.h"
#include "util.h"

WORD reverse2(WORD w)
{
    WORD ret;

    ((BYTE *)&ret)[0] = ((BYTE *)&w)[1];
    ((BYTE *)&ret)[1] = ((BYTE *)&w)[0];

    return ret;
}
