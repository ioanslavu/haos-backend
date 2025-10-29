from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WorkViewSet, RecordingViewSet, ReleaseViewSet,
    TrackViewSet, AssetViewSet
)
from .aggregate_views import song_hub, track_preview

router = DefaultRouter()
router.register(r'works', WorkViewSet)
router.register(r'recordings', RecordingViewSet)
router.register(r'releases', ReleaseViewSet)
router.register(r'tracks', TrackViewSet)
router.register(r'assets', AssetViewSet)

app_name = 'catalog'
urlpatterns = [
    path('', include(router.urls)),

    # Aggregate endpoints
    path('song-hub/<int:work_id>/', song_hub, name='song-hub'),
    path('track-preview/<int:recording_id>/', track_preview, name='track-preview'),
]