from django.urls import path
from . import views

urlpatterns = [
    # Authentication endpoints
    path('user_login/', views.user_login, name='user_login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.user_logout, name='logout'),

    # User endpoints
    path('users/<int:id>/update/', views.update_user, name='update_user'),
    path('users/<int:id>/profile/', views.get_user_profile, name='get_user_profile'),
    path('users/<int:user_id>/questions/', views.user_questions, name='user_questions'),
    path('users/<int:user_id>/questions/interests/', views.user_questions_by_interests, name='user_questions_by_interests'),
    path('users/<int:user_id>/bookmarks/', views.user_bookmarks, name='user_bookmarks'),

    # Question endpoints
    path('questions/', views.questions_list_create, name='questions_list_create'),
    path('questions/<int:question_id>/', views.question_detail, name='question_detail'),
    path('questions/<int:question_id>/vote/', views.vote_question, name='vote_question'),
    path('questions/<int:question_id>/bookmark/', views.bookmark_question, name='bookmark_question'),
    path('questions/<int:question_id>/answers/', views.question_answers, name='question_answers'),
    path('questions/hot/', views.get_hot_questions, name='get_hot_questions'),
    path('questions/trending/', views.trending_questions, name='trending_questions'),

    # Answer endpoints
    path('answers/<int:answer_id>/', views.answer_detail, name='answer_detail'),
    path('answers/<int:answer_id>/vote/', views.vote_answer, name='vote_answer'),
    path('answers/<int:answer_id>/accept/', views.accept_answer, name='accept_answer'),

    # Notification endpoints
    path('notifications/', views.user_notifications, name='user_notifications'),
    path('notifications/summary/', views.notification_summary, name='notification_summary'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),

    # Search endpoints
    path('search/questions/', views.search_questions, name='search_questions'),
    path('search/users/', views.search_users, name='search_users'),
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
    path('search/analytics/', views.search_analytics, name='search_analytics'),
    path('communities/search/', views.search_communities, name='search_communities'),

    # Trending endpoints
    path('trending/tags/', views.trending_tags, name='trending_tags'),
    path('trending/topics/', views.trending_topics, name='trending_topics'),
    path('trending/users/', views.trending_users, name='trending_users'),

    # Other endpoints
    path('new_users/', views.get_new_users, name='get_new_users'),

    # Password reset endpoints
    path('auth/reset-password/request/', views.request_password_reset, name='request_password_reset'),
    path('auth/reset-password/', views.reset_password, name='reset_password'),
]
