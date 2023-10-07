from flask import Flask, request, jsonify
import wave
import speech_recognition as sr
import openai
import os

app = Flask(__name__)

# Set up OpenAI API
openai.api_key = os.environ.get('OPENAI_API_KEY')

@app.route('/record_and_process', methods=['POST'])
def record_and_process():
    # Get the audio file from the iOS app
    audio_file = request.files['audio_file']
    audio_file.save("recording.wav")

    text, response = process_audio("recording.wav")
    return jsonify({
        'text': text,
        'response': response
    })

def process_audio(file_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
