import os
import httpx
from typing import Literal
from dataclasses import dataclass
from pipecat.services.llm_service import FunctionCallParams
from pipecat.adapters.schemas.direct_function import tool_options


class WebSearchException(Exception):
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (Error Code: {self.error_code})"


SearchMode = Literal["fast", "medium", "research"]


@dataclass
class WebSearchParameters:
    count: int = 8,
    maximum_number_of_urls: int = 3,
    maximum_number_of_tokens: int = 2048,
    maximum_number_of_tokens_per_url: int = 1024,
    maximum_number_of_snippets: int = 8,
    maximum_number_of_snippets_per_url: int = 2,
    context_threshold_mode: str = "strict",
    enable_local: bool = False,
    timeout: int = 8,
 
    @classmethod
    def medium(cls) -> "WebSearchParameters":
        return cls(
            count = 8,
            maximum_number_of_urls = 3,
            maximum_number_of_tokens = 3000,
            maximum_number_of_tokens_per_url = 1500,
            maximum_number_of_snippets = 6,
            maximum_number_of_snippets_per_url = 2,
            context_threshold_mode = "strict",
            enable_local = False,
            timeout = 10,
        )
 
    @classmethod
    def research(cls) -> "WebSearchParameters":
        return cls(
            count = 30,
            maximum_number_of_urls = 10,
            maximum_number_of_tokens = 16000,
            maximum_number_of_tokens_per_url = 4096,
            maximum_number_of_snippets = 40,
            maximum_number_of_snippets_per_url = 6,
            context_threshold_mode = "balanced",
            enable_local = False,
            timeout = 15,
        )


class WebSearch:
    def __init__(self, query: str = None, web_search_params: WebSearchParameters = None):
        web_search_params = web_search_params or WebSearchParameters()
        self.url = 'https://api.search.brave.com/res/v1/llm/context'
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": os.environ['BRAVE_SEARCH_API_KEY']
        }
        self.parameters = {
            "q": query, 
            "maximum_number_of_urls": web_search_params.maximum_number_of_urls,
            "maximum_number_of_tokens": web_search_params.maximum_number_of_tokens,
            "maximum_number_of_tokens_per_url": web_search_params.maximum_number_of_tokens_per_url,
            "maximum_number_of_snippets": web_search_params.maximum_number_of_snippets,
            "maximum_number_of_snippets_per_url": web_search_params.maximum_number_of_snippets_per_url,
            "context_threshold_mode": web_search_params.context_threshold_mode,
            "enable_local": web_search_params.enable_local
        }
        self.timeout = web_search_params.timeout

    async def get_response(self) -> dict:
        async with httpx.AsyncClient(timeout = self.timeout) as client:
            try:
                response = await client.get(self.url, params = self.parameters, headers = self.headers)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise WebSearchException(f"Brave search API Error: {e.response.status_code}", "http_error")
            except httpx.RequestError as e:
                raise WebSearchException(f"Failed to connect to the brave search API: {e}", "network_error")
        return response.json()


def resolve_params(mode: SearchMode) -> WebSearchParameters:
    if mode == "research":
        return WebSearchParameters.research()
    if mode == "medium":
        return WebSearchParameters.medium()
    return WebSearchParameters()


@tool_options(cancel_on_interruption = False)
async def get_answer(params: FunctionCallParams, query: str, mode: SearchMode = "fast"):
    """Search the web and return pre-extracted, relevant content to help answer a question.
 
    This call runs asynchronously: you must respond to the user immediately, before the
    result is available — say something like "Pozwól mi to sprawdzić" (or the equivalent
    in whatever language the conversation is in). Do not guess or answer from your own
    knowledge while waiting; the actual content will arrive afterward and you'll use it
    to answer in your next turn.
 
    If the user says something else in the meantime (asks a different question, changes
    topic) before the result arrives, handle that first, then return to this topic
    explicitly once you do answer it — e.g. "Wracając do pytania dotyczącego..." (or the
    equivalent in the conversation's language) — rather than answering out of nowhere as
    if no time had passed.
 
    Grounding: once the result arrives, treat it as your primary source of truth for this
    query, even if it conflicts with what you already "know." Your training data can be
    outdated or wrong on current events, prices, releases, and similar fast-changing facts —
    prefer the retrieved content over your own recollection. If the results don't clearly
    answer the question, say so rather than filling the gap from memory.
 
    If the "fast" results feel insufficient to answer confidently, or the topic turns out
    to be more complex than expected once you see the results, you may call this tool again
    with mode="research" to get broader context before answering. Don't guess or answer
    incompletely if better context is one more call away.
 
    Args:
        query: The specific question or topic to search for, e.g. "recent machine learning
            papers" or "latest AI technologies". Keep it focused — one topic per call.
        mode: How much search depth and context to retrieve. Choose based on question
            complexity, not user tone:
            - "fast": simple, single-fact lookups with one clear answer
              (e.g. "what's the capital of Norway", "who won yesterday's match").
              Used automatically if you don't specify a mode.
            - "medium": questions needing a bit more context than a single fact,
              but not a full multi-source comparison (e.g. "what is retrieval-augmented
              generation", "what's new in the latest iPhone").
            - "research": complex, multi-part, or comparative questions that benefit from
              broader context across several sources (e.g. "compare the latest LLM releases",
              "what are the arguments for and against X").
    """
    try:
        websearch = WebSearch(query, resolve_params(mode))
        answer = await websearch.get_response()
        await params.result_callback(answer)
    except WebSearchException as wse:
        await params.result_callback({"error": str(wse)})
    except Exception as e:
        await params.result_callback({"error": f"Failed to get response: {e}"})