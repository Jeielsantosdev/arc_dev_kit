"""CLI commands for view-key encryption (experimental privacy primitives)."""

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(help="Experimental privacy primitives: view-key encryption.")
console = Console()


@app.command(name="generate-view-key")
def generate_view_key() -> None:
    """
    Generate a new view-key pair for selective disclosure.

    The private key is shown ONCE — store it securely. Share only the
    public key with senders who should be able to encrypt data to you.
    """
    from arc_devkit.privacy.view_key import generate_view_keypair

    keypair = generate_view_keypair()
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
    )

    private_bytes = keypair.private_key.private_bytes(
        encoding=Encoding.DER,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )

    console.print(
        Panel(
            f"[bold]Public key:[/bold]\n[cyan]{keypair.public_key_bytes.hex()}[/cyan]\n\n"
            f"[bold]Private key (DER, hex):[/bold]\n[dim]{private_bytes.hex()}[/dim]\n\n"
            "[bold red]⚠ WARNING:[/bold red] Private key shown only once. "
            "Store it securely. Never share or commit to git.",
            title="[bold green]New View-Key Pair[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )


@app.command(name="encrypt")
def encrypt(
    viewer_public_key_hex: str = typer.Argument(..., help="Viewer's public key (hex)."),
    message: str = typer.Argument(..., help="Plaintext to encrypt (e.g. an amount or memo)."),
) -> None:
    """Encrypt a message so only the holder of the matching view private key can read it."""
    from arc_devkit.privacy.view_key import encrypt_for_viewer

    payload = encrypt_for_viewer(bytes.fromhex(viewer_public_key_hex), message.encode())
    console.print(f"\n[bold]Encrypted payload:[/bold]\n[cyan]{payload.to_hex()}[/cyan]\n")
