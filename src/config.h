// ============================================================================
//  config.h — the file you're meant to edit.
//  Pin numbers are GPIO numbers ("GP2" on the Pico pinout = 2),
//  NOT physical pin numbers.
// ============================================================================
#pragma once

// ---------------------------------------------------------------------------
//  Buttons
// ---------------------------------------------------------------------------
// Wiring: one leg of each switch to its GPIO, the other leg to GND.
// The internal pull-up resistors are enabled, so no external resistors needed.
//
// The ORDER of this list is the button number the computer sees:
// the first entry is "Button 1", the second is "Button 2", etc. (max 16).
// Add, remove or reorder entries freely. The name is only used for debug output.
//
// A tilt switch (ball/mercury type) is just another switch, so it goes here too.
#define GUITAR_BUTTONS                 \
    { "green",       2 },              \
    { "red",         3 },              \
    { "yellow",      4 },              \
    { "blue",        5 },              \
    { "orange",      6 },              \
    { "strum_up",    7 },              \
    { "strum_down",  8 },              \
    { "start",       9 },              \
    { "select",     10 },  /* a.k.a. Star Power / Back */ \
    { "tilt",       11 },

// Ignore further changes on a button for this long after it changes.
// The first edge is reported instantly, so this does NOT add input lag.
// Raise it if a switch "double-triggers"; tilt switches can be very bouncy.
#define DEBOUNCE_MS 5

// ---------------------------------------------------------------------------
//  Analog axes
// ---------------------------------------------------------------------------
// Only GPIO 26, 27, 28 can read analog values on the RP2040. Use -1 to disable.
//
// Whammy: a potentiometer. Outer legs to 3V3 and GND, middle leg to the GPIO.
#define WHAMMY_PIN      26
// Analog tilt: e.g. one axis of an analog accelerometer. Disabled by default
// (most builds use a tilt *switch* in the button list instead).
#define TILT_AXIS_PIN  -1

// Calibration. Raw readings go from 0 to 4095. Enable DEBUG_PRINT, open the
// serial monitor, move the whammy end to end, and put the values you see here.
// If the axis works backwards, swap MIN and MAX.
#define WHAMMY_RAW_MIN  0
#define WHAMMY_RAW_MAX  4095
#define TILT_RAW_MIN    0
#define TILT_RAW_MAX    4095

// Smoothing for analog axes, 0..7. Higher = steadier but slower to respond.
#define AXIS_SMOOTHING  2

// ---------------------------------------------------------------------------
//  Debugging
// ---------------------------------------------------------------------------
// 1 = print button presses and raw analog values to the USB serial port.
// Open it with the VS Code Serial Monitor (or any terminal) to watch.
#define DEBUG_PRINT     1

// Light the board's LED while any button is held (handy for checking wiring).
#define LED_ON_PRESS    1
