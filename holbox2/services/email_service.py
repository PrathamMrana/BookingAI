def send_email(to_email: str, subject: str, message: str) -> None:
    """
    A simple email service that just prints the email details to the console.
    In production, this would be replaced with actual email sending logic.
    """
    print(f"\nEmail Service:")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print(f"Message: {message}\n") 