from rest_framework import serializers
from .models import CustomUser, Question, Answer, Bookmark, Notification

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'email', 'handle', 'institution', 'bio', 'dob', 'interests', 'title', 'expertise', 'certifications', 'profile_picture', 'date_joined']

class AnswerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # Nested serializer for user
    
    class Meta:
        model = Answer
        fields = ['id', 'content', 'user', 'question', 'created_at', 'upvotes', 'downvotes', 'is_accepted']

class BookmarkSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # Nested serializer for user
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())  # Question reference
    
    class Meta:
        model = Bookmark
        fields = ['id', 'user', 'question', 'created_at']

class NotificationSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)  # Nested serializer for sender
    recipient = UserSerializer(read_only=True)  # Nested serializer for recipient
    related_question_title = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'sender', 'notification_type', 'title', 'message',
            'related_question', 'related_answer', 'is_read', 'created_at',
            'action_url', 'related_question_title', 'time_ago'
        ]
    
    def get_related_question_title(self, obj):
        """Get the title of the related question if it exists."""
        if obj.related_question:
            return obj.related_question.title
        return None
    
    def get_time_ago(self, obj):
        """Get a human-readable time ago string."""
        from django.utils import timezone
        from datetime import datetime, timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 7:
            return obj.created_at.strftime('%b %d, %Y')
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"

class QuestionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # Nested serializer for user
    question_answers = AnswerSerializer(many=True, read_only=True)  # Include answers
    isBookmarked = serializers.SerializerMethodField()  # Dynamic bookmark status
    
    class Meta:
        model = Question
        fields = ['id', 'title', 'description', 'user', 'tags', 'created_at', 'views', 'upvotes', 'downvotes', 'answers', 'isBookmarked', 'question_answers']
    
    def get_isBookmarked(self, obj):
        """
        Get the bookmark status for the current user
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return Bookmark.objects.filter(user=request.user, question=obj).exists()
        return False