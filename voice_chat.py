from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from omnivoice import OmniVoice
from ollama import chat
import soundfile as sf
import torch


device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32


class VoiceChat:
    def __init__(self, 
                 stt_id: str = "openai/whisper-large-v3", 
                 moe_id: str = "qwen3:8b",
                 tts_id: str = "k2-fsa/OmniVoice",
                 instruction: str = "female, low pitch, british accent"):

        self.speech2text = self.stt(stt_id)
        self.response = lambda transcribed_text : chat(
            model = moe_id,
            messages = [
                {"role": "user", "content": transcribed_text}
            ]
        )
        self.text2speech = OmniVoice.from_pretrained(tts_id, device_map = device, dtype = torch_dtype)
        self.audio = lambda response : self.text2speech.generate(text = response["message"]["content"], 
                                                            instruct = instruction)

    def stt(self, stt_id: str, 
            chunk_length_s: int = 50, 
            batch_size: int = 50) -> pipeline:
        
        speech_seq2seq = AutoModelForSpeechSeq2Seq.from_pretrained(
            stt_id, 
            dtype = torch_dtype, 
            low_cpu_mem_usage = True, 
            use_safetensors = True).to(device)
        
        processor = AutoProcessor.from_pretrained(stt_id)

        return pipeline(
            "automatic-speech-recognition",
            model = speech_seq2seq,
            tokenizer = processor.tokenizer,
            feature_extractor = processor.feature_extractor,
            chunk_length_s = chunk_length_s,
            batch_size = batch_size,
            dtype = torch_dtype,
            device = device,
        )        

    def process(self, x: str, y: str = 'out.wav') -> None:
        encoded_speech = self.speech2text(x)
        transcribed_text = encoded_speech['text']
        moe_answer = self.response(transcribed_text)
        audio = self.audio(moe_answer)
        sf.write(y, audio[0], 24000)


if __name__ == "__main__":
    voicechat = VoiceChat()
    voicechat.process('in.mp3')


