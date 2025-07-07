from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
import json

class CustomUser(AbstractUser):
    """
    CustomUser model extending AbstractUser to include additional profile fields.
    - Inherits username, email, password, first_name, last_name, etc., from AbstractUser.
    - Adds fields for bio, institution, handle, title, expertise, certifications, dob, interests, and profile_picture.
    - Custom save method to generate name from first_name and last_name if not set.
    - Overrides email to enforce uniqueness as it is the USERNAME_FIELD.

    Fields:
    - email: Email address, unique and used as the username for authentication.
    - bio: User's biography (optional).
    - institution: Educational or professional institution (optional).
    - handle: Unique handle (e.g., @username), optional but unique if provided.
    - title: Professional title (e.g., Dr, Prof), optional.
    - expertise: Area of expertise for professionals, optional.
    - certifications: Certification details or file names stored as JSON, optional.
    - dob: Date of birth, optional.
    - interests: Interests for students, optional.
    - profile_picture: Profile picture file, uploaded to 'profile_pics/', optional.
    - name: Full name, optional, derived from first_name and last_name if not set.
    """
    email = models.EmailField(_('email address'), unique=True, blank=False)  # Override to enforce uniqueness
    bio = models.TextField(blank=True, null=True, help_text="User's biography.")
    institution = models.CharField(max_length=255, blank=True, null=True, help_text="Educational or professional institution.")
    handle = models.CharField(max_length=50, blank=True, null=True, unique=True, help_text="User's unique handle (e.g., @username).")
    title = models.CharField(max_length=50, blank=True, null=True, help_text="Professional title (e.g., Dr, Prof).")
    expertise = models.CharField(max_length=255, blank=True, null=True, help_text="Area of expertise for professionals.")
    certifications = models.TextField(blank=True, null=True, help_text="Certification details or file names as JSON.")
    dob = models.DateField(blank=True, null=True, help_text="Date of birth.")
    interests = models.TextField(blank=True, null=True, help_text="Interests for students.")
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True, help_text="Profile picture file.")
    name = models.CharField(max_length=255, blank=True, null=True, help_text="Full name of the user.")

    USERNAME_FIELD = 'email'  # Use email as the username field for authentication
    REQUIRED_FIELDS = ['name']  # Name is required during user creation

    def __str__(self):
        """Return a string representation of the user."""
        return self.name or self.username or self.handle or self.email

    def save(self, *args, **kwargs):
        """Override save to generate name from first_name and last_name if not set."""
        if not self.name and (self.first_name or self.last_name):
            self.name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        # Validate handle starts with '@' if provided
        if self.handle and not self.handle.startswith('@'):
            raise ValidationError("Handle must start with '@'")
        super().save(*args, **kwargs)

    def clean(self):
        """Validate model fields before saving."""
        if self.handle and not self.handle.startswith('@'):
            raise ValidationError({'handle': "Handle must start with '@'"})
        if self.certifications:
            try:
                json.loads(self.certifications)  # Ensure JSON is valid
            except json.JSONDecodeError:
                raise ValidationError({'certifications': "Certifications must be valid JSON"})
        if not self.email:
            raise ValidationError({'email': "Email is required"})

class Question(models.Model):
    """
    Question model to store user-submitted questions.
    - title: Question title.
    - description: Detailed question content.
    - user: Foreign key to CustomUser who posted the question.
    - tags: JSON list of tags associated with the question.
    - created_at: Timestamp of question creation.
    - views: Number of views, default 0.
    - upvotes: Number of upvotes, default 0.
    - downvotes: Number of downvotes, default 0.
    - answers: JSON list of answer IDs or content, default empty.
    - isBookmarked: Boolean indicating if the question is bookmarked, default False.
    """
    title = models.CharField(max_length=255)
    description = models.TextField()
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    tags = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    views = models.IntegerField(default=0)
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)
    answers = models.JSONField(default=list)
    isBookmarked = models.BooleanField(default=False)

    def __str__(self):
        """Return a string representation of the question."""
        return self.title

    def clean(self):
        """Validate model fields before saving."""
        if not self.title.strip():
            raise ValidationError({'title': "Title cannot be empty"})
        if not self.description.strip():
            raise ValidationError({'description': "Description cannot be empty"})
        try:
            json.loads(json.dumps(self.tags))  # Ensure tags are valid JSON
            json.loads(json.dumps(self.answers))  # Ensure answers are valid JSON
        except json.JSONDecodeError:
            raise ValidationError({'tags': "Tags must be valid JSON"})

class Answer(models.Model):
    """
    Answer model to store user responses to questions.
    - content: The answer content/text.
    - user: Foreign key to CustomUser who posted the answer.
    - question: Foreign key to the Question being answered.
    - created_at: Timestamp of answer creation.
    - upvotes: Number of upvotes, default 0.
    - downvotes: Number of downvotes, default 0.
    - is_accepted: Boolean indicating if this is the accepted answer.
    """
    content = models.TextField()
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='question_answers')
    created_at = models.DateTimeField(auto_now_add=True)
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)
    is_accepted = models.BooleanField(default=False)

    def __str__(self):
        """Return a string representation of the answer."""
        return f"Answer by {self.user.name or self.user.username} to '{self.question.title}'"

    def clean(self):
        """Validate model fields before saving."""
        if not self.content.strip():
            raise ValidationError({'content': "Answer content cannot be empty"})

    class Meta:
        ordering = ['-created_at']  # Show newest answers first

class Bookmark(models.Model):
    """
    Bookmark model to store user bookmarks for questions.
    - user: Foreign key to CustomUser who bookmarked the question.
    - question: Foreign key to the Question being bookmarked.
    - created_at: Timestamp of bookmark creation.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'question')  # Ensure a user can only bookmark a question once
        ordering = ['-created_at']  # Show newest bookmarks first

    def __str__(self):
        """Return a string representation of the bookmark."""
        return f"{self.user.name or self.user.username} bookmarked '{self.question.title}'"

class Notification(models.Model):
    """
    Notification model to store user notifications for various activities.
    - recipient: Foreign key to CustomUser who receives the notification.
    - sender: Foreign key to CustomUser who triggered the notification (optional).
    - notification_type: Type of notification (answer, vote, mention, etc.).
    - title: Short notification title.
    - message: Detailed notification message.
    - related_question: Foreign key to related Question (optional).
    - related_answer: Foreign key to related Answer (optional).
    - is_read: Boolean indicating if notification has been read.
    - created_at: Timestamp of notification creation.
    - action_url: URL to redirect when notification is clicked.
    """
    
    NOTIFICATION_TYPES = [
        ('answer', 'New Answer'),
        ('question_vote', 'Question Vote'),
        ('answer_vote', 'Answer Vote'),
        ('answer_accepted', 'Answer Accepted'),
        ('mention', 'Mention'),
        ('follow', 'New Follower'),
        ('bookmark', 'Question Bookmarked'),
        ('community_invite', 'Community Invitation'),
        ('community_question', 'Community Question'),
        ('community_join_request', 'Community Join Request'),
        ('community_request_approved', 'Community Request Approved'),
        ('community_request_declined', 'Community Request Declined'),
        ('community_post', 'Community Post'),
        ('community_admin_assigned', 'Community Admin Assigned'),
        ('system', 'System Notification'),
    ]
    
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_question = models.ForeignKey(Question, on_delete=models.CASCADE, null=True, blank=True)
    related_answer = models.ForeignKey(Answer, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    action_url = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']  # Show newest notifications first
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        """Return a string representation of the notification."""
        return f"{self.notification_type} notification for {self.recipient.name or self.recipient.username}"

    def mark_as_read(self):
        """Mark this notification as read."""
        self.is_read = True
        self.save(update_fields=['is_read'])

    @classmethod
    def create_notification(cls, recipient, notification_type, title, message, sender=None, 
                          related_question=None, related_answer=None, action_url=None):
        """
        Class method to create a new notification with proper validation.
        """
        # Don't create notification if recipient is the same as sender
        if sender and recipient.id == sender.id:
            return None
            
        return cls.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            related_question=related_question,
            related_answer=related_answer,
            action_url=action_url or f"/question/{related_question.id}" if related_question else None
        )

class PasswordResetToken(models.Model):
    """
    Model to store password reset tokens for users.
    - user: Foreign key to CustomUser.
    - token: Unique random string for reset verification.
    - created_at: Timestamp of token creation.
    - expires_at: Timestamp when the token expires (24 hours by default).
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    token = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        """Check if the token has expired."""
        return timezone.now() > self.expires_at

    def __str__(self):
        """Return a string representation of the token."""
        return f"Token for {self.user.email}"