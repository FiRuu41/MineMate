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
    """First-time setup wizard: check environment, init DB, guide data import."""
    click.echo("╔══════════════════════════╗")
    click.echo("║   MineMate Setup Wizard  ║")
    click.echo("╚══════════════════════════╝")
    click.echo()

    import subprocess

    from config.settings import settings as _s
    # 1. Check API key
    click.echo("[1/2] Checking DeepSeek API key ... ", nl=False)
    try:
        from config.settings import settings
        key = settings.deepseek_api_key
        if key and key != "sk-xxx" and len(key) > 10:
            click.echo(click.style("OK", fg="green"))
        else:
            click.echo(click.style("MISSING", fg="yellow"))
            click.echo("  Edit .env file and set DEEPSEEK_API_KEY=sk-your-key")
    except Exception as e:
        click.echo(click.style("MISSING", fg="yellow"))
        click.echo(f"  Copy .env.example to .env and fill in DEEPSEEK_API_KEY")

    # 2. Init DB
    click.echo("[2/2] Initializing database (SQLite) ... ", nl=False)
    r = subprocess.run([sys.executable, "-m", "scripts.init_db"], capture_output=True, text=True)
    if r.returncode == 0:
        click.echo(click.style("OK", fg="green"))
    else:
        click.echo(click.style("FAIL", fg="red"))
        click.echo(f"  {r.stderr}")

    click.echo()
    click.echo("  MineMate does NOT include mod data. You need to provide it.")
    click.echo("  Import mod data into MySQL table 'mods' with columns:")
    click.echo("    mod_id, name_zh, name_en, mcmod_url, loader, mc_versions, author, description")
    click.echo()
    click.echo("  Optional: run 'minemate build-index' and 'minemate build-tags' after importing data.")
    click.echo()
    click.echo(click.style("Setup complete! Run 'minemate start' to launch.", fg="green"))


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


if __name__ == "__main__":
    main()
