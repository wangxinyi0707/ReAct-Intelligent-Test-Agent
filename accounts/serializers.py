from django.contrib.auth.models import User
from rest_framework import serializers

from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    """用户旅行偏好资料序列化器"""

    class Meta:
        model = UserProfile
        fields = [
            "nickname",
            "phone",
            "preferred_destinations",
            "travel_style",
            "budget_level",
            "language",
        ]


class UserSerializer(serializers.ModelSerializer):
    """用户信息序列化器，嵌套返回资料信息"""

    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "profile"]


class RegisterSerializer(serializers.ModelSerializer):
    """注册序列化器：密码只写不读，带基础校验"""

    password = serializers.CharField(
        write_only=True, min_length=8, trim_whitespace=False
    )

    class Meta:
        model = User
        fields = ["username", "password", "email"]
        extra_kwargs = {
            "username": {"max_length": 150},
            "email": {"required": False, "allow_blank": True},
        }

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("用户名已存在")
        return value

    def create(self, validated_data):
        # create_user 内部使用 set_password 做加盐哈希，不存明文
        return User.objects.create_user(**validated_data)
