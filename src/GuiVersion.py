import requests
import json
import ssl
from requests.packages.urllib3.util.ssl_ import create_urllib3_context

# Force TLSv1.2
create_urllib3_context(ssl_version=ssl.PROTOCOL_TLSv1_2)

# URL of your Heroku app. Replace this with your app's URL
HEROKU_APP_URL = "https://therapai-4bfe081d185e.herokuapp.com/"

def test_app():
    # Assuming you'll have a 'test_audio.wav' file to test
    with open('recording.wav', 'rb') as audio_file:
        payload = {
            'device_index': 1  # or whichever device index you want to test with
        }
        
        files = {
            'audio_file': audio_file
        }
        
        response = requests.post(HEROKU_APP_URL, data=payload, files=files)
        
        if response.status_code == 200:
            print("Response received:")
            print(json.dumps(response.json(), indent=4))
        else:
            print(f"Failed with status code {response.status_code}:")
            print(response.text)

if __name__ == "__main__":
    test_app()