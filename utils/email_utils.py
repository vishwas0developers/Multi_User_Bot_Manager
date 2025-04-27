from flask_mail import Mail, Message
import os

mail = Mail()

def init_mail(app):
    app.config.update(
        MAIL_SERVER=os.getenv("MAIL_SERVER"),
        MAIL_PORT=int(os.getenv("MAIL_PORT")),
        MAIL_USE_TLS=os.getenv("MAIL_USE_TLS") == "True",
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    )
    mail.init_app(app)

def send_upgrade_confirmation(email, name, plan):
    msg = Message(
        subject="✅ Your Plan Has Been Upgraded!",
        sender=os.getenv("MAIL_USERNAME"),
        recipients=[email],
    )
    msg.body = f"""
Hi {name},

Your upgrade request has been approved. 🎉

✅ New Plan: {plan.capitalize()}
📦 Upload Limit: {plan_limit_display(plan)}

You can now upload more apps at:
👉 https://bot.online2study.in/dashboard

Thanks for being with us!
- Team Online2Study
"""
    mail.send(msg)

def plan_limit_display(plan):
    limits = {"free": 2, "silver": 10, "gold": "Unlimited"}
    return limits.get(plan, "Unknown")
