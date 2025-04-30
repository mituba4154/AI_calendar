import os
import logging

class Config:
    # 基本設定
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_secret_key_should_be_changed_in_production')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # デバッグ関連の設定
    DEBUG_SKIP_LOGIN_CHECK = False  # 本番環境では必ずFalseにする
    DEBUG_SKIP_LOGIN_EMAIL = "debug@example.com"
    
    # ロギング設定
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    LOG_FILE = 'logs/app.log'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # サーバー設定
    HOST = '0.0.0.0'
    PORT = 53833
    DEBUG = False  # 本番環境ではFalseにする
    
    # セッション設定
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 86400  # セッション有効期間（秒）- デフォルト24時間
    
    # セキュリティ設定
    SESSION_COOKIE_SECURE = True  # HTTPSを使用する場合はTrueに設定
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # 将来のAPI統合用設定
    # API_KEY_REQUIRED = True
    # DEFAULT_API_TIMEOUT = 30  # 秒
    
    # 機能フラグ
    # ENABLE_AI_FEATURES = False  # AI機能を有効にするか
    # ENABLE_CALENDAR_SYNC = False  # カレンダー同期機能を有効にするか
    
    @staticmethod
    def init_app(app):
        """アプリケーション固有の追加設定を行うメソッド"""
        # ログディレクトリの作成
        os.makedirs('logs', exist_ok=True)
        
        # ログハンドラの設定
        formatter = logging.Formatter(
            Config.LOG_FORMAT,
            Config.LOG_DATE_FORMAT
        )
        
        # ファイルハンドラ
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # コンソールハンドラ
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # アプリケーションロガーの設定
        app.logger.addHandler(file_handler)
        app.logger.addHandler(console_handler)
        app.logger.setLevel(getattr(logging, Config.LOG_LEVEL))

class DevelopmentConfig(Config):
    """開発環境用の設定"""
    DEBUG = True
    DEBUG_SKIP_LOGIN_CHECK = True
    LOG_LEVEL = 'DEBUG'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        app.logger.info('Development environment initialized')

class ProductionConfig(Config):
    """本番環境用の設定"""
    DEBUG = False
    DEBUG_SKIP_LOGIN_CHECK = False
    SESSION_COOKIE_SECURE = True
    LOG_LEVEL = 'INFO'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # 本番環境特有のエラーハンドリング
        import logging
        from logging.handlers import SMTPHandler
        
        # メールによるエラー通知（設定されている場合のみ）
        mail_handler = SMTPHandler(
            mailhost=(os.environ.get('MAIL_SERVER', 'localhost'),
                     int(os.environ.get('MAIL_PORT', 25))),
            fromaddr=os.environ.get('MAIL_SENDER'),
            toaddrs=[os.environ.get('ADMIN_EMAIL')],
            subject='アプリケーションエラー'
        )
        mail_handler.setLevel(logging.ERROR)
        mail_handler.setFormatter(logging.Formatter('''
Message Type: %(levelname)s
Location: %(pathname)s:%(lineno)d
Module: %(module)s
Function: %(funcName)s
Time: %(asctime)s

Message:
%(message)s
'''))
        if os.environ.get('MAIL_SERVER'):
            app.logger.addHandler(mail_handler)
        
        app.logger.info('Production environment initialized')

class TestingConfig(Config):
    """テスト環境用の設定"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # インメモリDBを使用
    WTF_CSRF_ENABLED = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # テスト環境特有の設定を追加

# 設定の辞書
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
