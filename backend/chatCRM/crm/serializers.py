from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    message = serializers.CharField()
    session_key = serializers.CharField(required=False, allow_blank=True)