#include "uart.h"
#include "fw_hal.h"

void uart_init(uint32_t baud) {
    UART1_Config8bitUart(UART1_BaudSource_Timer2, HAL_State_ON, baud);
}

void uart_send(uint8_t data) {
    UART1_TxChar(data);
}

uint8_t uart_rx_ready(void) {
    return RI ? 1 : 0;
}
