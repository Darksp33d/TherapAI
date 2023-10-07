import requests

# Replace this URL with the one Elastic Beanstalk gave you for your deployment
YOUR_ELASTIC_BEANSTALK_URL = 'http://durranico.us-east-1.elasticbeanstalk.com/'

def test_record_and_process_endpoint():
    # Using the first device index as an example. Modify this if needed.
    payload = {
        'device_index': 0
    }
    
    response = requests.post(f"{YOUR_ELASTIC_BEANSTALK_URL}/record_and_process", json=payload)
    
    if response.status_code == 200:
        print("Response received!")
        data = response.json()
        print("Text recognized:", data.get('text'))
        print("GPT-4 response:", data.get('response'))
    else:
        print(f"Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    test_record_and_process_endpoint()
