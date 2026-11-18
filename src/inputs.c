// Reading the physical controls: switches (with debouncing) and analog axes.
#include "inputs.h"
#include "config.h"

#include "pico/stdlib.h"
#include "hardware/adc.h"

typedef struct {
    const char *name;
    uint8_t     pin;
} button_cfg_t;

static const button_cfg_t buttons[] = { GUITAR_BUTTONS };
#define NUM_BUTTONS ((int)(sizeof(buttons) / sizeof(buttons[0])))
_Static_assert(NUM_BUTTONS <= 16, "The report only has room for 16 buttons");

static bool     pressed[NUM_BUTTONS];
static uint32_t last_change_us[NUM_BUTTONS];

// Analog state: filtered value scaled up by 2^AXIS_SMOOTHING
typedef struct {
    int      pin;
    int      raw_min, raw_max;
    uint32_t filtered;
    uint16_t raw;
} axis_t;

static axis_t whammy = { WHAMMY_PIN,    WHAMMY_RAW_MIN, WHAMMY_RAW_MAX, 0, 0 };
static axis_t tilt   = { TILT_AXIS_PIN, TILT_RAW_MIN,   TILT_RAW_MAX,   0, 0 };

static void axis_init(axis_t *a) {
    if (a->pin < 0) return;
    adc_gpio_init(a->pin);
}

static uint8_t axis_read(axis_t *a) {
    if (a->pin < 0) return 0;

    adc_select_input(a->pin - 26);   // GPIO26 = ADC0, 27 = ADC1, 28 = ADC2
    a->raw = adc_read();             // 0..4095

    // Exponential moving average to tame pot noise.
    if (a->filtered == 0) a->filtered = (uint32_t)a->raw << AXIS_SMOOTHING;
    a->filtered = a->filtered - (a->filtered >> AXIS_SMOOTHING) + a->raw;
    int value = (int)(a->filtered >> AXIS_SMOOTHING);

    // Map calibrated range onto 0..255 (works for reversed ranges too).
    int span = a->raw_max - a->raw_min;
    if (span == 0) return 0;
    int out = (value - a->raw_min) * 255 / span;
    if (out < 0)   out = 0;
    if (out > 255) out = 255;
    return (uint8_t)out;
}

void inputs_init(void) {
    for (int i = 0; i < NUM_BUTTONS; i++) {
        gpio_init(buttons[i].pin);
        gpio_set_dir(buttons[i].pin, GPIO_IN);
        gpio_pull_up(buttons[i].pin);
    }

    adc_init();
    axis_init(&whammy);
    axis_init(&tilt);
}

void inputs_read(guitar_report_t *report) {
    uint32_t now = time_us_32();
    uint16_t bits = 0;

    for (int i = 0; i < NUM_BUTTONS; i++) {
        bool raw = !gpio_get(buttons[i].pin);   // pulled up, so pressed = low

        // "Eager" debounce: accept a change immediately, then ignore the
        // switch for DEBOUNCE_MS so contact bounce can't toggle it back.
        if (raw != pressed[i] && (now - last_change_us[i]) >= DEBOUNCE_MS * 1000u) {
            pressed[i] = raw;
            last_change_us[i] = now;
        }
        if (pressed[i]) bits |= (uint16_t)(1u << i);
    }

    report->buttons = bits;
    report->whammy  = axis_read(&whammy);
    report->tilt    = axis_read(&tilt);
}

int         inputs_button_count(void)      { return NUM_BUTTONS; }
const char *inputs_button_name(int index)  { return buttons[index].name; }
uint16_t    inputs_whammy_raw(void)        { return whammy.raw; }
uint16_t    inputs_tilt_raw(void)          { return tilt.raw; }
