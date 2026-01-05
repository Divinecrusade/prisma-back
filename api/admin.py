from django.contrib import admin
from .models import ResearchProject, ResearchImage, Annotation


@admin.register(ResearchProject)
class ResearchProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'is_hidden']
    list_filter = ['is_hidden', 'created_at']
    search_fields = ['name', 'description']


@admin.register(ResearchImage)
class ResearchImageAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'added_at', 'is_hidden', 'review_count']
    list_filter = ['is_hidden', 'project', 'added_at']
    search_fields = ['name', 'question']


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ['id', 'image', 'session_id', 'created_at']
    list_filter = ['image', 'created_at']
    search_fields = ['text', 'session_id']
