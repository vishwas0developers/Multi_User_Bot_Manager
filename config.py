import os

class Config:
    # ... अन्य कॉन्फ़िगरेशन ...
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID') or 'YOUR_KEY_ID' # अपना Key ID यहाँ डालें या एनवायरनमेंट वेरिएबल सेट करें
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET') or 'YOUR_KEY_SECRET' # अपना Key Secret यहाँ डालें या एनवायरनमेंट वेरिएबल सेट करें