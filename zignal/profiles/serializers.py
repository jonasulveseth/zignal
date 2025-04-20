from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id', 'email')

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Profile
        fields = (
            'id', 'user', 'bio', 'position', 'phone_number', 'profile_image',
            'linkedin_url', 'twitter_url', 'github_url', 'website_url',
            'email_notifications', 'dark_mode', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = (
            'bio', 'position', 'phone_number', 'profile_image',
            'linkedin_url', 'twitter_url', 'github_url', 'website_url',
            'email_notifications', 'dark_mode'
        ) 