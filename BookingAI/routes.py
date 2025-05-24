from flask import request, jsonify, send_from_directory, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from . import db
from .database.models import User, ServiceProvider, Availability, Appointment, Message, Feedback, CallRequest
from .services.email_service import send_email
from datetime import datetime, timezone, time, timedelta
import os
import uuid
import re

# In-memory storage for active calls
active_calls = {}

def init_routes(app):
    @app.route('/')
    def serve_index():
        return render_template('index.html')

    @app.route('/<path:path>')
    def serve_static_files(path):
        return send_from_directory(app.static_folder, path)

    @app.route('/api/users/register', methods=['POST'])
    def register_user():
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        phone_number = data.get('phone_number')

        if not email or not password or not full_name:
            return jsonify({'message': 'Missing required fields'}), 400

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
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'message': 'Missing email or password'}), 400

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'message': 'Invalid email or password'}), 401

        access_token = create_access_token(identity=user.id)
        return jsonify({
            'access_token': access_token,
            'user_id': user.id,
            'email': user.email
        }), 200

    @app.route('/api/providers/register', methods=['POST'])
    @jwt_required()
    def register_service_provider():
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if ServiceProvider.query.filter_by(user_id=user_id).first():
            return jsonify({'message': 'User is already registered as a service provider'}), 409

        new_provider = ServiceProvider(
            user_id=user_id,
            service_type=data.get('service_type'),
            bio=data.get('bio')
        )
        db.session.add(new_provider)
        db.session.commit()

        return jsonify({
            'message': 'Service provider registered successfully',
            'provider_id': new_provider.id
        }), 201

    @app.route('/api/providers/availability', methods=['POST', 'GET'])
    @jwt_required()
    def manage_availability():
        if request.method == 'POST':
            return add_availability_slot()
        return get_availability_slots()

    def add_availability_slot():
        user_id = get_jwt_identity()
        provider = ServiceProvider.query.filter_by(user_id=user_id).first()
        if not provider:
            return jsonify({'message': 'User is not a service provider'}), 403

        data = request.get_json()
        start_time = datetime.fromisoformat(data.get('start_time'))
        end_time = datetime.fromisoformat(data.get('end_time'))

        if start_time >= end_time:
            return jsonify({'message': 'Start time must be before end time'}), 400

        # Check for overlapping slots
        overlapping = Availability.query.filter(
            Availability.provider_id == provider.id,
            Availability.start_time < end_time,
            Availability.end_time > start_time
        ).first()

        if overlapping:
            return jsonify({'message': 'Time slot overlaps with existing availability'}), 409

        new_slot = Availability(
            provider_id=provider.id,
            start_time=start_time,
            end_time=end_time
        )
        db.session.add(new_slot)
        db.session.commit()

        return jsonify({
            'message': 'Availability slot added successfully',
            'slot_id': new_slot.id
        }), 201

    def get_availability_slots():
        user_id = get_jwt_identity()
        provider = ServiceProvider.query.filter_by(user_id=user_id).first()
        if not provider:
            return jsonify({'message': 'User is not a service provider'}), 403

        slots = Availability.query.filter_by(provider_id=provider.id).all()
        return jsonify({
            'slots': [{
                'id': slot.id,
                'start_time': slot.start_time.isoformat(),
                'end_time': slot.end_time.isoformat(),
                'is_booked': slot.is_booked
            } for slot in slots]
        }), 200

    @app.route('/api/availability', methods=['GET'])
    def query_available_slots():
        provider_id = request.args.get('provider_id', type=int)
        service_type = request.args.get('service_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        preferred_time = request.args.get('preferred_time')  # 'morning', 'afternoon', 'evening'

        query = Availability.query.filter_by(is_booked=False)

        if provider_id:
            query = query.filter_by(provider_id=provider_id)
        elif service_type:
            provider_ids = [p.id for p in ServiceProvider.query.filter_by(service_type=service_type)]
            query = query.filter(Availability.provider_id.in_(provider_ids))

        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(Availability.start_time >= start_dt)
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(Availability.end_time <= end_dt)

        slots = query.all()

        if preferred_time:
            def is_preferred_time(slot):
                hour = slot.start_time.hour
                if preferred_time == 'morning':
                    return 6 <= hour < 12
                elif preferred_time == 'afternoon':
                    return 12 <= hour < 17
                elif preferred_time == 'evening':
                    return 17 <= hour < 22
                return True

            slots = [slot for slot in slots if is_preferred_time(slot)]

        return jsonify({
            'available_slots': [{
                'id': slot.id,
                'provider_id': slot.provider_id,
                'provider_name': slot.provider.user.full_name,
                'service_type': slot.provider.service_type,
                'start_time': slot.start_time.isoformat(),
                'end_time': slot.end_time.isoformat()
            } for slot in slots]
        }), 200

    @app.route('/api/appointments/book', methods=['POST'])
    @jwt_required()
    def book_appointment():
        user_id = get_jwt_identity()
        data = request.get_json()
        slot_id = data.get('slot_id')
        urgency_level = data.get('urgency_level', 0)

        if not slot_id:
            return jsonify({'message': 'Missing slot_id'}), 400

        slot = Availability.query.get(slot_id)
        if not slot:
            return jsonify({'message': 'Invalid slot_id'}), 404
        if slot.is_booked:
            return jsonify({'message': 'Slot is already booked'}), 409

        appointment = Appointment(
            user_id=user_id,
            provider_id=slot.provider_id,
            availability_id=slot.id,
            start_time=slot.start_time,
            end_time=slot.end_time,
            urgency_level=urgency_level
        )

        slot.is_booked = True
        db.session.add(appointment)
        db.session.commit()

        # Send confirmation emails
        user = User.query.get(user_id)
        provider = slot.provider.user
        
        user_msg = f"Your appointment has been confirmed for {slot.start_time}"
        provider_msg = f"New appointment scheduled for {slot.start_time}"
        
        send_email(user.email, "Appointment Confirmation", user_msg)
        send_email(provider.email, "New Appointment", provider_msg)

        return jsonify({
            'message': 'Appointment booked successfully',
            'appointment_id': appointment.id
        }), 201

    @app.route('/api/appointments/call', methods=['POST'])
    @jwt_required()
    def schedule_call_appointment():
        user_id = get_jwt_identity()
        data = request.get_json()
        
        service_type = data.get('service_type')
        phone_number = data.get('phone_number')
        preferred_time = data.get('preferred_time')  # 'morning', 'afternoon', 'evening'
        preferred_date = data.get('preferred_date')
        notes = data.get('notes', '')

        if not all([service_type, phone_number, preferred_time, preferred_date]):
            return jsonify({'message': 'Missing required fields'}), 400

        # Create call request
        call_request = CallRequest(
            user_id=user_id,
            service_type=service_type,
            phone_number=phone_number,
            preferred_time=preferred_time,
            preferred_date=datetime.fromisoformat(preferred_date),
            notes=notes,
            status='pending'
        )
        db.session.add(call_request)
        db.session.commit()

        # Notify available agents
        available_agents = ServiceProvider.query.filter_by(service_type=service_type).all()
        for agent in available_agents:
            message = Message(
                sender_id=user_id,
                receiver_id=agent.user_id,
                content=f"New call request from {call_request.user.full_name} for {service_type} service",
                call_request_id=call_request.id
            )
            db.session.add(message)

        db.session.commit()

        # Send confirmation email to user
        send_email(
            to=call_request.user.email,
            subject="Call Request Received",
            body=f"Your call request has been received. An agent will contact you at {preferred_time} on {preferred_date}."
        )

        return jsonify({
            'message': 'Call request scheduled successfully',
            'call_request_id': call_request.id
        }), 201

    @app.route('/api/appointments/call/<int:call_id>/accept', methods=['POST'])
    @jwt_required()
    def accept_call_request(call_id):
        agent_id = get_jwt_identity()
        agent = ServiceProvider.query.filter_by(user_id=agent_id).first()
        
        if not agent:
            return jsonify({'message': 'User is not a service provider'}), 403

        call_request = CallRequest.query.get_or_404(call_id)
        
        if call_request.status != 'pending':
            return jsonify({'message': 'Call request is no longer available'}), 400

        call_request.status = 'accepted'
        call_request.agent_id = agent_id
        db.session.commit()

        # Notify user
        message = Message(
            sender_id=agent_id,
            receiver_id=call_request.user_id,
            content=f"Your call request has been accepted by {agent.user.full_name}. They will call you at the scheduled time.",
            call_request_id=call_id
        )
        db.session.add(message)
        db.session.commit()

        # Send email notification
        send_email(
            to=call_request.user.email,
            subject="Call Request Accepted",
            body=f"Your call request has been accepted by {agent.user.full_name}. They will call you at the scheduled time."
        )

        return jsonify({'message': 'Call request accepted successfully'}), 200

    @app.route('/api/appointments/call/<int:call_id>/complete', methods=['POST'])
    @jwt_required()
    def complete_call_request(call_id):
        agent_id = get_jwt_identity()
        call_request = CallRequest.query.get_or_404(call_id)
        
        if call_request.agent_id != agent_id:
            return jsonify({'message': 'Unauthorized'}), 403

        call_request.status = 'completed'
        call_request.completed_at = datetime.now(timezone.utc)
        db.session.commit()

        # Notify user
        message = Message(
            sender_id=agent_id,
            receiver_id=call_request.user_id,
            content="Your call has been completed. Please provide feedback on your experience.",
            call_request_id=call_id
        )
        db.session.add(message)
        db.session.commit()

        return jsonify({'message': 'Call marked as completed'}), 200

    @app.route('/api/messages', methods=['GET'])
    @jwt_required()
    def get_messages():
        user_id = get_jwt_identity()
        messages = Message.query.filter(
            (Message.sender_id == user_id) | (Message.receiver_id == user_id)
        ).order_by(Message.created_at.desc()).all()

        return jsonify({
            'messages': [{
                'id': msg.id,
                'sender_id': msg.sender_id,
                'sender_name': msg.sender.full_name,
                'receiver_id': msg.receiver_id,
                'receiver_name': msg.receiver.full_name,
                'content': msg.content,
                'created_at': msg.created_at.isoformat(),
                'is_read': msg.is_read,
                'call_request_id': msg.call_request_id
            } for msg in messages]
        }), 200

    @app.route('/api/messages', methods=['POST'])
    @jwt_required()
    def send_message():
        user_id = get_jwt_identity()
        data = request.get_json()
        
        receiver_id = data.get('receiver_id')
        content = data.get('content')
        call_request_id = data.get('call_request_id')

        if not all([receiver_id, content]):
            return jsonify({'message': 'Missing required fields'}), 400

        message = Message(
            sender_id=user_id,
            receiver_id=receiver_id,
            content=content,
            call_request_id=call_request_id
        )
        db.session.add(message)
        db.session.commit()

        # Send email notification
        receiver = User.query.get(receiver_id)
        send_email(
            to=receiver.email,
            subject="New Message",
            body=f"You have received a new message: {content}"
        )

        return jsonify({
            'message': 'Message sent successfully',
            'message_id': message.id
        }), 201

    @app.route('/api/feedback', methods=['POST'])
    @jwt_required()
    def submit_feedback():
        user_id = get_jwt_identity()
        data = request.get_json()
        
        feedback = Feedback(
            user_id=user_id,
            appointment_id=data.get('appointment_id'),
            rating=data.get('rating'),
            comment=data.get('comment'),
            feedback_type=data.get('feedback_type')
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            'message': 'Feedback submitted successfully',
            'feedback_id': feedback.id
        }), 201

    @app.route('/api/call/start', methods=['POST'])
    def start_ai_call():
        data = request.get_json()
        phone_number = data.get('phone_number')
        department = data.get('department')
        
        if not phone_number or not department:
            return jsonify({'message': 'Phone number and department are required'}), 400
        
        call_id = str(uuid.uuid4())
        active_calls[call_id] = {
            'phone_number': phone_number,
            'department': department,
            'history': [],
            'voice_enabled': True,
            'start_time': datetime.utcnow()
        }
        
        greeting = f"Hello! I'm your AI assistant for the {department} department. I can help you schedule or reschedule appointments, answer questions, or assist with any other inquiries. How may I help you today?"
        
        active_calls[call_id]['history'].append({
            'role': 'assistant',
            'content': greeting,
            'timestamp': datetime.utcnow()
        })
        
        return jsonify({
            'call_id': call_id,
            'message': greeting
        })

    @app.route('/api/call/<call_id>/interact', methods=['POST'])
    def interact_with_ai(call_id):
        if call_id not in active_calls:
            return jsonify({'message': 'Call session not found'}), 404
        
        data = request.get_json()
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({'message': 'Message is required'}), 400
        
        # Add user message to history
        active_calls[call_id]['history'].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.utcnow()
        })
        
        # Process the message
        response = process_user_message(user_message, active_calls[call_id]['department'])
        
        # Add AI response to history
        active_calls[call_id]['history'].append({
            'role': 'assistant',
            'content': response['message'],
            'timestamp': datetime.utcnow()
        })
        
        # Check for long silence
        if len(active_calls[call_id]['history']) > 2:
            last_user_message = next((msg for msg in reversed(active_calls[call_id]['history']) 
                                    if msg['role'] == 'user'), None)
            if last_user_message:
                time_since_last_message = datetime.utcnow() - last_user_message['timestamp']
                if time_since_last_message.total_seconds() > 30:  # 30 seconds of silence
                    response['message'] += "\nI notice you've been quiet for a while. Are you still there? I'm here to help you schedule an appointment or answer any questions you might have."
        
        return jsonify(response)

    @app.route('/api/call/<call_id>/end', methods=['POST'])
    def end_ai_call(call_id):
        if call_id not in active_calls:
            return jsonify({'message': 'Call session not found'}), 404
        
        # Store call history in database
        call_history = active_calls[call_id]
        call_history['end_time'] = datetime.utcnow()
        call_history['status'] = 'completed'
        
        # TODO: Store call history in database
        
        # Remove from active calls
        del active_calls[call_id]
        
        return jsonify({'message': 'Call ended successfully'})

    def process_user_message(message, department):
        message = message.lower()
        
        # Appointment scheduling
        if any(word in message for word in ['schedule', 'book', 'appointment', 'make an appointment']):
            # Extract date and time using regex
            date_match = re.search(r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december))', message)
            time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))', message)
            
            if date_match and time_match:
                date = date_match.group(1)
                time = time_match.group(1)
                
                # Check if the requested time slot is available
                requested_datetime = datetime.strptime(f"{date} {time}", "%d %B %I:%M %p")
                
                # Check for availability
                available_slots = Availability.query.filter(
                    Availability.start_time >= requested_datetime,
                    Availability.start_time < requested_datetime + timedelta(hours=1),
                    Availability.is_booked == False
                ).all()
                
                if available_slots:
                    # Slot is available
                    return {
                        'message': f"I've found an available slot for {date} at {time}. Would you like me to confirm this appointment for you?",
                        'appointment_scheduled': True,
                        'appointment_details': {
                            'date': date,
                            'time': time,
                            'provider': 'Dr. Smith'  # This would be dynamically assigned in a real system
                        }
                    }
                else:
                    # Find next available slots
                    next_available = Availability.query.filter(
                        Availability.start_time > requested_datetime,
                        Availability.is_booked == False
                    ).order_by(Availability.start_time).limit(3).all()
                    
                    if next_available:
                        alternative_times = [slot.start_time.strftime("%B %d at %I:%M %p") for slot in next_available]
                        return {
                            'message': f"I apologize, but {date} at {time} is not available. However, I can offer you these alternative times:\n" +
                                     "\n".join([f"- {time}" for time in alternative_times]) +
                                     "\nWould you like to schedule for any of these times instead?",
                            'alternative_slots': alternative_times
                        }
                    else:
                        return {
                            'message': f"I apologize, but I couldn't find any available slots near {date} at {time}. Would you like me to check availability for a different date or time?"
                        }
            else:
                return {
                    'message': "I'd be happy to help you schedule an appointment. Could you please tell me what date and time you'd prefer? For example, you could say 'I'd like to schedule for March 15th at 2 PM'."
                }
        
        # Confirm appointment
        elif any(word in message for word in ['yes', 'confirm', 'sure', 'okay', 'fine']):
            return {
                'message': "Great! I'll confirm your appointment. You'll receive a confirmation email shortly. Is there anything else you need help with?",
                'appointment_confirmed': True
            }
        
        # Reschedule request
        elif any(word in message for word in ['reschedule', 'change time', 'different time', 'another time']):
            return {
                'message': "I can help you reschedule your appointment. Could you please tell me your preferred new date and time? For example, you could say 'I'd like to reschedule for March 20th at 3 PM'."
            }
        
        # Hours inquiry
        elif any(word in message for word in ['hours', 'open', 'close', 'when are you open']):
            return {
                'message': f"Our {department} department is open Monday through Friday from 9 AM to 5 PM, and Saturday from 9 AM to 1 PM. We're closed on Sundays and major holidays."
            }
        
        # Emergency handling
        elif any(word in message for word in ['emergency', 'urgent', 'immediately', 'right now']):
            return {
                'message': "I understand this is an emergency. For immediate medical attention, please call our emergency line at 911 or visit the nearest emergency room. Would you like me to connect you with our emergency services?"
            }
        
        # Help request
        elif any(word in message for word in ['help', 'what can you do', 'how can you help']):
            return {
                'message': f"I can help you with several things in the {department} department:\n"
                          f"1. Schedule appointments\n"
                          f"2. Reschedule existing appointments\n"
                          f"3. Provide information about our services\n"
                          f"4. Answer questions about our hours and location\n"
                          f"5. Connect you with emergency services if needed\n"
                          f"What would you like help with?"
            }
        
        # End call
        elif any(word in message for word in ['goodbye', 'bye', 'end call', 'hang up']):
            return {
                'message': "Thank you for calling. Is there anything else you need help with before we end the call?"
            }
        
        # Default response
        else:
            return {
                'message': f"I'm here to help you with the {department} department. You can ask me about scheduling or rescheduling appointments, our services, or any other questions you might have. What would you like to know?"
            } 