from app import create_app
from app.config import Config

app = create_app()

if __name__ == '__main__':
    if Config.DEBUG_SKIP_LOGIN_CHECK:
        app.logger.critical("!!! DEBUG LOGIN BYPASS ENABLED !!!")
        app.logger.warning(f"!!! Debug User Email: {Config.DEBUG_SKIP_LOGIN_EMAIL} !!!")
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
