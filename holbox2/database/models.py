from datetime import datetime
from .. import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    full_name = db.Column(db.String)
    phone_number = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    service_provider = db.relationship("ServiceProvider", uselist=False, back_populates="user")
    appointments = db.relationship("Appointment", back_populates="user", cascade="all, delete-orphan")
    sent_messages = db.relationship("Message", foreign_keys="[Message.sender_user_id]", back_populates="sender", cascade="all, delete-orphan")
    received_messages = db.relationship("Message", foreign_keys="[Message.recipient_user_id]", back_populates="recipient", cascade="all, delete-orphan")
    feedback_given = db.relationship("Feedback", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"

class ServiceProvider(db.Model):
    __tablename__ = 'service_providers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service_type = db.Column(db.String)
    bio = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="service_provider")
    availabilities = db.relationship("Availability", back_populates="provider", cascade="all, delete-orphan")
    appointments = db.relationship("Appointment", back_populates="provider", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ServiceProvider(id={self.id}, user_id={self.user_id}, service_type='{self.service_type}')>"

class Availability(db.Model):
    __tablename__ = 'availabilities'

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('service_providers.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    is_booked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    provider = db.relationship("ServiceProvider", back_populates="availabilities")
    appointment = db.relationship("Appointment", uselist=False, back_populates="availability_slot")

    def __repr__(self):
        return f"<Availability(id={self.id}, provider_id={self.provider_id}, start='{self.start_time}', end='{self.end_time}', booked={self.is_booked})>"

class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('service_providers.id'), nullable=False)
    availability_id = db.Column(db.Integer, db.ForeignKey('availabilities.id'), nullable=False, unique=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String, default='confirmed', nullable=False)
    urgency_level = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="appointments")
    provider = db.relationship("ServiceProvider", back_populates="appointments")
    availability_slot = db.relationship("Availability", back_populates="appointment")
    related_messages = db.relationship("Message", back_populates="related_appointment", cascade="all, delete-orphan")
    related_feedback = db.relationship("Feedback", back_populates="appointment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Appointment(id={self.id}, user_id={self.user_id}, provider_id={self.provider_id}, slot_id={self.availability_id}, status='{self.status}', urgency={self.urgency_level})>"

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    recipient_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    related_appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    
    message_type = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    payload = db.Column(db.JSON, nullable=True)
    
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sender = db.relationship("User", foreign_keys=[sender_user_id], back_populates="sent_messages")
    recipient = db.relationship("User", foreign_keys=[recipient_user_id], back_populates="received_messages")
    related_appointment = db.relationship("Appointment", back_populates="related_messages")

    def __repr__(self):
        return f"<Message(id={self.id}, from={self.sender_user_id}, to={self.recipient_user_id}, type='{self.message_type}', read={self.is_read})>"

class Feedback(db.Model):
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    
    rating = db.Column(db.Integer, nullable=True)
    comment = db.Column(db.Text, nullable=True)
    feedback_type = db.Column(db.String, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="feedback_given")
    appointment = db.relationship("Appointment", back_populates="related_feedback")

    def __repr__(self):
        return f"<Feedback(id={self.id}, user_id={self.user_id}, rating={self.rating}, type='{self.feedback_type}')>" 