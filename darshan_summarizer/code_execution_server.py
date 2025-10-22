"""
MCP Server for code execution using Jupyter kernel.

This module provides an MCP server with tools for executing Python and shell code
through a Jupyter kernel.
"""

import logging
from typing import Optional
from fastmcp import FastMCP
from pydantic import Field

from .jupyter_kernel import JupyterKernel, ExecutionResult

logger = logging.getLogger(__name__)


class CodeExecutionServer:
    """MCP server for code execution"""
    
    def __init__(self, working_dir: Optional[str] = None, kernel: Optional[JupyterKernel] = None):
        self.working_dir = working_dir
        self.kernel: Optional[JupyterKernel] = kernel  # Allow passing existing kernel
        self.mcp = FastMCP(
            name="code_execution",
            instructions="Execute Python and shell code through a Jupyter kernel"
        )
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register code execution tools"""
        
        @self.mcp.tool()
        async def execute_python(
            code: str = Field(..., description="Python code to execute")
        ) -> str:
            """
            Execute Python code in the Jupyter kernel.
            
            This tool executes Python code and returns the output, including any
            print statements, return values, or errors.
            """
            logger.info(f"Executing Python code:\n{code[:200]}...")
            
            # Ensure kernel is started
            if not self.kernel:
                self.kernel = JupyterKernel(working_dir=self.working_dir)
                await self.kernel.start()
            
            # Execute the code
            result = await self.kernel.execute(code, language="python")
            
            # Format the output
            if result.success:
                output = result.get_text_output()
                if output:
                    return f"✓ Execution successful:\n{output}"
                else:
                    return "✓ Execution successful (no output)"
            else:
                output = result.get_text_output()
                return f"✗ Execution failed:\n{output}"
        
        @self.mcp.tool()
        async def execute_shell(
            command: str = Field(..., description="Shell command to execute")
        ) -> str:
            """
            Execute shell commands in the Jupyter kernel.
            
            This tool executes shell commands and returns the output.
            """
            logger.info(f"Executing shell command: {command}")
            
            # Ensure kernel is started
            if not self.kernel:
                self.kernel = JupyterKernel(working_dir=self.working_dir)
                await self.kernel.start()
            
            # Execute the command
            result = await self.kernel.execute(command, language="bash")
            
            # Format the output
            if result.success:
                output = result.get_text_output()
                if output:
                    return f"✓ Command successful:\n{output}"
                else:
                    return "✓ Command successful (no output)"
            else:
                output = result.get_text_output()
                return f"✗ Command failed:\n{output}"
    
    async def shutdown(self):
        """Shutdown the kernel"""
        if self.kernel:
            await self.kernel.shutdown()
            self.kernel = None
    
    def get_server(self) -> FastMCP:
        """Get the FastMCP server instance"""
        return self.mcp


def create_code_execution_server(working_dir: Optional[str] = None, kernel: Optional[JupyterKernel] = None) -> FastMCP:
    """
    Create a code execution MCP server.
    
    Args:
        working_dir: Working directory for code execution
        kernel: Optional existing JupyterKernel instance to use
        
    Returns:
        FastMCP server instance
    """
    server = CodeExecutionServer(working_dir=working_dir, kernel=kernel)
    return server.get_server()

