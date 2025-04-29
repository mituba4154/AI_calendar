from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import logging
import os
import click
from werkzeug.security import generate_password_hash

# データベースオブジェクトを初期化（循環インポート回避のため先に定義）
db = SQLAlchemy()

def create_app():
    """アプリケーションファクトリ関数：設定を読み込み、Flaskアプリを作成して返す"""
    app = Flask(__name__, static_folder='../static', template_folder='../templates')
    
    # 設定の読み込み
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key_should_be_changed_in_production')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 設定ファイルからの追加設定読み込み
    from app.config import Config
    app.config.from_object(Config)
    
    # ロギング設定
    logging.basicConfig(level=logging.INFO)
    
    # データベースの初期化
    db.init_app(app)
    
    # ルーティングの登録
    from app.routes import bp as routes_bp
    app.register_blueprint(routes_bp)
    
    # モデルのインポート（循環インポート回避のためここで）
    from app.models import User, Subject, Task
    
    # CLIコマンドを登録
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
            return
            
        hashed_password = generate_password_hash(password)
        new_user = User(email=email, password_hash=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            print(f"Success: ユーザー '{email}' が作成されました。")
        except Exception as e:
            db.session.rollback()
            print(f"Error: ユーザー作成中にエラーが発生しました - {e}")
    
    # 起動時にデータベースの作成と確認
    with app.app_context():
        db.create_all()
        app.logger.info("--- Database tables checked/created (if necessary) ---")
        
        # デバッグユーザー作成ロジック
        DEBUG_SKIP_LOGIN_CHECK = app.config.get('DEBUG_SKIP_LOGIN_CHECK', False)
        DEBUG_SKIP_LOGIN_EMAIL = app.config.get('DEBUG_SKIP_LOGIN_EMAIL', 'debug@example.com')
        
        if DEBUG_SKIP_LOGIN_CHECK and not User.query.filter_by(email=DEBUG_SKIP_LOGIN_EMAIL).first():
            app.logger.warning(f"--- Creating default debug user: {DEBUG_SKIP_LOGIN_EMAIL} ---")
            try:
                hashed_password = generate_password_hash("debug")
                debug_user = User(email=DEBUG_SKIP_LOGIN_EMAIL, password_hash=hashed_password)
                db.session.add(debug_user)
                db.session.commit()
                app.logger.info(f"--- Default debug user created successfully. ---")
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"--- Error creating default debug user: {e} ---")
        
        # DEBUG_SKIP_LOGIN_CHECKが有効な場合は警告ログを出力
        if DEBUG_SKIP_LOGIN_CHECK:
            app.logger.critical("!!! DEBUG LOGIN BYPASS ENABLED !!!")
            app.logger.warning(f"!!! Debug User Email: {DEBUG_SKIP_LOGIN_EMAIL} !!!")
    
    # アプリケーションオブジェクトを返す
    return app
