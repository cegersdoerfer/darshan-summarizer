"""
Command-line interface for Darshan log summarization.
"""

import argparse
import sys
import os
from typing import Optional

from .agent import DarshanSummarizerAgent


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Analyze and summarize Darshan I/O profiling logs using LLM-based analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a Darshan log
  darshan-summarizer analyze my_app.darshan
  
  # Analyze with custom output directory
  darshan-summarizer analyze my_app.darshan --output-dir ./results
  
  # Analyze with custom model
  darshan-summarizer analyze my_app.darshan --model openai/gpt-4o
  
  # Just parse the log to CSV (no analysis)
  darshan-summarizer parse my_app.darshan --output-dir ./parsed_data
  
  # Ask a question about a previously analyzed log
  darshan-summarizer question ./darshan_analysis_my_app "What files were accessed?"
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Parse and analyze a Darshan log"
    )
    analyze_parser.add_argument(
        "log_path",
        help="Path to the .darshan log file"
    )
    analyze_parser.add_argument(
        "-o", "--output-dir",
        help="Output directory for analysis results (default: auto-generated)"
    )
    analyze_parser.add_argument(
        "-m", "--model",
        default="openai/gpt-5",
        help="LLM model to use (default: openai/gpt-4o)"
    )
    analyze_parser.add_argument(
        "--skip-summary",
        action="store_true",
        help="Skip generating the summary (only run analysis)"
    )
    
    # Parse command
    parse_parser = subparsers.add_parser(
        "parse",
        help="Parse a Darshan log to CSV files (no analysis)"
    )
    parse_parser.add_argument(
        "log_path",
        help="Path to the .darshan log file"
    )
    parse_parser.add_argument(
        "-o", "--output-dir",
        help="Output directory for CSV files (default: auto-generated)"
    )
    
    # Question command
    question_parser = subparsers.add_parser(
        "question",
        help="Ask a question about a previously analyzed log"
    )
    question_parser.add_argument(
        "analysis_dir",
        help="Path to the analysis directory containing CSV files"
    )
    question_parser.add_argument(
        "question",
        help="Question to ask about the log"
    )
    question_parser.add_argument(
        "-m", "--model",
        default="openai/gpt-4o",
        help="LLM model to use (default: openai/gpt-4o)"
    )
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == "analyze":
            run_analyze(args)
        elif args.command == "parse":
            run_parse(args)
        elif args.command == "question":
            run_question(args)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def run_analyze(args):
    """Run the analyze command."""
    # Verify log file exists
    if not os.path.exists(args.log_path):
        raise FileNotFoundError(f"Log file not found: {args.log_path}")
    
    print("="*70)
    print("DARSHAN LOG SUMMARIZER")
    print("="*70)
    print(f"\nLog file: {args.log_path}")
    print(f"Model: {args.model}")
    print(f"Auto-run: {not args.no_auto_run}")
    print()
    
    # Create agent
    agent = DarshanSummarizerAgent(
        log_path=args.log_path,
        output_dir=args.output_dir,
        model=args.model,
        auto_run=not args.no_auto_run
    )
    
    # Parse the log
    agent.parse_log()
    
    # Run analysis
    agent.analyze()
    
    # Generate summary (unless skipped)
    if not args.skip_summary:
        summary = agent.summarize()
        
        # Display summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70 + "\n")
        print(summary)
    
    print("\n" + "="*70)
    print(f"✓ Complete! Results saved to: {agent.output_dir}")
    print("="*70 + "\n")


def run_parse(args):
    """Run the parse command."""
    from .parser import parse_darshan_log, parse_darshan_to_csv
    
    if not os.path.exists(args.log_path):
        raise FileNotFoundError(f"Log file not found: {args.log_path}")
    
    print("="*70)
    print("DARSHAN LOG PARSER")
    print("="*70)
    print(f"\nLog file: {args.log_path}\n")
    
    # Determine output directory
    if args.output_dir is None:
        log_basename = os.path.basename(args.log_path).replace(".darshan", "")
        output_dir = os.path.join(os.getcwd(), f"darshan_parsed_{log_basename}")
    else:
        output_dir = args.output_dir
    
    # Parse
    log_content, log_filename = parse_darshan_log(args.log_path)
    print(f"Successfully parsed: {log_filename}")
    
    # Convert to CSV
    parse_darshan_to_csv(log_content, output_dir)
    
    print("\n" + "="*70)
    print(f"✓ Complete! CSV files saved to: {output_dir}")
    print("="*70 + "\n")


def run_question(args):
    """Run the question command."""
    if not os.path.exists(args.analysis_dir):
        raise FileNotFoundError(f"Analysis directory not found: {args.analysis_dir}")
    
    print("="*70)
    print("DARSHAN LOG Q&A")
    print("="*70)
    print(f"\nAnalysis directory: {args.analysis_dir}")
    print(f"Question: {args.question}")
    print(f"Model: {args.model}\n")
    
    # Create agent with existing analysis directory
    # We need a dummy log path, so we'll use the first .darshan file in the dir if available
    log_path = os.path.join(args.analysis_dir, "dummy.darshan")
    
    agent = DarshanSummarizerAgent(
        log_path=log_path,
        output_dir=args.analysis_dir,
        model=args.model
    )
    
    # Load modules from the existing directory
    from .parser import list_darshan_modules
    agent.darshan_modules = list_darshan_modules(args.analysis_dir)
    
    print(f"Found {len(agent.darshan_modules)} modules in the analysis directory\n")
    print("-"*70 + "\n")
    
    # Ask the question
    answer = agent.ask_question(args.question, load_new_environment=True)
    
    print("\n" + "="*70)
    print("ANSWER")
    print("="*70 + "\n")
    print(answer)
    print()


if __name__ == "__main__":
    main()

