// SPDX-License-Identifier: GPL-2.0+
/*
 * Xiaomi Mi Box 4 (MDZ-21-AA) board support
 *
 * A cold boot leaves GPIOAO_4 as an input and the shared HDMI/USB supply
 * disabled.  Xiaomi's BL33 executes "gpio set gpioao_4 1".  Reproduce the
 * resulting register state verified on hardware:
 *
 *   0xc8100024: 0xbfff3fff -> 0xbfff3fef
 */

#include <asm/io.h>
#include <init.h>
#include <led.h>
#include <linux/bitops.h>

#define MIBOX4_GPIOAO_4_EN_N	BIT(4)
#define MIBOX4_GPIOAO_4_OUT	BIT(20)
#define MIBOX4_AO_GPIO_O_EN_N	((void __iomem *)0xc8100024)

static void mibox4_enable_hdmi_usb_power(void)
{
	clrsetbits_le32(MIBOX4_AO_GPIO_O_EN_N,
			MIBOX4_GPIOAO_4_EN_N | MIBOX4_GPIOAO_4_OUT,
			MIBOX4_GPIOAO_4_OUT);
}

static void mibox4_enable_power_led(void)
{
	struct udevice *dev;

	/* Xiaomi's BL33 drives GPIOX_6 high during normal startup. */
	if (!led_get_by_label("mibox4:power", &dev))
		led_set_state(dev, LEDST_ON);
}

int board_early_init_f(void)
{
	mibox4_enable_hdmi_usb_power();
	return 0;
}

int board_init(void)
{
	mibox4_enable_hdmi_usb_power();
	mibox4_enable_power_led();
	return 0;
}
