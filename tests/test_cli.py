import sys
import pytest
from unittest.mock import patch
from brain.brain_cli import main

def test_cli_help(capsys):
    with patch.object(sys, 'argv', ['brain_cli', '--help']):
        with pytest.raises(SystemExit):
            main()
    captured = capsys.readouterr()
    assert "BRAIN - Cartório Notary Pipeline CLI" in captured.out

def test_cli_calculate(capsys):
    with patch.object(sys, 'argv', ['brain_cli', 'calculate', '--value', '200000', '--act', 'Escritura']):
        main()
    captured = capsys.readouterr()
    assert "emoluments" in captured.out
    assert "tax_comparison" in captured.out

def test_cli_validate(capsys):
    with patch.object(sys, 'argv', ['brain_cli', 'validate', '--act', 'Usucapião', '--docs', 'Ata Notarial, Planta e Memorial Descritivo']):
        main()
    captured = capsys.readouterr()
    assert "status" in captured.out
    assert "Usucapião" in captured.out
