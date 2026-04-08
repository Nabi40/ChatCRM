from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ChatRequestSerializer
from .services import process_chat


class ChatAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = process_chat(
            email=data["email"],
            message=data["message"],
            session_key=data.get("session_key", ""),
        )

        http_status = status.HTTP_200_OK if result.get("ok") else status.HTTP_404_NOT_FOUND
        return Response(result, status=http_status)