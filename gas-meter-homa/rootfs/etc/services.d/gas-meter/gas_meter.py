#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=import-outside-toplevel, logging-fstring-interpolation
"""
Reads gas meter pulses and sends them to MQTT broker used by HomA framework.

Holger Mueller
2018/03/12 Initial revision
2020/10/15 Made script Python3 compatible
2025/12/27 Added support for Home Assistant add-on system
2026/01/05 Replaced RPi.GPIO with gpiod for GPIO access (required by Raspberry Pi 5)
2026/01/09 Renamed "Count" topic to "Volume", added "Energy" topic by using calorific_value config option
2026/01/11 Refacored use of global variables to function attributes, fixed debounce handling
2026/01/15 Added suggested_display_precision to Home Assistant discovery config messages
"""

import argparse
from datetime import timedelta
import sys
import json
import os.path
import time
import ssl
# import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import addon  # provides logging like bashio, provides Home Assistant / MQTT broker config


debug = addon.config.get('debug', False)
device_name = addon.config.get('device_name', "Gas Meter")
# pinout see https://pinout.xyz or https://pinout-xyz.github.io/pinout-2024
gpio_pin = addon.config.get('gpio_pin', 17)  # Line 17 = GPIO/BCM pin 17 = physical pin 11
calorific_value: float = addon.config.get('calorific_value', 11.4)  # kWh/m^3
systemId = addon.config.get('homa_system_id', "123456-gas-meter")
room = addon.config.get('homa_room', "Sensors")
area = addon.config.get('hass_area', "Energie")

# config here ...
PY_FILE = os.path.basename(__file__)
# Reminder if HomA setup messages have been send, delete and restart to resend
INIT_FILE = "/dev/shm/homa_init."+ systemId
GPIO_CHIP = "/dev/gpiochip0"
RESOLUTION = 0.01 # m^3 / pulse
DEBOUNCE_MS = 1000 # debounce time [ms]

T_VOLUME = "Volume"
T_ENERGY = "Energy"
T_FLOW_RATE = "Flow rate"
T_TIMESTAMP = "Timestamp"
# config components control room name (if wanted) here
mqtt_arr = [
    {'topic': T_VOLUME,    'room': 'Home', 'unit': ' m³',   'precision': 2, 'class': 'gas'},
    {'topic': T_ENERGY,    'room': '',     'unit': ' kWh',  'precision': 2, 'class': 'energy'},
    {'topic': T_FLOW_RATE, 'room': '',     'unit': ' m³/h', 'precision': 3, 'class': 'volume_flow_rate'},
    {'topic': T_TIMESTAMP, 'room': '',     'unit': '',      'class': '_datetime'}]


def get_topic(t1 = None, t2 = None, t3 = None) -> str:
    """Create topic string."""
    if not t1:
        addon.log.error("get_topic(): t1 not specified!")
        sys.exit(1)
    topic = f"/devices/{systemId}"
    if t1:
        topic += "/"+ t1
    if t2:
        topic += "/"+ t2
    if t3:
        topic += "/"+ t3
    addon.log.debug("get_topic(): '%s'", topic)
    return topic


def homa_init():
    "Publish HomA setup messages to MQTT broker."
    # check if we need to init HomA
    if os.path.isfile(INIT_FILE):
        addon.log.info(f"{PY_FILE} HomA setup data not reloaded, to do so delete {INIT_FILE} and restart.")
        return
    addon.log.info(f"{PY_FILE} Publishing HomA setup data ...")
    # set room name
    mqttc.publish(get_topic("meta/room"), room, retain=True)
    # set device name
    mqttc.publish(get_topic("meta/name"), device_name, retain=True)
    # setup controls
    order = 1
    for mqtt_item in mqtt_arr:
        mqttc.publish(get_topic("controls", mqtt_item['topic'], "meta/type"), "text", retain=True)
        mqttc.publish(get_topic("controls", mqtt_item['topic'], "meta/order"), order, retain=True)
        mqttc.publish(get_topic("controls", mqtt_item['topic'], "meta/unit"), mqtt_item['unit'], retain=True)
        mqttc.publish(get_topic("controls", mqtt_item['topic'], "meta/room"), mqtt_item['room'], retain=True)
        homeassistant_config(mqtt_item)
        order += 1
    # create init file (do not fail if not writable)
    try:
        with open(INIT_FILE, 'w', encoding="utf-8"):
            pass
    except OSError as exc:  # pragma: no cover - environment dependent
        addon.log.warning("Could not create HomA init file %s: %s", INIT_FILE, exc)


def homeassistant_config(mqtt_item):
    """Send the Home Assistant config messages to enable discovery"""
    if 'class' not in mqtt_item:
        return
    object_id = systemId+"-"+mqtt_item['topic'].replace(" ", "-")
    payload = {
        "device_class":mqtt_item['class'],
        "state_topic":"/devices/"+systemId+"/controls/"+mqtt_item['topic'],
        "name":mqtt_item['topic'],
        "unique_id":object_id,
        "object_id":object_id,
        "device":{
            "identifiers":[systemId],
            "name":device_name,
            "manufacturer":"Holger Müller",
            "model":"Raspberry Pi 5 Gas Meter Module",
            "suggested_area":area
        }
    }
    if mqtt_item['class'] in ["temperature", "power_factor"]:
        payload['state_class'] = "measurement"
    if mqtt_item['class'] in ["energy", "gas"]:
        payload['state_class'] = "total_increasing"
    # special treatment for _int
    if mqtt_item['class'] == "_int":
        del payload['device_class']
        payload['native_value'] = "int"
    # special treatment for _datetime
    if mqtt_item['class'] == "_datetime":
        del payload['device_class']
        payload['value_template'] = "{{ as_datetime(value) }}"
        payload['icon'] = "mdi:calendar-arrow-right"
    # set suggested_display_precision only if available
    if 'precision' in mqtt_item and isinstance(mqtt_item['precision'], int):
        payload['suggested_display_precision'] = mqtt_item['precision']
    # set unit_of_measurement only if available
    if 'unit' in mqtt_item and mqtt_item['unit']:
        payload['unit_of_measurement'] = mqtt_item['unit'].strip()
    # set value_template only if available
    if 'template' in mqtt_item:
        payload['value_template'] = mqtt_item['template']
    topic = "homeassistant/sensor/"+object_id+"/config"
    mqttc.publish(topic, json.dumps(payload), retain=True)
    addon.log.debug(f"Published HA config {topic}: {json.dumps(payload)}")


def homa_remove():
    """Remove HomA messages from MQTT broker."""
    addon.log.info(f"Removing HomA / Home Assistant data (systemId {systemId}) ...")
    mqttc.publish(get_topic("meta/room"), "", retain=True)
    mqttc.publish(get_topic("meta/name"), "", retain=True)
    for mqtt_item in mqtt_arr:
        mqttc.publish(get_topic("controls", mqtt_item['topic'], "meta/type"), "", retain=True)
        mqttc.publish(get_topic("controls", mqtt_item['topic'], "meta/order"), "", retain=True)
        mqttc.publish(get_topic("controls", mqtt_item['topic'], "meta/unit"), "", retain=True)
        mqttc.publish(get_topic("controls", mqtt_item['topic'], "meta/room"), "", retain=True)
        mqttc.publish(get_topic("controls", mqtt_item['topic']), "", retain=True)
        object_id = systemId+"-"+mqtt_item['topic'].replace(" ", "-")
        mqttc.publish("homeassistant/sensor/"+object_id+"/config", "", retain=True)


def on_connect(client, userdata, flags, reason_code, properties):  # pylint: disable=unused-argument
    """The callback for when the client receives a CONNACK response from the broker."""
    addon.log.debug("on_connect(): Connected with result code %s", str(reason_code))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(get_topic("controls", T_VOLUME))


def on_message(client, userdata, msg):  # pylint: disable=unused-argument
    """The callback for when a PUBLISH message is received from the broker."""
    payload_str = msg.payload.decode("utf-8")  # payload is bytes since API version 2
    addon.log.debug("on_message(): "+ msg.topic+ ": "+ payload_str)
    if msg.topic == get_topic("controls", T_VOLUME):
        new_gas_counter = round(float(payload_str) / RESOLUTION)
        if abs(gas_meter_count.gas_counter - new_gas_counter) > 0:
            addon.log.warning(f"Setting new gas_counter: {new_gas_counter} which differs from current ({gas_meter_count.gas_counter})")
            gas_meter_count.gas_counter = new_gas_counter


def on_publish(client, userdata, mid, reason_code, properties):  # pylint: disable=unused-argument
    """The callback for when a message is published to the broker."""
    # addon.log.debug("on_publish(): message send %s", str(mid))


def gas_meter_count(ts_ms: int):
    """
    Count gas meter pulse and send to MQTT broker.
    ts: timestamp in ms
    """

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    gas_meter_count.gas_counter += 1
    volume = round(gas_meter_count.gas_counter * RESOLUTION, 3)  # do limit precision 3 digits after dot
    energy = round(volume * calorific_value, 3)  # do limit precision 3 digits after dot
    if gas_meter_count.ts_last_ms == 0:
        rate = 0.0
    else:
        rate = round(RESOLUTION / (ts_ms - gas_meter_count.ts_last_ms) * 1000 * 3600, 3)  # do limit precision 3 digits after dot
    gas_meter_count.ts_last_ms = ts_ms
    mqttc.publish(get_topic("controls", T_VOLUME), volume, retain=True)
    mqttc.publish(get_topic("controls", T_ENERGY), energy, retain=True)
    mqttc.publish(get_topic("controls", T_FLOW_RATE), rate, retain=True)
    mqttc.publish(get_topic("controls", T_TIMESTAMP), timestamp, retain=True)
    addon.log.debug(f"Rising edge detected. gas_counter = {gas_meter_count.gas_counter}, volume = {volume} m³")


def gas_meter_wait():
    """Wait for gas meter pulses and send them to MQTT broker."""
    import gpiod
    from gpiod.line import Direction, Edge, Bias
    from gpiod.edge_event import EdgeEvent

    with gpiod.Chip(GPIO_CHIP) as chip:
        info = chip.get_info()
        addon.log.info(f"{PY_FILE} Using {info.name} [{info.label}] ({info.num_lines} lines)")

    with gpiod.request_lines(
        GPIO_CHIP,
        consumer=PY_FILE,
        config={
            gpio_pin: gpiod.LineSettings(
                direction=Direction.INPUT,
                edge_detection=Edge.RISING,
                debounce_period=timedelta(milliseconds=100),
                bias=Bias.PULL_UP
            )
        },
    ) as request:
        addon.log.info(f"{PY_FILE} Started – waiting for pulses ...")
        while True:
            # blocks until at least one event arrives
            request.wait_edge_events(timeout=5_000)  # 5 sec timeout
            events = request.read_edge_events()
            for event in events:
                # raising edge = impulse
                if event.line_offset == gpio_pin and event.event_type == EdgeEvent.Type.RISING_EDGE:
                    # debounce
                    ts_ms = event.timestamp_ns // 1_000_000
                    if ts_ms - gas_meter_wait.ts_last_ms < DEBOUNCE_MS:
                        addon.log.debug(f"Debounce: Ignored pulse on line {event.line_offset} at {ts_ms} ms, last at {gas_meter_wait.ts_last_ms} ms")
                        gas_meter_wait.ts_last_ms = ts_ms
                        continue
                    gas_meter_count(ts_ms)
                    gas_meter_wait.ts_last_ms = ts_ms
                else:
                    addon.log.error(f"Unexpected event type {event.event_type} on line {event.line_offset}, expected {EdgeEvent.Type.RISING_EDGE} on {gpio_pin}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Gas meter module publishing to HomA MQTT framework and Home Assistant.",
                                     epilog="Example: gas_meter.py -d --brokerHost my-mqtt --brokerPort 8883")
    parser.add_argument('-d', action='store_true', help='Enable debug output')
    parser.add_argument('-r', action='store_true', help='Remove all retained MQTT messages and exit')
    parser.add_argument('--brokerHost', type=str, default=None, help='Set MQTT broker host')
    parser.add_argument('--brokerPort', type=int, default=None, help='Set MQTT broker port')
    return parser.parse_args()


# main program
gas_meter_count.gas_counter = 0  # counter of gas amount [ticks per RESOLUTION]
gas_meter_count.ts_last_ms = 0  # time of last pulse send to broker [ms]
gas_meter_wait.ts_last_ms = 0  # time of last debounced pulse [ms]
args = parse_args()
if args.d:
    debug = True
if debug:
    addon.log.setLevel(addon.DEBUG)
    addon.log.info("Debug output enabled.")
if args.brokerHost is not None:
    addon.log.debug("set config.host = %s", args.brokerHost)
    addon.mqtt_host = args.brokerHost
if args.brokerPort is not None:
    addon.log.debug("set config.port = %s", args.brokerPort)
    addon.mqtt_port = args.brokerPort

# connect to MQTT broker
mqttc = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message
mqttc.on_publish = on_publish
if addon.mqtt_ca_certs != "":
    #mqttc.tls_insecure_set(True) # Do not use this "True" in production!
    mqttc.tls_set(addon.mqtt_ca_certs, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
mqttc.username_pw_set(addon.mqtt_user, password=addon.mqtt_pwd)
mqttc.connect(addon.mqtt_host, port=addon.mqtt_port)
mqttc.loop_start()
time.sleep(1)  # wait for connection setup

if args.r:
    homa_remove()  # remove HomA MQTT device and control settings
else:
    homa_init()  # setup MQTT device and control settings
    gas_meter_wait()  # wait for gas meter pulses (blocking)

# configure GPIO
# GPIO.setmode(GPIO.BCM)
# GPIO.setup(gpio_pin, GPIO.IN)

# # Wait for signal rise on pin. Make it interrupt driven ...
# # http://raspi.tv/2013/how-to-use-interrupts-with-python-on-the-raspberry-pi-and-rpi-gpio
# while True:
#     try:
#         # without timeout [ms] ^C does not interrupt GPIO.wait_for_edge()!
#         while GPIO.wait_for_edge(gpio_pin, GPIO.RISING, timeout=2000) is not None:
#             millis = int(round(time.time() * 1000))
#             # debounce and check for HIGH
#             time.sleep(0.05) # [s]
#             if GPIO.input(gpio_pin) == GPIO.LOW:
#                 addon.log.debug("ERROR: Input pin is LOW after a RISING edge!")
#                 break
#             ts_last_ms = gas_meter_count(millis)
#             time.sleep(1) # debounce timer [s]
#     except (KeyboardInterrupt, SystemExit):
#         addon.log.info('\nKeyboardInterrupt. Stopping program.')
#         GPIO.cleanup() # clean up GPIO on CTRL+C exit
#         break

# wait until all queued topics are published
mqttc.loop_stop()
mqttc.disconnect()
