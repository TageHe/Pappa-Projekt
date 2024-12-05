from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from . import db
from os import path
import random
import time

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')

        user = User.query.filter_by(name = name).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Login successful!', category='success')
                login_user(user, remember = True)
                return redirect(url_for('views.home'))  # Redirect to home page
            else:
                flash('Login failed. Combination of name and password does not exist.', category = 'error')
        else:
            flash('Name does not exist', category = 'error')

    return render_template("login.html", user = current_user)

@auth.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')

        user = User.query.filter_by(name = name).first()
        if user:
            flash('Name already taken', category = 'error')
        elif len(name) < 2:
            flash('Name must be longer than 2 characters.', category='error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', category='error')
        else:
            new_user = User(name = name, password = generate_password_hash(password, method = 'pbkdf2:sha256'))
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully!', category='success')

            return redirect(url_for('auth.login'))  # Redirect to home page


    return render_template("sign_up.html", user = current_user)

@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'GET':
        flash("", category = "message")

    return render_template("profile.html", user = current_user)


# Beneath this is the quiz, shouldn't be here but don'w know where to put it...

import random

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
                        "answered_correctly": False  # Track if this question has been answered correctly
                    })
    else:
        print("File doesn't exist")

    # Select 12 random questions if there are at least 12, otherwise return all
    num_questions = min(12, len(all_questions))
    selected_questions = random.sample(all_questions, num_questions)

    return selected_questions


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
            'start_time': time.time(),
        }

    state = session['quiz_state']
    current_index = state['current_index']

    if request.method == 'POST':
        # Get the user's answer for the current question
        selected_answer = request.form.get('answer')
        correct_answer = questions[current_index]['correct']

        # Check if the answer is correct
        if selected_answer == correct_answer:
            state['score'] += 1  # Increase score for correct answer
            questions[current_index]['answered_correctly'] = True
        else:
            # If answer is wrong, move the question to the end of the list
            question_to_move = questions.pop(current_index)
            questions.append(question_to_move)
            flash('Incorrect answer. This question has been moved to the end of the quiz.', 'error')

        # Move to the next question
        state['current_index'] = (state['current_index'] + 1) % len(questions)  # Ensure it loops properly
        session['quiz_state'] = state

    # Check if the quiz is finished
    if all(q['answered_correctly'] for q in questions):
        end_time = time.time()
        time_taken = round(end_time - state['start_time'], 2)
        final_score = state['score']

        # Clear session data related to the quiz
        session.pop('quiz_state', None)
        session.pop('questions', None)

        flash(f"You scored {final_score}/{len(questions)} in {time_taken} seconds", 'success')
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

    # Render the current question
    return render_template(
        "quiz.html",
        user=current_user,
        question=current_question,
        current_index=state['current_index'] + 1,
        total_questions=len(questions)
    )
