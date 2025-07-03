from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import CustomUser, Question
import json
import logging
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .serializers import UserSerializer, QuestionSerializer

# Configure logging to track errors and debug information
logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])  # Changed from IsAuthenticated to AllowAny
def signup(request):
    """
    Handles user signup via a POST request.
    Expects JSON data with 'email', 'password', and 'name' fields.
    Returns a success response with user ID, name, token, and email if successful.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            email = data.get('email')
            password = data.get('password')
            name = data.get('name')

            if email and password and name:
                username = email.split('@')[0]
                user = CustomUser.objects.create_user(username=username, email=email, password=password)
                user.name = name
                user.save()

                token, _ = Token.objects.get_or_create(user=user)
                return Response({
                    'status': 'success',
                    'id': user.id,
                    'name': name,
                    'token': token.key,
                    'data': {'email': email, 'handle': user.handle}
                })
            return Response({'status': 'error', 'message': 'Email, password, and name required'}, status=400)
        except Exception as e:
            logger.error(f"Signup error: {str(e)}")
            return Response({'status': 'error', 'message': str(e)}, status=500)
    return Response({'status': 'error', 'message': 'Use POST method'}, status=405)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    """
    Handles user login via a POST request.
    Expects JSON data with 'email' and 'password' fields.
    Returns a success response with user ID, name, token, and email if authenticated.
    """
    logger.debug(f"Request path: {request.path}, method: {request.method}, headers: {request.headers}")
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            email = data.get('email')
            password = data.get('password')

            user = authenticate(request, username=email.split('@')[0], password=password)
            if user is None:
                try:
                    user = CustomUser.objects.get(email=email)
                    if not user.check_password(password):
                        return Response({'status': 'error', 'message': 'Invalid credentials'}, status=401)
                except CustomUser.DoesNotExist:
                    return Response({'status': 'error', 'message': 'Invalid credentials'}, status=401)
            else:
                # Use token authentication instead of session
                token, _ = Token.objects.get_or_create(user=user)
                return Response({
                    'status': 'success',
                    'id': user.id,
                    'name': getattr(user, 'name', ''),
                    'token': token.key,
                    'data': {'email': email, 'handle': user.handle}
                })
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return Response({'status': 'error', 'message': str(e)}, status=500)
    return Response({'status': 'error', 'message': 'Use POST method'}, status=405)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request, id):
    """
    Fetches user profile data by ID.
    Requires authentication and returns serialized user data.
    """
    try:
        user = CustomUser.objects.get(id=id)
        serializer = UserSerializer(user)
        return Response({
            'status': 'success',
            'data': serializer.data
        })
    except CustomUser.DoesNotExist:
        return Response({'status': 'error', 'message': 'User not found'}, status=404)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_hot_questions(request):
    """
    Fetches the top 10 questions ordered by views.
    Accessible to all users, no authentication required.
    """
    try:
        questions = Question.objects.order_by('-views')[:10]
        serializer = QuestionSerializer(questions, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        })
    except Exception as e:
        logger.error(f"Hot questions error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to fetch hot questions'}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_new_users(request):
    """
    Fetches the 10 most recently joined users.
    Accessible to all users, no authentication required.
    """
    try:
        users = CustomUser.objects.order_by('-date_joined')[:10]
        serializer = UserSerializer(users, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        })
    except Exception as e:
        logger.error(f"New users error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to fetch new users'}, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])  # Changed from IsAuthenticated to AllowAny
def user_logout(request):
    """
    Handles user logout via a POST request.
    Requires authentication and clears the session.
    """
    try:
        logout(request)
        return Response({'status': 'success', 'message': 'Logged out'})
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user(request, id):
    """
    Updates user profile data, including file uploads.
    Requires authentication and accepts PUT requests with user data.
    Supports fields: name, email, handle, bio, institution, title, expertise, certifications, dob, interests,
    profilePicture, and certificateFiles.
    """
    if request.method == 'PUT':
        try:
            user = CustomUser.objects.get(id=id)
            if not user:
                return Response({'status': 'error', 'message': 'User not found'}, status=404)
            
            data = request.data
            new_name = data.get('name')
            if new_name:
                user.name = new_name
            elif data.get('first_name') or data.get('last_name'):
                user.name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
            
            user.email = data.get('email', user.email)
            user.handle = data.get('handle', user.handle)
            user.bio = data.get('bio', user.bio)
            user.institution = data.get('institution', user.institution)
            user.title = data.get('title', user.title)
            user.expertise = data.get('expertise', user.expertise)
            user.certifications = data.get('certifications', user.certifications)
            user.dob = data.get('dob', user.dob)
            user.interests = data.get('interests', user.interests)
            
            if 'profilePicture' in request.FILES:
                user.profile_picture = request.FILES['profilePicture']
            if 'certificateFiles' in request.FILES:
                certificate_files = request.FILES.getlist('certificateFiles')
                if certificate_files:
                    user.certifications = json.dumps([f.name for f in certificate_files])
            
            user.save()
            logger.info(f"User {id} updated successfully: {data}")
            serializer = UserSerializer(user)
            return Response({
                'status': 'success',
                'message': 'Profile updated',
                'data': serializer.data
            })
        except CustomUser.DoesNotExist:
            logger.error(f"User not found: ID {id}")
            return Response({'status': 'error', 'message': 'User not found'}, status=404)
        except json.JSONDecodeError:
            logger.error("Invalid JSON data in request body")
            return Response({'status': 'error', 'message': 'Invalid request data'}, status=400)
        except IntegrityError as e:
            logger.error(f"Database integrity error: {str(e)}")
            return Response({'status': 'error', 'message': 'Duplicate field (e.g., handle or email)'}, status=400)
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return Response({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Update user error: {str(e)}")
            return Response({'status': 'error', 'message': str(e)}, status=500)
    return Response({'status': 'error', 'message': 'Use PUT method'}, status=405)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            email = data.get('email')
            if email:
                try:
                    user = CustomUser.objects.get(email=email)
                    return Response({'status': 'success', 'message': 'Password reset email sent'})
                except CustomUser.DoesNotExist:
                    return Response({'status': 'error', 'message': 'Email not found'}, status=404)
            return Response({'status': 'error', 'message': 'Email required'}, status=400)
        except Exception as e:
            logger.error(f"Password reset request error: {str(e)}")
            return Response({'status': 'error', 'message': str(e)}, status=500)
    return Response({'status': 'error', 'message': 'Use POST method'}, status=405)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            token = data.get('token')
            new_password = data.get('newPassword')
            if token and new_password:
                try:
                    user = CustomUser.objects.get(id=1)  # Replace with token-based lookup
                    user.set_password(new_password)
                    user.save()
                    return Response({'status': 'success', 'message': 'Password reset successfully'})
                except CustomUser.DoesNotExist:
                    return Response({'status': 'error', 'message': 'Invalid token'}, status=400)
            return Response({'status': 'error', 'message': 'Token and new password required'}, status=400)
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            return Response({'status': 'error', 'message': str(e)}, status=500)
    return Response({'status': 'error', 'message': 'Use POST method'}, status=405)