from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify, current_app
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from app.extensions import db
from app.models import User, Subject, Task
from app.utils import login_required
from sqlalchemy.exc import SQLAlchemyError

bp = Blueprint('routes', __name__)

# ブルートフォース攻撃対策用
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME_SEC = 300  # 5分

@bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('routes.dashboard'))
    return redirect(url_for('routes.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('routes.dashboard'))
    error = None
    # セッションで失敗回数・ロック時刻を管理
    login_attempts = session.get('login_attempts', 0)
    lockout_until = session.get('lockout_until')
    now_ts = int(datetime.utcnow().timestamp())
    if lockout_until and now_ts < lockout_until:
        wait_sec = lockout_until - now_ts
        error = f"ログイン試行が多すぎます。{wait_sec}秒後に再試行してください。"
        flash(error, "danger")
        return render_template('login.html', error=error)
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        pwd   = request.form.get('password','')
        app   = current_app._get_current_object()
        app.logger.info(f"Login attempt: {email}")
        # debug skip
        if app.config.get('DEBUG_SKIP_LOGIN_CHECK') and email == app.config.get('DEBUG_SKIP_LOGIN_EMAIL'):
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(email=email, password_hash=generate_password_hash("debug"))
                db.session.add(user); db.session.commit()
            session.clear()
            session['user_id']    = user.id
            session['user_email'] = user.email
            session['login_attempts'] = 0
            flash(f"Debug login ({email})",'warning')
            return redirect(url_for('routes.dashboard'))
        if not email:
            error="メールアドレスを入力"
        elif not pwd:
            error="パスワードを入力"
        else:
            user = User.query.filter_by(email=email).first()
            if not user or not check_password_hash(user.password_hash,pwd):
                login_attempts += 1
                session['login_attempts'] = login_attempts
                if login_attempts >= MAX_LOGIN_ATTEMPTS:
                    session['lockout_until'] = int(datetime.utcnow().timestamp()) + LOCKOUT_TIME_SEC
                    error = f"ログイン失敗が多すぎます。{LOCKOUT_TIME_SEC//60}分後に再試行してください。"
                else:
                    error = f"メールアドレスorパスワードが違います（{login_attempts}/{MAX_LOGIN_ATTEMPTS}）"
            else:
                session.clear()
                session['user_id']    = user.id
                session['user_email'] = user.email
                session['login_attempts'] = 0
                flash("ログインしました。","success")
                return redirect(url_for('routes.dashboard'))
        flash(error,"danger")
    return render_template('login.html', error=error)

@bp.route('/logout')
@login_required
def logout():
    user_email = session.get('user_email','Unknown')
    session.clear()
    current_app.logger.info(f"{user_email} logged out")
    flash("ログアウトしました。","info")
    return redirect(url_for('routes.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    uid = session['user_id']
    email = session.get('user_email','')
    tasks=[]
    if uid!=0:
        now=datetime.utcnow()
        tasks=Task.query.filter(
            Task.user_id==uid,
            Task.status!='完了',
            Task.due_date!=None,
            Task.due_date>=now,
            Task.due_date<=now+timedelta(days=3)
        ).order_by(Task.due_date.asc()).all()
        for t in tasks:
            t.days_remaining=(t.due_date-now).days
    return render_template(
        'dashboard.html',
        user_email=email,
        upcoming_tasks=tasks,
        ai_recommendations=None,
        api_key_set=False
    )

@bp.route('/subjects', methods=['GET', 'POST'])
@login_required
def subjects():
    uid = session['user_id']
    if request.method == 'POST':
        try:
            name = request.form.get('subject_name', '').strip()
            if name:
                # パラメータバインディングを使用
                existing_subject = Subject.query.filter_by(
                    user_id=uid,
                    name=name
                ).first()
                
                if not existing_subject:
                    new_subject = Subject(name=name, user_id=uid)
                    db.session.add(new_subject)
                    db.session.commit()
                    flash(f"教科 '{name}' を登録しました", "success")
                else:
                    flash("既に登録済みの教科です", "warning")
            else:
                flash("教科名を入力してください", "warning")
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Subject creation failed: {str(e)}")
            flash("教科の登録中にエラーが発生しました。", "danger")
        except Exception as e:
            current_app.logger.error(f"Unexpected error in subjects: {str(e)}")
            flash("予期せぬエラーが発生しました。", "danger")
        
        return redirect(url_for('routes.subjects'))

    try:
        subs = Subject.query.filter_by(user_id=uid).order_by(Subject.name).all()
        return render_template('subjects.html', subjects=subs)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Subject query failed: {str(e)}")
        flash("教科一覧の取得中にエラーが発生しました。", "danger")
        return redirect(url_for('routes.dashboard'))

@bp.route('/subjects/<int:subject_id>/delete', methods=['POST'])
@login_required
def delete_subject(subject_id):
    try:
        uid = session['user_id']
        sub = Subject.query.get_or_404(subject_id)
        
        if sub.user_id != uid:
            flash("権限がありません。", "danger")
        else:
            name = sub.name
            db.session.delete(sub)
            db.session.commit()
            flash(f"教科 '{name}' を削除しました。", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Subject deletion failed: {str(e)}")
        flash("教科の削除中にエラーが発生しました。", "danger")
    except Exception as e:
        current_app.logger.error(f"Unexpected error in delete_subject: {str(e)}")
        flash("予期せぬエラーが発生しました。", "danger")
    
    return redirect(url_for('routes.subjects'))

@bp.route('/tasks')
@login_required
def tasks():
    try:
        uid = session['user_id']
        tasks = Task.query.filter_by(user_id=uid).order_by(
            Task.due_date.asc().nullslast(), Task.priority
        ).all() if uid != 0 else []
        return render_template('tasks.html', tasks=tasks)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Task query failed: {str(e)}")
        flash("課題一覧の取得中にエラーが発生しました。", "danger")
        return redirect(url_for('routes.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Unexpected error in tasks view: {str(e)}")
        flash("予期せぬエラーが発生しました。", "danger")
        return redirect(url_for('routes.dashboard'))

@bp.route('/tasks/new', methods=['GET', 'POST'])
@login_required
def new_task():
    try:
        uid = session['user_id']
        subs = Subject.query.filter_by(user_id=uid).order_by(Subject.name).all()

        if request.method == 'POST':
            try:
                title = request.form.get('title', '').strip()
                subject_name = request.form.get('subject_name', '').strip()
                period = request.form.get('period') or None
                due_date_str = request.form.get('due_date') or None
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M') if due_date_str else None
                priority = request.form.get('priority', '中')
                status = request.form.get('status', '未着手')
                est_time = request.form.get('estimated_time') or None
                details = request.form.get('details', '').strip()

                # 入力値の検証
                if not title:
                    flash("課題名は必須です。", "danger")
                    return render_template('new_task.html', subjects=subs)

                if period and (not period.isdigit() or not 1 <= int(period) <= 8):
                    flash("時間目は1から8の間で指定してください。", "danger")
                    return render_template('new_task.html', subjects=subs)

                # 新しい課題を作成
                t = Task(
                    title=title,
                    subject_name=subject_name,
                    period=int(period) if period else None,
                    due_date=due_date,
                    priority=priority,
                    status=status,
                    estimated_time=int(est_time) if est_time else None,
                    details=details,
                    user_id=uid
                )
                db.session.add(t)
                db.session.commit()
                flash("新しい課題を登録しました。", "success")
                return redirect(url_for('routes.dashboard'))

            except ValueError as e:
                current_app.logger.error(f"Invalid input in new task: {str(e)}")
                flash("入力値が不正です。", "danger")
                return render_template('new_task.html', subjects=subs)
            except SQLAlchemyError as e:
                db.session.rollback()
                current_app.logger.error(f"Task creation failed: {str(e)}")
                flash("課題の登録中にエラーが発生しました。", "danger")
                return render_template('new_task.html', subjects=subs)

        return render_template('new_task.html', subjects=subs)

    except Exception as e:
        current_app.logger.error(f"Unexpected error in new task: {str(e)}")
        flash("予期せぬエラーが発生しました。", "danger")
        return redirect(url_for('routes.dashboard'))

@bp.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    try:
        uid = session['user_id']
        task = Task.query.get_or_404(task_id)
        
        # 権限チェック
        if task.user_id != uid:
            flash("この課題を編集する権限がありません。", "danger")
            return redirect(url_for('routes.tasks'))

        subs = Subject.query.filter_by(user_id=uid).order_by(Subject.name).all()

        if request.method == 'POST':
            try:
                # 入力値の取得と検証
                title = request.form.get('title', '').strip()
                if not title:
                    flash("課題名は必須です。", "danger")
                    return render_template('edit_task.html', task=task, subjects=subs)

                # フォームデータの取得
                subject_name = request.form.get('subject_name', '').strip()
                period = request.form.get('period') or None
                due_date_str = request.form.get('due_date') or None
                priority = request.form.get('priority', '中')
                status = request.form.get('status', '未着手')
                est_time = request.form.get('estimated_time') or None
                details = request.form.get('details', '').strip()

                # 時間目の検証
                if period and (not period.isdigit() or not 1 <= int(period) <= 8):
                    flash("時間目は1から8の間で指定してください。", "danger")
                    return render_template('edit_task.html', task=task, subjects=subs)

                # タスクの更新
                task.title = title
                task.subject_name = subject_name
                task.period = int(period) if period else None
                task.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M') if due_date_str else None
                task.priority = priority
                task.status = status
                task.estimated_time = int(est_time) if est_time else None
                task.details = details

                db.session.commit()
                flash("課題を更新しました。", "success")
                return redirect(url_for('routes.tasks'))

            except ValueError as e:
                current_app.logger.error(f"Invalid input in edit task: {str(e)}")
                flash("入力値が不正です。", "danger")
                return render_template('edit_task.html', task=task, subjects=subs)
            except SQLAlchemyError as e:
                db.session.rollback()
                current_app.logger.error(f"Task update failed: {str(e)}")
                flash("課題の更新中にエラーが発生しました。", "danger")
                return render_template('edit_task.html', task=task, subjects=subs)

        # GET リクエストの場合
        task.due_date_str = task.due_date.strftime('%Y-%m-%dT%H:%M') if task.due_date else ''
        return render_template('edit_task.html', task=task, subjects=subs)

    except Exception as e:
        current_app.logger.error(f"Unexpected error in edit task: {str(e)}")
        flash("予期せぬエラーが発生しました。", "danger")
        return redirect(url_for('routes.tasks'))

@bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    try:
        uid = session['user_id']
        task = Task.query.get_or_404(task_id)
        
        if task.user_id != uid:
            flash("この課題を削除する権限がありません。", "danger")
        else:
            title = task.title
            db.session.delete(task)
            db.session.commit()
            flash(f"課題「{title}」を削除しました。", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Task deletion failed: {str(e)}")
        flash("課題の削除中にエラーが発生しました。", "danger")
    except Exception as e:
        current_app.logger.error(f"Unexpected error in delete task: {str(e)}")
        flash("予期せぬエラーが発生しました。", "danger")
    
    return redirect(url_for('routes.tasks'))

@bp.route('/calendar')
@login_required
def calendar():
    return render_template('calendar.html')

@bp.route('/api/events')
@login_required
def api_events():
    try:
        uid = session['user_id']
        events = []
        tasks = Task.query.filter_by(user_id=uid).filter(Task.due_date != None).all()
        
        for t in tasks:
            events.append({
                'id': t.id,
                'title': f"[{t.subject_name}] {t.title}" if t.subject_name else t.title,
                'start': t.due_date.isoformat(),
                'color': None,
                'extendedProps': {
                    'status': t.status,
                    'priority': t.priority,
                    'description': t.details or ''
                }
            })
        return jsonify(events)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Event query failed: {str(e)}")
        return jsonify({'error': 'データの取得中にエラーが発生しました。'}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error in api events: {str(e)}")
        return jsonify({'error': '予期せぬエラーが発生しました。'}), 500

@bp.route('/settings', methods=['GET'])
@login_required
def settings():
    user=User.query.get(session['user_id'])
    return render_template('settings.html', user=user, api_key_is_set=False)

@bp.route('/settings/change_password', methods=['POST'])
@login_required
def change_password():
    try:
        user = User.query.get_or_404(session['user_id'])
        cur = request.form.get('current_password', '')
        new = request.form.get('new_password', '')
        con = request.form.get('confirm_password', '')

        # 現在のパスワードが正しくない場合
        if not check_password_hash(user.password_hash, cur):
            flash("現在のパスワードが違います。", "danger")
            # セキュリティのため、失敗回数をカウント
            session['pwd_change_attempts'] = session.get('pwd_change_attempts', 0) + 1
            if session.get('pwd_change_attempts', 0) >= 5:
                # 5回失敗したらログアウト
                session.clear()
                flash("パスワード変更の試行回数が多すぎます。再度ログインしてください。", "danger")
                return redirect(url_for('routes.login'))
            return redirect(url_for('routes.settings'))

        # 新しいパスワードの検証
        if len(new) < 6:
            flash("新しいパスワードは6文字以上必要です。", "danger")
        elif new != con:
            flash("確認パスワードが一致しません。", "danger")
        else:
            try:
                user.password_hash = generate_password_hash(new)
                db.session.commit()
                # パスワード変更成功後はセッションをクリアして再ログインを要求
                session.clear()
                flash("パスワードを変更しました。新しいパスワードで再度ログインしてください。", "success")
                return redirect(url_for('routes.login'))
            except SQLAlchemyError as e:
                db.session.rollback()
                current_app.logger.error(f"Password change failed: {str(e)}")
                flash("パスワード変更中にエラーが発生しました。", "danger")

        return redirect(url_for('routes.settings'))
    except Exception as e:
        current_app.logger.error(f"Unexpected error in change_password: {str(e)}")
        flash("予期せぬエラーが発生しました。", "danger")
        return redirect(url_for('routes.settings'))
