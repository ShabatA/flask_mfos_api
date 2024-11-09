import os
import json
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from decouple import config

# Define the scopes for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def authenticate_gmail():
    """Authenticate with Gmail API using stored token JSON."""
    # Load token data from the environment variable and parse it
    token_data = json.loads(config("TOKEN_JSON"))

    # Create credentials using the token data
    creds = Credentials.from_authorized_user_info(token_data, SCOPES)

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
