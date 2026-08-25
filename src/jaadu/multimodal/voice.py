from __future__ import annotations

from jaadu.google.clients import speech_client, tts_client


def transcribe_audio(audio_bytes: bytes, language_code: str = "hi-IN") -> dict:
    """Speech-to-Text for investigator or radio notes. Not an alert source."""
    client = speech_client()
    if client is None:
        return {"text": "", "skipped": True, "reason": "GOOGLE_CLOUD_PROJECT not set"}
    from google.cloud import speech

    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        language_code=language_code,
        alternative_language_codes=["en-IN", "mr-IN", "kn-IN", "en-US", "pt-BR"],
        enable_automatic_punctuation=True,
    )
    response = client.recognize(config=config, audio=audio)
    chunks = [r.alternatives[0].transcript for r in response.results if r.alternatives]
    return {"text": " ".join(chunks), "skipped": False, "language_code": language_code}


def synthesize_brief(text: str, language_code: str = "en-IN") -> dict:
    """Read the investigation brief. Refuses to speak a numeric forecast."""
    if not text or not text.strip():
        return {"skipped": True, "reason": "empty"}
    lowered = text.lower()
    banned = ("will rise", "will fall", "forecast:", "prices will")
    if any(b in lowered for b in banned):
        return {"skipped": True, "reason": "refused_forecast_phrasing"}
    client = tts_client()
    if client is None:
        return {"skipped": True, "reason": "GOOGLE_CLOUD_PROJECT not set", "text": text}
    from google.cloud import texttospeech

    input_text = texttospeech.SynthesisInput(text=text[:4500])
    voice = texttospeech.VoiceSelectionParams(language_code=language_code, ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
    return {"skipped": False, "audio_content": response.audio_content, "language_code": language_code}
