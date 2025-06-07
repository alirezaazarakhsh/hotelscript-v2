from django.contrib import admin
from .models import (
    StoryCategory,
    Story,
    ArticleCategory,
    ArticleSubCategory,
    ArticleTag,
    Article,
    Comment,
)
from .forms import (
    StoryCategoryAdminForm,
    StoryAdminForm,
    ArticleAdminForm,
)
# Register your models here.
@admin.register(StoryCategory)
class StoryCategoryAdmin(admin.ModelAdmin):
    form = StoryCategoryAdminForm
    list_display = (
        'id',
        'title',
        'order',
    )
    search_fields = (
        'title',
    )

@admin.register(Story)
class StoryCategoryAdmin(admin.ModelAdmin):
    form = StoryAdminForm
    list_display = (
        'id',
        'category',
    )
    list_filter = (
        'category',
    )
    ordering = ('-created',)

@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'slug',
        'description',
    )
    search_fields = (
        'title',
        'slug',
        'description',
    )

@admin.register(ArticleSubCategory)
class ArticleSubCategoryAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'slug',
        'description',
        'parent',
    )
    search_fields = (
        'title',
        'slug',
        'description',
    )

@admin.register(ArticleTag)
class ArticleTagAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
    )
    search_fields = (
        'title',
    )

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    form = ArticleAdminForm
    list_display = (
        'id',
        'title',
        'slug',
        'summary',
        'author',
        'category',
        'view_count',
        'status',
        'is_popular',
        'is_engaging',
        'created',
        'published_date',
    )
    search_fields = (
        'title',
        'slug',
        'body',
    )
    list_filter = (
        'status',
        'is_popular',
        'is_engaging',
    )

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        'author_name',
        'author_email',
        'text',
        'article',
        'is_approved',
        'reply_to',
        'created',
    )
    search_fields = (
        'author_name',
        'author_email',
        'text',
    )
    list_filter = (
        'author_name',
        'author_email',
        'article',
        'is_approved',
    )
