from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'projects', views.ResearchProjectViewSet)
router.register(r'images', views.ResearchImageViewSet)
router.register(r'annotations', views.AnnotationViewSet)

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/me/', views.get_current_session, name='current-session'),
    
    # Annotation submission (public)
    path('annotations/submit/', views.submit_annotations, name='submit-annotations'),
    
    # Report data (admin only)
    path('report/<uuid:image_id>/', views.get_report_data, name='report-data'),
    
    # Router URLs
    path('', include(router.urls)),
]
