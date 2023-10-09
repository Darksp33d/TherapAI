from flask import Flask, request, jsonify
import wave
import speech_recognition as sr
import openai
import os

app = Flask(__name__)

# Set up OpenAI API
openai.api_key = os.environ.get('OPENAI_API_KEY')

@app.route('/process_text', methods=['POST'])
def process_text():
    user_text = request.form['text']  # Assume text is sent as form data
    response_text = get_gpt_response(user_text)
    return jsonify({
        'response': response_text
    })

def get_gpt_response(input_text):
    messages = [
        {
            "role": "user",
            "content": f"As a therapist, address '{input_text}' in a human-like, helpful manner. Ask follow-up questions if necessary."

        }
    ]
    response = openai.ChatCompletion.create(model="gpt-4", messages=messages, max_tokens=150, temperature=0.3)
    return response.choices[0].message['content'].strip()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
