from flask import Blueprint, render_template, request, session
from flask_login import login_required, current_user
from os import path

views = Blueprint('views', __name__)

@views.route('/', methods = ['GET', 'POST'])
@login_required
def home():

    session.pop('quiz_state', None)
    session.pop('questions', None)

    leaderboard = get_high_scores()
    return render_template("home.html", user = current_user, leaderboard = get_high_scores())

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
