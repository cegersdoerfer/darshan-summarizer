"""
Prompt templates for Darshan log analysis.

This module provides prompt templates for guiding the LLM through
the analysis and summarization of Darshan I/O profiling logs.
"""

import json
from typing import List, Optional, Dict


ANALYSIS_INSTRUCTION_NOTES = """
Remember:
 - The application code will not be able to be changed, so you must only focus on information which can help to tune the file system parameters to improve performance of the application as it is currently written.
 - **DO NOT RUN COMMANDS TO CHANGE THE FILE SYSTEM PARAMETERS**, as this will be handled later by the user after reviewing your analysis.
 - **DO NOT SUGGEST ANY SPECIFIC COMMANDS TO RUN**, as the user is already an expert in implementing file system configuration changes.
 - **DO NOT CREATE ANY PLOTS OR GRAPHS**.
 - Keep these instructions as part of your plan so you do not forget them later in the analysis process.
"""


def create_darshan_analysis_prompt(
    darshan_modules: List[str],
    setup_code: str,
    fs_config_description: Optional[Dict] = None
) -> str:
    """
    Create a prompt for analyzing Darshan log data.
    
    Args:
        darshan_modules: List of Darshan module names
        setup_code: Python code that was executed to setup the environment
        fs_config_description: Optional description of file system parameters being tuned
        
    Returns:
        Formatted prompt string
    """
    prompt_parts = ["Here is some context before I give you the task:\n"]
    
    # Add tuning config context if provided
    if fs_config_description is not None:
        tuning_config_context = f"""
### **Tuning Configuration:**

I am trying to tune these file system parameters to achieve maximal performance on my HPC application:
```
{json.dumps(fs_config_description, indent=4)}
```
"""
        prompt_parts.append(tuning_config_context)
    
    # Add Darshan modules description
    darshan_modules_description = f"""
### **Darshan Modules:**

In order to decide which parameters to tune and how to tune them, I have run the application and traced its I/O behavior using Darshan. \
The application used these Darshan modules: {darshan_modules}.
"""
    prompt_parts.append(darshan_modules_description)
    
    # Add setup code context
    setup_code_context = f"""
### **Environment Setup:**

I have processed the Darshan log by splitting each recorded Darshan module into one dataframe and one description string. \
Each module's description string contains information about the data columns in that module's corresponding dataframe as well as some important information about interpreting them, while the dataframe contains the actual data for the described columns.\
There is also a string called `header` which contains the information extracted from the start of the Darshan log which describes the application's total runtime, number of processes used, etc.\
This is the code I already ran in the environment to setup the data:

```
{setup_code}
```
"""
    prompt_parts.append(setup_code_context)
    
    # Add task description
    task_description = """
### **Task Description:**

 1) Inspect the dataframes and description variables to understand the data columns and what they represent.
 2) Then, find which unique directories are accessed by the application.
 3) Then, you must analyze the data from the Darshan log to extract the most important information which may help guide me to tune file system parameters to improve performance of the application.

"""
    prompt_parts.append(task_description)
    
    # Add instruction notes
    prompt_parts.append(ANALYSIS_INSTRUCTION_NOTES)
    
    return "\n".join(prompt_parts)


def create_darshan_summary_prompt(analysis_messages: List[Dict]) -> str:
    """
    Create a prompt for summarizing the analysis results.
    
    Args:
        analysis_messages: List of message dictionaries from the analysis chat
        
    Returns:
        Formatted summary prompt string
    """
    # Format the analysis messages as a readable log
    analysis_log = json.dumps(analysis_messages, indent=2)
    
    summary_prompt = f"""
A user has asked an assistant to analyze a darshan log and extract any useful knowledge which may help to tune the file system parameters to improve the performance of the application which was traced using Darshan.
The analysis consists of an initial message from the user detailing the task for the assistant, followed by a series of messages between the assistant and the CLI console where the assistant describes its analysis plan, uses the CLI to run the analysis code, and then interprets the results of the code that was run via the console's output.

Here is the full log of messages documenting the analysis conducted by the assistant:
{analysis_log}


### **Task Description:**

You must review the analysis conducted by the assistant and generate a detailed summary of all of the information the assistant discovered through the analysis process to summarize the detailed I/O behavior of the application.
Your summary should include specific information discovered by the assistant about the application's I/O behavior which may be helpful to tune the file system parameters to improve performance of the application.
"""
    
    return summary_prompt


def create_qa_prompt(question: str, setup_code: Optional[str] = None, new_environment: bool = False) -> str:
    """
    Create a prompt for answering questions about the Darshan log.
    
    Args:
        question: The question to answer
        setup_code: Optional Python setup code (if starting a new environment)
        new_environment: Whether this is a new environment that needs setup
        
    Returns:
        Formatted Q&A prompt string
    """
    if new_environment and setup_code:
        prompt = f"""
I have processed a Darshan I/O profiling log by splitting each recorded Darshan module into one dataframe and one description string. \
Each module's description string contains information about the data columns in that module's corresponding dataframe as well as some important information about interpreting them.
There is also a string called `header` which contains the information extracted from the start of the Darshan log.

This is the code I already ran in the environment to setup the data:

```python
{setup_code}
```

Please answer the following question about the Darshan log data:

{question}
"""
    else:
        prompt = f"""
Please answer the following question about the Darshan log data:

{question}
"""
    
    return prompt

