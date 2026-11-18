#pragma once
#include <stdint.h>

// What we send to the computer every time something changes.
// Its layout must match the HID report descriptor in usb_descriptors.c.
typedef struct __attribute__((packed)) {
    uint16_t buttons;   // bit 0 = Button 1, bit 1 = Button 2, ...
    uint8_t  whammy;    // X axis, 0..255
    uint8_t  tilt;      // Y axis, 0..255
} guitar_report_t;

void inputs_init(void);

// Read every switch and analog input and fill in the report.
void inputs_read(guitar_report_t *report);

// For debug output.
int         inputs_button_count(void);
const char *inputs_button_name(int index);
uint16_t    inputs_whammy_raw(void);
uint16_t    inputs_tilt_raw(void);
