# Home Assistant add-on: HomA MQTT gas meter

This add-on is a gas meter used by HomA MQTT framework.

It shows the counter in m^3 of a gas meter. This is done by counting pulses of a given resolution.
The start counter value needs to be set manually.

## Installation

Install a hall sensor, reed contact or retro-reflective sensor on the gas meter as works best for you.
The use of a Schmitt-Trigger is recommended. Connect the pulse sensor to a GPIO of the Raspberry Pi.

Modify `gas_meter.py` settings to your needs.

## How to use

To set the current counter use
```shell
$ mosquitto_pub -r -t "/devices/123456-gas-meter/controls/Count" -m "123.4"
```

## Configuration

The add-on supports the internal (Home Assistant) or an external MQTT broker. To configure the external MQTT broker you have to activate the _"Show unused optional configuration options"_.

You can modify the subscribed topic id `<systemId>` by setting _"HomA System ID"_.
