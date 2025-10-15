import os
import json
import time
import base64
import requests
import html
from flask import Flask, Response, request, redirect, session
import redis

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a-super-secret-key")

TRAKT_USERNAME = os.environ.get("TRAKT_USERNAME")
TRAKT_CLIENT_ID = os.environ.get("TRAKT_CLIENT_ID")
TRAKT_CLIENT_SECRET = os.environ.get("TRAKT_CLIENT_SECRET")
TRAKT_REDIRECT_URI = os.environ.get("TRAKT_REDIRECT_URI")

TRAKT_API_BASE_URL = "https://api.trakt.tv"

# Initialize Redis client
redis_client = redis.from_url(
    os.environ.get("REDIS_URL"),
    password=os.environ.get("KV_REST_API_TOKEN")
)

# Redis storage functions
def get_tokens_from_redis():
    """Get tokens from Redis"""
    try:
        tokens_json = redis_client.get("trakt_tokens")
        return json.loads(tokens_json) if tokens_json else None
    except Exception as e:
        print(f"Error getting tokens from Redis: {e}")
        return None

def save_tokens_to_redis(tokens):
    """Save tokens to Redis"""
    try:
        # Add metadata
        tokens['saved_at'] = time.time()
        tokens['expires_at'] = time.time() + tokens.get('expires_in', 0)
        
        redis_client.set("trakt_tokens", json.dumps(tokens))
        print("Tokens saved to Redis successfully")
        return True
    except Exception as e:
        print(f"Error saving tokens to Redis: {e}")
        return False

def refresh_trakt_token_from_redis():
    """Refresh token using stored refresh token from Redis"""
    tokens = get_tokens_from_redis()
    if not tokens or not tokens.get('refresh_token'):
        return None
        
    try:
        response = requests.post(f"{TRAKT_API_BASE_URL}/oauth/token", json={
            'refresh_token': tokens['refresh_token'],
            'client_id': TRAKT_CLIENT_ID,
            'client_secret': TRAKT_CLIENT_SECRET,
            'redirect_uri': TRAKT_REDIRECT_URI,
            'grant_type': 'refresh_token'
        })
        response.raise_for_status()
        new_credentials = response.json()
        print("Token refreshed successfully from Redis.")
        
        # Save new tokens to Redis
        save_tokens_to_redis(new_credentials)
        
        return new_credentials
    except requests.exceptions.RequestException as e:
        print(f"Could not refresh token from Redis: {e}.")
        return None

def get_valid_access_token():
    """Get a valid access token from Redis storage"""
    tokens = get_tokens_from_redis()
    if not tokens:
        return None
    
    # Check if token is expired (with 5 minute buffer)
    current_time = time.time()
    if current_time >= (tokens.get('expires_at', 0) - 300):  # 5 minute buffer
        print("Token expired or expiring soon, refreshing...")
        new_tokens = refresh_trakt_token_from_redis()
        if new_tokens:
            return new_tokens['access_token']
        return None
    
    return tokens['access_token']

@app.route('/login')
def login():
    auth_url = (
        f"{TRAKT_API_BASE_URL}/oauth/authorize?response_type=code"
        f"&client_id={TRAKT_CLIENT_ID}&redirect_uri={TRAKT_REDIRECT_URI}"
    )
    return redirect(auth_url)

@app.route('/oauth/callback')
def oauth_callback():
    code = request.args.get('code')
    if not code:
        return "Error: No authorization code provided.", 400

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
        
        # Save tokens to Redis instead of just session
        if save_tokens_to_redis(credentials):
            return """
            <h2>Authentication Successful!</h2>
            <p>Your tokens have been saved to Upstash Redis storage.</p>
            <p>Your public endpoint will now work automatically!</p>
            <p><a href="/api/trakt/public">Test your public endpoint</a></p>
            <p><a href="/api/refresh-token">Test token refresh</a></p>
            """
        else:
            return "Error: Could not save tokens to storage.", 500

    except requests.exceptions.RequestException as e:
        return f"Error exchanging code for token: {e}", 500

# Add a token refresh endpoint for manual testing
@app.route('/api/refresh-token')
def refresh_token_endpoint():
    """Endpoint to manually refresh tokens"""
    new_creds = refresh_trakt_token_from_redis()
    if new_creds:
        return {"status": "success", "message": "Token refreshed successfully"}
    else:
        return {"status": "error", "message": "Failed to refresh token"}, 500

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
    url = f"{TRAKT_API_BASE_URL}/users/me/history?limit=1&extended=full,images"
    
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

        secondary_line_html = f'<div style="margin-bottom: 12px; font-size: 14px; color: #a9fef7;">{secondary_line}</div>' if secondary_line else ""
        svg_height = 190 if secondary_line else 160

        content_html = f"""
        <a href="https://trakt.tv/users/{trakt_username}/history" style="text-decoration:none;">
        <div style="background-color: #151515; border-radius: 6px; padding: 16px; border: 1px solid #e4e3e2; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji'; color: #fff; display: flex; align-items: center; height: {svg_height - 34}px;">
            
            <div style="flex-shrink: 0; width: 130px; display: flex; align-items: center; justify-content: center;">
                <img src="{logo_base64}" alt="Logo" width="120" style="max-height: 120px;"/>
            </div>

            <div style="flex-grow: 1; padding-left: 12px;">
                <div style="margin-bottom: 8px; font-size: 12px; color: #888; font-weight: 600;">LATEST WATCH</div>
                <div style="margin-bottom: 8px; font-size: 18px; font-weight: 600;">{title_line}</div>
                {secondary_line_html}
                <div style="font-size: 12px; color: #888;">{genres}</div>
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
    creds = session.get('trakt_credentials')

    if not creds:
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

# Public endpoint for GitHub README
@app.route('/api/trakt/public')
def get_trakt_svg_public():
    """Public endpoint that works without session authentication"""
    access_token = get_valid_access_token()
    
    if not access_token:
        return Response("No valid Trakt credentials found. Please authenticate first at /login", mimetype='text/plain', status=401)
    
    svg_data = generate_svg(TRAKT_USERNAME, access_token)
    
    return Response(svg_data, mimetype='image/svg+xml', headers={
        'Cache-Control': 's-maxage=3600, stale-while-revalidate',
        'Access-Control-Allow-Origin': '*',  # Allow cross-origin requests
    })

# Health check endpoint
@app.route('/')
def health_check():
    return "Trakt Stats Generator is running!"
