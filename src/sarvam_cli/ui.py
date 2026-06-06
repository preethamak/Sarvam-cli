from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter

from rich.align import Align
from rich.box import HEAVY, ROUNDED
from rich.columns import Columns
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text


console = Console()


@dataclass
class SessionStats:
    model: str
    turns: int = 0
    started_at: float = 0.0

    def start(self) -> None:
        self.started_at = perf_counter()

    @property
    def elapsed(self) -> float:
        if not self.started_at:
            return 0.0
        return perf_counter() - self.started_at


def print_banner(*, title: str = "Sarvam CLI", subtitle: str = "Multilingual AI in your terminal") -> None:
    wordmark = Text(justify="left")
    wordmark.append("SARVAM", style="bold white on blue")
    wordmark.append("  CLI", style="bold black on white")
    meta = Text()
    meta.append(subtitle, style="bright_black")
    console.print(
        Panel(
            Group(wordmark, Text(""), meta),
            border_style="bright_blue",
            box=HEAVY,
            padding=(1, 2),
        )
    )


def print_home(*, configured: bool, base_url: str) -> None:
    print_banner(subtitle="Speech, chat, translation, and voice agents for builders")
    status_text = "configured" if configured else "needs api key"
    status_style = "bold black on green" if configured else "bold black on yellow"
    intro = Group(
        Text("A terminal-native Sarvam workspace for fast multilingual prototyping.", style="white"),
        Text(""),
        Text.assemble(
            ("status ", "bright_black"),
            (status_text, status_style),
            ("   "),
            ("endpoint ", "bright_black"),
            (base_url, "cyan"),
        ),
    )
    console.print(
        Panel(
            intro,
            title="[bold]Command Center[/bold]",
            border_style="blue",
            box=ROUNDED,
            padding=(1, 2),
        )
    )

    quick_start = Table.grid(expand=True)
    quick_start.add_column(style="bright_black", width=3)
    quick_start.add_column(style="white")
    quick_start.add_row("01", "sarvam config set-api-key")
    quick_start.add_row("02", "sarvam chat")
    quick_start.add_row("03", "sarvam help")

    actions = [
        Panel(
            Text.assemble(
                ("Talk to the model with context-aware replies\n\n", "white"),
                ("sarvam chat", "bold cyan"),
            ),
            title="[bold]Chat[/bold]",
            border_style="cyan",
            box=ROUNDED,
            padding=(1, 2),
        ),
        Panel(
            Text.assemble(
                ("Hands-free microphone in, spoken answer out\n\n", "white"),
                ("sarvam chat --voice --lang hi-IN", "bold magenta"),
            ),
            title="[bold]Voice[/bold]",
            border_style="magenta",
            box=ROUNDED,
            padding=(1, 2),
        ),
        Panel(
            Text.assemble(
                ("Translate, detect, transcribe, and generate speech\n\n", "white"),
                ("sarvam translate file.txt --to hi-IN", "bold green"),
            ),
            title="[bold]Language Ops[/bold]",
            border_style="green",
            box=ROUNDED,
            padding=(1, 2),
        ),
    ]

    workflow = Text()
    workflow.append("Microphone", style="bold magenta")
    workflow.append(" -> ", style="bright_black")
    workflow.append("Speech-to-Text", style="bold cyan")
    workflow.append(" -> ", style="bright_black")
    workflow.append("Sarvam Model", style="bold white")
    workflow.append(" -> ", style="bright_black")
    workflow.append("Text-to-Speech", style="bold green")
    workflow.append(" -> ", style="bright_black")
    workflow.append("Speaker", style="bold yellow")

    console.print(
        Columns(
            [
                Panel(
                    quick_start,
                    title="[bold]Quick Start[/bold]",
                    border_style="green",
                    box=ROUNDED,
                    padding=(1, 2),
                ),
                Panel(
                    workflow,
                    title="[bold]Signal Flow[/bold]",
                    border_style="yellow",
                    box=ROUNDED,
                    padding=(1, 2),
                ),
            ],
            equal=True,
            expand=True,
        )
    )
    console.print(Columns(actions, expand=True, equal=True))


def print_command_guide(*, configured: bool) -> None:
    table = Table(box=ROUNDED, border_style="blue")
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Use", style="white")
    table.add_row("sarvam", "Open the landing screen")
    table.add_row("sarvam help", "Show this guided command view")
    table.add_row("sarvam config set-api-key", "Save your API key for this user")
    table.add_row("sarvam config show", "Inspect config status and storage path")
    table.add_row("sarvam chat", "Launch the chat workspace")
    table.add_row("sarvam chat --voice --lang hi-IN", "Run a voice session")
    table.add_row("sarvam translate notes.txt --to kn-IN", "Translate text or files")
    table.add_row("sarvam transcribe audio.wav", "Transcribe audio")
    table.add_row("sarvam speak \"Hello\" --lang en-IN", "Generate speech audio")
    table.add_row("sarvam detect-language notes.txt", "Detect language")
    console.print(
        Panel(
            table,
            title="[bold]Command Guide[/bold]",
            border_style="blue",
            box=ROUNDED,
        )
    )
    note = (
        "You are configured. Jump into `sarvam chat`."
        if configured
        else "Fresh install: run `sarvam config set-api-key` before chat, speech, or translation."
    )
    note_style = "green" if configured else "yellow"
    console.print(
        Panel(
            Text(note, style="white"),
            title="[bold]Onboarding[/bold]",
            border_style=note_style,
            box=ROUNDED,
            padding=(1, 2),
        )
    )


def print_chat_shell(*, model: str, voice: bool = False) -> None:
    badge = "VOICE" if voice else "CHAT"
    badge_style = "bold black on magenta" if voice else "bold black on cyan"
    header = Text.assemble(
        (badge, badge_style),
        ("  "),
        ("model ", "bright_black"),
        (model, "white"),
        ("  "),
        ("controls ", "bright_black"),
        ("/help /stats /clear /exit", "cyan"),
    )
    composer = Text()
    composer.append("Composer ready.\n", style="white")
    composer.append("Write naturally. Press Enter to send the next turn.", style="bright_black")
    console.print(
        Panel(
            Group(
                header,
                Rule(style="bright_black"),
                composer,
            ),
            title="[bold]Workspace[/bold]",
            border_style="blue",
            box=HEAVY,
            padding=(1, 2),
        )
    )


def print_composer(*, stats: SessionStats) -> None:
    rows = Table.grid(expand=True)
    rows.add_column(style="bright_black", ratio=1)
    rows.add_column(style="white", ratio=3)
    rows.add_row("turn", str(stats.turns + 1))
    rows.add_row("elapsed", f"{stats.elapsed:.1f}s")
    rows.add_row("hint", "Type a message or a slash command")
    console.print(
        Panel(
            rows,
            title="[bold]Compose[/bold]",
            border_style="magenta",
            box=ROUNDED,
            padding=(0, 2),
        )
    )


def print_assistant_message(message: str, *, title: str = "Sarvam") -> None:
    renderable = Markdown(message) if "\n" in message or any(ch in message for ch in "#*-`") else Text(message)
    console.print(
        Panel(
            renderable,
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan",
            box=ROUNDED,
            padding=(1, 2),
        )
    )


def print_user_message(message: str, *, title: str = "You") -> None:
    console.print(
        Panel(
            Text(message, style="white"),
            title=f"[bold magenta]{title}[/bold magenta]",
            border_style="magenta",
            box=ROUNDED,
            padding=(0, 2),
        )
    )


def print_kv(title: str, rows: list[tuple[str, str]]) -> None:
    table = Table(box=ROUNDED, border_style="blue", show_header=False)
    table.add_column(style="cyan", no_wrap=True)
    table.add_column(style="white")
    for key, value in rows:
        table.add_row(key, value)
    console.print(
        Panel(
            table,
            title=f"[bold]{title}[/bold]",
            border_style="blue",
            box=ROUNDED,
        )
    )


def print_help() -> None:
    table = Table(box=ROUNDED, border_style="blue")
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Action", style="white")
    table.add_row("/help", "Show chat controls")
    table.add_row("/clear", "Clear the current conversation history")
    table.add_row("/stats", "Show live session stats")
    table.add_row("/exit", "Close the workspace")
    console.print(
        Panel(
            table,
            title="[bold]Session Commands[/bold]",
            border_style="blue",
            box=ROUNDED,
        )
    )


def print_stats(stats: SessionStats) -> None:
    print_kv(
        "Session Stats",
        [
            ("model", stats.model),
            ("turns", str(stats.turns)),
            ("elapsed", f"{stats.elapsed:.1f}s"),
        ],
    )


def print_system(message: str) -> None:
    console.print(Align.left(Text.assemble(("sarvam ", "bold blue"), (message, "white"))))


def print_success(message: str) -> None:
    console.print(Text.assemble(("ok ", "bold green"), (message, "white")))


def print_warning(message: str) -> None:
    console.print(Text.assemble(("warn ", "bold yellow"), (message, "white")))


def print_error(message: str) -> None:
    console.print(Text.assemble(("error ", "bold red"), (message, "white")))


@contextmanager
def status(message: str):
    with console.status(f"[bold blue]{message}[/bold blue]", spinner="dots"):
        yield
