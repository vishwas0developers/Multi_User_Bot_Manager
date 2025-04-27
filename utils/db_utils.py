import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME")
    )

def get_user_id(google_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM clients WHERE google_id = %s", (google_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result["id"] if result else None

def get_user_plan(google_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT plan FROM clients WHERE google_id = %s", (google_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result["plan"] if result else "free"

def get_all_users():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, google_id FROM clients")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

def get_latest_upgrade_request(user_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT requested_plan, status, created_at 
        FROM upgrade_requests 
        WHERE user_id = %s 
        ORDER BY created_at DESC LIMIT 1
    """, (user_id,))
    request = cursor.fetchone()
    cursor.close()
    conn.close()
    return request

def save_bot_to_db(button_name, folder_name, image_url):
    from utils.upload_utils import get_user_paths
    from flask import session
    conn = get_db()
    cursor = conn.cursor()
    google_id = session.get("google_id")
    user_id = get_user_id(google_id)
    cursor.execute(
        "INSERT INTO bots (user_id, button_name, folder_name, image_url) VALUES (%s, %s, %s, %s)",
        (user_id, button_name, folder_name, image_url)
    )
    conn.commit()
    cursor.close()
    conn.close()

def update_button_metadata(google_id, folder_name, new_button_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE bots SET button_name = %s WHERE folder_name = %s AND user_id = (SELECT id FROM clients WHERE google_id = %s)",
        (new_button_name, folder_name, google_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

def update_user_plan(google_id, plan_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET plan = %s WHERE google_id = %s", (plan_name, google_id))
    conn.commit()
    cursor.close()
    conn.close()

def get_user_apps(user_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    # Ensure user_id is passed correctly as a tuple even if it's a single value
    cursor.execute("SELECT * FROM bots WHERE user_id=%s ORDER BY id DESC", (user_id,))
    apps = cursor.fetchall()
    cursor.close()
    conn.close()
    return apps

# Add this new function
def get_app_by_name(user_id, button_name):
    """Checks if an app with the given button_name exists for the user."""
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id FROM bots WHERE user_id = %s AND button_name = %s",
            (user_id, button_name)
        )
        app = cursor.fetchone()
        return app # Returns the app dict if found, None otherwise
    except mysql.connector.Error as err:
        print(f"❌ Database error checking app name '{button_name}' for user {user_id}: {err}")
        return None # Return None on error to prevent upload
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def save_uploaded_app(user_id, google_id, button_name, folder_name, image_url):
    conn = get_db()
    cursor = conn.cursor()
    # Check if google_id needs to be inserted or if user_id is sufficient
    # Assuming 'google_id' column exists in 'bots' table based on previous code context
    cursor.execute(
        "INSERT INTO bots (user_id, google_id, button_name, folder_name, image_url) VALUES (%s, %s, %s, %s, %s)",
        (user_id, google_id, button_name, folder_name, image_url)
    )
    conn.commit()
    cursor.close()
    conn.close()

def delete_app_from_db(user_id, folder_name):
    """Deletes an app record from the database for a specific user."""
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        # Ensure deletion is specific to the user and folder name
        cursor.execute(
            "DELETE FROM bots WHERE user_id = %s AND folder_name = %s",
            (user_id, folder_name)
        )
        conn.commit()
        # Check if any row was actually deleted
        return cursor.rowcount > 0
    except mysql.connector.Error as err:
        print(f"❌ Database error deleting app {folder_name} for user {user_id}: {err}")
        if conn:
            conn.rollback() # Rollback in case of error
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Helper function to get app limit based on plan
def get_plan_limit(plan):
    """Returns the app limit for a given plan."""
    plan_limits = {
        "free": 2,
        "silver": 10,
        "gold": float('inf')  # Infinite
    }
    # Return the limit for the plan (case-insensitive), default to 2 if plan is unknown
    return plan_limits.get(str(plan).lower(), 2)


