from django.urls import path
from . import views

urlpatterns = [
    path('user_login/', views.user_login, name='user_login'),
    path('signup/', views.signup, name='signup'),
    path('users/<int:id>/', views.update_user, name='update_user'),
    path('users/<int:id>/', views.get_user_profile, name='get_user_profile'),
    path('hot_questions/', views.get_hot_questions, name='get_hot_questions'),
    path('new_users/', views.get_new_users, name='get_new_users'),
    path('logout/', views.user_logout, name='user_logout'),
    path('auth/reset-password/request/', views.request_password_reset, name='request_password_reset'),
    path('auth/reset-password/', views.reset_password, name='reset_password'),
]