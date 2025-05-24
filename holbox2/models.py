from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON # Added JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String)
    phone_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    service_provider = relationship("ServiceProvider", uselist=False, back_populates="user")
    appointments = relationship("Appointment", back_populates="user", cascade="all, delete-orphan")
    sent_messages = relationship("Message", foreign_keys="[Message.sender_user_id]", back_populates="sender", cascade="all, delete-orphan")
    received_messages = relationship("Message", foreign_keys="[Message.recipient_user_id]", back_populates="recipient", cascade="all, delete-orphan")
    feedback_given = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"

class ServiceProvider(Base):
    __tablename__ = 'service_providers'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    service_type = Column(String)
    bio = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="service_provider")
    availabilities = relationship("Availability", back_populates="provider", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="provider", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ServiceProvider(id={self.id}, user_id={self.user_id}, service_type='{self.service_type}')>"

class Availability(Base):
    __tablename__ = 'availabilities'

    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey('service_providers.id'), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_booked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    provider = relationship("ServiceProvider", back_populates="availabilities")
    appointment = relationship("Appointment", uselist=False, back_populates="availability_slot")


    def __repr__(self):
        return f"<Availability(id={self.id}, provider_id={self.provider_id}, start='{self.start_time}', end='{self.end_time}', booked={self.is_booked})>"

class Appointment(Base):
    __tablename__ = 'appointments'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    provider_id = Column(Integer, ForeignKey('service_providers.id'), nullable=False)
    availability_id = Column(Integer, ForeignKey('availabilities.id'), nullable=False, unique=True)
    start_time = Column(DateTime, nullable=False) # Denormalized
    end_time = Column(DateTime, nullable=False) # Denormalized
    status = Column(String, default='confirmed', nullable=False) # e.g., "confirmed", "cancelled", "pending"
    urgency_level = Column(Integer, nullable=False, default=0) # 0: Normal, 1: High
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="appointments")
    provider = relationship("ServiceProvider", back_populates="appointments")
    availability_slot = relationship("Availability", back_populates="appointment")
    related_messages = relationship("Message", back_populates="related_appointment", cascade="all, delete-orphan")
    related_feedback = relationship("Feedback", back_populates="appointment", cascade="all, delete-orphan")


    def __repr__(self):
        return f"<Appointment(id={self.id}, user_id={self.user_id}, provider_id={self.provider_id}, slot_id={self.availability_id}, status='{self.status}', urgency={self.urgency_level})>"

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    sender_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    recipient_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    related_appointment_id = Column(Integer, ForeignKey('appointments.id'), nullable=True)
    
    message_type = Column(String, nullable=False) # e.g., "STATUS_UPDATE", "RESCHEDULE_REQUEST"
    content = Column(Text, nullable=False)
    payload = Column(JSON, nullable=True) # For structured data
    
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sender = relationship("User", foreign_keys=[sender_user_id], back_populates="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_user_id], back_populates="received_messages")
    related_appointment = relationship("Appointment", back_populates="related_messages")

    def __repr__(self):
        return f"<Message(id={self.id}, from={self.sender_user_id}, to={self.recipient_user_id}, type='{self.message_type}', read={self.is_read})>"

class Feedback(Base):
    __tablename__ = 'feedback'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    appointment_id = Column(Integer, ForeignKey('appointments.id'), nullable=True)
    
    rating = Column(Integer, nullable=True) # e.g., 1-5
    comment = Column(Text, nullable=True)
    feedback_type = Column(String, nullable=True) # e.g., "scheduling_experience", "slot_suggestion_quality"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="feedback_given")
    appointment = relationship("Appointment", back_populates="related_feedback")

    def __repr__(self):
        return f"<Feedback(id={self.id}, user_id={self.user_id}, rating={self.rating}, type='{self.feedback_type}')>"
