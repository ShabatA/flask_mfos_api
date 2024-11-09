import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Define the scopes for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print(BASE_DIR)

def authenticate_gmail():
    """Authenticate with Gmail API and return the service object."""
    creds = None
    print(BASE_DIR)

    CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
    TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')
    
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        auth_url, _ = flow.authorization_url(prompt='consent')
        print("Please go to this URL and authorize access:", auth_url)
        code = input("Enter the authorization code here: ")
        flow.fetch_token(code=code)
        creds = flow.credentials
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def send_email(service, sender_email, recipient_email, subject, body):
    """Send an email using the Gmail API service."""
    message = MIMEMultipart()
    message['to'] = recipient_email
    message['from'] = sender_email
    message['subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    raw_message = base64.urlsafe_b64encode(message.as_string().encode("utf-8"))
    raw_message = raw_message.decode("utf-8")
    body = {'raw': raw_message}

    try:
        message = service.users().messages().send(userId="me", body=body).execute()
        return f"Email sent successfully! Message ID: {message['id']}"
    except HttpError as error:
        return f"An error occurred: {error}"
