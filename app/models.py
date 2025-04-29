from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    tasks = db.relationship('Task', backref='author', lazy=True, cascade="all, delete-orphan")
    subjects = db.relationship('Subject', backref='owner', lazy=True, cascade="all, delete-orphan")
    # gemini_api_key = db.Column(db.String(200), nullable=True) # 将来用

    def __repr__(self):
        return f"User(id={self.id}, email='{self.email}')"

class Subject(db.Model):
    __tablename__ = 'subject'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    def __repr__(self): 
        return f"Subject(id={self.id}, name='{self.name}', user_id={self.user_id})"

class Task(db.Model):
    __tablename__ = 'task'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    subject_name = db.Column(db.String(50))
    period = db.Column(db.Integer, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    details = db.Column(db.Text)
    priority = db.Column(db.String(10), default='中')
    status = db.Column(db.String(10), nullable=False, default='未着手')
    estimated_time = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        due_date_str = self.due_date.strftime('%Y-%m-%d %H:%M') if self.due_date else 'None'
        return f"Task(id={self.id}, title='{self.title}', Due: {due_date_str}, Status: {self.status})"
