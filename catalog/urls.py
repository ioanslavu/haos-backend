from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers
from .views import (
    WorkViewSet, RecordingViewSet, ReleaseViewSet,
    TrackViewSet, AssetViewSet,
    SongViewSet, SongChecklistViewSet, SongAssetViewSet,
    SongNoteViewSet, SongAlertViewSet
)
from .aggregate_views import song_hub, track_preview

# Main router
router = DefaultRouter()
router.register(r'works', WorkViewSet)
router.register(r'recordings', RecordingViewSet)
router.register(r'releases', ReleaseViewSet)
router.register(r'tracks', TrackViewSet)
router.register(r'assets', AssetViewSet)

# Song Workflow router
router.register(r'songs', SongViewSet, basename='song')
router.register(r'alerts', SongAlertViewSet, basename='alert')

# Nested routers for Song
songs_router = nested_routers.NestedDefaultRouter(router, r'songs', lookup='song')
songs_router.register(r'checklist', SongChecklistViewSet, basename='song-checklist')
songs_router.register(r'assets', SongAssetViewSet, basename='song-asset')
songs_router.register(r'notes', SongNoteViewSet, basename='song-note')

app_name = 'catalog'
urlpatterns = [
    path('', include(router.urls)),
    path('', include(songs_router.urls)),

    # Aggregate endpoints
    path('song-hub/<int:work_id>/', song_hub, name='song-hub'),
    path('track-preview/<int:recording_id>/', track_preview, name='track-preview'),
]