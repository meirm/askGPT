#!/usr/bin/env python
from click.testing import CliRunner
from askGPT import cli

def test_cli():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Show this message and exit." in result.output
    
def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.6.0" in result.output

def test_show():
    runner = CliRunner()
    result = runner.invoke(cli, ["show", "config"])
    assert result.exit_code == 0
    assert "maxTokens" in result.output
    result = runner.invoke(cli, ["show", "scenarios"])
    assert result.exit_code == 0
    assert "scenarios" in result.output
    result = runner.invoke(cli, ["show", "subjects"])
    assert result.exit_code == 0
    assert "subjects" in result.output
    result = runner.invoke(cli, ["show", "conversations"])
    assert result.exit_code == 0 #FIXME it should be 1
    assert "Please specify what to show" in result.output
    result = runner.invoke(cli, ["show", "subject", "test"])
    assert result.exit_code == 0
    assert "user: are you still working?" in result.output

def test_config():
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "set", "maxTokens", "10"])
    assert result.exit_code == 2
    result = runner.invoke(cli, [ "config", "--max-tokens", "10"])
    assert result.exit_code == 0
    result = runner.invoke(cli, ["config"])
    assert result.exit_code == 0
    assert "maxTokens = 10" in result.output 


if __name__ == "__main__":
    test_cli()
    test_version()
    test_show()
    test_config()