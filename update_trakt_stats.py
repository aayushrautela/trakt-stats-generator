import os
import json
import time
import base64
import requests
import html
from flask import Flask, Response, request, redirect, session

app = Flask(__name__)
# It is important to set a secret key for session management
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a-super-secret-key")

TRAKT_USERNAME = os.environ.get("TRAKT_USERNAME")
TRAKT_CLIENT_ID = os.environ.get("TRAKT_CLIENT_ID")
TRAKT_CLIENT_SECRET = os.environ.get("TRAKT_CLIENT_SECRET")

# You will need to set this to the callback URL of your application
# For local testing, you can use something like 'http://127.0.0.1:5000/oauth/callback'
# For production, it should be the URL of your deployed application
TRAKT_REDIRECT_URI = os.environ.get("TRAKT_REDIRECT_URI")


TRAKT_API_BASE_URL = "https://api.trakt.tv"

# --- New Routes for OAuth 2.0 Flow ---

@app.route('/login')
def login():
    """
    Redirects the user to Trakt's authorization page.
    """
    auth_url = (
        f"{TRAKT_API_BASE_URL}/oauth/authorize?response_type=code"
        f"&client_id={TRAKT_CLIENT_ID}&redirect_uri={TRAKT_REDIRECT_URI}"
    )
    return redirect(auth_url)

@app.route('/oauth/callback')
def oauth_callback():
    """
    Handles the callback from Trakt after the user authorizes the application.
    """
    code = request.args.get('code')
    if not code:
        return "Error: No authorization code provided.", 400

    # Exchange the authorization code for an access token
    token_url = f"{TRAKT_API_BASE_URL}/oauth/token"
    token_data = {
        'code': code,
        'client_id': TRAKT_CLIENT_ID,
        'client_secret': TRAKT_CLIENT_SECRET,
        'redirect_uri': TRAKT_REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    
    try:
        response = requests.post(token_url, json=token_data)
        response.raise_for_status()
        credentials = response.json()
        
        # Store the credentials securely. For a simple app, a session is fine.
        # For a more robust application, you might want to store this in a database.
        session['trakt_credentials'] = credentials
        session['trakt_credentials']['created_at'] = time.time()
        
        return "Successfully authenticated with Trakt! You can now close this window."

    except requests.exceptions.RequestException as e:
        return f"Error exchanging code for token: {e}", 500


def refresh_trakt_token(credentials):
    print("Token expired, attempting to refresh...")
    try:
        response = requests.post(f"{TRAKT_API_BASE_URL}/oauth/token", json={
            'refresh_token': credentials['refresh_token'],
            'client_id': TRAKT_CLIENT_ID,
            'client_secret': TRAKT_CLIENT_SECRET,
            'redirect_uri': TRAKT_REDIRECT_URI, # The redirect_uri is also needed for refreshing
            'grant_type': 'refresh_token'
        })
        response.raise_for_status()
        new_credentials = response.json()
        print("Token refreshed successfully.")
        
        # Update the stored credentials
        session['trakt_credentials'] = new_credentials
        session['trakt_credentials']['created_at'] = time.time()
        
        return new_credentials
    except requests.exceptions.RequestException as e:
        print(f"Could not refresh token: {e}.")
        return None

def image_to_base64(image_url):
    if not image_url: return ""
    try:
        full_url = f"https://{image_url}" if not image_url.startswith('http') else image_url
        response = requests.get(full_url)
        response.raise_for_status()
        mime_type = response.headers.get('Content-Type', 'image/png')
        encoded_string = base64.b64encode(response.content).decode('utf-8')
        return f"data:{mime_type};base64,{encoded_string}"
    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        return ""

def generate_svg(trakt_username, access_token):
    headers = {'Content-Type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': TRAKT_CLIENT_ID, 'Authorization': f"Bearer {access_token}"}
    url = f"{TRAKT_API_BASE_URL}/users/{trakt_username}/history?limit=1&extended=full,images"
    
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        history = r.json()
        if not history:
            return "<svg width='400' height='100'><text y='50'>Nothing watched recently.</text></svg>"

        last_item = history[0]
        item_type = last_item.get('type')
        item_details, title_line, secondary_line, genres, logo_base64 = None, "Could not parse item.", "", "", ""

        if item_type == 'movie':
            item_details = last_item.get('movie', {})
            title = item_details.get('title', '')
            year = item_details.get('year', '')
            title_line = f"<strong>{html.escape(title)} ({html.escape(str(year))})</strong>"
            tagline_content = item_details.get('tagline', '')
            if tagline_content:
                secondary_line = f"<em>{html.escape(tagline_content)}</em>"
            genres = html.escape(" | ".join(g.title() for g in item_details.get('genres', [])[:3]))
        elif item_type == 'episode':
            item_details = last_item.get('show', {})
            episode = last_item.get('episode', {})
            title = item_details.get('title','')
            s, e_num = episode.get('season', 0), episode.get('number', 0)
            title_line = f"<strong>{html.escape(title)} (S{s:02d}E{e_num:02d})</strong>"
            secondary_line = ""
            genres = html.escape(" | ".join(g.title() for g in item_details.get('genres', [])[:3]))

        if item_details:
            logo_list = item_details.get('images', {}).get('logo', [])
            if logo_list:
                logo_url = logo_list[0]
                logo_base64 = image_to_base64(logo_url)

        secondary_line_html = f'<p style="margin: 0 0 12px; font-size: 14px; color: #a9fef7;">{secondary_line}</p>' if secondary_line else ""
        svg_height = 190 if secondary_line else 160

        content_html = f"""
        <a href="https://trakt.tv/users/{trakt_username}/history" style="text-decoration:none;">
        <div style="background-color: #151515; border-radius: 6px; padding: 16px; border: 1px solid #e4e3e2; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji'; color: #fff; display: flex; align-items-center; height: {svg_height - 34}px;">
            <div style="flex-shrink: 0; width: 130px; text-align: center;">
                <img src="{logo_base64}" alt="Logo" width="120"/>
            </div>
            <div style="flex-grow: 1; padding-left: 12px;">
                <p style="margin: 0 0 8px; font-size: 12px; color: #888; font-weight: 600;">LATEST WATCH</p>
                <p style="margin: 0 0 8px; font-size: 18px; font-weight: 600;">{title_line}</p>
                {secondary_line_html}
                <p style="margin: 0; font-size: 12px; color: #888;">{genres}</p>
            </div>
        </div>
        </a>
        """
        
        return f"""
        <svg fill="none" width="550" height="{svg_height}" viewBox="0 0 550 {svg_height}" xmlns="http://www.w3.org/2000/svg">
            <foreignObject width="100%" height="100%">
                <div xmlns="http://www.w3.org/1999/xhtml" style="height: 100%;">
                    {content_html}
                </div>
            </foreignObject>
        </svg>
        """
    except requests.exceptions.RequestException as e:
        return f"<svg width='400' height='100'><text y='50'>Error fetching data: {e}</text></svg>"

@app.route('/api/trakt')
def get_trakt_svg():
    # Instead of loading from environment variables, we now get credentials from the session
    creds = session.get('trakt_credentials')

    if not creds:
        # If not authenticated, you can either return an error or redirect to login
        return Response("Not authenticated with Trakt. Please go to /login", mimetype='text/plain', status=401)
    
    expiry_time = creds.get('created_at', 0) + creds.get('expires_in', 0)
    if time.time() > expiry_time:
        new_creds = refresh_trakt_token(creds)
        if not new_creds:
             return Response("Failed to refresh Trakt token.", mimetype='text/plain', status=500)
        creds = new_creds

    svg_data = generate_svg(TRAKT_USERNAME, creds['access_token'])
    
    return Response(svg_data, mimetype='image/svg+xml', headers={
        'Cache-Control': 's-maxage=3600, stale-while-revalidate',
    })
