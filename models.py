from . import db
from flask_login import UserMixin
# ... अन्य इम्पोर्ट्स ...

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # ... मौजूदा फ़ील्ड्स ...
    plan_type = db.Column(db.String(50), default='free') # उदाहरण: free, premium
    plan_expiry_date = db.Column(db.DateTime, nullable=True)
    razorpay_order_id = db.Column(db.String(100), nullable=True)
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    razorpay_signature = db.Column(db.String(200), nullable=True)

    # ... मौजूदा मेथड्स ...