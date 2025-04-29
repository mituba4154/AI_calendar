from functools import wraps
from flask import session, redirect, url_for, request, flash, current_app
import logging

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 現在のアプリケーションコンテキストから設定を取得
        DEBUG_SKIP_LOGIN_CHECK = current_app.config.get('DEBUG_SKIP_LOGIN_CHECK', False)
        DEBUG_SKIP_LOGIN_EMAIL = current_app.config.get('DEBUG_SKIP_LOGIN_EMAIL', 'debug@example.com')
        
        # デバッグバイパスが有効なら常に通過
        if DEBUG_SKIP_LOGIN_CHECK and 'user_id' not in session:
            current_app.logger.warning(f"--- DEBUG MODE: Bypassing login_required for user_id check ---")
            
            # デバッグユーザー情報をセッションに入れる
            from app.models import User
            debug_user = User.query.filter_by(email=DEBUG_SKIP_LOGIN_EMAIL).first()
            session['user_id'] = debug_user.id if debug_user else 0
            session['user_email'] = DEBUG_SKIP_LOGIN_EMAIL
            current_app.logger.warning(f"--- DEBUG MODE: Set session user_id={session['user_id']}, email={session['user_email']} ---")

        if 'user_id' not in session:
            flash('ログインが必要です。', 'warning')
            return redirect(url_for('routes.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# その他のユーティリティ関数
def format_datetime(dt):
    """日時を指定された形式でフォーマットする"""
    if dt:
        return dt.strftime('%Y-%m-%d %H:%M')
    return ''

def is_valid_period(period_str):
    """時間目の値が有効かチェックする"""
    if not period_str or period_str.strip() == "":
        return True, None
    
    if not period_str.isdigit():
        return False, "時間目は半角数値を入力してください。"
    
    period = int(period_str)
    if not (1 <= period <= 8):
        return False, "時間目は1から8の数値を入力してください。"
    
    return True, period
