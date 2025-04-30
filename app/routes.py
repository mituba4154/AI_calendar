from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify, current_app
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from app.extensions import db
from app.models import User, Subject, Task
from app.utils import login_required

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

@bp.route('/subjects', methods=['GET','POST'])
@login_required
def subjects():
    uid=session['user_id']
    if request.method=='POST':
        name=request.form.get('subject_name','').strip()
        if name:
            if not Subject.query.filter_by(user_id=uid,name=name).first():
                db.session.add(Subject(name=name,user_id=uid))
                db.session.commit()
                flash(f"教科 '{name}' 登録","success")
            else:
                flash("既に登録済","warning")
        else:
            flash("教科名を入力","warning")
        return redirect(url_for('routes.subjects'))
    subs=Subject.query.filter_by(user_id=uid).order_by(Subject.name).all()
    return render_template('subjects.html', subjects=subs)

@bp.route('/subjects/<int:subject_id>/delete', methods=['POST'])
@login_required
def delete_subject(subject_id):
    uid=session['user_id']
    sub=Subject.query.get_or_404(subject_id)
    if sub.user_id!=uid:
        flash("権限なし","danger")
    else:
        db.session.delete(sub); db.session.commit()
        flash(f"教科 '{sub.name}' 削除","success")
    return redirect(url_for('routes.subjects'))

@bp.route('/tasks')
@login_required
def tasks():
    uid=session['user_id']
    ts = Task.query.filter_by(user_id=uid).order_by(
        Task.due_date.asc().nullslast(), Task.priority
    ).all() if uid!=0 else []
    return render_template('tasks.html', tasks=ts)

@bp.route('/tasks/new', methods=['GET','POST'])
@login_required
def new_task():
    uid = session['user_id']
    subs = Subject.query.filter_by(user_id=uid).order_by(Subject.name).all()
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        subject_name = request.form.get('subject_name','').strip()
        period = request.form.get('period') or None
        due_date_str = request.form.get('due_date') or None
        due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M') if due_date_str else None
        priority = request.form.get('priority','中')
        status = request.form.get('status','未着手')
        est_time = request.form.get('estimated_time') or None
        details = request.form.get('details','').strip()
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
        flash("新しい課題が登録されました。", "success")
        return redirect(url_for('routes.dashboard'))
    return render_template('new_task.html', subjects=subs)

@bp.route('/tasks/<int:task_id>/edit', methods=['GET','POST'])
@login_required
def edit_task(task_id):
    task=Task.query.get_or_404(task_id)
    uid=session['user_id']
    if task.user_id!=uid:
        flash("権限なし","danger")
        return redirect(url_for('routes.dashboard'))
    subs=Subject.query.filter_by(user_id=uid).order_by(Subject.name).all()
    if request.method=='POST':
        task.title        = request.form.get('title','').strip()
        task.subject_name = request.form.get('subject_name','').strip()
        per              = request.form.get('period') or None
        task.period      = int(per) if per else None
        ds               = request.form.get('due_date') or None
        task.due_date    = datetime.strptime(ds, '%Y-%m-%dT%H:%M') if ds else None
        task.priority    = request.form.get('priority','中')
        task.status      = request.form.get('status','未着手')
        et               = request.form.get('estimated_time') or None
        task.estimated_time = int(et) if et else None
        task.details     = request.form.get('details','').strip()
        db.session.commit()
        flash("課題が更新されました。","success")
        return redirect(url_for('routes.dashboard'))
    task.due_date_str = task.due_date.strftime('%Y-%m-%dT%H:%M') if task.due_date else ''
    return render_template('edit_task.html', task=task, subjects=subs)

@bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task=Task.query.get_or_404(task_id)
    uid=session['user_id']
    if task.user_id!=uid:
        flash("権限なし","danger")
    else:
        db.session.delete(task); db.session.commit()
        flash(f"課題 '{task.title}' 削除","success")
    return redirect(url_for('routes.dashboard'))

@bp.route('/calendar')
@login_required
def calendar():
    return render_template('calendar.html')

@bp.route('/api/events')
@login_required
def api_events():
    uid=session['user_id']
    events=[]
    for t in Task.query.filter_by(user_id=uid).filter(Task.due_date!=None).all():
        events.append({
            'id':t.id,
            'title':f"[{t.subject_name}] {t.title}" if t.subject_name else t.title,
            'start':t.due_date.isoformat(),
            'color': None,
            'extendedProps': {
                'status':t.status, 'priority':t.priority,
                'description':t.details or ''
            }
        })
    return jsonify(events)

@bp.route('/settings', methods=['GET'])
@login_required
def settings():
    user=User.query.get(session['user_id'])
    return render_template('settings.html', user=user, api_key_is_set=False)

@bp.route('/settings/change_password', methods=['POST'])
@login_required
def change_password():
    user=User.query.get(session['user_id'])
    cur=request.form.get('current_password','')
    new=request.form.get('new_password','')
    con=request.form.get('confirm_password','')
    if not check_password_hash(user.password_hash,cur):
        flash("現在のパスワードが違います。","danger")
    elif len(new)<6:
        flash("新しいパスワードは6文字以上必要です。","danger")
    elif new!=con:
        flash("確認パスワードが一致しません。","danger")
    else:
        user.password_hash=generate_password_hash(new)
        db.session.commit()
        flash("パスワードを変更しました。","success")
    return redirect(url_for('routes.settings'))
