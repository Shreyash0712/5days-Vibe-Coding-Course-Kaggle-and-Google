from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.json import JSON

console = Console()

def print_success(message: str, data: dict):
    """Prints a beautiful success box with the JSON response."""
    # Create the title
    title = Text("Pub/Sub Event Sent ", style="bold green on black")
    
    # Format the message
    msg_text = Text(f"\n{message}\n", style="bold cyan")
    
    # Create a nice rendering of the JSON payload
    json_render = JSON.from_data(data)
    
    # Combine them
    content = msg_text
    
    # Create the panel (Python's equivalent of boxen)
    panel = Panel(
        json_render,
        title=title,
        border_style="green",
        padding=(1, 2)
    )
    
    console.print()
    console.print(panel)
    console.print()

def print_error(message: str, error_detail: str):
    """Prints a beautiful error box."""
    title = Text(" ❌ Error ", style="bold red on black")
    
    msg_text = Text(f"{message}\n\n", style="bold red")
    detail_text = Text(error_detail, style="dim yellow")
    
    msg_text.append(detail_text)
    
    panel = Panel(
        msg_text,
        title=title,
        border_style="red",
        padding=(1, 2)
    )
    
    console.print()
    console.print(panel)
    console.print()
