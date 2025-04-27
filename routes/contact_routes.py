from flask import Blueprint, render_template, request, redirect, url_for, session
# Import the new helper function and remove get_user_plan if only used for limit calculation here
from utils.db_utils import get_db, get_user_id, get_user_plan, get_user_apps, get_latest_upgrade_request, get_plan_limit

contact_bp = Blueprint('contact_bp', __name__)

@contact_bp.route("/profile")
def profile():
    if "user_logged_in" not in session:
        return redirect(url_for("user_bp.login"))

    google_id = session["google_id"]
    user_id = get_user_id(google_id)
    name = session.get("name", "User")
    email = session["email"]
    user_plan = get_user_plan(google_id) # Keep this to display the plan name
    apps = get_user_apps(user_id)
    app_count = len(apps)
    # Use the helper function to get the limit
    plan_limit = get_plan_limit(user_plan)

    upgrade_request = get_latest_upgrade_request(user_id)

    return render_template("profile.html",
        name=name,
        email=email,
        user_plan=user_plan,
        app_count=app_count,
        plan_limit=plan_limit,
        upgrade_request=upgrade_request
    )

@contact_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if "user_logged_in" not in session:
        return redirect(url_for("user_bp.login"))

    google_id = session["google_id"]
    user_id = get_user_id(google_id)
    name = session.get("name", "User")
    email = session["email"]
    current_plan = get_user_plan(google_id) # Keep this

    latest = get_latest_upgrade_request(user_id)

    if request.method == "POST":
        if latest and latest["status"] == "pending":
            return render_template("contact.html", error="⏳ Your previous request is still pending.", current_plan=current_plan)

        requested_plan = request.form["requested_plan"]
        message = request.form["message"]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO upgrade_requests (user_id, name, email, current_plan, requested_plan, message, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (user_id, name, email, current_plan, requested_plan, message))
        conn.commit()
        cursor.close()
        conn.close()

        return render_template("contact.html", success=True)

    return render_template("contact.html", current_plan=current_plan) # Keep passing current_plan
