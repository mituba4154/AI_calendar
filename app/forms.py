# Flask-WTFなどを使う場合の雛形
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class SampleForm(FlaskForm):
    name = StringField('名前', validators=[DataRequired()])
    submit = SubmitField('送信')
