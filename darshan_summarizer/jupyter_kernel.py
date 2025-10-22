"""
Jupyter Kernel Manager for code execution.

This module provides a simple interface to execute Python and shell code
using a Jupyter kernel, without requiring Docker.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from jupyter_client.manager import AsyncKernelManager
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of code execution"""
    success: bool
    messages: List[Dict[str, Any]]
    error: Optional[str] = None
    
    def get_text_output(self) -> str:
        """Extract text output from messages"""
        outputs = []
        for msg in self.messages:
            msg_type = msg.get("msg_type")
            content = msg.get("content", {})
            
            if msg_type == "stream":
                outputs.append(content.get("text", ""))
            elif msg_type == "execute_result":
                data = content.get("data", {})
                if "text/plain" in data:
                    outputs.append(data["text/plain"])
            elif msg_type == "display_data":
                data = content.get("data", {})
                if "text/plain" in data:
                    outputs.append(data["text/plain"])
            elif msg_type == "error":
                # Include error information
                traceback = content.get("traceback", [])
                outputs.append("\n".join(traceback))
        
        return "\n".join(outputs)
    
    def has_error(self) -> bool:
        """Check if execution resulted in an error"""
        for msg in self.messages:
            if msg.get("msg_type") == "error":
                return True
        return self.error is not None


class JupyterKernel:
    """Manages a single Jupyter kernel for code execution"""
    
    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = working_dir
        self.km: Optional[AsyncKernelManager] = None
        self.kc = None
        self._execution_lock = asyncio.Lock()
        self._started = False
    
    async def start(self):
        """Start the Jupyter kernel"""
        if self._started:
            return
        
        logger.info(f"Starting Jupyter kernel in {self.working_dir or 'current directory'}")
        self.km = AsyncKernelManager()
        
        kwargs = {}
        if self.working_dir:
            kwargs["cwd"] = self.working_dir
        
        await self.km.start_kernel(**kwargs)
        self.kc = self.km.client()
        self.kc.start_channels()
        await self.kc.wait_for_ready()
        self._started = True
        logger.info("Jupyter kernel started successfully")
    
    async def execute_raw(self, code: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute code and yield raw Jupyter messages"""
        if not self._started:
            await self.start()
        
        async with self._execution_lock:
            msg_id = self.kc.execute(code)
            logger.debug(f"Executing code with msg_id: {msg_id}")
            
            try:
                while True:
                    reply = await self.kc.get_iopub_msg()
                    msg_type = reply.get("msg_type")
                    logger.debug(f"Received message type: {msg_type}")
                    
                    yield reply
                    
                    # Break on status idle
                    if msg_type == "status" and reply["content"]["execution_state"] == "idle":
                        break
                        
            except asyncio.CancelledError:
                logger.info("Execution cancelled")
                raise
    
    async def execute(self, code: str, language: str = "python") -> ExecutionResult:
        """
        Execute code and return a structured result.
        
        Args:
            code: The code to execute
            language: Either "python" or "bash"
            
        Returns:
            ExecutionResult with success status and output
        """
        if not self._started:
            await self.start()
        
        # Convert bash code to Jupyter shell magic
        if language == "bash":
            code = code.strip()
            if '\n' in code:
                code = f"%%bash\n{code}"
            else:
                code = f"!{code}"
        
        messages = []
        has_error = False
        error_msg = None
        
        try:
            async for message in self.execute_raw(code):
                messages.append(message)
                
                # Check for errors
                if message.get("msg_type") == "error":
                    has_error = True
                    content = message.get("content", {})
                    error_msg = f"{content.get('ename', 'Error')}: {content.get('evalue', 'Unknown error')}"
        
        except Exception as e:
            logger.error(f"Error during code execution: {e}")
            has_error = True
            error_msg = str(e)
        
        return ExecutionResult(
            success=not has_error,
            messages=messages,
            error=error_msg
        )
    
    async def shutdown(self):
        """Shutdown the kernel"""
        if not self._started:
            return
        
        logger.info("Shutting down Jupyter kernel")
        if self.kc:
            self.kc.stop_channels()
        if self.km:
            await self.km.shutdown_kernel()
        self._started = False
    
    def __del__(self):
        """Cleanup on deletion"""
        if self._started and self.km:
            try:
                # Try to shutdown gracefully
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.shutdown())
            except Exception:
                pass

