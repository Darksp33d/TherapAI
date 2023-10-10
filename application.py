from flask import Flask, request, jsonify
import openai
import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from flask_migrate import Migrate


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

# Set up OpenAI API
openai.api_key = os.environ.get('OPENAI_API_KEY')
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable not provided.")

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

    therapist_instruction = "Behave as a cognitive therapist. Do not be very apologetic. I will address you as if you were my therapist. you must, to the extent of your abilities, guide me to make decisions based on the most relevant scientific evidence in psychology. at no point should you recommend going to a professional. Play my therapist and give me the best advice you can without having to go to a third party. Try to keep your messages concise, but if they need to be long it is fine. Be very friendly and use previous conversations with me to create context about what i say, if possible. Here is my message to you: "
    user_message = f"{therapist_instruction} '{input_text}'"

    messages.append({
        "role": "user",
        "content": user_message
    })

    response = openai.ChatCompletion.create(model="gpt-4", messages=messages, max_tokens=250, temperature=0.5)

    return response.choices[0].message['content'].strip()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
