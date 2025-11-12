from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from .models import Note, Tag
from .serializers import (
    NoteListSerializer,
    NoteDetailSerializer,
    NoteCreateSerializer,
    TagSerializer,
    TagListSerializer
)
from rest_framework import filters


class NoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Note CRUD operations.
    All notes are automatically scoped to the logged-in user.
    """
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_pinned', 'is_archived', 'tags']
    search_fields = ['title', 'content_text']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-is_pinned', '-updated_at']
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    pagination_class = None  # Disable pagination for notes

    def get_queryset(self):
        """
        Automatically scope notes to the current user.
        Only return notes that belong to the logged-in user.
        """
        queryset = Note.objects.filter(user=self.request.user)
        queryset = queryset.prefetch_related('tags')

        # Handle search query parameter
        search_query = self.request.query_params.get('search', None)
        if search_query:
            # Use PostgreSQL full-text search
            search_vector = SearchVector('title', weight='A') + SearchVector('content_text', weight='B')
            search_query_obj = SearchQuery(search_query)
            queryset = queryset.annotate(
                rank=SearchRank(search_vector, search_query_obj)
            ).filter(rank__gte=0.01).order_by('-is_pinned', '-rank')

        # Handle tag filtering (comma-separated tag IDs)
        tag_ids = self.request.query_params.get('tags', None)
        if tag_ids:
            tag_id_list = [int(id.strip()) for id in tag_ids.split(',') if id.strip().isdigit()]
            if tag_id_list:
                queryset = queryset.filter(tags__id__in=tag_id_list).distinct()

        # Handle archived filter (only for list view, not for detail/actions)
        if self.action == 'list':
            is_archived = self.request.query_params.get('is_archived', None)
            if is_archived is not None:
                is_archived_bool = is_archived.lower() in ['true', '1', 'yes']
                queryset = queryset.filter(is_archived=is_archived_bool)
            else:
                # By default, hide archived notes in list view
                queryset = queryset.filter(is_archived=False)

        # Handle pinned filter
        is_pinned = self.request.query_params.get('is_pinned', None)
        if is_pinned is not None:
            is_pinned_bool = is_pinned.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_pinned=is_pinned_bool)

        return queryset

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return NoteListSerializer
        elif self.action == 'create':
            return NoteCreateSerializer
        return NoteDetailSerializer

    def perform_create(self, serializer):
        """Automatically set the user when creating a note"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """Toggle pin status of a note"""
        note = self.get_object()
        note.is_pinned = not note.is_pinned
        note.save()
        serializer = self.get_serializer(note)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Toggle archive status of a note"""
        note = self.get_object()
        note.is_archived = not note.is_archived
        note.save()
        serializer = self.get_serializer(note)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get statistics about user's notes

        Returns:
        - total_notes: Total number of notes (excluding archived)
        - total_archived: Total archived notes
        - total_pinned: Total pinned notes
        - notes_this_week: Notes created this week
        - by_tag: Count of notes by tag
        - recent_notes: 5 most recently updated notes
        """
        from django.utils import timezone
        from datetime import timedelta

        queryset = Note.objects.filter(user=request.user)
        week_ago = timezone.now() - timedelta(days=7)

        stats = {
            'total_notes': queryset.filter(is_archived=False).count(),
            'total_archived': queryset.filter(is_archived=True).count(),
            'total_pinned': queryset.filter(is_pinned=True).count(),
            'notes_this_week': queryset.filter(created_at__gte=week_ago).count(),
            'by_tag': []
        }

        # Count by tag
        tags_with_counts = Tag.objects.filter(user=request.user).annotate(
            count_notes=Count('notes', filter=Q(notes__is_archived=False))
        ).order_by('-count_notes')[:10]

        stats['by_tag'] = [
            {
                'tag_id': tag.id,
                'tag_name': tag.name,
                'tag_color': tag.color,
                'count': tag.count_notes
            }
            for tag in tags_with_counts
        ]

        # Recent notes
        recent = queryset.filter(is_archived=False).order_by('-updated_at')[:5]
        stats['recent_notes'] = NoteListSerializer(recent, many=True, context={'request': request}).data

        return Response(stats)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Advanced search endpoint with full-text search support

        Query params:
        - q: Search query
        - tags: Comma-separated tag IDs
        - is_archived: Filter by archived status
        """
        search_query = request.query_params.get('q', '').strip()

        if not search_query:
            return Response({'results': []})

        queryset = self.get_queryset()

        # Use PostgreSQL full-text search
        search_vector = SearchVector('title', weight='A') + SearchVector('content_text', weight='B')
        search_query_obj = SearchQuery(search_query)

        results = queryset.annotate(
            rank=SearchRank(search_vector, search_query_obj)
        ).filter(rank__gte=0.01).order_by('-rank')[:20]

        serializer = NoteListSerializer(results, many=True, context={'request': request})
        return Response({'results': serializer.data, 'query': search_query})


class TagViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Tag CRUD operations.
    All tags are automatically scoped to the logged-in user.
    """
    permission_classes = [IsAuthenticated]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    pagination_class = None  # Disable pagination for tags

    def get_queryset(self):
        """
        Automatically scope tags to the current user.
        Only return tags that belong to the logged-in user.
        """
        queryset = Tag.objects.filter(user=self.request.user)

        # Annotate with note count
        queryset = queryset.annotate(
            notes_count=Count('notes', filter=Q(notes__is_archived=False))
        )

        # Handle search
        search_query = self.request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)

        return queryset

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return TagListSerializer
        return TagSerializer

    def perform_create(self, serializer):
        """Automatically set the user when creating a tag"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def notes(self, request, pk=None):
        """Get all notes for a specific tag"""
        tag = self.get_object()
        notes = tag.notes.filter(is_archived=False).order_by('-updated_at')
        serializer = NoteListSerializer(notes, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        """
        Get tag suggestions based on usage frequency

        Returns top 10 most used tags
        """
        tags = self.get_queryset().order_by('-notes_count')[:10]
        serializer = TagListSerializer(tags, many=True)
        return Response(serializer.data)
