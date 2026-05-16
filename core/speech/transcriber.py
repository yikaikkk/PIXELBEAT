"""Speech transcription module using SiliconFlow API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TranscriptionResult:
    """Result of speech transcription."""

    text: str
    language: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
    saved_path: Optional[str] = None


class SpeechTranscriber:
    """Speech transcription service using SiliconFlow API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        save_dir: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("SPEECH_API_KEY", "")
        self.api_url = api_url or os.getenv("SPEECH_API_URL", "https://api.siliconflow.cn/v1/audio/transcriptions")
        self.model = model or os.getenv("SPEECH_MODEL", "FunAudioLLM/SenseVoiceSmall")
        self.save_dir = Path(save_dir or ".pixelbeat/doc/audioTodoc")

        if not self.api_key:
            raise ValueError("SPEECH_API_KEY is not set. Please configure it in .env file.")

    def _save_transcription(self, text: str, audio_path: Path) -> str:
        """
        Save transcription text to file.

        Args:
            text: Transcribed text.
            audio_path: Original audio file path.

        Returns:
            Path to the saved text file.
        """
        self.save_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{audio_path.stem}.txt"
        save_path = self.save_dir / filename

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(text)

        return str(save_path)

    def transcribe(self, audio_path: str | Path) -> TranscriptionResult:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to the audio file (mp3, wav, etc.)

        Returns:
            TranscriptionResult with transcribed text or error information.
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            return TranscriptionResult(
                text="",
                success=False,
                error=f"Audio file not found: {audio_path}",
            )

        try:
            with open(audio_path, "rb") as audio_file:
                files = {"file": audio_file}
                data = {"model": self.model}
                headers = {"Authorization": f"Bearer {self.api_key}"}

                response = requests.post(
                    self.api_url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=180,
                )

                if response.status_code == 200:
                    result = response.json()
                    text = result.get("text", "")
                    language = result.get("language")
                    saved_path = self._save_transcription(text, audio_path)
                    return TranscriptionResult(
                        text=text,
                        language=language,
                        success=True,
                        saved_path=saved_path,
                    )
                else:
                    return TranscriptionResult(
                        text="",
                        success=False,
                        error=f"API error: {response.status_code} - {response.text}",
                    )

        except requests.exceptions.Timeout:
            return TranscriptionResult(
                text="",
                success=False,
                error="Request timed out. The audio file may be too large.",
            )
        except requests.exceptions.RequestException as e:
            return TranscriptionResult(
                text="",
                success=False,
                error=f"Network error: {str(e)}",
            )
        except Exception as e:
            return TranscriptionResult(
                text="",
                success=False,
                error=f"Unexpected error: {str(e)}",
            )

    def transcribe_batch(self, audio_paths: list[str | Path]) -> list[TranscriptionResult]:
        """
        Transcribe multiple audio files.

        Args:
            audio_paths: List of paths to audio files.

        Returns:
            List of TranscriptionResult for each file.
        """
        return [self.transcribe(path) for path in audio_paths]


def test_transcription(audio_path: str) -> None:
    """
    Test function for speech transcription.

    Args:
        audio_path: Path to a test audio file.
    """
    print("=" * 50)
    print("Speech Transcription Test")
    print("=" * 50)

    try:
        transcriber = SpeechTranscriber()
        print(f"API URL: {transcriber.api_url}")
        print(f"Model: {transcriber.model}")
        print(f"Audio file: {audio_path}")
        print("-" * 50)

        print("Transcribing...")
        result = transcriber.transcribe(audio_path)

        if result.success:
            print("✓ Transcription successful!")
            print(f"Language: {result.language or 'Unknown'}")
            print(f"Text: {result.text}")
        else:
            print("✗ Transcription failed!")
            print(f"Error: {result.error}")

    except ValueError as e:
        print(f"✗ Configuration error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

    print("=" * 50)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        test_audio_path = sys.argv[1]
    else:
        test_audio_path = input("Enter path to audio file: ").strip()

    if test_audio_path:
        test_transcription(test_audio_path)
    else:
        print("No audio file provided. Exiting.")
