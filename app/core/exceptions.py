"""Core domain exceptions."""


class UnsupportedEventError(LookupError):
    """Raised when no Handler is registered for an event."""


class PayloadValidationError(ValueError):
    """Raised when a webhook payload lacks required domain data."""


class InvalidSignatureError(PermissionError):
    """Raised when webhook authentication fails."""


class DiscordApiError(RuntimeError):
    """Raised when Discord delivery fails permanently."""


class ChannelNotFoundError(LookupError):
    """Raised when a configured Discord channel cannot be resolved."""


class InvalidConfigurationError(RuntimeError):
    """Raised when required project or channel configuration is missing."""
