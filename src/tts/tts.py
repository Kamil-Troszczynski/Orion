import os
from dataclasses import dataclass
from pipecat.transcriptions.language import Language
from pipecat.services.cartesia.tts import CartesiaTTSService


@dataclass
class TTSParameters:
    model_name: str = 'sonic-3.5'
    voice: str = 'd358377a-cd1d-45c5-abd0-701314e36cbe'
    language: Language = Language.PL


class TTSModel:
    def __init__(self, tts_parameters: TTSParameters = TTSParameters()):
        self.tts_parameters = CartesiaTTSService.Settings(
            model = tts_parameters.model_name,
            voice = tts_parameters.voice,
            language = tts_parameters.language
        )

        self.api_key = os.environ["CARTESIA_API_KEY"]

    def get_tts(self) -> CartesiaTTSService:
        return CartesiaTTSService(api_key = self.api_key, settings = self.tts_parameters)