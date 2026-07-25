"""CLI commands for wallet and agent management on Arc."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Wallet and economic agent management for Arc.")
job_app = typer.Typer(help="ERC-8183 job marketplace: create, accept, deliver, settle.")
app.add_typer(job_app, name="job")
console = Console()


@app.command(name="create-wallet")
def create_wallet() -> None:
    """
    Create a new EVM wallet and display its address and private key.

    The private key is shown ONCE. Store it in a safe place.
    """
    from arc_devkit.core.wallet import create_wallet as _criar

    carteira = _criar()

    console.print(
        Panel(
            f"[bold green]✓ New wallet created![/bold green]\n\n"
            f"  [bold]Address:[/bold]\n"
            f"  [cyan]{carteira['address']}[/cyan]\n\n"
            f"  [bold]Private Key:[/bold]\n"
            f"  [dim]{carteira['private_key']}[/dim]\n\n"
            "[bold red]⚠ WARNING:[/bold red] Private key shown only once.\n"
            "Store it securely. Never share or commit to git.",
            title="[bold green]New Arc Wallet[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )


@app.command()
def balance(
    address: str = typer.Argument(..., help="EVM address to query."),
) -> None:
    """Display the balance of an Arc wallet."""
    from arc_devkit.core.wallet import get_balance

    with console.status("[bold]Fetching balance...[/bold]", spinner="dots"):
        resultado = get_balance(address)

    console.print(f"\n  [bold]Wallet:[/bold] [cyan]{resultado['address']}[/cyan]")
    console.print(f"  [bold]Balance:[/bold] [green]{resultado['balance_usdc']}[/green] USDC\n")


@app.command()
def status() -> None:
    """Display Arc network information (current block, chain ID, gas price)."""
    from arc_devkit.core.connection import get_web3

    with console.status("[bold]Querying Arc network...[/bold]", spinner="dots"):
        w3 = get_web3()
        bloco = w3.eth.block_number
        chain_id = w3.eth.chain_id
        gas_price_gwei = w3.from_wei(w3.eth.gas_price, "gwei")
        conectado = w3.is_connected()

    tabela = Table(
        title="Arc Network Status",
        show_header=True,
        header_style="bold magenta",
        border_style="magenta",
    )
    tabela.add_column("Property", style="bold", min_width=14)
    tabela.add_column("Value")

    tabela.add_row("Connected", "[green]✓ Yes[/green]" if conectado else "[red]✗ No[/red]")
    tabela.add_row("Current Block", f"[bold]#{bloco}[/bold]")
    tabela.add_row("Chain ID", str(chain_id))
    tabela.add_row("Gas Price", f"{gas_price_gwei} gwei")

    console.print(tabela)


@app.command()
def pay(
    to: str = typer.Argument(..., help="Recipient EVM address."),
    amount: float = typer.Argument(..., help="Amount to transfer (in USDC)."),
    send: bool = typer.Option(
        False, "--send", help="Send the transaction to the network (requires ARC_PRIVATE_KEY)."
    ),
    private_key: str = typer.Option("", "--key", help="Private key (overrides ARC_PRIVATE_KEY)."),
) -> None:
    """
    Prepare (and optionally send) a payment on Arc.

    Without --send, displays the signed transaction without broadcasting it (safe default mode).

    Examples:
      arcdevkit agent pay 0xDest... 5.0
      arcdevkit agent pay 0xDest... 5.0 --send
      arcdevkit agent pay 0xDest... 5.0 --send --key 0xYOURKEY...
    """
    from arc_devkit.agents.payment_agent import PaymentAgent

    agente = PaymentAgent(private_key=private_key or None)

    with console.status(
        f"[bold green]{'Sending' if send else 'Preparing'} payment of {amount} USDC → {to[:10]}...[/bold green]",
        spinner="dots",
    ):
        resultado = agente.execute(to=to, amount_usdc=amount, enviar=send)

    if resultado.get("status") == "error":
        console.print(f"\n[red]✗ Error:[/red] {resultado.get('error')}\n")
        raise typer.Exit(1)

    tabela = Table(
        title="Arc Payment",
        show_header=True,
        header_style="bold green",
        border_style="green",
    )
    tabela.add_column("Field", style="bold", min_width=14)
    tabela.add_column("Value")

    tabela.add_row("Status", f"[green]{resultado['status']}[/green]")
    tabela.add_row("From", resultado.get("from", "N/A"))
    tabela.add_row("To", resultado.get("to", "N/A"))
    tabela.add_row("Amount", f"{resultado.get('amount_usdc', amount)} USDC")

    if resultado.get("tx_hash"):
        tabela.add_row("TX Hash", f"[cyan]{resultado['tx_hash']}[/cyan]")
    if resultado.get("nota"):
        tabela.add_row("Note", f"[dim]{resultado['nota']}[/dim]")

    console.print(tabela)


@app.command()
def dashboard(
    addresses: list[str] = typer.Argument(..., help="One or more EVM addresses to watch."),
    interval: int = typer.Option(15, "--interval", "-i", help="Polling interval in seconds."),
    max_iter: int = typer.Option(0, "--max", help="Maximum iterations (0 = infinite)."),
) -> None:
    """
    Live terminal dashboard: watched balances and events updated in place.

    Press Ctrl+C to stop.

    Example:
      arcdevkit agent dashboard 0xWallet1... 0xWallet2... --interval 10
    """
    from arc_devkit.agents.dashboard import AgentDashboard
    from arc_devkit.agents.monitor_agent import MonitorAgent

    monitor = MonitorAgent(watched_addresses=addresses, interval_seconds=interval)
    try:
        AgentDashboard(monitor).run(max_iterations=max_iter)
    except KeyboardInterrupt:
        monitor.stop()
        console.print("\n[dim]Dashboard stopped.[/dim]\n")


@app.command()
def stop() -> None:
    """
    KILL SWITCH: halt all autonomous agents immediately.

    Creates ~/.arc_devkit/agents.stop — every guarded autonomous action
    (auto-refuel, triggers, scheduled payments) refuses to run while it exists.
    Use 'arcdevkit agent resume' to re-enable.
    """
    from arc_devkit.agents.guardrails import activate_kill_switch

    path = activate_kill_switch()
    console.print(
        Panel.fit(
            f"[bold red]■ Kill switch ACTIVATED[/bold red]\n"
            f"[dim]{path}[/dim]\n\n"
            "All autonomous agent actions are halted.\n"
            "Run [bold]arcdevkit agent resume[/bold] to re-enable.",
            border_style="red",
        )
    )


@app.command()
def resume() -> None:
    """Clear the kill switch and re-enable autonomous agents."""
    from arc_devkit.agents.guardrails import clear_kill_switch

    if clear_kill_switch():
        console.print(
            "[bold green]✓ Kill switch cleared — autonomous agents re-enabled.[/bold green]"
        )
    else:
        console.print("[dim]Kill switch was not active.[/dim]")


@app.command()
def audit(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of records to display."),
) -> None:
    """Show the most recent autonomous-action audit records (~/.arc_devkit/audit.log)."""
    import json as _json
    from pathlib import Path

    audit_file = Path.home() / ".arc_devkit" / "audit.log"
    if not audit_file.exists():
        console.print("[dim]No audit records yet.[/dim]")
        return

    lines = audit_file.read_text().strip().splitlines()[-limit:]
    tabela = Table(title="Autonomous Actions Audit", header_style="bold yellow")
    tabela.add_column("Timestamp", style="dim")
    tabela.add_column("Agent")
    tabela.add_column("Trigger")
    tabela.add_column("Action")
    tabela.add_column("Details", overflow="fold")

    for line in lines:
        try:
            rec = _json.loads(line)
        except Exception:
            continue
        details = {
            k: v for k, v in rec.items() if k not in {"timestamp", "agent", "trigger", "action"}
        }
        tabela.add_row(
            rec.get("timestamp", ""),
            rec.get("agent", ""),
            rec.get("trigger", ""),
            rec.get("action", ""),
            _json.dumps(details, ensure_ascii=False),
        )
    console.print(tabela)


@app.command()
def monitor(
    address: str = typer.Argument(..., help="EVM address to monitor."),
    interval: int = typer.Option(15, "--interval", "-i", help="Polling interval in seconds."),
    max_iter: int = typer.Option(0, "--max", help="Maximum iterations (0 = infinite)."),
) -> None:
    """
    Monitor an Arc wallet and display alerts when the balance changes.

    Press Ctrl+C to stop monitoring.

    Examples:
      arcdevkit agent monitor 0xWallet...
      arcdevkit agent monitor 0xWallet... --interval 5 --max 20
    """
    from arc_devkit.agents.monitor_agent import MonitorAgent

    def _callback(evento: dict) -> None:
        tipo = evento["type"]
        change_wei = int(evento["change_wei"])
        cor = "green" if tipo == "credit" else "red"
        sinal = "+" if tipo == "credit" else "-"
        console.print(
            f"  [{cor}]{sinal}{abs(change_wei)} wei ({tipo})[/{cor}]"
            f" → balance: {evento['balance_wei']} wei"
        )

    agente = MonitorAgent(watched_address=address, interval_seconds=interval)

    console.print(
        Panel.fit(
            f"[bold]Monitoring:[/bold] [cyan]{address}[/cyan]\n"
            f"[dim]Interval: {interval}s  |  Ctrl+C to stop[/dim]",
            border_style="magenta",
        )
    )

    try:
        agente.execute(callback=_callback, max_iterations=max_iter)
    except KeyboardInterrupt:
        agente.stop()
        console.print("\n[dim]Monitoring stopped.[/dim]\n")


# ---------------------------------------------------------------------------
# ERC-8004 identity / reputation
# ---------------------------------------------------------------------------


@app.command()
def register(
    domain: str = typer.Argument(..., help="Domain identifying the agent (e.g. myagent.eth)."),
    registry: str = typer.Option(..., "--registry", help="ERC-8004 Identity Registry address."),
    key: str = typer.Option("", "--key", help="Private key (overrides ARC_PRIVATE_KEY)."),
) -> None:
    """
    Register the caller's wallet as an on-chain agent (ERC-8004 Identity Registry).

    No canonical Identity Registry address is published for Arc yet — point
    --registry at your own deployment (see arc_devkit.agents.identity).

    Example:
      arcdevkit agent register myagent.eth --registry 0xRegistry...
    """
    from arc_devkit.agents.identity import AgentRegistry
    from arc_devkit.config import settings
    from arc_devkit.core.connection import get_web3

    private_key = key or settings.arc_private_key
    if not private_key:
        console.print("\n[red]✗ Error:[/red] No private key configured.\n")
        raise typer.Exit(1)

    try:
        registry_client = AgentRegistry(w3=get_web3(), identity_registry_address=registry)
        with console.status("[bold]Registering agent...[/bold]", spinner="dots"):
            identity = registry_client.register(domain, private_key)
    except Exception as exc:
        console.print(f"\n[red]✗ Error:[/red] {exc}\n")
        raise typer.Exit(1) from exc

    console.print(
        Panel(
            f"[bold]Agent ID:[/bold] {identity.agent_id}\n"
            f"[bold]Domain:[/bold] {identity.domain}\n"
            f"[bold]Address:[/bold] {identity.agent_address}\n"
            f"[bold]TX:[/bold] {identity.tx_hash}",
            title="[bold green]Agent Registered[/bold green]",
            border_style="green",
        )
    )


@app.command()
def reputation(
    agent_id: int = typer.Argument(..., help="On-chain agent id."),
    registry: str = typer.Option(..., "--registry", help="ERC-8004 Identity Registry address."),
    reputation_registry: str = typer.Option(
        ..., "--reputation-registry", help="ERC-8004 Reputation Registry address."
    ),
) -> None:
    """
    Show an agent's aggregated reputation (ERC-8004 Reputation Registry).

    Example:
      arcdevkit agent reputation 42 --registry 0x... --reputation-registry 0x...
    """
    from arc_devkit.agents.identity import AgentRegistry
    from arc_devkit.core.connection import get_web3

    try:
        registry_client = AgentRegistry(
            w3=get_web3(),
            identity_registry_address=registry,
            reputation_registry_address=reputation_registry,
        )
        score = registry_client.get_reputation(agent_id)
    except Exception as exc:
        console.print(f"\n[red]✗ Error:[/red] {exc}\n")
        raise typer.Exit(1) from exc

    if score is None:
        console.print(f"\n[red]✗ Error:[/red] No reputation found for agent {agent_id}.\n")
        raise typer.Exit(1)

    tabela = Table(title=f"Reputation — Agent {agent_id}", header_style="bold magenta")
    tabela.add_column("Field", style="bold", min_width=16)
    tabela.add_column("Value")
    tabela.add_row("Total Score", str(score.total_score))
    tabela.add_row("Feedback Count", str(score.feedback_count))
    tabela.add_row("Average", f"{score.average:.2f}")
    console.print(tabela)


# ---------------------------------------------------------------------------
# ERC-8183 job marketplace
# ---------------------------------------------------------------------------


def _print_job(job) -> None:
    tabela = Table(title="Job", header_style="bold cyan", border_style="cyan")
    tabela.add_column("Field", style="bold", min_width=16)
    tabela.add_column("Value")
    tabela.add_row("Job ID", str(job.job_id))
    tabela.add_row("Requester", job.requester)
    tabela.add_row("Agent", job.agent)
    tabela.add_row("Amount", f"{job.amount_usdc} USDC")
    tabela.add_row("Spec", job.spec)
    tabela.add_row("Status", job.status.value if hasattr(job.status, "value") else str(job.status))
    if job.deliverable_uri:
        tabela.add_row("Deliverable", job.deliverable_uri)
    if job.tx_hash:
        tabela.add_row("TX", job.tx_hash)
    if job.error:
        tabela.add_row("Error", f"[red]{job.error}[/red]")
    console.print(tabela)


@job_app.command(name="create")
def job_create(
    agent_address: str = typer.Argument(..., help="Address of the agent being hired."),
    amount: float = typer.Argument(..., help="Escrow amount in USDC."),
    spec: str = typer.Option(..., "--spec", help="Job specification / description."),
    registry: str = typer.Option(..., "--registry", help="ERC-8183 Job Registry address."),
    key: str = typer.Option("", "--key", help="Private key (overrides ARC_PRIVATE_KEY)."),
) -> None:
    """
    Create a job with USDC escrow for another agent.

    The registry contract must already be approve()'d to spend `amount` USDC
    from your wallet (standard ERC-20 escrow pattern).

    Example:
      arcdevkit agent job create 0xAgent... 25.0 --spec "summarize this PDF" --registry 0x...
    """
    from decimal import Decimal

    from arc_devkit.agents.jobs import JobRegistry
    from arc_devkit.config import settings
    from arc_devkit.core.connection import get_web3

    private_key = key or settings.arc_private_key
    if not private_key:
        console.print("\n[red]✗ Error:[/red] No private key configured.\n")
        raise typer.Exit(1)

    try:
        job_registry = JobRegistry(w3=get_web3(), registry_address=registry)
        with console.status("[bold]Creating job...[/bold]", spinner="dots"):
            job = job_registry.create_job(agent_address, Decimal(str(amount)), spec, private_key)
    except Exception as exc:
        console.print(f"\n[red]✗ Error:[/red] {exc}\n")
        raise typer.Exit(1) from exc

    _print_job(job)
    if job.error:
        raise typer.Exit(1)


@job_app.command(name="accept")
def job_accept(
    job_id: int = typer.Argument(..., help="Job id to accept."),
    registry: str = typer.Option(..., "--registry", help="ERC-8183 Job Registry address."),
    key: str = typer.Option("", "--key", help="Private key (overrides ARC_PRIVATE_KEY)."),
) -> None:
    """Accept a job as the assigned agent."""
    from arc_devkit.agents.jobs import JobRegistry
    from arc_devkit.config import settings
    from arc_devkit.core.connection import get_web3

    private_key = key or settings.arc_private_key
    if not private_key:
        console.print("\n[red]✗ Error:[/red] No private key configured.\n")
        raise typer.Exit(1)

    try:
        job_registry = JobRegistry(w3=get_web3(), registry_address=registry)
        job = job_registry.accept_job(job_id, private_key)
    except Exception as exc:
        console.print(f"\n[red]✗ Error:[/red] {exc}\n")
        raise typer.Exit(1) from exc

    _print_job(job)
    if job.error:
        raise typer.Exit(1)


@job_app.command(name="deliver")
def job_deliver(
    job_id: int = typer.Argument(..., help="Job id to deliver."),
    deliverable: str = typer.Argument(..., help="Deliverable URI or result string."),
    registry: str = typer.Option(..., "--registry", help="ERC-8183 Job Registry address."),
    key: str = typer.Option("", "--key", help="Private key (overrides ARC_PRIVATE_KEY)."),
) -> None:
    """Submit a deliverable for an accepted job."""
    from arc_devkit.agents.jobs import JobRegistry
    from arc_devkit.config import settings
    from arc_devkit.core.connection import get_web3

    private_key = key or settings.arc_private_key
    if not private_key:
        console.print("\n[red]✗ Error:[/red] No private key configured.\n")
        raise typer.Exit(1)

    try:
        job_registry = JobRegistry(w3=get_web3(), registry_address=registry)
        job = job_registry.deliver_job(job_id, deliverable, private_key)
    except Exception as exc:
        console.print(f"\n[red]✗ Error:[/red] {exc}\n")
        raise typer.Exit(1) from exc

    _print_job(job)
    if job.error:
        raise typer.Exit(1)


@job_app.command(name="settle")
def job_settle(
    job_id: int = typer.Argument(..., help="Job id to settle."),
    registry: str = typer.Option(..., "--registry", help="ERC-8183 Job Registry address."),
    key: str = typer.Option("", "--key", help="Private key (overrides ARC_PRIVATE_KEY)."),
) -> None:
    """Release escrow to the agent for a delivered job."""
    from arc_devkit.agents.jobs import JobRegistry
    from arc_devkit.config import settings
    from arc_devkit.core.connection import get_web3

    private_key = key or settings.arc_private_key
    if not private_key:
        console.print("\n[red]✗ Error:[/red] No private key configured.\n")
        raise typer.Exit(1)

    try:
        job_registry = JobRegistry(w3=get_web3(), registry_address=registry)
        job = job_registry.settle_job(job_id, private_key)
    except Exception as exc:
        console.print(f"\n[red]✗ Error:[/red] {exc}\n")
        raise typer.Exit(1) from exc

    _print_job(job)
    if job.error:
        raise typer.Exit(1)


@job_app.command(name="status")
def job_status(
    job_id: int = typer.Argument(..., help="Job id to look up."),
    registry: str = typer.Option(..., "--registry", help="ERC-8183 Job Registry address."),
) -> None:
    """Show the current on-chain state of a job."""
    from arc_devkit.agents.jobs import JobRegistry
    from arc_devkit.core.connection import get_web3

    try:
        job_registry = JobRegistry(w3=get_web3(), registry_address=registry)
        job = job_registry.get_job(job_id)
    except Exception as exc:
        console.print(f"\n[red]✗ Error:[/red] {exc}\n")
        raise typer.Exit(1) from exc

    if job is None:
        console.print(f"\n[red]✗ Error:[/red] No job found with id {job_id}.\n")
        raise typer.Exit(1)
    _print_job(job)
