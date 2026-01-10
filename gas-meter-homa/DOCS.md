# Home Assistant add-on: HomA MQTT gas meter

This add-on is a gas meter used by HomA MQTT framework.

It shows the counter in m³ of a gas meter. This is done by counting pulses of a given resolution.
The start counter value needs to be set manually.

## Installation

Install a hall sensor, reed contact or retro-reflective sensor on the gas meter as works best for you.
The use of a Schmitt-Trigger is recommended. Connect the pulse sensor to a GPIO of the Raspberry Pi.

Modify `gas_meter.py` settings to your needs.

All relevant settings are done in the add-on Configuration page (see also #Configuration).

## How to use

Configure and start the add-on. That's all.

To set the current counter use
```shell
$ mosquitto_pub -r -t "/devices/123456-gas-meter/controls/Volume" -m "123.4"
```

To remove all retained MQTT messages from the broker, you can use
```shell
$ /etc/services.d/gas-meter/gas_meter.py -r
```

## Configuration

The add-on supports the internal (Home Assistant) or an external MQTT broker. To configure the external MQTT broker you have to activate the _"Show unused optional configuration options"_.

You can modify the subscribed topic id `<systemId>` by setting _"HomA System ID"_.

The _GPIO Pin_ counts the raising edges of the gas pulses. The _calorific value_ is used to convert the volume (m³) to an energy (kWh).
