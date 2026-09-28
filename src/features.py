"""Engenharia de atributos do modelo de risco (Q9).

Usado pelo notebook de modelagem e pela aplicação Streamlit, para que o
treino e a previsão calculem os atributos exatamente da mesma forma.

Evento previsto (alvo)
----------------------
Redução de D no ano seguinte, com D = fase efetiva − fase ideal:
``defasagem[t+1] < defasagem[t]``. Em linguagem gerencial, é a **piora da
adequação de nível** do aluno de um ano para o outro.

O evento não equivale à retenção de fase nem à entrada em defasagem:

- quase todos os eventos ocorrem entre alunos não promovidos, mas uma parte
  relevante dos não promovidos não tem o evento (a fase ideal abrange mais
  de uma idade);
- o evento inclui três situações distintas: entrada em defasagem (D ≥ 0 →
  D < 0), agravamento de quem já estava defasado e perda de vantagem de quem
  continua em fase. ``decompor_evento`` separa esses casos.

População: alunos das fases 0 a 7 observados em dois anos consecutivos.
A previsão é condicional a o aluno aparecer na base do ano seguinte.
"""

import numpy as np
import pandas as pd

ALVO = "risco_reducao_D"
ALVO_SENSIBILIDADE = "risco_reducao_D_regra"

# Todos os atributos são conhecidos no fechamento do ano t (sem informação do futuro).
ATRIBUTOS = [
    "fase",
    "idade",
    "idade_relativa_fase",
    "defasagem",
    "anos_no_programa",
    "genero_feminino",
    "escola_publica",
    "IDA",
    "IEG",
    "IAA",
    "IPV",
    "mat",
    "por",
    "inde",
]

DESCRICAO_ATRIBUTOS = {
    "fase": "Fase atual na Passos Mágicos (ALFA = 0)",
    "idade": "Idade registrada no ano de referência",
    "idade_relativa_fase": "Idade menos a idade de entrada da fase (tabela oficial PEDE)",
    "defasagem": "D = fase efetiva − fase ideal (negativo = atrasado), como na fonte",
    "anos_no_programa": "Anos desde o ingresso",
    "genero_feminino": "1 = feminino",
    "escola_publica": "1 = escola pública",
    "IDA": "Desempenho acadêmico",
    "IEG": "Engajamento (0 sem outras avaliações tratado como não avaliado)",
    "IAA": "Autoavaliação (0 tratado como ausente; hipótese de não resposta)",
    "IPV": "Ponto de virada",
    "mat": "Nota de Matemática",
    "por": "Nota de Português",
    "inde": "INDE oficial (mantido como na fonte)",
}

# Fora do modelo, com justificativa:
# - IPP: não existe em 2022 (ano de treino).
# - IPS: distribuição de 2023 muito diferente dos demais anos (concentração em
#   2,52 e 7,52); a causa (mudança de instrumento?) não está confirmada.
# - IAN e Pedra: funções de defasagem e INDE (redundantes).
FASE_MAXIMA = 7  # Fase 8 (universitários) não tem fase seguinte comparável.

# Idade de entrada de cada fase (tabela oficial de equivalência ano escolar,
# fase e idade da PEDE): ALFA 7–8, Fase 1 8–9, Fase 2 10–11, Fase 3 12–13,
# Fase 4 14, Fase 5 15, Fase 6 16, Fase 7 17 anos.
IDADE_INICIAL_FASE = {0: 7, 1: 8, 2: 10, 3: 12, 4: 14, 5: 15, 6: 16, 7: 17}

# Faixas plausíveis para validar entradas (aplicação Streamlit).
FAIXAS_VALIDAS = {
    "fase": (0, FASE_MAXIMA),
    "idade": (5, 30),
    "defasagem": (-8, 8),
    "anos_no_programa": (0, 20),
    "genero_feminino": (0, 1),
    "escola_publica": (0, 1),
    "IDA": (0, 10), "IEG": (0, 10), "IAA": (0, 10), "IPV": (0, 10),
    "mat": (0, 10), "por": (0, 10), "inde": (0, 10),
}


def preparar_atributos(base):
    """Cria os atributos do modelo a partir da base longitudinal."""
    dados = base.copy()
    dados["IAA_fonte"] = dados["IAA"]
    dados["IEG_fonte"] = dados["IEG"]
    dados["IAA"] = dados["IAA_analise"]
    dados["IEG"] = dados["IEG_analise"]
    dados["genero_feminino"] = (dados["genero"] == "Feminino").astype(int)
    dados["escola_publica"] = (dados["tipo_escola"] == "Pública").astype(int)
    dados["idade_relativa_fase"] = dados["idade"] - dados["fase"].map(IDADE_INICIAL_FASE)
    return dados


def construir_pares(base):
    """Une o ano t (atributos) ao ano t+1 (alvo) para cada aluno.

    Pares sem defasagem em algum dos anos são descartados explicitamente
    (nunca convertidos em "sem evento").
    """
    dados = preparar_atributos(base)
    seguinte = dados[["ra", "ano", "defasagem", "defasagem_regra", "fase"]].rename(
        columns={"defasagem": "defasagem_seguinte", "defasagem_regra": "defasagem_regra_seguinte",
                 "fase": "fase_seguinte"})
    seguinte["ano"] -= 1
    pares = dados.merge(seguinte, on=["ra", "ano"], validate="one_to_one")
    pares = pares[pares["fase"] <= FASE_MAXIMA]
    pares = pares.dropna(subset=["defasagem", "defasagem_seguinte"]).copy()
    pares[ALVO] = (pares["defasagem_seguinte"] < pares["defasagem"]).astype(int)
    pares[ALVO_SENSIBILIDADE] = (pares["defasagem_regra_seguinte"] < pares["defasagem_regra"]).astype(int)
    pares["promovido"] = pares["fase_seguinte"] > pares["fase"]
    return pares


def decompor_evento(pares):
    """Classifica cada evento em entrada, agravamento ou perda de vantagem."""
    evento = pares[ALVO].eq(1)
    return pd.Series(np.select(
        [evento & (pares["defasagem"] >= 0) & (pares["defasagem_seguinte"] < 0),
         evento & (pares["defasagem"] < 0),
         evento & (pares["defasagem_seguinte"] >= 0)],
        ["Entrada em defasagem", "Agravamento (já defasado)", "Perda de vantagem (continua em fase)"],
        default="Sem evento"), index=pares.index)


def faixa_de_risco(probabilidade, limiar_medio, limiar_alto):
    """Converte probabilidade em faixa operacional."""
    return np.select(
        [probabilidade >= limiar_alto, probabilidade >= limiar_medio],
        ["Alto", "Médio"],
        default="Baixo",
    )


def validar_entrada(df):
    """Valida entradas para previsão. Retorna (atributos, lista de erros por linha).

    Verifica presença, tipo numérico, faixa plausível, fase elegível (0–7)
    e coerência entre idade, fase e ``idade_relativa_fase``.
    """
    faltantes = [c for c in ATRIBUTOS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Atributos ausentes: {', '.join(faltantes)}")
    X = df[ATRIBUTOS].apply(pd.to_numeric, errors="coerce")
    erros = [[] for _ in range(len(X))]
    for coluna in ATRIBUTOS:
        texto_invalido = df[coluna].notna() & X[coluna].isna()
        for i in np.where(texto_invalido)[0]:
            erros[i].append(f"{coluna}: valor não numérico")
        if coluna in FAIXAS_VALIDAS:
            minimo, maximo = FAIXAS_VALIDAS[coluna]
            fora = X[coluna].notna() & ~X[coluna].between(minimo, maximo)
            for i in np.where(fora)[0]:
                erros[i].append(f"{coluna}: {X[coluna].iloc[i]} fora de [{minimo}, {maximo}]")
    for obrigatoria in ["fase", "idade", "defasagem"]:
        for i in np.where(X[obrigatoria].isna())[0]:
            erros[i].append(f"{obrigatoria}: obrigatório")
    esperada = X["idade"] - X["fase"].map(IDADE_INICIAL_FASE)
    incoerente = X["idade_relativa_fase"].notna() & esperada.notna() & (X["idade_relativa_fase"] != esperada)
    for i in np.where(incoerente)[0]:
        erros[i].append("idade_relativa_fase incoerente com idade e fase")
    return X, erros
