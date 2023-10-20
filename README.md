## bt-lamp
This is a python lib for control your Bluetooth Low Energy (BLE) lamp.

## Features
The lib offers the following functionality:
- Turning the lamp on / off
- Controlling lamp brightness
- Controlling lamp temperature
- Sending initial setup signal

## Lamp compatibility
bt-lamp should work with at least some lamps (that are non-RGB, dimmable, cool/warm only) that use the following app

- [LampSmart Pro](https://play.google.com/store/apps/details?id=com.jingyuan.lamp)

Lamps tested to work include

- Natali Kovaltseva with BT support

### OS

Lib tested on raspberry 2. Lib need sudo permissions

### Hardware
Your bluetooth card needs to support at least Bluetooth v4.0 LE and have working drivers / firmware for Linux.

Working cards (not exhaustive):

 - Intel AC-8265
 - Broadcom BCM20702A0, see https://github.com/winterheart/broadcom-bt-firmware
 - Qualcomm Atheros QCA9377
 - Realtek RTL8761BU (most "cheap" eBay USB BT dongles) via `firmware-realtek` package
 - TP-Link UB500 Adapter
   

## Usage

You van use lib from command line or import as module. To install the module, run:

    pip install bt_lamp

### Comand line syntax
sudo -E env PATH=$PATH python -m bt_lamp command name [level] [log-level]

Available command:
 - setup           connect to the lamp
 - on              turn the lamp on
 - off             turn the lamp off
 - cold  <1..10>    set cold brightness
 - warm  <1..10>    set warm brightness
 - dual  <1..10>    set dual brightness

 level - lamp brightness, number between 1 and 10

### Using as module

```
from bt_lamp import BtLamp

lamp = BtLamp("MY_LAMP")

# setup
lamp.setup()

# on
lamp.on()

# off
lamp.off()

# cold
lamp.cold(5)

# warm
lamp.warm(5)

# dual
lamp.dual(5)

```

### Initial setup
Before you can control your lamp, you have to perform an initial setup so the lamp will remember a unique name that you specify.

To setup more than one lamp, setup each lamp individually by assigning a new name to each lamp.

To perform the initial setup:
- Think up of a name. In this example we will use LAMP0.
- Turn the lamp on using the power switch
- Within a few seconds after powering the lamp on, send a setup signal from your device:

```
sudo -E env PATH=$PATH python -m bt_lamp setup LAMP0
```
  
- If you see the lamp flashing, the connection is established

To reiterate **sudo permissions are required to access the ble stack on modern linux**
