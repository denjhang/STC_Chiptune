#include "..\System\os_link.h"

/* forward declarations */
extern void AudioTask(void);
extern void UartTask(void);
extern void LedTask(void);

void start_hook(void)
{
	uStartTask_Ready(AudioTask);
	uStartTask_Ready(UartTask);
	uStartTask_Ready(LedTask);
}
