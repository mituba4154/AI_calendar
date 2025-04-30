import os
import logging
import click
from flask import Flask
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models import User
from app.config import Config

def create_app():
    """アプリケーションファクトリ"""
    app = Flask(
        __name__,
        static_folder='../static',
        template_folder='../templates'
    )

    # 設定の読み込み
    app.config.from_object(Config)

    # ロギング
    logging.basicConfig(level=logging.INFO)

    # データベース初期化
    db.init_app(app)

    # Blueprint登録
    from app.routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    # --- CLI: ユーザー作成 ---
    @app.cli.command("create-user")
    @click.argument("email")
    @click.password_option()
    def create_user(email, password):
        """メールアドレスとパスワードからユーザーを作成"""
        if '@' not in email:
            print("Error: 無効なメールアドレス形式です。")
            return
        if User.query.filter_by(email=email).first():
            print(f"Error: '{email}' は既に存在します。")
            return
        if len(password) < 6:
            print("Error: パスワードは6文字以上必要です。")
            return
        u = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(u)
        db.session.commit()
        print(f"Success: ユーザー '{email}' を作成しました。")

    # --- CLI: ユーザー削除 ---
    @app.cli.command("delete-user")
    @click.argument("email")
    def delete_user(email):
        """メールアドレス指定でユーザーを削除"""
        u = User.query.filter_by(email=email).first()
        if not u:
            print(f"Error: '{email}' は存在しません。")
            return
        db.session.delete(u)
        db.session.commit()
        print(f"Success: ユーザー '{email}' を削除しました。")

    # --- CLI: ユーザー一覧 ---
    @app.cli.command("list-users")
    def list_users():
        """登録済ユーザーの一覧を表示"""
        users = User.query.order_by(User.id).all()
        if not users:
            print("ユーザーが存在しません。")
            return
        print("ID   | Email")
        print("-----+------------------------")
        for u in users:
            print(f"{u.id:<4} | {u.email}")

    # 起動時にDBテーブル作成＆デバッグユーザー作成
    with app.app_context():
        db.create_all()
        if app.config.get('DEBUG_SKIP_LOGIN_CHECK'):
            dbg = app.config.get('DEBUG_SKIP_LOGIN_EMAIL')
            if not User.query.filter_by(email=dbg).first():
                pwd = generate_password_hash("debug")
                user = User(email=dbg, password_hash=pwd)
                db.session.add(user)
                db.session.commit()
                app.logger.warning(f"Debug user '{dbg}' created.")

    return app
