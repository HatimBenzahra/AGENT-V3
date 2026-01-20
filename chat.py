"""CLI Chat Interface for ReAct Agent with Docker workspace and session management."""
import asyncio
import sys
from typing import Optional

from src.agent.react_agent import ReActAgent
from src.execution.docker_context import DockerExecutionContext
from src.session.conversation_context import ConversationContext
from src.session.session_manager import Session, SessionManager
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


class ChatInterface:
    """Interactive chat interface with Docker workspace support."""

    def __init__(self, verbose: bool = False) -> None:
        """Initialize chat interface."""
        self.verbose = verbose
        self.session: Optional[Session] = None
        self.agent: Optional[ReActAgent] = None
        self.session_manager = SessionManager()

    async def _initialize_session(self, session_id: Optional[str] = None) -> None:
        """Initialize or resume a session."""
        if session_id:
            # Resume existing session
            print(f"Resuming session: {session_id}")
            self.session = await Session.resume(session_id)
        else:
            # Create new session
            self.session = await Session.create_new()
            print(f"Created new session: {self.session.session_id}")

        # Register tools with contexts
        registry = ToolRegistry()

        # Context-free tools
        registry.register(CalculatorTool())

        # Web tools (no context needed)
        registry.register(WebSearchTool())
        registry.register(WebNewsSearchTool())
        registry.register(HttpClientTool())
        registry.register(FetchWebPageTool())

        # Docker-dependent tools
        registry.register(TerminalTool(
            execution_context=self.session.docker_context,
            conversation_context=self.session.context,
        ))
        registry.register(ReadFileTool(
            execution_context=self.session.docker_context,
            conversation_context=self.session.context,
        ))
        registry.register(WriteFileTool(
            execution_context=self.session.docker_context,
            conversation_context=self.session.context,
        ))
        registry.register(ListDirectoryTool(
            execution_context=self.session.docker_context,
            conversation_context=self.session.context,
        ))
        registry.register(DeleteFileTool(
            execution_context=self.session.docker_context,
            conversation_context=self.session.context,
        ))

        # Context-dependent tools
        registry.register(SaveOutputTool(
            conversation_context=self.session.context,
        ))
        registry.register(ListOutputsTool(
            conversation_context=self.session.context,
        ))

        # Initialize agent with context
        self.agent = ReActAgent(
            tool_registry=registry,
            conversation_context=self.session.context,
        )

    def _print_header(self) -> None:
        """Print chat header."""
        print("=" * 60)
        print("ReAct Agent - Docker Workspace Mode")
        print("=" * 60)
        if self.session:
            print(f"Session: {self.session.session_id}")
            print(f"Workspace: {self.session.docker_context.workspace_dir}")
        print("-" * 60)
        print("Commands:")
        print("  /quit, /exit, /q     - Exit chat")
        print("  /new                 - Start new session")
        print("  /list                - List all sessions")
        print("  /resume <id>         - Resume a session")
        print("  /save                - Force save current state")
        print("  /files               - List created files")
        print("  /outputs             - List saved outputs")
        print("  /verbose             - Toggle verbose mode")
        print("  /help                - Show this help")
        print("=" * 60 + "\n")

    def _print_user_message(self, message: str) -> None:
        """Print user message."""
        print(f"\n{'─' * 60}")
        print(f"You: {message}")
        print(f"{'─' * 60}")

    def _print_agent_response(self, response: str, state=None) -> None:
        """Print agent response."""
        print(f"\n{'─' * 60}")
        print(f"Agent: {response}")
        if self.verbose and state:
            print(f"\n[Details: {state.iteration} iterations]")
        print(f"{'─' * 60}\n")

    def _print_thinking(self) -> None:
        """Print thinking indicator."""
        print("Agent is thinking...", end="", flush=True)

    def _clear_thinking(self) -> None:
        """Clear thinking indicator."""
        print("\r" + " " * 30 + "\r", end="", flush=True)

    async def _handle_command(self, command: str) -> bool:
        """Handle a command. Returns True if should continue, False to exit."""
        cmd_parts = command.lower().split()
        cmd = cmd_parts[0]

        if cmd in ("/quit", "/exit", "/q"):
            if self.session:
                print("Saving session and cleaning up...")
                await self.session.close()
            print("\nGoodbye!\n")
            return False

        elif cmd == "/new":
            if self.session:
                await self.session.close()
            await self._initialize_session()
            self._print_header()

        elif cmd == "/list":
            sessions = self.session_manager.list_sessions()
            if not sessions:
                print("No sessions found.\n")
            else:
                print("\nAvailable sessions:")
                for s in sessions:
                    print(f"  {s.session_id} - {s.message_count} messages, {s.file_count} files")
                    print(f"    Updated: {s.updated_at}")
                print()

        elif cmd == "/resume":
            if len(cmd_parts) < 2:
                print("Usage: /resume <session_id>\n")
            else:
                session_id = cmd_parts[1]
                if not self.session_manager.session_exists(session_id):
                    print(f"Session not found: {session_id}\n")
                else:
                    if self.session:
                        await self.session.close()
                    await self._initialize_session(session_id)
                    self._print_header()

        elif cmd == "/save":
            if self.session:
                self.session.context.save()
                print("Session saved.\n")
            else:
                print("No active session.\n")

        elif cmd == "/files":
            if self.session:
                files = self.session.context.get_created_files()
                protected = self.session.context.get_protected_files()
                if not files:
                    print("No files created in this session.\n")
                else:
                    print("\nCreated files:")
                    for f in files:
                        prot = " [protected]" if f in protected else ""
                        print(f"  {f}{prot}")
                    print()
            else:
                print("No active session.\n")

        elif cmd == "/outputs":
            if self.session:
                outputs = self.session.context.get_outputs()
                if not outputs:
                    print("No outputs saved in this session.\n")
                else:
                    print("\nSaved outputs:")
                    for i, out in enumerate(outputs, 1):
                        print(f"  {i}. {out.task}")
                        print(f"     File: {out.file_path}")
                    print()
            else:
                print("No active session.\n")

        elif cmd == "/verbose":
            self.verbose = not self.verbose
            status = "enabled" if self.verbose else "disabled"
            print(f"Verbose mode {status}.\n")

        elif cmd == "/help":
            self._print_header()

        else:
            print(f"Unknown command: {command}\n")

        return True

    async def chat(self, message: str) -> str:
        """Process a chat message."""
        if not self.agent:
            return "Error: No active session"

        self._print_thinking()

        try:
            state = await self.agent.run(message)
            self._clear_thinking()

            if self.verbose:
                print("\n" + "=" * 60)
                print("REACT PROCESS:")
                print("=" * 60)
                for msg in state.conversation_history:
                    role = msg["role"].upper()
                    content = msg["content"]
                    print(f"\n[{role}]\n{content}")
                print("=" * 60 + "\n")

            return state.final_answer
        except Exception as e:
            self._clear_thinking()
            return f"Error: {str(e)}"

    async def run(self) -> None:
        """Run the chat interface."""
        print("\nInitializing Docker workspace...")

        try:
            await self._initialize_session()
        except Exception as e:
            print(f"\nError initializing Docker: {e}")
            print("Make sure Docker is running and try again.\n")
            return

        self._print_header()

        while True:
            try:
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    should_continue = await self._handle_command(user_input)
                    if not should_continue:
                        break
                    continue

                # Process chat message
                self._print_user_message(user_input)
                response = await self.chat(user_input)
                self._print_agent_response(response)

            except KeyboardInterrupt:
                if self.session:
                    print("\n\nSaving session...")
                    await self.session.close()
                print("\nGoodbye!\n")
                break
            except EOFError:
                if self.session:
                    await self.session.close()
                print("\nGoodbye!\n")
                break


async def main() -> None:
    """Main entry point."""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    chat = ChatInterface(verbose=verbose)
    await chat.run()


if __name__ == "__main__":
    asyncio.run(main())
