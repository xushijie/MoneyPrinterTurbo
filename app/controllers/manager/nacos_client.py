import requests
import time
from loguru import logger
from app.config import config


NACOS_SERVER = config.app.get("nacos_server", 'http://localhost:8848/nacos')
NACOS_GROUP_NAME = config.app.get("nacos_group",  'DEFAULT_GROUP')
SERVICE_NAME = config.project_name
SERVICE_IP = config.listen_host
SERVICE_PORT = config.listen_port
HEARTBEAT_INTERVAL = 2  # Heartbeat interval in seconds


def register():
    url = f"{NACOS_SERVER}/v1/ns/instance"
    params = {
        "serviceName": SERVICE_NAME,
        "ip": SERVICE_IP,
        "port": SERVICE_PORT,
        "groupName": NACOS_GROUP_NAME
    }
    try:
        response = requests.post(url, params=params)
        if response.status_code == 200:
            logger.info("Service registered successfully with Nacos")
        else:
            logger.info(f"Failed to register service with Nacos: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"Error registering service with Nacos: {e}")


def send_heartbeat_to_nacos():
    url = f"{NACOS_SERVER}/v1/ns/instance/beat"
    params = {
        "serviceName": SERVICE_NAME,
        "ip": SERVICE_IP,
        "port": SERVICE_PORT,
        "groupName": NACOS_GROUP_NAME
    }
    while True:
        try:
            response = requests.put(url, params=params)
            if response.status_code == 200:
                print("Heartbeat sent successfully to Nacos")
            else:
                print(f"Failed to send heartbeat to Nacos: {response.status_code} {response.text}")
        except Exception as e:
            print(f"Error sending heartbeat to Nacos: {e}")
        time.sleep(HEARTBEAT_INTERVAL)
