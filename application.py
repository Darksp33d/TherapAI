from flask import Flask, request, jsonify
import openai
import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db = SQLAlchemy(app)

# Database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid_hash = db.Column(db.BigInteger, unique=True, nullable=False)
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
    try:
        uuid_hash = int(request.form['user_id'])
        user_text = request.form['text']

        user = User.query.filter_by(uuid_hash=uuid_hash).first()
        if not user:
            # Create a new user if it doesn't exist
            user = User(uuid_hash=uuid_hash)
            db.session.add(user)
            db.session.commit()

        response_text = get_gpt_response(user, user_text)

        # Store the GPT response in the database for the user
        gpt_response_entry = ChatHistory(role='assistant', content=response_text, user_id=user.id)
        db.session.add(gpt_response_entry)
        db.session.commit()

        return jsonify({'response': response_text})

    except exc.SQLAlchemyError as e:   # Catching SQLAlchemy specific exceptions
        return jsonify({'error': 'Database error: ' + str(e)}), 500
    except Exception as e:
        return jsonify({'error': 'An error occurred: ' + str(e)}), 500

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

@app.before_first_request
def initialize_database():
    db.create_all()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
