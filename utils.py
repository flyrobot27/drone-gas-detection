import redis
from decouple import config
from enum import Enum
from typing import Tuple
from typing_extensions import Self

class SensorReadingFieldNames(str, Enum):
    """
    Enum class for sensor reading field names
    """

    GAS_SENSOR_VOLTAGE = "GAS_VOLTAGE"
    GAS_PPM = "GAS_PPM"
    GAS_SENSOR_VALUE = "GAS_VALUE"
    TEMPERATURE = "TEMP"
    HUMIDITY = "HUMIDITY"

    @staticmethod
    def get_all_field_names() -> Tuple[Self]:
        """Static method for getting all the field names. Returns a tuple of SensorReadingFieldNames


        Returns:
            Tuple[Self]: iterable of field names in SensorReadingFieldNames
        """
        return tuple(SensorReadingFieldNames)


def connect_redis(password: str) -> redis.Redis:
    """
    Connect to redis.

    Args:
        password (str): password of redis server
    
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
        print("Connected to redis server")
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
    return value is None or value.isspace()
