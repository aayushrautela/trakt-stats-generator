import requests
import sys
import os
import json
import time
import base64
import mimetypes
import html
from datetime import datetime

#FILE PATHS
CREDENTIALS_PATH = 'trakt_credentials.json'
SVG_PATH = 'trakt_stats.svg'

#API URLS
TRAKT_API_BASE_URL = "https://api.trakt.tv"

def get_trakt_tokens_interactive(client_id, client_secret):
    """Handles the interactive OAuth 2.0 device authentication flow."""
    print("Starting Trakt device authentication...")
    try:
        code_response = requests.post(f"{TRAKT_API_BASE_URL}/oauth/device/code", json={'client_id': client_id})
        code_response.raise_for_status()
        code_data = code_response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting device code from Trakt: {e}")
        sys.exit(1)

    device_code, user_code, verification_url, interval = code_data['device_code'], code_data['user_code'], code_data['verification_url'], code_data['interval']
    
    print("="*50 + "\nPlease authorize this application.\n" + f"1. Go to: {verification_url}\n" + f"2. Enter the code: {user_code}\n" + "="*50)
    
    while True:
        time.sleep(interval)
        try:
            token_response = requests.post(f"{TRAKT_API_BASE_URL}/oauth/device/token", json={'client_id': client_id, 'client_secret': client_secret, 'code': device_code})
            if token_response.status_code == 200:
                credentials = token_response.json()
                with open(CREDENTIALS_PATH, 'w') as f: json.dump(credentials, f, indent=4)
                print(f"\nAuthorization successful! Credentials saved to '{CREDENTIALS_PATH}'.")
                print("IMPORTANT: Copy the entire content of this file and paste it into the 'TRAKT_CREDENTIALS' secret in your GitHub repository settings.")
                return
            elif token_response.status_code != 400: token_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error polling for token: {e}")
            sys.exit(1)

def save_image_from_url(image_url):
    """Downloads an image from a URL and returns its local path and content type."""
    if not image_url: return None, None
    try:
        full_url = f"https://{image_url}" if not image_url.startswith('http') else image_url
        file_extension = os.path.splitext(full_url)[1] if os.path.splitext(full_url)[1] else '.png'
        file_path = f"logo{file_extension}"

        response = requests.get(full_url, stream=True)
        response.raise_for_status()
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return file_path, response.headers.get('Content-Type', 'image/png')
    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        return None, None

def image_to_base64(file_path, mime_type):
    """Converts an image file to a Base64 data URI."""
    if not file_path or not os.path.exists(file_path): return ""
    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:{mime_type};base64,{encoded_string}"

def generate_trakt_svg(trakt_username, access_token):
    """Fetches the last watched item and creates a stats-block SVG file."""
    headers = {'Content-Type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': os.environ.get("TRAKT_CLIENT_ID"), 'Authorization': f"Bearer {access_token}"}
    url = f"{TRAKT_API_BASE_URL}/users/{trakt_username}/history?limit=1&extended=full,images"
    
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        history = r.json()
        if not history:
            content_html = "<p>Nothing watched recently.</p>"
            svg_height = 160
        else:
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
                    logo_path, logo_mime = save_image_from_url(logo_url)
                    logo_base64 = image_to_base64(logo_path, logo_mime)

            secondary_line_html = f'<p style="margin: 0 0 12px; font-size: 14px; color: #a9fef7;">{secondary_line}</p>' if secondary_line else ""
            svg_height = 190 if secondary_line else 160

            content_html = f"""
            <a href="https://trakt.tv/users/{trakt_username}/history" style="text-decoration:none;">
            <div style="background-color: #151515; border-radius: 6px; padding: 16px; border: 1px solid #e4e3e2; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji'; color: #fff; display: flex; align-items: center; height: {svg_height - 34}px;">
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
        
        svg_content = f"""
        <svg fill="none" width="550" height="{svg_height}" viewBox="0 0 550 {svg_height}" xmlns="http://www.w3.org/2000/svg">
            <foreignObject width="100%" height="100%">
                <div xmlns="http://www.w3.org/1999/xhtml" style="height: 100%;">
                    {content_html}
                </div>
            </foreignObject>
        </svg>
        """

        with open(SVG_PATH, 'w', encoding='utf-8') as f:
            f.write(svg_content.strip())
        print(f"Successfully created '{SVG_PATH}'")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Trakt: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # Check for local authentication mode
    if len(sys.argv) > 1 and sys.argv[1] == 'auth':
        local_client_id = input("Enter your Trakt Client ID: ")
        local_client_secret = input("Enter your Trakt Client Secret: ")
        get_trakt_tokens_interactive(local_client_id, local_client_secret)
    # Default mode for GitHub Actions
    else:
        TRAKT_USERNAME = os.environ.get("TRAKT_USERNAME")
        TRAKT_CREDENTIALS_JSON = os.environ.get("TRAKT_CREDENTIALS")

        if not all([TRAKT_USERNAME, os.environ.get("TRAKT_CLIENT_ID"), os.environ.get("TRAKT_CLIENT_SECRET"), TRAKT_CREDENTIALS_JSON]):
            print("Error: Required environment variables (secrets) are not set for the GitHub Action.")
            sys.exit(1)
        
        creds = json.loads(TRAKT_CREDENTIALS_JSON)
        
        expiry_time = creds.get('created_at', 0) + creds.get('expires_in', 0)
        if time.time() > expiry_time:
            print("Error: Trakt token has expired. Please re-run with 'auth' argument locally to generate new credentials and update your GitHub secret.")
            sys.exit(1)

        generate_trakt_svg(TRAKT_USERNAME, creds['access_token'])

