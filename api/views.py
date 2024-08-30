from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from pymongo import MongoClient
from .models import UserModel, MedicinalItem, DoctorModel, ChatMessage, ChatRoom
from .serializers import UserSerializer, MedicinalItemSerializer
import jwt # type: ignore
from django.conf import settings
from django.contrib.auth.hashers import check_password
import os
from dotenv import load_dotenv # type: ignore
import base64
from django.core.files.storage import default_storage
from .decoraters import jwt_required
from bson import ObjectId
from datetime import datetime, date, timedelta
from django.http import JsonResponse
import pymongo
import re

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DB = os.getenv('MONGODB_DB')
SECRET_KEY = os.getenv('SECRET_KEY')

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]


def get_current_site(request):
    scheme = request.scheme  # 'http' or 'https'
    host = request.get_host()  # e.g. 'example.com'
    full_url = f"{scheme}://{host}"
    return full_url

@api_view(['POST'])
def signup(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        try:
            user = UserModel(**serializer.validated_data)
            user.save()
            user = db.users.find_one({"email": serializer.validated_data.get('email')})
            user_info = {
                'user_id': str(user['_id']),
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'gender': user['gender']
            }
            payload = {
                'user_id': str(user['_id']),
                'exp': datetime.utcnow() + timedelta(hours=1)  # Set token expiry as needed
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
            return Response({'message': 'User created successfully', 'data': user_info, 'access': token,}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')
    user = db.users.find_one({"email": email})

    if user and check_password(password, user['password']):
        payload = {
            'user_id': str(user['_id']),
            'exp': datetime.utcnow() + timedelta(hours=1)  # Set token expiry as needed
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        if user['verified']:
            user_info = {
                'user_id': str(user['_id']),
                'username': user['username'],
                'email': user['email'],
                'role': user['role']
            }
            return Response({'access': token, 'user': user_info}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Your account is currently pending verification. Once your professional details have been verified, you will be able to access your account.'}, status=status.HTTP_401_UNAUTHORIZED)
    return Response({'message': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def logout(request):
    # Implement logout functionality if needed
    return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)


@api_view(['GET'])
def check_auth(request):
    token = request.META.get('HTTP_AUTHORIZATION')
    if token:
        try:
            token = token.split()[1]
            decoded = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            print(decoded)
            return Response({'message': 'Authenticated', 'user_id': str(decoded['user_id'])}, status=status.HTTP_200_OK)
        except jwt.ExpiredSignatureError:
            return Response({'message': 'Token expired'}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({'message': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
    return Response({'message': 'Token required'}, status=status.HTTP_401_UNAUTHORIZED)


def handle_base64_image(base64_image, name):
    """Decodes base64 image and saves it to the media directory."""
    # Replace spaces and invalid characters in the name
    name = re.sub(r'[^\w\s-]', '', name).replace(' ', '_')

    # Ensure the media directory exists
    media_root = settings.MEDIA_ROOT
    if not os.path.exists(media_root):
        os.makedirs(media_root)

    # Decode the base64 image
    try:
        format, imgstr = base64_image.split(';base64,')
        ext = format.split('/')[-1]
        img_data = base64.b64decode(imgstr)
    except Exception as e:
        raise ValueError(f"Invalid base64 image format: {e}")

    # Generate a safe filename with a timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    image_name = f"{name}_{timestamp}.{ext}"
    image_path = os.path.join(media_root, image_name)

    # Save the image
    try:
        with open(image_path, 'wb') as f:
            f.write(img_data)
    except OSError as e:
        raise OSError(f"Error saving image: {e}")

    return image_name


@api_view(['GET', 'POST'])
@jwt_required
def medicinal_item_list_create(request):
    if request.method == 'GET':
        items = list(db.medicinal_items.find())
        for item in items:
            item['_id'] = str(item['_id'])
        return Response(items)

    elif request.method == 'POST':
        data = request.data.copy()  # Use copy to allow modification
        base64_image = data.get('image')
        if base64_image:
            image_name = handle_base64_image(base64_image, data.get('name'))
            if image_name:
                image_url = default_storage.url(image_name)
                data['image'] = f"{get_current_site(request)}{image_url}"
        
        # Check if an item with the same name already exists
        existing_item = db.medicinal_items.find_one({'name': data.get('name')})
        if existing_item:
            return Response({'error': 'Item with this name already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MedicinalItemSerializer(data=data)
        if serializer.is_valid():
            item = MedicinalItem(**serializer.validated_data)
            item.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET', 'PUT', 'DELETE'])
@jwt_required
def medicinal_item_detail(request, pk):
    try:
        item = db.medicinal_items.find_one({'_id': ObjectId(pk)})
        if item:
            item['_id'] = str(item['_id'])
    except:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(item)

    elif request.method == 'PUT':
        data = request.data.copy()  # Use copy to allow modification
        base64_image = data.get('image')
        expiration_date = data.get('expiration_date')
        print(expiration_date, type(expiration_date))
        if isinstance(expiration_date, str):
            try:
                expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d').date()
                data['expiration_date'] = expiration_date.isoformat()
            except ValueError:
                pass

        if base64_image:
            image_name = handle_base64_image(base64_image, data.get('name'))
            print(image_name,'-----------')
            if image_name:
                image_url = default_storage.url(image_name)
                data['image'] = f"{get_current_site(request)}{image_url}"

        serializer = MedicinalItemSerializer(data=data)
        if serializer.is_valid():
            db.medicinal_items.update_one({'_id': ObjectId(pk)}, {'$set': serializer.validated_data})
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        db.medicinal_items.delete_one({'_id': ObjectId(pk)})
        return Response(status=status.HTTP_204_NO_CONTENT)
    

@api_view(['GET'])
@jwt_required
def fetch_category_items(request, category):
    try:
        # Fetch items with the specified category
        items = list(db.medicinal_items.find({'category': category}))
        
        # Convert ObjectId to string for JSON serialization
        for item in items:
            item['_id'] = str(item['_id'])
        
        return JsonResponse(items, safe=False)
    except pymongo.errors.PyMongoError as e:
        # Log the exception if needed
        print(f"Database error: {e}")
        return JsonResponse({'error': 'An error occurred while fetching data.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
@jwt_required
def fetch_all_doctors(request):
    try:
        # Fetch doctors with role 'doctor' and include _id, username, and email fields
        doctors = list(db.users.find({'role': 'doctor'}, {'_id': 1, 'username': 1, 'email': 1}))
        
        # Iterate over the list of doctors and convert _id to string
        for doctor in doctors:
            print(doctor)
            doctor['_id'] = str(doctor['_id'])
            # Fetch the doctor's profile from the doctors collection
            profile = db.doctors.find_one({'user_id':  str(doctor['_id'])})
            print(profile)
            if profile:
                # Add relevant profile information to the doctor object
                doctor['profile'] = {
                    'name': profile.get('name'),
                    'age': profile.get('age'),
                    'experience': profile.get('experience'),
                    'field': profile.get('field')
                }
        
        return JsonResponse(doctors, safe=False)
    except pymongo.errors.PyMongoError as e:
        # Log the exception if needed
        print(f"Database error: {e}")
        return JsonResponse({'error': 'An error occurred while fetching data.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@jwt_required
def add_to_cart(request):
    try:
        user_id = request.data.get('user_id')  # ID of the user whose cart is being updated
        item_ids = request.data.get('item_ids')  # List of item IDs to be added
        quantity = request.data.get('quantity', 1)  # Quantity of the item to be added (default is 1)

        print(user_id, item_ids)

        # Ensure valid input
        if not user_id or not item_ids:
            return Response({'error': 'User and Product are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the user has a cart
        cart = db.cart.find_one({'_id': ObjectId(user_id)})

        if cart:
            # Update existing cart
            items = cart.get('items', [])
            for item_id in item_ids:
                item_exists = False

                for item in items:
                    if item['item_id'] == item_id:
                        item['quantity'] += quantity
                        item_exists = True
                        break

                if not item_exists:
                    items.append({'item_id': item_id, 'quantity': quantity})

            db.cart.update_one({'_id': ObjectId(user_id)}, {'$set': {'items': items}})
        else:
            # Create a new cart
            new_items = [{'item_id': item_id, 'quantity': quantity} for item_id in item_ids]
            db.cart.insert_one({
                '_id': ObjectId(user_id),
                'items': new_items
            })

        return Response({'message': 'Items added to cart successfully.'})
    except pymongo.errors.PyMongoError as e:
        # Log the exception if needed
        print(f"Database error: {e}")
        return Response({'error': 'An error occurred while updating the cart.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@jwt_required
def get_cart_items(request):
    try:
        user_id = request.data.get('user_id') 
        if not user_id:
            return Response({'error': 'User ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the user's cart
        cart = db.cart.find_one({'_id': ObjectId(user_id)})
        if not cart:
            return Response({'message': 'Cart not found for this user.'}, status=status.HTTP_404_NOT_FOUND)

        items = cart.get('items', [])
        if not items:
            return Response({'message': 'Cart is empty.'}, status=status.HTTP_200_OK)

        # Fetch item details
        for item in items:
            item['item_id'] = str(item['item_id'])
            # Fetch item details from the items collection
            item_details = db.medicinal_items.find_one({'_id': ObjectId(item['item_id'])})
            if item_details:
                item.update({
                    'item_name': item_details.get('name', 'N/A'),
                    'item_price': item_details.get('amount', 'N/A'),
                    'item_description': item_details.get('description', 'N/A'),
                    'expiration_date': item_details.get('expiration_date', 'N/A'),
                    'image' : item_details.get('image', 'N/A'),
                })
            else:
                # In case the item details are not found
                item.update({
                    'item_name': 'Unknown',
                    'item_price': 'Unknown',
                    'item_description': 'No description available',
                    'expiration_date': 'N/A',
                    'image' : 'N/A',
                })

        return Response({'cart': {'user_id': str(user_id), 'items': items}})

    except pymongo.errors.PyMongoError as e:
        # Log the exception if needed
        print(f"Database error: {e}")
        return Response({'error': 'An error occurred while fetching cart items.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@jwt_required
def checkout_cart(request):
    try:
        user_id = request.data.get('user_id')  # ID of the user checking out
        if not user_id:
            return Response({'error': 'User ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the user's cart
        cart = db.cart.find_one({'_id': ObjectId(user_id)})
        if not cart:
            return Response({'error': 'Cart not found.'}, status=status.HTTP_404_NOT_FOUND)

        items = cart.get('items', [])
        if not items:
            return Response({'error': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create an order entry
        order_id = ObjectId()
        order = {
            '_id': order_id,
            'user_id': ObjectId(user_id),
            'items': items,
            'created_date': datetime.now()
        }
        db.orders.insert_one(order)

        # Remove items from the cart
        db.cart.delete_one({'_id': ObjectId(user_id)})

        return Response({'message': 'Order created and cart cleared successfully.', 'order_id': str(order_id)})

    except pymongo.errors.PyMongoError as e:
        # Log the exception if needed
        print(f"Database error: {e}")
        return Response({'error': 'An error occurred while processing the order.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@jwt_required
def get_user_orders(request):
    try:
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'User ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the user's orders
        orders = list(db.orders.find({'user_id': ObjectId(user_id)}))
        if not orders:
            return Response({'message': 'No orders found for this user.'}, status=status.HTTP_404_NOT_FOUND)

        # Convert ObjectId to string for JSON serialization
        for order in orders:
            order['_id'] = str(order['_id'])
            order['user_id'] = str(order['user_id'])
            for item in order.get('items', []):
                item['item_id'] = str(item['item_id'])

                # Fetch item details from the items collection
                item_details = db.medicinal_items.find_one({'_id': ObjectId(item['item_id'])})
                if item_details:
                    item.update({
                        'item_name': item_details.get('name', 'N/A'),
                        'item_price': item_details.get('amount', 'N/A'),
                        'item_description': item_details.get('description', 'N/A'),
                        'expiration_date': item_details.get('expiration_date', 'N/A'),
                        'image' : item_details.get('image', 'N/A'),
                    })
                else:
                    # In case the item details are not found
                    item.update({
                        'item_name': 'Unknown',
                        'item_price': 'Unknown',
                        'item_description': 'No description available',
                        'expiration_date': 'N/A',
                        'image' : 'N/A',
                    })

        return Response({'orders': orders})

    except pymongo.errors.PyMongoError as e:
        # Log the exception if needed
        print(f"Database error: {e}")
        return Response({'error': 'An error occurred while fetching orders.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@jwt_required
def add_doctor_profile(request):
    try:
        data = request.data
        name = data.get("name")
        age = data.get("age")
        experience = data.get("experience")
        field = data.get("field")
        user_id = data.get("user_id")
        medical_license_number = data.get("medical_license_number")
        issuing_authority = data.get("issuing_authority")
        education = data.get("education")

        # Check if the doctor profile already exists
        doctor_exist = db.doctors.find_one({"user_id": user_id})

        # Check if the user exists and has the role of 'doctor'
        user = db.users.find_one({"_id": ObjectId(user_id), "role": "doctor"})
        if not user:
            return JsonResponse({"error": "User not found or not a doctor"}, status=404)

        # If doctor profile exists, update it
        if doctor_exist:
            db.doctors.update_one(
                {"user_id": user_id},
                {"$set": {
                    "name": name,
                    "age": age,
                    "experience": experience,
                    "field": field,
                    "medical_license_number" : medical_license_number,
                    "issuing_authority" : issuing_authority,
                    "education" : education,
                }}
            )
            return JsonResponse({"message": "Doctor profile updated successfully"}, status=200)
        else:
            # If doctor profile does not exist, create a new one
            doctor = DoctorModel(name, age, experience, field, medical_license_number, issuing_authority, education, user_id)
            doctor.save()
            return JsonResponse({"message": "Doctor profile created successfully"}, status=201)
    except pymongo.errors.PyMongoError as e:
        # Log the exception if needed
        print(f"Database error: {e}")
        return Response({'error': 'An error occurred while processing the request.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['GET'])
@jwt_required
def fetch_doctor_profile(request, user_id):
    try:
        # Find the doctor profile by user_id
        doctor = db.doctors.find_one({"user_id": user_id})

        if not doctor:
            return JsonResponse({"error": "Doctor profile not found"}, status=404)

        # Convert ObjectId to string for JSON serialization
        doctor["_id"] = str(doctor["_id"])
        doctor["user_id"] = str(doctor["user_id"])
        return JsonResponse({"doctor": doctor}, status=200)
    except pymongo.errors.PyMongoError as e:
        # Log the exception if needed
        print(f"Database error: {e}")
        return Response({'error': 'An error occurred while fetching the doctor profile.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['GET'])
@jwt_required
def verify_doctor_by_admin(request, user_id):
    try:
        # Find the doctor profile by user_id
        doctor = db.users.find_one({"_id": ObjectId(user_id)})
        if not doctor:
            return JsonResponse({"error": "Doctor profile not found"}, status=404)

        # Convert ObjectId to string for JSON serialization
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "verified": True
            }}
        )
        return JsonResponse({"message": "Doctor profile is verified successfully"}, status=200)
    except pymongo.errors.PyMongoError as e:
        # Log the exception if needed
        print(f"Database error: {e}")
        return Response({'error': 'An error occurred while fetching the doctor profile.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@jwt_required
def request_appointment(request):
    try:
        user_id = request.data.get('user_id')
        doctor_id = request.data.get('doctor_id')
        appointment_time = request.data.get('appointment_time')

        if not user_id or not doctor_id or not appointment_time:
            return Response({'error': 'User ID, Doctor ID, and Appointment Time are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the requesting user exists and is of role 'user'
        user = db.users.find_one({'_id': ObjectId(user_id), 'role': 'user'})
        if not user:
            return Response({'error': 'User not found or not authorized to request appointments.'}, status=status.HTTP_404_NOT_FOUND)

        # Ensure the target doctor exists and is of role 'doctor'
        doctor = db.users.find_one({'_id': ObjectId(doctor_id), 'role': 'doctor'})
        if not doctor:
            return Response({'error': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Convert appointment time to datetime object if it's not already
        if isinstance(appointment_time, str):
            try:
                appointment_time = datetime.fromisoformat(appointment_time)
            except ValueError:
                return Response({'error': 'Invalid appointment time format. Use ISO format.'}, status=status.HTTP_400_BAD_REQUEST)

        # Insert the appointment request into the appointments collection
        appointment_id = db.appointments.insert_one({
            'user_id': ObjectId(user_id),
            'doctor_id': ObjectId(doctor_id),
            'appointment_time': appointment_time,
            'status': 'pending',
            'requested_at': datetime.now()
        }).inserted_id

        return Response({'message': 'Appointment requested successfully.', 'appointment_id': str(appointment_id)})

    except pymongo.errors.PyMongoError as e:
        # Log the exception if needed
        print(f"Database error: {e}")
        return Response({'error': 'An error occurred while requesting the appointment.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@jwt_required
def get_doctor_appointments(request):
    try:
        doctor_id = request.query_params.get('doctor_id')  # ID of the doctor whose appointments are being fetched
        if not doctor_id:
            return Response({'error': 'Doctor ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the requester is a doctor
        doctor = db.users.find_one({'_id': ObjectId(doctor_id), 'role': 'doctor'})
        if not doctor:
            return Response({'error': 'Doctor not found or not authorized.'}, status=status.HTTP_404_NOT_FOUND)

        # Fetch appointments for the doctor
        appointments = list(db.appointments.find({'doctor_id': ObjectId(doctor_id)}))

        # Prepare response data
        for appointment in appointments:
            appointment['_id'] = str(appointment['_id'])
            appointment['user_id'] = str(appointment['user_id'])
            appointment['doctor_id'] = str(appointment['doctor_id'])
            appointment['appointment_time'] = appointment['appointment_time'].isoformat()

            # Fetch user details
            user = db.users.find_one({'_id': ObjectId(appointment['user_id'])})
            if user:
                appointment['user_details'] = {
                    'username': user.get('username'),
                    'email': user.get('email'),
                    # Add more fields as necessary
                }
            else:
                appointment['user_details'] = 'User not found'

        return Response({'appointments': appointments}, status=status.HTTP_200_OK)

    except pymongo.errors.PyMongoError as e:
        # Log the exception if needed
        print(f"Database error: {e}")
        return Response({'error': 'An error occurred while fetching appointments.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@jwt_required
def get_patient_appointments(request):
    try:
        patient_id = request.query_params.get('patient_id')  # ID of the patient whose appointments are being fetched
        if not patient_id:
            return Response({'error': 'Patient ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the requester is a valid user and patient
        patient = db.users.find_one({'_id': ObjectId(patient_id), 'role': 'user'})
        if not patient:
            return Response({'error': 'Patient not found or not authorized.'}, status=status.HTTP_404_NOT_FOUND)

        # Fetch appointments for the patient
        appointments = list(db.appointments.find({'user_id': ObjectId(patient_id)}))

        # Prepare response data
        for appointment in appointments:
            appointment['_id'] = str(appointment['_id'])
            appointment['user_id'] = str(appointment['user_id'])
            appointment['doctor_id'] = str(appointment['doctor_id'])
            appointment['appointment_time'] = appointment['appointment_time'].isoformat()

            # Fetch doctor details
            doctor = db.users.find_one({'_id': ObjectId(appointment['doctor_id'])})
            if doctor:
                appointment['doctor_details'] = {
                    'username': doctor.get('username'),
                    'email': doctor.get('email'),
                    # Add more fields as necessary
                }
            else:
                appointment['doctor_details'] = 'Doctor not found'

        return Response({'appointments': appointments}, status=status.HTTP_200_OK)

    except pymongo.errors.PyMongoError as e:
        # Log the exception if needed
        print(f"Database error: {e}")
        return Response({'error': 'An error occurred while fetching appointments.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@jwt_required
def update_appointment_status(request):
    try:
        doctor_id = request.data.get('doctor_id')
        appointment_id = request.data.get('appointment_id') 
        status_update = request.data.get('status')

        if not doctor_id or not appointment_id or not status_update:
            return Response({'error': 'Doctor ID, Appointment ID, and Status are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if status_update not in ['accepted', 'rejected', 'completed']:
            return Response({'error': 'Invalid status update. Must be "accepted", "rejected", or "completed".'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the requester is a doctor
        doctor = db.users.find_one({'_id': ObjectId(doctor_id), 'role': 'doctor'})
        if not doctor:
            return Response({'error': 'Doctor not found or not authorized.'}, status=status.HTTP_404_NOT_FOUND)

        # Ensure the appointment exists and is assigned to the doctor
        appointment = db.appointments.find_one({'_id': ObjectId(appointment_id), 'doctor_id': ObjectId(doctor_id)})
        if not appointment:
            return Response({'error': 'Appointment not found or not assigned to this doctor.'}, status=status.HTTP_404_NOT_FOUND)

        # Update the appointment status
        db.appointments.update_one({'_id': ObjectId(appointment_id)}, {'$set': {'status': status_update, 'updated_at': datetime.now()}})

        return Response({'message': f'Appointment status updated to {status_update}.'}, status=status.HTTP_200_OK)

    except pymongo.errors.PyMongoError as e:
        # Log the exception if needed
        print(f"Database error: {e}")
        return Response({'error': 'An error occurred while updating the appointment.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@jwt_required
def search_medicine(request):
    try:
        search_term = request.query_params.get('q', '').strip()
        if not search_term:
            return Response({'error': 'Search term is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Perform a case-insensitive search on the 'name' field in the medicines collection
        medicines = list(db.medicinal_items.find({'name': {'$regex': search_term, '$options': 'i'}}))

        # Format the response data
        formatted_medicines = []
        for medicine in medicines:
            formatted_medicine = {
                'name': medicine.get('name'),
                'description': medicine.get('description', ''),
                'category': medicine.get('category', ''),
                'quantity': medicine.get('quantity', 0),
                'expiration_date': medicine.get('expiration_date'),
                'amount': medicine.get('amount', 0),
                'image': medicine.get('image', '')
            }
            formatted_medicines.append(formatted_medicine)

        return Response({'medicines': formatted_medicines}, status=status.HTTP_200_OK)

    except pymongo.errors.PyMongoError as e:
        # Log the exception if needed
        print(f"Database error: {e}")
        return Response({'error': 'An error occurred while searching for medicines.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@jwt_required
def create_chat_room(request):
    user1_id = request.data.get('user1_id')
    user2_id = request.data.get('user2_id')
    
    if not user1_id or not user2_id:
        return Response({'error': 'User IDs are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    chat_room = ChatRoom(user1_id=user1_id, user2_id=user2_id)
    chat_room.save()
    return Response({'room_id': str(chat_room._id)}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@jwt_required
def get_chat_room(request, user1_id, user2_id):
    # Find the chat room where either user1_id and user2_id match or vice versa
    chat_room = db.chat_rooms.find_one({
        '$or': [
            {'user1_id': ObjectId(user1_id), 'user2_id': ObjectId(user2_id)},
            {'user1_id': ObjectId(user2_id), 'user2_id': ObjectId(user1_id)}
        ]
    })
    
    if chat_room:
        # Convert ObjectId to string for JSON serialization
        chat_room['_id'] = str(chat_room['_id'])
        chat_room['user1_id'] = str(chat_room['user1_id'])
        chat_room['user2_id'] = str(chat_room['user2_id'])
        return Response(chat_room, status=status.HTTP_200_OK)
    else:
        return Response({'detail': 'Chat room not found'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@jwt_required
def save_message(request):
    room_id = request.data.get('room_id')
    sender_id = request.data.get('sender_id')
    receiver_id = request.data.get('receiver_id')
    message = request.data.get('message')

    if not room_id or not sender_id or not receiver_id or not message:
        return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)

    chat_message = ChatMessage(room_id=room_id, sender_id=sender_id, receiver_id=receiver_id, message=message)
    chat_message.save()
    return Response({'message': 'Message sent successfully'}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@jwt_required
def get_messages(request, room_id):
    try:
        messages = list(db.chat_messages.find({'room_id': ObjectId(room_id)}))
        for message in messages:
            message['_id'] = str(message['_id'])
            message['room_id'] = str(message['room_id'])
            message['sender_id'] = str(message['sender_id'])
            message['receiver_id'] = str(message['receiver_id'])

        return Response(messages, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"Error retrieving messages: {e}")
        return Response({'error': 'An error occurred while retrieving messages.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['POST'])
@jwt_required
def upload_patient_bill(request):
    try:
        data = request.data
        patient_id = data.get('patient_id') 
        base64_bill = data.get('bill')

        if not patient_id or not base64_bill:
            return Response({'error': 'Patient ID and Bill are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the requester is a valid user and patient
        patient = db.users.find_one({'_id': ObjectId(patient_id)})
        if not patient:
            return Response({'error': 'Patient not found or not authorized.'}, status=status.HTTP_404_NOT_FOUND)
        
        base64_image = base64_bill
        if base64_image:
            image_name = handle_base64_image(base64_image, f"bill{datetime.now()}")
            if image_name:
                image_url = default_storage.url(image_name)
                full_image_url = f"{get_current_site(request)}{image_url}"

        # Store the bill information in the database
        db.bills.insert_one({
            'patient_id': ObjectId(patient_id),
            'bill_url': full_image_url,
            'uploaded_at': datetime.now()
        })

        return Response({'message': 'Bill uploaded successfully.', 'bill_url': full_image_url}, status=status.HTTP_201_CREATED)

    except Exception as e:
        # Log the exception if needed
        print(f"Error occurred: {e}")
        return Response({'error': 'An error occurred while uploading the bill.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)