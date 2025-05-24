from flask import request, jsonify, send_from_directory, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from . import db
from .database.models import User, ServiceProvider, Availability, Appointment, Message, Feedback
from .services.email_service import send_email
from datetime import datetime, timezone, time
import os

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

    @app.route('/api/messages', methods=['GET'])
    @jwt_required()
    def get_messages():
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        unread_only = request.args.get('unread_only', False, type=bool)

        query = Message.query.filter_by(recipient_user_id=user_id)
        if unread_only:
            query = query.filter_by(is_read=False)

        messages = query.order_by(Message.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'messages': [{
                'id': msg.id,
                'sender_id': msg.sender_user_id,
                'content': msg.content,
                'message_type': msg.message_type,
                'is_read': msg.is_read,
                'created_at': msg.created_at.isoformat()
            } for msg in messages.items],
            'total': messages.total,
            'pages': messages.pages,
            'current_page': messages.page
        }), 200

    @app.route('/api/messages/<int:message_id>/read', methods=['PUT'])
    @jwt_required()
    def mark_message_as_read(message_id):
        user_id = get_jwt_identity()
        message = Message.query.get_or_404(message_id)
        
        if message.recipient_user_id != user_id:
            return jsonify({'message': 'Unauthorized'}), 403
        
        if not message.is_read:
            message.is_read = True
            db.session.commit()
        
        return jsonify({'message': 'Message marked as read'}), 200

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