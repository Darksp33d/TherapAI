import requests
import json
import ssl


HEROKU_APP_URL = "https://therapai-4bfe081d185e.herokuapp.com/record_and_process"

def test_app():

    with open('recording.wav', 'rb') as audio_file:
        payload = {
            'device_index': 1  
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