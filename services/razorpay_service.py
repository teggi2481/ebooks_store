import razorpay
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
