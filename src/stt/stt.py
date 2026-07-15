import os
from dataclasses import dataclass
from pipecat.transcriptions.language import Language
from pipecat.services.deepgram.stt import DeepgramSTTService, LiveOptions


@dataclass
class STTParameters:
    model_name: str = 'nova-3'
    language: Language = Language.PL
    interim_results: bool = True
    punctuate: bool = True
    profanity_filter: bool = True


class STTModel:
    def __init__(self, stt_parameters: STTParameters = STTParameters()):
        self.stt_parameters = LiveOptions(
            model = stt_parameters.model_name,
            language = stt_parameters.language,
            interim_results = stt_parameters.interim_results,
            punctuate = stt_parameters.punctuate,
            profanity_filter = stt_parameters.profanity_filter,
        )

        self.api_key = os.environ["DEEPGRAM_API_KEY"]

    def get_stt(self) -> DeepgramSTTService:
        return DeepgramSTTService(api_key = self.api_key, live_options = self.stt_parameters)