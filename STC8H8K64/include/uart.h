#ifndef UART_H
#define UART_H

#include <stdint.h>

void uart_init(uint32_t baud);
void uart_send(uint8_t data);
uint8_t uart_rx_ready(void);

#endif
