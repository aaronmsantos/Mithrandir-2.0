import os
import sys
from pathlib import Path

# Add project root directory to sys.path to allow execution of scripts directly
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from typing import Any, Dict, List, Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import core functionalities
from core.harness import doctor as harness_doctor
from core.memory.manager import MemoryManager
from core.memory.compactor import MemoryCompactor, _call_llm_api
from core.memory.fenced_context import get_fenced_context

# Import domain modules
from domains.personal import PersonalDomain
from domains.investing import InvestingDomain
from domains.travel import TravelDomain
from domains.work import WorkDomain
from domains.projects import ProjectsDomain
from domains.profile import ProfileDomain

# Initialize Typer and Rich Console
app = typer.Typer(help="🔮 Mithrandir 2.0 Command Line Interface ✨", rich_markup_mode="rich")
console = Console()

def audit_and_confirm(category: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Audits proposed memory entry against L2 Playbook rules and asks user to confirm if drift detected."""
    from core.memory.sentinel import DriftSentinel
    sentinel = DriftSentinel()
    try:
        violations = sentinel.audit_entry(category, content, metadata)
    except Exception as e:
        console.print(f"[dim yellow]⚠️ Sentinel audit check encountered an error: {e}. Proceeding...[/dim yellow]")
        return True

    if not violations:
        return True

    table = Table(show_header=True, header_style="bold red", box=None)
    table.add_column("Rule Violated", style="cyan")
    table.add_column("Justification", style="white")
    table.add_column("Severity", style="yellow")

    for v in violations:
        table.add_row(
            v.get("rule", "Unknown rule"),
            v.get("justification", "No justification provided."),
            v.get("severity", "WARNING")
        )

    console.print(Panel(
        table,
        title="🔮 [bold red]Sentinel Warning: Cognitive Drift Detected[/bold red] 🔮",
        border_style="red"
    ))

    return typer.confirm("Do you want to proceed with storing this entry despite the drift?", default=False)

# Sub-command groups
journal_app = typer.Typer(name="journal", help="📓 Manage your encrypted personal journal entries.")
invest_app = typer.Typer(name="invest", help="📈 Run market analysis using the Confluence Framework.")
memory_app = typer.Typer(name="memory", help="🧠 Memory compaction and maintenance.")
prompt_app = typer.Typer(name="prompt", help="💬 Prompt translation and Machine English optimization.")
travel_app = typer.Typer(name="travel", help="✈️ Track travel itineraries and packing lists.")
work_app = typer.Typer(name="work", help="💼 Track weekly work tasks and deliverables.")
projects_app = typer.Typer(name="projects", help="🚀 Manage AI sprint backlogs and project tasks.")
profile_app = typer.Typer(name="profile", help="🧙‍♂️ Manage your professional history and profile coordinates.")

app.add_typer(journal_app)
app.add_typer(invest_app)
app.add_typer(memory_app)
app.add_typer(prompt_app)
app.add_typer(travel_app)
app.add_typer(work_app)
app.add_typer(projects_app)
app.add_typer(profile_app)


# --- Root Commands ---

@app.command("doctor")
def doctor():
    """🔮 Run Mithrandir 2.0 system diagnostics checker."""
    console.print("[bold cyan]🩺 Initializing Mithrandir 2.0 Doctor...[/bold cyan]")
    harness_doctor()


@app.command("compact")
def compact(
    limit: int = typer.Option(50, help="Number of recent memories to analyze.")
):
    """🧠 Run Mithrandir 2.0 Memory Compaction loop (extracts rules to playbook)."""
    console.print("[bold magenta]⚡️ Launching Memory Compaction loop...[/bold magenta]")
    compactor = MemoryCompactor()
    try:
        updated = compactor.run_compaction(limit=limit)
        console.print(Panel(
            f"🧠 Memory compaction completed successfully.\n[bold green]Playbook topics updated/reconciled:[/bold green] {updated}",
            title="🧠 Compactor Status",
            border_style="magenta",
            expand=False
        ))
    except Exception as e:
        console.print(f"[bold red]❌ Error executing memory compactor: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command("chat")
def chat():
    """💬 Interactive agent-first chat experience with fenced context recall."""
    console.print(Panel(
        "Welcome to the [bold cyan]Mithrandir 2.0 Fenced Context Chat Loop[/bold cyan]! 🤖\n"
        "Ask anything. Mithrandir will query the durable memory layer to find relevant past logs and guidelines,\n"
        "display them in a fenced block, and use them to construct a personalized response.\n\n"
        "Type [bold red]exit[/bold red] or [bold red]quit[/bold red] to end the chat session.",
        title="⚡️ Mithrandir Interactive Chat ⚡️",
        border_style="cyan"
    ))
    
    manager = MemoryManager()
    
    while True:
        try:
            user_input = typer.prompt("You")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold red]Ending chat session. Bye! 👋[/bold red]")
            break
            
        if user_input.strip().lower() in ["exit", "quit"]:
            console.print("[bold red]Ending chat session. Bye! 👋[/bold red]")
            break
            
        if not user_input.strip():
            continue
            
        # 1. Retrieve fenced context
        fenced_context = get_fenced_context(query=user_input)
        
        # 2. Print fenced context block
        console.print(Panel(
            fenced_context,
            title="🔍 Recalled Fenced Context",
            border_style="yellow",
            padding=(1, 2)
        ))
        
        # 3. Generate response using LLM or local fallback
        chat_prompt = f"""You are Mithrandir 2.0, an advanced personal system architect.
Here is the recalled context from our durable memory layer:
{fenced_context}

The user is saying: "{user_input}"

Please provide a helpful, concise, and high-energy response based on the recalled context. Keep it short and to the point.
"""
        console.print("[dim cyan]Mithrandir thinking...[/dim cyan]")
        response_text = _call_llm_api(chat_prompt)
        
        if not response_text:
            response_text = (
                "⚡️ [Mithrandir local mode] I have successfully recalled your context (displayed above) but "
                "no external LLM API keys are configured (or API call timed out). I've securely logged this chat turn!"
            )
            
        console.print(f"[bold green]Mithrandir:[/bold green] {response_text}\n")
        
        # 4. Save conversation turn as chat memory
        chat_turn_content = f"User: {user_input}\nAgent: {response_text}"
        
        # Run non-blocking Sentinel audit
        from core.memory.sentinel import DriftSentinel
        try:
            sentinel = DriftSentinel()
            violations = sentinel.audit_entry("chat", chat_turn_content, {"type": "chat_turn"})
            if violations:
                console.print("\n[bold yellow]🔮 Sentinel: Cognitive drift detected in chat history![/bold yellow]")
                for v in violations:
                    console.print(f"  [cyan]* Rule Violated:[/cyan] {v.get('rule')}")
                    console.print(f"    [dim]Justification:[/dim] {v.get('justification')}")
                console.print("")
        except Exception as e:
            # Silently ignore sentinel check failures in chat loop
            pass
            
        manager.add_memory(
            category="chat",
            content=chat_turn_content,
            metadata={"type": "chat_turn"}
        )


# --- Journal Subcommands ---

@journal_app.command("add")
@journal_app.command("write")
def journal_write(
    content: Optional[str] = typer.Option(None, "--content", "-c", help="Journal entry content"),
    mood: Optional[int] = typer.Option(None, "--mood", "-m", help="Mood score (1-10)"),
):
    """📓 Add a new journal entry (decrypted review in-memory, stored encrypted on disk)."""
    console.print("[bold magenta]📓 Creating a New Journal Entry[/bold magenta]")
    
    if not content:
        content = typer.prompt("What's on your mind? (thoughts/feelings)")
    if not mood:
        while True:
            try:
                mood_input = typer.prompt("Rate your mood (1-10)")
                mood = int(mood_input)
                if 1 <= mood <= 10:
                    break
                console.print("[bold red]Please enter an integer between 1 and 10.[/bold red]")
            except ValueError:
                console.print("[bold red]Invalid input. Please enter an integer between 1 and 10.[/bold red]")

    # Run audit check
    if not audit_and_confirm("journal", content, {"mood_score": mood}):
        console.print("[bold yellow]❌ Aborted journal write to prevent cognitive drift.[/bold yellow]")
        raise typer.Exit(code=1)
    
    # Decrypted/In-memory review
    console.print(Panel(
        f"[bold]Mood Score:[/bold] {mood}/10\n[bold]Content:[/bold] {content}",
        title="🔑 [yellow]In-Memory Plaintext Review (Pre-encryption)[/yellow]",
        border_style="yellow"
    ))
    
    # Save (calling memory manager Fernet encryptor internally)
    personal = PersonalDomain()
    memory_id = personal.add_journal_entry(content=content, mood_score=mood)
    
    console.print(f"[bold green]✨ Success![/bold green] Journal entry safely encrypted and stored (Memory ID: {memory_id}). 🔮")


@journal_app.command("list")
def journal_list(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Optional search string to filter entries")
):
    """📓 List decrypted journal entries (supports filtering by query)."""
    personal = PersonalDomain()
    entries = personal.list_journal_entries(query=query)
    
    if not entries:
        console.print("[bold yellow]No journal entries found matching criteria. 📓[/bold yellow]")
        return
        
    table = Table(title="📓 Decrypted Journal Entries", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan")
    table.add_column("Timestamp", style="green")
    table.add_column("Mood Score", style="yellow")
    table.add_column("Content (Decrypted in Memory)", style="white")
    
    for e in entries:
        mood = e["metadata"].get("mood_score", "N/A")
        table.add_row(
            str(e["id"]),
            e["timestamp"],
            f"{mood}/10",
            e["content"]
        )
    console.print(table)


@journal_app.command("search")
def journal_search(
    query: str = typer.Argument(..., help="Search query to match decrypted content in-memory")
):
    """📓 Search decrypted journal entries for a search term."""
    journal_list(query=query)


# --- Invest Subcommands ---

@invest_app.command("calculate")
def invest_calculate(
    tom_lee: Optional[float] = typer.Option(None, "--tom-lee", help="Tom Lee pivot stance (1-10)"),
    cpi: Optional[float] = typer.Option(None, "--cpi", help="CPI/liquidity trend (1-10)"),
    flows: Optional[float] = typer.Option(None, "--flows", help="ETF flows (1-10)"),
    fintwit: Optional[float] = typer.Option(None, "--fintwit", help="FinTwit velocity (1-10)"),
    cnbc: Optional[float] = typer.Option(None, "--cnbc", help="CNBC amplitude (1-10)"),
    skeptics: Optional[float] = typer.Option(None, "--skeptics", help="Skeptic flow (1-10)"),
    sr: Optional[float] = typer.Option(None, "--sr", help="Support/Resistance alignment (1-10)"),
    momentum: Optional[float] = typer.Option(None, "--momentum", help="Momentum slope (1-10)"),
    volume: Optional[float] = typer.Option(None, "--volume", help="Volume divergence (1-10)"),
):
    """📈 Calculate Confluence Score and save investing recommendation report."""
    console.print("[bold green]📈 Mithrandir Confluence Framework Calculator[/bold green]")
    
    def prompt_score(name: str) -> float:
        while True:
            try:
                val = float(typer.prompt(name))
                if 1.0 <= val <= 10.0:
                    return val
                console.print("[bold red]Score must be between 1.0 and 10.0.[/bold red]")
            except ValueError:
                console.print("[bold red]Please enter a valid number.[/bold red]")

    # Prompt if parameters are missing
    if tom_lee is None:
        console.print("\n[bold cyan]--- Macro Indicators ---[/bold cyan]")
        tom_lee = prompt_score("Tom Lee pivot stance (1-10)")
    if cpi is None:
        cpi = prompt_score("CPI/liquidity trend (1-10)")
    if flows is None:
        flows = prompt_score("ETF flows (1-10)")
        
    if fintwit is None:
        console.print("\n[bold cyan]--- Sentiment Indicators ---[/bold cyan]")
        fintwit = prompt_score("FinTwit velocity (1-10)")
    if cnbc is None:
        cnbc = prompt_score("CNBC amplitude (1-10)")
    if skeptics is None:
        skeptics = prompt_score("Skeptic flow (1-10)")
        
    if sr is None:
        console.print("\n[bold cyan]--- Technical Indicators ---[/bold cyan]")
        sr = prompt_score("Support/Resistance alignment (1-10)")
    if momentum is None:
        momentum = prompt_score("Momentum slope (1-10)")
    if volume is None:
        volume = prompt_score("Volume divergence (1-10)")

    investing = InvestingDomain()
    report = investing.calculate_confluence(
        tom_lee_stance=tom_lee,
        cpi_liquidity=cpi,
        etf_flows=flows,
        fintwit_velocity=fintwit,
        cnbc_amplitude=cnbc,
        skeptic_flow=skeptics,
        sr_alignment=sr,
        momentum_slope=momentum,
        volume_divergence=volume
    )
    
    # Run sentinel audit
    if not audit_and_confirm("investing", report["justification"], report["ratings"]):
        console.print("[bold yellow]❌ Aborted saving confluence report to prevent cognitive drift.[/bold yellow]")
        raise typer.Exit(code=1)
        
    memory_id = investing.save_confluence_report(report)
    
    # Output to Console
    console.print("\n")
    console.print(Panel(
        report["justification"],
        title="📈 Confluence Framework Analysis Results ⚡️",
        border_style="green",
        expand=False
    ))
    console.print(f"[bold green]✨ Success![/bold green] Report saved to SQLite under 'investing' (Memory ID: {memory_id}).\n")


@invest_app.command("list")
def invest_list():
    """📈 List past confluence framework analysis reports."""
    investing = InvestingDomain()
    reports = investing.list_confluence_reports()
    
    if not reports:
        console.print("[bold yellow]No investing confluence reports found. 📈[/bold yellow]")
        return
        
    table = Table(title="📈 Past Confluence Framework Reports", show_header=True, header_style="bold green")
    table.add_column("ID", style="cyan")
    table.add_column("Date", style="green")
    table.add_column("Macro", style="cyan")
    table.add_column("Sentiment", style="magenta")
    table.add_column("Technical", style="blue")
    table.add_column("Confluence Score", style="yellow bold")
    table.add_column("Recommendation", style="white bold")
    
    for r in reports:
        meta = r["metadata"]
        table.add_row(
            str(r["id"]),
            meta.get("date", r["timestamp"]),
            f"{meta.get('macro_score', 0.0):.2f}/10",
            f"{meta.get('sentiment_score', 0.0):.2f}/10",
            f"{meta.get('technical_score', 0.0):.2f}/10",
            f"{meta.get('final_score', 0.0):.2f}/10",
            meta.get("recommendation", "N/A")
        )
    console.print(table)


# --- Memory Subcommands ---

@memory_app.command("compact")
def memory_compact_cmd(
    limit: int = typer.Option(50, help="Number of recent memories to analyze.")
):
    """🧠 Run Mithrandir 2.0 Memory Compaction loop (extracts rules to playbook)."""
    compact(limit=limit)


@memory_app.command("export")
def memory_export():
    """🧠 Export all memories to a timestamped JSON file (ISO-8601 name)."""
    console.print("[bold magenta]⚡️ Exporting memories...[/bold magenta]")
    manager = MemoryManager()
    try:
        export_file = manager.export_memories()
        console.print(f"[bold green]✨ Export complete![/bold green] File written to: [cyan]{export_file}[/cyan]")
    except Exception as e:
        console.print(f"[bold red]❌ Export failed: {e}[/bold red]")
        raise typer.Exit(code=1)


# --- Prompt Subcommands ---

@prompt_app.command("translate")
@prompt_app.command("optimize")
def prompt_optimize(
    raw_instruction: Optional[str] = typer.Option(None, "--text", "-t", help="Raw prompt or instructions to translate")
):
    """💬 Translate raw user input into Machine English for agent-optimal parsing."""
    if not raw_instruction:
        raw_instruction = typer.prompt("Enter raw instructions to translate")
        
    console.print("[bold magenta]⚡️ Translating instruction to Machine English...[/bold magenta]")
    from core.prompt_optimizer import translate_to_machine_english
    
    try:
        optimized = translate_to_machine_english(raw_instruction)
        console.print(Panel(
            optimized,
            title="🦾 [bold green]Machine English Translation[/bold green] 🦾",
            border_style="green",
            padding=(1, 2)
        ))
        
        # Log this translation memory
        manager = MemoryManager()
        manager.add_memory(
            category="prompt_optimization",
            content=f"Raw: {raw_instruction}\nOptimized: {optimized}",
            metadata={"type": "prompt_translation"}
        )
    except Exception as e:
        console.print(f"[bold red]❌ Translation failed: {e}[/bold red]")
        raise typer.Exit(code=1)


# --- Travel Subcommands ---

# --- Travel Subcommands and Helpers ---

def _render_travel_details(data: Dict[str, Any]):
    """Renders structured travel confirmation details nicely in the CLI."""
    details_panel = (
        f"[bold cyan]Type:[/bold cyan] {data.get('type', 'mixed').title()}\n"
        f"[bold cyan]Destination:[/bold cyan] {data.get('destination', 'N/A')}\n"
        f"[bold cyan]Dates:[/bold cyan] {data.get('start_date', 'N/A')} to {data.get('end_date', 'N/A')}\n"
    )
    if data.get("carrier"):
        details_panel += f"[bold cyan]Carrier:[/bold cyan] {data['carrier']}\n"
    if data.get("flight_number"):
        details_panel += f"[bold cyan]Flight Number:[/bold cyan] {data['flight_number']}\n"
    if data.get("hotel_name"):
        details_panel += f"[bold cyan]Lodging / Hotel:[/bold cyan] {data['hotel_name']}\n"
    if data.get("confirmation_code"):
        details_panel += f"[bold cyan]Confirmation Code:[/bold cyan] {data['confirmation_code']}\n"
        
    console.print(Panel(
        details_panel,
        title="✈️ [bold green]Travel Confirmation Details[/bold green] ✈️",
        border_style="green",
        expand=False
    ))
    
    activities = data.get("activities", [])
    if activities:
        console.print("[bold yellow]Enriched Activities (Bourdain Style):[/bold yellow]")
        for act in activities:
            console.print(f"  * {act}")
        console.print("")
        
    packs = data.get("packing_list", [])
    if packs:
        console.print("[bold magenta]Packing List:[/bold magenta]")
        console.print(f"  {', '.join(packs)}\n")


@travel_app.command("add")
def travel_add(
    destination: Optional[str] = typer.Option(None, "--destination", "-d", help="Travel destination"),
    start_date: Optional[str] = typer.Option(None, "--start", help="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
    activities: Optional[str] = typer.Option(None, "--activities", "-a", help="Comma-separated activities"),
    packing_list: Optional[str] = typer.Option(None, "--packing", "-p", help="Comma-separated packing items"),
):
    """✈️ Log a new travel itinerary and packing list."""
    if not destination:
        destination = typer.prompt("Destination")
    if not start_date:
        start_date = typer.prompt("Start Date (YYYY-MM-DD)")
    if not end_date:
        end_date = typer.prompt("End Date (YYYY-MM-DD)")
    if not activities:
        activities = typer.prompt("Activities (comma-separated)")
    if not packing_list:
        packing_list = typer.prompt("Packing list (comma-separated)")

    acts = [x.strip() for x in activities.split(",") if x.strip()]
    packs = [x.strip() for x in packing_list.split(",") if x.strip()]
    
    # Format content for audit
    travel_content = (
        f"Trip Itinerary to {destination} from {start_date} to {end_date}.\n"
        f"Planned Activities: {', '.join(acts)}\n"
        f"Packing List: {', '.join(packs)}"
    )
    travel_metadata = {
        "destination": destination,
        "start_date": start_date,
        "end_date": end_date,
        "activities": acts,
        "packing_list": packs
    }
    
    if not audit_and_confirm("travel", travel_content, travel_metadata):
        console.print("[bold yellow]❌ Aborted saving itinerary to prevent cognitive drift.[/bold yellow]")
        raise typer.Exit(code=1)
        
    travel = TravelDomain()
    memory_id = travel.add_itinerary(destination, start_date, end_date, acts, packs)
    console.print(f"[bold green]✈️ Success![/bold green] Itinerary logged under travel (Memory ID: {memory_id}).")


@travel_app.command("import")
def travel_import(
    file_or_dir: Optional[str] = typer.Argument(None, help="Path to travel confirmation file or directory. If omitted, scans 'data/incoming_travel/'.")
):
    """✈️ Import flight (Delta) and hotel (IHG) confirmations, parse details, and sync to memory."""
    travel = TravelDomain()
    
    if file_or_dir:
        path = Path(file_or_dir)
        if not path.exists():
            console.print(f"[bold red]❌ Path not found at: {path}[/bold red]")
            raise typer.Exit(code=1)
            
        if path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                
            parsed = travel.parse_travel_confirmation(content)
            
            # Format text representation for Sentinel checks
            type_str = parsed["type"].title()
            details = []
            if parsed.get("carrier"):
                details.append(f"Carrier: {parsed['carrier']}")
            if parsed.get("flight_number"):
                details.append(f"Flight #: {parsed['flight_number']}")
            if parsed.get("hotel_name"):
                details.append(f"Lodging: {parsed['hotel_name']}")
            if parsed.get("confirmation_code"):
                details.append(f"Confirmation Code: {parsed['confirmation_code']}")
                
            travel_content = (
                f"Parsed {type_str} Travel Confirmation for {parsed['destination']}.\n"
                f"Dates: {parsed['start_date']} to {parsed['end_date']}\n"
                f"{', '.join(details)}"
            )
            
            # Run Sentinel audit check before storing
            if not audit_and_confirm("travel", travel_content, {"type": "travel_confirmation", "parsed_data": parsed}):
                console.print("[bold yellow]❌ Aborted travel import to prevent cognitive drift.[/bold yellow]")
                raise typer.Exit(code=1)
                
            try:
                memory_id = travel.import_confirmation_file(path)
                console.print(f"[bold green]✨ Success![/bold green] Travel confirmation safely imported (Memory ID: {memory_id}). 🔮")
                
                # Show parsed details
                _render_travel_details(travel.manager.get_memory(memory_id)["metadata"]["parsed_data"])
            except Exception as e:
                console.print(f"[bold red]❌ Import failed: {e}[/bold red]")
                raise typer.Exit(code=1)
                
        else: # is directory
            console.print(f"[bold magenta]⚡️ Scanning directory [cyan]{path}[/cyan] for travel confirmations...[/bold magenta]")
            ids = travel.import_confirmation_files(path)
            if ids:
                console.print(f"[bold green]✨ Success![/bold green] Successfully imported {len(ids)} travel confirmations.")
            else:
                console.print("[bold yellow]No confirmation files found to process. ✈️[/bold yellow]")
    else:
        # Default directory scan
        workspace_dir = Path(__file__).resolve().parent
        incoming_dir = workspace_dir / "data" / "incoming_travel"
        console.print(f"[bold magenta]⚡️ Scanning default incoming directory [cyan]{incoming_dir}[/cyan]...[/bold magenta]")
        ids = travel.import_confirmation_files(incoming_dir)
        if ids:
            console.print(f"[bold green]✨ Success![/bold green] Successfully imported {len(ids)} travel confirmations.")
        else:
            console.print("[bold yellow]No confirmation files found in default incoming directory. ✈️[/bold yellow]")


@travel_app.command("list")
def travel_list():
    """✈️ List logged travel itineraries."""
    travel = TravelDomain()
    trips = travel.list_itineraries()
    
    if not trips:
        console.print("[bold yellow]No travel itineraries found. ✈️[/bold yellow]")
        return
        
    table = Table(title="✈️ Logged Travel Itineraries", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="cyan")
    table.add_column("Destination", style="white bold")
    table.add_column("Dates", style="green")
    table.add_column("Details", style="cyan")
    table.add_column("Activities", style="magenta")
    table.add_column("Packing List", style="yellow")
    
    for t in trips:
        meta = t["metadata"]
        parsed = meta.get("parsed_data", {})
        
        # Details summary
        details_list = []
        if parsed:
            if parsed.get("carrier"):
                details_list.append(f"Carrier: {parsed['carrier']}")
            if parsed.get("flight_number"):
                details_list.append(f"Flight #: {parsed['flight_number']}")
            if parsed.get("hotel_name"):
                details_list.append(f"Hotel: {parsed['hotel_name']}")
            if parsed.get("confirmation_code"):
                details_list.append(f"Code: {parsed['confirmation_code']}")
        else:
            # Fallback for manual itineraries
            pass
            
        details_str = "\n".join(details_list) if details_list else "Manual Entry"
        
        dest = meta.get("destination") or parsed.get("destination", "N/A")
        start = meta.get("start_date") or parsed.get("start_date", "N/A")
        end = meta.get("end_date") or parsed.get("end_date", "N/A")
        acts = meta.get("activities") or parsed.get("activities", [])
        packs = meta.get("packing_list") or parsed.get("packing_list", [])
        
        table.add_row(
            str(t["id"]),
            dest,
            f"{start} to {end}",
            details_str,
            ", ".join(acts),
            ", ".join(packs)
        )
    console.print(table)



# --- Work Subcommands ---

@work_app.command("add")
def work_add(
    task: Optional[str] = typer.Option(None, "--task", "-t", help="Task name"),
    desc: Optional[str] = typer.Option(None, "--desc", "-d", help="Task description"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Task status (Todo, In Progress, Done)"),
    due: Optional[str] = typer.Option(None, "--due", help="Due date (YYYY-MM-DD)"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="Priority (High, Medium, Low)"),
):
    """💼 Log a new weekly work task or deliverable."""
    if not task:
        task = typer.prompt("Task Name")
    if not desc:
        desc = typer.prompt("Description")
    if not status:
        status = typer.prompt("Status (Todo/In Progress/Done)")
    if not due:
        due = typer.prompt("Due Date (YYYY-MM-DD)")
    if not priority:
        priority = typer.prompt("Priority (High/Medium/Low)")

    work_content = (
        f"Work Task: {task} (Priority: {priority}, Status: {status})\n"
        f"Description: {desc}\n"
        f"Due Date: {due}"
    )
    work_metadata = {
        "task_name": task,
        "description": desc,
        "status": status,
        "due_date": due,
        "priority": priority
    }
    
    if not audit_and_confirm("work", work_content, work_metadata):
        console.print("[bold yellow]❌ Aborted saving work task to prevent cognitive drift.[/bold yellow]")
        raise typer.Exit(code=1)

    work = WorkDomain()
    memory_id = work.add_task(task, desc, status, due, priority)
    console.print(f"[bold green]💼 Success![/bold green] Work task logged (Memory ID: {memory_id}).")


@work_app.command("list")
def work_list():
    """💼 List logged work tasks."""
    work = WorkDomain()
    tasks = work.list_tasks()
    
    if not tasks:
        console.print("[bold yellow]No work tasks found. 💼[/bold yellow]")
        return
        
    table = Table(title="💼 Weekly Work Tasks", show_header=True, header_style="bold blue")
    table.add_column("ID", style="cyan")
    table.add_column("Task Name", style="white bold")
    table.add_column("Priority", style="magenta")
    table.add_column("Status", style="yellow")
    table.add_column("Due Date", style="green")
    table.add_column("Description", style="dim white")
    
    for t in tasks:
        meta = t["metadata"]
        table.add_row(
            str(t["id"]),
            meta.get("task_name", "N/A"),
            meta.get("priority", "N/A"),
            meta.get("status", "N/A"),
            meta.get("due_date", "N/A"),
            meta.get("description", "")
        )
    console.print(table)


# --- Projects Subcommands ---

@projects_app.command("add")
def projects_add(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
    task: Optional[str] = typer.Option(None, "--task", "-t", help="Task name"),
    complexity: Optional[str] = typer.Option(None, "--complexity", "-c", help="Complexity estimation (XS, S, M, L, XL)"),
    desc: Optional[str] = typer.Option(None, "--desc", "-d", help="Task description"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Task status"),
):
    """🚀 Log a new AI project sprint backlog task."""
    if not project:
        project = typer.prompt("Project Name")
    if not task:
        task = typer.prompt("Task Name")
    if not complexity:
        complexity = typer.prompt("Complexity (XS/S/M/L/XL)")
    if not desc:
        desc = typer.prompt("Description")
    if not status:
        status = typer.prompt("Status")

    project_content = (
        f"Project: {project} | Task: {task}\n"
        f"Complexity: {complexity} | Status: {status}\n"
        f"Description: {desc}"
    )
    project_metadata = {
        "project_name": project,
        "task_name": task,
        "complexity": complexity,
        "description": desc,
        "status": status
    }
    
    if not audit_and_confirm("projects", project_content, project_metadata):
        console.print("[bold yellow]❌ Aborted saving project task to prevent cognitive drift.[/bold yellow]")
        raise typer.Exit(code=1)

    projects = ProjectsDomain()
    memory_id = projects.add_project_task(project, task, complexity, desc, status)
    console.print(f"[bold green]🚀 Success![/bold green] AI sprint task logged (Memory ID: {memory_id}).")


@projects_app.command("list")
def projects_list():
    """🚀 List logged AI project sprint tasks."""
    projects = ProjectsDomain()
    tasks = projects.list_project_tasks()
    
    if not tasks:
        console.print("[bold yellow]No AI project tasks found. 🚀[/bold yellow]")
        return
        
    table = Table(title="🚀 AI Project Backlog Tasks", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan")
    table.add_column("Project", style="cyan bold")
    table.add_column("Task Name", style="white bold")
    table.add_column("Complexity", style="yellow")
    table.add_column("Status", style="magenta")
    table.add_column("Description", style="dim white")
    
    for t in tasks:
        meta = t["metadata"]
        table.add_row(
            str(t["id"]),
            meta.get("project_name", "N/A"),
            meta.get("task_name", "N/A"),
            meta.get("complexity", "N/A"),
            meta.get("status", "N/A"),
            meta.get("description", "")
        )
    console.print(table)

# --- Profile Helper and Subcommands ---

def _render_structured_profile(data: Dict[str, Any]):
    """Renders a structured profile JSON beautifully with Rich."""
    console.print("\n")
    console.print(Panel(
        f"[bold cyan]Name:[/bold cyan] {data.get('name', 'N/A')}\n"
        f"[bold cyan]Headline:[/bold cyan] {data.get('headline', 'N/A')}\n\n"
        f"[bold cyan]Summary:[/bold cyan]\n{data.get('summary', 'N/A')}",
        title="🧙‍♂️ [bold magenta]Profile Overview[/bold magenta] ✨",
        border_style="magenta",
        expand=False
    ))
    
    # Render Experience Table
    experience = data.get("experience", [])
    if experience:
        table = Table(title="💼 Professional Experience", show_header=True, header_style="bold green")
        table.add_column("Role", style="white bold")
        table.add_column("Company", style="cyan")
        table.add_column("Period", style="green")
        table.add_column("Description", style="dim white")
        
        for exp in experience:
            table.add_row(
                exp.get("role", "N/A"),
                exp.get("company", "N/A"),
                exp.get("period", "N/A"),
                exp.get("description", "")
            )
        console.print(table)
        
    # Render Education Table
    education = data.get("education", [])
    if education:
        table_edu = Table(title="🎓 Education", show_header=True, header_style="bold blue")
        table_edu.add_column("School", style="white bold")
        table_edu.add_column("Degree/Field", style="cyan")
        table_edu.add_column("Period", style="green")
        
        for edu in education:
            degree_field = []
            if edu.get("degree"):
                degree_field.append(edu["degree"])
            if edu.get("field"):
                degree_field.append(edu["field"])
            table_edu.add_row(
                edu.get("school", "N/A"),
                " - ".join(degree_field) if degree_field else "N/A",
                edu.get("period", "N/A")
            )
        console.print(table_edu)
        
    # Render Skills & Languages
    skills = data.get("skills", [])
    languages = data.get("languages", [])
    
    if skills or languages:
        skills_text = ", ".join(skills) if skills else "None"
        langs_text = ", ".join(languages) if languages else "None"
        
        console.print(Panel(
            f"[bold yellow]Skills:[/bold yellow] {skills_text}\n\n"
            f"[bold magenta]Languages:[/bold magenta] {langs_text}",
            title="🪄 [bold yellow]Skills & Languages[/bold yellow] 🪄",
            border_style="yellow",
            expand=False
        ))


@profile_app.command("import")
def profile_import(
    file: str = typer.Argument(..., help="Path to the professional history text/markdown file"),
    linkedin: bool = typer.Option(False, "--linkedin", "-l", help="Process as structured LinkedIn profile")
):
    """🧙‍♂️ Import your professional history from a text/markdown file."""
    file_path = Path(file)
    console.print(f"[bold magenta]⚡️ Importing professional profile from [cyan]{file_path}[/cyan]...[/bold magenta]")
    
    profile = ProfileDomain()
    
    try:
        if not file_path.exists():
            console.print(f"[bold red]❌ File not found at: {file_path}[/bold red]")
            raise typer.Exit(code=1)
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Run Sentinel audit check before importing
        if not audit_and_confirm("profile", content, {"source_file": file_path.name, "is_linkedin": linkedin}):
            console.print("[bold yellow]❌ Aborted profile import to prevent cognitive drift.[/bold yellow]")
            raise typer.Exit(code=1)
            
        memory_id = profile.import_profile(file_path=file_path, is_linkedin=linkedin)
        console.print(f"[bold green]✨ Success![/bold green] Professional history safely imported (Memory ID: {memory_id}). 🔮")
        
        if linkedin:
            latest = profile.get_latest_profile()
            if latest and latest.get("metadata", {}).get("parsed"):
                _render_structured_profile(latest["metadata"]["profile_data"])
    except Exception as e:
        console.print(f"[bold red]❌ Import failed: {e}[/bold red]")
        raise typer.Exit(code=1)


@profile_app.command("import-linkedin")
def profile_import_linkedin(
    file: Optional[str] = typer.Argument(None, help="Path to the LinkedIn profile text/markdown/HTML file. If omitted, you will be prompted to paste content.")
):
    """🧙‍♂️ Import and structure your LinkedIn professional history."""
    profile = ProfileDomain()
    
    content = ""
    source_name = "direct_input"
    
    if file:
        file_path = Path(file)
        if not file_path.exists():
            console.print(f"[bold red]❌ File not found at: {file_path}[/bold red]")
            raise typer.Exit(code=1)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        source_name = file_path.name
    else:
        console.print("[bold magenta]🔮 Paste your raw copy-pasted LinkedIn profile text below. Press Ctrl-D (Mac/Linux) or Ctrl-Z (Windows) followed by Enter when done: [/bold magenta]")
        import sys
        content = sys.stdin.read().strip()
        
    if not content:
        console.print("[bold red]❌ No content provided.[/bold red]")
        raise typer.Exit(code=1)
        
    # Run Sentinel audit check before importing
    if not audit_and_confirm("profile", content, {"source_file": source_name, "type": "linkedin_profile"}):
        console.print("[bold yellow]❌ Aborted profile import to prevent cognitive drift.[/bold yellow]")
        raise typer.Exit(code=1)
        
    console.print("[bold cyan]🧙‍♂️ Parsing LinkedIn profile content...[/bold cyan]")
    
    try:
        memory_id = profile.import_profile(raw_content=content, is_linkedin=True)
        console.print(f"[bold green]✨ Success![/bold green] LinkedIn profile successfully parsed, imported, and synced with Agent.MD (Memory ID: {memory_id}). 🔮")
        
        # Display the parsed summary immediately
        latest = profile.get_latest_profile()
        if latest and latest.get("metadata", {}).get("parsed"):
            _render_structured_profile(latest["metadata"]["profile_data"])
    except Exception as e:
        console.print(f"[bold red]❌ Import failed: {e}[/bold red]")
        raise typer.Exit(code=1)


@profile_app.command("show")
def profile_show():
    """🧙‍♂️ Display your current imported professional history."""
    profile = ProfileDomain()
    latest = profile.get_latest_profile()
    
    if not latest:
        console.print("[bold yellow]No professional history imported yet. Use 'profile import-linkedin' or 'profile import [file]' first. 🧙‍♂️[/bold yellow]")
        return
        
    meta = latest.get("metadata", {})
    if meta.get("parsed") and "profile_data" in meta:
        _render_structured_profile(meta["profile_data"])
    else:
        console.print(Panel(
            latest["content"],
            title=f"🧙‍♂️ Professional History (Imported: {latest['timestamp']}) ✨",
            border_style="magenta",
            expand=False
        ))



# --- Run Command (Interactive Router) ---

@app.command("run")
def run(
    domain: str = typer.Argument(..., help="Domain to run: travel, work, or projects")
):
    """🔮 Run interactive CLI loops for travel, work, or projects."""
    dom = domain.strip().lower()
    
    if dom == "travel":
        console.print(Panel("✈️ [bold cyan]Travel Domain Interactive Console[/bold cyan] ✈️", border_style="cyan"))
        choice = typer.prompt("Select action: [1] Add Itinerary, [2] List Itineraries, [3] Exit")
        if choice == "1":
            travel_add()
        elif choice == "2":
            travel_list()
        else:
            console.print("[yellow]Exited Travel loop.[/yellow]")
            
    elif dom == "work":
        console.print(Panel("💼 [bold blue]Work Domain Interactive Console[/bold blue] 💼", border_style="blue"))
        choice = typer.prompt("Select action: [1] Add Work Task, [2] List Work Tasks, [3] Exit")
        if choice == "1":
            work_add()
        elif choice == "2":
            work_list()
        else:
            console.print("[yellow]Exited Work loop.[/yellow]")
            
    elif dom == "projects":
        console.print(Panel("🚀 [bold magenta]Projects Domain Interactive Console[/bold magenta] 🚀", border_style="magenta"))
        choice = typer.prompt("Select action: [1] Add Project Task, [2] List Project Tasks, [3] Exit")
        if choice == "1":
            projects_add()
        elif choice == "2":
            projects_list()
        else:
            console.print("[yellow]Exited Projects loop.[/yellow]")
            
    else:
        console.print(f"[bold red]Unknown domain '{domain}'. Please use 'travel', 'work', or 'projects'.[/bold red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
