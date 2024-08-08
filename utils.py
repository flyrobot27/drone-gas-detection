import redis
from decouple import config
from enum import Enum
from typing import Tuple
from typing_extensions import Self
import numpy as np
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

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
        return float(data[s < m].mean())

    
    def reset(self) -> None:
        """ Reset the buffer to nan values """
        self.buffer = np.empty(self.size)
        self.buffer[:] = np.nan
        self.index = 0

class SensorReadingFieldNames(str, Enum):
    """
    Enum class for sensor reading field names
    """

    GAS_SENSOR_VOLTAGE = "GAS_VOLTAGE"
    GAS_PPM = "GAS_PPM"
    GAS_SENSOR_VALUE = "GAS_VALUE"
    GAS_SENSOR_PERCENT = "GAS_PERCENT"
    TEMPERATURE = "TEMP"
    HUMIDITY = "HUMIDITY"

    @staticmethod
    def get_all_field_names() -> Tuple[Self]:
        """Static method for getting all the field names. Returns a tuple of SensorReadingFieldNames


        Returns:
            Tuple[Self]: iterable of field names in SensorReadingFieldNames
        """
        return tuple(SensorReadingFieldNames)

def init_sensor(pin: ADS) -> AnalogIn:
    """Initialize the analog gas sensor

    Args:
        pin (ADS): sensor pin of the plugged in sensor on the ADS1115.

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

def get_temp_sensor_reading(voltage: float) -> float:
    """Get the temperature sensor reading

    Args:
        voltage (float): voltage reading

    Returns:
        float: temperature reading
    """
    return 100 * voltage - 50


def connect_redis(password: str, debug: bool = False) -> redis.Redis:
    """
    Connect to redis.

    Args:
        password (str): password of redis server
        debug (bool, optional): debug flag. Defaults to False.
    
    Returns:
        redis.Redis: redis connection
    """
    host = config("REDIS_HOST", default="127.0.0.1")
    port = config("REDIS_PORT", default=6379, cast=int)
    r = redis.Redis(host=host, port=port, db=0, password=password)
    
    # check redis connectivity
    try:
        r.get("")
    except (redis.exceptions.ConnectionError, 
            redis.exceptions.BusyLoadingError):
        print("Failed to connect to redis server")
        exit(1)
    else:
        print_if_debug("Connected to redis server", debug)
        return r


def is_float(value: str) -> bool:
    """Check if the value is a float

    Args:
        value (str): value to check

    Returns:
        bool: True if value is a float, False otherwise
    """
    try:
        float(value)
        return True
    except ValueError:
        return False


def is_none_or_whitespace(value: str) -> bool:
    """Check if the value is None or whitespace

    Args:
        value (str): value to check

    Returns:
        bool: True if value is None or whitespace, False otherwise
    """
    return value is None or str(value).isspace()

def print_if_debug(message: str, debug: bool) -> None:
    """Print message if debug is True

    Args:
        message (str): message to print
        debug (bool): debug flag
    """
    if debug:
        print(message)

def convert_to_float_or_default(value: str, default: float = float('nan')) -> float:
    """Convert the value to float or return the default value

    Args:
        value (str): value to convert
        default (float, optional): default value if failed to convert. Defaults to float('nan').

    Returns:
        float: converted value
    """
    # check if default is float / whitespace
    if is_none_or_whitespace(default) or not is_float(default):
        raise ValueError("Default value must be a float")

    if is_none_or_whitespace(value) or not is_float(value):
        # use a default failsafe gas reading value
        return default
    else:
        return float(value)
