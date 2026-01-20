"""Docker-based execution context for agent operations."""
import asyncio
import uuid
from pathlib import Path
from typing import Optional, Tuple

import docker
from docker.errors import DockerException, ImageNotFound

from src.config import Config


class DockerExecutionContext:
    """Manages Docker container for isolated agent execution."""

    def __init__(self, session_id: Optional[str] = None) -> None:
        """Initialize Docker execution context.

        Args:
            session_id: Optional session ID. If not provided, generates a new one.
        """
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.client: Optional[docker.DockerClient] = None
        self.container: Optional[docker.models.containers.Container] = None
        self.workspace_dir = Config.SESSIONS_DIR / self.session_id / "files"
        self.mount_path = Config.WORKSPACE_MOUNT_PATH
        self._started = False

    async def start(self) -> None:
        """Start the Docker container."""
        if self._started:
            return

        try:
            self.client = docker.from_env()
        except DockerException as e:
            raise RuntimeError(f"Failed to connect to Docker: {e}")

        # Ensure workspace directory exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Ensure Docker image is available
            try:
                self.client.images.get(Config.DOCKER_IMAGE)
            except ImageNotFound:
                print(f"Pulling Docker image: {Config.DOCKER_IMAGE}")
                self.client.images.pull(Config.DOCKER_IMAGE)

            # Remove existing container if any
            try:
                existing = self.client.containers.get(f"agent-workspace-{self.session_id}")
                existing.remove(force=True)
            except docker.errors.NotFound:
                pass

            # Create and start container
            self.container = self.client.containers.run(
                Config.DOCKER_IMAGE,
                command="tail -f /dev/null",  # Keep container running
                detach=True,
                volumes={
                    str(self.workspace_dir.resolve()): {
                        "bind": self.mount_path,
                        "mode": "rw",
                    }
                },
                working_dir=self.mount_path,
                remove=False,
                name=f"agent-workspace-{self.session_id}",
                tty=True,
            )

            # Wait for container to be ready
            await asyncio.sleep(0.5)
            self._started = True

        except DockerException as e:
            raise RuntimeError(f"Failed to start Docker container: {e}")

    async def execute_command(
        self, command: str, timeout: int = 30
    ) -> Tuple[str, str, int]:
        """Execute a command in the container.

        Args:
            command: Shell command to execute.
            timeout: Timeout in seconds.

        Returns:
            Tuple of (stdout, stderr, exit_code).
        """
        if not self.container:
            raise RuntimeError("Container not started. Call start() first.")

        try:
            # Use bash with command passed via -c flag
            # The command is passed as a separate argument to avoid shell escaping issues
            exec_result = self.container.exec_run(
                ["bash", "-c", command],
                workdir=self.mount_path,
                stdout=True,
                stderr=True,
                demux=True,
            )

            stdout = ""
            stderr = ""

            if exec_result.output:
                if isinstance(exec_result.output, tuple):
                    stdout = exec_result.output[0].decode("utf-8") if exec_result.output[0] else ""
                    stderr = exec_result.output[1].decode("utf-8") if exec_result.output[1] else ""
                else:
                    stdout = exec_result.output.decode("utf-8")

            return stdout, stderr, exec_result.exit_code

        except Exception as e:
            return "", f"Error executing command: {e}", 1

    def resolve_path(self, path: str) -> Path:
        """Resolve a relative path to workspace absolute path.

        Args:
            path: Relative or absolute path.

        Returns:
            Absolute path within workspace.

        Raises:
            ValueError: If path is outside workspace.
        """
        p = Path(path)
        if p.is_absolute():
            # If absolute, ensure it's within workspace
            try:
                p.relative_to(self.workspace_dir)
            except ValueError:
                raise ValueError(f"Path {path} is outside workspace")
            return p
        return self.workspace_dir / path

    def get_container_path(self, local_path: Path) -> str:
        """Convert local workspace path to container path.

        Args:
            local_path: Local path in workspace.

        Returns:
            Container path.
        """
        try:
            relative = local_path.relative_to(self.workspace_dir)
            return str(Path(self.mount_path) / relative)
        except ValueError:
            raise ValueError(f"Path {local_path} is not in workspace")

    def get_workspace_dir(self) -> Path:
        """Get the workspace directory path."""
        return self.workspace_dir

    def get_session_dir(self) -> Path:
        """Get the session directory path (parent of files/)."""
        return Config.SESSIONS_DIR / self.session_id

    async def stop(self) -> None:
        """Stop and remove the container."""
        if self.container:
            try:
                self.container.stop(timeout=5)
                self.container.remove()
            except Exception:
                pass
            self.container = None
            self._started = False

    async def cleanup(self) -> None:
        """Clean up container and optionally workspace."""
        await self.stop()
        if Config.AUTO_CLEANUP and self.workspace_dir.exists():
            import shutil
            shutil.rmtree(self.workspace_dir, ignore_errors=True)

    def is_running(self) -> bool:
        """Check if container is running."""
        if not self.container:
            return False
        try:
            self.container.reload()
            return self.container.status == "running"
        except Exception:
            return False

    async def __aenter__(self) -> "DockerExecutionContext":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()
