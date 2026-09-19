class ProviderError(Exception):
    """A channel provider rejected or failed a request. Message is admin-readable."""


class NotConfigured(ProviderError):
    """Required .env keys for a provider are missing."""
