from rest_framework import serializers

class UserSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100)
    password = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    role = serializers.CharField(max_length=50)
    age = serializers.IntegerField()
    gender = serializers.CharField(max_length=100)


class MedicinalItemSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(allow_blank=True)
    category = serializers.ChoiceField(choices=['medicine', 'equipment', 'other'])
    quantity = serializers.IntegerField()
    expiration_date = serializers.CharField(allow_null=True)
    amount = serializers.IntegerField()
    image = serializers.URLField(required=False)
   