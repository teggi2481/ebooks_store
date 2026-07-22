from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
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
