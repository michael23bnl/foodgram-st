import rest_framework.serializers as slz
from users.models import Follow
from recipes.models import Recipe, RecipeIngredient, Ingredient
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from djoser.serializers import TokenCreateSerializer
from django.contrib.auth import authenticate
from rest_framework.exceptions import ValidationError
from .services import Base64ImageField
User = get_user_model()


class RecipeIngredientSerializer(slz.ModelSerializer):
    id = slz.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = slz.IntegerField(min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'amount']


class IngredientSerializer(slz.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class RecipeSerializer(slz.ModelSerializer):
    is_favorited = slz.SerializerMethodField()
    is_in_shopping_cart = slz.SerializerMethodField()
    author = slz.SerializerMethodField()
    ingredients = RecipeIngredientSerializer(many=True, write_only=True)

    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'author', 'name', 'image', 'text', 'ingredients',
                  'cooking_time', 'is_favorited', 'is_in_shopping_cart')

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and obj.favorited_by.filter(user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and obj.in_shopping_cart.filter(user=user).exists()

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(user=request.user, following=obj).exists()
        return False

    def get_author(self, obj):
        return {
            'id': obj.author.id,
            'email': obj.author.email,
            'username': obj.author.username,
            'first_name': obj.author.first_name,
            'last_name': obj.author.last_name,
            'is_subscribed': self.get_is_subscribed(obj.author),
            'avatar': obj.author.avatar.url if obj.author.avatar else None
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        ingredients = []
        for recipe_ingredient in instance.ingredients_amounts.all():
            ingredient_data = IngredientSerializer(
                recipe_ingredient.ingredient).data
            ingredient_data['amount'] = recipe_ingredient.amount
            ingredients.append(ingredient_data)
        representation['ingredients'] = ingredients
        return representation

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        if not ingredients_data:
            raise ValidationError(
                {"ingredients": ["Список ингредиентов не может быть пустым."]})

        ingredient_ids = [item['id'] for item in ingredients_data]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise ValidationError(
                {"ingredients": ["Ингредиенты не должны повторяться."]})

        user = self.context['request'].user
        recipe = Recipe.objects.create(author=user, **validated_data)

        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount']
            )
            for item in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)

        if not ingredients_data:
            raise ValidationError(
                {"ingredients": ["Список ингредиентов не может быть пустым."]})

        ingredient_ids = [item['id'] for item in ingredients_data]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise ValidationError(
                {"ingredients": ["Ингредиенты не должны повторяться."]})

        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time)
        if cooking_time < 1:
            raise ValidationError(
                {"cooking_time": ["Время готовки не может быть меньше 1."]})
        instance.cooking_time = cooking_time
        if 'image' in validated_data:
            instance.image = validated_data.get('image', instance.image)

        instance.save()

        if ingredients_data is not None:

            instance.ingredients.clear()

            recipe_ingredients = [
                RecipeIngredient(
                    recipe=instance,
                    ingredient=item['id'],
                    amount=item['amount']
                )
                for item in ingredients_data
            ]
            RecipeIngredient.objects.bulk_create(recipe_ingredients)

        return instance


class UserSerializer(slz.ModelSerializer):
    password = slz.CharField(write_only=True)
    recipes = RecipeSerializer(many=True, read_only=True)
    recipes_count = slz.IntegerField(read_only=True)
    avatar = slz.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'password', 'recipes', 'recipes_count', 'avatar'
        )

    def get_avatar(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None

    def validate_username(self, value):
        if self.instance and User.objects.filter(username=value).exclude(pk=self.instance.pk).exists():
            raise slz.ValidationError(
                "Пользователь с таким именем уже существует.")
        elif not self.instance and User.objects.filter(username=value).exists():
            raise slz.ValidationError(
                "Пользователь с таким именем уже существует.")
        return value

    def validate_email(self, value):
        if self.instance and User.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
            raise slz.ValidationError(
                "Пользователь с таким email уже существует.")
        elif not self.instance and User.objects.filter(email=value).exists():
            raise slz.ValidationError(
                "Пользователь с таким email уже существует.")
        return value

    def validate_password(self, value):
        if value:
            try:
                validate_password(value)
            except DjangoValidationError as e:
                raise slz.ValidationError(e.messages)
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data, password=password)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)


class ChangePasswordSerializer(slz.Serializer):
    current_password = slz.CharField(write_only=True)
    new_password = slz.CharField(write_only=True)


class CustomTokenCreateSerializer(TokenCreateSerializer):
    email = slz.EmailField()

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(request=self.context.get(
                "request"), email=email, password=password)

            if not user:
                raise slz.ValidationError("Неверные email или пароль.")

            attrs["user"] = user
            return attrs
        else:
            raise slz.ValidationError("Email и пароль обязательны.")


class ShortRecipeSerializer(slz.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class FollowSerializer(slz.ModelSerializer):
    is_subscribed = slz.SerializerMethodField()
    recipes = slz.SerializerMethodField()
    recipes_count = slz.SerializerMethodField()
    avatar = slz.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "email", "username", "first_name", "last_name",
            "is_subscribed", "recipes", "recipes_count", "avatar"
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(user=request.user, following=obj).exists()
        return False

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get(
            'recipes_limit') if request else None

        recipes = Recipe.objects.filter(author=obj)

        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[:int(recipes_limit)]

        return ShortRecipeSerializer(recipes, many=True, context=self.context).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()

    def get_avatar(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None
