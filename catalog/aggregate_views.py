from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Q, Count, Prefetch
from catalog.models import Work, Recording, Release, Track
from identity.models import Entity, Identifier
from rights.models import Credit, Split
from distribution.models import Publication
from contracts.models import Contract, ContractScope


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def song_hub(request, work_id):
    """
    Song Hub aggregate endpoint - comprehensive view of a work.
    Returns all related data for a work including recordings, releases,
    credits, splits, publications, and contracts.
    """
    try:
        work = Work.objects.get(id=work_id)
    except Work.DoesNotExist:
        return Response(
            {'error': 'Work not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Get ISWC
    iswc = work.get_iswc()

    # Get all recordings of this work
    recordings = Recording.objects.filter(work=work).prefetch_related(
        Prefetch('tracks', queryset=Track.objects.select_related('release'))
    )

    recordings_data = []
    for recording in recordings:
        # Get ISRC for recording
        isrc = recording.get_isrc()

        # Get releases this recording appears on
        releases = Release.objects.filter(
            tracks__recording=recording
        ).distinct()

        releases_data = []
        for release in releases:
            # Get UPC for release
            upc = release.get_upc()

            # Get track info
            track = release.tracks.filter(recording=recording).first()

            releases_data.append({
                'id': release.id,
                'title': release.title,
                'upc': upc,
                'type': release.type,
                'status': release.status,
                'release_date': release.release_date,
                'label_name': release.label_name,
                'catalog_number': release.catalog_number,
                'track_number': track.track_number if track else None,
                'disc_number': track.disc_number if track else None,
                'track_version': track.version if track else None
            })

        # Get recording credits
        recording_credits = Credit.objects.filter(
            scope='recording',
            object_id=recording.id
        ).select_related('entity')

        recording_credits_data = [{
            'id': credit.id,
            'entity_id': credit.entity.id,
            'entity_name': credit.entity.display_name,
            'role': credit.role,
            'role_display': credit.get_role_display(),
            'credited_as': credit.credited_as
        } for credit in recording_credits]

        # Get recording splits
        recording_splits = Split.objects.filter(
            scope='recording',
            object_id=recording.id
        ).select_related('entity')

        recording_splits_data = [{
            'id': split.id,
            'entity_id': split.entity.id,
            'entity_name': split.entity.display_name,
            'right_type': split.right_type,
            'share': float(split.share),
            'is_locked': split.is_locked,
            'source': split.source
        } for split in recording_splits]

        # Get recording publications
        recording_publications = Publication.objects.filter(
            object_type='recording',
            object_id=recording.id
        )

        recording_publications_data = [{
            'id': pub.id,
            'platform': pub.platform,
            'platform_display': pub.get_platform_display(),
            'territory': pub.territory,
            'status': pub.status,
            'url': pub.url,
            'is_monetized': pub.is_monetized,
            'published_at': pub.published_at
        } for pub in recording_publications]

        recordings_data.append({
            'id': recording.id,
            'title': recording.title,
            'isrc': isrc,
            'type': recording.type,
            'status': recording.status,
            'duration_seconds': recording.duration_seconds,
            'formatted_duration': recording.formatted_duration,
            'recording_date': recording.recording_date,
            'studio': recording.studio,
            'version': recording.version,
            'has_complete_master_splits': recording.has_complete_master_splits,
            'releases': releases_data,
            'credits': recording_credits_data,
            'splits': recording_splits_data,
            'publications': recording_publications_data
        })

    # Get work credits
    work_credits = Credit.objects.filter(
        scope='work',
        object_id=work.id
    ).select_related('entity')

    work_credits_data = [{
        'id': credit.id,
        'entity_id': credit.entity.id,
        'entity_name': credit.entity.display_name,
        'role': credit.role,
        'role_display': credit.get_role_display(),
        'credited_as': credit.credited_as,
        'share_kind': credit.share_kind,
        'share_value': credit.share_value
    } for credit in work_credits]

    # Get work splits
    work_splits = Split.objects.filter(
        scope='work',
        object_id=work.id
    ).select_related('entity')

    work_splits_data = []
    for split in work_splits:
        work_splits_data.append({
            'id': split.id,
            'entity_id': split.entity.id,
            'entity_name': split.entity.display_name,
            'right_type': split.right_type,
            'right_type_display': split.get_right_type_display(),
            'share': float(split.share),
            'is_locked': split.is_locked,
            'source': split.source
        })

    # Get contracts covering this work
    contract_scopes = ContractScope.objects.filter(
        Q(work=work) |
        Q(all_in_term=True)  # Catalog-wide contracts
    ).select_related('contract', 'contract__counterparty_entity')

    contracts_data = []
    for scope in contract_scopes:
        contract = scope.contract

        # Determine scope type based on which foreign key is set
        if scope.work:
            scope_type = 'work'
        elif scope.recording:
            scope_type = 'recording'
        elif scope.release:
            scope_type = 'release'
        elif scope.all_in_term:
            scope_type = 'catalog'
        else:
            scope_type = 'unknown'

        contracts_data.append({
            'id': contract.id,
            'contract_number': contract.contract_number,
            'title': contract.title,
            'entity_id': contract.counterparty_entity.id if contract.counterparty_entity else None,
            'entity_name': contract.counterparty_entity.display_name if contract.counterparty_entity else None,
            'status': contract.status,
            'effective_date': contract.term_start,  # Changed from effective_date
            'scope_type': scope_type,
            'include_derivatives': scope.include_derivatives,
            'all_in_term': scope.all_in_term
        })

    # Compile final response
    response_data = {
        'work': {
            'id': work.id,
            'title': work.title,
            'alternate_titles': work.alternate_titles,
            'iswc': iswc,
            'language': work.language,
            'genre': work.genre,
            'sub_genre': work.sub_genre,
            'year_composed': work.year_composed,
            'lyrics': work.lyrics,
            'notes': work.notes,
            'has_complete_publishing_splits': work.has_complete_publishing_splits,
            'created_at': work.created_at,
            'updated_at': work.updated_at
        },
        'credits': work_credits_data,
        'splits': {
            'writer': [s for s in work_splits_data if s['right_type'] == 'writer'],
            'publisher': [s for s in work_splits_data if s['right_type'] == 'publisher']
        },
        'recordings': recordings_data,
        'contracts': contracts_data,
        'statistics': {
            'total_recordings': len(recordings_data),
            'total_releases': sum(len(r['releases']) for r in recordings_data),
            'total_publications': sum(len(r['publications']) for r in recordings_data),
            'has_complete_writer_splits': Split.validate_splits_total('work', work.id, 'writer')['is_complete'],
            'has_complete_publisher_splits': Split.validate_splits_total('work', work.id, 'publisher')['is_complete'],
            'platforms_covered': list(set(
                pub['platform'] for r in recordings_data
                for pub in r['publications']
            ))
        }
    }

    return Response(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def track_preview(request, recording_id):
    """
    Track Preview aggregate endpoint - comprehensive view of a recording.
    Returns all related data for a recording including work, releases,
    credits, splits, publications, and assets.
    """
    try:
        recording = Recording.objects.select_related('work').get(id=recording_id)
    except Recording.DoesNotExist:
        return Response(
            {'error': 'Recording not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Get ISRC
    isrc = recording.get_isrc()

    # Get work data if exists
    work_data = None
    if recording.work:
        work = recording.work
        iswc = work.get_iswc()

        # Get work splits
        work_writer_splits = Split.objects.filter(
            scope='work',
            object_id=work.id,
            right_type='writer'
        ).select_related('entity')

        work_publisher_splits = Split.objects.filter(
            scope='work',
            object_id=work.id,
            right_type='publisher'
        ).select_related('entity')

        work_data = {
            'id': work.id,
            'title': work.title,
            'iswc': iswc,
            'language': work.language,
            'genre': work.genre,
            'year_composed': work.year_composed,
            'writer_splits': [{
                'entity_id': split.entity.id,
                'entity_name': split.entity.display_name,
                'share': float(split.share)
            } for split in work_writer_splits],
            'publisher_splits': [{
                'entity_id': split.entity.id,
                'entity_name': split.entity.display_name,
                'share': float(split.share)
            } for split in work_publisher_splits]
        }

    # Get releases
    releases = Release.objects.filter(
        tracks__recording=recording
    ).distinct().prefetch_related(
        Prefetch('tracks', queryset=Track.objects.filter(recording=recording))
    )

    releases_data = []
    for release in releases:
        # Get UPC
        upc = release.get_upc()

        # Get track info for this recording
        track = release.tracks.filter(recording=recording).first()

        # Get other tracks on the release
        other_tracks = release.tracks.exclude(recording=recording).select_related('recording')

        releases_data.append({
            'id': release.id,
            'title': release.title,
            'upc': upc,
            'type': release.type,
            'status': release.status,
            'release_date': release.release_date,
            'label_name': release.label_name,
            'catalog_number': release.catalog_number,
            'artwork_url': release.artwork_url,
            'track_info': {
                'track_number': track.track_number if track else None,
                'disc_number': track.disc_number if track else None,
                'version': track.version if track else None,
                'is_bonus': track.is_bonus if track else False,
                'is_hidden': track.is_hidden if track else False
            },
            'track_count': release.track_count,
            'other_tracks': [{
                'track_number': t.track_number,
                'disc_number': t.disc_number,
                'recording_id': t.recording.id,
                'recording_title': t.recording.title,
                'duration': t.recording.duration_seconds
            } for t in other_tracks[:5]]  # Limit to 5 for performance
        })

    # Get recording credits
    credits = Credit.objects.filter(
        scope='recording',
        object_id=recording.id
    ).select_related('entity')

    credits_data = [{
        'id': credit.id,
        'entity_id': credit.entity.id,
        'entity_name': credit.entity.display_name,
        'role': credit.role,
        'role_display': credit.get_role_display(),
        'credited_as': credit.credited_as
    } for credit in credits]

    # Get recording splits
    splits = Split.objects.filter(
        scope='recording',
        object_id=recording.id,
        right_type='master'
    ).select_related('entity')

    splits_data = [{
        'id': split.id,
        'entity_id': split.entity.id,
        'entity_name': split.entity.display_name,
        'share': float(split.share),
        'is_locked': split.is_locked,
        'source': split.source
    } for split in splits]

    # Get publications
    publications = Publication.objects.filter(
        object_type='recording',
        object_id=recording.id
    )

    publications_data = [{
        'id': pub.id,
        'platform': pub.platform,
        'platform_display': pub.get_platform_display(),
        'platform_icon': pub.platform_icon,
        'territory': pub.territory,
        'territory_display': pub.get_territory_display(),
        'status': pub.status,
        'url': pub.url,
        'external_id': pub.external_id,
        'is_monetized': pub.is_monetized,
        'published_at': pub.published_at,
        'metrics': pub.metrics
    } for pub in publications]

    # Get assets
    assets = recording.assets.all()

    assets_data = [{
        'id': asset.id,
        'kind': asset.kind,
        'file_name': asset.file_name,
        'file_size': asset.file_size,
        'formatted_file_size': asset.formatted_file_size,
        'mime_type': asset.mime_type,
        'is_master': asset.is_master,
        'is_public': asset.is_public,
        'sample_rate': asset.sample_rate,
        'bit_depth': asset.bit_depth,
        'bitrate': asset.bitrate
    } for asset in assets]

    # Get contracts covering this recording
    # Build query for contracts covering this recording
    q_filter = Q(recording=recording)
    if recording.work:
        q_filter |= Q(work=recording.work)
    q_filter |= Q(all_in_term=True)  # Catalog-wide contracts

    contract_scopes = ContractScope.objects.filter(q_filter).select_related(
        'contract', 'contract__counterparty_entity'
    )

    contracts_data = []
    for scope in contract_scopes:
        contract = scope.contract

        # Determine scope type based on which foreign key is set
        if scope.recording:
            scope_type = 'recording'
        elif scope.work:
            scope_type = 'work'
        elif scope.release:
            scope_type = 'release'
        elif scope.all_in_term:
            scope_type = 'catalog'
        else:
            scope_type = 'unknown'

        contracts_data.append({
            'id': contract.id,
            'contract_number': contract.contract_number,
            'title': contract.title,
            'entity_id': contract.counterparty_entity.id if contract.counterparty_entity else None,
            'entity_name': contract.counterparty_entity.display_name if contract.counterparty_entity else None,
            'status': contract.status,
            'scope_type': scope_type,
            'include_derivatives': scope.include_derivatives,
            'all_in_term': scope.all_in_term
        })

    # Compile response
    response_data = {
        'recording': {
            'id': recording.id,
            'title': recording.title,
            'isrc': isrc,
            'type': recording.type,
            'status': recording.status,
            'duration_seconds': recording.duration_seconds,
            'formatted_duration': recording.formatted_duration,
            'bpm': recording.bpm,
            'key': recording.key,
            'recording_date': recording.recording_date,
            'studio': recording.studio,
            'version': recording.version,
            'notes': recording.notes,
            'has_complete_master_splits': recording.has_complete_master_splits,
            'created_at': recording.created_at,
            'updated_at': recording.updated_at
        },
        'work': work_data,
        'releases': releases_data,
        'credits': credits_data,
        'master_splits': splits_data,
        'publications': publications_data,
        'assets': assets_data,
        'contracts': contracts_data,
        'statistics': {
            'total_releases': len(releases_data),
            'total_publications': len(publications_data),
            'total_assets': len(assets_data),
            'has_master_asset': any(a['is_master'] for a in assets_data),
            'platforms_covered': list(set(pub['platform'] for pub in publications_data)),
            'territories_covered': list(set(pub['territory'] for pub in publications_data)),
            'monetized_platforms': [
                pub['platform'] for pub in publications_data
                if pub['is_monetized']
            ]
        }
    }

    return Response(response_data)