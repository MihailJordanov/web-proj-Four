

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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