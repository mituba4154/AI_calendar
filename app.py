# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify # jsonify を追加
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta # timedelta を追加
import os
import logging
import click

# --- デバッグ用ログインバイパスフラグ ---
DEBUG_SKIP_LOGIN_CHECK = False # MUST BE FALSE IN PRODUCTION
DEBUG_SKIP_LOGIN_EMAIL = "debug@example.com"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key_should_be_changed_in_production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- ロギング設定 ---
logging.basicConfig(level=logging.INFO)
# app.logger.setLevel(logging.INFO)

# --- モデル定義 ---
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
    def __repr__(self): return f"Subject(id={self.id}, name='{self.name}', user_id={self.user_id})"

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

# --- 認証ヘルパー ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # デバッグバイパスが有効なら常に通過
        if DEBUG_SKIP_LOGIN_CHECK and 'user_id' not in session:
            app.logger.warning(f"--- DEBUG MODE: Bypassing login_required for user_id check ---")
            # デバッグユーザー情報をセッションに入れる (ログイン処理と同様に)
            debug_user = User.query.filter_by(email=DEBUG_SKIP_LOGIN_EMAIL).first()
            session['user_id'] = debug_user.id if debug_user else 0
            session['user_email'] = DEBUG_SKIP_LOGIN_EMAIL
            app.logger.warning(f"--- DEBUG MODE: Set session user_id={session['user_id']}, email={session['user_email']} ---")
            # return f(*args, **kwargs) # ここでreturnすると下のチェックに進まない

        if 'user_id' not in session:
            flash('ログインが必要です。', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- ルート定義 ---
@app.route('/')
def index():
    if 'user_id' in session:
        # === デフォルト遷移先をダッシュボードに変更 ===
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        # === ログイン済みの場合もダッシュボードへ ===
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        error = None
        app.logger.info(f"Login attempt: '{email}'")
        if DEBUG_SKIP_LOGIN_CHECK and email == DEBUG_SKIP_LOGIN_EMAIL:
            app.logger.warning(f"--- DEBUG MODE: Bypassing password check for {email} ---")
            user = User.query.filter_by(email=email).first()
            if not user: # デバッグ用ユーザーが存在しない場合は作成する（初回のみ）
                app.logger.warning(f"--- DEBUG MODE: Creating debug user {email} ---")
                hashed_password = generate_password_hash("debug") # 仮パスワード
                user = User(email=email, password_hash=hashed_password)
                try:
                    db.session.add(user)
                    db.session.commit()
                    app.logger.info(f"--- DEBUG MODE: Debug user {email} created. ---")
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f"--- DEBUG MODE: Failed to create debug user: {e} ---")
                    flash("デバッグユーザーの自動作成に失敗しました。", "danger")
                    return render_template('login.html') # エラー時はログイン画面に戻る

            session.clear()
            session['user_id'] = user.id
            session['user_email'] = email # ユーザーIDを正しく設定
            # === デバッグログイン後のリダイレクト先もダッシュボードへ ===
            flash(f'デバッグモードでログイン ({email})', 'warning')
            return redirect(url_for('dashboard'))

        if not email or email.strip() == "":
            error = 'メールアドレスを入力'
            flash(error, 'danger')
        elif not password:
            error = 'パスワードを入力'
            flash(error, 'danger')
        else:
            user = User.query.filter_by(email=email).first()
            if user is None or not check_password_hash(user.password_hash, password):
                error = 'メールアドレスorパスワードが違います'
                app.logger.warning(f"Login failed for {email}")
                flash(error, 'danger')
            else:
                app.logger.info(f"Login successful: {email}")
                session.clear()
                session['user_id'] = user.id
                session['user_email'] = user.email
                flash('ログインしました。', 'success')
                next_page = request.args.get('next')
                # === ログイン後のデフォルト遷移先もダッシュボードへ ===
                # next_page が外部URLでないか基本的なチェック
                if next_page and next_page.startswith('/') and not next_page.startswith('//') and ':' not in next_page:
                     return redirect(next_page)
                else:
                     return redirect(url_for('dashboard')) # 安全のため dashboard にリダイレクト

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    user_email = session.get('user_email', 'Unknown')
    session.clear()
    app.logger.info(f"User {user_email} logged out.")
    flash('ログアウトしました。', 'info')
    return redirect(url_for('login'))

# --- ★★★ ダッシュボード（ホーム画面）ルート (修正版) ★★★ ---
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    user_email = session.get('user_email', 'ゲスト')
    upcoming_tasks = [] # 期限が近い課題リスト用

    # === 期限が近い課題を取得 (デバッグユーザー以外) ===
    if user_id != 0:
        try:
            now = datetime.utcnow()
            # 締切が今日以降で、かつ3日以内の未完了タスクを取得
            upcoming_tasks = Task.query.filter(
                Task.user_id == user_id,
                Task.status != '完了', # 未完了のタスク
                Task.due_date != None, # 締切日が設定されている
                Task.due_date >= now,  # 締切が今日以降
                Task.due_date <= now + timedelta(days=3) # 締切が3日以内
            ).order_by(Task.due_date.asc()).limit(5).all() # 締切日順で最大5件

            # (任意) 残り日数を計算してタスクオブジェクトに追加（テンプレートでの処理が楽になる）
            for task in upcoming_tasks:
                time_diff = task.due_date - now
                task.days_remaining = time_diff.days # 残り日数を計算
                # さらに細かい時間も表示したい場合
                # task.hours_remaining = time_diff.seconds // 3600
                # task.minutes_remaining = (time_diff.seconds // 60) % 60

        except Exception as e:
            app.logger.error(f"Error fetching upcoming tasks for user_id {user_id}: {e}")
            flash("期限が近い課題の取得中にエラーが発生しました。", "danger")

    # === ここに後でAI推奨機能のロジックを追加 ===
    ai_recommendations = None # AI推奨結果用 (今はまだNone)
    # user = User.query.get(user_id) # AI機能でユーザー情報が必要なら取得
    # api_key_set = bool(user and user.gemini_api_key) # APIキーが設定されているか (将来用)
    api_key_set = False # 現時点ではAPIキーは未実装なのでFalse

    # --- ここまでAI推奨機能の準備 ---


    return render_template('dashboard.html',
                           user_email=user_email,
                           upcoming_tasks=upcoming_tasks, # 期限が近い課題リストを渡す
                           ai_recommendations=ai_recommendations, # AI推奨結果を渡す
                           api_key_set=api_key_set # APIキー設定状況を渡す
                           )


# --- 教科管理ルート (変更なし) ---
@app.route('/subjects', methods=['GET', 'POST'])
@login_required
def subjects():
    user_id = session['user_id']
    if user_id == 0 and DEBUG_SKIP_LOGIN_CHECK:
        flash("デバッグユーザーは教科管理を利用できません。", "warning")
        return redirect(url_for('dashboard')) # 戻り先を dashboard に
    if request.method == 'POST':
        subject_name = request.form.get('subject_name')
        if subject_name and subject_name.strip() != "":
            existing_subject = Subject.query.filter_by(user_id=user_id, name=subject_name.strip()).first()
            if not existing_subject:
                new_subject = Subject(name=subject_name.strip(), user_id=user_id)
                try:
                    db.session.add(new_subject)
                    db.session.commit()
                    flash(f"教科 '{subject_name}' 登録", "success")
                except Exception as e:
                    db.session.rollback()
                    flash(f"教科登録エラー: {e}", "danger")
                    app.logger.error(f"Sub add err: {e}")
            else:
                flash(f"教科 '{subject_name}' は登録済", "warning")
        else:
            flash("教科名を入力", "warning")
        return redirect(url_for('subjects'))
    user_subjects = Subject.query.filter_by(user_id=user_id).order_by(Subject.name).all()
    # ★★★ ダッシュボードへのリンクを渡す（教科管理ページにも適用する場合） ★★★
    return render_template('subjects.html', subjects=user_subjects, show_dashboard_link=True)

@app.route('/subjects/<int:subject_id>/delete', methods=['POST'])
@login_required
def delete_subject(subject_id):
    user_id = session['user_id']
    if user_id == 0 and DEBUG_SKIP_LOGIN_CHECK:
        flash("デバッグユーザーは教科削除を利用できません。", "warning")
        return redirect(url_for('subjects'))
    subject_to_delete = Subject.query.get_or_404(subject_id)
    if subject_to_delete.owner.id != user_id:
        flash("権限なし", "danger")
        return redirect(url_for('subjects'))
    try:
        db.session.delete(subject_to_delete)
        db.session.commit()
        flash(f"教科 '{subject_to_delete.name}' 削除", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"教科削除エラー: {e}", "danger")
        app.logger.error(f"Sub del err: {e}")
    return redirect(url_for('subjects'))

# --- タスク関連ルート ---
@app.route('/tasks')
@login_required
def tasks():
    user_id = session['user_id']
    user_tasks = []
    # デバッグユーザー(user_id=0)の場合もタスクは空リストになる
    if user_id != 0: # デバッグユーザー(user_id=0) のタスクは表示しない
        user_tasks = Task.query.filter_by(user_id=user_id).order_by(Task.due_date.asc().nullslast(), Task.priority).all()
    # ★★★ ダッシュボードへのリンクを渡す（テンプレート側で表示） ★★★
    return render_template('tasks.html', tasks=user_tasks, show_dashboard_link=True) # デバッグユーザー設定非表示フラグは削除

@app.route('/tasks/new', methods=['GET', 'POST'])
@login_required
def new_task():
    user_id = session['user_id']
    # デバッグユーザー(user_id=0)はタスク追加不可とする
    if user_id == 0 and DEBUG_SKIP_LOGIN_CHECK:
        flash("デバッグユーザーはタスクを追加できません。", "warning")
        return redirect(url_for('dashboard')) # 戻り先を dashboard に

    user_subjects = Subject.query.filter_by(user_id=user_id).order_by(Subject.name).all()

    if request.method == 'POST':
        title = request.form.get('title')
        subject_name = request.form.get('subject_name')
        period_str = request.form.get('period')
        due_date_str = request.form.get('due_date')
        priority = request.form.get('priority', '中')
        status = request.form.get('status', '未着手')
        estimated_time_str = request.form.get('estimated_time')
        details = request.form.get('details')

        error = None
        # === 検証処理 ===
        if not title or title.strip() == "": error = "課題名は必須です。"
        period = None
        if period_str and period_str.strip() != "":
            if period_str.isdigit():
                period = int(period_str)
                if not (1 <= period <= 8):
                    if error is None: error = "時間目は1から8の数値を入力してください。"
            else:
                if error is None: error = "時間目は半角数値を入力してください。"
        due_date = None
        if due_date_str:
            try: due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                 if error is None: error = "締切日時の形式が不正 (例: 2024-01-01T10:00)"
        estimated_time = None
        if estimated_time_str and estimated_time_str.strip() != "":
            try:
                estimated_time = int(estimated_time_str);
                if estimated_time < 0:
                     if error is None: error = "想定所要時間は0以上の数値を入力してください。"
            except ValueError:
                 if error is None: error = "想定所要時間は半角数値を入力してください。"
        # === ここまで検証 ===

        if error is None:
            new_task_obj = Task(
                title=title,
                subject_name=subject_name,
                period=period,
                due_date=due_date,
                priority=priority,
                status=status,
                estimated_time=estimated_time,
                details=details,
                user_id=user_id # ユーザーIDをセット
            )
            try:
                db.session.add(new_task_obj)
                db.session.commit()
                flash('新しい課題が登録されました。', 'success')
                # === 登録後のリダイレクト先もダッシュボードへ ===
                return redirect(url_for('dashboard')) # 遷移先変更
            except Exception as e:
                db.session.rollback()
                flash(f"登録エラー: {e}", 'danger')
                app.logger.error(f"Task add err: {e}")
        else:
            flash(error, 'danger')
            # === エラー時に入力値を保持して再表示 ===
            return render_template('new_task.html',
                                   subjects=user_subjects,
                                   title=title,
                                   subject_name=subject_name,
                                   period=period_str,
                                   due_date=due_date_str,
                                   priority=priority,
                                   status=status,
                                   estimated_time=estimated_time_str,
                                   details=details,
                                   show_dashboard_link=True # エラー時も渡す
                                  )

    # GETリクエストの場合
    # ★★★ ダッシュボードへのリンクを渡す ★★★
    return render_template('new_task.html', subjects=user_subjects, show_dashboard_link=True)


@app.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    user_id = session['user_id']
    task_to_edit = Task.query.get_or_404(task_id)

    # デバッグユーザー(user_id=0) または 他のユーザーのタスク編集不可
    if (user_id == 0 and DEBUG_SKIP_LOGIN_CHECK) or task_to_edit.author.id != user_id:
        flash("権限がありません。", "danger")
        return redirect(url_for('dashboard')) # 戻り先を dashboard に

    user_subjects = Subject.query.filter_by(user_id=user_id).order_by(Subject.name).all()

    if request.method == 'POST':
        title = request.form.get('title')
        subject_name = request.form.get('subject_name')
        period_str = request.form.get('period')
        due_date_str = request.form.get('due_date')
        priority = request.form.get('priority', '中')
        status = request.form.get('status', '未着手')
        estimated_time_str = request.form.get('estimated_time')
        details = request.form.get('details')

        error = None
        # === 検証処理 (new_taskと同様) ===
        if not title or title.strip() == "": error = "課題名は必須です。"
        period = None
        if period_str and period_str.strip() != "":
            if period_str.isdigit():
                period = int(period_str)
                if not (1 <= period <= 8):
                    if error is None: error = "時間目は1から8の数値を入力してください。"
            else:
                if error is None: error = "時間目は半角数値を入力してください。"
        due_date = None
        if due_date_str:
            try: due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                 if error is None: error = "締切日時の形式が不正 (例: 2024-01-01T10:00)"
        else: # 空の場合は None にする (既存の日付をクリアする場合)
             due_date = None
        estimated_time = None
        if estimated_time_str and estimated_time_str.strip() != "":
            try:
                estimated_time = int(estimated_time_str)
                if estimated_time < 0:
                     if error is None: error = "想定所要時間は0以上の数値を入力してください。"
            except ValueError:
                 if error is None: error = "想定所要時間は半角数値を入力してください。"
        else: # 空の場合は None にする
            estimated_time = None
        # === ここまで検証 ===

        if error is None:
            task_to_edit.title = title
            task_to_edit.subject_name = subject_name
            task_to_edit.period = period
            task_to_edit.due_date = due_date
            task_to_edit.priority = priority
            task_to_edit.status = status
            task_to_edit.estimated_time = estimated_time
            task_to_edit.details = details

            try:
                db.session.commit()
                flash('課題が更新されました。', 'success');
                # === 更新後のリダイレクト先もダッシュボードへ ===
                return redirect(url_for('dashboard')) # 遷移先変更
            except Exception as e:
                db.session.rollback()
                flash(f"更新エラー: {e}", 'danger')
                app.logger.error(f"Task edit err: {e}")
        else:
            flash(error, 'danger')
            # === エラー時も入力値を保持して再表示 (フォームにはエラー時の値を表示) ===
            # Taskオブジェクト自体はまだコミットされていないので元の値だが、
            # render_templateに渡す値はPOSTされた値を使う
            task_to_edit.title = title # 一時的に表示用に上書き (DBには反映されない)
            task_to_edit.subject_name = subject_name
            task_to_edit.period = period_str # 文字列で保持
            # due_dateは文字列で保持するための処理を追加
            task_to_edit.due_date_str = due_date_str
            task_to_edit.priority = priority
            task_to_edit.status = status
            task_to_edit.estimated_time = estimated_time_str # 文字列で保持
            task_to_edit.details = details
            # ★★★ ダッシュボードへのリンクを渡す ★★★
            return render_template('edit_task.html', task=task_to_edit, subjects=user_subjects, show_dashboard_link=True)


    # GETリクエストの場合 (エラーがなく、初回表示時)
    # due_dateを適切なフォーマットの文字列に変換して渡す
    if task_to_edit.due_date:
        task_to_edit.due_date_str = task_to_edit.due_date.strftime('%Y-%m-%dT%H:%M')
    else:
        task_to_edit.due_date_str = "" # Noneの場合は空文字列

    # ★★★ ダッシュボードへのリンクを渡す ★★★
    return render_template('edit_task.html', task=task_to_edit, subjects=user_subjects, show_dashboard_link=True)


@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    user_id = session['user_id']
    task_to_delete = Task.query.get_or_404(task_id)

    # デバッグユーザー(user_id=0) または 他のユーザーのタスク削除不可
    if (user_id == 0 and DEBUG_SKIP_LOGIN_CHECK) or task_to_delete.author.id != user_id:
        flash("権限がありません。", "danger")
        # === 戻り先をダッシュボードへ ===
        return redirect(url_for('dashboard')) # 遷移先変更

    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        flash(f"課題 '{task_to_delete.title}' 削除", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"削除エラー: {e}", "danger")
        app.logger.error(f"Task del err: {e}")
    # === 削除後のリダイレクト先もダッシュボードへ ===
    return redirect(url_for('dashboard')) # 遷移先変更

# --- ★★★ カレンダー表示用ルート ★★★ ---
@app.route('/calendar')
@login_required
def calendar():
    user_id = session['user_id']
    # デバッグユーザーの場合もカレンダーページ自体は表示する
    # API側でデータを空にするなどで対応
    if user_id == 0 and DEBUG_SKIP_LOGIN_CHECK:
        flash("デバッグユーザーはカレンダー機能のデータが制限されます。", "info")

    # calendar.html をレンダリングするだけ。
    # イベントデータはFullCalendarが /api/events から非同期で取得する。
    # ★★★ ダッシュボードへのリンクを渡す ★★★
    return render_template('calendar.html', show_dashboard_link=True)

# --- ★★★ FullCalendar用イベントデータ供給APIエンドポイント ★★★ ---
@app.route('/api/events')
@login_required
def api_events():
    user_id = session['user_id']
    events = []

    # デバッグユーザーの場合はログを出力して空のイベントリストを返す
    if user_id == 0 and DEBUG_SKIP_LOGIN_CHECK:
        app.logger.warning("API events request bypassed for debug user (user_id=0). Returning empty list.")
        return jsonify(events) # 空リストを返す

    # 通常のログインユーザーのタスクを取得 (締切日が設定されているもののみ)
    try:
        user_tasks = Task.query.filter(
            Task.user_id == user_id,
            Task.due_date.isnot(None) # 締切日 (due_date) がNULLでないもの
        ).order_by(Task.due_date).all() # 念のため日付順でソート

        # FullCalendarが要求する形式に変換
        for task in user_tasks:
            event_color = None # ステータス等に応じて色分け
            if task.status == '完了':
                event_color = 'grey'
            elif task.priority == '高':
                event_color = 'red'
            elif task.priority == '低':
                event_color = 'lightblue'
            # '中' はデフォルト色 or 指定しない

            event_title = task.title
            if task.subject_name:
                event_title = f"[{task.subject_name}] {task.title}" # 教科名を先頭に

            events.append({
                'id': task.id, # TaskのIDをそのまま使う
                'title': event_title,
                'start': task.due_date.isoformat(), # ISO 8601形式 (YYYY-MM-DDTHH:MM:SS)
                'allDay': False, # 時刻を持つデータなので False とする
                'description': task.details or '', # detailsがNoneの場合空文字に
                'color': event_color, # イベントの色
                'extendedProps': {
                    'status': task.status,
                    'priority': task.priority,
                    'period': task.period,
                    'estimated_time': task.estimated_time,
                    'task_url': url_for('edit_task', task_id=task.id) # 詳細表示用にURLを渡す
                }
            })
        app.logger.info(f"API events: Found {len(events)} events for user_id={user_id}")

    except Exception as e:
        app.logger.error(f"Error fetching tasks for API events (user_id={user_id}): {e}")
        return jsonify({"error": "Failed to fetch events"}), 500

    return jsonify(events)

# --- 設定ページルート ---
@app.route('/settings', methods=['GET'])
@login_required
def settings():
    user_id = session['user_id']
    # デバッグユーザーは設定ページ利用不可
    if user_id == 0 and DEBUG_SKIP_LOGIN_CHECK:
        flash("デバッグユーザーは設定を変更できません。", "warning")
        return redirect(url_for('dashboard')) # 戻り先を dashboard に

    user = User.query.get(user_id)
    if not user:
        flash("ユーザー情報の取得に失敗しました。", "danger")
        session.clear()
        return redirect(url_for('login'))
    # ★★★ ダッシュボードへのリンクを渡す ★★★
    return render_template('settings.html', user=user, show_dashboard_link=True)

@app.route('/settings/change_password', methods=['POST'])
@login_required
def change_password():
    user_id = session['user_id']
    # デバッグユーザーはパスワード変更不可
    if user_id == 0 and DEBUG_SKIP_LOGIN_CHECK:
        flash("デバッグユーザーはパスワードを変更できません。", "warning")
        return redirect(url_for('settings')) # 設定ページにリダイレクト

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    user = User.query.get(user_id)
    error = None
    if not user:
        flash("ユーザー情報取得失敗", "danger")
        return redirect(url_for('settings'))

    if not current_password: error = "現在のパスワードを入力してください。"
    elif not new_password: error = "新しいパスワードを入力してください。"
    elif len(new_password) < 6: # 簡単なパスワード強度チェック（例）
        error = "新しいパスワードは6文字以上で入力してください。"
    elif new_password != confirm_password: error = "新しいパスワードが一致しません。"
    elif not check_password_hash(user.password_hash, current_password):
        error = "現在のパスワードが正しくありません。"
        app.logger.warning(f"PW change fail: Incorrect current PW for {user.email}")

    if error: flash(error, 'danger')
    else:
        try:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash("パスワードが正常に変更されました。", "success")
            app.logger.info(f"PW changed: {user.email}")
        except Exception as e:
            db.session.rollback()
            flash(f"パスワード変更中にエラーが発生しました: {e}", "danger")
            app.logger.error(f"PW change err: {e}")
    # === 成功・失敗に関わらず設定ページへリダイレクト (変更なし) ===
    return redirect(url_for('settings'))

# --- 管理者用ユーザー作成コマンド (変更なし) ---
@app.cli.command("create-user")
@click.argument("email")
@click.password_option()
def create_user(email, password):
    if '@' not in email:
        print("Error: 無効なメールアドレス形式です。")
        return
    if User.query.filter_by(email=email).first():
        print(f"Error: メールアドレス '{email}' は既に使用されています。")
        return
    if len(password) < 6:
        print("Error: パスワードは6文字以上で設定してください。")
        return # パスワード長のチェック追加

    hashed_password = generate_password_hash(password)
    new_user = User(email=email, password_hash=hashed_password)
    try:
        with app.app_context(): # コマンド実行時もappコンテキスト内で実行
             db.session.add(new_user)
             db.session.commit()
             print(f"Success: ユーザー '{email}' が作成されました。")
    except Exception as e:
        db.session.rollback()
        print(f"Error: ユーザー作成中にエラーが発生しました - {e}")

# --- アプリケーションコンテキスト内でデータベースを作成 ---
# このブロックは development 環境での初回実行時などに役立つが、
# 本番環境では Flask-Migrate などを使う方が一般的
with app.app_context():
    db.create_all()
    print("--- Database tables checked/created (if necessary) ---")
    # デバッグユーザーが存在しない場合に作成する処理を追加（create-userコマンドとは別）
    if DEBUG_SKIP_LOGIN_CHECK and not User.query.filter_by(email=DEBUG_SKIP_LOGIN_EMAIL).first():
        print(f"--- Creating default debug user: {DEBUG_SKIP_LOGIN_EMAIL} ---")
        try:
            hashed_password = generate_password_hash("debug") # デバッグ用パスワード
            debug_user = User(email=DEBUG_SKIP_LOGIN_EMAIL, password_hash=hashed_password)
            db.session.add(debug_user)
            db.session.commit()
            print(f"--- Default debug user {DEBUG_SKIP_LOGIN_EMAIL} created successfully. ---")
        except Exception as e:
            db.session.rollback()
            print(f"--- Error creating default debug user: {e} ---")


if __name__ == '__main__':
    if DEBUG_SKIP_LOGIN_CHECK:
        app.logger.critical("!!! DEBUG LOGIN BYPASS ENABLED !!!")
        app.logger.warning(f"!!! Debug User Email: {DEBUG_SKIP_LOGIN_EMAIL} !!!")
    app.run(debug=False, host='0.0.0.0', port=53833)