from pymavlink import mavutil
import redis
from decouple import config
import argparse
from time import sleep, time
from utils import connect_redis, convert_to_float_or_default, is_none_or_whitespace, SensorReadingFieldNames
from typing import Dict, Tuple

class SensorMavlinkConnection:
    """
    Class to send sensor reading to drone via mavlink
    """

    """
    Component id of the sensor. Auto increment
    """
    __component_id = 10

    def __init__(self, sensor_name: SensorReadingFieldNames, host: str, port: int, fc_sysid: int) -> None:
        """
        Initialize sensor mavlink connection

        Args:
            sensor_name (SensorReadingFieldNames): name of the sensor
            host (str): hostname of the mavlink router
            port (int): port number of the mavlink router
            fc_sysid (int): flight controller system id
        """
        self.sensor_name = sensor_name
        self.encoded_name = self.sensor_name.encode('ascii').ljust(10, b'\0')
        self.mavsender: mavutil.mavfile = mavutil.mavlink_connection(f'tcp:{host}:{port}', source_system=fc_sysid, source_component=SensorMavlinkConnection.__component_id)
        SensorMavlinkConnection.__component_id += 1


    def send(self, value: float) -> None:
        """
        Send sensor reading to drone

        Args:
            value (float): sensor reading value
        """
        time_boot_ms = int((time() - self.mavsender.start_time) * 1000)
        self.mavsender.mav.named_value_float_send(time_boot_ms, self.encoded_name, value)
        print(f"Sent {self.sensor_name} to drone: {value}")
    

def read_and_send(r: redis.Redis, port: int, fc_sysid: int, refresh_second: float = 1) -> None:
    """Read gas sensor data from redis and send it to the drone

    Args:
        r (redis.Redis): redis connection to db.
        port (int): port number of mavlink broadcast.
        fc_sysid (int): flight controller system id.
        refresh_second (float, optional): Refresh rate in seconds. Defaults to 1.
    """
    name_enums: Tuple[SensorReadingFieldNames] = SensorReadingFieldNames.get_all_field_names()
    host = config('MAVLINK_ROUTER_HOST', default='127.0.0.1')

    sensor_mavlink: Dict[SensorReadingFieldNames, SensorMavlinkConnection] = dict()

    for n in name_enums:
        if is_none_or_whitespace(n.value):
            print("Gas field name cannot be None or whitespace")
            exit(1)

        mavsender = SensorMavlinkConnection(n.value, host, port, fc_sysid)
        sensor_mavlink[n] = mavsender
    
    while True:
        print("Sending sensor data to drone")
        for n in name_enums:
            # read value from redis
            gas_reading = r.get(n.value)
            print("Got value from redis:", gas_reading)
            # convert gas reading to float
            gas_reading = convert_to_float_or_default(gas_reading, float('nan'))
            # round to 2 decimal places
            gas_reading = round(gas_reading, 2)

            # send gas reading via mavsender
            mavsender = sensor_mavlink[n]
            mavsender.send(gas_reading)
            print(f"Sent {n.value} to drone: {gas_reading}")

        sleep(refresh_second)


def main():
    parser = argparse.ArgumentParser(description='Send gas sensor data to drone via mavlink')
    parser.add_argument('-p', '--password', 
                        type=str, 
                        help='Redis password. Default to REDIS_PASSWORD env variable', 
                        default=config('REDIS_PASSWORD', default=''))
    parser.add_argument('-P', '--port',
                        type=int,
                        help='Mavlink router port. Default to 5760',
                        default=5760)
    parser.add_argument('-f', '--fc-sysid',
                        type=int,
                        help='Flight controller system id. Default to FC_SYSID env variable',
                        default=config('FC_SYSID', default=1))
    parser.add_argument('-r', '--refresh-rate',
                        type=float,
                        help='Refresh rate in seconds. Default to 1',
                        default=1)
    args = parser.parse_args()

    r = connect_redis(args.password)

    # start read and send thread
    print("Starting mavlink thread. Refresh time:", args.refresh_rate)
    read_and_send(r, args.port, args.fc_sysid, args.refresh_rate)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
        exit(0)
    