from django.contrib.auth import authenticate, logout
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .models import CustomUser, Question, Answer, Bookmark, Notification
from .serializers import UserSerializer, QuestionSerializer, AnswerSerializer, NotificationSerializer
import json
import logging
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.mail import send_mail
from django.conf import settings
from django.db import models

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


# =============================================================================
# QUESTION ENDPOINTS
# =============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def questions_list_create(request):
    """
    GET: List all questions
    POST: Create a new question
    """
    if request.method == 'GET':
        try:
            questions = Question.objects.all().order_by('-created_at')
            serializer = QuestionSerializer(questions, many=True, context={'request': request})
            return Response({'status': 'success', 'data': serializer.data})
        except Exception as e:
            logger.error(f"List questions error: {str(e)}")
            return Response({'status': 'error', 'message': 'Failed to fetch questions'}, status=500)
    
    elif request.method == 'POST':
        try:
            title = request.data.get('title')
            description = request.data.get('description')
            tags = request.data.get('tags', [])
            
            if not title or not description:
                return Response({'status': 'error', 'message': 'Title and description are required'}, status=400)
            
            question = Question.objects.create(
                title=title,
                description=description,
                user=request.user,
                tags=tags
            )
            
            serializer = QuestionSerializer(question, context={'request': request})
            return Response({'status': 'success', 'data': serializer.data}, status=201)
        except Exception as e:
            logger.error(f"Create question error: {str(e)}")
            return Response({'status': 'error', 'message': 'Failed to create question'}, status=500)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def question_detail(request, question_id):
    """
    GET: Retrieve a specific question
    PUT: Update a question (only by owner)
    DELETE: Delete a question (only by owner)
    """
    try:
        question = Question.objects.get(id=question_id)
    except Question.DoesNotExist:
        return Response({'status': 'error', 'message': 'Question not found'}, status=404)
    
    if request.method == 'GET':
        try:
            # Increment view count
            question.views += 1
            question.save()
            
            serializer = QuestionSerializer(question, context={'request': request})
            return Response({'status': 'success', 'data': serializer.data})
        except Exception as e:
            logger.error(f"Get question error: {str(e)}")
            return Response({'status': 'error', 'message': 'Failed to fetch question'}, status=500)
    
    elif request.method == 'PUT':
        if question.user != request.user:
            return Response({'status': 'error', 'message': 'You can only edit your own questions'}, status=403)
        
        try:
            title = request.data.get('title')
            description = request.data.get('description')
            tags = request.data.get('tags')
            
            if title:
                question.title = title
            if description:
                question.description = description
            if tags is not None:
                question.tags = tags
            
            question.save()
            serializer = QuestionSerializer(question, context={'request': request})
            return Response({'status': 'success', 'data': serializer.data})
        except Exception as e:
            logger.error(f"Update question error: {str(e)}")
            return Response({'status': 'error', 'message': 'Failed to update question'}, status=500)
    
    elif request.method == 'DELETE':
        if question.user != request.user:
            return Response({'status': 'error', 'message': 'You can only delete your own questions'}, status=403)
        
        try:
            question.delete()
            return Response({'status': 'success', 'message': 'Question deleted successfully'})
        except Exception as e:
            logger.error(f"Delete question error: {str(e)}")
            return Response({'status': 'error', 'message': 'Failed to delete question'}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_questions(request, user_id):
    """
    Get all questions posted by a specific user
    """
    try:
        user = CustomUser.objects.get(id=user_id)
        questions = Question.objects.filter(user=user).order_by('-created_at')
        serializer = QuestionSerializer(questions, many=True, context={'request': request})
        return Response({'status': 'success', 'data': serializer.data})
    except CustomUser.DoesNotExist:
        return Response({'status': 'error', 'message': 'User not found'}, status=404)
    except Exception as e:
        logger.error(f"User questions error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to fetch user questions'}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_questions_by_interests(request, user_id):
    """
    Get questions that match the user's interests
    """
    try:
        user = CustomUser.objects.get(id=user_id)
        
        # Get user's interests
        user_interests = user.interests if hasattr(user, 'interests') and user.interests else []
        
        if not user_interests:
            return Response({'status': 'success', 'data': []})
        
        # Find questions that have tags matching user's interests
        questions = Question.objects.filter(
            tags__name__in=user_interests
        ).distinct().order_by('-created_at')
        
        serializer = QuestionSerializer(questions, many=True, context={'request': request})
        return Response({'status': 'success', 'data': serializer.data})
    except CustomUser.DoesNotExist:
        return Response({'status': 'error', 'message': 'User not found'}, status=404)
    except Exception as e:
        logger.error(f"User questions by interests error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to fetch questions by interests'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def trending_questions(request):
    """
    Get trending questions based on recent activity
    """
    try:
        # Get questions with high activity in the last 7 days
        seven_days_ago = timezone.now() - timedelta(days=7)
        questions = Question.objects.filter(
            created_at__gte=seven_days_ago
        ).order_by('-upvotes', '-created_at')[:10]
        
        serializer = QuestionSerializer(questions, many=True, context={'request': request})
        return Response({'status': 'success', 'data': serializer.data})
    except Exception as e:
        logger.error(f"Trending questions error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to fetch trending questions'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vote_question(request, question_id):
    """
    Vote on a question (upvote or downvote)
    """
    try:
        question = Question.objects.get(id=question_id)
        vote_type = request.data.get('vote_type')  # 'upvote' or 'downvote'
        
        if vote_type not in ['upvote', 'downvote']:
            return Response({'status': 'error', 'message': 'Invalid vote type'}, status=400)
        
        if vote_type == 'upvote':
            question.upvotes += 1
            # Create notification for question owner on upvote
            if question.user != request.user:
                Notification.create_notification(
                    recipient=question.user,
                    sender=request.user,
                    notification_type='question_vote',
                    title='Your Question Got an Upvote!',
                    message=f'{request.user.name or request.user.username} upvoted your question "{question.title}"',
                    related_question=question
                )
        else:
            question.downvotes += 1
        
        question.save()
        serializer = QuestionSerializer(question)
        return Response({'status': 'success', 'data': serializer.data})
    except Question.DoesNotExist:
        return Response({'status': 'error', 'message': 'Question not found'}, status=404)
    except Exception as e:
        logger.error(f"Vote question error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to vote on question'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bookmark_question(request, question_id):
    """
    Toggle bookmark status for a question
    """
    try:
        question = Question.objects.get(id=question_id)
        
        # Check if user has already bookmarked this question
        bookmark, created = Bookmark.objects.get_or_create(
            user=request.user,
            question=question
        )
        
        if created:
            # Bookmark was created (user bookmarked the question)
            return Response({
                'status': 'success', 
                'message': 'Question bookmarked successfully',
                'isBookmarked': True
            })
        else:
            # Bookmark already exists, so remove it (unbookmark)
            bookmark.delete()
            return Response({
                'status': 'success', 
                'message': 'Question unbookmarked successfully',
                'isBookmarked': False
            })
    except Question.DoesNotExist:
        return Response({'status': 'error', 'message': 'Question not found'}, status=404)
    except Exception as e:
        logger.error(f"Bookmark question error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to bookmark question'}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_bookmarks(request, user_id):
    """
    Get all bookmarked questions for a specific user
    """
    try:
        # Ensure user can only access their own bookmarks
        if request.user.id != user_id:
            return Response({'status': 'error', 'message': 'Access denied'}, status=403)
        
        user = CustomUser.objects.get(id=user_id)
        bookmarks = Bookmark.objects.filter(user=user).order_by('-created_at')
        
        # Get the questions from the bookmarks
        questions = [bookmark.question for bookmark in bookmarks]
        
        # Add bookmark status to each question
        questions_data = []
        for question in questions:
            serializer = QuestionSerializer(question)
            question_data = serializer.data
            question_data['isBookmarked'] = True  # Always true for bookmarked questions
            questions_data.append(question_data)
        
        return Response({'status': 'success', 'data': questions_data})
    except CustomUser.DoesNotExist:
        return Response({'status': 'error', 'message': 'User not found'}, status=404)
    except Exception as e:
        logger.error(f"User bookmarks error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to fetch bookmarks'}, status=500)


# =============================================================================
# ANSWER ENDPOINTS
# =============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def question_answers(request, question_id):
    """
    GET: Get all answers for a specific question
    POST: Create a new answer for a question
    """
    try:
        question = Question.objects.get(id=question_id)
    except Question.DoesNotExist:
        return Response({'status': 'error', 'message': 'Question not found'}, status=404)
    
    if request.method == 'GET':
        try:
            answers = Answer.objects.filter(question=question).order_by('-created_at')
            serializer = AnswerSerializer(answers, many=True)
            return Response({'status': 'success', 'data': serializer.data})
        except Exception as e:
            logger.error(f"Get answers error: {str(e)}")
            return Response({'status': 'error', 'message': 'Failed to fetch answers'}, status=500)
    
    elif request.method == 'POST':
        try:
            content = request.data.get('content')
            if not content or not content.strip():
                return Response({'status': 'error', 'message': 'Answer content is required'}, status=400)
            
            answer = Answer.objects.create(
                content=content,
                user=request.user,
                question=question
            )
            
            # Create notification for the question owner
            if question.user != request.user:
                Notification.create_notification(
                    recipient=question.user,
                    sender=request.user,
                    notification_type='answer',
                    title='New Answer to Your Question',
                    message=f'{request.user.name or request.user.username} answered your question "{question.title}"',
                    related_question=question,
                    related_answer=answer
                )
            
            serializer = AnswerSerializer(answer)
            return Response({'status': 'success', 'data': serializer.data}, status=201)
        except Exception as e:
            logger.error(f"Create answer error: {str(e)}")
            return Response({'status': 'error', 'message': 'Failed to create answer'}, status=500)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def answer_detail(request, answer_id):
    """
    GET: Retrieve a specific answer
    PUT: Update an answer (only by owner)
    DELETE: Delete an answer (only by owner)
    """
    try:
        answer = Answer.objects.get(id=answer_id)
    except Answer.DoesNotExist:
        return Response({'status': 'error', 'message': 'Answer not found'}, status=404)
    
    if request.method == 'GET':
        try:
            serializer = AnswerSerializer(answer)
            return Response({'status': 'success', 'data': serializer.data})
        except Exception as e:
            logger.error(f"Get answer error: {str(e)}")
            return Response({'status': 'error', 'message': 'Failed to fetch answer'}, status=500)
    
    elif request.method == 'PUT':
        if answer.user != request.user:
            return Response({'status': 'error', 'message': 'You can only edit your own answers'}, status=403)
        
        try:
            content = request.data.get('content')
            if content:
                answer.content = content
                answer.save()
            
            serializer = AnswerSerializer(answer)
            return Response({'status': 'success', 'data': serializer.data})
        except Exception as e:
            logger.error(f"Update answer error: {str(e)}")
            return Response({'status': 'error', 'message': 'Failed to update answer'}, status=500)
    
    elif request.method == 'DELETE':
        if answer.user != request.user:
            return Response({'status': 'error', 'message': 'You can only delete your own answers'}, status=403)
        
        try:
            answer.delete()
            return Response({'status': 'success', 'message': 'Answer deleted successfully'})
        except Exception as e:
            logger.error(f"Delete answer error: {str(e)}")
            return Response({'status': 'error', 'message': 'Failed to delete answer'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vote_answer(request, answer_id):
    """
    Vote on an answer (upvote or downvote)
    """
    try:
        answer = Answer.objects.get(id=answer_id)
        vote_type = request.data.get('vote_type')  # 'upvote' or 'downvote'
        
        if vote_type not in ['upvote', 'downvote']:
            return Response({'status': 'error', 'message': 'Invalid vote type'}, status=400)
        
        if vote_type == 'upvote':
            answer.upvotes += 1
            # Create notification for answer owner on upvote
            if answer.user != request.user:
                Notification.create_notification(
                    recipient=answer.user,
                    sender=request.user,
                    notification_type='answer_vote',
                    title='Your Answer Got an Upvote!',
                    message=f'{request.user.name or request.user.username} upvoted your answer to "{answer.question.title}"',
                    related_question=answer.question,
                    related_answer=answer
                )
        else:
            answer.downvotes += 1
        
        answer.save()
        serializer = AnswerSerializer(answer)
        return Response({'status': 'success', 'data': serializer.data})
    except Answer.DoesNotExist:
        return Response({'status': 'error', 'message': 'Answer not found'}, status=404)
    except Exception as e:
        logger.error(f"Vote answer error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to vote on answer'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_answer(request, answer_id):
    """
    Accept an answer as the correct solution (only question owner can do this)
    """
    try:
        answer = Answer.objects.get(id=answer_id)
        
        # Only the question owner can accept answers
        if answer.question.user != request.user:
            return Response({'status': 'error', 'message': 'Only the question owner can accept answers'}, status=403)
        
        # Remove previous accepted answers for this question
        Answer.objects.filter(question=answer.question, is_accepted=True).update(is_accepted=False)
        
        # Mark this answer as accepted
        answer.is_accepted = True
        answer.save()
        
        # Create notification for the answer author
        Notification.create_notification(
            recipient=answer.user,
            sender=request.user,
            notification_type='answer_accepted',
            title='Answer Accepted!',
            message=f'Your answer to "{answer.question.title}" has been accepted as the solution!',
            related_question=answer.question,
            related_answer=answer
        )
        
        serializer = AnswerSerializer(answer)
        return Response({'status': 'success', 'data': serializer.data})
    except Answer.DoesNotExist:
        return Response({'status': 'error', 'message': 'Answer not found'}, status=404)
    except Exception as e:
        logger.error(f"Accept answer error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to accept answer'}, status=500)


# =============================================================================
# NOTIFICATION ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_notifications(request):
    """
    Get notifications for the authenticated user with optional filtering
    """
    try:
        # Get query parameters
        unread_only = request.GET.get('unread_only', 'false').lower() == 'true'
        notification_type = request.GET.get('type')
        limit = request.GET.get('limit', 20)
        
        # Base queryset
        queryset = Notification.objects.filter(recipient=request.user)
        
        # Apply filters
        if unread_only:
            queryset = queryset.filter(is_read=False)
        
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # Limit results
        try:
            limit = int(limit)
            if limit > 100:  # Cap at 100 notifications
                limit = 100
        except (ValueError, TypeError):
            limit = 20
        
        notifications = queryset[:limit]
        
        # Get counts
        total_count = Notification.objects.filter(recipient=request.user).count()
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        
        serializer = NotificationSerializer(notifications, many=True)
        
        return Response({
            'status': 'success',
            'data': serializer.data,
            'meta': {
                'total_count': total_count,
                'unread_count': unread_count,
                'returned_count': len(notifications)
            }
        })
    except Exception as e:
        logger.error(f"User notifications error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to fetch notifications'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """
    Mark a specific notification as read
    """
    try:
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
        notification.mark_as_read()
        
        serializer = NotificationSerializer(notification)
        return Response({
            'status': 'success',
            'data': serializer.data,
            'message': 'Notification marked as read'
        })
    except Notification.DoesNotExist:
        return Response({'status': 'error', 'message': 'Notification not found'}, status=404)
    except Exception as e:
        logger.error(f"Mark notification read error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to mark notification as read'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """
    Mark all notifications as read for the authenticated user
    """
    try:
        updated_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        
        return Response({
            'status': 'success',
            'message': f'Marked {updated_count} notifications as read',
            'updated_count': updated_count
        })
    except Exception as e:
        logger.error(f"Mark all notifications read error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to mark all notifications as read'}, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, notification_id):
    """
    Delete a specific notification
    """
    try:
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
        notification.delete()
        
        return Response({
            'status': 'success',
            'message': 'Notification deleted successfully'
        })
    except Notification.DoesNotExist:
        return Response({'status': 'error', 'message': 'Notification not found'}, status=404)
    except Exception as e:
        logger.error(f"Delete notification error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to delete notification'}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_summary(request):
    """
    Get a summary of notifications for the user (counts by type, recent notifications)
    """
    try:
        # Get counts by type
        type_counts = Notification.objects.filter(recipient=request.user).values('notification_type').annotate(
            count=Count('id'),
            unread_count=Count('id', filter=Q(is_read=False))
        ).order_by('-count')
        
        # Get recent unread notifications (last 5)
        recent_unread = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        )[:5]
        
        recent_serializer = NotificationSerializer(recent_unread, many=True)
        
        # Total counts
        total_count = Notification.objects.filter(recipient=request.user).count()
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        
        return Response({
            'status': 'success',
            'data': {
                'total_count': total_count,
                'unread_count': unread_count,
                'type_counts': list(type_counts),
                'recent_unread': recent_serializer.data
            }
        })
    except Exception as e:
        logger.error(f"Notification summary error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to get notification summary'}, status=500)


# =============================================================================
# SEARCH ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def search_questions(request):
    """
    Advanced search for questions with multiple filters and sorting options
    """
    try:
        # Get search parameters
        query = request.GET.get('q', '').strip()
        tags = request.GET.get('tags', '').strip()
        user_id = request.GET.get('user_id')
        sort_by = request.GET.get('sort_by', 'relevance')  # relevance, newest, oldest, most_votes, most_answers
        date_range = request.GET.get('date_range', 'all')  # all, today, week, month, year
        has_answer = request.GET.get('has_answer')  # true, false, accepted
        min_votes = request.GET.get('min_votes', 0)
        limit = min(int(request.GET.get('limit', 20)), 100)
        offset = int(request.GET.get('offset', 0))
        
        # Base queryset
        questions = Question.objects.all()
        
        # Apply search filters
        if query:
            from django.db.models import Q
            questions = questions.filter(
                Q(title__icontains=query) | 
                Q(description__icontains=query) |
                Q(tags__icontains=query)
            )
        
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            for tag in tag_list:
                questions = questions.filter(tags__icontains=tag)
        
        if user_id:
            questions = questions.filter(user_id=user_id)
        
        # Date range filter
        if date_range != 'all':
            from datetime import datetime
            now = timezone.now()
            if date_range == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif date_range == 'week':
                start_date = now - timedelta(days=7)
            elif date_range == 'month':
                start_date = now - timedelta(days=30)
            elif date_range == 'year':
                start_date = now - timedelta(days=365)
            
            questions = questions.filter(created_at__gte=start_date)
        
        # Answer filter
        if has_answer == 'true':
            questions = questions.filter(question_answers__isnull=False).distinct()
        elif has_answer == 'false':
            questions = questions.filter(question_answers__isnull=True)
        elif has_answer == 'accepted':
            questions = questions.filter(question_answers__is_accepted=True).distinct()
        
        # Vote filter
        if min_votes:
            questions = questions.filter(upvotes__gte=int(min_votes))
        
        # Sorting
        if sort_by == 'newest':
            questions = questions.order_by('-created_at')
        elif sort_by == 'oldest':
            questions = questions.order_by('created_at')
        elif sort_by == 'most_votes':
            questions = questions.order_by('-upvotes', '-created_at')
        elif sort_by == 'most_answers':
            questions = questions.annotate(
                answer_count=Count('question_answers')
            ).order_by('-answer_count', '-created_at')
        else:  # relevance (default)
            if query:
                # Simple relevance scoring based on query matches
                questions = questions.extra(
                    select={
                        'relevance': """
                            CASE 
                                WHEN title ILIKE %s THEN 3
                                WHEN description ILIKE %s THEN 2
                                WHEN tags ILIKE %s THEN 1
                                ELSE 0
                            END
                        """
                    },
                    select_params=[f'%{query}%', f'%{query}%', f'%{query}%']
                ).order_by('-relevance', '-upvotes', '-created_at')
            else:
                questions = questions.order_by('-upvotes', '-created_at')
        
        # Get total count before pagination
        total_count = questions.count()
        
        # Apply pagination
        questions = questions[offset:offset + limit]
        
        serializer = QuestionSerializer(questions, many=True, context={'request': request})
        
        return Response({
            'status': 'success',
            'data': serializer.data,
            'meta': {
                'total_count': total_count,
                'returned_count': len(questions),
                'offset': offset,
                'limit': limit,
                'has_more': offset + limit < total_count
            }
        })
    except Exception as e:
        logger.error(f"Search questions error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to search questions'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_users(request):
    """
    Search for users by name, handle, institution, or expertise
    """
    try:
        query = request.GET.get('q', '').strip()
        limit = min(int(request.GET.get('limit', 20)), 100)
        offset = int(request.GET.get('offset', 0))
        
        if not query:
            return Response({
                'status': 'success',
                'data': [],
                'meta': {'total_count': 0, 'returned_count': 0, 'offset': offset, 'limit': limit}
            })
        
        users = CustomUser.objects.filter(
            Q(name__icontains=query) |
            Q(handle__icontains=query) |
            Q(institution__icontains=query) |
            Q(expertise__icontains=query) |
            Q(username__icontains=query)
        ).order_by('-date_joined')
        
        total_count = users.count()
        users = users[offset:offset + limit]
        
        serializer = UserSerializer(users, many=True)
        
        return Response({
            'status': 'success',
            'data': serializer.data,
            'meta': {
                'total_count': total_count,
                'returned_count': len(users),
                'offset': offset,
                'limit': limit,
                'has_more': offset + limit < total_count
            }
        })
    except Exception as e:
        logger.error(f"Search users error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to search users'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_suggestions(request):
    """
    Get search suggestions based on query prefix
    """
    try:
        query = request.GET.get('q', '').strip()
        limit = min(int(request.GET.get('limit', 10)), 20)
        
        if len(query) < 2:
            return Response({
                'status': 'success',
                'data': {'questions': [], 'tags': [], 'users': [], 'communities': []}
            })
        
        # Question suggestions
        questions = Question.objects.filter(
            Q(title__icontains=query)
        ).values('title').distinct()[:limit//3]
        
        # Tag suggestions (extract from existing questions)
        import json
        from django.db.models import Func, Value
        
        # Get all unique tags that contain the query
        tag_questions = Question.objects.exclude(tags__isnull=True).exclude(tags='[]')
        all_tags = set()
        for q in tag_questions:
            try:
                tags = json.loads(q.tags) if isinstance(q.tags, str) else q.tags
                for tag in tags:
                    if query.lower() in tag.lower():
                        all_tags.add(tag)
                        if len(all_tags) >= limit//3:
                            break
            except (json.JSONDecodeError, TypeError):
                continue
        
        # User suggestions
        users = CustomUser.objects.filter(
            Q(name__icontains=query) | Q(handle__icontains=query)
        ).values('name', 'handle').distinct()[:limit//3]
        
        # Community suggestions (mock data for now)
        mock_communities = [
            'Computer Science Study Group',
            'Mathematics Help Hub',
            'Biology Research Community',
            'Engineering Projects',
            'Physics Discussion Forum',
            'Chemistry Lab Community',
            'Literature Analysis Group',
            'History Research Society',
            'Psychology Studies Hub',
            'Economics & Finance Club'
        ]
        
        communities = [c for c in mock_communities if query.lower() in c.lower()][:limit//4]
        
        return Response({
            'status': 'success',
            'data': {
                'questions': [q['title'] for q in questions],
                'tags': list(all_tags),
                'users': [f"{u['name']} ({u['handle']})" if u['handle'] else u['name'] for u in users],
                'communities': communities
            }
        })
    except Exception as e:
        logger.error(f"Search suggestions error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to get search suggestions'}, status=500)


# =============================================================================
# TRENDING ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def trending_tags(request):
    """
    Get trending tags based on recent question activity
    """
    try:
        days = int(request.GET.get('days', 7))  # Default to last 7 days
        limit = min(int(request.GET.get('limit', 20)), 50)
        
        # Get questions from the specified time period
        since_date = timezone.now() - timedelta(days=days)
        recent_questions = Question.objects.filter(created_at__gte=since_date)
        
        # Count tag occurrences
        tag_counts = {}
        for question in recent_questions:
            try:
                tags = json.loads(question.tags) if isinstance(question.tags, str) else question.tags
                for tag in tags:
                    if tag.strip():
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except (json.JSONDecodeError, TypeError):
                continue
        
        # Sort by count and get top tags
        trending_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return Response({
            'status': 'success',
            'data': [{'name': tag, 'count': count, 'questions': count} for tag, count in trending_tags]
        })
    except Exception as e:
        logger.error(f"Trending tags error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to fetch trending tags'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def trending_topics(request):
    """
    Get trending topics with comprehensive analytics
    """
    try:
        days = int(request.GET.get('days', 7))
        limit = min(int(request.GET.get('limit', 10)), 20)
        
        since_date = timezone.now() - timedelta(days=days)
        
        # Get trending topics based on multiple factors
        topics_data = []
        
        # Get questions with high activity
        trending_questions = Question.objects.filter(
            created_at__gte=since_date
        ).annotate(
            activity_score=models.F('upvotes') * 3 + 
                          models.F('views') * 0.1 + 
                          Count('question_answers') * 5
        ).order_by('-activity_score')[:limit]
        
        for question in trending_questions:
            try:
                tags = json.loads(question.tags) if isinstance(question.tags, str) else question.tags
                topics_data.append({
                    'id': question.id,
                    'title': question.title,
                    'tags': tags,
                    'upvotes': question.upvotes,
                    'views': question.views,
                    'answers': question.question_answers.count(),
                    'activity_score': question.upvotes * 3 + question.views * 0.1 + question.question_answers.count() * 5,
                    'created_at': question.created_at,
                    'user': question.user.name or question.user.username
                })
            except (json.JSONDecodeError, TypeError):
                continue
        
        return Response({
            'status': 'success',
            'data': topics_data
        })
    except Exception as e:
        logger.error(f"Trending topics error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to fetch trending topics'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def trending_users(request):
    """
    Get trending users based on recent activity and reputation
    """
    try:
        days = int(request.GET.get('days', 7))
        limit = min(int(request.GET.get('limit', 10)), 20)
        
        since_date = timezone.now() - timedelta(days=days)
        
        # Calculate user activity scores
        users_with_scores = CustomUser.objects.annotate(
            recent_questions=Count('question', filter=Q(question__created_at__gte=since_date)),
            recent_answers=Count('answer', filter=Q(answer__created_at__gte=since_date)),
            total_upvotes=Count('question__upvotes') + Count('answer__upvotes'),
            activity_score=
                Count('question', filter=Q(question__created_at__gte=since_date)) * 5 +
                Count('answer', filter=Q(answer__created_at__gte=since_date)) * 3 +
                Count('question__upvotes') * 2 +
                Count('answer__upvotes') * 1
        ).filter(activity_score__gt=0).order_by('-activity_score')[:limit]
        
        trending_users_data = []
        for user in users_with_scores:
            trending_users_data.append({
                'id': user.id,
                'name': user.name or user.username,
                'handle': user.handle,
                'institution': user.institution,
                'expertise': user.expertise,
                'recent_questions': user.recent_questions,
                'recent_answers': user.recent_answers,
                'activity_score': user.activity_score,
                'profile_picture': user.profile_picture.url if user.profile_picture else None
            })
        
        return Response({
            'status': 'success',
            'data': trending_users_data
        })
    except Exception as e:
        logger.error(f"Trending users error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to fetch trending users'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_analytics(request):
    """
    Get search and trending analytics for the platform
    """
    try:
        days = int(request.GET.get('days', 30))
        since_date = timezone.now() - timedelta(days=days)
        
        # Basic statistics
        stats = {
            'total_questions': Question.objects.count(),
            'recent_questions': Question.objects.filter(created_at__gte=since_date).count(),
            'total_answers': Answer.objects.count(),
            'recent_answers': Answer.objects.filter(created_at__gte=since_date).count(),
            'total_users': CustomUser.objects.count(),
            'active_users': CustomUser.objects.filter(
                Q(question__created_at__gte=since_date) |
                Q(answer__created_at__gte=since_date)
            ).distinct().count(),
        }
        
        # Most active tags
        recent_questions = Question.objects.filter(created_at__gte=since_date)
        tag_activity = {}
        for question in recent_questions:
            try:
                tags = json.loads(question.tags) if isinstance(question.tags, str) else question.tags
                for tag in tags:
                    if tag.strip():
                        tag_activity[tag] = tag_activity.get(tag, 0) + 1
            except (json.JSONDecodeError, TypeError):
                continue
        
        top_tags = sorted(tag_activity.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Growth metrics
        previous_period = since_date - timedelta(days=days)
        previous_questions = Question.objects.filter(
            created_at__gte=previous_period,
            created_at__lt=since_date
        ).count()
        
        growth_rate = 0
        if previous_questions > 0:
            growth_rate = ((stats['recent_questions'] - previous_questions) / previous_questions) * 100
        
        return Response({
            'status': 'success',
            'data': {
                'statistics': stats,
                'top_tags': [{'name': tag, 'count': count} for tag, count in top_tags],
                'growth_rate': round(growth_rate, 2),
                'period_days': days
            }
        })
    except Exception as e:
        logger.error(f"Search analytics error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to fetch analytics'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_communities(request):
    """
    Search communities by name, description, and category
    """
    try:
        query = request.GET.get('q', '').strip()
        limit = min(int(request.GET.get('limit', 20)), 50)
        sort_by = request.GET.get('sort', 'relevance')
        category = request.GET.get('category', '')
        
        if not query:
            return Response({'status': 'error', 'message': 'Search query is required'}, status=400)
        
        # For now, return mock data since Community model might not exist
        # This should be replaced with actual database queries when Community model is available
        mock_communities = [
            {
                'id': 1,
                'name': f'Computer Science Study Group',
                'description': 'A community for computer science students to collaborate and learn together',
                'members': 150,
                'category': 'Academic',
                'created_at': timezone.now().isoformat(),
                'isJoined': False,
                'creator': {'name': 'John Doe', 'id': 1},
                'tags': ['computer-science', 'programming', 'algorithms']
            },
            {
                'id': 2,
                'name': f'Mathematics Help Hub',
                'description': 'Get help with calculus, algebra, and advanced mathematics topics',
                'members': 89,
                'category': 'Academic',
                'created_at': timezone.now().isoformat(),
                'isJoined': False,
                'creator': {'name': 'Jane Smith', 'id': 2},
                'tags': ['mathematics', 'calculus', 'algebra']
            },
            {
                'id': 3,
                'name': f'Biology Research Community',
                'description': 'Discuss latest research and share knowledge in biological sciences',
                'members': 67,
                'category': 'Research',
                'created_at': timezone.now().isoformat(),
                'isJoined': True,
                'creator': {'name': 'Dr. Wilson', 'id': 3},
                'tags': ['biology', 'research', 'science']
            },
            {
                'id': 4,
                'name': f'Engineering Projects',
                'description': 'Collaborate on engineering projects and share innovative solutions',
                'members': 234,
                'category': 'Projects',
                'created_at': timezone.now().isoformat(),
                'isJoined': False,
                'creator': {'name': 'Alex Johnson', 'id': 4},
                'tags': ['engineering', 'projects', 'innovation']
            }
        ]
        
        # Filter communities based on search query
        filtered_communities = []
        query_lower = query.lower()
        
        for community in mock_communities:
            if (query_lower in community['name'].lower() or 
                query_lower in community['description'].lower() or
                any(query_lower in tag for tag in community['tags']) or
                (category and category.lower() == community['category'].lower())):
                filtered_communities.append(community)
        
        # Sort results
        if sort_by == 'members':
            filtered_communities.sort(key=lambda x: x['members'], reverse=True)
        elif sort_by == 'newest':
            filtered_communities.sort(key=lambda x: x['created_at'], reverse=True)
        # Default relevance sorting (already filtered by relevance)
        
        # Limit results
        results = filtered_communities[:limit]
        
        return Response({
            'status': 'success',
            'data': results,
            'total': len(results),
            'query': query
        })
        
    except Exception as e:
        logger.error(f"Search communities error: {str(e)}")
        return Response({'status': 'error', 'message': 'Failed to search communities'}, status=500)
