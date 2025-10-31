"""
Currency conversion service for financial calculations.

This service provides currency conversion functionality with Redis caching
for exchange rates. It fetches rates from an external API and caches them
to minimize API calls and improve performance.
"""

import logging
import requests
from decimal import Decimal
from typing import Dict, Optional
from django.core.cache import cache
from django.conf import settings


logger = logging.getLogger(__name__)


# Fallback exchange rates (updated periodically)
# These are used if the external API is unavailable
FALLBACK_RATES = {
    'USD': Decimal('1.08'),  # 1 EUR = 1.08 USD
    'GBP': Decimal('0.86'),  # 1 EUR = 0.86 GBP
    'RON': Decimal('4.97'),  # 1 EUR = 4.97 RON
    'CHF': Decimal('0.94'),  # 1 EUR = 0.94 CHF
    'JPY': Decimal('161.50'),  # 1 EUR = 161.50 JPY
    'EUR': Decimal('1.00'),  # EUR to EUR
}


class CurrencyConverter:
    """
    Currency conversion service with Redis caching.

    Fetches exchange rates from an external API and caches them in Redis
    to improve performance and reduce API calls.
    """

    def __init__(self):
        """Initialize the currency converter with cache settings."""
        # Cache TTL in seconds (1 hour by default)
        self.cache_ttl = getattr(settings, 'EXCHANGE_RATE_CACHE_TTL', 3600)

        # Exchange rate API endpoint
        # Using exchangerate-api.io (free tier: 1,500 requests/month)
        # Alternative: https://api.frankfurter.app/ (no API key needed, ECB data)
        self.api_url = getattr(
            settings,
            'EXCHANGE_RATE_API_URL',
            'https://api.frankfurter.app/latest'
        )

        # API key (if using a service that requires it)
        self.api_key = getattr(settings, 'EXCHANGE_RATE_API_KEY', None)

    def get_cache_key(self, from_currency: str, to_currency: str = 'EUR') -> str:
        """Generate cache key for exchange rate."""
        return f"exchange_rate:{from_currency}:{to_currency}"

    def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str = 'EUR'
    ) -> Decimal:
        """
        Get exchange rate from one currency to another.

        Args:
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (default: 'EUR')

        Returns:
            Decimal: Exchange rate

        Raises:
            ValueError: If currency codes are invalid
        """
        # Normalize currency codes
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # Same currency - rate is 1.0
        if from_currency == to_currency:
            return Decimal('1.00')

        # Try cache first
        cache_key = self.get_cache_key(from_currency, to_currency)
        cached_rate = cache.get(cache_key)

        if cached_rate is not None:
            logger.debug(
                f"Cache hit for {from_currency} -> {to_currency}: {cached_rate}"
            )
            return Decimal(str(cached_rate))

        # Fetch from API
        try:
            rate = self._fetch_rate_from_api(from_currency, to_currency)

            # Cache the rate
            cache.set(cache_key, str(rate), self.cache_ttl)

            logger.info(
                f"Fetched exchange rate from API: "
                f"{from_currency} -> {to_currency} = {rate}"
            )

            return rate

        except Exception as e:
            logger.error(
                f"Error fetching exchange rate for {from_currency} -> {to_currency}: {e}",
                exc_info=True
            )

            # Fall back to hardcoded rates
            return self._get_fallback_rate(from_currency, to_currency)

    def _fetch_rate_from_api(
        self,
        from_currency: str,
        to_currency: str
    ) -> Decimal:
        """
        Fetch exchange rate from external API.

        Uses https://api.frankfurter.app (European Central Bank data)
        which is free and doesn't require an API key.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            Decimal: Exchange rate

        Raises:
            requests.RequestException: If API request fails
            ValueError: If response is invalid
        """
        # Frankfurter API: GET /latest?from=USD&to=EUR
        params = {
            'from': from_currency,
            'to': to_currency,
        }

        response = requests.get(
            self.api_url,
            params=params,
            timeout=5  # 5 second timeout
        )
        response.raise_for_status()

        data = response.json()

        # Extract rate from response
        # Frankfurter API format: {"amount": 1.0, "base": "USD", "date": "2024-01-01", "rates": {"EUR": 0.92}}
        if 'rates' not in data or to_currency not in data['rates']:
            raise ValueError(f"Invalid API response: {data}")

        rate = Decimal(str(data['rates'][to_currency]))
        return rate

    def _get_fallback_rate(
        self,
        from_currency: str,
        to_currency: str
    ) -> Decimal:
        """
        Get fallback exchange rate from hardcoded values.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            Decimal: Fallback exchange rate

        Raises:
            ValueError: If currency is not in fallback rates
        """
        logger.warning(
            f"Using fallback rate for {from_currency} -> {to_currency}"
        )

        if to_currency == 'EUR':
            # Convert from source currency to EUR
            if from_currency not in FALLBACK_RATES:
                raise ValueError(
                    f"No fallback rate available for {from_currency}"
                )

            # Rates in FALLBACK_RATES are EUR -> other currency
            # So we need to inverse for other currency -> EUR
            return Decimal('1.00') / FALLBACK_RATES[from_currency]

        elif from_currency == 'EUR':
            # Convert from EUR to target currency
            if to_currency not in FALLBACK_RATES:
                raise ValueError(
                    f"No fallback rate available for {to_currency}"
                )
            return FALLBACK_RATES[to_currency]

        else:
            # Convert via EUR: source -> EUR -> target
            # This is less accurate but provides a reasonable estimate
            rate_to_eur = Decimal('1.00') / FALLBACK_RATES[from_currency]
            rate_from_eur = FALLBACK_RATES[to_currency]
            return rate_to_eur * rate_from_eur

    def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str = 'EUR'
    ) -> Decimal:
        """
        Convert amount from one currency to another.

        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code (default: 'EUR')

        Returns:
            Decimal: Converted amount
        """
        if amount is None:
            return None

        amount = Decimal(str(amount))

        # Same currency - no conversion needed
        if from_currency.upper() == to_currency.upper():
            return amount

        rate = self.get_exchange_rate(from_currency, to_currency)
        converted = amount * rate

        # Round to 2 decimal places for currency
        return converted.quantize(Decimal('0.01'))

    def convert_to_eur(
        self,
        amount: Decimal,
        from_currency: str
    ) -> Decimal:
        """
        Convenience method to convert any currency to EUR.

        Args:
            amount: Amount to convert
            from_currency: Source currency code

        Returns:
            Decimal: Amount in EUR
        """
        return self.convert(amount, from_currency, 'EUR')

    def get_multiple_rates(
        self,
        from_currency: str,
        to_currencies: list
    ) -> Dict[str, Decimal]:
        """
        Get exchange rates for multiple target currencies at once.

        Args:
            from_currency: Source currency code
            to_currencies: List of target currency codes

        Returns:
            Dict mapping currency codes to exchange rates
        """
        rates = {}
        for to_currency in to_currencies:
            try:
                rates[to_currency] = self.get_exchange_rate(
                    from_currency,
                    to_currency
                )
            except Exception as e:
                logger.error(
                    f"Failed to get rate for {from_currency} -> {to_currency}: {e}"
                )
                rates[to_currency] = None

        return rates

    def refresh_cache(self, from_currency: str, to_currency: str = 'EUR') -> None:
        """
        Force refresh of cached exchange rate.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
        """
        cache_key = self.get_cache_key(from_currency, to_currency)
        cache.delete(cache_key)

        # Fetch new rate
        self.get_exchange_rate(from_currency, to_currency)

        logger.info(f"Refreshed cache for {from_currency} -> {to_currency}")


# Singleton instance for use throughout the application
currency_converter = CurrencyConverter()


def convert_to_eur(amount: Optional[Decimal], currency: str) -> Optional[Decimal]:
    """
    Convenience function to convert any amount to EUR.

    This is the primary function that should be used in views and serializers.

    Args:
        amount: Amount to convert (can be None)
        currency: Source currency code

    Returns:
        Converted amount in EUR, or None if amount is None

    Example:
        >>> from campaigns.services import convert_to_eur
        >>> value_eur = convert_to_eur(campaign.value, campaign.currency)
    """
    if amount is None:
        return None

    return currency_converter.convert_to_eur(amount, currency)
