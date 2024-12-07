from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from . import db
from os import path
import random
import time

# Initialize Blueprint for authentication routes
auth = Blueprint('auth', __name__)

# Login route to authenticate users
@auth.route('/login', methods=['GET', 'POST'])
def login():
    leaderboard = get_high_scores()  # Get leaderboard data

    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')

        # Look up the user in the database
        user = User.query.filter_by(name=name).first()

        if user:
            # Verify password hash
            if check_password_hash(user.password, password):
                flash('Login successful!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))  # Redirect to home page
            else:
                flash('Login failed. Invalid name or password.', category='error')
        else:
            flash('Name does not exist', category='error')

    return render_template("login.html", user=current_user, leaderboard=leaderboard)

# Logout route to log users out
@auth.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    leaderboard = get_high_scores()  # Get leaderboard data
    logout_user()  # Log out the user
    return redirect(url_for('auth.login'))  # Redirect to login page

# Sign up route for new users
@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    leaderboard = get_high_scores()  # Get leaderboard data

    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')

        # Check if the user already exists
        user = User.query.filter_by(name=name).first()
        if user:
            flash('Name already taken', category='error')
        elif len(name) < 2:
            flash('Name must be longer than 2 characters.', category='error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', category='error')
        else:
            # Create new user and hash their password
            new_user = User(name=name, password=generate_password_hash(password, method='pbkdf2:sha256'))
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully!', category='success')

            return redirect(url_for('auth.login'))  # Redirect to login page

    return render_template("sign_up.html", user=current_user, leaderboard=leaderboard)

# Profile route for authenticated users
@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    leaderboard = get_high_scores()  # Get leaderboard data
    if request.method == 'GET':
        flash(f"Personal Best: {get_user_high_score(current_user.name)}", category='message')

    return render_template("profile.html", user=current_user, leaderboard=leaderboard)

# Helper function to load quiz questions from a file
def load_questions(file_path):
    all_questions = []
    
    if path.exists(file_path):
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split('|')
                if len(parts) == 2:  # Ensure valid format
                    question_text = parts[0]
                    correct_answer = parts[1]
                    all_questions.append({
                        "question": question_text,
                        "correct": correct_answer,
                        "answered_correctly": False
                    })
    else:
        print("File doesn't exist")

    # Select 12 random questions if there are at least 12, otherwise return all
    num_questions = min(12, len(all_questions))
    selected_questions = random.sample(all_questions, num_questions)

    return selected_questions

# Quiz route for authenticated users to take the quiz
@auth.route('/quiz', methods=['GET', 'POST'])
@login_required
def quiz():
    file_path = path.join(path.dirname(__file__), "questions.txt")
    if 'questions' not in session:
        session['questions'] = load_questions(file_path)

    questions = session['questions']

    if not questions:
        return "No questions available."

    # Initialize quiz state if not already set
    if 'quiz_state' not in session:
        session['quiz_state'] = {
            'current_index': 0,  # Start from the first question
            'score': 0,
            'failed': 0,
            'high_score': 0,
            'start_time': time.time(),
        }

    state = session['quiz_state']
    current_index = state['current_index']

    if request.method == 'POST':
        selected_answer = request.form.get('answer')
        correct_answer = questions[current_index]['correct']

        # Check if the answer is correct
        if selected_answer == correct_answer:
            state['score'] += 1  # Increase score for correct answer
            questions[current_index]['answered_correctly'] = True
            state['current_index'] = (state['current_index'] + 1) % len(questions)
        else:
            # If answer is wrong, move the question to the end of the list
            state['failed'] += 1
            question_to_move = questions.pop(current_index)
            questions.append(question_to_move)
            flash('Incorrect answer. This question has been moved to the end of the quiz.', 'error')

        session['quiz_state'] = state

    # Check if the quiz is finished
    if all(q['answered_correctly'] for q in questions):
        end_time = time.time()
        time_taken = round(end_time - state['start_time'], 2)
        final_score = state['score']
        state['high_score'] = round(((12 - min(12, state['failed'])) * 100 - (time_taken * 10)), 1)

        # Update high score file
        update_high_score(current_user.name, state['high_score'])

        # Clear session data related to the quiz
        session.pop('quiz_state', None)
        session.pop('questions', None)

        if state['failed'] == 1:
            flash(f"You scored {state['high_score']} with {state['failed']} fault", 'success')
        else:
            flash(f"You scored {state['high_score']} with {state['failed']} faults", 'success')
        return redirect(url_for('views.home'))

    # Get the current question
    current_question = questions[state['current_index']]

    # Dynamically calculate options for this question
    unanswered_correct_answers = [
        q['correct'] for q in questions if not q['answered_correctly']
    ]
    all_options = list(set(unanswered_correct_answers))  # Use only unanswered answers as options
    random.shuffle(all_options)

    current_question['options'] = all_options

    leaderboard = get_high_scores()  # Get leaderboard data
    return render_template(
        "quiz.html",
        user=current_user,
        question=current_question,
        current_index=state['current_index'] + 1,
        total_questions=len(questions),
        leaderboard = leaderboard
    )

# Function to update the user's high score
def update_high_score(username, score):
    file_path = path.join(path.dirname(__file__), "high_score.txt")
    high_scores = {}

    # Load existing high scores
    if path.exists(file_path):
        with open(file_path, 'r') as file:
            for line in file:
                name, high_score = line.strip().split('|')
                high_scores[name] = float(high_score)

    # Update score if necessary
    if username not in high_scores or score > high_scores[username]:
        high_scores[username] = score

    # Write updated high scores back to the file
    with open(file_path, 'w') as file:
        for name, high_score in high_scores.items():
            file.write(f"{name}|{high_score}\n")

# Function to get the leaderboard/high scores from the file
def get_high_scores():
    file_path = path.join(path.dirname(__file__), "high_score.txt")
    high_scores = []

    # Read high scores from the file
    if path.exists(file_path):
        with open(file_path, 'r') as file:
            for line in file:
                name, score = line.strip().split('|')
                high_scores.append((name, float(score)))

    # Sort high scores by score in descending order
    high_scores.sort(key=lambda x: x[1], reverse=True)
    return high_scores

def get_user_high_score(username):
    print(username)
    users = get_high_scores()
    for user in users:
        if user[0] == username:
            return user[1]
        else:
            pass
    return "No Record"
