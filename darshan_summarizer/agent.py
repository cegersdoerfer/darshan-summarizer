"""
Darshan log analysis agent using Open Interpreter.

This module provides the main agent class that orchestrates the analysis
of Darshan logs using LLM-based code generation and execution.
"""

import os
import json
from typing import Optional, List, Dict, Tuple
from interpreter import OpenInterpreter

from .parser import parse_darshan_log, parse_darshan_to_csv, list_darshan_modules
from .prompts import (
    create_darshan_analysis_prompt,
    create_darshan_summary_prompt,
    create_qa_prompt
)


def init_code_interpreter(model: str = "openai/gpt-4o", auto_run: bool = True) -> OpenInterpreter:
    """
    Initialize an Open Interpreter instance for code execution.
    
    Args:
        model: LLM model to use (default: "openai/gpt-4o")
        auto_run: Whether to automatically run generated code (default: True)
        
    Returns:
        Configured OpenInterpreter instance
    """
    interpreter = OpenInterpreter()
    interpreter.llm.model = model
    interpreter.auto_run = True
    interpreter.loop = True
    interpreter.llm.stream = False
    interpreter.llm.max_tokens = 8192
    interpreter.llm.context_window = 200000
    return interpreter


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
        model: str = "openai/gpt-4o",
        auto_run: bool = True,
        fs_config_description: Optional[Dict] = None
    ):
        """
        Initialize the Darshan summarizer agent.
        
        Args:
            log_path: Path to the .darshan log file
            output_dir: Directory for analysis outputs (default: creates one based on log name)
            model: LLM model to use for analysis
            auto_run: Whether to automatically run generated code
            fs_config_description: Optional description of file system parameters being tuned
        """
        self.log_path = log_path
        self.model = model
        self.auto_run = auto_run
        self.fs_config_description = fs_config_description
        
        # Set up output directory
        if output_dir is None:
            log_basename = os.path.basename(log_path).replace(".darshan", "")
            self.output_dir = os.path.join(os.getcwd(), f"darshan_analysis_{log_basename}")
        else:
            self.output_dir = output_dir
        
        # Initialize interpreter
        self.interpreter = init_code_interpreter(model=model, auto_run=auto_run)
        
        # State variables
        self.darshan_modules: List[str] = []
        self.analysis_messages: Optional[List[Dict]] = None
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
        
        return self.output_dir
    
    def _prepare_interpreter_session(self) -> str:
        """
        Prepare the Open Interpreter session by loading data into the environment.
        
        Returns:
            The setup code that was executed
        """
        print("\nPreparing analysis environment...")
        
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
        
        # Execute the setup code
        self.interpreter.computer.run("python", setup_code, display=True)
        print("✓ Environment prepared")
        
        return setup_code
    
    def analyze(self) -> List[Dict]:
        """
        Analyze the Darshan log using Open Interpreter.
        
        Returns:
            List of analysis messages from the conversation
        """
        print(f"\n{'='*60}")
        print("STEP 2: Analyzing Darshan Log")
        print(f"{'='*60}\n")
        
        # Change to output directory
        original_dir = os.getcwd()
        os.chdir(self.output_dir)
        
        try:
            # Prepare the interpreter session
            setup_code = self._prepare_interpreter_session()
            
            # Create analysis prompt
            prompt = create_darshan_analysis_prompt(
                darshan_modules=self.darshan_modules,
                setup_code=setup_code,
                fs_config_description=self.fs_config_description
            )
            
            print("\nStarting analysis chat...")
            print("-" * 60)
            
            # Run the analysis
            messages = self.interpreter.chat(prompt)
            
            # Save analysis messages
            analysis_file = os.path.join(self.output_dir, "analysis.json")
            with open(analysis_file, "w") as f:
                json.dump(messages, f, indent=4)
            print(f"\n✓ Analysis saved to: {analysis_file}")
            
            self.analysis_messages = messages
            return messages
            
        finally:
            os.chdir(original_dir)
    
    def summarize(self) -> str:
        """
        Generate a summary of the analysis results.
        
        Returns:
            Summary text
        """
        if self.analysis_messages is None:
            raise RuntimeError("Must run analyze() before summarize()")
        
        print(f"\n{'='*60}")
        print("STEP 3: Generating Summary")
        print(f"{'='*60}\n")
        
        # Create summary prompt
        summary_prompt = create_darshan_summary_prompt(self.analysis_messages)
        
        # Generate summary using the interpreter's LLM
        print("Generating summary...")
        messages = self.interpreter.chat(summary_prompt, reset=True)
        
        # Extract the summary from the last message
        summary = messages[-1]["content"] if messages else "No summary generated"
        
        # Save summary
        summary_file = os.path.join(self.output_dir, "summary.txt")
        with open(summary_file, "w") as f:
            f.write(summary)
        print(f"✓ Summary saved to: {summary_file}")
        
        self.summary = summary
        return summary
    
    def run(self) -> Tuple[List[Dict], str]:
        """
        Run the complete analysis pipeline: parse, analyze, and summarize.
        
        Returns:
            Tuple of (analysis_messages, summary)
        """
        self.parse_log()
        self.analyze()
        summary = self.summarize()
        
        print(f"\n{'='*60}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*60}")
        print(f"\nResults saved to: {self.output_dir}")
        print(f"  - Data files: {len(self.darshan_modules)} CSV files + descriptions")
        print(f"  - Analysis: analysis.json")
        print(f"  - Summary: summary.txt")
        
        return self.analysis_messages, summary
    
    def ask_question(self, question: str, load_new_environment: bool = True) -> str:
        """
        Ask a question about the Darshan log data.
        
        Args:
            question: The question to answer
            load_new_environment: Whether to reload the data environment (default: True)
            
        Returns:
            The answer to the question
        """
        original_dir = os.getcwd()
        
        try:
            if load_new_environment:
                # Change to output directory and setup environment
                os.chdir(self.output_dir)
                setup_code = self._prepare_interpreter_session()
                prompt = create_qa_prompt(question, setup_code, new_environment=True)
            else:
                prompt = create_qa_prompt(question, new_environment=False)
            
            # Ask the question
            messages = self.interpreter.chat(prompt)
            
            # Extract the answer
            answer = messages[-1]["content"] if messages else "No answer generated"
            return answer
            
        finally:
            if load_new_environment:
                os.chdir(original_dir)
    
    def get_summary(self) -> Optional[str]:
        """Get the generated summary, if available."""
        return self.summary
    
    def get_analysis_messages(self) -> Optional[List[Dict]]:
        """Get the analysis messages, if available."""
        return self.analysis_messages

