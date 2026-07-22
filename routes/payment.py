import time
import razorpay
from flask import Blueprint, request, jsonify, render_template, current_app
from models import db
from models.ebook import EBook
from models.order import Order
from services.razorpay_service import RazorpayService
from services.download_service import DownloadService

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

def get_razorpay_client():
    key_id = current_app.config.get('RAZORPAY_KEY_ID')
    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')

    # Sanity Check Log
    if not key_id or not key_secret:
        print("❌ CRITICAL: Razorpay Key ID or Secret is missing in Flask config!")
    else:
        print(f"🔑 Initializing Razorpay with Key ID: {key_id[:8]}...")

    #return razorpay.Client(auth=(key_id, key_secret))
    return razorpay.Client(auth=("rzp_test_TGAamt9Vc8ZQps", "QpnNslcv9zteK2pAFXj2ofmQ"))

@payment_bp.route('/create-order', methods=['POST'])
def create_order():
    try:
        data = request.get_json() or {}
        ebook_id = data.get('ebook_id')

        ebook = EBook.query.get(ebook_id)
        if not ebook:
            return jsonify({'error': 'E-book not found'}), 404

        # Convert price to paise (e.g. ₹499 -> 49900)
        amount_in_paise = int(float(ebook.price) * 100)

        # Create order with Razorpay SDK
        order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'receipt': f'order_{ebook_id}_{int(time.time())}'
        }
        print(order_data)
        razorpay_order = get_razorpay_client().order.create(data=order_data)

        return jsonify({
            'status': 'success',
            'razorpay_order_id': razorpay_order['id'],
            'amount': razorpay_order['amount'],
            'currency': razorpay_order['currency']
        }), 200

    except Exception as e:
        # Catch errors so Flask returns JSON instead of an HTML 500 error page
        print(f"Error creating Razorpay order: {e}")
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
