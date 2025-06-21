import os
import base64
import json

from dotenv import load_dotenv
from bs4 import BeautifulSoup
from redis import StrictRedis
from time import strftime, sleep

load_dotenv()

def encode_base64(text):
    try:
        encoded_bytes = base64.b64encode(text.encode('utf-8'))
        return encoded_bytes.decode('utf-8')
    except Exception as e:
        print(f"Error on encode to base64: {e}")
        return None


def decode_base64(encoded_text):
    try:
        decoded_bytes = base64.b64decode(encoded_text)
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        print(f"Error on decode base64: {e}")
        return None


def extract_readable_text(html_content):
    if decoded_content := decode_base64(html_content):
        soup = BeautifulSoup(decoded_content, 'html.parser')

        for tag in soup(['script', 'style', 'head', 'noscript']):
            tag.decompose()

        return soup.get_text(separator=' ', strip=True)

    return None


def subscribe_redis_channel():
    try:
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = os.getenv('REDIS_PORT', '6379')
        redis_pw = os.getenv('REDIS_PW', 'password')
        redis_channels = os.getenv('REDIS_CHANNELS', 'channel_test').split(',')

        client = StrictRedis(host=redis_host, password=redis_pw, port=int(redis_port))
        subscriber = client.pubsub()
        subscriber.psubscribe(*redis_channels)

        while True:
            messages = subscriber.get_message(ignore_subscribe_messages=True, timeout=1.0)
            now = strftime('%Y-%m-%d:%H:%M:%S')

            if messages:
                channel = messages["channel"].decode("utf-8")
                print(f'{now} - {channel}')

                try:
                    data = json.loads(messages["data"].decode("utf-8"))
                    if clean_content := extract_readable_text(data.get('base64Content')):
                        message = {
                            'emailId': data.get('emailId'),
                            'folderId': data.get('folderId'),
                            'base64Content': encode_base64(clean_content)
                        }
                        client.publish(f'{channel}_get_back', json.dumps(message))
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON message: {e}")
                    continue
            sleep(1)
    except Exception as e:
        print(f"Error on connecting Redis: {e}")
        return None


if __name__ == "__main__":
    print('Starting Mdk Mail Cleaner')
    subscribe_redis_channel()
