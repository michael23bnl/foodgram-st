from django.urls import path
import api.views as vs


urlpatterns = [
    path('<str:short_code>/', vs.RecipeViewSet.as_view(
        {'get': 'redirect_to_recipe'}), name='redirect-to-recipe'),
]
