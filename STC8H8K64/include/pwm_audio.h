#ifndef PWM_AUDIO_H
#define PWM_AUDIO_H

#include <stdint.h>

void pwm_audio_init(uint32_t sample_rate);
void pwm_audio_set_sample(int8_t sample);

#endif
