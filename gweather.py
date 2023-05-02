import sys, requests, time, logging, os
from threading import Thread
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s|[%(levelname)s]|%(message)s",
    handlers=[
        logging.FileHandler("gweather.log"),
        logging.StreamHandler(sys.stdout)
    ]
)


bucket = "gweather"
client = InfluxDBClient(
    url="https://eu-central-1-1.aws.cloud2.influxdata.com",
    token=os.environ.get("INFLUXDB_TOKEN"),
    org=os.environ.get("INFLUX_ORG"),
)
write_api = client.write_api(write_options=SYNCHRONOUS)


def write_point(measurement, tagname, tagvalue, field, value):
    p = (
        Point(measurement)
        .tag(tagname, tagvalue)
        .field(field, value)
    )
    try:
        write_api.write(bucket=bucket, record=p)
    except:
        logging.error('Error writing data to influxDB')


netatmo_access_token= ''
netatmo_refresh_token= ''
netatmo_refresh_url = 'https://api.netatmo.com/oauth2/token'
netatmo_data_url = 'https://api.netatmo.com/api/getstationsdata?device_id=70:ee:50:04:cc:74&get_favorites=false'

def init_netatmo():
    global netatmo_access_token, netatmo_refresh_token, netatmo_refresh_url
    auth_params = {
        'grant_type': 'password',
        'client_id': os.environ.get("NETATMO_CLIENT_ID"),
        'client_secret': os.environ.get("NETATMO_CLIENT_SECRET"),
        'username': os.environ.get("NETATMO_USERNAME"),
        'password': os.environ.get("NETATMO_PASSWORD"),
        'scope': 'read_station'
    }
    response = requests.post(netatmo_refresh_url, data=auth_params)
    logging.info(response.json())
    netatmo_access_token = response.json()['access_token']
    logging.info('access token:' + netatmo_access_token)
    netatmo_refresh_token = response.json()['refresh_token']
    logging.info('refresh token:' + netatmo_refresh_token)


def refresh():
    global netatmo_access_token, netatmo_refresh_token, netatmo_refresh_url
    while True:
        try:
            auth = (os.environ.get("NETATMO_CLIENT_ID"), os.environ.get("NETATMO_CLIENT_SECRET"))
            params = {
                "grant_type": "refresh_token",
                "refresh_token": netatmo_refresh_token
            }
            response = requests.post(netatmo_refresh_url, auth=auth, data=params)
            logging.info(response.json())
            netatmo_access_token = response.json()['access_token']
            logging.info('access token:' + netatmo_access_token)
            netatmo_refresh_token = response.json()['refresh_token']
            logging.info('refresh token:' + netatmo_refresh_token)
        except:
            logging.error('something went wrong when refreshing token')
        time.sleep(10000)


init_netatmo()
refresh_thread = Thread(target=refresh, args=())
refresh_thread.start()

while True:
    time.sleep(1 * 60)
    try:
        response = requests.get(netatmo_data_url, headers={'Authorization': 'Bearer ' + netatmo_access_token})
        temperature = response.json()['body']['devices'][0]['modules'][1]['dashboard_data']['Temperature']
        logging.info(temperature)
        write_point('outside', 'temperature', 'celsius', 'carport temperature', temperature)
    except:
        logging.error('something went wrong when getting and writing temperature')
    time.sleep(11 * 60)

