from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from utils.db_utils import get_db, get_all_users, get_user_id
from utils.email_utils import send_upgrade_confirmation

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

@admin_bp.before_request
def require_admin():
    if "user_logged_in" not in session or not session.get("is_admin"):
        session.clear()
        return redirect(url_for('user_bp.admin_login'))

@admin_bp.route("/")
def admin_panel():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.id, c.name, c.email, c.plan, c.created_at, COUNT(b.id) as total_apps
        FROM clients c LEFT JOIN bots b ON c.id = b.user_id
        GROUP BY c.id ORDER BY c.created_at DESC
    """)
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin_panel.html", users=users)

@admin_bp.route("/change-plan", methods=["POST"])
def change_user_plan():
    data = request.get_json()
    user_id = data["user_id"]
    plan = data["plan"]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET plan = %s WHERE id = %s", (plan, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success", "message": f"Plan updated to {plan}"})

@admin_bp.route("/delete-user/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bots WHERE user_id = %s", (user_id,))
    cursor.execute("DELETE FROM clients WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success", "message": "User deleted"})

@admin_bp.route("/requests")
def view_upgrade_requests():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, name, email, current_plan, requested_plan, message, created_at, status
        FROM upgrade_requests
        ORDER BY created_at DESC
    """)
    requests = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin_requests.html", requests=requests)

@admin_bp.route("/update-request", methods=["POST"])
def update_request_status():
    data = request.get_json()
    request_id = data["request_id"]
    new_status = data["status"]

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, requested_plan FROM upgrade_requests WHERE id = %s", (request_id,))
    request_data = cursor.fetchone()

    if not request_data:
        return jsonify({"status": "error", "message": "Request not found"}), 404

    user_id = request_data["user_id"]
    requested_plan = request_data["requested_plan"]

    cursor.execute("UPDATE upgrade_requests SET status = %s WHERE id = %s", (new_status, request_id))

    if new_status == "approved":
        cursor.execute("UPDATE clients SET plan = %s WHERE id = %s", (requested_plan, user_id))
        cursor.execute("SELECT email, name FROM clients WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if user:
            send_upgrade_confirmation(user["email"], user["name"], requested_plan)

    conn.commit()
    cursor.close()
    conn.close()

    msg = f"Request marked as {new_status}"
    if new_status == "approved":
        msg += f" and user upgraded to {requested_plan}"

    return jsonify({"status": "success", "message": msg})
