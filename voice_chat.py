from RealtimeSTT import AudioToTextRecorder
from omnivoice import OmniVoice
from ollama import chat
import sounddevice as sd
import torch


device = "cuda" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32


class VoiceChat:
    def __init__(self, 
                 stt_id: str = "tiny", 
                 moe_id: str = "qwen3:8b",
                 tts_id: str = "k2-fsa/OmniVoice",
                 sample_rate: int = 24000,
                 instruction: str = "female, low pitch, british accent"):

        self.recorder = AudioToTextRecorder(model = stt_id, device = "cpu", compute_type = "int8")
        self.sample_rate = sample_rate
        self.response = lambda transcribed_text : chat(
            model = moe_id,
            messages = [
                {"role": "user", "content": transcribed_text}
            ]
        )
        self.text2speech = OmniVoice.from_pretrained(tts_id, device_map = device, dtype = torch_dtype)
        self.audio = lambda response : self.text2speech.generate(text = response["message"]["content"], 
                                                            instruct = instruction)

    def process(self) -> None:
        with self.recorder:
            while True:
                text = self.recorder.text()
                if not text or not text.strip():
                    continue
                moe_answer = self.response(text)
                audio = self.audio(moe_answer)
                sd.play(audio[0], samplerate = self.sample_rate)
                sd.wait()

