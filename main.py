# ver. 0.0.8
import time
import os
import paho.mqtt.client as mqtt
import config.config as config
import config.registers as registers
from pysolarmanv5.pysolarmanv5 import PySolarmanV5
import logging

pid = str(os.getpid())
with open("/tmp/main.pid", "w") as f:
    f.write(pid)

topics = []
debug = 0


def modify_solis(topic, payload):
    new_value = int(payload)
    try:
        logging.info('Connecting to Solis Modbus')
        modbus = PySolarmanV5(
            config.INVERTER_IP, config.INVERTER_SERIAL, port=config.INVERTER_PORT, mb_slave_id=1, verbose=debug)
    except Exception as e:
        logging.error(f'{repr(e)}. Exiting')
        exit(1)
    reg = registers.TOPICS_REGS[topic][0]

    try:
        logging.info(f'Changing register {reg} topic {topic} value to {new_value}')
        modbus.write_holding_register(register_addr=reg, value=int(payload))
        time.sleep(0.3)

    except Exception as e:
        logging.error(f'Could not read or modify register {reg} {repr(e)}')
        logging.info(f'Retrying')
        time.sleep(0.3)
        modbus.write_holding_register(register_addr=reg, value=int(payload))
        logging.info(f'Changing register {reg} topic {topic} value to {new_value}')


def on_connect(client, userdata, flags, rc):
    try:
        logging.debug(f'MQTT connected with result code {rc}')
        client.subscribe(topics)
    except Exception as e:
        logging.error(f'Could not connect to MQTT {repr(e)}')


def on_message(client, userdata, msg):
    try:
        logging.debug(f'Message received [{msg.topic}]: {msg.payload}')
        modify_solis(msg.topic, msg.payload)
    except Exception as e:
        logging.error(f'Error on receive message {repr(e)}')


if __name__ == '__main__':
    try:
        if config.DEBUG:
            logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.DEBUG,
                                datefmt='%Y-%m-%d %H:%M:%S')
            debug = 1
        else:
            logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO,
                                datefmt='%Y-%m-%d %H:%M:%S')
            debug = 0

        logging.info('Starting')

        # Populate topics list from config
        for k in registers.TOPICS_REGS:
            topics.append((k, 0))
        logging.debug(f'Loaded topics {topics}')

        client = mqtt.Client()
        if config.MQTT_USER != '':
            client.username_pw_set(config.MQTT_USER, config.MQTT_PASS)
        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(config.MQTT_SERVER, config.MQTT_PORT)
        client.loop_forever()

    except Exception as e:
        logging.error(f'Cannot start: {repr(e)}')
        exit(1)
