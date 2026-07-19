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
    temperature: float = 0.85
    max_tokens: int = 400
    top_p: float = 0.5
    top_k: int = 2
    frequency_penalty: float = 0.5
    presence_penalty: float = 0.1


class LLM:
    def __init__(self, llm_parameters: LLMParameters = LLMParameters()):
        self.instruction = OpenAILLMService.Settings(system_instruction = """
            You are a helpful AI assistant and your name is Orion.
            Your responses will be spoken aloud by a text-to-speech system rather than displayed as text. 
            Write as if you are speaking naturally in a smooth, conversational way.

            Follow these rules:
            - Do not use Markdown formatting. Do not use bullet points, numbered lists, headings, tables, or formatting characters.
            - Do not use abbreviations. Write them out in full. 
            For example, write "for example" instead of "e.g.", "that is" instead of "i.e.", and "and so on" instead of "etc.".
            - Write numbers, dates, times, and units as words exactly as they would be spoken. 
            For example, write "twenty-three degrees" instead of numerical representation, and "five o'clock in the afternoon" instead of "5:00 PM".
            Do not use symbols that have no meaning when spoken aloud, such as percent signs, ampersands, slashes, or punctuation used only for formatting. 
            Rewrite the sentence naturally using words instead.
            - If the conversation takes place in a language other than Polish, apply these same rules in that language. 
            - Do not use Markdown, avoid abbreviations, and write numbers and symbols as they would naturally be spoken.
            """)

        self.llm_parameters = BaseOpenAILLMService.InputParams(
            temperature = llm_parameters.temperature,
            max_tokens = llm_parameters.max_tokens,
            top_p = llm_parameters.top_p,
            top_k = llm_parameters.top_k,
            frequency_penalty = llm_parameters.frequency_penalty,
            presence_penalty = llm_parameters.presence_penalty
        )

        self.api_key = os.environ['OPENAI_API_KEY']

    def get_llm(self) -> OpenAILLMService:
      return OpenAILLMService(api_key = self.api_key, params = self.llm_parameters, settings = self.instruction)  

    def get_aggregators(self, tools, vad_analyzer) -> LLMContextAggregatorPair:
        context = LLMContext(tools = tools)
        return LLMContextAggregatorPair(context, user_params = LLMUserAggregatorParams(vad_analyzer = vad_analyzer))
