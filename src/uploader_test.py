# FILE: src/uploader.py
# This is the new, robust version that handles authentication correctly.

import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pathlib import Path

# Define the paths for the credential files in the root directory
# Use Path for better cross-platform compatibility
CLIENT_SECRETS_FILE = Path('client_secrets.json')
CREDENTIALS_FILE = Path('credentials.json')
YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]

def get_authenticated_service():
    """
    Handles the entire OAuth2 flow and returns an authenticated YouTube service object.
    """
    credentials = None
    
    # Check if we already have credentials stored from a previous run
    if CREDENTIALS_FILE.exists():
        print("Found existing credentials file.")
        credentials = Credentials.from_authorized_user_file(str(CREDENTIALS_FILE), YOUTUBE_UPLOAD_SCOPE)

    # If we don't have valid credentials, start the authentication flow
    if not credentials or not credentials.valid:
        # If credentials exist but are expired, try to refresh them automatically
        if credentials and credentials.expired and credentials.refresh_token:
            print("Refreshing expired credentials...")
            credentials.refresh(Request())
        else:
            # This is the part that runs on the very first execution
            print("No valid credentials found. Starting authentication flow...")
            if not CLIENT_SECRETS_FILE.exists():
                raise FileNotFoundError(f"CRITICAL ERROR: {CLIENT_SECRETS_FILE} not found. Please download it from Google Cloud Console.")
            
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), scopes=YOUTUBE_UPLOAD_SCOPE)
            
            # This command will start a local server, open your browser,
            # and wait for you to grant permission.
            credentials = flow.run_local_server(port=0)
        
        # Save the new, fresh credentials for all future runs
        with open(CREDENTIALS_FILE, 'w') as f:
            f.write(credentials.to_json())
        print(f"Credentials saved to {CREDENTIALS_FILE}")
            
    return build('youtube', 'v3', credentials=credentials)


def upload_to_youtube(video_path, title, description, tags):
    """Uploads a video to YouTube with the given metadata."""
    print(f"⬆️ Uploading '{video_path}' to YouTube...")
    try:
        youtube = get_authenticated_service()
        
        request_body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags.split(','),
                'categoryId': '28' # 28 = Science & Technology
            },
            'status': {
                'privacyStatus': 'private', # 'private', 'public', or 'unlisted'
                'selfDeclaredMadeForKids': False
            }
        }

        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        
        request = youtube.videos().insert(
            part=','.join(request_body.keys()),
            body=request_body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%.")
                
        print(f"✅ Video uploaded successfully! Video ID: {response.get('id')}")
        return response.get('id')
        
    except Exception as e:
        print(f"❌ ERROR: Failed to upload to YouTube. {e}")
        raise
