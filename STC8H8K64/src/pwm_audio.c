#include "pwm_audio.h"
#include "fw_hal.h"

void pwm_audio_init(uint32_t sample_rate) {
    /* PWMA.PWM1 on P2.0 (default port) for audio output */
    GPIO_P2_SetMode(GPIO_Pin_0, GPIO_Mode_Output_PP);

    /* PWM prescaler = 0, period = 255 (8-bit duty for audio) */
    PWMA_SetPrescaler(0);
    PWMA_SetPeriod(255);

    /* PWM1 output mode: PWM_HighIfLess (duty = CCR / ARR) */
    PWMA_PWM1_ConfigOutputMode(PWM_OutputMode_PWM_HighIfLess);
    PWMA_PWM1_SetPortDirection(PWMA_PortDirOut);

    /* Enable PWM1 output pin and overall output */
    PWMA_SetPinOutputState(PWM_Pin_1, HAL_State_ON);
    PWMA_SetOverallState(HAL_State_ON);

    /* Counter up, edge alignment */
    PWMA_SetCounterDirection(PWM_CounterDirection_Up);
    PWMA_SetEdgeAlignment(PWM_EdgeAlignment_Side);
    PWMA_SetCounterState(HAL_State_ON);

    /* Timer3 drives sample rate */
    TIM_Timer3_Config(HAL_State_ON, 0, sample_rate, HAL_State_ON);
}

void pwm_audio_set_sample(int8_t sample) {
    /* Map int8_t (-128~127) to 0~255 PWM duty */
    uint16_t duty = (uint16_t)((int16_t)sample + 128);
    PWMA_PWM1_SetCaptureCompareValue(duty);
}
