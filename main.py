"""Task-based ReAct Agent CLI with Docker workspace (shows full ReAct process)."""
import asyncio
import sys

from src.agent.react_agent import ReActAgent
from src.execution.docker_context import DockerExecutionContext
from src.session.conversation_context import ConversationContext
from src.tools.calculator import CalculatorTool
from src.tools.file_tools import (
    DeleteFileTool,
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
)
from src.tools.output_tool import ListOutputsTool, SaveOutputTool
from src.tools.registry import ToolRegistry
from src.tools.terminal_tool import TerminalTool
from src.tools.web_search_tool import WebSearchTool, WebNewsSearchTool
from src.tools.http_tool import HttpClientTool, FetchWebPageTool


async def main() -> None:
    """Run the agent in task mode with Docker workspace."""
    simple_mode = "--simple" in sys.argv or "-s" in sys.argv

    if simple_mode:
        # Simple mode: calculator only, no Docker
        print("ReAct Agent - Simple Mode (calculator only)")
        print("Enter 'quit' or 'exit' to stop\n")

        registry = ToolRegistry()
        registry.register(CalculatorTool())
        agent = ReActAgent(registry)

        while True:
            task = input("Enter your task: ").strip()
            if not task or task.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            print("\n" + "=" * 60)
            print("Processing...")
            print("=" * 60 + "\n")

            try:
                state = await agent.run(task)
                _print_result(state)
            except Exception as e:
                print(f"\nError: {e}\n")

    else:
        # Full mode: Docker workspace with all tools
        print("ReAct Agent - Task Mode with Docker Workspace")
        print("Initializing Docker workspace...")

        try:
            docker_ctx = DockerExecutionContext()
            await docker_ctx.start()
            context = ConversationContext(docker_ctx.session_id)
        except Exception as e:
            print(f"\nError initializing Docker: {e}")
            print("Make sure Docker is running.")
            print("Use --simple or -s flag to run without Docker.\n")
            return

        print(f"Session: {docker_ctx.session_id}")
        print(f"Workspace: {docker_ctx.workspace_dir}")
        print("Enter 'quit' or 'exit' to stop\n")

        # Register all tools
        registry = ToolRegistry()
        registry.register(CalculatorTool())

        # Web tools (no context needed)
        registry.register(WebSearchTool())
        registry.register(WebNewsSearchTool())
        registry.register(HttpClientTool())
        registry.register(FetchWebPageTool())

        registry.register(TerminalTool(
            execution_context=docker_ctx,
            conversation_context=context,
        ))
        registry.register(ReadFileTool(
            execution_context=docker_ctx,
            conversation_context=context,
        ))
        registry.register(WriteFileTool(
            execution_context=docker_ctx,
            conversation_context=context,
        ))
        registry.register(ListDirectoryTool(
            execution_context=docker_ctx,
            conversation_context=context,
        ))
        registry.register(DeleteFileTool(
            execution_context=docker_ctx,
            conversation_context=context,
        ))
        registry.register(SaveOutputTool(conversation_context=context))
        registry.register(ListOutputsTool(conversation_context=context))

        agent = ReActAgent(registry, conversation_context=context)

        try:
            while True:
                task = input("Enter your task: ").strip()
                if not task or task.lower() in ("quit", "exit", "q"):
                    print("Saving session and cleaning up...")
                    context.save()
                    await docker_ctx.stop()
                    print("Goodbye!")
                    break

                print("\n" + "=" * 60)
                print("Processing...")
                print("=" * 60 + "\n")

                try:
                    state = await agent.run(task)
                    _print_result(state)
                except Exception as e:
                    print(f"\nError: {e}\n")

        except KeyboardInterrupt:
            print("\n\nSaving session and cleaning up...")
            context.save()
            await docker_ctx.stop()
            print("Goodbye!\n")


def _print_result(state) -> None:
    """Print the result of a task."""
    print("\n" + "=" * 60)
    print("REACT PROCESS:")
    print("=" * 60)
    for msg in state.conversation_history:
        role = msg["role"].upper()
        content = msg["content"]
        print(f"\n[{role}]\n{content}")

    print("\n" + "=" * 60)
    print(f"FINAL ANSWER: {state.final_answer}")
    print(f"Iterations: {state.iteration}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
