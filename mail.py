import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(sender_email, app_password, recipient_email, subject, body):
    # Set up the server
    smtp_server = "smtp.gmail.com"
    port = 587  # For TLS

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Try to log in to server and send email
    try:
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()  # Secure the connection
        server.login(sender_email, app_password)  # Login with your Google App Password or email password
        server.sendmail(sender_email, recipient_email, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        server.quit()

# Example usage
sender_email = "info@mofs.online"
app_password = "usmsrjquxjojivgx"  # Use the App Password or your Gmail password if "Less Secure Apps" is enabled
recipient_email = "abshabat@gmail.com"
subject = "Test Email from Python"
body = "Hello, this is a test email sent from a Python script!"

send_email(sender_email, app_password, recipient_email, subject, body)
