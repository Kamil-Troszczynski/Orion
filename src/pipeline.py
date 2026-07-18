from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.runner.types import RunnerArguments
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.frames.frames import LLMConfigureOutputFrame

from src.llm.llm import LLM
from src.stt.stt import STTModel
from src.tts.tts import TTSModel
from src.memory.memory import Memory
from src.tools.weather import get_weather
from src.tools.web_search import get_answer


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    stt, memory, llm, tts = STTModel(), Memory(), LLM(), TTSModel()
    stt_service, memory_service, llm_service, tts_service = stt.get_stt(), memory.get_memory(), llm.get_llm(), tts.get_tts()

    silero_vad = SileroVADAnalyzer()

    tools = [get_weather, get_answer]

    user_aggregator, assistant_aggregator = llm.get_aggregators(tools, silero_vad)

    pipeline_parameters = PipelineParams(
        audio_in_sample_rate = 16000,
        audio_out_sample_rate = 24000,
        enable_metrics = True,
        enable_usage_metrics = True,
    )

    pipeline = Pipeline([
            transport.input(),
            stt_service,
            user_aggregator,
            memory_service,
            llm_service,
            tts_service,
            transport.output(),
            assistant_aggregator,
        ])

    task = PipelineTask(pipeline, params = pipeline_parameters)

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        await task.queue_frame(LLMConfigureOutputFrame(skip_tts = True))

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await task.cancel()

    runner = PipelineRunner(handle_sigint = runner_args.handle_sigint)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    transport_parameters = TransportParams(audio_in_enabled = True, audio_out_enabled = True)
    transport = SmallWebRTCTransport(params = transport_parameters, webrtc_connection = runner_args.webrtc_connection,)
    await run_bot(transport, runner_args)