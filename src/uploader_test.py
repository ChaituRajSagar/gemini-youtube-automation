# FILE: src/uploader.py
# This is the corrected version.

import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Define the paths for the credential files
CLIENT_SECRETS_FILE = 'client_secrets.json'
CREDENTIALS_FILE = 'credentials.json'

def get_authenticated_service():
    """
    Handles the authentication flow and returns an authenticated YouTube service object.
    """
    credentials = None
    
    # Check if we already have credentials stored
    if os.path.exists(CREDENTIALS_FILE):
        credentials = Credentials.from_authorized_user_file(CREDENTIALS_FILE, ['https://www.googleapis.com/auth/youtube.upload'])

    # If we don't have valid credentials, start the authentication flow
    if not credentials or not credentials.valid:
        # If credentials exist but are expired, try to refresh them
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            # This is the part that runs the first time
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE,
                scopes=['https://www.googleapis.com/auth/youtube.upload']
            )
            # --- THIS IS THE CRITICAL FIX ---
            # This command will start a local server, open your browser,
            # and wait for you to grant permission.
            credentials = flow.run_local_server(port=0)
        
        # Save the new, fresh credentials for the next run
        with open(CREDENTIALS_FILE, 'w') as f:
            f.write(credentials.to_json())
            
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
