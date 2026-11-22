#!/usr/bin/env python

from datetime import datetime

import json
import threading

import paho.mqtt.client as mqtt

import IdmPump
import Config

# number of MQTT messages to average before writing to the iDM
SAMPLE_COUNT = 10
# maximum time to wait for the samples (seconds)
SAMPLE_TIMEOUT = 30


def log(msg):
    print(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + " " + msg)


def process_shelly_data(conf):

    samples = []
    complete = threading.Event()

    def on_connect(client, userdata, flags, reason_code, properties):
        client.subscribe(conf["mqtt_topic"])

    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            # Shelly Pro 3EM: total_act_power is in W,
            # negative values mean feed-in to the grid
            samples.append(float(data["total_act_power"]))
            if len(samples) >= SAMPLE_COUNT:
                complete.set()
        except Exception as ex:
            log("ERROR MQTT message: " + str(ex))

    client = None
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.username_pw_set(conf["mqtt_user"], conf["mqtt_password"])
        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(conf["mqtt_broker"], conf.get("mqtt_port", 1883), 60)
        client.loop_start()
        complete.wait(SAMPLE_TIMEOUT)
    except Exception as ex:
        log("ERROR MQTT: " + str(ex))
    finally:
        if client is not None:
            client.loop_stop()
            client.disconnect()

    if not samples:
        log("ERROR: no Shelly values received, iDM not updated")
        return

    grid_power = sum(samples) / len(samples)

    # keep the original threshold logic:
    # export above feed_in_limit is passed to the iDM in kW, otherwise 0
    # iDM does not need fine-grained values: use 100 W (0.1 kW) steps
    if grid_power < -conf["feed_in_limit"]:
        feed_in = round(-grid_power / 1000, 1)
    else:
        feed_in = 0

    # connection iDM: only write if the rounded value actually changed
    current = IdmPump.read(conf["idm_ip"], conf["idm_port"])
    if current is not None and abs(current - feed_in) < 0.05:
        idmval = current
        changed = False
    else:
        idmval = IdmPump.writeandread(conf["idm_ip"], conf["idm_port"], feed_in)
        changed = True

    log_stmt = ("Shelly Pro 3EM: " + str(round(grid_power)) + " W, IDM: "
                + str(idmval) + " kW")
    if not changed:
        log_stmt += " (unchanged)"
    if len(samples) < SAMPLE_COUNT:
        log_stmt += " (n=" + str(len(samples)) + ")"
    log(log_stmt)


if __name__ == "__main__":
    # print(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + " START #####")
    try:
        conf = Config.read()

        # read Shelly and send to iDM
        process_shelly_data(conf)

        # print(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + " END #####")

    except Exception as ex:
        print("ERROR: ", ex)
