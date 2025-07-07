from django.urls import path
from .views import (
    CommunityListCreate,
    CommunityDetail,
    JoinCommunity,
    LeaveCommunity,
    CommunityQuestions,
    CheckMembership,
    AddQuestionToCommunity,
    RemoveQuestionFromCommunity,
    community_messages,
    reply_to_message,
    like_message,
    delete_message,
    ask_community_question,
    check_current_user_membership,
    get_join_requests,
    approve_join_request,
    decline_join_request,
    get_community_members,
    delete_community
)

urlpatterns = [
    # Community management
    path('', CommunityListCreate.as_view(), name='community-list'),
    path('<int:pk>/', CommunityDetail.as_view(), name='community-detail'),
    path('<int:pk>/members/<int:user_id>/', CheckMembership.as_view(), name='check-membership'),
    path('<int:pk>/membership/', check_current_user_membership, name='check-current-user-membership'),
    path('<int:pk>/join/', JoinCommunity.as_view(), name='join-community'),
    path('<int:pk>/leave/', LeaveCommunity.as_view(), name='leave-community'),
    
    # Community admin
    path('<int:pk>/admin/join-requests/', get_join_requests, name='get-join-requests'),
    path('<int:pk>/admin/join-requests/<int:membership_id>/approve/', approve_join_request, name='approve-join-request'),
    path('<int:pk>/admin/join-requests/<int:membership_id>/decline/', decline_join_request, name='decline-join-request'),
    path('<int:pk>/members/', get_community_members, name='get-community-members'),
    path('<int:pk>/delete/', delete_community, name='delete-community'),
    
    # Community questions
    path('<int:pk>/questions/', CommunityQuestions.as_view(), name='community-questions'),
    path('<int:pk>/questions/add/', AddQuestionToCommunity.as_view(), name='add-question-to-community'),
    path('<int:pk>/questions/ask/', ask_community_question, name='ask-community-question'),
    path('<int:pk>/questions/<int:question_id>/remove/', RemoveQuestionFromCommunity.as_view(), name='remove-question-from-community'),
    
    # Community chat/messaging
    path('<int:pk>/messages/', community_messages, name='community-messages'),
    path('<int:pk>/messages/<int:message_id>/reply/', reply_to_message, name='reply-to-message'),
    path('<int:pk>/messages/<int:message_id>/like/', like_message, name='like-message'),
    path('<int:pk>/messages/<int:message_id>/delete/', delete_message, name='delete-message'),
]