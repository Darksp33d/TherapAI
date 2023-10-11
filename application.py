from flask import Flask, request, jsonify
import openai
import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from flask_migrate import Migrate
import datetime
import logging

logging.basicConfig(level=logging.INFO)


app = Flask(__name__)
app.config['DEBUG'] = True

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not provided.")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db = SQLAlchemy(app)
migrate = Migrate(app, db)

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

class Journal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.String(2000), nullable=False)
    date = db.Column(db.Date, default=datetime.date.today)

class JournalDate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)

# Set up OpenAI API
openai.api_key = os.environ.get('OPENAI_API_KEY')
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable not provided.")

@app.route('/add_journal_entry', methods=['POST'])
def add_journal_entry():
    try:
        user_id = request.form['user_id']
        content = request.form['content']

        # Log request details
        logging.info(f"Received add journal request. User ID: {user_id}. Content: {content}")

        journal_entry = Journal(user_id=user_id, content=content)
        db.session.add(journal_entry)
        db.session.commit()

        return jsonify(success=True)

    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"SQLAlchemy Error while adding journal entry: {str(e)}")
        return jsonify(error="Database error."), 500

    except Exception as e:
        logging.error(f"General Error while adding journal entry: {str(e)}")
        return jsonify(error="Something went wrong."), 500

@app.route('/get_journal_entries', methods=['GET'])
def get_journal_entries():
    try:
        user_id = request.args.get('user_id')

        # Log request details
        logging.info(f"Received get journal entries request. User ID: {user_id}")

        entries = Journal.query.filter_by(user_id=user_id).all()
        result = [{"date": entry.date.strftime("%Y-%m-%d"), "content": entry.content} for entry in entries]
        return jsonify(result)

    except SQLAlchemyError as e:
        logging.error(f"SQLAlchemy Error while fetching journal entries: {str(e)}")
        return jsonify(error="Database error."), 500

    except Exception as e:
        logging.error(f"General Error while fetching journal entries: {str(e)}")
        return jsonify(error="Something went wrong."), 500

@app.route('/process_text', methods=['POST'])
def process_text():
    try:
        uuid_hash = int(request.form['user_id'])
        user_text = request.form['text']

        user = User.query.filter_by(uuid_hash=uuid_hash).first()
        if not user:
            user = User(uuid_hash=uuid_hash)
            db.session.add(user)
            db.session.commit()

        response_text = get_gpt_response(user, user_text)

        existing_messages = ChatHistory.query.filter_by(user_id=user.id).order_by(ChatHistory.id).all()

        if len(existing_messages) >= 25:
            db.session.delete(existing_messages[0])

        gpt_response_entry = ChatHistory(role='assistant', content=response_text, user_id=user.id)
        db.session.add(gpt_response_entry)
        user_message_entry = ChatHistory(role='user', content=user_text, user_id=user.id)
        db.session.add(user_message_entry)

        db.session.commit()

        return jsonify({'response': response_text})

    except SQLAlchemyError as e:
        db.session.rollback()
        print("SQLAlchemy Error:", str(e))
        return jsonify(error="Database error."), 500

    except Exception as e:
        print("General Error:", str(e))
        return jsonify(error="Something went wrong."), 500

def get_gpt_response(user, input_text):
    messages = [{"role": chat.role, "content": chat.content} for chat in user.chat_histories]

    therapist_instruction = ("Behave as a human therapist. Keep in mind")

    # Check if there's a name in the input_text
    split_text = input_text.split(". ", 1)
    if len(split_text) == 2:
        name_text, actual_text = split_text
    else:
        name_text = "My name hasn't been provided"
        actual_text = split_text[0]

    user_message = (f"{therapist_instruction} {name_text}. "
                    f" Rarely use my name in your messages. Be very friendly. "
                    f"Here is my message to you: '{actual_text}'")

    messages.append({
        "role": "user",
        "content": user_message
    })

    response = openai.ChatCompletion.create(model="gpt-4", messages=messages, max_tokens=150, temperature=0.4)

    response_text = response.choices[0].message['content'].strip()

    # Check for undesired phrases
    undesired_phrases = ["I'm really sorry that you're feeling this way", "I'm unable to provide the help"]
    for phrase in undesired_phrases:
        if phrase in response_text:
            response_text = "Let's try discussing this in a different way. Please provide more information or rephrase your concern."

    return response_text

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
