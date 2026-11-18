cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.3.1)
set(toolchainVersion 15_2_Rel1)
set(picotoolVersion 2.3.1)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================

# Change this if you're not on a plain Raspberry Pi Pico
# (e.g. "waveshare_rp2040_zero", "adafruit_kb2040", "sparkfun_promicro").
set(PICO_BOARD pico CACHE STRING "Board type")

include(pico_sdk_import.cmake)

project(guitar C CXX ASM)
pico_sdk_init()

add_executable(guitar
    src/main.c
    src/inputs.c
    src/usb_descriptors.c
)

# tusb_config.h lives in src/
target_include_directories(guitar PRIVATE ${CMAKE_CURRENT_LIST_DIR}/src)

target_compile_definitions(guitar PRIVATE
    # Lets the VS Code "Run" button / picotool reboot the board into BOOTSEL
    # without anyone touching the BOOTSEL button. See usb_descriptors.c.
    PICO_ENABLE_USB_RESET_VIA_VENDOR_INTERFACE=1
    PICO_ENABLE_USB_RESET_VIA_BAUD_RATE=1
    PICO_USB_RESET_SUPPORT_MS_OS_20_DESCRIPTOR=1
    PICO_USB_RESET_MS_OS_20_DESCRIPTOR_ITF=3
)

target_link_libraries(guitar PRIVATE
    pico_stdlib
    hardware_adc
    tinyusb_device
    pico_usb_reset
    pico_unique_id
)

# printf() goes over the same USB cable (shows up as a serial port).
pico_enable_stdio_usb(guitar 1)
pico_enable_stdio_uart(guitar 0)

pico_add_extra_outputs(guitar)
