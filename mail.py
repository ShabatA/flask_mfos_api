import os.path
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Define the scopes - Gmail API requires these to send email
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def authenticate_gmail():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Initialize the flow to obtain the authorization URL
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            auth_url, _ = flow.authorization_url(prompt='consent')

            # Print the authorization URL for manual copy-pasting
            print("Please go to this URL and authorize access:", auth_url)
            code = input("Enter the authorization code here: ")

            # Fetch the credentials using the authorization code
            flow.fetch_token(code=code)
            creds = flow.credentials

            # Save the credentials for future runs
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
                
    return creds


def send_email(service, sender_email, recipient_email, subject, body):
    # Create the email
    message = MIMEMultipart()
    message['to'] = recipient_email
    message['from'] = sender_email
    message['subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    # Encode the message in base64
    raw_message = base64.urlsafe_b64encode(message.as_string().encode("utf-8"))
    raw_message = raw_message.decode("utf-8")
    body = {'raw': raw_message}

    try:
        # Use the Gmail API to send the email
        message = service.users().messages().send(userId="me", body=body).execute()
        print(f"Email sent successfully! Message ID: {message['id']}")
    except HttpError as error:
        print(f"An error occurred: {error}")

def main():
    # Authenticate and build the Gmail API service
    creds = authenticate_gmail()
    service = build('gmail', 'v1', credentials=creds)

    # Email details
    sender_email = "info@mofs.online"  # Replace with your email
    recipient_email = "abshabat@gmail.com"  # Replace with recipient email
    subject = "Test Email using Gmail API"
    body = "Hello, this is a test email sent from Python using the Gmail API!"

    # Send the email
    send_email(service, sender_email, recipient_email, subject, body)

if __name__ == '__main__':
    main()
