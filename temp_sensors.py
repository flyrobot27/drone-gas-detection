import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from utils import connect_redis, print_if_debug, SensorReadingFieldNames, is_float, is_none_or_whitespace
import argparse
from decouple import config
import numpy as np

DEBUG = False

class Buffer:
    """A circular buffer to store values and get the mean of the buffer without the nan values
    """

    def __init__(self, size: int):
        """Initialize the buffer

        Args:
            size (int): size of the buffer
        """
        self.size = size
        self.buffer = np.empty(size)
        self.buffer[:] = np.nan
        self.index = 0
    
    def add(self, value: float) -> None:
        """Add a value to the buffer

        Args:
            value (float): value to add
        """
        self.buffer[self.index] = value
        self.index = (self.index + 1) % self.size
    
    def get(self, m = 6.0) -> float:
        """Get the mean of the buffer without the nan values and remove outliers

        Args:
            m (float, optional): Outlier cutoff value. Defaults to 6.0.

        Returns:
            float: The mean, or nan if the buffer is empty
        """
        data = self.buffer[~np.isnan(self.buffer)]

        if len(data) == 0:
            return np.nan
        
        d = np.abs(data - np.median(data))
        mdev = np.median(d)
        s = d / (mdev if mdev else 1.)
        return data[s < m].mean()

    
    def reset(self) -> None:
        """ Reset the buffer to nan values """
        self.buffer = np.empty(self.size)
        self.buffer[:] = np.nan
        self.index = 0


def init_sensor(pin = ADS.P3) -> AnalogIn:
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
    parser = argparse.ArgumentParser(description='Read temperature and humidity sensor data and send it to redis')

    parser.add_argument('-p', '--password', 
                    type=str, 
                    help='Redis password. Default to REDIS_PASSWORD env variable', 
                    default=config('REDIS_PASSWORD', default=''))
    parser.add_argument('-r', '--refresh-rate',
                        type=float,
                        help='Refresh rate in seconds. Default to TEMP_REFRESH_RATE env variable or 5.0. Cannot be lower than 5.0',
                        default=config('TEMP_REFRESH_RATE', default=5.0, cast=float))

    parser.add_argument('-d', '--debug',
                        action='store_true',
                        help='Enable debug mode')

    parser.add_argument('-e', '--expire-time',
                        type=int,
                        help='Set expire time for the key in seconds. Default to TEMP_EXPIRE env variable or 10 seconds',
                        default=config('TEMP_EXPIRE', default=10, cast=int))
    
    parser.add_argument('-c', '--cutoff-value', 
                        type=float,
                        help='Outlier cutoff value. Default to TEMP_OUTLIER_CUTOFF env variable or 6.0',
                        default=config('TEMP_OUTLIER_CUTOFF', default=6.0, cast=float))
    
    parser.add_argument('-b', '--buffer-size',
                        type=int,
                        help='Buffer size for the number of readings to consider. Default to TEMP_BUFFER_SIZE env variable or 4',
                        default=config('TEMP_BUFFER_SIZE', default=4, cast=int))

    args = parser.parse_args()

    # check if args.refresh_rate is lower than 5.0
    if args.refresh_rate < 5.0:
        parser.error("Refresh rate cannot be lower than 5.0")    

    global DEBUG
    DEBUG = args.debug
   
    r = connect_redis(args.password, DEBUG)
    sensor = init_sensor()

    temperature = float('nan')
    humidity = float('nan')

    buffer = Buffer(args.buffer_size)

    while True:
        try:
            voltage = sensor.voltage
            temperature = 100 * voltage - 50
            
            print_if_debug("Raw Temperature reading: " + str(temperature), DEBUG)
            print_if_debug("Raw Voltage reading: " + str(voltage), DEBUG)

            if is_none_or_whitespace(temperature) or is_none_or_whitespace(humidity):
                raise RuntimeError("Failed to read temperature or humidity")

            # filter value
            buffer.add(temperature)
            filtered_temperature = buffer.get(m=args.cutoff_value)
            print_if_debug("Filtered Temperature: " + str(filtered_temperature), DEBUG)

            # set the values in redis
            r.set(SensorReadingFieldNames.TEMPERATURE, filtered_temperature, ex=args.expire_time)
            print_if_debug("Set Temperature and Humidity to redis", DEBUG)
        except RuntimeError as error:
            print(error.args[0])
            continue
        except Exception as error:
            buffer.reset()
            raise error

        time.sleep(args.refresh_rate)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
        exit(0)
    except Exception as error:
        print(error)
        exit(1)
