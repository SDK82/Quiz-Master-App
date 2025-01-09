from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Quizresponse(db.Model):
    __tablename__ = 'quiz_responses'  # Table name
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)  # Foreign key to Quiz table
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Foreign key to User table
    time_stamp_of_attempt = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp when the quiz was submitted
    total_scored = db.Column(db.Integer, nullable=False)  # Total marks scored
    user_responses = db.Column(db.JSON, nullable=True)

    # Relationships
    quiz = db.relationship('Quiz', backref='quiz_responses', lazy=True)
    user = db.relationship('User', backref='quiz_responses', lazy=True)

    def __init__(self, quiz_id, user_id, total_scored, user_responses=None):
        self.quiz_id = quiz_id
        self.user_id = user_id
        self.total_scored = total_scored
        self.user_responses = user_responses


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)  # Email
    password = db.Column(db.String(150), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    qualification = db.Column(db.String(100), nullable=True)
    dob = db.Column(db.String(10), nullable=True)

    quiz_attempts = db.relationship('Quizresponse', back_populates='user')



class Admin(db.Model):
    __tablename__ = 'Admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)



class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    chapters = db.relationship('Chapter', back_populates='subject', cascade="all, delete-orphan")

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    date_of_quiz = db.Column(db.Date, nullable=False)
    time_duration = db.Column(db.String(5), nullable=False)  # Duration in "hh:mm" format
    total_marks = db.Column(db.Integer, nullable=False)  # Total Marks for the quiz


    chapter = db.relationship('Chapter', back_populates="quizzes")
    questions = db.relationship('Question', back_populates="quiz", cascade="all, delete-orphan")

    quiz_attempts = db.relationship('Quizresponse', back_populates='quiz', cascade="all, delete-orphan")

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_statement = db.Column(db.Text, nullable=False)
    option1 = db.Column(db.String(255), nullable=False)
    option2 = db.Column(db.String(255), nullable=False)
    option3 = db.Column(db.String(255), nullable=False)
    option4 = db.Column(db.String(255), nullable=False)
    correct_option = db.Column(db.String(255), nullable=False)
    marks = db.Column(db.Float, nullable=False)

    quiz = db.relationship('Quiz', back_populates="questions")


class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)

    subject = db.relationship('Subject', back_populates="chapters")
    quizzes = db.relationship('Quiz', back_populates="chapter", cascade="all, delete-orphan")