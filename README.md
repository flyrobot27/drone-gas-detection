# Drone Gas Detection

Detecting gas from a drone utilizing the MQ-135 Gas Sensor

## Initial Setup

The wiring of the flight controller / Raspberry Pi / sensors are shown as following:

![Wiring Diagram](<img/drone layout.png>)

We have utilized the following hardware:
 - Matek H743 WLITE Flight Controller
 - Raspberry Pi 5 4GB
 - Flying Fish MQ-135 Gas Sensor with 1K ohm Pullup Resistor
 - TMP235 Analog Temperature Sensor
 - ADS1115 16-bit ADC
 - DAOKI 9 - 36V to 5v 5A Converter
 - Holybro Sik Telemetry Radio V3

Steps:
 - Disable USB max current limit, bluetooth and enable uart in `/boot/config.txt` (or `/boot/firmware/config.txt`)
 - Enable I2C interface in `raspi-config` Under `Advanced Option`
 - Connect ADS1115 to the I2C bus of the Raspberry Pi (SCL / SDA)
 - The ADS1115 can be supplied by Raspberry Pi's 3.3V supply
 - Connect the MQ-135 Analog Out to Pin A0 of ADS1115
 - Connect the TMP235 sensor's Analog Out to Pin A3 of ADS1115
 - Both MQ-135 and TMP235 can be powered by the Pi's 5V output

Next, setup your flight controller and raspberry pi configuration following the steps on Ardupilot Wiki. We are using Mavlink Router:

https://ardupilot.org/dev/docs/raspberry-pi-via-mavlink.html

We are assuming that:
 - The drone is already tuned and raedy to fly
 - All hardware is secure
 - The battery is capable of supplying between 9 - 36 V to the DAOKI Converter. We used a 4S LiPo battery (14.8V 5200mAh)
 - We couldn't source a working Humidity sensor in time. (We have considered the DHT series but couldn't get it to work). Since humidity's effect on the gas sensor is minimal, we assumed a constant humidity of 35

Create a `.env` file that specifies your flight controller Sys Id:
 - `FC_SYSID={your_sysid_integer}`


## Installing dependencies

Create a new Python virtual environment using `virtualenv`.

Install required dependencies using `pip install -r requirements.txt`

## Calibrate MQ-135

The MQ-135 requires calibration in order to function properly. To get the best calibration:
 - Place drone is a controlled enviroment with minimal temperature fluctuation
 - Record CO2 concentration in PPM
 - modify the `.env` file that would contain the following additional variable:
    - `ATMOCO2` to the recorded CO2 PPM
    - `RZERO` to the value returned by the calibration script

## Config REDIS

The Redis database is used to exchange data between different services. Included, there is a `redis.conf` file. Change the `requirepass` parameter to a password of your choice.

Once password is setup, add the `REDIS_PASSWORD` variable to the `.env` file:
 - `REDIS_PASSWORD="password"`


## Run

Install Docker following the official guide (Assuming the Raspberry Pi is running 64bit Raspberry pi OS):

https://docs.docker.com/engine/install/debian/

Once docker is installed, all service can be brought up with 

`docker compose up --build -d`

The raspberry pi will be injecting the gas readings into the flight controller bin log. All readings will be presented as `NVAL`:

`NVAL, 542749458, 1515205, GAS_PPM, 302.75, 213, 11`

You can also connect via the telemetry radio and get the reading using Mission Planner.