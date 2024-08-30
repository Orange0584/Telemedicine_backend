from django.db import models
from pymongo import MongoClient, errors
from bson import ObjectId
from datetime import datetime
from django.contrib.auth.hashers import make_password
import os
from pymongo.errors import PyMongoError
from dotenv import load_dotenv
from datetime import date
# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DB = os.getenv('MONGODB_DB')

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]

class UserModel:
    def __init__(self, username, password, email, role, age, gender):
        if role not in ['doctor', 'user']:
            raise ValueError("Invalid role")
        if age <= 18:
            raise ValueError("Age must be greater than 18")
        self._id = ObjectId()
        self.username = username
        self.password = make_password(password)
        self.created_date = datetime.now()
        self.email = email
        self.role = role
        self.age = age
        self.gender = gender
        if role == "doctor":
            self.verified = False
        if role == "user":
            self.verified = True

    def save(self):
        try:
            db.users.create_index("username", unique=True)
            db.users.create_index("email", unique=True)
            db.users.insert_one(self.__dict__)
        except errors.DuplicateKeyError:
            raise ValueError("Username or Email already exists")
        

class MedicinalItem:
    def __init__(self, name, description, amount, category, quantity, image, expiration_date):
        self.name = name
        self.description = description
        self.amount = amount
        self.category = category
        self.quantity = quantity
        self.expiration_date = expiration_date
        self.image = image

    def save(self):
        try:
            db.medicinal_items.insert_one(self.__dict__)
        except PyMongoError as e:
            raise ValueError(f"Database error: {e}")
        

class DoctorModel:
    def __init__(self, name, age, experience, field, medical_license_number, issuing_authority, education,  user_id):
        self._id = ObjectId()
        self.name = name
        self.age = age
        self.experience = experience
        self.field = field
        self.medical_license_number = medical_license_number
        self.issuing_authority = issuing_authority
        self.education = education
        self.user_id = user_id

    def save(self):
        db.doctors.insert_one(self.__dict__)

class ChatRoom:
    def __init__(self, user1_id, user2_id):
        self._id = ObjectId()
        self.user1_id = ObjectId(user1_id)
        self.user2_id = ObjectId(user2_id)
        self.created_date = datetime.now()

    def save(self):
        db.chat_rooms.insert_one(self.__dict__)

class ChatMessage:
    def __init__(self, room_id, sender_id, receiver_id, message):
        self._id = ObjectId()
        self.room_id = ObjectId(room_id)
        self.sender_id = ObjectId(sender_id)
        self.receiver_id = ObjectId(receiver_id)
        self.message = message
        self.timestamp = datetime.now()

    def save(self):
        db.chat_messages.insert_one(self.__dict__)