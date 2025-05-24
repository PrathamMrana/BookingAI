import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def send_email(to_email, subject, body):
    """
    Simulates sending an email by logging the details to the console.
    """
    log_message = f"""
--- Sending Email ---
To: {to_email}
Subject: {subject}
Body:
{body}
--- Email End ---
"""
    logging.info(log_message)

if __name__ == '__main__':
    # Example Usage
    send_email(
        to_email="test_user@example.com",
        subject="Test Subject - Appointment Confirmation",
        body="Dear Test User,\n\nThis is a test body for your appointment.\n\nRegards,\nSystem"
    )
    send_email(
        to_email="test_provider@example.com",
        subject="Test Subject - New Booking",
        body="Dear Test Provider,\n\nYou have a new test booking.\n\nRegards,\nSystem"
    )
