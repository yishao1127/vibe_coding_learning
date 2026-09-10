"""Application-specific errors exposed in friendly form by the UI."""


class LearningPartnerError(Exception):
    """Base error with a message safe to show in the desktop app."""


class LocalModelConnectionError(LearningPartnerError):
    """The configured local model service cannot be reached."""


class LocalModelResponseError(LearningPartnerError):
    """The local model service returned an invalid or unusable response."""


class RecordSaveError(LearningPartnerError):
    """A generated result could not be written to the learning directory."""


class LocalSpeechError(LearningPartnerError):
    """The local Windows speech service cannot pronounce the requested word."""
