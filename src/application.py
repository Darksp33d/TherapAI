from flask import Flask, request, jsonify
import pyaudio
import wave
import speech_recognition as sr
import openai
import os

app = Flask(__name__)

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Set up OpenAI API
openai.api_key = os.environ.get('OPENAI_API_KEY')

@app.route('/record_and_process', methods=['POST'])
def record_and_process():
    # TODO: You'd get the audio file from the iOS app, instead of recording it again.
    # For now, we'll continue with the recording logic as before
    device_index = int(request.json['device_index']) # This assumes you're sending device index from the frontend
    text, response = record_audio(device_index)
    return jsonify({
        'text': text,
        'response': response
    })

def record_audio(device_index):
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024
    OUTPUT_FILENAME = "recording.wav"

    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, input_device_index=device_index, frames_per_buffer=CHUNK)
    frames = []

    for _ in range(0, int(RATE / CHUNK * 10)):
        data = stream.read(CHUNK)
        frames.append(data)

    stream.stop_stream()
    stream.close()

    with wave.open(OUTPUT_FILENAME, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    recognizer = sr.Recognizer()
    with sr.AudioFile(OUTPUT_FILENAME) as source:
        audio_data = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio_data)
            messages = [
                {
                    "role": "user",
                    "content": f"As a therapist, respond in a human-like, helpful and non-judgemental way to: '{text}'"
                }
            ]
            response = openai.ChatCompletion.create(model="gpt-4", messages=messages, max_tokens=150, temperature=0.3)
            gpt_response = response.choices[0].message['content'].strip()
            return text, gpt_response

        except sr.UnknownValueError:
            return "Could not understand the audio.", None
        except sr.RequestError:
            return "API unavailable.", None

if __name__ == "__main__":
    app.run(debug=True)
