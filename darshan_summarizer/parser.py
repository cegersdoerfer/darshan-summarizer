"""
Darshan log parsing utilities.

This module provides functions to parse Darshan I/O profiling logs and convert them
into structured CSV files for analysis.
"""

import pandas as pd
from tqdm import tqdm
import re
import os
import subprocess
from typing import Optional, List, Tuple, Dict


SKIP_LINES = [
    "# *WARNING*: The POSIX module contains incomplete data!",
    "#            This happens when a module runs out of",
    "#            memory to store new record data.",
    "# To avoid this error, consult the darshan-runtime",
    "# documentation and consider setting the",
    "# DARSHAN_EXCLUDE_DIRS environment variable to prevent",
    "# Darshan from instrumenting unecessary files.",
]


def parse_darshan_log(log_path: str) -> Tuple[str, str]:
    """
    Parse a Darshan log file using darshan-parser.
    
    Args:
        log_path: Path to the .darshan log file
        
    Returns:
        Tuple of (log_content, log_filename)
        
    Raises:
        FileNotFoundError: If the log file doesn't exist
        subprocess.CalledProcessError: If darshan-parser fails
    """
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Darshan log file not found: {log_path}")
    
    if not log_path.endswith(".darshan"):
        raise ValueError("Log file must have .darshan extension")
    
    # Create a temporary txt file with parsed contents
    txt_file = log_path.replace(".darshan", "_parsed.txt")
    
    print(f"Parsing Darshan log file: {log_path}")
    command = f"darshan-parser --show-incomplete {log_path} > {txt_file}"
    
    try:
        subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"darshan-parser failed: {e.stderr}")
    
    # Read the parsed content
    with open(txt_file, "r") as f:
        log_content = f.read()
    
    # Clean up the temporary file
    os.remove(txt_file)
    
    return log_content, os.path.basename(log_path)


def extract_header(log_data: str) -> str:
    """
    Extract the header section from parsed Darshan log data.
    
    The header contains metadata about the application run (name, runtime, processes, etc.)
    
    Args:
        log_data: Parsed Darshan log content
        
    Returns:
        Header text as a string
    """
    header_text = ""
    for line in log_data.splitlines():
        if "log file regions" in line:
            break
        header_text += line + "\n"
    return header_text


def extract_modules(log_data: str) -> Dict:
    """
    Extract module data from parsed Darshan log.
    
    Args:
        log_data: Parsed Darshan log content
        
    Returns:
        Dictionary mapping module names to their data, columns, and descriptions
    """
    modules = {}
    module = None
    in_module = False
    current_description = []
    
    for line in tqdm(log_data.splitlines(), desc="Extracting modules"):
        if line in SKIP_LINES:
            continue
            
        # If we find a module header, start collecting description
        if "module data" in line:
            current_description = []
            continue
            
        # If we hit the column definitions, we're done with description
        elif line.startswith("#<module>"):
            column_names = re.findall(r'<(.*?)>', line)
            # Replace spaces in column names with underscores
            column_names = [name.replace(" ", "_") for name in column_names]
            in_module = True
            continue
            
        # Collect all comment lines as description
        elif line.startswith("#") and not in_module:
            current_description.append(line)
            
        elif in_module:
            if not line.strip():  # Empty line signifies end of module data
                in_module = False
                module = None
            else:
                fields = line.split()
                if not module:
                    module = fields[0]  # First field is the module name
                    modules[module] = {
                        'columns': column_names,
                        'data': [],
                        'description': '\n'.join(current_description)
                    }
                modules[module]['data'].append(fields)
    
    return modules


def parse_darshan_to_csv(log_content: str, output_dir: str) -> None:
    """
    Parse Darshan log content and save to CSV files.
    
    Creates one CSV file per module plus description files and a header file.
    
    Args:
        log_content: Parsed Darshan log content
        output_dir: Directory to save CSV files and descriptions
    """
    if not log_content:
        raise ValueError("No data found in the log content")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract modules and header
    print("Parsing Darshan log content...")
    modules = extract_modules(log_content)
    header = extract_header(log_content)
    
    # Save header
    header_path = os.path.join(output_dir, "header.txt")
    with open(header_path, "w") as f:
        f.write(header)
    print(f"Saved header to {header_path}")
    
    # Process each module
    for module_name, module_data in modules.items():
        print(f"Processing module: {module_name}")
        
        description = module_data["description"]
        columns = module_data["columns"]
        rows = module_data["data"]
        
        # Create DataFrame
        df = pd.DataFrame(rows, columns=columns)
        
        # Pivot table to get counters as columns
        index_columns = [col for col in columns if col not in ['counter', 'value']]
        df = df.pivot_table(
            index=index_columns, 
            columns='counter', 
            values='value', 
            aggfunc='first'
        ).reset_index()
        
        # Save data and description
        data_path = os.path.join(output_dir, f"{module_name}.csv")
        desc_path = os.path.join(output_dir, f"{module_name}_description.txt")
        
        df.to_csv(data_path, index=False)
        with open(desc_path, "w") as f:
            f.write(description)
        
        print(f"  ✓ Saved data to {data_path}")
        print(f"  ✓ Saved description to {desc_path}")
    
    print(f"\nSuccessfully parsed {len(modules)} modules to {output_dir}")


def list_darshan_modules(analysis_dir: str) -> List[str]:
    """
    List all Darshan modules in an analysis directory.
    
    Args:
        analysis_dir: Directory containing parsed CSV files
        
    Returns:
        List of module names
    """
    modules = []
    for file in os.listdir(analysis_dir):
        if file.endswith(".csv"):
            module_name = file.replace(".csv", "")
            modules.append(module_name)
    return modules

