// TinyUSB configuration: which USB classes we use and their buffer sizes.
#pragma once

#define CFG_TUSB_RHPORT0_MODE   OPT_MODE_DEVICE
#define CFG_TUD_ENABLED         1
#define CFG_TUD_ENDPOINT0_SIZE  64

#define CFG_TUD_HID             1   // the gamepad
#define CFG_TUD_CDC             1   // USB serial, for printf debugging
#define CFG_TUD_MSC             0
#define CFG_TUD_MIDI            0
#define CFG_TUD_VENDOR          0   // the reset interface uses its own driver

#define CFG_TUD_HID_EP_BUFSIZE  16

#define CFG_TUD_CDC_RX_BUFSIZE  64
#define CFG_TUD_CDC_TX_BUFSIZE  256
#define CFG_TUD_CDC_EP_BUFSIZE  64
