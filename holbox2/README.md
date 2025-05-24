# Intelligent Appointment Booking System

## Overview

The Intelligent Appointment Booking System is an AI-powered application designed to simplify and streamline the process of scheduling appointments. It features a backend API built with Flask and a proof-of-concept voice interface for user interaction. The system aims to provide smart scheduling suggestions, manage user and service provider details, handle appointment bookings, and facilitate communication through notifications and a feedback mechanism.

Key features include:
- User and Service Provider Registration & Authentication
- Management of Service Provider Availability
- Appointment Booking with Urgency Levels
- Smart Scheduling Hints (e.g., preferred time of day)
- Voice Interaction Proof-of-Concept (STT/TTS in browser)
- Console-based Email Notifications
- User Feedback System for appointments and services
- Automated API Documentation via Swagger

## Features Implemented

- **User Management:**
    - User registration (`/api/users/register`)
    - User login with JWT authentication (`/api/users/login`)
- **Service Provider Management:**
    - Service Provider registration (`/api/providers/register`)
- **Availability Management:**
    - Providers can add availability slots (`/api/providers/availability` - POST)
    - Providers can view their availability slots (`/api/providers/availability` - GET)
    - Overlap detection for availability slots.
- **Appointment Booking:**
    - Users can query available slots with filters (service type, provider, date range, preferred time of day) (`/api/availability`)
    - Users can book appointments (`/api/appointments/book`), which also marks the slot as booked.
    - Support for specifying appointment urgency.
- **Messaging System:**
    - Users can send messages (`/api/messages` - POST).
    - Users can retrieve their messages with status filters and pagination (`/api/messages` - GET).
    - Users can mark messages as read (`/api/messages/<message_id>/read` - PUT).
- **Feedback System:**
    - Users can submit feedback, optionally linked to an appointment (`/api/feedback` - POST).
- **Voice Interface (Proof-of-Concept):**
    - A basic HTML page (`/static/index.html`) demonstrates Speech-to-Text (STT) and Text-to-Speech (TTS) interaction with the backend (`/api/voice/interact`).
- **Notifications:**
    - Console-based email notifications (simulated) for appointment booking confirmations (to user and provider).
- **API Documentation:**
    - Automated Swagger UI documentation available at `/apidocs/`.
- **Database:**
    - SQLite database with tables for users, service providers, availability, appointments, messages, and feedback.
    - CLI command `flask init-db` to initialize the database schema.
- **Testing:**
    - Unit tests for core logic (password hashing, availability overlap).

## Tech Stack

-   **Backend:**
    -   Python 3.x
    -   Flask: Web framework
    -   SQLAlchemy: ORM for database interaction
    -   Flask-SQLAlchemy: Flask integration for SQLAlchemy
    -   Flask-JWT-Extended: JWT authentication
    -   Werkzeug: WSGI utility library (for password hashing)
    -   Flasgger: OpenAPI/Swagger UI generation
-   **Frontend (Voice PoC):**
    -   HTML
    -   JavaScript (using browser's Web Speech API for SpeechRecognition and SpeechSynthesis)
-   **Database:**
    -   SQLite (for MVP development)

## Setup Instructions

### Prerequisites
-   Python 3.8 or newer
-   `pip` (Python package installer)
-   Git

### Steps
1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create and Activate a Virtual Environment (Recommended):**
    -   **Linux/macOS:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    -   **Windows:**
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```

3.  **Install Dependencies:**
    Ensure your virtual environment is activated, then run:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Initialize the Database:**
    The application uses a Flask CLI command to create the database tables based on the defined models. Run the following command from the project root:
    ```bash
    flask init-db
    ```
    This will create an `appointments.db` SQLite file in the project's instance folder (if not already configured elsewhere).

## Running the Application

1.  **Ensure your virtual environment is activated.**
2.  **Set the Flask application environment variable (optional, defaults to app.py):**
    ```bash
    # For Linux/macOS
    export FLASK_APP=src/api/app.py 
    # For Windows (PowerShell)
    # $env:FLASK_APP="src\api\app.py"
    # For Windows (CMD)
    # set FLASK_APP=src\api\app.py
    ```
    *Note: If your main Flask app file is named `app.py` or `wsgi.py` in the root, `FLASK_APP` might not need to be set explicitly, but since our app is in `src/api/app.py`, it's good practice.*

3.  **Run the Flask Development Server:**
    ```bash
    flask run
    ```
    Alternatively, you can use `python -m flask run`.

4.  The application will typically be available at `http://127.0.0.1:5000/`.

## API Documentation

The API is documented using Swagger (via Flasgger). Once the application is running, you can access the interactive Swagger UI at:
`http://127.0.0.1:5000/apidocs/`

## Running Tests

Unit tests are located in the `tests/unit/` directory.

1.  **Ensure your virtual environment is activated and dependencies are installed.**
2.  **To run all tests:**
    You can use Python's `unittest` discovery mechanism from the project root:
    ```bash
    python -m unittest discover tests
    ```
    Or, more specifically for unit tests:
    ```bash
    python -m unittest discover tests/unit
    ```

3.  **To run specific test files:**
    For example, to run the user authentication tests:
    ```bash
    python -m unittest tests/unit/test_user_auth.py
    ```
    To run the availability logic tests:
    ```bash
    python -m unittest tests/unit/test_availability_logic.py
    ```

## Voice Interface Proof-of-Concept (PoC)

A basic proof-of-concept for voice interaction is available.

1.  **Ensure the Flask application is running.**
2.  **Access the PoC page:**
    Open your web browser (Chrome or Edge recommended for best Web Speech API compatibility) and navigate to:
    `http://127.0.0.1:5000/static/index.html`
    *(Note: The Flask app is configured to serve the `static` directory from the root path, so `http://120.0.0.1:5000/` should also serve `index.html` from the `static` folder.)*

3.  **Usage:**
    -   Click the "Start Listening" button. Your browser may ask for microphone permission.
    -   Speak a phrase (e.g., "Hello backend").
    -   The transcribed text will appear under "You said:".
    -   This text is sent to the `/api/voice/interact` backend endpoint.
    -   The backend's response (e.g., "You said: Hello backend") will appear under "Backend says:" and should also be spoken out by your browser (Text-to-Speech).
    -   Click "Stop Listening" to manually stop the recognition.
```
