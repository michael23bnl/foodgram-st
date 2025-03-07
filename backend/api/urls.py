from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers
import api.views as vs

userRouter = routers.DefaultRouter()
recipeRouter = routers.DefaultRouter()

recipeRouter.register(
    'follow',
    vs.FollowViewSet,
    basename='follow',
)

userRouter.register(
    r'users',
    vs.UserViewSet,
    basename='users'
)

userRouter.register(
    r'auth/token',
    vs.LogoutViewSet,
    basename='logout'
)

recipeRouter.register(
    r'recipes',
    vs.RecipeViewSet,
    basename='recipes'
)

recipeRouter.register(
    r'ingredients',
    vs.IngredientViewSet,
    basename='ingredients'
)

urlpatterns = [
    path('', include(userRouter.urls)),
    path('', include('djoser.urls.jwt')),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(recipeRouter.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
