from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'projects', views.ResearchProjectViewSet)
router.register(r'images', views.ResearchImageViewSet)
router.register(r'annotations', views.AnnotationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('annotations/submit/', views.submit_annotations, name='submit-annotations'),
    path('auth/login/', views.login, name='login'),
    path('report/<uuid:image_id>/', views.get_report_data, name='report-data'),
]
