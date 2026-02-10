class ParserError(Exception):
    default_message = "Parser error"

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class SiteUnavailableError(ParserError):
    default_message = "Site is unavailable"


class AuthenticationError(ParserError):
    default_message = "Authentication failed"


class InvalidResponseError(ParserError):
    default_message = "Invalid response received"
