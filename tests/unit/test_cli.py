from click.testing import CliRunner
from minemate.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "setup" in result.output
    assert "start" in result.output
    assert "status" in result.output


def test_status_fails_without_env():
    """Without DEEPSEEK_API_KEY set, status should still run (it catches exceptions)."""
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    # Status handles missing env gracefully
    assert result.exit_code == 0
    assert "MineMate Status" in result.output


def test_setup_detects_no_docker():
    """setup should fail early if docker not available."""
    import shutil
    if shutil.which("docker"):
        # Docker IS available - can't test this failure path
        return
    runner = CliRunner()
    result = runner.invoke(main, ["setup"])
    assert result.exit_code == 1
    assert "Docker" in result.output
