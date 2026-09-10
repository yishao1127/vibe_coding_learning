from english_learning_partner.services.speech_service import SpeechService


class VoiceToken:
    def __init__(self, language: str) -> None:
        self.language = language

    def GetAttribute(self, name: str) -> str:
        assert name == "Language"
        return self.language


def test_prefers_requested_british_voice() -> None:
    british = VoiceToken("809")
    american = VoiceToken("409")

    selected, accent = SpeechService._select_voice([american, british], "british")

    assert selected is british
    assert accent == "british"


def test_falls_back_to_other_english_accent() -> None:
    american = VoiceToken("409")

    selected, accent = SpeechService._select_voice([american], "british")

    assert selected is american
    assert accent == "american"


def test_falls_back_to_other_english_voice() -> None:
    australian = VoiceToken("c09")

    selected, accent = SpeechService._select_voice([australian], "american")

    assert selected is australian
    assert accent == "english"


def test_rejects_non_english_voices() -> None:
    chinese = VoiceToken("804")

    selected, accent = SpeechService._select_voice([chinese], "american")

    assert selected is None
    assert accent == "english"
