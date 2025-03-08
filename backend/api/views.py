from rest_framework import filters, permissions, viewsets, mixins, viewsets, permissions, status
from rest_framework.generics import get_object_or_404
import api.serializers as sl
from collections import defaultdict
from recipes.models import Recipe, Ingredient, ShoppingCart
from users.models import Follow
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
import base64
import uuid
from .serializers import UserSerializer, ChangePasswordSerializer, RecipeSerializer, IngredientSerializer, FollowSerializer, ShortRecipeSerializer
from rest_framework.authtoken.models import Token
from django.contrib.auth import update_session_auth_hash
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from io import StringIO
import csv
from fpdf import FPDF
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import HttpResponse
from .paginations import CustomPagination
from rest_framework.exceptions import PermissionDenied
from .services import Base62Field
from django.shortcuts import redirect
from django.urls import reverse
User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    pagination_class = CustomPagination
    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = FollowSerializer(
                instance, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"detail": "Страница не найдена."}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(
                {"detail": "У вас нет прав доступа к этому ресурсу."},
                status=status.HTTP_403_FORBIDDEN
            )

        users = self.get_queryset()

        page = self.paginate_queryset(users)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['put', 'delete'], permission_classes=[permissions.IsAuthenticated], url_path='me/avatar')
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            avatar_data = request.data.get('avatar')

            if not avatar_data:
                return Response(
                    {"avatar": ["Это поле обязательно."]},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                if user.avatar:
                    user.avatar.delete()

                format, imgstr = avatar_data.split(';base64,')
                ext = format.split('/')[-1]
                data = ContentFile(base64.b64decode(imgstr),
                                   name=f"{uuid.uuid4()}.{ext}")

                user.avatar.save(data.name, data, save=True)
                user.save()

                avatar_url = request.build_absolute_uri(user.avatar.url)

                return Response({"avatar": avatar_url}, status=status.HTTP_200_OK)

            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        elif request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
                user.avatar = None
                user.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {"detail": "Аватар отсутствует."},
                    status=status.HTTP_404_NOT_FOUND
                )

    @action(detail=False, methods=['post'], url_path='set_password')
    def change_password(self, request):
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            current_password = serializer.validated_data['current_password']
            new_password = serializer.validated_data['new_password']

            if not user.check_password(current_password):
                return Response(
                    {"current_password": ["Неверный текущий пароль"]},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(new_password)
            user.save()

            update_session_auth_hash(request, user)

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='subscriptions', permission_classes=[permissions.IsAuthenticated])
    def get_subscriptions(self, request):
        user = request.user

        subscriptions = User.objects.filter(following__user=user)

        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = FollowSerializer(
                page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = FollowSerializer(
            subscriptions, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'delete'], url_path='subscribe', permission_classes=[permissions.IsAuthenticated])
    def manage_subscription(self, request, pk=None):
        user = request.user

        if request.method == 'POST':
            try:
                following_user = User.objects.get(pk=pk)

                if following_user == user:
                    return Response(
                        {"detail": "Невозможно подписаться на себя."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if Follow.objects.filter(user=user, following=following_user).exists():
                    return Response(
                        {"detail": "Вы уже подписаны на этого пользователя."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                Follow.objects.create(user=user, following=following_user)

                serializer = FollowSerializer(
                    following_user, context={'request': request})
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            except User.DoesNotExist:
                return Response(
                    {"detail": "Пользователь не найден."},
                    status=status.HTTP_404_NOT_FOUND
                )

        elif request.method == 'DELETE':
            try:
                following_user = User.objects.get(pk=pk)

                if following_user == user:
                    return Response(
                        {"detail": "Невозможно отписаться от себя."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                follow_instance = Follow.objects.filter(
                    user=user, following=following_user).first()

                if not follow_instance:
                    return Response(
                        {"detail": "Вы не подписаны на этого пользователя."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                follow_instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

            except User.DoesNotExist:
                return Response(
                    {"detail": "Пользователь не найден."},
                    status=status.HTTP_404_NOT_FOUND
                )


class LogoutViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def logout(self, request):
        try:
            Token.objects.get(user=request.user).delete()
        except Token.DoesNotExist:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().select_related(
        'author').prefetch_related('ingredients')
    serializer_class = RecipeSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = Recipe.objects.all().select_related(
            'author').prefetch_related('ingredients')

        user = self.request.user

        is_favorited = self.request.query_params.get('is_favorited')
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart')
        author = self.request.query_params.get('author')

        if author:
            queryset = queryset.filter(author_id=author)

        if user.is_authenticated:
            if is_favorited in ['1', 'true']:
                queryset = queryset.filter(favorited_by__user=user)

            if is_in_shopping_cart in ['1', 'true']:
                queryset = queryset.filter(in_shopping_cart__user=user)
        else:
            if is_favorited in ['1', 'true'] or is_in_shopping_cart in ['1', 'true']:
                queryset = queryset.none()

        return queryset

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied(
                "Вы должны быть авторизованы для выполнения этого действия.")
        serializer.save()

    def get_object(self):
        recipe = get_object_or_404(Recipe, id=self.kwargs["pk"])
        user = self.request.user

        recipe.is_favorited = user.is_authenticated and recipe.favorited_by.filter(
            user=user).exists()
        recipe.is_in_shopping_cart = user.is_authenticated and recipe.in_shopping_cart.filter(
            user=user).exists()

        return recipe

    def partial_update(self, request, *args, **kwargs):
        recipe = self.get_object()
        if recipe.author != request.user:
            return Response({"detail": "Недостаточно прав для редактирования."}, status=status.HTTP_403_FORBIDDEN)

        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        recipe = self.get_object()
        if recipe.author != request.user:
            return Response({"detail": "Недостаточно прав для удаления."}, status=status.HTTP_403_FORBIDDEN)

        self.perform_destroy(recipe)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request, pk=None):
        recipe = self.get_object()

        short_code = Base62Field.to_base62(recipe.id)

        short_link = f"http://localhost/s/{short_code}"

        return Response({"short-link": short_link}, status=status.HTTP_200_OK)

    def redirect_to_recipe(self, request, short_code=None):
        try:
            recipe_id = Base62Field.from_base62(short_code)
        except ValueError:
            return Response({"detail": "Неверный короткий код."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)

        redirect_url = f"http://localhost/recipes/{recipe.id}/"
        return redirect(redirect_url)

    @action(detail=True, methods=['post', 'delete'], url_path='shopping_cart', permission_classes=[permissions.IsAuthenticated])
    def manage_shopping_cart(self, request, pk=None):
        try:
            recipe = self.get_object()
            if request.method == 'POST':
                if ShoppingCart.objects.filter(user=request.user, recipe=recipe).exists():
                    return Response(
                        {"detail": "Рецепт уже в списке покупок."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                ShoppingCart.objects.create(user=request.user, recipe=recipe)

                recipe_serializer = ShortRecipeSerializer(recipe)
                return Response(recipe_serializer.data, status=status.HTTP_201_CREATED)

            elif request.method == 'DELETE':
                shopping_cart_item = ShoppingCart.objects.filter(
                    user=request.user, recipe=recipe).first()

                if not shopping_cart_item:
                    return Response(
                        {"detail": "Рецепт не найден в списке покупок."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                shopping_cart_item.delete()

                recipe_serializer = ShortRecipeSerializer(recipe)
                return Response(recipe_serializer.data, status=status.HTTP_204_NO_CONTENT)

        except Recipe.DoesNotExist:
            return Response(
                {"detail": "Рецепт не найден."},
                status=status.HTTP_404_NOT_FOUND
            )

    from collections import defaultdict

    @action(detail=False, methods=['get'], url_path='download_shopping_cart', permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        shopping_cart = Recipe.objects.filter(
            in_shopping_cart__user=request.user)
        ingredients_dict = defaultdict(
            lambda: {'amount': 0, 'measurement_unit': ''})

        for recipe in shopping_cart:
            for ri in recipe.ingredients_amounts.all():
                ingredient_name = ri.ingredient.name
                ingredients_dict[ingredient_name]['amount'] += ri.amount
                ingredients_dict[ingredient_name]['measurement_unit'] = ri.ingredient.measurement_unit

        ingredients_list = [{'name': name, 'amount': data['amount'], 'measurement_unit': data['measurement_unit']}
                            for name, data in ingredients_dict.items()]

        file_format = request.query_params.get('format', 'txt').lower()

        if file_format == 'txt':
            return self.generate_txt_file(ingredients_list)
        elif file_format == 'csv':
            return self.generate_csv_file(ingredients_list)
        elif file_format == 'pdf':
            return self.generate_pdf_file(ingredients_list)
        else:
            return Response({"detail": "Invalid file format requested"}, status=400)

    def generate_txt_file(self, ingredients):
        content = "\n".join(
            [f"{ingredient['name']} ({ingredient['measurement_unit']}) — {ingredient['amount']}" for ingredient in ingredients])
        response = HttpResponse(content, content_type="text/plain")
        response['Content-Disposition'] = 'attachment; filename="shopping_cart.txt"'
        return response

    def generate_csv_file(self, ingredients):
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Ингредиент', 'Количество',
                        'Единица измерения'])  # Заголовок
        for ingredient in ingredients:
            writer.writerow(
                [ingredient['name'], ingredient['amount'], ingredient['measurement_unit']])

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename="shopping_cart.csv"'
        return response

    def generate_pdf_file(self, ingredients):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt="Список покупок", ln=True, align='C')

        for ingredient in ingredients:
            pdf.cell(
                200, 10, txt=f"{ingredient['name']} ({ingredient['measurement_unit']}) — {ingredient['amount']}", ln=True)

        response = HttpResponse(pdf.output(dest='S').encode(
            'latin1'), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="shopping_cart.pdf"'
        return response

    from .serializers import ShortRecipeSerializer

    @action(detail=True, methods=['post', 'delete'], url_path='favorite', permission_classes=[permissions.IsAuthenticated])
    def manage_favorite(self, request, pk=None):
        try:
            recipe = self.get_object()

            if request.method == 'POST':
                if recipe.favorited_by.filter(user=request.user).exists():
                    return Response(
                        {"detail": "Рецепт уже в избранном."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                recipe.favorited_by.create(user=request.user)

                serializer = ShortRecipeSerializer(recipe)

                return Response(serializer.data, status=status.HTTP_201_CREATED)

            elif request.method == 'DELETE':
                if not recipe.favorited_by.filter(user=request.user).exists():
                    return Response(
                        {"detail": "Рецепт не найден в избранном."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                recipe.favorited_by.filter(user=request.user).delete()
                return Response(
                    {"detail": "Рецепт успешно удалён из избранного"},
                    status=status.HTTP_204_NO_CONTENT
                )

        except Recipe.DoesNotExist:
            return Response(
                {"detail": "Рецепт не найден."},
                status=status.HTTP_404_NOT_FOUND
            )


class IngredientSearchViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer

    def get_queryset(self):
        query = self.request.query_params.get('name', '')
        if query:
            return Ingredient.objects.filter(name__icontains=query)
        return Ingredient.objects.all()


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (SearchFilter,)
    search_fields = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)


class FollowViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    serializer_class = sl.FollowSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('following__username',)

    def get_queryset(self):
        return self.request.user.follower.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
