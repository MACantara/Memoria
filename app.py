from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
import os
import json
from google import genai
from models import db, Topic, Flashcard
from datetime import datetime

load_dotenv()
api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flashcards.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route("/", methods=["GET"])
def index():
    topics = Topic.query.order_by(Topic.created_at.desc()).all()
    return render_template("index.html", topics=topics)

@app.route("/generate", methods=["POST"])
def generate():
    user_input = request.form["topic"]
    
    # Check if topic exists
    topic = Topic.query.filter_by(name=user_input).first()
    if not topic:
        topic = Topic(name=user_input)
        db.session.add(topic)
        db.session.commit()

    client = genai.Client(api_key=api_key)
    prompt = f"""Generate 5 unique flashcards about {user_input}. 
    For each flashcard provide:
    1. A question
    2. The correct answer
    3. Three incorrect but plausible answers
    Format each flashcard as: question: [the question] correct: [correct answer] incorrect: [wrong answer 1]; [wrong answer 2]; [wrong answer 3]"""

    response = client.models.generate_content(
        model="gemini-2.0-flash-lite-preview-02-05", contents=prompt
    )

    for card in parse_flashcards(response.text):
        flashcard = Flashcard(
            question=card['question'],
            correct_answer=card['correct_answer'],
            incorrect_answers=json.dumps(card['incorrect_answers']),
            topic_id=topic.id
        )
        db.session.add(flashcard)
    
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "redirect_url": url_for('get_topic_flashcards', topic_id=topic.id)})
    return redirect(url_for('get_topic_flashcards', topic_id=topic.id))

@app.route("/topic/<int:topic_id>")
def get_topic_flashcards(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    flashcards = Flashcard.query.filter_by(topic_id=topic_id).all()
    return render_template("flashcards.html", topic=topic, flashcards=flashcards)

@app.route("/update_progress", methods=["POST"])
def update_progress():
    data = request.json
    flashcard = Flashcard.query.get_or_404(data['flashcard_id'])
    
    if data['is_correct']:
        flashcard.correct_count += 1
    else:
        flashcard.incorrect_count += 1
    
    flashcard.last_reviewed = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True})

def parse_flashcards(text):
    flashcards = []
    flashcard_responses = text.split("question:")

    for card_response in flashcard_responses[1:]:  # Skip first empty split
        try:
            question_start = 0
            correct_start = card_response.lower().index("correct:") + len("correct:")
            incorrect_start = card_response.lower().index("incorrect:") + len("incorrect:")
            
            question = card_response[question_start:correct_start].replace("correct:", "").strip()
            correct_answer = card_response[correct_start:incorrect_start].replace("incorrect:", "").strip()
            incorrect_answers = [
                ans.strip().split('**')[0].strip() # Remove any **text** markers
                for ans in card_response[incorrect_start:].split(";")
                if ans.strip()
            ]

            # Clean up any remaining markdown or extra text
            question = question.replace('*', '').strip()
            correct_answer = correct_answer.replace('*', '').strip()
            
            if len(incorrect_answers) >= 3:  # Ensure we have enough wrong answers
                flashcards.append({
                    "question": question,
                    "correct_answer": correct_answer,
                    "incorrect_answers": incorrect_answers[:3],  # Take only first 3 wrong answers
                })
        except ValueError as e:
            print(f"Error parsing flashcard: {e}")
            continue

    return flashcards

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", debug=True)