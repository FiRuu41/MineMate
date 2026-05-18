"""MineMate CLI — MC mod Q&A agent launcher."""
import os
import sys

# Ensure project root is on path (needed when run via installed entry point).
# The user always runs from the project root directory.
_cwd = os.getcwd()
if _cwd not in sys.path:
    sys.path.insert(0, _cwd)

import click


@click.group()
def main():
    """MineMate — Your AI buddy for Minecraft mods."""
    pass


@main.command()
def setup():
    """Diagnose setup status: API key / data / Playwright / BGE-M3 model."""
    import os
    from pathlib import Path
    from config.settings import settings

    click.echo("╔══════════════════════════╗")
    click.echo("║   MineMate Setup Wizard  ║")
    click.echo("╚══════════════════════════╝")
    click.echo()

    issues = []

    # [1/4] DeepSeek API key
    click.echo("[1/4] DeepSeek API key ...                   ", nl=False)
    try:
        key = settings.deepseek_api_key
        if key and key != "sk-xxx" and len(key) > 10:
            click.echo(click.style("OK", fg="green"))
        else:
            click.echo(click.style("MISSING", fg="yellow"))
            issues.append("Edit .env and set DEEPSEEK_API_KEY=sk-your-key")
    except Exception:
        click.echo(click.style("MISSING", fg="red"))
        issues.append("Copy .env.example to .env and set DEEPSEEK_API_KEY")

    # [2/4] Data files
    click.echo("[2/4] Data files ...                         ", nl=False)
    db = settings.resolved_sqlite_path
    chroma = settings.resolved_chroma_path
    if db.exists() and (chroma / "chroma.sqlite3").exists():
        try:
            import sqlite3
            conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            n = conn.execute("SELECT COUNT(*) FROM mods").fetchone()[0]
            conn.close()
            click.echo(click.style(f"OK ({n} mods)", fg="green"))
        except Exception:
            click.echo(click.style("PARTIAL (db unreadable)", fg="yellow"))
            issues.append(f"SQLite at {db} appears corrupted")
    else:
        click.echo(click.style("MISSING", fg="yellow"))
        issues.append(
            "Get a data zip from the author and run: minemate import-data <zip>"
        )

    # [3/4] Playwright Chromium
    click.echo("[3/4] Playwright Chromium ...                ", nl=False)
    pw_path = settings.playwright_browsers_path or os.environ.get(
        "PLAYWRIGHT_BROWSERS_PATH", ""
    )
    has_chromium = False
    if pw_path:
        pw_dir = Path(pw_path)
        if pw_dir.exists():
            has_chromium = any(
                p.name.startswith("chromium") for p in pw_dir.iterdir() if p.is_dir()
            )
    else:
        default_dir = Path.home() / "AppData" / "Local" / "ms-playwright"
        if default_dir.exists():
            has_chromium = any(
                p.name.startswith("chromium") for p in default_dir.iterdir() if p.is_dir()
            )

    if has_chromium:
        click.echo(click.style("OK", fg="green"))
    else:
        click.echo(click.style("MISSING", fg="yellow"))
        issues.append("Run: uv run playwright install chromium")

    # [4/4] BGE-M3 model
    click.echo("[4/4] BGE-M3 model ...                       ", nl=False)
    hf_home = os.environ.get("HF_HOME") or settings.hf_home or str(
        Path.home() / ".cache" / "huggingface"
    )
    bge_dir = Path(hf_home) / "hub" / "models--BAAI--bge-m3"
    if bge_dir.exists():
        click.echo(click.style("OK", fg="green"))
    else:
        click.echo(click.style("MISSING", fg="yellow"))
        issues.append(
            "BGE-M3 model will auto-download on first 'minemate start' (~2.3 GB)"
        )

    click.echo()
    if not issues:
        click.echo(click.style("Setup complete. Run 'minemate start' to launch.", fg="green"))
    else:
        click.echo(click.style("Setup incomplete:", fg="yellow"))
        for i, msg in enumerate(issues, 1):
            click.echo(f"  {i}. {msg}")


@main.command()
def start():
    """Launch the Gradio web UI."""
    click.echo("Starting MineMate at http://127.0.0.1:7860 ...")
    from app.gradio_app import main as gradio_main
    gradio_main()


@main.command()
def status():
    """Show system status: data files, model cache, mod counts."""
    from config.settings import settings
    from pathlib import Path
    import os

    click.echo("=== MineMate Status ===")

    # SQLite
    db = settings.resolved_sqlite_path
    if db.exists():
        size_mb = db.stat().st_size / 1024 / 1024
        click.echo(f"  SQLite:  {click.style('OK', fg='green')}  {db} ({size_mb:.1f} MB)")
    else:
        click.echo(f"  SQLite:  {click.style('MISSING', fg='yellow')}  expected at {db}")

    # Chroma
    chroma = settings.resolved_chroma_path
    chroma_db = chroma / "chroma.sqlite3"
    if chroma_db.exists():
        size_mb = chroma_db.stat().st_size / 1024 / 1024
        click.echo(f"  Chroma:  {click.style('OK', fg='green')}  {chroma} ({size_mb:.1f} MB)")
    else:
        click.echo(f"  Chroma:  {click.style('MISSING', fg='yellow')}  expected at {chroma}")

    # BGE-M3 cache (HuggingFace)
    hf_home = os.environ.get("HF_HOME") or settings.hf_home or str(Path.home() / ".cache" / "huggingface")
    bge_dir = Path(hf_home) / "hub" / "models--BAAI--bge-m3"
    if bge_dir.exists():
        click.echo(f"  BGE-M3:  {click.style('OK', fg='green')}  cached at {bge_dir}")
    else:
        click.echo(f"  BGE-M3:  {click.style('MISSING', fg='yellow')}  will download on first run")

    # API key
    try:
        key = settings.deepseek_api_key
        if key and key != "sk-xxx" and len(key) > 10:
            click.echo(f"  API key: {click.style('OK', fg='green')}")
        else:
            click.echo(f"  API key: {click.style('MISSING', fg='yellow')}")
    except Exception:
        click.echo(f"  API key: {click.style('MISSING', fg='red')}")

    # Mod / tag counts
    try:
        from pipeline.storage.db import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as s:
            n = s.execute(text("SELECT COUNT(*) FROM mods")).scalar()
            tagged = s.execute(text("SELECT COUNT(*) FROM mods WHERE tags IS NOT NULL")).scalar()
        click.echo(f"  Mods:    {n} total, {tagged} tagged")
    except Exception as e:
        click.echo(f"  Mods:    {click.style('cannot connect', fg='red')} ({e})")


@main.command(name="import-data")
@click.argument("zip_path", type=click.Path(exists=True, dir_okay=False, path_type=__import__("pathlib").Path))
@click.option("--force", is_flag=True, default=False, help="Overwrite existing data at destination")
def import_data_cmd(zip_path, force):
    """Import a minemate-data zip into local SQLite + Chroma paths."""
    from config.settings import settings
    from scripts.import_data import import_data, ImportError_

    try:
        import_data(
            zip_path,
            settings.resolved_sqlite_path,
            settings.resolved_chroma_path,
            force=force,
            echo=click.echo,
        )
        click.echo()
        click.echo(click.style("Import complete. Run 'minemate start' to launch.", fg="green"))
    except ImportError_ as e:
        click.echo()
        click.echo(click.style(f"ERROR: {e}", fg="red"), err=True)
        raise click.exceptions.Exit(1)


@main.command(name="build-index")
@click.option("--mod", default=None, help="Rebuild only this mod_id")
def build_index_cmd(mod):
    """Build/rebuild Chroma vector index from SQLite mods (BGE-M3 embeddings)."""
    import sys
    from pipeline.build_index import main as _impl
    saved_argv = sys.argv
    sys.argv = ["build_index"] + (["--mod", mod] if mod else [])
    try:
        _impl()
    finally:
        sys.argv = saved_argv


@main.command(name="build-tags")
@click.option("--workers", type=int, default=10, help="Concurrent LLM calls")
@click.option("--limit", type=int, default=0, help="Max mods to tag (0=all)")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip 5s confirmation countdown")
def build_tags_cmd(workers, limit, yes):
    """Tag mods via DeepSeek LLM. WARNING: consumes API tokens."""
    import sys
    import time

    if not yes:
        click.echo(click.style("WARNING:", fg="yellow", bold=True)
                   + " This will call DeepSeek API for every untagged mod.")
        click.echo("  Estimated cost: ~$0.01 per 100 mods (~$1.10 for 11000 mods).")
        click.echo("  Press Ctrl+C within 5s to abort, or use --yes to skip this prompt.")
        click.echo()
        try:
            for i in range(5, 0, -1):
                click.echo(f"  {i}...", nl=False)
                time.sleep(1)
            click.echo(" starting.")
        except KeyboardInterrupt:
            click.echo()
            click.echo(click.style("aborted.", fg="red"))
            raise click.exceptions.Exit(130)

    from pipeline.tag_mods import main as _impl
    saved_argv = sys.argv
    args = ["tag_mods", "--workers", str(workers)]
    if limit:
        args += ["--limit", str(limit)]
    sys.argv = args
    try:
        _impl()
    finally:
        sys.argv = saved_argv


if __name__ == "__main__":
    main()
