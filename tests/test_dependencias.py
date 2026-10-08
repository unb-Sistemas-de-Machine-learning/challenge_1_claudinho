"""As listas de dependencias precisam bater.

A Vercel instala pelo pyproject.toml; o Docker e o CI, pelo requirements.txt. Se as duas
divergirem, o deploy roda com versoes diferentes das testadas, ou quebra no import.
"""

import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _requirements(nome: str) -> set[str]:
    linhas = (RAIZ / nome).read_text(encoding="utf-8").splitlines()
    return {
        linha.split("#")[0].strip()
        for linha in linhas
        if linha.split("#")[0].strip() and not linha.strip().startswith("-")
    }


def _pyproject() -> dict:
    return tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_runtime_do_pyproject_igual_ao_requirements():
    assert set(_pyproject()["dependencies"]) == _requirements("requirements.txt")


def test_extra_ml_do_pyproject_igual_ao_requirements_ml():
    assert set(_pyproject()["optional-dependencies"]["ml"]) == _requirements("requirements-ml.txt")


def test_runtime_da_api_nao_depende_do_torch():
    """O modelo roda no servico remoto; a API tem que caber em 500 MB (Vercel)."""
    pesados = ("torch", "sentence-transformers", "transformers", "scikit-learn")
    runtime = " ".join(_requirements("requirements.txt")).lower()

    assert not [p for p in pesados if p in runtime]
