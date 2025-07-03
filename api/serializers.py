from rest_framework import serializers
from .models import CustomUser, Question

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'email', 'handle', 'institution', 'bio', 'dob', 'interests', 'title', 'expertise', 'certifications', 'profile_picture', 'date_joined']

class QuestionSerializer(serializers.ModelSerializer):
    user = UserSerializer()  # Nested serializer for user
    class Meta:
        model = Question
        fields = ['id', 'title', 'description', 'user', 'tags', 'created_at', 'views', 'upvotes', 'downvotes', 'answers', 'isBookmarked']