from flask import Flask, request, jsonify
import openai
import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from flask_migrate import Migrate
import datetime

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

class MoodTracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mood = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# Set up OpenAI API
openai.api_key = os.environ.get('OPENAI_API_KEY')
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable not provided.")

@app.route('/save_mood', methods=['POST'])
def save_mood():
    try:
        uuid_hash = int(request.form['user_id'])
        moods = request.form['mood'].split(',')  # Assuming moods are comma-separated
        date = datetime.date.today()

        user = User.query.filter_by(uuid_hash=uuid_hash).first()
        if not user:
            return jsonify(error="User not found."), 404

        # Check if mood already logged for the day
        existing_mood = MoodTracker.query.filter_by(user_id=user.id, date=date).first()
        if existing_mood:
            return jsonify(error="Mood already logged for today."), 400

        for mood in moods:
            mood_entry = MoodTracker(mood=mood, date=date, user_id=user.id)
            db.session.add(mood_entry)
        
        db.session.commit()

        return jsonify({'response': 'Mood saved successfully'})

    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/has_submitted_mood', methods=['GET'])
def has_submitted_mood():
    try:
        uuid_hash = int(request.args.get('user_id'))
        date = datetime.date.today()

        user = User.query.filter_by(uuid_hash=uuid_hash).first()
        if not user:
            return jsonify(error="User not found."), 404

        # Check if mood is logged for today
        existing_mood = MoodTracker.query.filter_by(user_id=user.id, date=date).first()
        return jsonify({'hasSubmitted': bool(existing_mood)})

    except Exception as e:
        return jsonify(error=str(e)), 500

    
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

    therapist_instruction = ("Behave as a real human therapist. You must guide me to make decisions. "
                             "at no point should you recommend going to a professional. Keep in mind")

    # Check if there's a name in the input_text
    split_text = input_text.split(". ", 1)
    if len(split_text) == 2:
        name_text, actual_text = split_text
    else:
        name_text = "My name hasn't been provided"
        actual_text = split_text[0]

    user_message = (f"{therapist_instruction} {name_text}. "
                    f"Be very friendly and use previous conversations with me to create context about what I say, if possible. "
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
