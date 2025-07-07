from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from .models import Community, CommunityQuestion, CommunityMessage, CommunityMessageLike, CommunityMembership
from .serializers import (
    CommunitySerializer, 
    CommunityQuestionSerializer, 
    JoinLeaveSerializer,
    CommunityMessageSerializer,
    CommunityMessageCreateSerializer
)
from api.models import Notification


class CommunityListCreate(generics.ListCreateAPIView):
    queryset = Community.objects.all()
    serializer_class = CommunitySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        community = serializer.save(creator=self.request.user)
        # Automatically make the creator an admin and member
        CommunityMembership.objects.create(
            community=community,
            user=self.request.user,
            role='admin',
            status='approved',
            approved_at=timezone.now(),
            approved_by=self.request.user
        )

class CommunityDetail(generics.RetrieveAPIView):
    queryset = Community.objects.all()
    serializer_class = CommunitySerializer

class JoinCommunity(generics.GenericAPIView):
    serializer_class = JoinLeaveSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        community = get_object_or_404(Community, pk=pk)
        
        # Check if user already has a membership record
        existing_membership = CommunityMembership.objects.filter(
            community=community, 
            user=request.user
        ).first()
        
        if existing_membership:
            if existing_membership.status == 'approved':
                return Response({
                    'message': 'You are already a member of this community',
                    'status': 'already_member'
                }, status=400)
            elif existing_membership.status == 'pending':
                return Response({
                    'message': 'Your join request is already pending approval',
                    'status': 'pending'
                }, status=400)
            elif existing_membership.status == 'declined':
                # Allow re-requesting if previously declined
                existing_membership.status = 'pending'
                existing_membership.requested_at = timezone.now()
                existing_membership.save()
        else:
            # Create new membership request
            CommunityMembership.objects.create(
                community=community,
                user=request.user,
                role='member',
                status='pending'
            )
        
        # Notify all admins about the join request
        admins = CommunityMembership.objects.filter(
            community=community, 
            role='admin', 
            status='approved'
        ).select_related('user')
        
        for admin_membership in admins:
            Notification.create_notification(
                recipient=admin_membership.user,
                notification_type='community_join_request',
                title=f'New join request for {community.name}',
                message=f'{request.user.name or request.user.username} wants to join {community.name}',
                sender=request.user,
                action_url=f'/communities/{community.id}/admin'
            )
        
        return Response({
            'message': 'Join request sent successfully. You will be notified when approved.',
            'status': 'request_sent'
        })

class LeaveCommunity(generics.GenericAPIView):
    serializer_class = JoinLeaveSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        community = get_object_or_404(Community, pk=pk)
        
        # Check if user is the creator
        if community.creator == request.user:
            return Response({
                'message': 'Community creators cannot leave their own communities',
                'status': 'creator_cannot_leave'
            }, status=400)
        
        # Find and delete the membership
        membership = CommunityMembership.objects.filter(
            community=community,
            user=request.user
        ).first()
        
        if not membership:
            return Response({
                'message': 'You are not a member of this community',
                'status': 'not_member'
            }, status=400)
        
        membership.delete()
        
        return Response({
            'message': 'Successfully left community',
            'members': community.member_count
        })

class CommunityQuestions(generics.ListAPIView):
    serializer_class = CommunityQuestionSerializer

    def get_queryset(self):
        community_id = self.kwargs['pk']
        return CommunityQuestion.objects.filter(community_id=community_id).select_related('question')
    
class CheckMembership(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, user_id):
        community = get_object_or_404(Community, pk=pk)
        # Use the new CommunityMembership model
        is_member = CommunityMembership.objects.filter(
            community=community,
            user_id=user_id,
            status='approved'
        ).exists()
        return Response({'is_member': is_member})

class AddQuestionToCommunity(generics.CreateAPIView):
    """Add an existing question to a community"""
    serializer_class = CommunityQuestionSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        community = get_object_or_404(Community, pk=pk)
        
        # Check if user is a member of the community
        if not community.is_member(request.user):
            return Response({
                'status': 'error',
                'message': 'You must be a member to add questions to this community'
            }, status=403)
        
        question_id = request.data.get('question_id')
        if not question_id:
            return Response({
                'status': 'error',
                'message': 'Question ID is required'
            }, status=400)
        
        try:
            from api.models import Question
            question = Question.objects.get(id=question_id)
            
            # Check if question is already in community
            if CommunityQuestion.objects.filter(community=community, question=question).exists():
                return Response({
                    'status': 'error',
                    'message': 'Question already exists in this community'
                }, status=400)
            
            community_question = CommunityQuestion.objects.create(
                community=community,
                question=question
            )
            
            serializer = CommunityQuestionSerializer(community_question)
            return Response({
                'status': 'success',
                'data': serializer.data
            }, status=201)
            
        except Question.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Question not found'
            }, status=404)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=500)

class RemoveQuestionFromCommunity(generics.DestroyAPIView):
    """Remove a question from a community"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, question_id):
        community = get_object_or_404(Community, pk=pk)
        
        # Check if user is a member or creator of the community
        if not (community.is_member(request.user) or community.creator == request.user):
            return Response({
                'status': 'error',
                'message': 'Permission denied'
            }, status=403)
        
        try:
            community_question = CommunityQuestion.objects.get(
                community=community,
                question_id=question_id
            )
            community_question.delete()
            
            return Response({
                'status': 'success',
                'message': 'Question removed from community'
            })
            
        except CommunityQuestion.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Question not found in this community'
            }, status=404)


# =============================================================================
# COMMUNITY CHAT/MESSAGING ENDPOINTS
# =============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def community_messages(request, pk):
    """
    GET: Get all messages for a community
    POST: Create a new message in the community
    """
    community = get_object_or_404(Community, pk=pk)
    
    # Check if user is a member
    if not community.is_member(request.user):
        return Response({
            'status': 'error',
            'message': 'You must be a member to view or post messages'
        }, status=403)
    
    if request.method == 'GET':
        try:
            # Get only top-level messages (no parent)
            messages = CommunityMessage.objects.filter(
                community=community, 
                parent_message=None
            ).order_by('-created_at')
            
            # Pagination
            page_size = int(request.GET.get('page_size', 20))
            page = int(request.GET.get('page', 1))
            start = (page - 1) * page_size
            end = start + page_size
            
            paginated_messages = messages[start:end]
            
            serializer = CommunityMessageSerializer(
                paginated_messages, 
                many=True, 
                context={'request': request}
            )
            
            return Response({
                'status': 'success',
                'data': serializer.data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': messages.count(),
                    'has_next': end < messages.count()
                }
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to fetch messages: {str(e)}'
            }, status=500)
    
    elif request.method == 'POST':
        try:
            serializer = CommunityMessageCreateSerializer(data=request.data)
            if serializer.is_valid():
                message = serializer.save(
                    author=request.user,
                    community=community
                )
                
                # If it's a question type, also create a Question object
                if message.message_type == 'question':
                    from api.models import Question
                    question = Question.objects.create(
                        title=message.question_title,
                        description=message.content,
                        user=request.user,
                        tags=message.question_tags or []
                    )
                    
                    # Link the question to the community
                    CommunityQuestion.objects.create(
                        question=question,
                        community=community
                    )
                
                response_serializer = CommunityMessageSerializer(
                    message, 
                    context={'request': request}
                )
                return Response({
                    'status': 'success',
                    'data': response_serializer.data
                }, status=201)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Invalid data',
                    'errors': serializer.errors
                }, status=400)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to create message: {str(e)}'
            }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reply_to_message(request, pk, message_id):
    """
    Reply to a specific message in a community
    """
    community = get_object_or_404(Community, pk=pk)
    parent_message = get_object_or_404(CommunityMessage, id=message_id, community=community)
    
    # Check if user is a member
    if not community.is_member(request.user):
        return Response({
            'status': 'error',
            'message': 'You must be a member to reply to messages'
        }, status=403)
    
    try:
        content = request.data.get('content')
        if not content or not content.strip():
            return Response({
                'status': 'error',
                'message': 'Reply content is required'
            }, status=400)
        
        reply = CommunityMessage.objects.create(
            content=content,
            author=request.user,
            community=community,
            parent_message=parent_message,
            message_type='message'  # Replies are always regular messages
        )
        
        # Notify all community members about the new reply
        community_members = CommunityMembership.objects.filter(
            community=community,
            status='approved'
        ).exclude(user=request.user).select_related('user')
        
        for membership in community_members:
            Notification.create_notification(
                recipient=membership.user,
                notification_type='community_post',
                title=f'New reply in {community.name}',
                message=f'{request.user.name or request.user.username} replied: {content[:50]}...',
                sender=request.user,
                action_url=f'/communities/{community.id}/messages'
            )
        
        serializer = CommunityMessageSerializer(reply, context={'request': request})
        return Response({
            'status': 'success',
            'data': serializer.data
        }, status=201)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to create reply: {str(e)}'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_message(request, pk, message_id):
    """
    Toggle like on a community message
    """
    community = get_object_or_404(Community, pk=pk)
    message = get_object_or_404(CommunityMessage, id=message_id, community=community)
    
    # Check if user is a member
    if not community.is_member(request.user):
        return Response({
            'status': 'error',
            'message': 'You must be a member to like messages'
        }, status=403)
    
    try:
        like, created = CommunityMessageLike.objects.get_or_create(
            user=request.user,
            message=message
        )
        
        if not created:
            # Unlike if already liked
            like.delete()
            action = 'unliked'
        else:
            action = 'liked'
        
        return Response({
            'status': 'success',
            'message': f'Message {action}',
            'like_count': message.like_count,
            'is_liked': created
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to like message: {str(e)}'
        }, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_message(request, pk, message_id):
    """
    Delete a message (only by author or community creator)
    """
    community = get_object_or_404(Community, pk=pk)
    message = get_object_or_404(CommunityMessage, id=message_id, community=community)
    
    # Check permissions
    if message.author != request.user and not community.is_admin(request.user):
        return Response({
            'status': 'error',
            'message': 'You can only delete your own messages or messages in communities you admin'
        }, status=403)
    
    try:
        message.delete()
        return Response({
            'status': 'success',
            'message': 'Message deleted successfully'
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to delete message: {str(e)}'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ask_community_question(request, pk):
    """
    Ask a question directly in a community
    """
    community = get_object_or_404(Community, pk=pk)
    
    # Check if user is a member
    if not community.is_member(request.user):
        return Response({
            'status': 'error',
            'message': 'You must be a member to ask questions in this community'
        }, status=403)
    
    try:
        title = request.data.get('title')
        content = request.data.get('content') or request.data.get('description')
        tags = request.data.get('tags', [])
        
        if not title or not content:
            return Response({
                'status': 'error',
                'message': 'Title and content are required'
            }, status=400)
        
        # Create the question in the main Question model
        from api.models import Question
        question = Question.objects.create(
            title=title,
            description=content,
            user=request.user,
            tags=tags if isinstance(tags, list) else []
        )
        
        # Link the question to the community
        community_question = CommunityQuestion.objects.create(
            question=question,
            community=community
        )
        
        # Create a community message for the question
        community_message = CommunityMessage.objects.create(
            content=content,
            message_type='question',
            author=request.user,
            community=community,
            question_title=title,
            question_tags=tags if isinstance(tags, list) else []
        )
        
        # Notify all community members about the new question
        community_members = CommunityMembership.objects.filter(
            community=community,
            status='approved'
        ).exclude(user=request.user).select_related('user')
        
        for membership in community_members:
            Notification.create_notification(
                recipient=membership.user,
                notification_type='community_post',
                title=f'New question in {community.name}',
                message=f'{request.user.name or request.user.username} asked: {title}',
                sender=request.user,
                action_url=f'/communities/{community.id}/messages'
            )
        
        # Return the community question data
        from .serializers import CommunityQuestionSerializer
        serializer = CommunityQuestionSerializer(community_question)
        
        return Response({
            'status': 'success',
            'data': serializer.data,
            'message': 'Question posted successfully to community'
        }, status=201)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to create question: {str(e)}'
        }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_current_user_membership(request, pk):
    """
    Check if the current authenticated user is a member of the community
    """
    try:
        community = get_object_or_404(Community, pk=pk)
        membership = CommunityMembership.objects.filter(
            community=community,
            user=request.user
        ).first()
        
        is_member = membership and membership.status == 'approved'
        is_admin = membership and membership.role == 'admin' and membership.status == 'approved'
        has_pending_request = membership and membership.status == 'pending'
        
        return Response({
            'status': 'success',
            'is_member': is_member,
            'is_admin': is_admin,
            'has_pending_request': has_pending_request,
            'membership_status': membership.status if membership else None,
            'user_id': request.user.id,
            'community_id': community.id
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)


# =============================================================================
# COMMUNITY ADMIN ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_join_requests(request, pk):
    """
    Get all pending join requests for a community (admin only)
    """
    try:
        community = get_object_or_404(Community, pk=pk)
        
        # Check if user is admin
        if not community.is_admin(request.user):
            return Response({
                'status': 'error',
                'message': 'Only admins can view join requests'
            }, status=403)
        
        pending_requests = CommunityMembership.objects.filter(
            community=community,
            status='pending'
        ).select_related('user').order_by('-requested_at')
        
        requests_data = []
        for membership in pending_requests:
            user = membership.user
            requests_data.append({
                'id': membership.id,
                'user': {
                    'id': user.id,
                    'name': user.name or user.username,
                    'username': user.username,
                    'email': user.email,
                    'institution': user.institution,
                    'profile_picture': user.profile_picture.url if user.profile_picture else None
                },
                'requested_at': membership.requested_at
            })
        
        return Response({
            'status': 'success',
            'data': requests_data,
            'count': len(requests_data)
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_join_request(request, pk, membership_id):
    """
    Approve a join request (admin only)
    """
    try:
        community = get_object_or_404(Community, pk=pk)
        
        # Check if user is admin
        if not community.is_admin(request.user):
            return Response({
                'status': 'error',
                'message': 'Only admins can approve join requests'
            }, status=403)
        
        membership = get_object_or_404(CommunityMembership, id=membership_id, community=community)
        
        if membership.status != 'pending':
            return Response({
                'status': 'error',
                'message': 'Request is not pending'
            }, status=400)
        
        # Approve the membership
        membership.status = 'approved'
        membership.approved_at = timezone.now()
        membership.approved_by = request.user
        membership.save()
        
        # Notify the user
        Notification.create_notification(
            recipient=membership.user,
            notification_type='community_request_approved',
            title=f'Welcome to {community.name}!',
            message=f'Your request to join {community.name} has been approved.',
            sender=request.user,
            action_url=f'/communities/{community.id}'
        )
        
        return Response({
            'status': 'success',
            'message': 'Join request approved successfully',
            'member_count': community.member_count
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decline_join_request(request, pk, membership_id):
    """
    Decline a join request (admin only)
    """
    try:
        community = get_object_or_404(Community, pk=pk)
        
        # Check if user is admin
        if not community.is_admin(request.user):
            return Response({
                'status': 'error',
                'message': 'Only admins can decline join requests'
            }, status=403)
        
        membership = get_object_or_404(CommunityMembership, id=membership_id, community=community)
        
        if membership.status != 'pending':
            return Response({
                'status': 'error',
                'message': 'Request is not pending'
            }, status=400)
        
        # Decline the membership
        membership.status = 'declined'
        membership.approved_at = timezone.now()
        membership.approved_by = request.user
        membership.save()
        
        # Notify the user
        Notification.create_notification(
            recipient=membership.user,
            notification_type='community_request_declined',
            title=f'Join request declined',
            message=f'Your request to join {community.name} has been declined.',
            sender=request.user,
            action_url=f'/communities/{community.id}'
        )
        
        return Response({
            'status': 'success',
            'message': 'Join request declined successfully',
            'member_count': community.member_count
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_community_members(request, pk):
    """
    Get all members of a community with their roles
    """
    try:
        community = get_object_or_404(Community, pk=pk)
        
        # Check if user is a member
        if not community.is_member(request.user):
            return Response({
                'status': 'error',
                'message': 'Only members can view community members'
            }, status=403)
        
        members = CommunityMembership.objects.filter(
            community=community,
            status='approved'
        ).select_related('user').order_by('role', 'approved_at')
        
        members_data = []
        for membership in members:
            user = membership.user
            members_data.append({
                'id': membership.id,
                'user': {
                    'id': user.id,
                    'name': user.name or user.username,
                    'username': user.username,
                    'institution': user.institution,
                    'profile_picture': user.profile_picture.url if user.profile_picture else None
                },
                'role': membership.role,
                'joined_at': membership.approved_at
            })
        
        return Response({
            'status': 'success',
            'data': members_data,
            'count': len(members_data)
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_community(request, pk):
    """
    Delete a community (admin/creator only)
    """
    try:
        community = get_object_or_404(Community, pk=pk)
        
        # Check if user is admin or creator
        if not community.is_admin(request.user) and community.creator != request.user:
            return Response({
                'status': 'error',
                'message': 'Only admins or the community creator can delete this community'
            }, status=403)
        
        # Store community name for notification
        community_name = community.name
        
        # Get all community members before deletion for notifications
        members = CommunityMembership.objects.filter(
            community=community,
            status='approved'
        ).exclude(user=request.user).select_related('user')
        
        # Notify all members about community deletion
        for membership in members:
            Notification.create_notification(
                recipient=membership.user,
                notification_type='system',
                title=f'Community "{community_name}" has been deleted',
                message=f'The community "{community_name}" has been permanently deleted by an administrator.',
                sender=request.user,
                action_url='/communities'
            )
        
        # Delete the community (this will cascade delete related objects)
        community.delete()
        
        return Response({
            'status': 'success',
            'message': f'Community "{community_name}" has been successfully deleted'
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)