from flask import Flask, request, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, JWTManager
from flasgger import Swagger # Added Swagger
from src.database import db, User, ServiceProvider, Availability, Appointment, Message, Feedback
from src.database.db_config import DATABASE_URI
from src.services.email_service import send_email
import os
from datetime import datetime, timezone, time

# Define the static folder relative to the app's root path
# Assuming app.py is in src/api/ and static is at the project root
STATIC_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static')


app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# TODO: Use an environment variable for the JWT secret key in production
app.config['JWT_SECRET_KEY'] = 'super-secret' # Change this!

# Flasgger configuration
app.config['SWAGGER'] = {
    'title': 'Intelligent Appointment API',
    'uiversion': 3,
    'version': '1.0.0',
    'description': 'API for an intelligent appointment booking system',
    'termsOfService': '/tos', # Example, create a /tos route if needed
    'contact': {
        'name': 'API Support',
        'url': 'http://example.com/support',
        'email': 'support@example.com'
    },
    'license': {
        'name': 'MIT',
        'url': 'https://opensource.org/licenses/MIT'
    },
    'specs_route': "/apidocs/" # URL for exposing Swagger UI
}
swagger = Swagger(app) # Initialize Flasgger

jwt = JWTManager(app)
db.init_app(app)

@app.cli.command('init-db')
def init_db_command():
    """Creates the database tables."""
    with app.app_context():
        db.create_all()
    print('Initialized the database.')

# Serve static files (like index.html) from the root and other static assets
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory(app.static_folder, path)


@app.route('/api/users/register', methods=['POST'])
def register_user():
    """
    Register a new user.
    ---
    tags:
      - Users
    summary: Creates a new user account.
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: UserRegistration
          required:
            - email
            - password
            - full_name
          properties:
            email:
              type: string
              description: User's email address.
              example: user@example.com
            password:
              type: string
              format: password
              description: User's password.
              example: StrongPwd123
            full_name:
              type: string
              description: User's full name.
              example: "John Doe"
            phone_number:
              type: string
              description: User's phone number (optional).
              example: "+1234567890"
    responses:
      201:
        description: User registered successfully.
        schema:
          properties:
            message:
              type: string
              example: User registered successfully
            user_id:
              type: integer
              example: 1
      400:
        description: Invalid input (e.g., missing fields).
        schema:
          properties:
            message:
              type: string
              example: "Missing required fields (email, password, full_name)"
      409:
        description: Email already exists.
        schema:
          properties:
            message:
              type: string
              example: Email already exists
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')
    phone_number = data.get('phone_number')

    if not email or not password or not full_name:
        return jsonify({'message': 'Missing required fields (email, password, full_name)'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 409

    hashed_password = generate_password_hash(password)
    new_user = User(
        email=email,
        password_hash=hashed_password,
        full_name=full_name,
        phone_number=phone_number
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully', 'user_id': new_user.id}), 201

@app.route('/api/users/login', methods=['POST'])
def login_user():
    """
    Log in an existing user.
    ---
    tags:
      - Users
    summary: Authenticates a user and returns a JWT access token.
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: UserLogin
          required:
            - email
            - password
          properties:
            email:
              type: string
              description: User's email address.
              example: user@example.com
            password:
              type: string
              format: password
              description: User's password.
              example: StrongPwd123
    responses:
      200:
        description: Login successful.
        schema:
          properties:
            access_token:
              type: string
              description: JWT access token.
            user_id:
              type: integer
              description: ID of the logged-in user.
            email:
              type: string
              description: Email of the logged-in user.
      400:
        description: Invalid input (e.g., missing email or password).
        schema:
          properties:
            message:
              type: string
              example: "Email and password are required"
      401:
        description: Invalid credentials.
        schema:
          properties:
            message:
              type: string
              example: Invalid credentials
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Invalid credentials'}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify(access_token=access_token, user_id=user.id, email=user.email), 200

@app.route('/api/providers/register', methods=['POST'])
def register_service_provider():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')
    phone_number = data.get('phone_number') # Optional
    service_type = data.get('service_type')
    bio = data.get('bio') # Optional

    if not email or not password or not full_name or not service_type:
        return jsonify({'message': 'Missing required fields (email, password, full_name, service_type)'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 409

    hashed_password = generate_password_hash(password)
    
    # Create User
    new_user = User(
        email=email,
        password_hash=hashed_password,
        full_name=full_name,
        phone_number=phone_number
    )
    db.session.add(new_user)
    
    # Create ServiceProvider
    # We need to commit the user first to get the user_id if the DB doesn't support deferred foreign key checks
    # or if we are not in a transaction that handles this automatically.
    # For simplicity here, we'll commit the user, then create the provider.
    # A more robust solution might use a single transaction.
    try:
        db.session.commit() # Commit user to get ID
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to create user: {str(e)}'}), 500

    new_provider = ServiceProvider(
        user_id=new_user.id,
        service_type=service_type,
        bio=bio
    )
    db.session.add(new_provider)
    
    try:
        db.session.commit() # Commit service provider
    except Exception as e:
        # Attempt to rollback user creation if provider creation fails
        # This is a simplistic rollback, more complex scenarios might need Sagas or two-phase commits
        db.session.delete(new_user) # This will only work if new_user is still in session and not detached
        db.session.commit()
        return jsonify({'message': f'Failed to create service provider: {str(e)}'}), 500

    return jsonify({
        'message': 'Service provider registered successfully',
        'user_id': new_user.id,
        'provider_id': new_provider.id
    }), 201

@app.route('/api/voice/interact', methods=['POST'])
def voice_interact():
    data = request.get_json()
    if not data or 'transcribed_text' not in data:
        return jsonify({'message': 'Missing transcribed_text in request'}), 400
    
    transcribed_text = data['transcribed_text']
    
    # Simple echo logic
    response_text = f"You said: {transcribed_text}"
    
    return jsonify({'response_text': response_text}), 200

# Helper to get ServiceProvider from current_user (JWT identity)
def get_provider_from_jwt():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return None
    return ServiceProvider.query.filter_by(user_id=user.id).first()

@app.route('/api/providers/availability', methods=['POST', 'GET']) # Added GET method
@jwt_required()
def manage_availability(): # Renamed function to handle both POST and GET
    if request.method == 'POST':
        return add_availability_slot()
    elif request.method == 'GET':
        return get_availability_slots()

def add_availability_slot(): # Extracted POST logic into its own function
    provider = get_provider_from_jwt()
    if not provider:
        return jsonify({'message': 'User is not a service provider or not found'}), 403

    data = request.get_json()
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')

    if not start_time_str or not end_time_str:
        return jsonify({'message': 'Missing start_time or end_time'}), 400

    try:
        # Assume UTC if no timezone info. fromisoformat handles 'Z' for UTC.
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'message': 'Invalid datetime format. Use ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)'}), 400

    # Ensure times are timezone-aware (UTC) for consistent comparison
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    
    now_utc = datetime.now(timezone.utc)

    if start_time >= end_time:
        return jsonify({'message': 'End time must be after start time'}), 400
    if start_time < now_utc: # Allowing start_time to be exactly now
        return jsonify({'message': 'Availability start time cannot be in the past'}), 400
    
    # Check for overlaps
    overlapping_slots = Availability.query.filter(
        Availability.provider_id == provider.id,
        Availability.start_time < end_time,
        Availability.end_time > start_time
    ).first()

    if overlapping_slots:
        return jsonify({
            'message': 'Availability slot overlaps with an existing one',
            'conflicting_slot': {
                'start_time': overlapping_slots.start_time.isoformat(),
                'end_time': overlapping_slots.end_time.isoformat()
            }
        }), 409

    new_availability = Availability(
        provider_id=provider.id,
        start_time=start_time,
        end_time=end_time
    )
    db.session.add(new_availability)
    db.session.commit()

    return jsonify({
        'message': 'Availability slot added successfully',
        'availability': {
            'id': new_availability.id,
            'provider_id': new_availability.provider_id,
            'start_time': new_availability.start_time.isoformat(),
            'end_time': new_availability.end_time.isoformat(),
            'is_booked': new_availability.is_booked
        }
    }), 201

def get_availability_slots(): # New function for GET logic
    provider = get_provider_from_jwt()
    if not provider:
        return jsonify({'message': 'User is not a service provider or not found'}), 403

    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    query = Availability.query.filter_by(provider_id=provider.id)

    try:
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            query = query.filter(Availability.start_time >= start_date)
        
        if end_date_str:
            # For end_date, we want to include slots that start anytime on that day,
            # so we effectively set the time to the end of that day.
            # Example: if end_date is 2024-07-29, we want to include slots up to 2024-07-29T23:59:59.999999Z
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            # To include the whole day, we check if the slot's end_time is after the start of the given end_date
            # or if the slot's start_time is before or on the given end_date.
            # A simpler filter for listing: availability.start_time <= end_date (if end_date is effectively end of day)
            # For end_time of a slot, it must be greater than the start_date filter.
            # For start_time of a slot, it must be less than the end_date filter
            # A common interpretation for end_date is to include everything that starts on or before that date.
            # Let's assume end_date filter means "slots ending on or before this date" or "slots starting on or before this date"
            # For simplicity: slots that START on or before the end_date.
            query = query.filter(Availability.start_time <= end_date)

    except ValueError:
        return jsonify({'message': 'Invalid date format for start_date or end_date. Use ISO 8601 (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)'}), 400

    availabilities = query.order_by(Availability.start_time).all()
    
    output = []
    for slot in availabilities:
        output.append({
            'id': slot.id,
            'provider_id': slot.provider_id,
            'start_time': slot.start_time.isoformat(),
            'end_time': slot.end_time.isoformat(),
            'is_booked': slot.is_booked
        })
    
    return jsonify(output), 200

@app.route('/api/availability', methods=['GET'])
def query_available_slots():
    """
    Query available appointment slots.
    ---
    tags:
      - Availability
    summary: Retrieves available appointment slots based on filter criteria.
    produces:
      - application/json
    parameters:
      - name: service_type
        in: query
        type: string
        required: false
        description: Filter by service type (e.g., "Dental Checkup", "Haircut").
        example: "Dental Checkup"
      - name: provider_id
        in: query
        type: integer
        required: false
        description: Filter by specific service provider ID.
        example: 1
      - name: start_date
        in: query
        type: string
        format: date
        required: true
        description: Start date for querying availability (YYYY-MM-DD).
        example: "2024-08-01"
      - name: end_date
        in: query
        type: string
        format: date
        required: false
        description: End date for querying availability (YYYY-MM-DD). Defaults to start_date.
        example: "2024-08-01"
      - name: preferred_time_of_day
        in: query
        type: string
        required: false
        enum: ["morning", "afternoon", "evening"]
        description: Preferred time of day to prioritize slots.
        example: "afternoon"
    responses:
      200:
        description: A list of available appointment slots.
        schema:
          type: array
          items:
            type: object
            properties:
              availability_id:
                type: integer
              start_time:
                type: string
                format: date-time
              end_time:
                type: string
                format: date-time
              provider:
                type: object
                properties:
                  id:
                    type: integer
                  full_name:
                    type: string
                  service_type:
                    type: string
                  bio:
                    type: string
              matched_preference:
                type: boolean
      400:
        description: Invalid input (e.g., missing start_date, invalid date format).
        schema:
          properties:
            message:
              type: string
              example: "Missing required query parameter: start_date"
    """
    service_type = request.args.get('service_type')
    provider_id_str = request.args.get('provider_id')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date', start_date_str) # Defaults to start_date
    preferred_time_of_day = request.args.get('preferred_time_of_day') # morning, afternoon, evening

    if not start_date_str:
        return jsonify({'message': 'Missing required query parameter: start_date'}), 400

    try:
        start_date = datetime.fromisoformat(start_date_str).replace(tzinfo=timezone.utc)
        # To include the whole day, set time to the beginning of the day
        start_datetime = datetime.combine(start_date.date(), time.min, tzinfo=timezone.utc)
        
        end_date = datetime.fromisoformat(end_date_str).replace(tzinfo=timezone.utc)
        # To include the whole day, set time to the end of the day
        end_datetime = datetime.combine(end_date.date(), time.max, tzinfo=timezone.utc)

    except ValueError:
        return jsonify({'message': 'Invalid date format. Use ISO 8601 (YYYY-MM-DD)'}), 400

    if start_datetime > end_datetime:
        return jsonify({'message': 'start_date cannot be after end_date'}), 400

    query = Availability.query.filter(Availability.is_booked == False)
    query = query.filter(Availability.start_time >= start_datetime)
    query = query.filter(Availability.start_time <= end_datetime) # Slots must START within the day range

    if provider_id_str:
        try:
            provider_id = int(provider_id_str)
            query = query.filter(Availability.provider_id == provider_id)
        except ValueError:
            return jsonify({'message': 'Invalid provider_id format. Must be an integer.'}), 400
    
    if service_type:
        query = query.join(ServiceProvider).filter(ServiceProvider.service_type.ilike(f"%{service_type}%"))

    available_slots = query.order_by(Availability.start_time).all()

    # Smart scheduling based on preferred_time_of_day
    preferred_slots = []
    other_slots = []
    matched_preference_applied = False

    if preferred_time_of_day and preferred_time_of_day.lower() in ['morning', 'afternoon', 'evening']:
        matched_preference_applied = True
        # Define time ranges (hours in UTC, assuming slot.start_time is UTC)
        # These ranges should ideally be configurable or more timezone-aware in a real app
        time_ranges = {
            'morning': (8, 12),   # 8:00 AM to 11:59 AM
            'afternoon': (12, 17), # 12:00 PM to 4:59 PM
            'evening': (17, 21)   # 5:00 PM to 8:59 PM
        }
        pref_start_hour, pref_end_hour = time_ranges.get(preferred_time_of_day.lower())

        for slot in available_slots:
            slot_start_hour = slot.start_time.hour # Assumes start_time is a datetime object
            if pref_start_hour <= slot_start_hour < pref_end_hour:
                preferred_slots.append(slot)
            else:
                other_slots.append(slot)
        
        # Results are preferred slots first, then others, both sorted by start_time (already done by initial query)
        processed_slots = preferred_slots + other_slots
    else:
        processed_slots = available_slots # No preference or invalid preference, use original order

    output = []
    for slot in processed_slots:
        provider_info = {
            'id': slot.provider.id,
            'full_name': slot.provider.user.full_name,
            'service_type': slot.provider.service_type,
            'bio': slot.provider.bio
        }
        slot_data = {
            'availability_id': slot.id,
            'start_time': slot.start_time.isoformat(),
            'end_time': slot.end_time.isoformat(),
            'provider': provider_info,
            'matched_preference': False # Default
        }
        if matched_preference_applied and slot in preferred_slots:
            slot_data['matched_preference'] = True
        
        output.append(slot_data)
    
    return jsonify(output), 200

@app.route('/api/appointments/book', methods=['POST'])
@jwt_required()
def book_appointment():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'message': 'User not found for token identity'}), 404 # Should not happen if token is valid

    data = request.get_json()
    availability_id = data.get('availability_id')
    urgency_level = data.get('urgency_level', 0) # Default to 0 if not provided

    if not availability_id:
        return jsonify({'message': 'Missing availability_id in request'}), 400
    
    if urgency_level not in [0, 1]:
        return jsonify({'message': 'Invalid urgency_level. Must be 0 (Normal) or 1 (High).'}), 400

    try:
        availability_id = int(availability_id)
    except ValueError:
        return jsonify({'message': 'Invalid availability_id format. Must be an integer.'}), 400

    # Start transaction handling
    try:
        availability_slot = Availability.query.filter_by(id=availability_id).with_for_update().first() # Lock the row

        if not availability_slot:
            return jsonify({'message': 'Availability slot not found'}), 404
        
        if availability_slot.is_booked:
            return jsonify({'message': 'This slot is already booked'}), 409

        # Mark slot as booked
        availability_slot.is_booked = True
        
        # Create appointment
        new_appointment = Appointment(
            user_id=user.id,
            provider_id=availability_slot.provider_id,
            availability_id=availability_slot.id,
            start_time=availability_slot.start_time, # Denormalized
            end_time=availability_slot.end_time,     # Denormalized
            status='confirmed',
            urgency_level=urgency_level # Set urgency level
        )
        
        db.session.add(availability_slot)
        db.session.add(new_appointment)
        db.session.commit()

        # --- Start Email Notification ---
        try:
            user_email = user.email
            user_name = user.full_name
            
            provider_user = User.query.get(availability_slot.provider.user_id)
            provider_email = provider_user.email
            provider_name = provider_user.full_name
            service_type = availability_slot.provider.service_type
            
            appointment_start_time = new_appointment.start_time.strftime("%Y-%m-%d at %I:%M %p %Z")

            # Email to User
            user_subject = "Your Appointment Confirmation"
            user_body = (
                f"Dear {user_name},\n\n"
                f"Your appointment with {provider_name} for {service_type} "
                f"on {appointment_start_time} is confirmed.\n\n"
                f"Appointment ID: {new_appointment.id}\n\n"
                f"Regards,\nIntelligent Booking System"
            )
            send_email(user_email, user_subject, user_body)

            # Email to Provider
            provider_subject = "New Appointment Booking"
            provider_body = (
                f"Dear {provider_name},\n\n"
                f"You have a new appointment with {user_name} for your {service_type} service "
                f"on {appointment_start_time}.\n\n"
                f"Appointment ID: {new_appointment.id}\n"
                f"Booker's Email: {user_email}\n"
                f"Booker's Phone: {user.phone_number or 'Not provided'}\n\n"
                f"Regards,\nIntelligent Booking System"
            )
            send_email(provider_email, provider_subject, provider_body)
            
        except Exception as email_exc:
            # Log email sending failure but do not rollback transaction or fail the request
            print(f"CRITICAL: Failed to send confirmation emails for appointment {new_appointment.id}: {email_exc}")
        # --- End Email Notification ---

        return jsonify({
            'message': 'Appointment booked successfully',
            'appointment': {
                'id': new_appointment.id,
                'user_id': new_appointment.user_id,
                'provider_id': new_appointment.provider_id,
                'availability_id': new_appointment.availability_id,
                'start_time': new_appointment.start_time.isoformat(),
                'end_time': new_appointment.end_time.isoformat(),
                'status': new_appointment.status,
                'urgency_level': new_appointment.urgency_level
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        # Log the error e
        print(f"Error booking appointment: {e}") # Basic logging
        return jsonify({'message': 'Failed to book appointment due to an internal error'}), 500

@app.route('/api/messages', methods=['GET'])
@jwt_required()
def get_messages():
    recipient_user_id = get_jwt_identity()
    
    status = request.args.get('status', 'unread').lower()
    limit = request.args.get('limit', default=20, type=int)
    offset = request.args.get('offset', default=0, type=int)

    query = Message.query.filter_by(recipient_user_id=recipient_user_id)

    if status == 'read':
        query = query.filter_by(is_read=True)
    elif status == 'unread':
        query = query.filter_by(is_read=False)
    elif status != 'all':
        return jsonify({'message': 'Invalid status parameter. Use "read", "unread", or "all".'}), 400

    total_messages = query.count()
    messages = query.order_by(Message.created_at.desc()).limit(limit).offset(offset).all()

    output = []
    for msg in messages:
        output.append({
            'id': msg.id,
            'sender_user_id': msg.sender_user_id,
            'recipient_user_id': msg.recipient_user_id,
            'related_appointment_id': msg.related_appointment_id,
            'message_type': msg.message_type,
            'content': msg.content,
            'payload': msg.payload,
            'is_read': msg.is_read,
            'created_at': msg.created_at.isoformat(),
            'updated_at': msg.updated_at.isoformat(),
            'sender_full_name': msg.sender.full_name if msg.sender else None # Assuming User model has full_name
        })
    
    return jsonify({
        'messages': output,
        'total_messages': total_messages,
        'limit': limit,
        'offset': offset
    }), 200

@app.route('/api/messages/<int:message_id>/read', methods=['PUT'])
@jwt_required()
def mark_message_as_read(message_id):
    current_user_id = get_jwt_identity()
    
    message = Message.query.get(message_id)

    if not message:
        return jsonify({'message': 'Message not found'}), 404

    if message.recipient_user_id != current_user_id:
        return jsonify({'message': 'Forbidden: You are not the recipient of this message'}), 403

    if message.is_read:
        return jsonify({'message': 'Message already marked as read'}), 200 # Or 304 Not Modified

    message.is_read = True
    try:
        db.session.commit()
        return jsonify({
            'message': 'Message marked as read successfully',
            'message_details': {
                'id': message.id,
                'is_read': message.is_read,
                'updated_at': message.updated_at.isoformat()
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error marking message as read: {e}") # Basic logging
        return jsonify({'message': 'Failed to mark message as read due to an internal error'}), 500

@app.route('/api/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'Authenticated user not found'}), 404 # Should not happen

    data = request.get_json()
    rating = data.get('rating')
    comment = data.get('comment')
    feedback_type = data.get('feedback_type')
    appointment_id = data.get('appointment_id')

    if rating is None and not comment:
        return jsonify({'message': 'At least one of rating or comment must be provided'}), 400

    if rating is not None:
        try:
            rating = int(rating)
            if not (1 <= rating <= 5):
                raise ValueError("Rating out of range.")
        except ValueError:
            return jsonify({'message': 'Rating must be an integer between 1 and 5'}), 400
    
    if not feedback_type: # feedback_type is required
        return jsonify({'message': 'Missing required field: feedback_type'}), 400

    appointment = None
    if appointment_id is not None:
        try:
            appointment_id = int(appointment_id)
            appointment = Appointment.query.get(appointment_id)
            if not appointment:
                return jsonify({'message': f'Appointment with id {appointment_id} not found'}), 404
            # Optional: Validate if user is part of the appointment
            # provider_user_id = appointment.provider.user_id
            # if user_id != appointment.user_id and user_id != provider_user_id:
            #    return jsonify({'message': 'You are not authorized to leave feedback for this appointment'}), 403
        except ValueError:
            return jsonify({'message': 'Invalid appointment_id format. Must be an integer.'}), 400

    new_feedback = Feedback(
        user_id=user_id,
        rating=rating,
        comment=comment,
        feedback_type=feedback_type,
        appointment_id=appointment.id if appointment else None
    )

    try:
        db.session.add(new_feedback)
        db.session.commit()
        return jsonify({
            'message': 'Feedback submitted successfully',
            'feedback': {
                'id': new_feedback.id,
                'user_id': new_feedback.user_id,
                'rating': new_feedback.rating,
                'comment': new_feedback.comment,
                'feedback_type': new_feedback.feedback_type,
                'appointment_id': new_feedback.appointment_id,
                'created_at': new_feedback.created_at.isoformat()
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting feedback: {e}") # Basic logging
        return jsonify({'message': 'Failed to submit feedback due to an internal error'}), 500

if __name__ == '__main__':
    app.run(debug=True)
