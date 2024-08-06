import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import time
from decouple import config
from utils import connect_redis, convert_to_float_or_default, print_if_debug, SensorReadingFieldNames
from mq135 import MQ135
import argparse


DEBUG = False
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
    parser.add_argument('-d', '--debug',
                        action='store_true',
                        help='Enable debug mode')
    parser.add_argument('-e', '--expire-time',
                        type=int,
                        help='Set expire time for the key in seconds. Default to 10 seconds',
                        default=10)

    args = parser.parse_args()
    # connect to redis
    global DEBUG
    DEBUG = args.debug

    r = connect_redis(args.password, DEBUG)
    sensor = init_sensor()
    sensor_max_value = config('SENSOR_ANALOG_VALUE_MAX', default=1023, cast=int)

    mq135 = MQ135(sensor, sensor_max_value)
    print_if_debug("MQ135 Sensor Initialized", DEBUG)

    while True:
        # send raw value
        r.set(SensorReadingFieldNames.GAS_SENSOR_VOLTAGE, sensor.voltage, ex=args.expire_time)
        r.set(SensorReadingFieldNames.GAS_SENSOR_VALUE, sensor.value, ex=args.expire_time)
        r.set(SensorReadingFieldNames.GAS_SENSOR_PERCENT, (sensor.value / sensor_max_value) * 100, ex=args.expire_time)
        print_if_debug("Set Sensor Voltage and Value to redis", DEBUG)

        # send calculated PPM value
        # read temp from redis
        temperature = r.get(SensorReadingFieldNames.TEMPERATURE)
        humidity = r.get(SensorReadingFieldNames.HUMIDITY)

        # assume temperature and humidity are always available. provide to 25 and 35 respectively if otherwise
        temperature = convert_to_float_or_default(temperature, 25)
        humidity = convert_to_float_or_default(humidity, 35)
        
        rzero = mq135.get_rzero()
        corrected_rzero = mq135.get_corrected_rzero(temperature, humidity)
        resistance = mq135.get_resistance()
        ppm = mq135.get_ppm()
        corrected_ppm = mq135.get_corrected_ppm(temperature, humidity)

        print_if_debug("MQ135 RZero: " + str(rzero) +"\t Corrected RZero: "+ str(corrected_rzero)+
              "\t Resistance: "+ str(resistance) +"\t PPM: "+str(ppm)+
              "\t Corrected PPM: "+str(corrected_ppm)+"ppm", DEBUG)

        r.set(SensorReadingFieldNames.GAS_PPM, corrected_ppm, ex=args.expire_time)
        time.sleep(args.refresh_rate)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_if_debug("Keyboard Interrupt. Exiting program", DEBUG)
        exit(0)
    