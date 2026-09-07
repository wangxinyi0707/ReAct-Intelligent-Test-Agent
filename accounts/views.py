from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserProfile
from .serializers import RegisterSerializer, UserSerializer


class RegisterView(APIView):
    """用户注册：校验通过后创建用户与资料，返回用户信息"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        UserProfile.objects.create(user=user)
        return Response(
            {"message": "注册成功", "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class ProfileView(APIView):
    """获取 / 更新当前登录用户资料"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def put(self, request):
        profile = request.user.profile
        for field in [
            "nickname",
            "phone",
            "preferred_destinations",
            "travel_style",
            "budget_level",
            "language",
        ]:
            if field in request.data:
                setattr(profile, field, request.data[field])
        profile.save()
        return Response({"message": "更新成功", "user": UserSerializer(request.user).data})


class LogoutView(APIView):
    """退出登录：将 refresh token 加入黑名单，使其失效"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response({"error": "缺少 refresh token"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh).blacklist()
        except Exception:
            return Response({"error": "token 已失效"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "退出成功"})
