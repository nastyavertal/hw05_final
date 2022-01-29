from django.contrib import admin

# Из модуля models импортируем модель
from .models import Comment, Follow, Group, Post


class PostAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'text',
        'pub_date',
        'author',
        'group')
    search_fields = ('text',)
    list_filter = ('pub_date',)
    list_editable = ('group',)
    empty_value_display = '-пусто-'


class GroupAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'description',
    )
    search_fields = ('title',)


class CommentAdmin(admin.ModelAdmin):
    list_display = ('text', 'author', 'post')


class FollowAdmin(admin.ModelAdmin):
    list_display = ('author', 'user')


admin.site.register(Post, PostAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Follow, FollowAdmin)
