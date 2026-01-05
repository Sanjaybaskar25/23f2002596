from flask import Flask
from datetime import datetime
from controllers.auth import auth_bp
from controllers.admin_routes import admin_bp
from controllers.user import user_bp
from database import init_db
import os

def create_app():
    app = Flask(__name__)
    app.secret_key = 'supersecretkey'
    
    @app.template_filter('datetimeformat')
    def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return value
        return value.strftime(format)

    if not os.path.exists('instance'):
        os.makedirs('instance')

    init_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_bp, url_prefix='/user')

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)