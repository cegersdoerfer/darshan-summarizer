"""
Darshan log analysis agent using PocketAgent with Jupyter kernel.

This module provides the main agent class that orchestrates the analysis
of Darshan logs using LLM-based code generation and execution.
"""

import os
import json
import asyncio
from typing import Optional, List, Dict, Tuple
from pocket_agent import PocketAgent, AgentConfig

from .parser import parse_darshan_log, parse_darshan_to_csv, list_darshan_modules
from .prompts import (
    create_darshan_analysis_prompt,
    create_darshan_summary_prompt,
    create_qa_prompt
)
from .code_execution_server import create_code_execution_server


def init_pocket_agent(
    model: str = "gpt-4o",
    working_dir: Optional[str] = None,
    system_prompt: Optional[str] = None,
    kernel = None
) -> PocketAgent:
    """
    Initialize a PocketAgent instance for code execution.
    
    Args:
        model: LLM model to use (default: "gpt-4o")
        working_dir: Working directory for code execution
        system_prompt: Optional system prompt for the agent
        kernel: Optional existing JupyterKernel instance
        
    Returns:
        Configured PocketAgent instance
    """
    # Create code execution MCP server with optional kernel
    mcp_server = create_code_execution_server(working_dir=working_dir, kernel=kernel)
    
    # Create agent config
    config = AgentConfig(
        llm_model=model,
        name="DarshanAnalyzer",
        role_description="Expert at analyzing Darshan I/O profiling logs and extracting insights about application I/O behavior",
        system_prompt=system_prompt or "You are an expert at analyzing Darshan I/O profiling logs using Python code.",
        completion_kwargs={
            "tool_choice": "auto",
            "max_tokens": 8192
        }
    )
    
    # Create and return the agent
    agent = PocketAgent(
        agent_config=config,
        mcp_config=mcp_server
    )
    
    return agent


class DarshanSummarizerAgent:
    """
    Agent for analyzing and summarizing Darshan I/O profiling logs.
    
    This agent uses Open Interpreter to analyze Darshan logs by:
    1. Parsing the log into CSV files
    2. Using Python code execution to analyze the data
    3. Generating insights and summaries about I/O behavior
    """
    
    def __init__(
        self,
        log_path: str,
        output_dir: Optional[str] = None,
        model: str = "gpt-4o",
        fs_config_description: Optional[Dict] = None
    ):
        """
        Initialize the Darshan summarizer agent.
        
        Args:
            log_path: Path to the .darshan log file
            output_dir: Directory for analysis outputs (default: creates one based on log name)
            model: LLM model to use for analysis
            fs_config_description: Optional description of file system parameters being tuned
        """
        self.log_path = log_path
        self.model = model
        self.fs_config_description = fs_config_description
        
        # Set up output directory
        if output_dir is None:
            log_basename = os.path.basename(log_path).replace(".darshan", "")
            self.output_dir = os.path.join(os.getcwd(), f"darshan_analysis_{log_basename}")
        else:
            self.output_dir = output_dir
        
        # Agent will be initialized after parsing (when we know the working directory)
        self.agent: Optional[PocketAgent] = None
        self.kernel = None  # Store reference to the Jupyter kernel
        
        # State variables
        self.darshan_modules: List[str] = []
        self.analysis_result: Optional[str] = None
        self.summary: Optional[str] = None
        
    def parse_log(self) -> str:
        """
        Parse the Darshan log file into CSV files.
        
        Returns:
            Path to the output directory containing CSV files
        """
        print(f"\n{'='*60}")
        print("STEP 1: Parsing Darshan Log")
        print(f"{'='*60}\n")
        
        # Parse the log
        log_content, log_filename = parse_darshan_log(self.log_path)
        print(f"Successfully parsed: {log_filename}")
        
        # Convert to CSV
        parse_darshan_to_csv(log_content, self.output_dir)
        
        # List available modules
        self.darshan_modules = list_darshan_modules(self.output_dir)
        print(f"\nFound {len(self.darshan_modules)} Darshan modules")
        
        # Initialize the Jupyter kernel
        print("\nInitializing Jupyter kernel...")
        from .jupyter_kernel import JupyterKernel
        self.kernel = JupyterKernel(working_dir=self.output_dir)
        asyncio.run(self.kernel.start())
        print("✓ Kernel started")
        
        # Initialize the agent with the kernel
        print("Initializing analysis agent...")
        self.agent = init_pocket_agent(
            model=self.model,
            working_dir=self.output_dir,
            kernel=self.kernel
        )
        print("✓ Agent initialized")
        
        return self.output_dir
    
    def _prepare_setup_code(self) -> str:
        """
        Prepare the setup code for loading data into the environment.
        
        Returns:
            The setup code string (not executed yet)
        """
        print("\nPreparing setup code...")
        
        # Build setup code
        setup_code_lines = [
            "import pandas as pd",
            "import numpy as np",
            "import os",
            "",
            "header = open('header.txt', 'r').read()",
            ""
        ]
        
        # Load each module's data and description
        forbidden_chars = ["-", " "]
        for module_name in self.darshan_modules:
            # Create valid Python variable name
            var_name = module_name
            for char in forbidden_chars:
                var_name = var_name.replace(char, "_")
            
            setup_code_lines.append(f"{var_name}_data = pd.read_csv('{module_name}.csv')")
            setup_code_lines.append(f"{var_name}_description = open('{module_name}_description.txt', 'r').read()")
        
        setup_code = "\n".join(setup_code_lines)
        print("✓ Setup code prepared")
        
        return setup_code
    
    def analyze(self) -> str:
        """
        Analyze the Darshan log using PocketAgent.
        
        Returns:
            Analysis result string
        """
        print(f"\n{'='*60}")
        print("STEP 2: Analyzing Darshan Log")
        print(f"{'='*60}\n")
        
        if not self.agent or not self.kernel:
            raise RuntimeError("Agent not initialized. Call parse_log() first.")
        
        # Prepare setup code
        setup_code = self._prepare_setup_code()
        
        # Execute setup code directly in the kernel
        print("Loading data into Jupyter kernel...")
        result = asyncio.run(self.kernel.execute(setup_code, language="python"))
        if not result.success:
            raise RuntimeError(f"Failed to load data: {result.error}")
        print("✓ Data loaded successfully\n")
        
        # Create analysis prompt
        prompt = create_darshan_analysis_prompt(
            darshan_modules=self.darshan_modules,
            setup_code=setup_code,
            fs_config_description=self.fs_config_description
        )
        
        print("Starting analysis...")
        print("-" * 60)
        
        # Run the analysis (async)
        result = asyncio.run(self.agent.run(prompt))
        
        # Save analysis result
        analysis_file = os.path.join(self.output_dir, "analysis.txt")
        with open(analysis_file, "w") as f:
            f.write(result)
        print(f"\n✓ Analysis saved to: {analysis_file}")
        
        # Also save the full conversation history
        messages_file = os.path.join(self.output_dir, "messages.json")
        with open(messages_file, "w") as f:
            json.dump(self.agent.messages, f, indent=4)
        print(f"✓ Conversation history saved to: {messages_file}")
        
        self.analysis_result = result
        return result
    
    def summarize(self) -> str:
        """
        Generate a summary of the analysis results.
        
        Returns:
            Summary text
        """
        if not self.agent or not self.agent.messages:
            raise RuntimeError("Must run analyze() before summarize()")
        
        print(f"\n{'='*60}")
        print("STEP 3: Generating Summary")
        print(f"{'='*60}\n")
        
        # Create summary prompt from the conversation history
        summary_prompt = create_darshan_summary_prompt(self.agent.messages)
        
        # Create a new agent for summarization (without code execution tools)
        summary_agent_config = AgentConfig(
            llm_model=self.model,
            name="Summarizer",
            system_prompt="You are an expert at summarizing technical analyses and extracting key insights.",
            completion_kwargs={
                "max_tokens": 8192
            }
        )
        
        # Create a minimal MCP server for the summarization agent
        from fastmcp import FastMCP
        summary_mcp = FastMCP(name="summarizer")
        
        summary_agent = PocketAgent(
            agent_config=summary_agent_config,
            mcp_config=summary_mcp
        )
        
        # Generate summary
        print("Generating summary...")
        summary = asyncio.run(summary_agent.run(summary_prompt))
        
        # Save summary
        summary_file = os.path.join(self.output_dir, "summary.txt")
        with open(summary_file, "w") as f:
            f.write(summary)
        print(f"✓ Summary saved to: {summary_file}")
        
        self.summary = summary
        return summary
    
    def run(self) -> Tuple[str, str]:
        """
        Run the complete analysis pipeline: parse, analyze, and summarize.
        
        Returns:
            Tuple of (analysis_result, summary)
        """
        self.parse_log()
        analysis_result = self.analyze()
        summary = self.summarize()
        
        print(f"\n{'='*60}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*60}")
        print(f"\nResults saved to: {self.output_dir}")
        print(f"  - Data files: {len(self.darshan_modules)} CSV files + descriptions")
        print(f"  - Analysis: analysis.txt")
        print(f"  - Messages: messages.json")
        print(f"  - Summary: summary.txt")
        
        return analysis_result, summary
    
    def ask_question(self, question: str, reset_conversation: bool = False) -> str:
        """
        Ask a question about the Darshan log data.
        
        Args:
            question: The question to answer
            reset_conversation: Whether to reset the conversation history (default: False)
            
        Returns:
            The answer to the question
        """
        if not self.agent or not self.kernel:
            raise RuntimeError("Agent not initialized. Call parse_log() first.")
        
        # If resetting, create a new agent and reload data
        if reset_conversation:
            # Restart the kernel to clear state
            asyncio.run(self.kernel.shutdown())
            asyncio.run(self.kernel.start())
            
            # Create new agent with the same kernel
            self.agent = init_pocket_agent(
                model=self.model,
                working_dir=self.output_dir,
                kernel=self.kernel
            )
            
            # Execute setup code directly in the kernel
            setup_code = self._prepare_setup_code()
            print("Reloading data into Jupyter kernel...")
            result = asyncio.run(self.kernel.execute(setup_code, language="python"))
            if not result.success:
                raise RuntimeError(f"Failed to reload data: {result.error}")
            print("✓ Data reloaded\n")
            
            prompt = create_qa_prompt(question, setup_code, new_environment=True)
        else:
            prompt = create_qa_prompt(question, new_environment=False)
        
        # Ask the question
        answer = asyncio.run(self.agent.run(prompt))
        
        return answer
    
    def get_summary(self) -> Optional[str]:
        """Get the generated summary, if available."""
        return self.summary
    
    def get_analysis_result(self) -> Optional[str]:
        """Get the analysis result, if available."""
        return self.analysis_result
    
    def get_conversation_messages(self) -> Optional[List[Dict]]:
        """Get the conversation messages, if available."""
        if self.agent:
            return self.agent.messages
        return None

