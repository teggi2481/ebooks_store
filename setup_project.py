import os
import zipfile

project_dir = "datamindslab-ebook-store"

files = {}

# config.py
files["config.py"] = '''import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-this")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'database' / 'ebooks.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    EBOOK_UPLOAD_FOLDER = UPLOAD_FOLDER / "ebooks"
    COVER_UPLOAD_FOLDER = UPLOAD_FOLDER / "covers"
    
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_dummy_key_id")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "dummy_secret_key")
    
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
'''

# .env
files[".env"] = '''SECRET_KEY=dev-secret-key-12345
DATABASE_URL=sqlite:///database/ebooks.db
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
'''

# requirements.txt
files["requirements.txt"] = '''Flask==3.0.2
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.5
razorpay==1.4.1
python-dotenv==1.0.1
Werkzeug==3.0.1
Pillow==10.2.0
'''

# models/__init__.py
files["models/__init__.py"] = '''from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
'''

# models/ebook.py
files["models/ebook.py"] = '''from models import db
from datetime import datetime

class EBook(db.Model):
    __tablename__ = 'ebooks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    cover_image = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', backref='ebook', lazy=True)
'''

# models/order.py
files["models/order.py"] = '''from models import db
from datetime import datetime
import uuid

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    ebook_id = db.Column(db.Integer, db.ForeignKey('ebooks.id'), nullable=False)
    customer_name = db.Column(db.String(255), nullable=False)
    customer_email = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    razorpay_order_id = db.Column(db.String(255), nullable=True)
    razorpay_payment_id = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default='PENDING')
    download_token = db.Column(db.String(64), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
'''

# services/razorpay_service.py
files["services/razorpay_service.py"] = '''import razorpay
from flask import current_app

class RazorpayService:
    @staticmethod
    def get_client():
        return razorpay.Client(auth=(
            current_app.config['RAZORPAY_KEY_ID'],
            current_app.config['RAZORPAY_KEY_SECRET']
        ))

    @classmethod
    def create_order(cls, amount, currency="INR", receipt=None):
        client = cls.get_client()
        data = {
            "amount": int(amount * 100),
            "currency": currency,
            "receipt": receipt,
            "payment_capture": "1"
        }
        return client.order.create(data=data)

    @classmethod
    def verify_signature(cls, params_dict):
        client = cls.get_client()
        try:
            client.utility.verify_payment_signature(params_dict)
            return True
        except razorpay.errors.SignatureVerificationError:
            return False
'''

# services/download_service.py
files["services/download_service.py"] = '''import secrets
from models import db
from models.order import Order

class DownloadService:
    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)

    @staticmethod
    def attach_download_token(order_id):
        order = Order.query.get(order_id)
        if order and not order.download_token:
            order.download_token = DownloadService.generate_token()
            db.session.commit()
        return order.download_token if order else None
'''

# routes/home.py
files["routes/home.py"] = '''from flask import Blueprint, render_template, request
from models.ebook import EBook

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def index():
    search_query = request.args.get('q', '').strip()
    if search_query:
        ebooks = EBook.query.filter(
            (EBook.title.ilike(f'%{search_query}%')) | 
            (EBook.author.ilike(f'%{search_query}%')) |
            (EBook.description.ilike(f'%{search_query}%'))
        ).all()
    else:
        ebooks = EBook.query.order_by(EBook.created_at.desc()).all()
    return render_template('index.html', ebooks=ebooks, search_query=search_query)
'''

# routes/ebook.py
files["routes/ebook.py"] = '''from flask import Blueprint, render_template, abort, send_from_directory, current_app
from models.ebook import EBook
from models.order import Order
from pathlib import Path

ebook_bp = Blueprint('ebook', __name__)

@ebook_bp.route('/ebook/<int:ebook_id>')
def details(ebook_id):
    ebook = EBook.query.get_or_404(ebook_id)
    return render_template('ebook_details.html', ebook=ebook, razorpay_key=current_app.config['RAZORPAY_KEY_ID'])

@ebook_bp.route('/download/<token>')
def download_file(token):
    order = Order.query.filter_by(download_token=token, status='PAID').first_or_404()
    ebook = EBook.query.get_or_404(order.ebook_id)
    
    file_path = Path(ebook.file_path)
    directory = file_path.parent
    filename = file_path.name
    
    return send_from_directory(directory=directory, path=filename, as_attachment=True, download_name=f"{ebook.title}.pdf")
'''

# routes/payment.py
files["routes/payment.py"] = '''from flask import Blueprint, request, jsonify, render_template, current_app
from models import db
from models.ebook import EBook
from models.order import Order
from services.razorpay_service import RazorpayService
from services.download_service import DownloadService

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/create-order', methods=['POST'])
def create_order():
    data = request.json
    ebook_id = data.get('ebook_id')
    name = data.get('name')
    email = data.get('email')

    if not all([ebook_id, name, email]):
        return jsonify({'error': 'Missing required fields'}), 400

    ebook = EBook.query.get_or_404(ebook_id)

    try:
        rzp_order = RazorpayService.create_order(amount=ebook.price, receipt=f"rcpt_{ebook.id}")
        
        order = Order(
            ebook_id=ebook.id,
            customer_name=name,
            customer_email=email,
            amount=ebook.price,
            razorpay_order_id=rzp_order['id'],
            status='PENDING'
        )
        db.session.add(order)
        db.session.commit()

        return jsonify({
            'order_id': rzp_order['id'],
            'amount': rzp_order['amount'],
            'currency': rzp_order['currency'],
            'key': current_app.config['RAZORPAY_KEY_ID']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payment_bp.route('/verify-payment', methods=['POST'])
def verify_payment():
    data = request.json
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')

    order = Order.query.filter_by(razorpay_order_id=razorpay_order_id).first_or_404()

    verification_params = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    if RazorpayService.verify_signature(verification_params):
        order.status = 'PAID'
        order.razorpay_payment_id = razorpay_payment_id
        token = DownloadService.attach_download_token(order.id)
        db.session.commit()
        return jsonify({'status': 'success', 'download_token': token})
    else:
        order.status = 'FAILED'
        db.session.commit()
        return jsonify({'status': 'failed', 'message': 'Invalid signature'}), 400

@payment_bp.route('/payment-success/<token>')
def success(token):
    order = Order.query.filter_by(download_token=token, status='PAID').first_or_404()
    ebook = EBook.query.get_or_404(order.ebook_id)
    return render_template('payment_success.html', order=order, ebook=ebook)
'''

# routes/admin.py
files["routes/admin.py"] = '''from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from models import db
from models.ebook import EBook
from models.order import Order

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def is_admin_logged_in():
    return session.get('admin_logged_in', False)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == current_app.config['ADMIN_USERNAME'] and password == current_app.config['ADMIN_PASSWORD']:
            session['admin_logged_in'] = True
            flash('Successfully logged in as Admin', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully', 'info')
    return redirect(url_for('admin.login'))

@admin_bp.route('/dashboard')
def dashboard():
    if not is_admin_logged_in():
        return redirect(url_for('admin.login'))
    
    ebooks = EBook.query.order_by(EBook.created_at.desc()).all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    total_revenue = sum(o.amount for o in orders if o.status == 'PAID')
    
    return render_template('admin/dashboard.html', ebooks=ebooks, orders=orders, total_revenue=total_revenue)

@admin_bp.route('/add-ebook', methods=['GET', 'POST'])
def add_ebook():
    if not is_admin_logged_in():
        return redirect(url_for('admin.login'))

    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        price = float(request.form.get('price'))

        cover_file = request.files.get('cover_image')
        pdf_file = request.files.get('ebook_file')

        if cover_file and pdf_file:
            cover_filename = secure_filename(cover_file.filename)
            pdf_filename = secure_filename(pdf_file.filename)

            cover_path = current_app.config['COVER_UPLOAD_FOLDER'] / cover_filename
            pdf_path = current_app.config['EBOOK_UPLOAD_FOLDER'] / pdf_filename

            cover_file.save(cover_path)
            pdf_file.save(pdf_path)

            new_ebook = EBook(
                title=title,
                author=author,
                description=description,
                price=price,
                cover_image=f"covers/{cover_filename}",
                file_path=str(pdf_path)
            )
            db.session.add(new_ebook)
            db.session.commit()

            flash('EBook uploaded successfully!', 'success')
            return redirect(url_for('admin.dashboard'))

    return render_template('admin/add_ebook.html')
'''

# app.py
files["app.py"] = '''import os
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
'''

# Write files directly to disk
for filepath, content in files.items():
    full_path = os.path.join(project_dir, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"🎉 Success! Created full project folder '{project_dir}' with all files.")