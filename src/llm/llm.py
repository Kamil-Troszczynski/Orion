import os
from dataclasses import dataclass
from pipecat.services.openai.llm import OpenAILLMService, BaseOpenAILLMService
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)


@dataclass
class LLMParameters:
    temperature: float = 0.75
    max_tokens: int = 250
    top_p: float = 0.5
    top_k: int = 1
    frequency_penalty: float = 0.5
    presence_penalty: float = 0.1
    max_completion_tokens: int = 1000


class LLM:
    def __init__(self, llm_parameters: LLMParameters = LLMParameters()):
        self.instruction = OpenAILLMService.Settings(system_instruction = """
            Jesteś pomocnym asystentem AI i nazywasz się Orion.
        """)

        self.llm_parameters = BaseOpenAILLMService.InputParams(
            temperature = llm_parameters.temperature,
            max_tokens = llm_parameters.max_tokens,
            top_p = llm_parameters.top_p,
            top_k = llm_parameters.top_k,
            frequency_penalty = llm_parameters.frequency_penalty,
            presence_penalty = llm_parameters.presence_penalty,
            max_completion_tokens = llm_parameters.max_completion_tokens
        )

        self.api_key = os.environ['OPENAI_API_KEY']

    def get_llm(self) -> OpenAILLMService:
      return OpenAILLMService(api_key = self.api_key, params = self.llm_parameters, settings = self.instruction)  

    def get_aggregators(self, tools, vad_analyzer) -> LLMContextAggregatorPair:
        context = LLMContext(tools = tools)
        return LLMContextAggregatorPair(context, user_params = LLMUserAggregatorParams(vad_analyzer = vad_analyzer))
