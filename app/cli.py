import typer
import asyncio
import sys
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import json
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from app.schemas import BriefRequest
from app.graph.workflow import ResearchBriefWorkflow as ResearchWorkflow
from app.services.context_service import ContextService
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize CLI app
app = typer.Typer(help="Context-Aware Research Brief Generator CLI")
console = Console()

# Initialize services
research_workflow = ResearchWorkflow()
context_service = ContextService()

@app.command()
def generate(
    topic: str = typer.Argument(..., help="Research topic"),
    depth: int = typer.Option(3, "--depth", "-d", min=1, max=5, help="Research depth (1-5)"),
    user_id: str = typer.Option("cli_user", "--user-id", "-u", help="User identifier"),
    follow_up: bool = typer.Option(False, "--follow-up", "-f", help="Is this a follow-up query"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
):
    """Generate a research brief for the given topic"""
    
    # Verify API key
    if not os.getenv("GOOGLE_API_KEY"):
        console.print(Panel("[red]Error: GOOGLE_API_KEY environment variable not set[/red]"))
        raise typer.Exit(1)
    
    console.print(f"[bold blue]Generating research brief for:[/bold blue] {topic}")
    console.print(f"[dim]Depth: {depth}, User: {user_id}, Follow-up: {follow_up}[/dim]")
    
    # Create request
    request = BriefRequest(
        topic=topic,
        depth=depth,
        follow_up=follow_up,
        user_id=user_id
    )
    
    # Run the workflow with progress indicator
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Processing research brief...", total=None)
            result = asyncio.run(research_workflow.execute(request))
            progress.remove_task(task)
        
        # Extract final brief
        final_brief = result.get("final_brief")
        if not final_brief:
            error_msg = result.get("error", "Unknown error")
            console.print(f"[red]Error: {error_msg}[/red]")
            raise typer.Exit(1)
        
        # Display results
        display_brief(final_brief, verbose)
        
        # Save to file if requested
        if output_file:
            save_brief_to_file(final_brief, output_file)
            console.print(f"[green]Brief saved to: {output_file}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error generating brief: {str(e)}[/red]")
        raise typer.Exit(1)

def display_brief(brief, verbose: bool = False):
    """Display the research brief in a formatted way"""
    
    # Title
    title_text = Text(brief.topic, style="bold blue")
    console.print(Panel(title_text, title="Research Brief"))
    
    # Executive Summary
    console.print("\n[bold green]Executive Summary[/bold green]")
    console.print(brief.executive_summary)
    
    # Key Findings
    console.print("\n[bold yellow]Key Findings[/bold yellow]")
    for i, finding in enumerate(brief.key_findings, 1):
        console.print(f"{i}. {finding}")
    
    # Recommendations
    console.print("\n[bold cyan]Recommendations[/bold cyan]")
    for i, rec in enumerate(brief.recommendations, 1):
        console.print(f"{i}. {rec}")
    
    if verbose:
        # Detailed Analysis
        console.print("\n[bold magenta]Detailed Analysis[/bold magenta]")
        console.print(brief.detailed_analysis)
        
        # References
        console.print("\n[bold white]References[/bold white]")
        for i, ref in enumerate(brief.references, 1):
            console.print(f"{i}. [link]{ref.title}[/link]")
            console.print(f"   URL: {ref.url}")
            console.print(f"   Summary: {ref.summary}")
            console.print()
    
    # Metadata
    console.print(f"\n[dim]Confidence Level: {brief.confidence_level:.2f}")
    console.print(f"Context Used: {'Yes' if brief.context_used else 'No'}")
    console.print(f"Generated: {brief.generated_at}")

def save_brief_to_file(brief, filename: str):
    """Save the brief to a file"""
    
    # Determine format based on file extension
    if filename.endswith('.json'):
        # Save as JSON
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(brief.model_dump(), f, indent=2, default=str)
    else:
        # Save as text
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# Research Brief: {brief.topic}\n\n")
            f.write(f"**Generated:** {brief.generated_at}\n")
            f.write(f"**Confidence Level:** {brief.confidence_level:.2f}\n")
            f.write(f"**Context Used:** {'Yes' if brief.context_used else 'No'}\n\n")
            
            f.write("## Executive Summary\n\n")
            f.write(f"{brief.executive_summary}\n\n")
            
            f.write("## Key Findings\n\n")
            for i, finding in enumerate(brief.key_findings, 1):
                f.write(f"{i}. {finding}\n")
            f.write("\n")
            
            f.write("## Detailed Analysis\n\n")
            f.write(f"{brief.detailed_analysis}\n\n")
            
            f.write("## Recommendations\n\n")
            for i, rec in enumerate(brief.recommendations, 1):
                f.write(f"{i}. {rec}\n")
            f.write("\n")
            
            f.write("## References\n\n")
            for i, ref in enumerate(brief.references, 1):
                f.write(f"{i}. **{ref.title}**\n")
                f.write(f"   - URL: {ref.url}\n")
                f.write(f"   - Summary: {ref.summary}\n")
                f.write(f"   - Relevance: {ref.relevance}\n\n")

@app.command()
def test():
    """Test the system with a sample request"""
    
    console.print("[bold blue]Running system test...[/bold blue]")
    
    # Test with a simple topic
    test_request = BriefRequest(
        topic="renewable energy trends",
        depth=2,
        follow_up=False,
        user_id="test_user"
    )
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Running test...", total=None)
            result = asyncio.run(research_workflow.execute(test_request))
            progress.remove_task(task)
        
        final_brief = result.get("final_brief")
        if final_brief:
            console.print("[green]✓ System test passed![/green]")
            console.print(f"Generated brief with {len(final_brief.key_findings)} key findings")
            console.print(f"Confidence level: {final_brief.confidence_level:.2f}")
        else:
            console.print("[red]✗ System test failed![/red]")
            console.print(f"Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        console.print(f"[red]✗ System test failed: {str(e)}[/red]")

@app.command()
def history(
    user_id: str = typer.Argument(..., help="User identifier"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed history")
):
    """Show research history for a user"""
    
    try:
        history_summary = context_service.get_user_history_summary(user_id)
        
        console.print(f"[bold blue]Research History for User:[/bold blue] {user_id}")
        console.print(f"[dim]Total Briefs: {history_summary['total_briefs']}[/dim]")
        
        if history_summary['recent_activity']:
            console.print(f"[dim]Last Activity: {history_summary['recent_activity']}[/dim]")
        
        if history_summary['topics']:
            console.print("\n[bold]Recent Topics:[/bold]")
            for i, topic in enumerate(history_summary['topics'][-10:], 1):
                console.print(f"{i:2d}. {topic}")
        
        if detailed and history_summary['total_briefs'] > 0:
            avg_confidence = history_summary['avg_confidence']
            console.print(f"\n[dim]Average Confidence: {avg_confidence:.2f}[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error retrieving history: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command()
def workflow():
    """Display the workflow structure"""
    
    structure = research_workflow.get_workflow_visualization()
    
    panel = Panel(
        structure,
        title="Research Brief Generation Workflow",
        border_style="blue"
    )
    
    console.print(panel)

if __name__ == "__main__":
    app()