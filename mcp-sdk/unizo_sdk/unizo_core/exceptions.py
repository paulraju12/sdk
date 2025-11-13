class UnizoError(Exception):
    """Base exception for Unizo SDK errors."""
    pass

class AuthenticationError(UnizoError):
    """Raised when authentication fails."""
    pass

class ToolExecutionError(UnizoError):
    """Raised when a tool execution fails."""
    pass