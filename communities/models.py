from django.db import models
from api.models import CustomUser, Question

class Community(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    creator = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_communities')
    members = models.ManyToManyField(CustomUser, related_name='communities')
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "communities"

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        # Use the new CommunityMembership model for accurate count
        return self.communitymembership_set.filter(status='approved').count()
    
    @property
    def admin_count(self):
        return self.communitymembership_set.filter(role='admin').count()
    
    def is_admin(self, user):
        """Check if a user is an admin of this community"""
        return self.communitymembership_set.filter(user=user, role='admin').exists()
    
    def is_member(self, user):
        """Check if a user is a member of this community"""
        return self.communitymembership_set.filter(user=user, status='approved').exists()
    
    def has_pending_request(self, user):
        """Check if a user has a pending join request"""
        return self.communitymembership_set.filter(user=user, status='pending').exists()

class CommunityMembership(models.Model):
    """
    Through model for Community members with roles and request status
    """
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('member', 'Member'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]
    
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_memberships')
    
    class Meta:
        unique_together = ('community', 'user')
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"{self.user.name or self.user.username} in {self.community.name} ({self.role}, {self.status})"

class CommunityQuestion(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='community_questions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('question', 'community')

class CommunityMessage(models.Model):
    """
    Model for community chat messages and discussions
    """
    MESSAGE_TYPES = [
        ('message', 'Regular Message'),
        ('question', 'Community Question'),
        ('announcement', 'Announcement'),
    ]
    
    content = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='message')
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='community_messages')
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='messages')
    parent_message = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(default=False)
    likes = models.ManyToManyField(CustomUser, through='CommunityMessageLike', related_name='liked_messages')
    
    # For community questions
    question_title = models.CharField(max_length=255, blank=True, null=True)
    question_tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.author.name or self.author.username} in {self.community.name}: {self.content[:50]}..."
    
    @property
    def reply_count(self):
        return self.replies.count()
    
    @property
    def like_count(self):
        return self.likes.count()

class CommunityMessageLike(models.Model):
    """
    Through model for message likes
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.ForeignKey(CommunityMessage, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'message')