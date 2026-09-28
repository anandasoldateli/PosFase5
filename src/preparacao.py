"""Preparação da base longitudinal PEDE 2022–2024.

Lê as três abas da planilha original, harmoniza nomes, categorias e tipos
e grava uma base única no formato aluno × ano. A planilha original nunca
é alterada.

Principais tratamentos (cada um foi verificado contra a fonte):

- INDE e Pedra do próprio ano: em 2022 estão em ``INDE 22``/``Pedra 22``;
  em 2023 em ``INDE 2023``/``Pedra 2023`` (as colunas ``INDE 23`` e
  ``Pedra 23`` da aba 2023 estão vazias); em 2024 em ``INDE 2024``/``Pedra 2024``.
- ``INDE 2024 = "INCLUIR"`` (38 alunos da Fase 9, sem indicadores) vira
  ausente no campo numérico e fica sinalizado em ``inde_incluir``.
- Fase: 2022 usa inteiros, 2023 usa ``ALFA``/``FASE n`` e 2024 usa códigos
  de turma (``1A``, ``2B``...). Todas viram ``fase`` inteira (ALFA = 0).
- Gênero: ``Menina``/``Menino`` (2022) e ``Feminino``/``Masculino`` (2023–24).
- Instituição de ensino: rótulos diferentes a cada ano, agrupados em
  ``tipo_escola`` (Pública, Privada, Outros).
- Idade 2023: parte dos valores foi gravada como data serial do Excel
  (ex.: 1900-01-08 = 8 anos); o dia da data é a idade.
- Pedra: ``Agata`` e ``Ágata`` unificadas.

Campos originais × campos analíticos
------------------------------------
Os indicadores (IAN, IDA, IEG, IAA, IPS, IPP, IPV), a defasagem e o INDE são
mantidos exatamente como na fonte. Decisões analíticas ficam em colunas
separadas, para que cada análise escolha e documente o tratamento:

- ``IAA_analise``: IAA com zeros tratados como ausentes (hipótese de não
  resposta, a confirmar com a Associação). ``iaa_zero`` sinaliza os casos.
- ``IEG_analise``: IEG = 0 em registros sem nenhuma outra avaliação (sem IDA)
  tratado como "não avaliado". Em 2024 são 101 alunos, todos das Fases 8 e 9.
  ``ieg_sem_avaliacao`` sinaliza os casos.
- ``defasagem_regra``/``fase_ideal_regra``/``IAN_regra``: cenário de
  sensibilidade que aplica a todos os anos a correspondência idade → fase
  ideal observada em 2022 e 2023 (idêntica nos dois anos). Em 2024, 301
  registros da fonte não seguem essa correspondência, e nenhuma data de
  referência única reproduz a regra de 2024. O cenário não substitui a fonte.
"""

import re

import numpy as np
import pandas as pd

from config import ABAS, ARQUIVO_BRUTO, BASE_LONGITUDINAL, ORDEM_PEDRA

COLUNAS_ANO = {
    2022: {"INDE 22": "inde", "Pedra 22": "pedra", "Idade 22": "idade",
           "Defas": "defasagem", "Fase ideal": "fase_ideal_texto",
           "Matem": "mat", "Portug": "por", "Inglês": "ing"},
    2023: {"INDE 2023": "inde", "Pedra 2023": "pedra", "Idade": "idade",
           "Defasagem": "defasagem", "Fase Ideal": "fase_ideal_texto",
           "Mat": "mat", "Por": "por", "Ing": "ing"},
    2024: {"INDE 2024": "inde", "Pedra 2024": "pedra", "Idade": "idade",
           "Defasagem": "defasagem", "Fase Ideal": "fase_ideal_texto",
           "Mat": "mat", "Por": "por", "Ing": "ing"},
}

COLUNAS_COMUNS = {
    "RA": "ra",
    "Fase": "fase_original",
    "Turma": "turma",
    "Gênero": "genero",
    "Ano ingresso": "ano_ingresso",
    "Instituição de ensino": "instituicao",
    "IAN": "IAN",
    "IDA": "IDA",
    "IEG": "IEG",
    "IAA": "IAA",
    "IPS": "IPS",
    "IPP": "IPP",
    "IPV": "IPV",
}

COLUNAS_SAIDA = [
    "ra", "ano", "fase", "fase_original", "turma", "fase_ideal",
    "defasagem", "genero", "idade", "ano_ingresso", "anos_no_programa",
    "tipo_escola", "instituicao", "inde", "inde_incluir", "pedra",
    "pedra_nivel", "IAN", "IDA", "IEG", "IAA", "IPS", "IPP", "IPV",
    "mat", "por", "ing",
    # Campos analíticos (derivados; a fonte fica preservada acima).
    "IAA_analise", "iaa_zero", "IEG_analise", "ieg_sem_avaliacao",
    "fase_ideal_regra", "defasagem_regra", "IAN_regra",
]

INDICADORES_0_10 = ["IAN", "IDA", "IEG", "IAA", "IPS", "IPP", "IPV", "inde", "mat", "por", "ing"]


def converter_fase(valor):
    """Converte qualquer codificação de fase para inteiro (ALFA = 0)."""
    if pd.isna(valor):
        return np.nan
    texto = str(valor).strip().upper()
    if texto.startswith("ALFA"):
        return 0
    numero = re.search(r"\d+", texto)
    return int(numero.group()) if numero else np.nan


def converter_idade(valor):
    """Idade em anos; datas seriais do Excel guardam a idade no dia."""
    if pd.isna(valor):
        return np.nan
    if hasattr(valor, "day"):
        return float(valor.day)
    return float(valor)


def classificar_escola(valor):
    if pd.isna(valor):
        return np.nan
    texto = str(valor).lower()
    if "públic" in texto:
        return "Pública"
    if "privada" in texto or texto in {"rede decisão", "escola jp ii"}:
        return "Privada"
    return "Outros"


def padronizar_genero(valor):
    if valor in ("Menina", "Feminino"):
        return "Feminino"
    if valor in ("Menino", "Masculino"):
        return "Masculino"
    return np.nan


def fase_ideal_por_idade(idade):
    """Correspondência idade → fase ideal observada em 2022 e 2023.

    Verificada sem nenhuma divergência nos 1.874 registros desses dois anos:
    até 8 anos → ALFA; 9 → Fase 1; 10–11 → Fase 2; 12–13 → Fase 3;
    14 → Fase 4; 15 → Fase 5; 16 → Fase 6; 17 → Fase 7; 18+ → Fase 8.
    """
    return np.select(
        [idade <= 8, idade == 9, idade <= 11, idade <= 13,
         idade == 14, idade == 15, idade == 16, idade == 17],
        [0, 1, 2, 3, 4, 5, 6, 7],
        default=8,
    ).astype(float)


def ian_por_defasagem(defasagem):
    """Regra oficial: D >= 0 → 10; -2 <= D < 0 → 5; D < -2 → 2,5."""
    return np.select([defasagem >= 0, defasagem >= -2], [10.0, 5.0], default=2.5)


def preparar_ano(df, ano):
    renomear = {**COLUNAS_COMUNS, **COLUNAS_ANO[ano]}
    # A aba 2022 não possui IPP: a coluna entra vazia, sem imputação.
    df = df.reindex(columns=list(renomear))
    dados = df.rename(columns=renomear).copy()

    dados["ano"] = ano
    dados["fase"] = dados["fase_original"].map(converter_fase)
    dados["fase_ideal"] = dados["fase_ideal_texto"].map(converter_fase)
    dados["idade"] = dados["idade"].map(converter_idade)
    dados["genero"] = dados["genero"].map(padronizar_genero)
    dados["tipo_escola"] = dados["instituicao"].map(classificar_escola)
    dados["anos_no_programa"] = ano - dados["ano_ingresso"]

    dados["inde_incluir"] = dados["inde"].astype(str).eq("INCLUIR")
    dados["inde"] = pd.to_numeric(dados["inde"], errors="coerce")

    dados["pedra"] = dados["pedra"].replace({"Agata": "Ágata", "INCLUIR": np.nan})
    dados["pedra_nivel"] = dados["pedra"].map(ORDEM_PEDRA)

    dados["fase_original"] = dados["fase_original"].astype(str)
    return dados


def adicionar_campos_analiticos(base):
    base = base.copy()
    base["iaa_zero"] = base["IAA"].eq(0)
    base["IAA_analise"] = base["IAA"].where(~base["iaa_zero"])
    base["ieg_sem_avaliacao"] = base["IEG"].eq(0) & base["IDA"].isna()
    base["IEG_analise"] = base["IEG"].where(~base["ieg_sem_avaliacao"])
    base["fase_ideal_regra"] = fase_ideal_por_idade(base["idade"])
    base["defasagem_regra"] = base["fase"] - base["fase_ideal_regra"]
    base["IAN_regra"] = ian_por_defasagem(base["defasagem_regra"])
    return base


class ErroContrato(ValueError):
    """Violação que invalida a base (interrompe o pipeline)."""


def validar(base):
    """Checa contratos da base.

    Violações de chave, domínio ou cardinalidade interrompem o pipeline.
    Anomalias conhecidas da fonte (mantidas) retornam como avisos.
    """
    erros = []
    if base["ra"].isna().any():
        erros.append(f"{base['ra'].isna().sum()} registros sem RA")
    duplicados = base.duplicated(["ra", "ano"]).sum()
    if duplicados:
        erros.append(f"{duplicados} duplicidades de RA + ano")
    if not set(base["ano"].unique()) <= {2022, 2023, 2024}:
        erros.append(f"anos fora do domínio: {sorted(base['ano'].unique())}")
    if base["fase"].isna().any() or not base["fase"].between(0, 9).all():
        erros.append("fase ausente ou fora de 0–9")
    if base["defasagem"].isna().any():
        erros.append("defasagem ausente")
    for coluna in INDICADORES_0_10:
        fora = base[coluna].notna() & ~base[coluna].between(0, 10.5)
        if fora.any():
            erros.append(f"{coluna}: {fora.sum()} valores fora de 0–10")
    if not base["IAN"].isin([2.5, 5.0, 10.0]).all():
        erros.append("IAN fora do domínio {2,5; 5; 10}")
    if erros:
        raise ErroContrato("Base inválida:\n- " + "\n- ".join(erros))

    avisos = []
    divergentes = (base["IAN"] != ian_por_defasagem(base["defasagem"])).sum()
    if divergentes:
        avisos.append(f"{divergentes} registros com IAN fora da regra oficial")
    calculada = base["fase"] - base["fase_ideal"]
    divergentes = (calculada != base["defasagem"]).sum()
    if divergentes:
        avisos.append(f"{divergentes} registros em que Defasagem != Fase - Fase ideal (anomalia da fonte, mantida)")
    por_ano = (base["fase_ideal"] != base["fase_ideal_regra"]).groupby(base["ano"]).sum()
    for ano, n in por_ano.items():
        if n:
            avisos.append(f"{ano}: {n} registros com fase ideal diferente da correspondência idade → fase de 2022/2023")
    return avisos


def construir_base():
    if not ARQUIVO_BRUTO.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_BRUTO}")

    partes = [
        preparar_ano(pd.read_excel(ARQUIVO_BRUTO, sheet_name=aba), ano)
        for aba, ano in ABAS.items()
    ]
    base = pd.concat(partes, ignore_index=True)
    return adicionar_campos_analiticos(base)[COLUNAS_SAIDA]


def main():
    base = construir_base()
    avisos = validar(base)  # interrompe antes de gravar se houver violação

    BASE_LONGITUDINAL.parent.mkdir(parents=True, exist_ok=True)
    base.to_csv(BASE_LONGITUDINAL, index=False, encoding="utf-8-sig")

    print(f"Base longitudinal: {len(base)} registros, {base['ra'].nunique()} alunos")
    print(base.groupby("ano")[["inde", "pedra", "IPP", "IDA"]].count().to_string())
    print("\nContratos OK (chaves, domínios e cardinalidade).")
    if avisos:
        print("Avisos (anomalias conhecidas da fonte, mantidas):")
        for aviso in avisos:
            print(f"- {aviso}")
    print(f"\nArquivo: {BASE_LONGITUDINAL}")


if __name__ == "__main__":
    main()
