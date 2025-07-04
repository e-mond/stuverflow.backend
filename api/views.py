from django.contrib.auth import authenticate, logout
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .models import CustomUser, Question
from .serializers import UserSerializer, QuestionSerializer
import json
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    try:
        data = request.data
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')

        if not all([email, password, name]):
            return Response({'status': 'error', 'message': 'Email, password, and name required'}, status=400)

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
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return Response({'status': 'error', 'message': str(e)}, status=500)


@api_view(['POST', 'OPTIONS'])
@permission_classes([AllowAny])
def user_login(request):
    try:
        data = request.data
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


@api_view(['POST'])
@permission_classes([AllowAny])
def user_logout(request):
    try:
        logout(request)
        return Response({'status': 'success', 'message': 'Logged out'})
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response({'status': 'error', 'message': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request, id):
    try:
        user = CustomUser.objects.get(id=id)
        serializer = UserSerializer(user)
        return Response({'status': 'success', 'data': serializer.data})
    except CustomUser.DoesNotExist:
        return Response({'status': 'error', 'message': 'User not found'}, status=404)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user(request, id):
    try:
        user = CustomUser.objects.get(id=id)
        data = request.data

        user.name = data.get('name') or f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
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
            user.certifications = json.dumps([f.name for f in request.FILES.getlist('certificateFiles')])

        user.save()
        serializer = UserSerializer(user)
        return Response({'status': 'success', 'message': 'Profile updated', 'data': serializer.data})

    except CustomUser.DoesNotExist:
        return Response({'status': 'error', 'message': 'User not found'}, status=404)
    except IntegrityError:
        return Response({'status': 'error', 'message': 'Duplicate field (e.g., handle or email)'}, status=400)
    except ValidationError as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Update user error: {str(e)}")
        return Response({'status': 'error', 'message': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_hot_questions(request):
    try:
        questions = Question.objects.order_by('-views')[:10]
        serializer = QuestionSerializer(questions, many=True)
        return Response({'status': 'success', 'data': serializer.data})
    except Exception as e:
        logger.error(f"Hot questions error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to fetch hot questions'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_new_users(request):
    try:
        users = CustomUser.objects.order_by('-date_joined')[:10]
        serializer = UserSerializer(users, many=True)
        return Response({'status': 'success', 'data': serializer.data})
    except Exception as e:
        logger.error(f"New users error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to fetch new users'}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    try:
        data = request.data
        email = data.get('email')

        if not email:
            return Response({'status': 'error', 'message': 'Email required'}, status=400)

        if not CustomUser.objects.filter(email=email).exists():
            return Response({'status': 'error', 'message': 'Email not found'}, status=404)

        return Response({'status': 'success', 'message': 'Password reset email sent'})
    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        return Response({'status': 'error', 'message': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    try:
        data = request.data
        token = data.get('token')
        new_password = data.get('newPassword')

        if not all([token, new_password]):
            return Response({'status': 'error', 'message': 'Token and new password required'}, status=400)

        # Replace with actual token lookup logic
        user = CustomUser.objects.get(id=1)
        user.set_password(new_password)
        user.save()

        return Response({'status': 'success', 'message': 'Password reset successfully'})
    except CustomUser.DoesNotExist:
        return Response({'status': 'error', 'message': 'Invalid token'}, status=400)
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        return Response({'status': 'error', 'message': str(e)}, status=500)
