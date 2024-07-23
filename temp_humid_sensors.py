import time
import board
import adafruit_dht
from utils import connect_redis, print_if_debug, SensorReadingFieldNames
import argparse
from decouple import config

DEBUG = False

def init_sensor(pin: board.pin = board.D4) -> adafruit_dht.DHT11:
    """Initialize the DHT11 sensor

    Args:
        pin (board.pin, optional): physical out pin connection location. Defaults to board.D4.

    Returns:
        adafruit_dht.DHT11: the DHT11 sensor object
    """
    dhtDevice = adafruit_dht.DHT11(pin)
    return dhtDevice


def main():
    parser = argparse.ArgumentParser(description='Read temperature and humidity sensor data and send it to redis')

    parser.add_argument('-p', '--password', 
                    type=str, 
                    help='Redis password. Default to REDIS_PASSWORD env variable', 
                    default=config('REDIS_PASSWORD', default=''))
    parser.add_argument('-r', '--refresh-rate',
                        type=float,
                        help='Refresh rate in seconds. Default to 2.0. Cannot be lower than 2.0',
                        default=2.0)

    parser.add_argument('-d', '--debug',
                        action='store_true',
                        help='Enable debug mode')
    
    args = parser.parse_args()

    # check if args.refresh_rate is lower than 2.0
    if args.refresh_rate - 2.0 < 0.0001:
        parser.error("Refresh rate cannot be lower than 2.0")    

    global DEBUG
    DEBUG = args.debug
   
    r = connect_redis(args.password, DEBUG)
    sensor = init_sensor()

    temperature = float('nan')
    humidity = float('nan')

    while True:
        try:
            temperature = sensor.temperature
            humidity = sensor.humidity
            r.set(SensorReadingFieldNames.TEMPERATURE, temperature)
            r.set(SensorReadingFieldNames.HUMIDITY, humidity)
            print_if_debug("Set Temperature and Humidity to redis", DEBUG)
        except RuntimeError as error:
            print(error.args[0])
            continue
        except Exception as error:
            sensor.exit()
            raise error

        time.sleep(args.refresh_rate)

