import joblib
import pandas as pd
import streamlit as st

from src.features import (
    IDADE_INICIAL_FASE,
    faixa_de_risco,
    validar_entrada,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ARQUIVO_MODELO = "models/modelo_risco_defasagem.joblib"

artefatos = joblib.load(ARQUIVO_MODELO)

modelo = artefatos["modelo"]
atributos = artefatos["atributos"]
limiar_medio = artefatos["limiar_medio"]
limiar_alto = artefatos["limiar_alto"]

nome_modelo = artefatos["nome_modelo"]
evento = artefatos["evento"]
uso = artefatos["uso"]
limitacoes = artefatos["limitacoes"]


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Passos Mágicos - Risco de Defasagem",
    page_icon="🎓",
    layout="wide",
)


# ============================================================
# CABEÇALHO
# ============================================================

st.title("Passos Mágicos - Risco de Defasagem")

st.write(
    "Ferramenta de apoio à identificação de estudantes com maior "
    "probabilidade de redução da adequação entre sua fase efetiva "
    "e a fase ideal no ano seguinte."
)

st.info(
    "O modelo estima a probabilidade de redução da adequação entre "
    "a fase em que o estudante está e a fase considerada ideal para "
    "sua idade. O resultado é um indicador de apoio à priorização, "
    "e não um diagnóstico individual."
)


# ============================================================
# INFORMAÇÕES DO ESTUDANTE
# ============================================================

st.subheader("Informações do estudante")

coluna1, coluna2 = st.columns(2)

with coluna1:
    fase = st.number_input(
        "Fase atual",
        min_value=0,
        max_value=7,
        value=0,
        step=1,
        help=(
            "Informe a fase atual do estudante. "
            "O modelo considera as fases 0 a 7."
        ),
    )

with coluna2:
    idade = st.number_input(
        "Idade",
        min_value=5,
        max_value=30,
        value=7,
        step=1,
        help="Idade registrada no ano de referência.",
    )


# ============================================================
# CÁLCULO AUTOMÁTICO DA IDADE RELATIVA À FASE
# ============================================================

idade_relativa_fase = idade - IDADE_INICIAL_FASE[int(fase)]

st.caption(
    f"Idade relativa à fase calculada automaticamente: "
    f"{idade_relativa_fase}"
)


# ============================================================
# DEFASAGEM E TRAJETÓRIA
# ============================================================

st.subheader("Defasagem e trajetória")

coluna1, coluna2, coluna3 = st.columns(3)

with coluna1:
    defasagem = st.number_input(
        "Defasagem",
        min_value=-8.0,
        max_value=8.0,
        value=0.0,
        step=1.0,
        help=(
            "Diferença entre a fase efetiva do estudante e a fase ideal. "
            "Valores negativos indicam atraso em relação à fase ideal."
        ),
    )

with coluna2:
    anos_no_programa = st.number_input(
        "Anos no programa",
        min_value=0,
        max_value=20,
        value=0,
        step=1,
        help="Número de anos desde o ingresso no programa.",
    )

with coluna3:
    genero_feminino = st.selectbox(
        "Feminino?",
        options=[0, 1],
        format_func=lambda valor: (
            "Sim" if valor == 1 else "Não"
        ),
        help="Variável utilizada pelo modelo: 1 = feminino.",
    )


# ============================================================
# CONTEXTO ESCOLAR
# ============================================================

st.subheader("Contexto escolar")

escola_publica = st.selectbox(
    "Tipo de escola",
    options=[0, 1],
    format_func=lambda valor: (
        "Pública" if valor == 1 else "Não pública"
    ),
    help="Variável utilizada pelo modelo: 1 = escola pública.",
)


# ============================================================
# INDICADORES
# ============================================================

st.subheader("Indicadores do estudante")

coluna1, coluna2, coluna3 = st.columns(3)

with coluna1:
    IDA = st.number_input(
        "IDA - Desempenho acadêmico",
        min_value=0.0,
        max_value=10.0,
        value=5.0,
        step=0.1,
    )

with coluna2:
    IEG = st.number_input(
        "IEG - Engajamento",
        min_value=0.0,
        max_value=10.0,
        value=5.0,
        step=0.1,
    )

with coluna3:
    IAA = st.number_input(
        "IAA - Autoavaliação",
        min_value=0.0,
        max_value=10.0,
        value=5.0,
        step=0.1,
    )


coluna1, coluna2, coluna3 = st.columns(3)

with coluna1:
    IPV = st.number_input(
        "IPV - Ponto de virada",
        min_value=0.0,
        max_value=10.0,
        value=5.0,
        step=0.1,
    )

with coluna2:
    mat = st.number_input(
        "Nota de Matemática",
        min_value=0.0,
        max_value=10.0,
        value=5.0,
        step=0.1,
    )

with coluna3:
    por = st.number_input(
        "Nota de Português",
        min_value=0.0,
        max_value=10.0,
        value=5.0,
        step=0.1,
    )


inde = st.number_input(
    "INDE",
    min_value=0.0,
    max_value=10.0,
    value=5.0,
    step=0.1,
)


# ============================================================
# MONTAGEM DOS DADOS DE ENTRADA
# ============================================================

dados_entrada = pd.DataFrame(
    [
        {
            "fase": fase,
            "idade": idade,
            "idade_relativa_fase": idade_relativa_fase,
            "defasagem": defasagem,
            "anos_no_programa": anos_no_programa,
            "genero_feminino": genero_feminino,
            "escola_publica": escola_publica,
            "IDA": IDA,
            "IEG": IEG,
            "IAA": IAA,
            "IPV": IPV,
            "mat": mat,
            "por": por,
            "inde": inde,
        }
    ]
)


# ============================================================
# PREVISÃO
# ============================================================

st.subheader("Previsão")

if st.button("Calcular risco", type="primary"):

    X, erros = validar_entrada(dados_entrada)

    if erros[0]:

        st.error("Não foi possível realizar a previsão.")

        for erro in erros[0]:
            st.write(f"- {erro}")

    else:

        X_modelo = X[atributos]

        probabilidade = modelo.predict_proba(X_modelo)[0, 1]

        faixa = str(
            faixa_de_risco(
                probabilidade,
                limiar_medio,
                limiar_alto,
            ).item()
        )

        st.subheader("Resultado da previsão")

        coluna1, coluna2 = st.columns(2)

        with coluna1:
            st.metric(
                "Probabilidade estimada",
                f"{probabilidade:.1%}",
            )

        with coluna2:
            st.metric(
                "Faixa de risco",
                faixa,
            )

        if faixa == "Alto":

            st.error(
                "Faixa de risco alto segundo os critérios "
                "operacionais definidos no modelo."
            )

        elif faixa == "Médio":

            st.warning(
                "Faixa de risco médio segundo os critérios "
                "operacionais definidos no modelo."
            )

        else:

            st.success(
                "Faixa de risco baixo segundo os critérios "
                "operacionais definidos no modelo."
            )


# ============================================================
# SOBRE O MODELO
# ============================================================

with st.expander("Sobre o modelo"):

    st.write(f"**Modelo utilizado:** {nome_modelo}")

    st.write(
        "**Evento previsto:** redução da adequação entre a fase "
        "efetiva e a fase ideal do estudante no ano seguinte."
    )

    st.write(
        "O modelo utiliza informações disponíveis no fechamento "
        "do ano de referência para estimar a probabilidade do "
        "evento no ano seguinte."
    )

    st.write(
        "**Faixas operacionais:** "
        f"Baixo < {limiar_medio:.3f}; "
        f"Médio entre {limiar_medio:.3f} e {limiar_alto:.3f}; "
        f"Alto >= {limiar_alto:.3f}."
    )


# ============================================================
# USO E LIMITAÇÕES
# ============================================================

with st.expander("Uso e limitações"):

    st.warning(
        "Esta ferramenta é um instrumento de apoio à priorização. "
        "A previsão não deve ser interpretada como diagnóstico "
        "individual nem como certeza sobre a trajetória futura "
        "do estudante."
    )

    if isinstance(uso, (list, tuple)):

        for item in uso:
            st.write(f"- {item}")

    elif uso:

        st.write(uso)

    if limitacoes:

        st.write("**Limitações registradas no modelo:**")

        if isinstance(limitacoes, (list, tuple)):

            for limitacao in limitacoes:
                st.write(f"- {limitacao}")

        else:

            st.write(limitacoes)