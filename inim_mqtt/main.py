#!/usr/bin/env python3
"""This stupid webapp catches the latest podcast from ilpost.it ."""
import myconst
import os
import time
import logging
import log

logger = log.setup_custom_logger("root")
logger.info("Loaded Logger configuration")
import sys
import redis
import orjson, json
import asyncio
import aiohttp
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from typing import Union
from fastapi import FastAPI, status, Response, Request
from fastapi.responses import PlainTextResponse, ORJSONResponse, HTMLResponse
import inim
import client as mq
from datetime import datetime as dt
from ha_mqtt_discoverable import Settings, DeviceInfo
from ha_mqtt_discoverable.sensors import BinarySensor, BinarySensorInfo


# Load Environment Variables from file

load_dotenv()
time.tzset()

binary_sensors_cache = {}
binary_sensors_states_cache = {}

areas_cache = {}
area_states_cache = {}
# # Set the user agnet to something credible.


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(main())
    yield


# Initialize FastAPI
app = FastAPI(lifespan=lifespan)


@app.get("/ping", response_class=PlainTextResponse, status_code=200)
async def ping():
    """Pong"""
    return "pong"


def main():
    """Main function"""
    # Declare array binary_sensors

    # Create a inimCentral object.
    logger.warning(f"Connecting to redis at {myconst.REDIS_HOST}:{myconst.REDIS_PORT}")
    myredis = redis.Redis(
        host=myconst.REDIS_HOST,
        port=myconst.REDIS_PORT,
        db=myconst.REDIS_DB,
        socket_timeout=1,
    )

    # Create a new mqtt client instance
    mymqtt = mq.mqttLink(
        mqtt_host=myconst.MQTT_HOST,
        mqtt_port=myconst.MQTT_PORT,
        mqtt_user=myconst.MQTT_USER,
        mqtt_pass=myconst.MQTT_PASS,
        mqtt_topic=myconst.MQTT_TOPIC,
        mqtt_keepalive=myconst.MQTT_KEEPALIVE,
        mqtt_qos=myconst.MQTT_QOS,
    )

    # Start the mqtt client
    mqtt_client = mymqtt.start()

    myinim = inim.central(
        redis=myredis,
        username=myconst.EMAIL,
        password=myconst.PASSWORD,
        pin=myconst.PIN,
        client_id=myconst.CLIENTID,
        client_name=myconst.CLIENTNAME,
        device_id=myconst.DEVICEID,
    )

    # Mqtt Settings for ha_mqtt_discoverable library
    mqtt_settings = Settings.MQTT(
        host=myconst.MQTT_HOST,
        port=myconst.MQTT_PORT,
        username=myconst.MQTT_USER,
        password=myconst.MQTT_PASS,
        keepalive=myconst.MQTT_KEEPALIVE,
        qos=myconst.MQTT_QOS,
    )
    # TODO If multiple centrals we need to iterate. and create an object each.

    device = json.loads(myinim.GetDevices())["Data"][0]

    myinim_device_info = DeviceInfo(
        identifiers=[f"inim_{device['Id']}"],
        name=f"inim_{device['Id']}",
        model=f"{device['ModelFamily']}-{device['ModelNumber']}",
        serial_number=device["SerialNumber"],
        manufacturer="Inim Electronics",
        sw_version=f"{device['FirmwareVersionMajor']}.{device['FirmwareVersionMinor']}",
        configuration_url="https://my.inimcloud.com/login",
    )
    while True:
        process_sensors(
            myinim=myinim, device_info=myinim_device_info, mqtt_settings=mqtt_settings
        )
        process_areas(
            myinim=myinim, device_info=myinim_device_info, mqtt_settings=mqtt_settings
        )
        time.sleep(5)


def get_sensor_group(sensor_name):

    # TODO Spostare logica nelle variabili esterne
    binary_sensors_types = {
        "door": ["porta", "cancello", "door", "gate"],
        "window": ["fin", "finestra", "windows", "lucernario"],
        "presence": ["vol", "volumetric"],
    }
    sensor_name = (
        sensor_name.lower()
    )  # Convert to lowercase for case-insensitive matching

    for group_name, keywords in binary_sensors_types.items():
        for keyword in keywords:
            if keyword in sensor_name:
                return group_name

    return None  # No match found


def process_areas(myinim, device_info, mqtt_settings):
    areas = json.loads(myinim.GetDeviceAreas())
    zones = areas["Data"]

    for zone in zones:
        zone_id = zone["Id"]
        zone_tamper = zone["Tamper"]
        if not zone_id in areas_cache:
            zone_armed = zone["Armed"]
            zone_armed = zone["Armed"]
            zone_unique_id = f"{device_info.name}_zone_armed_{zone_id}"
            zone_alarm = zone["Alarm"]
            zone_alarmemory = zone["AlarmMemory"]

            zone_tampermemory = zone["TamperMemory"]
            zone_icon = None

            zone_class = "lock"
            zone_name = f'Zone {zone["Name"]} Armed'

            zone_info = BinarySensorInfo(
                name=zone_name,
                icon=zone_icon,
                device_class=zone_class,
                unique_id=zone_unique_id,
                device=device_info,
            )

            binary_settings = Settings(mqtt=mqtt_settings, entity=zone_info)

            # Instantiate the sensor
            binary_sensor = BinarySensor(binary_settings)
            # Start the sensor
            binary_sensor.set_attributes(zone)

            # Change the state of the sensor, publishing an MQTT message that gets picked up by HA
            if int(zone_armed) == 1:
                binary_sensor.off()
            else:
                binary_sensor.on()

            zone_class = "tamper"
            zone_name = f'Zone {zone["Name"]} Tamper'
            zone_unique_id = f"{device_info.name}_zone_tamper_{zone_id}"
            zone_info = BinarySensorInfo(
                name=zone_name,
                icon=zone_icon,
                device_class=zone_class,
                unique_id=zone_unique_id,
                device=device_info,
            )

            binary_settings = Settings(mqtt=mqtt_settings, entity=zone_info)

            areas_cache[zone_id] = BinarySensor(binary_settings)
            # Start the sensor
            areas_cache[zone_id].set_attributes(zone)
            area_states_cache.update({zone_id: "off"})
            logger.debug(f"Added {zone_name} to binary_sensors")

            # # Instantiate the sensor
            # binary_sensor = BinarySensor(binary_settings)
            # # Start the sensor
            # binary_sensor.set_attributes(zone)

        # Change the state of the sensor, publishing an MQTT message that gets picked up by HA
        logger.debug(areas_cache[zone_id])
        if int(zone_tamper) != 0:
            if area_states_cache[zone_id] == "off":
                areas_cache[zone_id].on()
                area_states_cache.update({zone_id: "on"})
        else:
            if area_states_cache[zone_id] == "on":
                areas_cache[zone_id].off()
                area_states_cache.update({zone_id: "off"})


def process_sensors(myinim, device_info, mqtt_settings):
    deviceZones = json.loads(myinim.GetDeviceZones())
    sensors = deviceZones["Data"]

    for sensor in sensors:
        sensor_status = int(sensor["Status"])
        sensor_id = sensor["Id"]
        # Check if value exist in array binary_sensors:
        # if sensor_id in binary_sensors:
        if not sensor_id in binary_sensors_cache:
            sensor_name = sensor["Name"]
            sensor_type = sensor["Type"]
            sensor_icon = None
            sensor_class = "unknown"
            if sensor_type == 1:
                sensor_class = "tamper"
                sensor_icon = "mdi:blinds-horizontal-closed"
            elif sensor_type == 2:
                sensor_class = get_sensor_group(sensor_name)
                if sensor_class is None:
                    sensor_class = "unknown"
                logger.info(f"Sensor group: {sensor_name} {sensor_class}")
            elif sensor_type == 8:
                sensor_class = "lock"
            elif sensor_type == 4:
                sensor_class = "sound"

            sensor_areas = sensor["Areas"]
            sensor_disabled = bool(sensor["Bypassed"])
            # https://www.home-assistant.io/integrations/binary_sensor/#device-class
            sensor_unique_id = f"{device_info.name}_alarm_sensor_{sensor_id}"
            sensor_info = BinarySensorInfo(
                name=sensor_name,
                icon=sensor_icon,
                device_class=sensor_class,
                unique_id=sensor_unique_id,
                device=device_info,
            )

            binary_settings = Settings(mqtt=mqtt_settings, entity=sensor_info)

            # Instantiate the sensor

            binary_sensors_cache[sensor_id] = BinarySensor(binary_settings)
            # Start the sensor
            binary_sensors_cache[sensor_id].set_attributes(sensor)
            binary_sensors_states_cache.update({sensor_id: "off"})
            logger.debug(f"Added {sensor} to binary_sensors")

        logger.debug(binary_sensors_cache[sensor_id])
        if sensor_status == 2:
            if binary_sensors_states_cache[sensor_id] == "off":
                binary_sensors_cache[sensor_id].on()
                binary_sensors_states_cache.update({sensor_id: "on"})
        else:
            if binary_sensors_states_cache[sensor_id] == "on":
                binary_sensors_cache[sensor_id].off()
                binary_sensors_states_cache.update({sensor_id: "off"})


if __name__ == "__main__":
    main()
