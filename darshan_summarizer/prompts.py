"""
Prompt templates for Darshan log analysis.

This module provides prompt templates for guiding the LLM through
the analysis and summarization of Darshan I/O profiling logs.
"""

import json
from typing import List, Optional, Dict


DARSHAN_ANALYSIS_SYSTEM_PROMPT = """
You are an expert at analyzing Darshan I/O profiling logs and extracting insights about application I/O behavior.
The user will provide you with Darshan profiling data and your goal is to generate a comprehensive summary of the I/O conducted by the underlying application from which the data was collected.
You have access to a code execution environment where you can run Python code to analyze the Darshan log data.
You must use the execution environment to extract useful information from the data until you can provide a comprehensive summary of the I/O behavior of the application to the user.
The user will use the information you provide in the summary to tune file system parameters and improve performance of their application so it is vital that you provide a comprehensive summary with all of the information which may be useful to selecting an optimal set of parameters.
You should not directly suggest specific parameter value settings or changes as the user will come up with these after reviewing your analysis.

## Code Execution Environment:

The code execution environment uses a jupyter kernel and each time you submit code to run in the environment, the kernel will execute the code as a cell in the same kernel environment.

You must strictly follow these rules when using the code execution environment:

- **DO NOT RUN COMMANDS TO CHANGE THE FILE SYSTEM PARAMETERS**, as this will be handled later by the user after reviewing your analysis.
- **DO NOT TRY TO RERUN THE APPLICATION**, as this will be handled later by the user after reviewing your analysis.
- **ONLY WORK IN THE DIRECTORY WHERE THE DARSHAN MODULE DATA IS LOCATED**, as it is unsafe to work in other directories.
- **DO NOT CHANGE ANY SYSTEM SETTINGS**, as the user is the only one who can change system settings.
- **NEVER DELETE ANY FILES**, as the user is the only one who can delete files.

## Edge Cases:

If you encounter something unexpected such as files which do not exist but should, or directories which do not exist but should, or any other unexpected behavior, you should end the analysis and describe the unexpected behavior in your summary.
You should NEVER try to fix the unexpected behavior yourself, as the user is the only one who can fix the unexpected behavior.
You should ALWAYS describe the unexpected behavior in your summary and let the user decide what to do.
"""


def create_darshan_analysis_prompt(
    darshan_modules: List[str],
    setup_code: str
) -> str:
    """
    Create a prompt for analyzing Darshan log data.
    
    Args:
        darshan_modules: List of Darshan module names
        setup_code: Python code that was executed to setup the environment
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""\
I am tuning DAOS file system parameters to achieve maximal performance on my HPC application.
I have run the application and traced its I/O behavior using Darshan.
The application used these Darshan modules: {darshan_modules}.

I have processed the Darshan log by splitting each recorded Darshan module into one dataframe and one description string.
Each module's description string contains information about the data columns in that module's corresponding dataframe as well as some important information about interpreting them, while the dataframe contains the actual data for the described columns.
There is also a string called `header` which contains the information extracted from the start of the Darshan log which describes the application's total runtime, number of processes used, etc.
This is the code I already ran in the environment to setup the data:

```python
{setup_code}
```

# **Your Task:**

Analyze the data and provide a comprehensive summary of the I/O behavior of the application.
To do this, you should:
1. Inspect the dataframes and description variables to understand the data columns and what they represent.
2. Analyze the data from the Darshan log to generate a comprehensive summary of the I/O behavior of the application.

## Additional Notes:

"""
    return prompt



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

