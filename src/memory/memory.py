import os
from pipecat.services.mem0.memory import Mem0MemoryService


class Memory:
    def __init__(self, user_id: str = 'unique_user_id', agent_id: str = 'orion'):
        self.api_key = os.environ["MEM0_API_KEY"]
        self.user_id = user_id
        self.agent_id = agent_id

    def get_memory(self) -> Mem0MemoryService:
        return Mem0MemoryService(api_key = self.api_key, user_id = self.user_id, agent_id = self.agent_id)
