from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from .models import User # User मॉडल इम्पोर्ट करें
from . import db # db इम्पोर्ट करें
import razorpay
import json
from datetime import datetime, timedelta

user_bp = Blueprint('user_bp', __name__)

# Razorpay क्लाइंट इनिशियलाइज़ करें
def get_razorpay_client():
    client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))
    client.set_app_details({"title" : "Flask Multi User Bot Manager", "version" : "1.0"}) # ऐप का नाम और संस्करण बदलें
    return client

@user_bp.route("/login")
def login():
    if "google_id" in session:
        return redirect(url_for('user_bp.dashboard'))
    return render_template("select_login.html")

@user_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('user_bp.login'))

@user_bp.route("/post-login")
def post_login():
    if "google_id" not in session:
        return redirect(url_for('user_bp.login'))

    if not session.get("plan"):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT plan FROM clients WHERE google_id=%s", (session["google_id"],))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result and result[0]:
            session["plan"] = result[0]
        else:
            return redirect(url_for("user_bp.select_plan"))

    return redirect(url_for('user_bp.dashboard'))

@user_bp.route("/select-plan")
def select_plan():
    if "google_id" not in session:
        return redirect(url_for('user_bp.login'))
    return render_template("select_plan.html")

@user_bp.route("/choose-plan", methods=["POST"])
def choose_plan():
    if "google_id" not in session:
        return redirect(url_for('user_bp.login'))
    
    plan = request.form.get("plan")
    session['plan'] = plan

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET plan=%s WHERE google_id=%s", (plan, session['google_id']))
    conn.commit()
    cursor.close()
    conn.close()

    if plan == "enterprise":
        flash("Please contact us to activate Enterprise Plan.", "info")
    
    return redirect(url_for('user_bp.dashboard'))

@user_bp.route("/dashboard")
def dashboard():
    if "google_id" not in session:
        return redirect(url_for('user_bp.login'))

    user_id = session.get("user_id")
    apps = get_user_apps(user_id)  # Updated to load only user's apps

    plan = session.get("plan", "free") # डिफ़ॉल्ट रूप से 'free' प्लान मानें यदि सेशन में नहीं है
    # plan_limit = float('inf') if plan == "gold" else (10 if plan == "silver" else 3) # पुरानी हार्डकोडेड सीमा
    plan_limit = get_plan_limit(plan) # get_plan_limit फ़ंक्शन का उपयोग करें
    app_count = len(apps)
    is_infinite = math.isinf(plan_limit)

    return render_template(
        "dashboard.html",
        apps=apps,
        user_id=user_id,
        app_count=app_count,
        plan_limit=plan_limit,
        user_plan=plan,
        is_infinite=is_infinite,
        user_email=session.get("email")
    )

@user_bp.route('/pay/<plan_name>')
@login_required
def initiate_payment(plan_name):
    # प्लान के आधार पर राशि निर्धारित करें (उदाहरण)
    # आप इसे डेटाबेस या कॉन्फ़िगरेशन से प्राप्त कर सकते हैं
    if plan_name == 'premium':
        amount_in_paise = 50000 # उदाहरण: ₹500.00 (राशि पैसे में होनी चाहिए)
        plan_display_name = "Premium Plan"
    # elif plan_name == 'another_plan':
    #     amount_in_paise = 100000 # उदाहरण: ₹1000.00
    #     plan_display_name = "Another Plan"
    else:
        flash('Invalid plan selected.', 'danger')
        return redirect(url_for('user_bp.dashboard')) # या प्लान चयन पेज पर

    client = get_razorpay_client()

    # Razorpay ऑर्डर बनाएं
    order_data = {
        'amount': amount_in_paise,
        'currency': 'INR',
        'receipt': f'order_rcptid_{current_user.id}_{int(datetime.now().timestamp())}', # एक यूनिक रसीद ID बनाएं
        'payment_capture': 1 # ऑटो कैप्चर
    }
    try:
        order = client.order.create(data=order_data)
        # ऑर्डर ID को यूजर के साथ अस्थायी रूप से स्टोर करें (वैकल्पिक, यदि आवश्यक हो)
        # current_user.razorpay_order_id = order['id']
        # db.session.commit()
    except Exception as e:
        flash(f'Error creating Razorpay order: {e}', 'danger')
        return redirect(url_for('user_bp.dashboard'))

    # पेमेंट पेज पर भेजने के लिए डेटा तैयार करें
    payment_data = {
        'key': current_app.config['RAZORPAY_KEY_ID'],
        'amount': order['amount'],
        'currency': order['currency'],
        'name': 'Your App Name', # अपनी ऐप का नाम डालें
        'description': f'Payment for {plan_display_name}',
        'order_id': order['id'],
        'callback_url': url_for('user_bp.payment_success', _external=True), # पेमेंट सफलता कॉलबैक URL
        'prefill': {
            'name': current_user.username, # या यूजर का पूरा नाम
            'email': current_user.email,
            # 'contact': 'USER_PHONE_NUMBER' # यदि उपलब्ध हो
        },
        'theme': {
            'color': '#3399cc'
        }
    }

    return render_template('payment.html', payment_data=payment_data, plan_name=plan_name)


@user_bp.route('/payment/success', methods=['POST'])
@login_required
def payment_success():
    client = get_razorpay_client()
    try:
        # फॉर्म डेटा से पेमेंट डिटेल्स प्राप्त करें
        payment_id = request.form.get('razorpay_payment_id')
        order_id = request.form.get('razorpay_order_id')
        signature = request.form.get('razorpay_signature')
        plan_name = request.form.get('plan_name') # यह हिडन फील्ड से आएगा

        if not all([payment_id, order_id, signature, plan_name]):
             flash('Payment data missing.', 'danger')
             return redirect(url_for('user_bp.dashboard'))

        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }

        # सिग्नेचर वेरीफाई करें
        client.utility.verify_payment_signature(params_dict)

        # सिग्नेचर सफल होने पर:
        user = User.query.get(current_user.id)
        user.razorpay_payment_id = payment_id
        user.razorpay_order_id = order_id
        user.razorpay_signature = signature

        # यूजर का प्लान अपडेट करें
        if plan_name == 'premium':
            user.plan_type = 'premium'
            # समाप्ति तिथि सेट करें (उदाहरण: 30 दिन)
            user.plan_expiry_date = datetime.utcnow() + timedelta(days=30)
        # elif plan_name == 'another_plan':
            # user.plan_type = 'another_plan'
            # user.plan_expiry_date = datetime.utcnow() + timedelta(days=90) # उदाहरण

        db.session.commit()

        flash('Payment Successful! Your plan has been upgraded.', 'success')
        return redirect(url_for('user_bp.dashboard'))

    except razorpay.errors.SignatureVerificationError as e:
        # सिग्नेचर विफल होने पर:
        flash('Payment verification failed. Please contact support.', 'danger')
        # आप चाहें तो यहाँ पेमेंट डिटेल्स लॉग कर सकते हैं
        print(f"Signature Verification Failed: {e}")
        return redirect(url_for('user_bp.dashboard')) # या पेमेंट पेज पर वापस भेजें
    except Exception as e:
        flash(f'An error occurred during payment processing: {e}', 'danger')
        print(f"Payment Processing Error: {e}")
        return redirect(url_for('user_bp.dashboard'))
