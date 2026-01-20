"""Test script for the ReAct agent with example tasks."""
import asyncio

from src.agent.react_agent import ReActAgent
from src.tools.calculator import CalculatorTool
from src.tools.registry import ToolRegistry


async def test_task(task: str, description: str) -> None:
    """Test a single task."""
    print(f"\n{'='*60}")
    print(f"Test: {description}")
    print(f"Task: {task}")
    print(f"{'='*60}\n")
    
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    
    agent = ReActAgent(registry)
    state = await agent.run(task)
    
    print(f"\n{'='*60}")
    print("CONVERSATION HISTORY:")
    print(f"{'='*60}")
    for msg in state.conversation_history:
        role = msg["role"].upper()
        content = msg["content"]
        print(f"\n[{role}]\n{content}")
    
    print(f"\n{'='*60}")
    print(f"FINAL ANSWER: {state.final_answer}")
    print(f"Iterations: {state.iteration}")
    print(f"{'='*60}\n")


async def main() -> None:
    """Run test cases."""
    test_cases = [
        ("What is 15 * 23?", "Simple calculation"),
        ("Calculate the square root of 144 and add 10 to it", "Multi-step calculation"),
        ("What is 2 + 2?", "Very simple task"),
    ]
    
    print("🧪 ReAct Agent Test Suite\n")
    
    for task, description in test_cases:
        try:
            await test_task(task, description)
        except Exception as e:
            print(f"❌ Error testing '{task}': {e}\n")
    
    print("\n✅ Test suite completed!")


if __name__ == "__main__":
    asyncio.run(main())
