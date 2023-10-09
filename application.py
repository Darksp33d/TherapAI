from flask import Flask, request, jsonify
import openai
import os
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db = SQLAlchemy(app)

# Database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_histories = db.relationship('ChatHistory', backref='user')

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), nullable=False)
    content = db.Column(db.String(2000), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Set up OpenAI API
openai.api_key = os.environ.get('OPENAI_API_KEY')

@app.route('/process_text', methods=['POST'])
def process_text():
    user_id = request.form['user_id']
    user_text = request.form['text']

    user = User.query.get(user_id)
    if not user:
        # Create a new user if it doesn't exist
        user = User(id=user_id)
        db.session.add(user)
        db.session.commit()

    response_text = get_gpt_response(user, user_text)

    # Store the GPT response in the database for the user
    gpt_response_entry = ChatHistory(role='assistant', content=response_text, user_id=user.id)
    db.session.add(gpt_response_entry)
    db.session.commit()

    return jsonify({'response': response_text})

def get_gpt_response(user, input_text):
    # Retrieve user's chat history
    messages = [{"role": chat.role, "content": chat.content} for chat in user.chat_histories]
    
    # Add the therapist instruction and the new message from the user
    therapist_instruction = "As a therapist, address the following in a human-like, helpful manner."
    user_message = f"{therapist_instruction} '{input_text}'"

    messages.append({
        "role": "user",
        "content": user_message
    })

    response = openai.ChatCompletion.create(model="gpt-4", messages=messages, max_tokens=150, temperature=0.3)

    return response.choices[0].message['content'].strip()


if __name__ == "__main__":
    db.create_all()  # This will ensure tables are created if they aren't there. Be cautious about using this in production.
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
