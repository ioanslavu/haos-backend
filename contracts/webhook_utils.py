"""
Utility functions for secure webhook processing.
Includes idempotency, verification, and validation helpers.
"""
import hashlib
import logging
import time
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)


def get_client_ip(request) -> Optional[str]:
    """
    Extract client IP address from request, checking proxy headers.

    Args:
        request: Django/DRF request object

    Returns:
        IP address as string or None
    """
    # Check X-Forwarded-For header (for requests behind proxy/load balancer)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP (client IP, not proxy IP)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        # Direct connection
        ip = request.META.get('REMOTE_ADDR')

    return ip


def calculate_event_hash(
    signature_request_id: str,
    event_type: str,
    signer_email: Optional[str] = None,
    timestamp: Optional[datetime] = None
) -> str:
    """
    Calculate unique hash for event idempotency check.
    Hash is based on signature request ID, event type, signer email, and timestamp (rounded to minute).

    Args:
        signature_request_id: Dropbox Sign signature request ID
        event_type: Type of event (signature_request_signed, etc.)
        signer_email: Email of signer (if applicable)
        timestamp: Event timestamp (defaults to now)

    Returns:
        SHA256 hash as hexadecimal string
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    # Round timestamp to minute to allow for minor timing differences
    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M')

    # Build unique string
    unique_string = f"{signature_request_id}:{event_type}:{signer_email or ''}:{timestamp_str}"

    # Calculate SHA256 hash
    event_hash = hashlib.sha256(unique_string.encode()).hexdigest()

    return event_hash


def validate_status_transition(current_status: str, new_status: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a contract status transition is allowed.
    Prevents invalid state changes (e.g., signed → draft).

    Args:
        current_status: Current contract status
        new_status: Proposed new status

    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])
    """
    # Define valid status transitions
    VALID_TRANSITIONS = {
        'processing': ['draft', 'failed'],
        'draft': ['pending_signature', 'failed'],
        'pending_signature': ['signed', 'cancelled'],
        'failed': ['processing'],  # Allow retry
        # Immutable states (terminal states):
        'signed': [],  # Once signed, cannot change
        'cancelled': [],  # Once cancelled, cannot change
    }

    # Get allowed transitions for current status
    allowed_transitions = VALID_TRANSITIONS.get(current_status, [])

    # Check if transition is allowed
    if new_status not in allowed_transitions:
        error_msg = f"Invalid status transition: cannot change from '{current_status}' to '{new_status}'"
        logger.warning(error_msg)
        return (False, error_msg)

    return (True, None)


def verify_event_with_dropbox_api(
    signature_request_id: str,
    event_type: str,
    signer_email: Optional[str] = None
) -> Tuple[bool, Optional[Any], Optional[str]]:
    """
    Verify webhook event by calling Dropbox Sign API server-to-server.
    This is the authoritative source of truth - never trust webhook payload alone.

    Implements retry logic with exponential backoff to handle API delays/caching.

    Args:
        signature_request_id: Dropbox Sign signature request ID
        event_type: Type of event to verify
        signer_email: Email of signer (for signature_request_signed events)

    Returns:
        Tuple of (is_valid: bool, api_response: Any, error: Optional[str])
    """
    from .services.dropbox_sign import DropboxSignService

    retry_delays = [5, 10, 15]  # Retry after 5s, 10s, 15s (total ~30s max)

    for attempt in range(1, len(retry_delays) + 2):  # +2 for initial attempt + final attempt
        try:
            logger.info(f"Verifying event with Dropbox Sign API (attempt {attempt}/{len(retry_delays) + 1})")

            # Fetch fresh data from Dropbox Sign API using OUR credentials
            dropbox_service = DropboxSignService()
            signature_request = dropbox_service.get_signature_request(signature_request_id)

            # Verify based on event type
            if event_type == 'signature_request_all_signed':
                # Check if ALL signatures are complete
                if signature_request.is_complete:
                    logger.info(f"API verification SUCCESS: All signatures complete")
                    return (True, signature_request, None)
                else:
                    error_msg = f"API reports not all signatures complete (is_complete={signature_request.is_complete})"
                    logger.warning(error_msg)
                    # Don't retry for this - if API says not complete, trust it
                    return (False, signature_request, error_msg)

            elif event_type == 'signature_request_signed':
                # Verify SPECIFIC signer has signed
                if signer_email:
                    for sig in signature_request.signatures:
                        if hasattr(sig, 'signer_email_address') and sig.signer_email_address == signer_email:
                            if hasattr(sig, 'status_code') and sig.status_code == 'signed':
                                logger.info(f"API verification SUCCESS: Signer {signer_email} has signed")
                                return (True, signature_request, None)
                            else:
                                sig_status = getattr(sig, 'status_code', 'unknown')
                                error_msg = f"API reports signer {signer_email} status: {sig_status} (not 'signed')"
                                logger.warning(error_msg)
                                return (False, signature_request, error_msg)

                    error_msg = f"Signer {signer_email} not found in API response"
                    logger.warning(error_msg)
                    return (False, signature_request, error_msg)
                else:
                    error_msg = "signer_email required for signature_request_signed verification"
                    logger.error(error_msg)
                    return (False, signature_request, error_msg)

            elif event_type == 'signature_request_declined':
                # Check if any signature is declined
                has_declined = any(
                    hasattr(sig, 'status_code') and sig.status_code == 'declined'
                    for sig in signature_request.signatures
                )
                has_error = signature_request.has_error if hasattr(signature_request, 'has_error') else False

                if has_declined or has_error:
                    logger.info(f"API verification SUCCESS: Request declined or has error")
                    return (True, signature_request, None)
                else:
                    error_msg = "API reports request not declined"
                    logger.warning(error_msg)
                    return (False, signature_request, error_msg)

            elif event_type == 'signature_request_viewed':
                # 'Viewed' events are transient - Dropbox might not persist them long-term
                # Trust the webhook for this event type
                logger.info(f"API verification SUCCESS: Viewing events are trusted")
                return (True, signature_request, None)

            elif event_type == 'signature_request_sent':
                # Sent event - just verify the request exists
                logger.info(f"API verification SUCCESS: Request exists")
                return (True, signature_request, None)

            else:
                # Unknown event type - log and allow (conservative approach)
                logger.warning(f"Unknown event type '{event_type}' - allowing")
                return (True, signature_request, None)

        except Exception as e:
            error_msg = f"API verification attempt {attempt} failed: {str(e)}"
            logger.error(error_msg)

            # Retry with backoff if we haven't exhausted retries
            if attempt <= len(retry_delays):
                delay = retry_delays[attempt - 1]
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                # All retries exhausted
                final_error = f"API verification failed after {attempt} attempts: {str(e)}"
                logger.error(final_error)
                return (False, None, final_error)

    # Should never reach here, but just in case
    return (False, None, "Retry logic error")
