// Guitar controller firmware: read inputs, send a USB HID report when they change.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pico/stdlib.h"
#include "tusb.h"

#include "config.h"
#include "inputs.h"

static void debug_print(const guitar_report_t *r) {
#if DEBUG_PRINT
    printf("buttons:");
    if (r->buttons == 0) printf(" (none)");
    for (int i = 0; i < inputs_button_count(); i++) {
        if (r->buttons & (1u << i)) printf(" %s", inputs_button_name(i));
    }
    printf(" | whammy %3u (raw %4u) | tilt %3u (raw %4u)\n",
           r->whammy, inputs_whammy_raw(), r->tilt, inputs_tilt_raw());
#else
    (void)r;
#endif
}

static void led_init(void) {
#if LED_ON_PRESS && defined(PICO_DEFAULT_LED_PIN)
    gpio_init(PICO_DEFAULT_LED_PIN);
    gpio_set_dir(PICO_DEFAULT_LED_PIN, GPIO_OUT);
#endif
}

static void led_set(bool on) {
#if LED_ON_PRESS && defined(PICO_DEFAULT_LED_PIN)
    gpio_put(PICO_DEFAULT_LED_PIN, on);
#else
    (void)on;
#endif
}

int main(void) {
    tusb_init();      // start USB (must happen before stdio_init_all)
    stdio_init_all(); // printf over USB serial
    inputs_init();
    led_init();

    guitar_report_t report = {0};
    guitar_report_t last_sent;
    memset(&last_sent, 0xFF, sizeof last_sent);   // force a first report

    // Analog values only get printed when they move this much, to keep
    // pot noise from flooding the serial monitor.
    uint8_t last_printed_whammy = 0, last_printed_tilt = 0;

    while (true) {
        tud_task();   // let TinyUSB do its thing; call this often

        inputs_read(&report);
        led_set(report.buttons != 0);

        if (memcmp(&report, &last_sent, sizeof report) != 0 && tud_hid_ready()) {
            // Only remember it as sent if the send actually happened,
            // so a busy moment just means we retry on the next loop.
            if (tud_hid_report(0, &report, sizeof report)) {
                bool buttons_changed = report.buttons != last_sent.buttons;
                bool axes_moved = abs(report.whammy - last_printed_whammy) > 8 ||
                                  abs(report.tilt   - last_printed_tilt)   > 8;
                if (buttons_changed || axes_moved) {
                    debug_print(&report);
                    last_printed_whammy = report.whammy;
                    last_printed_tilt   = report.tilt;
                }
                last_sent = report;
            }
        }
    }
}
