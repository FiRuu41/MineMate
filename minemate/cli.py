"""MineMate CLI — MC mod Q&A agent launcher."""
import os
import sys

# Ensure project root is on path (needed when run via installed entry point)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

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

    # 1. Check Docker
    click.echo("[1/5] Checking Docker ... ", nl=False)
    try:
        r = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            click.echo(click.style("OK", fg="green"))
        else:
            click.echo(click.style("FAIL", fg="red"))
            click.echo("  Docker is not running. Please start Docker Desktop first.")
            sys.exit(1)
    except FileNotFoundError:
        click.echo(click.style("NOT FOUND", fg="red"))
        click.echo("  Docker is not installed. Install from https://www.docker.com/")
        sys.exit(1)

    # 2. Start services
    click.echo("[2/5] Starting Qdrant + MySQL ... ", nl=False)
    r = subprocess.run(["docker-compose", "up", "-d"], capture_output=True, text=True)
    if r.returncode == 0:
        click.echo(click.style("OK", fg="green"))
    else:
        click.echo(click.style("FAIL", fg="red"))
        click.echo(f"  {r.stderr}")
        sys.exit(1)

    # 3. Check API key
    click.echo("[3/5] Checking DeepSeek API key ... ", nl=False)
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

    # 4. Init DB
    click.echo("[4/5] Initializing database ... ", nl=False)
    r = subprocess.run([sys.executable, "-m", "scripts.init_db"], capture_output=True, text=True)
    if r.returncode == 0:
        click.echo(click.style("OK", fg="green"))
    else:
        click.echo(click.style("FAIL", fg="red"))
        click.echo(f"  {r.stderr}")

    # 5. Data import guide
    click.echo("[5/5] Data import")
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
    """Show system status: Docker, MySQL, Qdrant, mod count."""
    click.echo("=== MineMate Status ===")
    # Docker
    import subprocess
    r = subprocess.run(["docker", "ps", "--format", "{{.Names}} {{.Status}}"], capture_output=True, text=True)
    has_mysql = "mcmod-mysql" in r.stdout
    has_qdrant = "mcmod-qdrant" in r.stdout
    click.echo(f"  Docker:  {'OK' if (has_mysql and has_qdrant) else 'MISSING SERVICES'}")
    click.echo(f"  MySQL:   {'Up' if has_mysql else 'Down'}")
    click.echo(f"  Qdrant:  {'Up' if has_qdrant else 'Down'}")

    # API key
    try:
        from config.settings import settings
        key = settings.deepseek_api_key
        click.echo(f"  API key: {'Set' if key and len(key) > 10 else 'MISSING'}")
    except Exception:
        click.echo(f"  API key: MISSING")

    # Mod count
    try:
        from pipeline.storage.db import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as s:
            n = s.execute(text("SELECT COUNT(*) FROM mods")).scalar()
            tagged = s.execute(text("SELECT COUNT(*) FROM mods WHERE tags IS NOT NULL")).scalar()
        click.echo(f"  Mods:    {n} total, {tagged} tagged")
    except Exception:
        click.echo(f"  Mods:    (cannot connect to MySQL)")


if __name__ == "__main__":
    main()
