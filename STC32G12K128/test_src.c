unsigned long udiv64_q(unsigned long nh, unsigned long nl, unsigned int dh, unsigned int dl) {
    (void)nl;
    return nh / dl;
}
