import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import time
from decouple import config
from utils import connect_redis, SensorReadingFieldNames
import argparse

def init_sensor(pin = ADS.P0) -> AnalogIn:
    """Initialize the analog gas sensor

    Args:
        pin (ADS, optional): sensor pin of the plugged in sensor on the ADS1115. Defaults to ADS.P0.

    Returns:
        AnalogIn: the analog sensor object
    """
    # Initialize the I2C bus
    i2c = busio.I2C(board.SCL, board.SDA)

    # Create the ADC object using the I2C bus
    ads = ADS.ADS1115(i2c)

    # Define the sensor (Analog input)
    sensor = AnalogIn(ads, pin)

    return sensor

def main():
    parser = argparse.ArgumentParser(description='Read analog sensor data and send it to redis')
    parser.add_argument('-p', '--password', 
                        type=str, 
                        help='Redis password. Default to REDIS_PASSWORD env variable', 
                        default=config('REDIS_PASSWORD', default=''))
    parser.add_argument('-r', '--refresh-rate',
                        type=float,
                        help='Refresh rate in seconds. Default to 0.1',
                        default=0.1)

    args = parser.parse_args()
    # connect to redis
    r = connect_redis(args.password)
    sensor = init_sensor()

    while True:
        # TODO Filter and calibrate sensor value
        # currently just send the raw value
        r.set(SensorReadingFieldNames.GAS_SENSOR_VOLTAGE, sensor.voltage)
        r.set(SensorReadingFieldNames.GAS_SENSOR_VALUE, sensor.value)
        print("Set Sensor Voltage and Value to redis")
        time.sleep(args.refresh_rate)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting program")
        exit(0)
    