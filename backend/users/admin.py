from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Follow
User = get_user_model()


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    search_fields = ('username', 'email')


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('user', 'following')
    list_filter = ('user', 'following')
    search_fields = ('user__username', 'following__username')
    raw_id_fields = ('user', 'following')

    def __str__(self):
        return f'{self.user} подписчик автора - {self.following}'
