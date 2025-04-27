from flask import Blueprint, redirect, url_for, session, request, current_app
from utils.db_utils import get_db
from authlib.integrations.flask_client import OAuth
import os

auth_bp = Blueprint('auth_bp', __name__)
oauth = OAuth()

def init_oauth(app):
    oauth.init_app(app)

    oauth.register(
        name='google',
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            'scope': 'openid email profile',
        }
    )

@auth_bp.route('/login')
def login():
    if 'google_id' in session:
        return redirect(url_for('user_bp.dashboard'))
    
    redirect_uri = url_for('auth_bp.callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/login/callback')
def callback():
    try:
        token = oauth.google.authorize_access_token()
        userinfo = token['userinfo']

        session['google_id'] = userinfo['sub']
        session['email'] = userinfo['email']
        session['name'] = userinfo.get('name', '')

        # Check and Insert into database
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM clients WHERE google_id = %s", (session['google_id'],))
        user = cursor.fetchone()

        if not user:
            cursor.execute(
                "INSERT INTO clients (google_id, email, name, plan) VALUES (%s, %s, %s, %s)",
                (session['google_id'], session['email'], session['name'], 'free')
            )
            conn.commit()

        # Fetch user_id and store in session
        cursor.execute("SELECT id FROM clients WHERE google_id = %s", (session['google_id'],))
        user = cursor.fetchone()
        session['user_id'] = user[0]

        cursor.close()
        conn.close()

        return redirect(url_for('user_bp.post_login'))

    except Exception as e:
        print(f"❌ Error during Google login callback: {e}")
        return redirect(url_for('auth_bp.login'))


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth_bp.login'))
