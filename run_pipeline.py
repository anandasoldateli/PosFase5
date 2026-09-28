"""Executa o pipeline completo, da planilha original ao documento Q1–Q11.

Uso:
    python run_pipeline.py

Pré-requisito: a planilha "BASE DE DADOS PEDE 2024 - DATATHON.xlsx" em data/.
"""

import subprocess
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

RAIZ = Path(__file__).resolve().parent
SRC = RAIZ / "src"
NOTEBOOK = RAIZ / "notebooks" / "modelo_risco_defasagem.ipynb"


def rodar_script(nome):
    print(f"\n>>> src/{nome}")
    subprocess.run([sys.executable, nome], cwd=SRC, check=True)


def rodar_notebook():
    print(f"\n>>> {NOTEBOOK.relative_to(RAIZ)}")
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    NotebookClient(notebook, timeout=900, resources={"metadata": {"path": str(NOTEBOOK.parent)}}).execute()
    nbformat.write(notebook, NOTEBOOK)
    print("Notebook executado e salvo com as saídas.")


def main():
    rodar_script("preparacao.py")
    rodar_script("analises.py")
    rodar_notebook()
    rodar_script("consolidacao.py")
    rodar_script("documento.py")
    print("\nPipeline concluído.")


if __name__ == "__main__":
    main()
