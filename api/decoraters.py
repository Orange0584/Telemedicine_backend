import jwt
from functools import wraps
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
import os
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')

def jwt_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        token = request.META.get('HTTP_AUTHORIZATION')
        print(f"Received token: {token}")
        if token:
            try:
                print(token,'tt')
                token = token.split()[1]
                print(token)
                decoded = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
                print(decoded,'kkkkk')
                request.user_id = decoded['user_id']  # Store user_id in request for use in view
                return view_func(request, *args, **kwargs)
            except jwt.ExpiredSignatureError:
                return Response({'message': 'Token expired'}, status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({'message': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({'message': 'Token required'}, status=status.HTTP_401_UNAUTHORIZED)
    return _wrapped_view
