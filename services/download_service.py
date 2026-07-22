import secrets
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
