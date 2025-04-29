from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import logging

from app.models import db, User, Subject, Task
from app.utils import login_required

# Blueprintを作成
bp = Blueprint('routes', __name__)

@bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('routes.dashboard'))
    return redirect(url_for('routes.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    from app import create_app
    app = create_app()
    
    if 'user_id' in session:
        return redirect(url_for('routes.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        error = None
        app.logger.info(f"Login attempt: '{email}'")
        
        # デバッグモードのログインバイパス処理
        DEBUG_SKIP_LOGIN_CHECK = app.config.get('DEBUG_SKIP_LOGIN_CHECK', False)
        DEBUG_SKIP_LOGIN_EMAIL = app.config.get('DEBUG_SKIP_LOGIN_EMAIL', 'debug@example.com')
        
        if DEBUG_SKIP_LOGIN_CHECK and email == DEBUG_SKIP_LOGIN_EMAIL:
            app.logger.warning(f"--- DEBUG MODE: Bypassing password check for {email} ---")
            user = User.query.filter_by(email=email).first()
            if not user:
                app.logger.warning(f"--- DEBUG MODE: Creating debug user {email} ---")
                hashed_password = generate_password_hash("debug")
                user = User(email=email, password_hash=hashed_password)
                try:
                    db.session.add(user)
                    db.session.commit()
                    app.logger.info(f"--- DEBUG MODE: Debug user {email} created. ---")
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f"--- DEBUG MODE: Failed to create debug user: {e} ---")
                    flash("デバッグユーザーの自動作成に失敗しました。", "danger")
                    return render_template('login.html')

            session.clear()
            session['user_id'] = user.id
            session['user_email'] = email
            flash(f'デバッグモードでログイン ({email})', 'warning')
            return redirect(url_for('routes.dashboard'))

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
                if next_page and next_page.startswith('/') and not next_page.startswith('//') and ':' not in next_page:
                    return redirect(next_page)
                else:
                    return redirect(url_for('routes.dashboard'))

    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    from app import create_app
    app = create_app()
    
    user_email = session.get('user_email', 'Unknown')
    session.clear()
    app.logger.info(f"User {user_email} logged out.")
    flash('ログアウトしました。', 'info')
    return redirect(url_for('routes.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    from app import create_app
    app = create_app()
    
    user_id = session['user_id']
    user_email = session.get('user_email', 'ゲスト')
    upcoming_tasks = []

    if user_id != 0:
        try:
            now = datetime.utcnow()
            upcoming_tasks = Task.query.filter(
                Task.user_id == user_id,
                Task.status != '完了',
                Task.due_date != None,
                Task.due_date >= now,
                Task.due_date <= now + timedelta(days=3)
            ).order_by(Task.due_date.asc()).limit(5).all()

            for task in upcoming_tasks:
                time_diff = task.due_date - now
                task.days_remaining = time_diff.days
        except Exception as e:
            app.logger.error(f"Error fetching upcoming tasks for user_id {user_id}: {e}")
            flash("期限が近い課題の取得中にエラーが発生しました。", "danger")

    ai_recommendations = None
    api_key_set = False

    return render_template('dashboard.html',
                          user_email=user_email,
                          upcoming_tasks=upcoming_tasks,
                          ai_recommendations=ai_recommendations,
                          api_key_set=api_key_set)

@bp.route('/subjects', methods=['GET', 'POST'])
@login_required
def subjects():
    from app import create_app
    app = create_app()
    
    user_id = session['user_id']
    DEBUG_SKIP_LOGIN_CHECK = app.config.get('DEBUG_SKIP_LOGIN_CHECK', False)
    
    if user_id == 0 and DEBUG_SKIP_LOGIN_CHECK:
        flash("デバッグユーザーは教科管理を利用できません。", "warning")
        return redirect(url_for('routes.dashboard'))
        
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
        return redirect(url_for('routes.subjects'))
        
    user_subjects = Subject.query.filter_by(user_id=user_id).order_by(Subject.name).all()
    return render_template('subjects.html', subjects=user_subjects, show_dashboard_link=True)

@bp.route('/subjects/<int:subject_id>/delete', methods=['POST'])
@login_required
def delete_subject(subject_id):
    from app import create_app
    app = create_app()
    
    user_id = session['user_id']
    DEBUG_SKIP_LOGIN_CHECK = app.config.get('DEBUG_SKIP_LOGIN_CHECK', False)
    
    if user_id == 0 and DEBUG_SKIP_LOGIN_CHECK:
        flash("デバッグユーザーは教科削除を利用できません。", "warning")
        return redirect(url_for('routes.subjects'))
        
    subject_to_delete = Subject.query.get_or_404(subject_id)
    if subject_to_delete.owner.id != user_id:
        flash("権限なし", "danger")
        return redirect(url_for('routes.subjects'))
        
    try:
        db.session.delete(subject_to_delete)
        db.session.commit()
        flash(f"教科 '{subject_to_delete.name}' 削除", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"教科削除エラー: {e}", "danger")
        app.logger.error(f"Sub del err: {e}")
        
    return redirect(url_for('routes.subjects'))

@bp.route('/tasks')
@login_required
def tasks():
    user_id = session['user_id']
    user_tasks = []
    
    if user_id != 0:
        user_tasks = Task.query.filter_by(user_id=user_id).order_by(Task.due_date.asc().nullslast(), Task.priority).all()
        
    return render_template('tasks.html', tasks=user_tasks, show_dashboard_link=True)

@bp.route('/tasks/new', methods=['GET', 'POST'])
@login_required
def new_task():
    from app import create_app
    app = create_app()
    
    user_id = session['user_id']
    DEBUG_SKIP_LOGIN_CHECK = app.config.get('DEBUG_SKIP_LOGIN_CHECK', False)
    
    if user_id == 0 and DEBUG_SKIP_LOGIN_CHECK:
        flash("デバッグユーザーはタスクを追加できません。", "warning")
        return redirect(url_for('routes.dashboard'))

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
        if not title or title.strip() == "":
            error = "課題名は必須です。"
            
        period = None
        if period_str and period_str.strip() != "":
            if period_str.isdigit():
                period = int(period_str)
                if not (1 <= period <= 8):
                    if error is None:
                        error = "時間目は1から8の数値を入力してください。"
            else:
                if error is None:
                    error = "時間目は半角数値を入力してください。"
                    
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                if error is None:
                    error = "締切日時の形式が不正 (例: 2024-01-01T10:00)"
                    
        estimated_time = None
        if estimated_time_str and estimated_time_str.strip() != "":
            try:
                estimated_time = int(estimated_time_str)
                if estimated_time < 0:
                    if error is None:
                        error = "想定所要時間は0以上の数値を入力してください。"
            except ValueError:
                if error is None:
                    error = "想定所要時間は半角数値を入力してください。"

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
                user_id=user_id
            )
            try:
                db.session.add(new_task_obj)
                db.session.commit()
                flash('新しい課題が登録されました。', 'success')
                return redirect(url_for('routes.dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f"登録エラー: {e}", 'danger')
                app.logger.error(f"Task add err: {e}")
        else:
            flash(error, 'danger')
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
                                  show_dashboard_link=True)

    return render_template('new_task.html', subjects=user_subjects, show_dashboard_link=True)

@bp.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    from app import create_app
    app = create_app()
    
    user_id = session['user_id']
    task_to_edit = Task.query.get_or_404(task_id)
    DEBUG_SKIP_LOGIN_CHECK = app.config.get('DEBUG_SKIP_LOGIN_CHECK', False)

    if (user_id == 0 and DEBUG_SKIP_LOGIN_CHECK) or task_to_edit.author.id != user_id:
        flash("権限がありません。", "danger")
        return redirect(url_for('routes.dashboard'))

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
        if not title or title.strip() == "":
            error = "課題名は必須です。"
            
        period = None
        if period_str and period_str.strip() != "":
            if period_str.isdigit():
                period = int(period_str)
                if not (1 <= period <= 8):
                    if error is None:
                        error = "時間目は1から8の数値を入力してください。"
            else:
                if error is None:
                    error = "時間目は半角数値を入力してください。"
                    
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                if error is None:
                    error = "締切日時の形式が不正 (例: 2024-01-01T10:00)"
        else:
            due_date = None
            
        estimated_time = None
        if estimated_time_str and estimated_time_str.strip() != "":
            try:
                estimated_time = int(estimated_time_str)
                if estimated_time < 0:
                    if error is None:
                        error = "想定所要時間は0以上の数値を入力してください。"
            except ValueError:
                if error is None:
                    error = "想定所要時間は半角数値を入力してください。"
        else:
            estimated_time = None

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
                flash('課題が更新されました。', 'success')
                return redirect(url_for('routes.dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f"更新エラー: {e}", 'danger')
                app.logger.error(f"Task edit err: {e}")
        else:
            flash(error, 'danger')
            task_to_edit.title = title
            task_to_edit.subject_name = subject_name
            task_to_edit.period = period_str
            task_to_edit.due_date_str = due_date_str
            task_to_edit.priority = priority
            task_to_edit.status = status
            task_to_edit.estimated_time = estimated_time_str
            task_to_edit.details = details
            return render_template('edit_task.html', task=task_to_edit, subjects=user_subjects, show_dashboard_link=True)

    if task_to_edit.due_date:
        task_to_edit.due_date_str = task_to_edit.due_date.strftime('%Y-%m-%dT%H:%M')
    else:
        task_to_edit.due_date_str = ""

    return render_template('edit_task.html', task=task_to_edit, subjects=user_subjects, show_dashboard_link=True)

@bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    from app import create_app
    app = create_app()
    
    user_id = session['user_id']
    task_to_delete = Task.query.get_or_404(task_id)
    DEBUG_SKIP_LOGIN_CHECK = app.config.get('DEBUG_SKIP_LOGIN_CHECK', False)

    if (user_id == 0 and DEBUG_SKIP_LOGIN_CHECK) or task_to_delete.author.id != user_id:
        flash("権限がありません。", "danger")
        return redirect(url_for('routes.dashboard'))

    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        flash(f"課題 '{task_to_delete.title}' 削除", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"削除エラー: {e}", "danger")
        app.logger.error(f"Task del err: {e}")
        
    return redirect(url_for('routes.dashboard'))

@bp.route('/calendar')
@login_required
def calendar():
    from app import create_app
    app = create_app()
    
    user_id = session['user_id']
    DEBUG_SKIP_LOGIN_CHECK = app.config.get('DEBUG_SKIP_LOGIN_CHECK', False)
    
    if user_id == 0 and DEBUG_SKIP_LOGIN_CHECK:
        flash("デバッグユーザーはカレンダー機能のデータが制限されます。", "info")

    return render_template('calendar.html', show_dashboard_link=True)

@bp.route('/api/events')
@login_required
def api_events():
    from app import create_app
    app = create_app()
    
    user_id = session['user_id']
    events = []
    DEBUG_SKIP_LOGIN_CHECK = app.config.get('DEBUG_SKIP_LOGIN_CHECK', False)

    if user_id == 0 and DEBUG_SKIP_LOGIN_CHECK:
        app.logger.warning("API events request bypassed for debug user (user_id=0). Returning empty list.")
        return jsonify(events)

    try:
        user_tasks = Task.query.filter(
            Task.user_id == user_id,
            Task.due_date.isnot(None)
        ).order_by(Task.due_date).all()

        for task in user_tasks:
            event_color = None
            if task.status == '完了':
                event_color = 'grey'
            elif task.priority == '高':
                event_color = 'red'
            elif task.priority == '低':
                event_color = 'lightblue'

            event_title = task.title
            if task.subject_name:
                event_title = f"[{task.subject_name}] {task.title}"

            events.append({
                'id': task.id,
                'title': event_title,
                'start': task.due_date.isoformat(),
                'allDay': False,
                'description': task.details or '',
                'color': event_color,
                'extendedProps': {
                    'status': task.status,
                    'priority': task.priority,
                    'period': task.period,
                    'estimated_time': task.estimated_time,
                    'task_url': url_for('routes.edit_task', task_id=task.id)
                }
            })
        app.logger.info(f"API events: Found {len(events)} events for user_id={user_id}")

    except Exception as e:
        app.logger.error(f"Error fetching tasks for API events (user_id={user_id}): {e}")
        return jsonify({"error": "Failed to fetch events"}), 500

    return jsonify(events)

@bp.route('/settings', methods=['GET'])
@login_required
def settings():
    from app import create_app
    app = create_app()
    
    user_id = session['user_id']
    DEBUG_SKIP_LOGIN_CHECK = app.config.get('DEBUG_SKIP_LOGIN_CHECK', False)
    
    if user_id == 0 and DEBUG_SKIP_LOGIN_CHECK:
        flash("デバッグユーザーは設定を変更できません。", "warning")
        return redirect(url_for('routes.dashboard'))

    user = User.query.get(user_id)
    if not user:
        flash("ユーザー情報の取得に失敗しました。", "danger")
        session.clear()
        return redirect(url_for('routes.login'))
        
    return render_template('settings.html', user=user, show_dashboard_link=True)

@bp.route('/settings/change_password', methods=['POST'])
@login_required
def change_password():
    from app import create_app
    app = create_app()
    
    user_id = session['user_id']
    DEBUG_SKIP_LOGIN_CHECK = app.config.get('DEBUG_SKIP_LOGIN_CHECK', False)
    
    if user_id == 0 and DEBUG_SKIP_LOGIN_CHECK:
        flash("デバッグユーザーはパスワードを変更できません。", "warning")
        return redirect(url_for('routes.settings'))

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    user = User.query.get(user_id)
    error = None
    
    if not user:
        flash("ユーザー情報取得失敗", "danger")
        return redirect(url_for('routes.settings'))

    if not current_password:
        error = "現在のパスワードを入力してください。"
    elif not new_password:
        error = "新しいパスワードを入力してください。"
    elif len(new_password) < 6:
        error = "新しいパスワードは6文字以上で入力してください。"
    elif new_password != confirm_password:
        error = "新しいパスワードが一致しません。"
    elif not check_password_hash(user.password_hash, current_password):
        error = "現在のパスワードが正しくありません。"
        app.logger.warning(f"PW change fail: Incorrect current PW for {user.email}")

    if error:
        flash(error, 'danger')
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
            
    return redirect(url_for('routes.settings'))
