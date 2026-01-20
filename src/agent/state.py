from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AgentState:
    task: str
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    iteration: int = 0
    is_complete: bool = False
    final_answer: str = ""

    def add_thought(self, thought: str) -> None:
        self.conversation_history.append({"role": "assistant", "content": f"Thought: {thought}"})

    def add_action(self, action: str) -> None:
        self.conversation_history.append({"role": "assistant", "content": f"Action: {action}"})

    def add_observation(self, observation: str) -> None:
        self.observations.append(observation)
        self.conversation_history.append({"role": "user", "content": f"Observation: {observation}"})

    def set_final_answer(self, answer: str) -> None:
        self.final_answer = answer
        self.is_complete = True
        self.conversation_history.append({"role": "assistant", "content": f"Final Answer: {answer}"})
