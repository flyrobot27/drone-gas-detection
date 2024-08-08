from mq135 import MQ135
from utils import Buffer, init_sensor, get_temp_sensor_reading
import adafruit_ads1x15.ads1115 as ADS
from decouple import config

def main():
    average_size = 20
    gas_sensor = init_sensor(pin=ADS.P0)
    temp_sensor = init_sensor(pin=ADS.P3)
    buffer = Buffer(average_size)
    sensor_max_value = config('SENSOR_MAX_VALUE', default=65536, cast=int)
    mq135 = MQ135(gas_sensor, sensor_max_value)

    for _ in range(average_size):
        temperature = get_temp_sensor_reading(temp_sensor.voltage)
        buffer.add(mq135.get_corrected_rzero(temperature))

    print("Calibration done. Please update the RZERO value in the mq135.py file with the following value:")
    print(buffer.get())
    print("Exiting...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit(0)