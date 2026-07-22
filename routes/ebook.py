from flask import Blueprint, render_template, abort, send_from_directory, current_app
from models.ebook import EBook
from models.order import Order
from pathlib import Path

ebook_bp = Blueprint('ebook', __name__)


#@ebook_bp.route('/ebook/<int:ebook_id>')
#def details(ebook_id):
#    ebook = EBook.query.get_or_404(ebook_id)
#    return render_template('ebook_details.html', ebook=ebook, razorpay_key=current_app.config['RAZORPAY_KEY_ID'])

@ebook_bp.route('/ebook/<int:ebook_id>')
def details(ebook_id):
    ebook = EBook.query.get_or_404(ebook_id)
    return render_template(
        'ebook_details.html',
        ebook=ebook,
        razorpay_key_id=current_app.config.get('RAZORPAY_KEY_ID')
    )

@ebook_bp.route('/download/<token>')
def download_file(token):
    order = Order.query.filter_by(download_token=token, status='PAID').first_or_404()
    ebook = EBook.query.get_or_404(order.ebook_id)
    
    file_path = Path(ebook.file_path)
    directory = file_path.parent
    filename = file_path.name
    
    return send_from_directory(directory=directory, path=filename, as_attachment=True, download_name=f"{ebook.title}.pdf")
