from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Match, User, UserMatch
from flask_migrate import Migrate
from datetime import datetime
import re
from sqlalchemy import func, extract
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
# Модели


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    number = db.Column(db.Integer, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    
    user_matches = db.relationship('UserMatch', backref='user', lazy=True)

class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    home_team = db.Column(db.String(50))
    away_team = db.Column(db.String(50))
    home_team_result = db.Column(db.Integer)
    away_team_result = db.Column(db.Integer)
    date = db.Column(db.Date)
    location = db.Column(db.String(100))
    user_matches = db.relationship('UserMatch', backref='match', lazy=True)

class UserMatch(db.Model):
    __tablename__ = 'user_match'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    goals = db.Column(db.Integer)
    shots = db.Column(db.Integer)
    shots_on_target = db.Column(db.Integer)
    passes = db.Column(db.Integer)
    fouls = db.Column(db.Integer)
    yellow_cards = db.Column(db.Integer)
    red_cards = db.Column(db.Integer)


@app.route('/getYears')
def get_years():
    years = db.session.query(func.extract('year', Match.date)).distinct().order_by(func.extract('year', Match.date)).all()
    # Преобразуваме резултата в обикновен списък от години
    year_list = [int(year[0]) for year in years]
    return jsonify(year_list)


@app.route('/getPlayTimeData')
def get_play_time_data():
    year = request.args.get('year', type=int)

    # Извличаме броя на мачовете по месеци за избраната година
    matches_by_month = db.session.query(
        extract('month', Match.date).label('month'),
        func.count(Match.id).label('count')
    ).filter(extract('year', Match.date) == year) \
     .group_by('month').order_by('month').all()

    # Преобразуваме данните в JSON формат
    data = [{'month': m[0], 'count': m[1]} for m in matches_by_month]

    return jsonify(data)


@app.route('/playtime')
def playtime():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('playtime.html')



@app.route('/saveStats', methods=['POST'])
def save_stats():
    data = request.json
    user_id = data.get('user_id')
    stats = data.get('stats')

    if not user_id or not stats:
        return jsonify({'error': 'Missing data'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Вземете най-голямото ID на мач от таблицата Matches
    max_match_id = db.session.query(func.max(Match.id)).scalar()
    if not max_match_id:
        return jsonify({'error': 'No matches found'}), 404

    try:
        user_match = UserMatch(
            user_id=user_id,
            match_id=max_match_id,  # Използвайте най-голямото ID на мача
            goals=stats['goals'],
            shots=stats['shots'],
            shots_on_target=stats['shots_on_target'],
            passes=stats['passes'],
            fouls=stats['fouls'],
            yellow_cards=stats['yellow_cards'],
            red_cards=stats['red_cards']
        )

        db.session.add(user_match)
        db.session.commit()

        return jsonify({'message': 'Stats saved successfully!'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")  # Ще добавим лог за грешката
        return jsonify({'error': str(e)}), 500


@app.route('/winRate')
def win_rate():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Извличаме всички мачове от базата данни
    matches = Match.query.all()
    
    # Изчисляваме общия win rate
    total_wins = sum(1 for match in matches if match.home_team_result > match.away_team_result)
    total_matches = len(matches)
    overall_win_rate = round((total_wins / total_matches * 100), 2) if total_matches > 0 else 0
    
    # Изчисляваме win rate по локация
    location_stats = {}
    for match in matches:
        location = match.location
        if location not in location_stats:
            location_stats[location] = {'wins': 0, 'total': 0}
        location_stats[location]['total'] += 1
        if match.home_team_result > match.away_team_result:
            location_stats[location]['wins'] += 1
    location_win_rates = {
        location: {
            'win_rate': round((stats['wins'] / stats['total'] * 100), 2) if stats['total'] > 0 else 0,
            'total_matches': stats['total']
        }
        for location, stats in location_stats.items()
    }

    # Изчисляваме win rate по away_team
    away_team_stats = {}
    for match in matches:
        away_team = match.away_team
        if away_team not in away_team_stats:
            away_team_stats[away_team] = {'wins': 0, 'total': 0}
        away_team_stats[away_team]['total'] += 1
        if match.home_team_result > match.away_team_result:
            away_team_stats[away_team]['wins'] += 1
    away_team_win_rates = {
        away_team: {
            'win_rate': round((stats['wins'] / stats['total'] * 100), 2) if stats['total'] > 0 else 0,
            'total_matches': stats['total']
        }
        for away_team, stats in away_team_stats.items()
    }

    return render_template('winRate.html', overall_win_rate=overall_win_rate, 
                           location_win_rates=location_win_rates, 
                           away_team_win_rates=away_team_win_rates)


@app.route('/getStats')
def get_stats():
    # Текущият потребител от сесията
    current_user_id = session.get('user_id')

    # Извличане на статистиките за всеки потребител с помощта на агрегационни функции
    user_stats = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        func.sum(UserMatch.goals).label('total_goals'),
        func.sum(UserMatch.shots).label('total_shots'),
        func.sum(UserMatch.shots_on_target).label('total_shots_on_target'),
        func.sum(UserMatch.passes).label('total_passes'),
        func.sum(UserMatch.fouls).label('total_fouls'),
        func.sum(UserMatch.yellow_cards).label('total_yellow_cards'),
        func.sum(UserMatch.red_cards).label('total_red_cards')
    ).join(UserMatch, User.id == UserMatch.user_id) \
    .group_by(User.id, User.first_name, User.last_name) \
    .all()

    # Маркиране на текущия потребител
    stats = []
    for user in user_stats:
        stats.append({
            'user_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'total_goals': user.total_goals or 0,
            'total_shots': user.total_shots or 0,
            'total_shots_on_target': user.total_shots_on_target or 0,
            'total_passes': user.total_passes or 0,
            'total_fouls': user.total_fouls or 0,
            'total_yellow_cards': user.total_yellow_cards or 0,
            'total_red_cards': user.total_red_cards or 0,
            'is_current_user': user.id == current_user_id
        })

    # Сортиране: текущият потребител първи
    sorted_stats = sorted(stats, key=lambda x: not x['is_current_user'])

    return jsonify(sorted_stats)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Your existing login logic
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            error = "Invalid email or password."
            return render_template('login.html', error=error)

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        number = request.form['number']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if len(first_name) < 3 or not re.match("^[A-Z][a-z]+$", first_name):
            flash('First name must be at least 3 characters long, contain only letters, and start with a capital letter.')
            return redirect(url_for('signup'))

        if len(last_name) < 3 or not re.match("^[A-Z][a-z]+$", last_name):
            flash('Last name must be at least 3 characters long, contain only letters, and start with a capital letter.')
            return redirect(url_for('signup'))
        
        if int(number) < 0 or int(number) > 99:
            flash('Number must be between 1 and 99.')
            return redirect(url_for('signup'))
        
        # Валидация на паролата: поне 3 символа
        if len(password) < 3:
            flash('Passwords do not match.')
            return redirect(url_for('signup'))

        
        # Проверка дали паролите съвпадат
        if password != confirm_password:
            flash('Passwords do not match.')
            return redirect(url_for('signup'))

        # Проверка дали съществува потребител с този имейл
        existing_user  = User.query.filter_by(email=email).first()
        if existing_user :
            flash('Email alreay exist.')
            return redirect(url_for('signup'))

        existing_number = User.query.filter_by(number=number).first() 
        if existing_number : # or (existing_number < 1 and existing_number > 99)    
            flash('Number is already taken. Please choose a different number between 1 and 99.')
            return redirect(url_for('signup'))

        new_user = User(first_name=first_name, last_name=last_name, email=email, number=number, password=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/', methods = ['GET'])
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/addMatches', methods=['GET', 'POST'])
def add_matches():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        home_team = request.form.get('home_team')
        away_team = request.form.get('away_team')
        home_team_result = int(request.form.get('home_team_result'))
        away_team_result = int(request.form.get('away_team_result'))
        date = request.form.get('date')
        location = request.form.get('location')



        # Създаване на нов мач
        new_match = Match(home_team=home_team, away_team=away_team,
                          home_team_result=home_team_result, away_team_result=away_team_result,
                          date=date, location=location)
        
        db.session.add(new_match)
        db.session.commit()
        try:
            # Обработка на статистиката на потребителите
            for user in User.query.all():
                # Прочитаме стойностите от формата и логваме стойностите
                goals = int(request.form.get(f'goals_{user.id}', 0))
                shots = int(request.form.get(f'shots_{user.id}', 0))
                shots_on_target = int(request.form.get(f'shots_on_target_{user.id}', 0))
                passes = int(request.form.get(f'passes_{user.id}', 0))
                fouls = int(request.form.get(f'fouls_{user.id}', 0))
                yellow_cards = int(request.form.get(f'yellow_cards_{user.id}', 0))
                red_cards = int(request.form.get(f'red_cards_{user.id}', 0))


                # Създаване и запазване на статистиката
                users_match = UserMatch(user_id=user.id, match_id=new_match.id,
                                        goals=goals, shots=shots, shots_on_target=shots_on_target,
                                        passes=passes, fouls=fouls, yellow_cards=yellow_cards,
                                        red_cards=red_cards)
                db.session.add(users_match)

            db.session.commit()

            return redirect(url_for('home'))
        except:      
            flash('Please fill in the blanks.')
            return redirect(url_for('add_matches'))

    return render_template('addmatch.html')


@app.route('/getUsers')
def get_users():
    users = User.query.all()
    return jsonify([{'id': user.id, 'last_name': user.last_name} for user in users])

@app.route('/getMatches', methods=['GET'])
def get_matches():

    matches = Match.query.all()
    matches_list = []
    for match in matches:
        match_data = {
            'home_team': match.home_team,
            'away_team': match.away_team,
            'home_team_result': match.home_team_result,
            'away_team_result': match.away_team_result,
            'date': match.date.isoformat()  
        }
        matches_list.append(match_data)
    return jsonify(matches_list)


@app.route('/matchHistory', methods=['GET', 'POST'])
def matchHistory():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('matchHistory.html')


@app.route('/stats', methods=['GET', 'POST'])
def stats():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('stats.html')


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    current_user_id = session.get('user_id')
    user = User.query.get(current_user_id)
    

    if user.number == 7:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bar1.jpg'  
    elif user.number == 8:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bg35.png' 
    elif user.number == 9:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bar1.jpg' 
    elif user.number == 10:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/man3.jpg' 
    elif user.number == 11:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bayernStadium.jpg' 
    elif user.number == 17:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bayernStadium.jpg'
    elif user.number == 19:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bayernStadium.jpg'
    elif user.number == 47:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bayernStadium.jpg'   
    else:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bg35.png'
    
    return render_template('profile.html', user=user, profile_image=profile_image, outline_image=outline_image)


if __name__ == '__main__':
    app.run(debug=True)



#pg_ctl restart -D "C:\Program Files\PostgreSQL\16\data"



