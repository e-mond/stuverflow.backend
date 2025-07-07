from rest_framework import serializers
from api.serializers import UserSerializer, QuestionSerializer
from .models import Community, CommunityQuestion, CommunityMessage, CommunityMessageLike

class CommunityMessageSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    like_count = serializers.ReadOnlyField()
    reply_count = serializers.ReadOnlyField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = CommunityMessage
        fields = [
            'id', 'content', 'message_type', 'author', 'community', 'parent_message',
            'created_at', 'updated_at', 'is_pinned', 'question_title', 'question_tags',
            'replies', 'like_count', 'reply_count', 'is_liked'
        ]
        read_only_fields = ['created_at', 'updated_at', 'like_count', 'reply_count']
    
    def get_replies(self, obj):
        if obj.parent_message is None:  # Only get replies for top-level messages
            replies = obj.replies.all()[:10]  # Limit to 10 most recent replies
            return CommunityMessageSerializer(replies, many=True, context=self.context).data
        return []
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

class CommunitySerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    members = serializers.SerializerMethodField()
    member_count = serializers.IntegerField(read_only=True)
    recent_messages = serializers.SerializerMethodField()
    
    class Meta:
        model = Community
        fields = ['id', 'name', 'description', 'creator', 'members', 'created_at', 'is_public', 'member_count', 'recent_messages']
    
    def get_members(self, obj):
        # Return array of member IDs using the new CommunityMembership model
        return list(obj.communitymembership_set.filter(status='approved').values_list('user__id', flat=True))
    
    def get_recent_messages(self, obj):
        # Get the 5 most recent messages for the community page preview
        recent_messages = obj.messages.filter(parent_message=None)[:5]  # Only top-level messages
        return CommunityMessageSerializer(recent_messages, many=True, context=self.context).data

class CommunityQuestionSerializer(serializers.ModelSerializer):
    question = QuestionSerializer()
    
    class Meta:
        model = CommunityQuestion
        fields = ['id', 'question', 'community', 'created_at']
        depth = 1

class JoinLeaveSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

class CommunityMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating community messages"""
    
    class Meta:
        model = CommunityMessage
        fields = ['content', 'message_type', 'parent_message', 'question_title', 'question_tags']
    
    def validate(self, data):
        if data.get('message_type') == 'question' and not data.get('question_title'):
            raise serializers.ValidationError("Question title is required for question messages")
        return data