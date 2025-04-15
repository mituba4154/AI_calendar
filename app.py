from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps # ← wraps を使う予定がなければこれも不要
import datetime # ← 締切日の処理で必要になるので追加推奨
import os # osモジュールをインポート (SECRET_KEYの生成に使う場合など)

app = Flask(__name__)
# 環境変数からSECRET_KEYを読み込むか、なければデフォルト値を設定（本番環境では必ず設定する）
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key_should_be_strong_and_random')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # SQLAlchemyの警告を抑制するため推奨
db = SQLAlchemy(app)

# --- モデル定義 ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    # Taskモデルとのリレーションシップ (Taskモデル定義後にコメント解除)
    tasks = db.relationship('Task', backref='author', lazy=True)

    def __repr__(self):
        return f"User('{self.email}')"


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # どのユーザーのタスクかを紐付けるための外部キー
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False) # 課題名 (必須)
    subject = db.Column(db.String(50)) # 科目
    # 締切日時 (DateTime型を使用)
    due_date = db.Column(db.DateTime, nullable=True) # nullを許可する場合
    details = db.Column(db.Text) # 詳細・メモ
    priority = db.Column(db.String(10), default='中') # 重要度 (高, 中, 低) デフォルトは中
    status = db.Column(db.String(10), nullable=False, default='未着手') # 進捗 (未着手, 進行中, 完了)
    estimated_time = db.Column(db.Integer) # 想定所要時間 (分単位など、任意)

    def __repr__(self):
        return f"Task('{self.title}', Due: {self.due_date})"

# --- ルート定義 ---
@app.route('/')
def index():
    # ログインしていればタスクページ、していなければログインページへ
    if 'user_id' in session:
        return redirect(url_for('tasks'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # 簡単な入力検証 (本来はもっと厳密に)
        if not email or not password:
             return render_template('signup.html', error='Email and password are required.')

        # メールアドレスの重複チェック
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template('signup.html', error='Email address already exists.')

        hashed_password = generate_password_hash(password)
        new_user = User(email=email, password_hash=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            # サインアップ成功後、ログインページへリダイレクト
            # flash('Account created successfully! Please log in.', 'success') # flashメッセージを使う場合
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback() # エラー時はロールバック
            # flash(f'An error occurred: {e}', 'danger') # エラーメッセージ表示
            return render_template('signup.html', error=f'An error occurred: {e}') # エラーメッセージ表示

    # GETリクエストの場合
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            return render_template('login.html', error='Email and password are required.')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_email'] = user.email # 必要であればメールアドレスもセッションに保存
            # flash('Login successful!', 'success') # flashメッセージ
            return redirect(url_for('tasks'))  # ログイン成功後、タスクページへリダイレクト
        else:
            # flash('Login unsuccessful. Please check email and password.', 'danger') # flashメッセージ
            return render_template('login.html', error='Invalid email or password.')

    # GETリクエストの場合
    if 'user_id' in session: # 既にログイン済みならタスクページへ
        return redirect(url_for('tasks'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None) # メールアドレスも削除
    # flash('You have been logged out.', 'info') # flashメッセージ
    return redirect(url_for('login'))

# --- タスク関連のルート (仮実装) ---
# この部分はステップ3で詳細を実装します
@app.route('/tasks')
def tasks():
    if 'user_id' not in session:
        return redirect(url_for('login')) # ログインしていなければログインページへ

    user_id = session['user_id']
    # ログイン中のユーザーのタスクを締切日順（NULLは最後に）で取得
    # order_by(Task.due_date.asc().nullslast()) など、並び順は調整可能
    user_tasks = Task.query.filter_by(user_id=user_id).order_by(Task.due_date).all()

    # tasks.htmlをレンダリングし、取得したタスクリストを渡す
    return render_template('tasks.html', tasks=user_tasks)

# --- アプリケーションコンテキスト内でデータベースを作成 ---
# 初回実行時やモデル変更時にテーブルを作成するために必要
# Flask 2.x以降では `flask db init`, `flask db migrate`, `flask db upgrade` (Flask-Migrate使用) が推奨される
# ここでは簡易的に `create_all` を使用
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # debug=True は開発時のみ。本番環境ではFalseにする
    app.run(debug=True)