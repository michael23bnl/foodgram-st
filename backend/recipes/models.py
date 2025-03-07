from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
User = get_user_model()

TEXT_LEN = 50


class Ingredient(models.Model):
    name = models.CharField(
        verbose_name='Название',
        max_length=200,
        unique=True,
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=50,
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        'Recipe',
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
        related_name='ingredients_amounts',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Ингредиент',
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
    )
    amount = models.IntegerField(
        verbose_name='Количество',
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient',
            )
        ]

    def __str__(self):
        return f'{self.ingredient.name} - {self.amount} {self.ingredient.measurement_unit}'


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='recipes',
    )
    name = models.CharField(
        verbose_name='Название',
        max_length=200,
    )
    image = models.ImageField(
        verbose_name='Картинка',
        upload_to='recipes/',
    )
    text = models.TextField(
        verbose_name='Описание',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through=RecipeIngredient,
        verbose_name='Ингредиенты',
        related_name='recipes',
    )
    cooking_time = models.IntegerField(
        verbose_name='Время приготовления (минуты)',
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        default=timezone.now,
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-pub_date']

    def __str__(self):
        return self.name


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        related_name='favorites',
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
        related_name='favorited_by',
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные рецепты'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite',
            )
        ]

    def __str__(self):
        return f'{self.user} добавил в избранное {self.recipe}'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        related_name='shopping_cart',
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
        related_name='in_shopping_cart',
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart',
            )
        ]

    def __str__(self):
        return f'{self.user} добавил в список покупок {self.recipe}'
