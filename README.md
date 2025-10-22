# Darshan Log Summarizer

An intelligent agent for analyzing and summarizing Darshan I/O profiling logs using LLM-based code generation and execution.

## Overview

This tool uses [Open Interpreter](https://github.com/KillianLucas/open-interpreter) to provide automated, intelligent analysis of Darshan I/O profiling logs. It:

1. **Parses** `.darshan` log files into structured CSV files (one per Darshan module)
2. **Analyzes** the data using Python code generation and execution via LLM
3. **Summarizes** the I/O behavior insights to help guide file system parameter tuning

## Features

- 🔍 **Automatic Log Parsing**: Converts Darshan logs to CSV format with module descriptions
- 🤖 **AI-Powered Analysis**: Uses Open Interpreter to write and execute Python code for data analysis
- 📊 **Comprehensive Insights**: Extracts key I/O patterns, file access behavior, and performance metrics
- 💬 **Interactive Q&A**: Ask questions about analyzed logs
- 🎯 **Tuning Guidance**: Focuses on actionable insights for file system parameter optimization

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

### Option 2: Install dependencies directly

```bash
pip install -r requirements.txt
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
- `-m, --model`: Choose LLM model (default: `openai/gpt-4o`)
- `--no-auto-run`: Require manual approval before running generated code
- `--skip-summary`: Skip summary generation (only run analysis)

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

### Python API

You can also use the tool programmatically:

```python
from darshan_summarizer import DarshanSummarizerAgent

# Create an agent
agent = DarshanSummarizerAgent(
    log_path="my_app.darshan",
    output_dir="./analysis_results",
    model="openai/gpt-4o"
)

# Run complete analysis
analysis_messages, summary = agent.run()

# Access results
print(summary)

# Ask follow-up questions
answer = agent.ask_question("What directories were accessed the most?")
print(answer)
```

### Just Parsing (No LLM)

If you only want to parse logs without analysis:

```python
from darshan_summarizer import parse_darshan_log, parse_darshan_to_csv

# Parse the log
log_content, log_filename = parse_darshan_log("my_app.darshan")

# Convert to CSV files
parse_darshan_to_csv(log_content, "./output_dir")
```

## Output Structure

After running analysis, the output directory contains:

```
darshan_analysis_<log_name>/
├── header.txt                    # Log header with metadata
├── <module_name>.csv             # Data for each Darshan module
├── <module_name>_description.txt # Column descriptions for each module
├── analysis.json                 # Full analysis conversation log
└── summary.txt                   # Human-readable summary
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_API_BASE`: Custom API endpoint (optional, for OpenAI-compatible APIs)

### Model Selection

You can use different models by specifying the `--model` flag:

```bash
# OpenAI models
--model openai/gpt-4o
--model openai/gpt-4-turbo

# Other providers (if configured)
--model anthropic/claude-3-opus
--model groq/llama-3-70b
```

See [Open Interpreter documentation](https://docs.openinterpreter.com/language-model-setup) for more model options.

## How It Works

### 1. Log Parsing

The tool uses `darshan-parser` to convert binary Darshan logs into text format, then parses the output into:
- **CSV files**: One per Darshan module (POSIX, MPI-IO, STDIO, etc.)
- **Description files**: Explain what each counter/column means
- **Header file**: Contains application metadata

### 2. Analysis

Using Open Interpreter, the agent:
1. Loads all module data into Pandas DataFrames
2. Generates and executes Python code to analyze the data
3. Extracts insights about:
   - File access patterns
   - I/O volume and operations
   - Directory usage
   - Performance characteristics
   - Potential optimization opportunities

### 3. Summarization

The analysis messages are passed to an LLM to generate a concise, actionable summary focused on:
- Key I/O behaviors
- Performance bottlenecks
- File system tuning recommendations

## Examples

### Example 1: Basic Analysis

```bash
python -m darshan_summarizer.main analyze /path/to/app.darshan
```

### Example 2: Analysis with Custom Output

```bash
python -m darshan_summarizer.main analyze app.darshan \
  --output-dir ./my_analysis \
  --model openai/gpt-4o
```

### Example 3: Parse Only

```bash
python -m darshan_summarizer.main parse app.darshan -o ./parsed
```

### Example 4: Interactive Q&A

```bash
# First analyze
python -m darshan_summarizer.main analyze app.darshan -o ./results

# Then ask questions
python -m darshan_summarizer.main question ./results \
  "What percentage of I/O operations were sequential?"
```

### Example 5: Programmatic Usage

```python
from darshan_summarizer import DarshanSummarizerAgent

agent = DarshanSummarizerAgent(
    log_path="simulation_run.darshan",
    fs_config_description={
        "stripe_size": "Lustre stripe size in MB",
        "stripe_count": "Number of OSTs to stripe across"
    }
)

# Run analysis
analysis, summary = agent.run()

# Get specific insights
q1 = agent.ask_question("What is the average file size accessed?")
q2 = agent.ask_question("How many unique files were opened?")
q3 = agent.ask_question("What is the read/write ratio?")

print(f"Q1: {q1}")
print(f"Q2: {q2}")
print(f"Q3: {q3}")
```

## Troubleshooting

### `darshan-parser: command not found`

Make sure Darshan is installed and in your PATH:
```bash
which darshan-parser
```

If not installed, follow the [Darshan installation guide](https://www.mcs.anl.gov/research/projects/darshan/docs/darshan-runtime.html).

### `OpenAI API key not found`

Set your API key:
```bash
export OPENAI_API_KEY="sk-..."
```

### Memory issues with large logs

For very large logs, consider:
- Using a model with a larger context window
- Analyzing specific modules separately
- Increasing available system memory

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Citation

If you use this tool in your research, please cite:

```bibtex
@software{darshan_log_summarizer,
  title={Darshan Log Summarizer: AI-Powered HPC I/O Analysis},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/darshan-log-summarizer}
}
```

## Acknowledgments

- [Darshan](https://www.mcs.anl.gov/research/projects/darshan/) - HPC I/O characterization tool
- [Open Interpreter](https://github.com/KillianLucas/open-interpreter) - Natural language interface to computers

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact: your.email@example.com

