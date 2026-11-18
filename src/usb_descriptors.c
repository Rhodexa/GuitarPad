// USB descriptors: how the board introduces itself to the computer.
//
// The device is a "composite" device with three parts:
//   - interface 0:   HID gamepad          (what games see)
//   - interface 1-2: CDC serial port      (printf debug output)
//   - interface 3:   Raspberry Pi reset   (lets picotool / VS Code "Run" reflash
//                                          without pressing BOOTSEL)
//
// You normally only touch this file if you change guitar_report_t in inputs.h
// (the HID report descriptor below must describe the same bytes),
// or want a different device name.
#include <string.h>

#include "tusb.h"
#include "pico/unique_id.h"
#include "pico/usb_reset.h"

#include "inputs.h"

// Placeholder IDs, fine for personal/classroom use. Real products need their own.
#define USB_VID   0xCAFE
#define USB_PID   0x4710
#define USB_BCD   0x0210   // USB 2.1: needed for the BOS descriptor the reset interface uses

#define STR_MANUFACTURER  "Rhodune"
#define STR_PRODUCT       "Guitar"

// ---------------------------------------------------------------------------
//  HID report descriptor: describes the bytes of guitar_report_t
// ---------------------------------------------------------------------------
uint8_t const desc_hid_report[] = {
    HID_USAGE_PAGE ( HID_USAGE_PAGE_DESKTOP ),
    HID_USAGE      ( HID_USAGE_DESKTOP_GAMEPAD ),
    HID_COLLECTION ( HID_COLLECTION_APPLICATION ),

        // uint16_t buttons: 16 one-bit buttons, Button 1..16
        HID_USAGE_PAGE   ( HID_USAGE_PAGE_BUTTON ),
        HID_USAGE_MIN    ( 1 ),
        HID_USAGE_MAX    ( 16 ),
        HID_LOGICAL_MIN  ( 0 ),
        HID_LOGICAL_MAX  ( 1 ),
        HID_REPORT_COUNT ( 16 ),
        HID_REPORT_SIZE  ( 1 ),
        HID_INPUT        ( HID_DATA | HID_VARIABLE | HID_ABSOLUTE ),

        // uint8_t whammy, uint8_t tilt: X and Y axes, 0..255
        HID_USAGE_PAGE   ( HID_USAGE_PAGE_DESKTOP ),
        HID_USAGE        ( HID_USAGE_DESKTOP_X ),
        HID_USAGE        ( HID_USAGE_DESKTOP_Y ),
        HID_LOGICAL_MIN  ( 0 ),
        HID_LOGICAL_MAX_N( 255, 2 ),
        HID_REPORT_COUNT ( 2 ),
        HID_REPORT_SIZE  ( 8 ),
        HID_INPUT        ( HID_DATA | HID_VARIABLE | HID_ABSOLUTE ),

    HID_COLLECTION_END
};
_Static_assert(sizeof(guitar_report_t) == 4, "Update desc_hid_report to match guitar_report_t");

uint8_t const *tud_hid_descriptor_report_cb(uint8_t instance) {
    (void)instance;
    return desc_hid_report;
}

// The host may ask for the current report or send us one (e.g. LEDs).
// We don't need either, so just say "nothing".
uint16_t tud_hid_get_report_cb(uint8_t instance, uint8_t report_id, hid_report_type_t report_type,
                               uint8_t *buffer, uint16_t reqlen) {
    (void)instance; (void)report_id; (void)report_type; (void)buffer; (void)reqlen;
    return 0;
}

void tud_hid_set_report_cb(uint8_t instance, uint8_t report_id, hid_report_type_t report_type,
                           uint8_t const *buffer, uint16_t bufsize) {
    (void)instance; (void)report_id; (void)report_type; (void)buffer; (void)bufsize;
}

// ---------------------------------------------------------------------------
//  Device descriptor
// ---------------------------------------------------------------------------
static tusb_desc_device_t const desc_device = {
    .bLength            = sizeof(tusb_desc_device_t),
    .bDescriptorType    = TUSB_DESC_DEVICE,
    .bcdUSB             = USB_BCD,
    // Composite device using Interface Association Descriptors (needed for CDC)
    .bDeviceClass       = TUSB_CLASS_MISC,
    .bDeviceSubClass    = MISC_SUBCLASS_COMMON,
    .bDeviceProtocol    = MISC_PROTOCOL_IAD,
    .bMaxPacketSize0    = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor           = USB_VID,
    .idProduct          = USB_PID,
    .bcdDevice          = 0x0100,
    .iManufacturer      = 1,
    .iProduct           = 2,
    .iSerialNumber      = 3,
    .bNumConfigurations = 1,
};

uint8_t const *tud_descriptor_device_cb(void) {
    return (uint8_t const *)&desc_device;
}

// ---------------------------------------------------------------------------
//  Configuration descriptor
// ---------------------------------------------------------------------------
enum { ITF_HID = 0, ITF_CDC, ITF_CDC_DATA, ITF_RESET, ITF_COUNT };

#define EP_HID_IN     0x81
#define EP_CDC_NOTIF  0x82
#define EP_CDC_OUT    0x03
#define EP_CDC_IN     0x83

#define CONFIG_LEN (TUD_CONFIG_DESC_LEN + TUD_HID_DESC_LEN + TUD_CDC_DESC_LEN + TUD_RPI_RESET_DESC_LEN)

_Static_assert(ITF_RESET == PICO_USB_RESET_MS_OS_20_DESCRIPTOR_ITF,
               "Update PICO_USB_RESET_MS_OS_20_DESCRIPTOR_ITF in CMakeLists.txt");

static uint8_t const desc_configuration[] = {
    TUD_CONFIG_DESCRIPTOR(1, ITF_COUNT, 0, CONFIG_LEN, 0x00, 100),

    // poll interval 1 ms = lowest latency USB full-speed allows
    TUD_HID_DESCRIPTOR(ITF_HID, 0, HID_ITF_PROTOCOL_NONE, sizeof(desc_hid_report),
                       EP_HID_IN, CFG_TUD_HID_EP_BUFSIZE, 1),

    TUD_CDC_DESCRIPTOR(ITF_CDC, 4, EP_CDC_NOTIF, 8, EP_CDC_OUT, EP_CDC_IN, 64),

    TUD_RPI_RESET_DESCRIPTOR(ITF_RESET, 5),
};

uint8_t const *tud_descriptor_configuration_cb(uint8_t index) {
    (void)index;
    return desc_configuration;
}

// ---------------------------------------------------------------------------
//  String descriptors
// ---------------------------------------------------------------------------
static char serial_str[2 * PICO_UNIQUE_BOARD_ID_SIZE_BYTES + 1];

static char const *const string_desc[] = {
    NULL,                 // 0: language (handled below)
    STR_MANUFACTURER,     // 1
    STR_PRODUCT,          // 2
    serial_str,           // 3: filled from the flash chip's unique ID
    "Guitar Debug Serial",// 4
    "Reset",              // 5
};

uint16_t const *tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void)langid;
    static uint16_t buf[32];
    uint8_t len;

    if (index == 0) {
        buf[1] = 0x0409;  // English (US)
        len = 1;
    } else {
        if (index >= sizeof(string_desc) / sizeof(string_desc[0])) return NULL;
        if (index == 3 && serial_str[0] == 0) {
            pico_get_unique_board_id_string(serial_str, sizeof serial_str);
        }
        const char *s = string_desc[index];
        len = (uint8_t)strlen(s);
        if (len > 31) len = 31;
        for (uint8_t i = 0; i < len; i++) buf[1 + i] = (uint16_t)s[i];
    }

    buf[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * len + 2));
    return buf;
}
