import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# This function assumes your client_secrets.json and credentials.json are in the root directory
def upload_to_youtube(video_path, title, description, tags):
    """Uploads a video to YouTube with the given metadata."""
    print(f"⬆️ Uploading '{video_path}' to YouTube...")
    
    try:
        # NOTE: This authentication flow is designed for local use. 
        # In GitHub Actions, you'll need a more robust, non-interactive method,
        # often by refreshing an existing token stored in credentials.json.
        # Your previous setup likely handled this correctly.
        
        flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', ['https://www.googleapis.com/auth/youtube.upload'])
        # You need to ensure credentials.json is valid and has a refresh token
        credentials = flow.credentials # In a real scenario, you'd load credentials from your file
        
        youtube = build('youtube', 'v3', credentials=credentials)
        
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
        # In a real workflow, you might not want to raise an error here
        # if the video generation was successful but the upload failed.
        # For now, we'll let it fail to see the error.
        raise