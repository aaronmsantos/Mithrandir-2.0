import pytest
from typer.testing import CliRunner
from main import app

runner = CliRunner()

def test_smoke_doctor():
    """Verify doctor command runs and exits with code 0."""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "🛡️ Mithrandir 2.0 Diagnostics Report" in result.stdout
    assert "System check complete!" in result.stdout

def test_smoke_help():
    """Verify help command displays correctly."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "🛡️ Mithrandir 2.0 Command Line Interface ⚡️" in result.stdout
