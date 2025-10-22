# Darshan Log Summarizer

An intelligent agent for analyzing and summarizing Darshan I/O profiling logs using LLM-based code generation and execution.

## Overview

This tool provides automated, intelligent analysis of Darshan I/O profiling logs. It:

1. **Parses** `.darshan` log files into structured CSV files (one per Darshan module)
2. **Analyzes** the data using Python code generation and execution via LLM producing a summary of the log as output


## Prerequisites

Before using this tool, you must have:

1. **Darshan CLI tools** installed (specifically `darshan-parser`)
   - Installation guide: https://www.mcs.anl.gov/research/projects/darshan/
   
2. **Python 3.8+**

3. **OpenAI API key** (or compatible LLM API)
   - Set as environment variable: `export OPENAI_API_KEY="your-key-here"`

## Installation

### Option 1: Install from source

```bash
git clone https://github.com/yourusername/darshan-log-summarizer.git
cd darshan-log-summarizer
pip install -e .
```

## Usage

### Command-Line Interface

The tool provides three main commands:

#### 1. Analyze a Darshan log

Performs complete analysis: parsing, data analysis, and summary generation.

```bash
python -m darshan_summarizer.main analyze <log_file.darshan>
```

**Options:**
- `-o, --output-dir`: Specify output directory for results
- `-m, --model`: Choose LLM model (default: `openai/gpt-5`)

**Example:**
```bash
python -m darshan_summarizer.main analyze my_app_2024.darshan --output-dir ./results
```

#### 2. Parse a log (without analysis)

Just convert the log to CSV files without running analysis.

```bash
python -m darshan_summarizer.main parse <log_file.darshan>
```

**Example:**
```bash
python -m darshan_summarizer.main parse my_app.darshan -o ./parsed_data
```

#### 3. Ask questions about an analyzed log

Query a previously analyzed log with specific questions.

```bash
python -m darshan_summarizer.main question <analysis_directory> "<your question>"
```

**Example:**
```bash
python -m darshan_summarizer.main question ./results "What are the most frequently accessed files?"
```


