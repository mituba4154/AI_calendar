import os

class Config:
    # 基本設定
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_secret_key_should_be_changed_in_production')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # デバッグ関連の設定
    DEBUG_SKIP_LOGIN_CHECK = True  # 本番環境では必ずFalseにする
    DEBUG_SKIP_LOGIN_EMAIL = "debug@example.com"
    
    # ロギング設定
    LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    # サーバー設定
    HOST = '0.0.0.0'
    PORT = 53833
    DEBUG = False  # 本番環境ではFalseにする
    
    # セッション設定
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 86400  # セッション有効期間（秒）- デフォルト24時間
    
    # セキュリティ設定
    SESSION_COOKIE_SECURE = False  # HTTPSを使用する場合はTrueに設定
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
        pass

class DevelopmentConfig(Config):
    """開発環境用の設定"""
    DEBUG = True
    DEBUG_SKIP_LOGIN_CHECK = True  # 開発環境ではログインチェックをスキップ可能
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # 開発環境特有の設定を追加

class ProductionConfig(Config):
    """本番環境用の設定"""
    DEBUG = False
    DEBUG_SKIP_LOGIN_CHECK = False  # 本番環境ではログインチェックを必須に
    SESSION_COOKIE_SECURE = True  # HTTPSを使用する場合
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # 本番環境特有の設定を追加（例：エラーハンドリング）

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
