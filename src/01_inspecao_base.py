import pandas as pd
from pathlib import Path


# ============================================================
# 1. Caminho da base
# ============================================================

ARQUIVO = Path("data/BASE DE DADOS PEDE 2024 - DATATHON.xlsx")


# ============================================================
# 2. Verificar se o arquivo existe
# ============================================================

if not ARQUIVO.exists():
    raise FileNotFoundError(
        f"Arquivo não encontrado: {ARQUIVO}\n"
        "Coloque o arquivo original dentro da pasta data/."
    )


# ============================================================
# 3. Listar as abas da planilha
# ============================================================

excel = pd.ExcelFile(ARQUIVO)

print("\n" + "=" * 60)
print("ABAS ENCONTRADAS")
print("=" * 60)

for aba in excel.sheet_names:
    print(f"- {aba}")


# ============================================================
# 4. Ler cada aba
# ============================================================

for aba in excel.sheet_names:

    print("\n" + "=" * 60)
    print(f"ABA: {aba}")
    print("=" * 60)

    df = pd.read_excel(ARQUIVO, sheet_name=aba)

    print(f"Linhas: {df.shape[0]}")
    print(f"Colunas: {df.shape[1]}")

    print("\nColunas:")
    for coluna in df.columns:
        print(f"- {coluna}")

    print("\nTipos de dados:")
    print(df.dtypes)

    print("\nValores ausentes:")
    print(df.isna().sum())

    print("\nPrimeiras 5 linhas:")
    print(df.head())