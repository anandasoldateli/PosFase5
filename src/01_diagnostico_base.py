import pandas as pd
from pathlib import Path


ARQUIVO = Path("data/BASE DE DADOS PEDE 2024 - DATATHON.xlsx")
ABAS = ["PEDE2022", "PEDE2023", "PEDE2024"]

INDICADORES = [
    "INDE 22",
    "INDE 23",
    "INDE 2024",
    "IAA",
    "IEG",
    "IPS",
    "IPP",
    "IDA",
    "IPV",
    "IAN",
    "Defasagem",
    "Defas",
]


def carregar_bases():
    if not ARQUIVO.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {ARQUIVO}"
        )

    return {
        aba: pd.read_excel(ARQUIVO, sheet_name=aba)
        for aba in ABAS
    }


def resumo_geral(bases):
    print("\n" + "=" * 70)
    print("DIAGNÓSTICO DA BASE")
    print("=" * 70)

    for nome, df in bases.items():
        print(
            f"{nome}: "
            f"{len(df)} alunos | "
            f"{len(df.columns)} colunas"
        )


def diagnostico_missing(bases):
    print("\n" + "=" * 70)
    print("COLUNAS COM MUITOS VALORES AUSENTES")
    print("=" * 70)

    for nome, df in bases.items():
        missing = (
            df.isna()
            .mean()
            .mul(100)
            .round(1)
            .sort_values(ascending=False)
        )

        criticas = missing[missing >= 50]

        print(f"\n{nome}:")

        if criticas.empty:
            print("  Nenhuma coluna com >= 50% ausente.")
        else:
            for coluna, percentual in criticas.items():
                print(f"  - {coluna}: {percentual}%")


def diagnostico_tipos(bases):
    print("\n" + "=" * 70)
    print("COLUNAS COM TIPOS NÃO NUMÉRICOS NOS INDICADORES")
    print("=" * 70)

    for nome, df in bases.items():
        print(f"\n{nome}:")

        encontradas = False

        for coluna in INDICADORES:
            if coluna not in df.columns:
                continue

            tipo = str(df[coluna].dtype)

            if tipo not in ["float64", "float32", "int64", "int32"]:
                print(f"  - {coluna}: {tipo}")
                encontradas = True

        if not encontradas:
            print("  Nenhuma inconsistência de tipo encontrada.")


def diagnostico_categoricas(bases):
    print("\n" + "=" * 70)
    print("CATEGORIAS IMPORTANTES")
    print("=" * 70)

    categorias = [
        "Fase",
        "Gênero",
        "Pedra 20",
        "Pedra 21",
        "Pedra 22",
        "Pedra 23",
        "Pedra 2024",
        "Ativo/ Inativo",
    ]

    for nome, df in bases.items():
        print(f"\n{nome}:")

        for coluna in categorias:
            if coluna not in df.columns:
                continue

            valores = df[coluna].dropna().unique()

            print(
                f"  - {coluna}: "
                f"{len(valores)} categorias"
            )


def diagnostico_indicadores(bases):
    print("\n" + "=" * 70)
    print("COBERTURA DOS INDICADORES")
    print("=" * 70)

    for nome, df in bases.items():
        print(f"\n{nome}:")

        for coluna in INDICADORES:
            if coluna not in df.columns:
                continue

            preenchidos = df[coluna].notna().sum()
            total = len(df)
            percentual = round(preenchidos / total * 100, 1)

            print(
                f"  - {coluna}: "
                f"{percentual}% preenchido"
            )


def main():
    bases = carregar_bases()

    resumo_geral(bases)
    diagnostico_missing(bases)
    diagnostico_tipos(bases)
    diagnostico_categoricas(bases)
    diagnostico_indicadores(bases)

    print("\n" + "=" * 70)
    print("DIAGNÓSTICO CONCLUÍDO")
    print("=" * 70)


if __name__ == "__main__":
    main()