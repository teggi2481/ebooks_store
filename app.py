import os
from flask import Flask, send_from_directory
from config import Config
from models import db
from routes.home import home_bp
from routes.ebook import ebook_bp
from routes.payment import payment_bp
from routes.admin import admin_bp
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config['EBOOK_UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['COVER_UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')), exist_ok=True)

    db.init_app(app)

    app.register_blueprint(home_bp)
    app.register_blueprint(ebook_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(admin_bp)

    @app.route('/uploads/covers/<filename>')
    def uploaded_cover(filename):
        return send_from_directory(app.config['COVER_UPLOAD_FOLDER'], filename)

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
