"""Análises das perguntas Q1–Q8, Q10 e Q11 do Datathon.

Cada função lê a base longitudinal preparada, grava tabelas em
``outputs/tabelas``, figuras em ``outputs/figuras`` e devolve um dicionário
com os números citados no documento final. Nada é digitado à mão: o
documento e a consolidação leem ``outputs/resultados_analises.json``.

Convenções
- Resultados são associações observacionais, nunca efeitos causais.
- Indicadores da fonte são preservados; ``IAA_analise`` e ``IEG_analise``
  (ver ``preparacao.py``) são usados quando o indicador é analisado como
  construto, com sensibilidade quando relevante. O INDE oficial é mantido.
- Faixas (tercis, quartis) são definidas por valor, sem separar alunos com
  o mesmo valor; limites e n de cada faixa são publicados.

A Q9 (modelo preditivo) está no notebook ``notebooks/modelo_risco_defasagem.ipynb``.
"""

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import roc_auc_score

from config import (
    ANOS,
    BASE_LONGITUDINAL,
    CLASSES_IAN,
    INDICADORES,
    PASTA_TABELAS,
    PEDRAS,
    PESOS_INDE,
    RESULTADOS_ANALISES,
)
from features import ALVO, construir_pares, decompor_evento
from graficos import (
    CORES_ANO,
    NEUTRO,
    ORDINAL,
    SERIES,
    SUPERFICIE,
    fmt_br,
    nova_figura,
    salvar,
)

N_MINIMO_FASE = 15


def carregar():
    return pd.read_csv(BASE_LONGITUDINAL)


def salvar_tabela(df, nome):
    PASTA_TABELAS.mkdir(parents=True, exist_ok=True)
    df.to_csv(PASTA_TABELAS / f"{nome}.csv", encoding="utf-8-sig")


def pares_consecutivos(base, colunas):
    """Une cada aluno no ano t às suas informações no ano t+1."""
    seguinte = base[["ra", "ano"] + colunas].copy()
    seguinte["ano"] -= 1
    return base.merge(seguinte, on=["ra", "ano"], suffixes=("", "_seg"), validate="one_to_one")


def correlacao(df, x, y, metodo="pearson"):
    dados = df[[x, y]].dropna()
    if len(dados) < 3:
        return {"r": None, "p": None, "n": len(dados)}
    funcao = stats.pearsonr if metodo == "pearson" else stats.spearmanr
    r, p = funcao(dados[x], dados[y])
    return {"r": round(float(r), 3), "p": float(p), "n": int(len(dados))}


def faixas_por_valor(serie, n_grupos, rotulos):
    """Faixas por quantis do valor, sem separar empates.

    Alunos com o mesmo valor sempre ficam na mesma faixa; por isso os grupos
    podem ter tamanhos diferentes. Devolve as faixas e os limites usados.
    """
    limites = np.unique(np.quantile(serie.dropna(), np.linspace(0, 1, n_grupos + 1)))
    if len(limites) - 1 < n_grupos:
        rotulos = rotulos[: len(limites) - 1]
    faixas = pd.cut(serie, bins=limites, labels=rotulos, include_lowest=True)
    return faixas, [round(float(v), 3) for v in limites]


def rotulo_ano(eixo, anos=ANOS):
    eixo.set_xticks(range(len(anos)))
    eixo.set_xticklabels([str(a) for a in anos])


def rotulo_fase(f):
    return "ALFA" if f == 0 else f"Fase {f}"


# ---------------------------------------------------------------------------
# Diagnóstico
# ---------------------------------------------------------------------------

def diagnostico(base):
    cobertura = (
        base.groupby("ano")[INDICADORES + ["inde", "pedra"]]
        .apply(lambda g: g.notna().mean() * 100)
        .round(1)
    )
    cobertura["IEG_efetivo"] = base.groupby("ano")["IEG_analise"].apply(lambda s: s.notna().mean() * 100).round(1)
    cobertura["IAA_sem_zero"] = base.groupby("ano")["IAA_analise"].apply(lambda s: s.notna().mean() * 100).round(1)
    salvar_tabela(cobertura, "diagnostico_cobertura")

    b24 = base[base["ano"] == 2024]
    n_anos = base.groupby("ra")["ano"].nunique()
    iaa_2023 = base.loc[base.ano == 2023, "IAA"]
    return {
        "registros_por_ano": base.groupby("ano").size().to_dict(),
        "alunos_distintos": int(base["ra"].nunique()),
        "alunos_3_anos": int((n_anos == 3).sum()),
        "alunos_2_ou_mais_anos": int((n_anos >= 2).sum()),
        "cobertura_pct": {int(a): linha.to_dict() for a, linha in cobertura.iterrows()},
        "inde_incluir_2024": int(base["inde_incluir"].sum()),
        "iaa_zero": base.groupby("ano")["iaa_zero"].sum().astype(int).to_dict(),
        "iaa_zero_pct_2023": round(float(iaa_2023.eq(0).sum() / iaa_2023.notna().sum() * 100), 1),
        "ieg_zero_2024": int(b24["IEG"].eq(0).sum()),
        "ieg_sem_avaliacao_2024": int(b24["ieg_sem_avaliacao"].sum()),
        "ieg_sem_avaliacao_fases": {int(k): int(v) for k, v in
                                    b24.loc[b24["ieg_sem_avaliacao"], "fase"].value_counts().sort_index().items()},
        "ieg_medio_2024": {
            "todos": round(float(b24["IEG"].mean()), 2),
            "sem_nao_avaliados": round(float(b24["IEG_analise"].mean()), 2),
        },
        "ips_moda_2023": {str(k): int(v) for k, v in
                          base.loc[base.ano == 2023, "IPS"].value_counts().head(3).items()},
        "defasagem_inconsistente_fonte": int(((base["fase"] - base["fase_ideal"]) != base["defasagem"]).sum()),
        "fase_ideal_diverge_regra": (base["fase_ideal"] != base["fase_ideal_regra"]).groupby(base["ano"]).sum().astype(int).to_dict(),
        "fase_ideal_2024_diferenca": {
            int(k): int(v) for k, v in
            (b24["fase_ideal"] - b24["fase_ideal_regra"]).value_counts().sort_index().items()},
    }


# ---------------------------------------------------------------------------
# Q1 — IAN / Defasagem (entre anos)
# ---------------------------------------------------------------------------

def q1(base):
    base = base.assign(classe_ian=base["IAN"].map(CLASSES_IAN), classe_ian_regra=base["IAN_regra"].map(CLASSES_IAN))
    classes = list(CLASSES_IAN.values())
    contagem = pd.crosstab(base["ano"], base["classe_ian"])[classes]
    percentual = (contagem.div(contagem.sum(axis=1), axis=0) * 100).round(1)
    contagem_regra = pd.crosstab(base["ano"], base["classe_ian_regra"]).reindex(columns=classes, fill_value=0)
    percentual_regra = (contagem_regra.div(contagem_regra.sum(axis=1), axis=0) * 100).round(1)
    salvar_tabela(contagem, "q1_classes_ian_contagem")
    salvar_tabela(percentual, "q1_classes_ian_pct")
    salvar_tabela(percentual_regra, "q1_classes_ian_pct_sensibilidade_regra")
    salvar_tabela(pd.crosstab(base["ano"], base["defasagem"]), "q1_defasagem_distribuicao")

    # Coorte: mesmos alunos nos três anos (controla mudança de composição).
    n_anos = base.groupby("ra")["ano"].nunique()
    coorte = base[base["ra"].isin(n_anos[n_anos == 3].index)]
    coorte_medias = coorte.groupby("ano")[["IAN", "defasagem"]].mean().round(2)
    coorte_pct = pd.DataFrame({
        "Fonte": coorte.groupby("ano")["defasagem"].apply(lambda s: (s < 0).mean() * 100),
        "Regra idade 2022/23": coorte.groupby("ano")["defasagem_regra"].apply(lambda s: (s < 0).mean() * 100),
    }).round(1)
    salvar_tabela(coorte_pct, "q1_coorte_pct_defasados_fonte_vs_regra")

    fig, eixo = nova_figura(7.5, 3.8)
    cores = {"Em fase": SERIES[2], "Moderada": SERIES[3], "Severa": SERIES[1]}
    acumulado = np.zeros(len(percentual))
    for classe in percentual.columns:
        valores = percentual[classe].values
        barras = eixo.barh(range(len(ANOS)), valores, left=acumulado, color=cores[classe],
                           edgecolor=SUPERFICIE, linewidth=2, label=classe, height=0.6)
        for barra, valor, n in zip(barras, valores, contagem[classe].values):
            if valor >= 6:
                eixo.text(barra.get_x() + barra.get_width() / 2, barra.get_y() + barra.get_height() / 2,
                          f"{fmt_br(valor)}%\n({n})", ha="center", va="center", fontsize=8.5, color="#0b0b0b")
            else:
                eixo.text(101, barra.get_y() + barra.get_height() / 2, f"Severa\n{fmt_br(valor)}% ({n})",
                          ha="left", va="center", fontsize=8, color="#52514e", clip_on=False)
        acumulado += valores
    eixo.set_yticks(range(len(ANOS)))
    eixo.set_yticklabels([str(a) for a in ANOS])
    eixo.invert_yaxis()
    eixo.set_xlim(0, 100)
    eixo.grid(axis="y", visible=False)
    eixo.grid(axis="x", visible=True)
    eixo.set_xlabel("% dos alunos (classificação da fonte)")
    eixo.set_title("Classificação do IAN por ano (defasagem)")
    eixo.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    salvar(fig, "q1_classes_ian")

    fig, eixo = nova_figura(7.5, 3.6)
    for coluna, cor in [("Fonte", SERIES[0]), ("Regra idade 2022/23", NEUTRO)]:
        serie = coorte_pct[coluna]
        eixo.plot(range(3), serie.values, marker="o", markersize=7, color=cor, label=coluna)
        eixo.text(2.08, serie.values[-1], f"{fmt_br(serie.values[-1])}%", va="center", fontsize=9, color="#52514e")
    rotulo_ano(eixo)
    eixo.set_xlim(-0.2, 2.45)
    eixo.set_ylim(0, 80)
    eixo.set_ylabel("% com defasagem (D < 0)")
    eixo.set_title(f"Mesmos {coorte['ra'].nunique()} alunos: fonte × regra idade→fase de 2022/23")
    eixo.legend(loc="lower left")
    salvar(fig, "q1_coorte_sensibilidade")

    return {
        "contagem": {int(a): l.to_dict() for a, l in contagem.iterrows()},
        "percentual": {int(a): l.to_dict() for a, l in percentual.iterrows()},
        "percentual_regra": {int(a): l.to_dict() for a, l in percentual_regra.iterrows()},
        "pct_defasagem_negativa": base.groupby("ano")["defasagem"].apply(lambda s: (s < 0).mean() * 100).round(1).to_dict(),
        "pct_defasagem_negativa_regra": base.groupby("ano")["defasagem_regra"].apply(lambda s: (s < 0).mean() * 100).round(1).to_dict(),
        "ian_medio": base.groupby("ano")["IAN"].mean().round(2).to_dict(),
        "coorte_n": int(coorte["ra"].nunique()),
        "coorte_ian": coorte_medias["IAN"].to_dict(),
        "coorte_defasagem": coorte_medias["defasagem"].to_dict(),
        "coorte_pct_defasagem_negativa": coorte_pct["Fonte"].to_dict(),
        "coorte_pct_defasagem_negativa_regra": coorte_pct["Regra idade 2022/23"].to_dict(),
        "corr_ian_defasagem": {int(a): correlacao(g, "IAN", "defasagem")["r"] for a, g in base.groupby("ano")},
    }


# ---------------------------------------------------------------------------
# Q2 — IDA ao longo de anos e fases
# ---------------------------------------------------------------------------

def q2(base):
    resumo = base.groupby("ano")["IDA"].agg(["count", "mean", "median"]).round(2)
    faixas = base.dropna(subset=["IDA"]).groupby("ano")["IDA"].agg(
        ate_5=lambda s: (s <= 5).mean() * 100,
        acima_8_5=lambda s: (s > 8.5).mean() * 100,
    ).round(1)
    escopo = base[base["fase"] <= 8]
    por_fase = escopo.pivot_table(index="fase", columns="ano", values="IDA", aggfunc="mean").round(2)
    n_fase = escopo.pivot_table(index="fase", columns="ano", values="IDA", aggfunc="count").fillna(0).astype(int)
    salvar_tabela(resumo, "q2_ida_ano")
    salvar_tabela(faixas, "q2_ida_faixas")
    salvar_tabela(por_fase, "q2_ida_fase_ano")
    salvar_tabela(n_fase, "q2_ida_fase_ano_n")

    fases_exibidas = [int(f) for f in por_fase.index if f <= 7 and n_fase.loc[f].min() >= N_MINIMO_FASE]
    ranking = {}
    for ano in ANOS:
        serie = por_fase.loc[fases_exibidas, ano]
        ranking[int(ano)] = {"maior": int(serie.idxmax()), "menor": int(serie.idxmin())}

    # Variação individual (mesmos alunos em anos consecutivos).
    pares = pares_consecutivos(base, ["IDA"]).dropna(subset=["IDA", "IDA_seg"])
    pares["delta"] = pares["IDA_seg"] - pares["IDA"]
    variacao = {}
    for ano, grupo in pares.groupby("ano"):
        teste = stats.wilcoxon(grupo["delta"])
        variacao[f"{ano}->{ano + 1}"] = {
            "n": int(len(grupo)),
            "delta_medio": round(float(grupo["delta"].mean()), 2),
            "delta_mediano": round(float(grupo["delta"].median()), 2),
            "pct_melhorou": round(float((grupo["delta"] > 0).mean() * 100), 1),
            "pct_piorou": round(float((grupo["delta"] < 0).mean() * 100), 1),
            "wilcoxon_estatistica": float(teste.statistic),
            "p_wilcoxon": float(teste.pvalue),
        }

    fig, eixo = nova_figura(7.5, 4.0)
    for ano in ANOS:
        serie = por_fase.loc[fases_exibidas, ano]
        eixo.plot(range(len(fases_exibidas)), serie.values, marker="o", markersize=6,
                  color=CORES_ANO[ano], label=str(ano))
    eixo.set_xticks(range(len(fases_exibidas)))
    eixo.set_xticklabels([rotulo_fase(f) for f in fases_exibidas])
    eixo.set_ylabel("IDA médio")
    eixo.set_ylim(4.5, 8.5)
    eixo.set_title(f"IDA médio por fase e ano (fases com n ≥ {N_MINIMO_FASE} em todos os anos)")
    eixo.legend(ncol=3, loc="upper right")
    salvar(fig, "q2_ida_fase_ano")

    return {
        "media": resumo["mean"].to_dict(),
        "mediana": resumo["median"].to_dict(),
        "n": resumo["count"].astype(int).to_dict(),
        "pct_ate_5": faixas["ate_5"].to_dict(),
        "pct_acima_8_5": faixas["acima_8_5"].to_dict(),
        "por_fase": {int(f): {int(a): v for a, v in l.dropna().items()} for f, l in por_fase.iterrows()},
        "n_por_fase": {int(f): {int(a): int(v) for a, v in l.items()} for f, l in n_fase.iterrows()},
        "fases_exibidas": fases_exibidas,
        "fases_excluidas_n_minimo": [int(f) for f in por_fase.index if f <= 7 and int(f) not in fases_exibidas],
        "ranking_fases_exibidas": ranking,
        "variacao_individual": variacao,
    }


# ---------------------------------------------------------------------------
# Q3 — IEG × IDA e IPV
# ---------------------------------------------------------------------------

def q3(base):
    resultado = {"corr": {}, "por_quartil_ieg": {}, "limites_quartis": {}}
    linhas = []
    for ano, grupo in base.groupby("ano"):
        resultado["corr"][int(ano)] = {
            "IEG_IDA": correlacao(grupo, "IEG_analise", "IDA"),
            "IEG_IPV": correlacao(grupo, "IEG_analise", "IPV"),
            "IEG_IDA_spearman": correlacao(grupo, "IEG_analise", "IDA", "spearman")["r"],
            "IEG_IPV_spearman": correlacao(grupo, "IEG_analise", "IPV", "spearman")["r"],
        }
        # Quartis definidos só entre alunos com IEG, IDA e IPV (grupos comparáveis).
        dados = grupo.dropna(subset=["IEG_analise", "IDA", "IPV"]).copy()
        dados["quartil"], limites = faixas_por_valor(dados["IEG_analise"], 4, ["Q1", "Q2", "Q3", "Q4"])
        medias = dados.groupby("quartil", observed=True).agg(n=("IDA", "size"), IDA=("IDA", "mean"), IPV=("IPV", "mean")).round(2)
        resultado["por_quartil_ieg"][int(ano)] = {q: l.to_dict() for q, l in medias.iterrows()}
        resultado["limites_quartis"][int(ano)] = limites
        for q, l in medias.iterrows():
            linhas.append({"ano": ano, "quartil_IEG": q, **l.to_dict()})
    resultado["ieg_medio"] = base.groupby("ano")["IEG_analise"].mean().round(2).to_dict()
    resultado["ieg_medio_fonte"] = base.groupby("ano")["IEG"].mean().round(2).to_dict()
    tabela = pd.DataFrame(linhas)
    salvar_tabela(tabela.set_index(["ano", "quartil_IEG"]), "q3_ida_ipv_por_quartil_ieg")

    fig, eixos = nova_figura(9.0, 3.8, ncols=2, sharey=True)
    for eixo, indicador in zip(eixos, ["IDA", "IPV"]):
        largura = 0.26
        for i, ano in enumerate(ANOS):
            t = tabela[tabela["ano"] == ano]
            eixo.bar(np.arange(len(t)) + (i - 1) * largura, t[indicador], width=largura - 0.03,
                     color=CORES_ANO[ano], label=str(ano))
        eixo.set_xticks(range(4))
        eixo.set_xticklabels(["Q1\n(menor IEG)", "Q2", "Q3", "Q4\n(maior IEG)"])
        eixo.set_title(f"{indicador} médio por quartil de IEG")
        eixo.set_ylim(0, 10)
    eixos[0].legend(ncol=3, loc="upper left")
    salvar(fig, "q3_ieg_quartis")
    return resultado


# ---------------------------------------------------------------------------
# Q4 — IAA × IDA / IEG (comparação exploratória)
# ---------------------------------------------------------------------------

def q4(base):
    """O IAA mede percepção sobre si, estudos, família, amigos, Associação e
    professores (PEDE, Tabela 40); não é uma previsão da nota. A diferença
    IAA − IDA compara duas escalas diferentes e é tratada como exploratória."""
    resultado = {"corr": {}, "corr_com_zeros": {}, "alinhamento": {}, "sensibilidade_corte": {}}
    linhas = []
    for ano, grupo in base.groupby("ano"):
        resultado["corr"][int(ano)] = {
            "IAA_IDA": correlacao(grupo, "IAA_analise", "IDA"),
            "IAA_IEG": correlacao(grupo, "IAA_analise", "IEG_analise"),
        }
        resultado["corr_com_zeros"][int(ano)] = {
            "IAA_IDA": correlacao(grupo, "IAA", "IDA")["r"],
            "IAA_IEG": correlacao(grupo, "IAA", "IEG")["r"],
        }
        dados = grupo.dropna(subset=["IAA_analise", "IDA"])
        gap = dados["IAA_analise"] - dados["IDA"]
        alinhamento = {
            "n": int(len(dados)),
            "gap_medio": round(float(gap.mean()), 2),
            "gap_mediano": round(float(gap.median()), 2),
            "pct_iaa_acima": round(float((gap > 2).mean() * 100), 1),
            "pct_proximo": round(float(gap.abs().le(2).mean() * 100), 1),
            "pct_iaa_abaixo": round(float((gap < -2).mean() * 100), 1),
        }
        resultado["alinhamento"][int(ano)] = alinhamento
        resultado["sensibilidade_corte"][int(ano)] = {
            str(c): round(float((gap > c).mean() * 100), 1) for c in [1, 2, 3]}
        linhas.append({"ano": ano, **alinhamento})
        resultado.setdefault("gap_com_zeros", {})[int(ano)] = round(float((grupo["IAA"] - grupo["IDA"]).mean()), 2)
    resultado["iaa_medio"] = base.groupby("ano")["IAA"].mean().round(2).to_dict()
    resultado["iaa_medio_sem_zeros"] = base.groupby("ano")["IAA_analise"].mean().round(2).to_dict()
    tabela = pd.DataFrame(linhas).set_index("ano")
    salvar_tabela(tabela, "q4_iaa_menos_ida")

    fig, eixo = nova_figura(7.5, 3.8)
    categorias = [("pct_iaa_abaixo", "IAA abaixo do IDA (> 2 pontos)", SERIES[0]),
                  ("pct_proximo", "Diferença de até 2 pontos", NEUTRO),
                  ("pct_iaa_acima", "IAA acima do IDA (> 2 pontos)", SERIES[1])]
    acumulado = np.zeros(len(tabela))
    for coluna, rotulo, cor in categorias:
        valores = tabela[coluna].values
        barras = eixo.barh(range(len(tabela)), valores, left=acumulado, color=cor,
                           edgecolor=SUPERFICIE, linewidth=2, label=rotulo, height=0.6)
        for barra, valor in zip(barras, valores):
            if valor >= 6:
                eixo.text(barra.get_x() + barra.get_width() / 2, barra.get_y() + barra.get_height() / 2,
                          f"{fmt_br(valor)}%", ha="center", va="center", fontsize=9,
                          color="white" if cor != NEUTRO else "#0b0b0b")
        acumulado += valores
    eixo.set_yticks(range(len(tabela)))
    eixo.set_yticklabels([f"{a}\n(n={tabela.loc[a, 'n']})" for a in tabela.index])
    eixo.invert_yaxis()
    eixo.set_xlim(0, 100)
    eixo.grid(axis="y", visible=False)
    eixo.grid(axis="x", visible=True)
    eixo.set_title("Diferença entre IAA e IDA (exploratória; IAA > 0)")
    eixo.legend(ncol=1, loc="upper left", bbox_to_anchor=(1.01, 1))
    salvar(fig, "q4_iaa_menos_ida")
    return resultado


# ---------------------------------------------------------------------------
# Q5 — IPS antecede quedas?
# ---------------------------------------------------------------------------

def razao_chances(grupo, preditor, desfecho):
    """Razão de chances por 1 desvio-padrão do preditor (IPS padronizado no ano), com IC 95%."""
    x = (grupo[preditor] - grupo[preditor].mean()) / grupo[preditor].std()
    modelo = sm.Logit(grupo[desfecho].astype(int), sm.add_constant(x)).fit(disp=0)
    coef, (inf, sup) = modelo.params.iloc[1], modelo.conf_int().iloc[1]
    return {"or": round(float(np.exp(coef)), 3), "ic95": [round(float(np.exp(inf)), 3), round(float(np.exp(sup)), 3)],
            "p": float(modelo.pvalues.iloc[1]), "n": int(len(grupo))}


def q5(base):
    resultado = {"corr_mesmo_ano": {}, "antecedencia": {}}
    for ano, grupo in base.groupby("ano"):
        resultado["corr_mesmo_ano"][int(ano)] = {
            "IPS_IDA": correlacao(grupo, "IPS", "IDA"),
            "IPS_IEG": correlacao(grupo, "IPS", "IEG_analise"),
        }
    resultado["ips_medio"] = base.groupby("ano")["IPS"].mean().round(2).to_dict()

    pares = pares_consecutivos(base, ["IDA", "IEG_analise"])
    pares["queda_IDA"] = (pares["IDA_seg"] - pares["IDA"]) <= -1
    pares["queda_IEG"] = (pares["IEG_analise_seg"] - pares["IEG_analise"]) <= -1
    linhas = []
    for ano, grupo in pares.groupby("ano"):
        grupo = grupo.dropna(subset=["IPS", "IDA", "IDA_seg", "IEG_analise", "IEG_analise_seg"]).copy()
        # IPS é muito discreto: tercis por valor ficariam desbalanceados. Usa-se
        # "IPS baixo" = até o 1º tercil do ano (empates incluídos) × demais.
        corte = float(np.quantile(grupo["IPS"], 1 / 3))
        grupo["grupo_IPS"] = np.where(grupo["IPS"] <= corte, "IPS baixo", "Demais")
        taxas = grupo.groupby("grupo_IPS").agg(
            n=("queda_IDA", "size"), queda_IDA=("queda_IDA", "mean"), queda_IEG=("queda_IEG", "mean"))
        taxas = taxas.reindex(["IPS baixo", "Demais"])
        taxas[["queda_IDA", "queda_IEG"]] = (taxas[["queda_IDA", "queda_IEG"]] * 100).round(1)
        resultado["antecedencia"][f"{ano}->{ano + 1}"] = {
            "n": int(len(grupo)),
            "corte_ips_baixo": round(corte, 2),
            "corr_IPS_deltaIDA": correlacao(grupo.assign(d=grupo["IDA_seg"] - grupo["IDA"]), "IPS", "d"),
            "corr_IPS_deltaIEG": correlacao(grupo.assign(d=grupo["IEG_analise_seg"] - grupo["IEG_analise"]), "IPS", "d"),
            "taxas_por_grupo": {t: l.to_dict() for t, l in taxas.iterrows()},
            "or_queda_IDA_por_dp_IPS": razao_chances(grupo, "IPS", "queda_IDA"),
            "or_queda_IEG_por_dp_IPS": razao_chances(grupo, "IPS", "queda_IEG"),
        }
        for t, l in taxas.iterrows():
            linhas.append({"transicao": f"{ano}→{ano + 1}", "grupo_IPS": t, **l.to_dict()})
    tabela = pd.DataFrame(linhas)
    salvar_tabela(tabela.set_index(["transicao", "grupo_IPS"]), "q5_quedas_por_grupo_ips")

    fig, eixos = nova_figura(9.0, 3.8, ncols=2, sharey=True)
    for eixo, (coluna, titulo) in zip(eixos, [("queda_IDA", "Queda de IDA ≥ 1 no ano seguinte"),
                                               ("queda_IEG", "Queda de IEG ≥ 1 no ano seguinte")]):
        largura = 0.38
        for i, transicao in enumerate(tabela["transicao"].unique()):
            t = tabela[tabela["transicao"] == transicao]
            eixo.bar(np.arange(len(t)) + (i - 0.5) * largura, t[coluna], width=largura - 0.04,
                     color=SERIES[i], label=f"{transicao} (n = {int(t['n'].iloc[0])} | {int(t['n'].iloc[1])})")
        eixo.set_xticks(range(2))
        eixo.set_xticklabels(["IPS baixo (≤ 1º tercil do ano)", "Demais"])
        eixo.set_title(titulo, fontsize=10.5)
        eixo.set_ylabel("% dos alunos")
        eixo.set_ylim(0, 50)
    eixos[0].legend(loc="upper left", fontsize=8.5)
    salvar(fig, "q5_ips_antecedencia")
    return resultado


# ---------------------------------------------------------------------------
# Q6 — IPP × IAN
# ---------------------------------------------------------------------------

def q6(base):
    resultado = {"corr": {}, "ipp_por_classe": {}, "kruskal": {}}
    dados = base.dropna(subset=["IPP"]).assign(classe_ian=lambda d: d["IAN"].map(CLASSES_IAN))
    for ano, grupo in dados.groupby("ano"):
        resultado["corr"][int(ano)] = {
            "pearson": correlacao(grupo, "IPP", "IAN")["r"],
            "spearman": correlacao(grupo, "IPP", "IAN", "spearman")["r"],
            "n": int(len(grupo)),
        }
        tabela = grupo.groupby("classe_ian")["IPP"].agg(["count", "mean"]).round(2)
        resultado["ipp_por_classe"][int(ano)] = {c: l.to_dict() for c, l in tabela.iterrows()}
        incluidas = [c for c, g in grupo.groupby("classe_ian") if len(g) >= 5]
        amostras = [grupo.loc[grupo["classe_ian"] == c, "IPP"].values for c in incluidas]
        resultado["kruskal"][int(ano)] = {"p": float(stats.kruskal(*amostras).pvalue), "classes_incluidas": incluidas,
                                          "criterio": "classes com n >= 5"}
        em_fase = grupo[grupo["classe_ian"] == "Em fase"]["IPP"]
        defasados = grupo[grupo["classe_ian"] != "Em fase"]["IPP"]
        resultado.setdefault("em_fase_vs_defasados", {})[int(ano)] = {
            "ipp_em_fase": round(float(em_fase.mean()), 2), "n_em_fase": int(len(em_fase)),
            "ipp_defasados": round(float(defasados.mean()), 2), "n_defasados": int(len(defasados)),
            "p_mannwhitney": float(stats.mannwhitneyu(em_fase, defasados).pvalue),
        }
        cruz = pd.crosstab(grupo["IPP"] < 6, grupo["classe_ian"] != "Em fase", normalize="index") * 100
        n_baixo = int((grupo["IPP"] < 6).sum())
        resultado.setdefault("pct_defasado_por_ipp_baixo", {})[int(ano)] = {
            "ipp_menor_6": round(float(cruz.loc[True, True]), 1) if True in cruz.index else None,
            "n_ipp_menor_6": n_baixo,
            "ipp_6_ou_mais": round(float(cruz.loc[False, True]), 1),
            "n_ipp_6_ou_mais": int(len(grupo) - n_baixo),
        }
    tabela = dados.pivot_table(index="classe_ian", columns="ano", values="IPP", aggfunc="mean").round(2)
    tabela = tabela.reindex(list(CLASSES_IAN.values()))
    salvar_tabela(tabela, "q6_ipp_por_classe_ian")

    fig, eixo = nova_figura(7.5, 3.8)
    largura = 0.36
    for i, ano in enumerate(tabela.columns):
        valores = tabela[ano].values
        barras = eixo.bar(np.arange(len(tabela)) + (i - 0.5) * largura, valores, width=largura - 0.04,
                          color=CORES_ANO[ano], label=str(ano))
        for barra, v in zip(barras, valores):
            if not np.isnan(v):
                eixo.text(barra.get_x() + barra.get_width() / 2, v + 0.1, fmt_br(v, 2),
                          ha="center", fontsize=8.5, color="#52514e")
    eixo.set_xticks(range(len(tabela)))
    n_classe = dados.pivot_table(index="classe_ian", columns="ano", values="IPP", aggfunc="count")
    eixo.set_xticklabels([
        f"{c} (IAN {fmt_br(k, 1).replace(',0', '')})\nn = {int(n_classe.loc[c, 2023])} | {int(n_classe.loc[c, 2024])}"
        for k, c in CLASSES_IAN.items()])
    eixo.set_ylim(0, 10)
    eixo.set_ylabel("IPP médio")
    eixo.set_title("IPP médio por classificação de defasagem (IAN)")
    eixo.legend(loc="upper right", ncol=2)
    salvar(fig, "q6_ipp_por_ian")
    return resultado


# ---------------------------------------------------------------------------
# Q7 — Associações com o IPV
# ---------------------------------------------------------------------------

def q7(base):
    """Regressões lineares separadas por ano (associação, não causalidade).
    O conjunto de indicadores difere entre anos: não há IPP em 2022."""
    resultado = {"coef_padronizados": {}, "r2": {}, "n": {}, "corr": {}, "corr_ano_seguinte": {}}
    explicativas_por_ano = {
        2022: ["IDA", "IEG_analise", "IAA_analise", "IPS", "IAN"],
        2023: ["IDA", "IEG_analise", "IAA_analise", "IPS", "IPP", "IAN"],
        2024: ["IDA", "IEG_analise", "IAA_analise", "IPS", "IPP", "IAN"],
    }
    nomes = {"IEG_analise": "IEG", "IAA_analise": "IAA"}
    linhas = []
    for ano, grupo in base.groupby("ano"):
        x = explicativas_por_ano[ano]
        dados = grupo.dropna(subset=x + ["IPV"])
        z = (dados[x] - dados[x].mean()) / dados[x].std()
        alvo = (dados["IPV"] - dados["IPV"].mean()) / dados["IPV"].std()
        modelo = LinearRegression().fit(z, alvo)
        coef = {nomes.get(k, k): float(v) for k, v in zip(x, np.round(modelo.coef_, 3))}
        resultado["coef_padronizados"][int(ano)] = coef
        resultado["r2"][int(ano)] = round(float(modelo.score(z, alvo)), 3)
        resultado["n"][int(ano)] = int(len(dados))
        resultado["corr"][int(ano)] = {nomes.get(v, v): correlacao(grupo, "IPV", v)["r"] for v in x}
        for k, v in coef.items():
            linhas.append({"ano": ano, "indicador": k, "coef": v})

    pares = pares_consecutivos(base, ["IPV"])
    for ano, grupo in pares.groupby("ano"):
        resultado["corr_ano_seguinte"][f"{ano}->{ano + 1}"] = {
            nomes.get(v, v): correlacao(grupo, v, "IPV_seg")["r"]
            for v in ["IDA", "IEG_analise", "IAA_analise", "IPS", "IPP", "IAN", "IPV"]
        }
    tabela = pd.DataFrame(linhas).pivot(index="indicador", columns="ano", values="coef")
    tabela = tabela.reindex(["IDA", "IEG", "IPP", "IAA", "IPS", "IAN"])
    salvar_tabela(tabela, "q7_ipv_coeficientes")

    fig, eixo = nova_figura(7.5, 4.0)
    largura = 0.26
    for i, ano in enumerate(tabela.columns):
        eixo.bar(np.arange(len(tabela)) + (i - 1) * largura, tabela[ano].fillna(0), width=largura - 0.03,
                 color=CORES_ANO[ano],
                 label=f"{ano} (R² = {fmt_br(resultado['r2'][int(ano)], 2)}; n = {resultado['n'][int(ano)]})")
    eixo.axhline(0, color="#c3c2b7", linewidth=0.8)
    eixo.set_xticks(range(len(tabela)))
    eixo.set_xticklabels(tabela.index)
    eixo.set_ylabel("Coeficiente padronizado")
    eixo.set_title("Associação de cada indicador com o IPV (regressão por ano)")
    eixo.legend(loc="upper right", fontsize=8.5)
    eixo.text(2, -0.08, "IPP não medido\nem 2022", ha="center", fontsize=7.5, color="#898781")
    salvar(fig, "q7_ipv_associacoes")
    return resultado


# ---------------------------------------------------------------------------
# Q8 — Combinações e INDE
# ---------------------------------------------------------------------------

def q8(base):
    """O INDE oficial usa os indicadores da fonte (inclusive IAA = 0)."""
    resultado = {"verificacao_formula": {}, "potencial_aritmetico": {}, "perfis": {}}
    pesos = pd.Series(PESOS_INDE)
    for ano, grupo in base.groupby("ano"):
        if ano == 2022:
            continue
        dados = grupo[(grupo["fase"] <= 7)].dropna(subset=list(pesos.index) + ["inde"])
        calculado = (dados[pesos.index] * pesos).sum(axis=1)
        erro = (calculado - dados["inde"]).abs()
        resultado["verificacao_formula"][int(ano)] = {
            "n": int(len(dados)),
            "erro_absoluto_max": round(float(erro.max()), 4),
            "r2": round(float(1 - ((calculado - dados["inde"]) ** 2).sum()
                               / ((dados["inde"] - dados["inde"].mean()) ** 2).sum()), 5),
        }
        medias = dados[pesos.index].mean()
        resultado["potencial_aritmetico"][int(ano)] = {
            "n": int(len(dados)),
            "media_indicador": medias.round(2).to_dict(),
            "ganho_inde_se_10": (pesos * (10 - medias)).round(3).to_dict(),
            "ganho_inde_mais_1_ponto": pesos.to_dict(),
        }

    # Perfis: cada indicador na mediana anual ou acima (≥ mediana) × abaixo.
    linhas = []
    for ano, grupo in base.groupby("ano"):
        dados = grupo.dropna(subset=["IDA", "IEG", "IPS", "IPP", "inde"]).copy()
        if dados.empty:
            continue
        for ind in ["IDA", "IEG", "IPS", "IPP"]:
            dados[f"{ind}_alto"] = dados[ind] >= dados[ind].median()
        dados["n_altos"] = dados[[f"{i}_alto" for i in ["IDA", "IEG", "IPS", "IPP"]]].sum(axis=1)
        dados["perfil"] = dados.apply(
            lambda l: " + ".join(i for i in ["IDA", "IEG", "IPS", "IPP"] if l[f"{i}_alto"]) or "nenhum", axis=1)
        por_n = dados.groupby("n_altos")["inde"].agg(["count", "mean"]).round(2)
        por_perfil = dados.groupby("perfil")["inde"].agg(["count", "mean"]).round(2).sort_values("mean", ascending=False)
        resultado["perfis"][int(ano)] = {
            "n": int(len(dados)),
            "por_numero_de_indicadores_altos": {int(k): l.to_dict() for k, l in por_n.iterrows()},
            "top_perfis": {k: l.to_dict() for k, l in por_perfil[por_perfil["count"] >= 20].head(5).iterrows()},
            "pares_altos": {},
        }
        for a, b in [("IDA", "IEG"), ("IDA", "IPP"), ("IEG", "IPP"), ("IDA", "IPS"), ("IEG", "IPS"), ("IPS", "IPP")]:
            ambos = dados[dados[f"{a}_alto"] & dados[f"{b}_alto"]]["inde"]
            resultado["perfis"][int(ano)]["pares_altos"][f"{a}+{b}"] = {"inde": round(float(ambos.mean()), 2), "n": int(len(ambos))}
        for k, l in por_perfil.iterrows():
            linhas.append({"ano": ano, "perfil": k, **l.to_dict()})
    salvar_tabela(pd.DataFrame(linhas).set_index(["ano", "perfil"]), "q8_perfis_inde")

    ganho = pd.DataFrame({a: v["ganho_inde_se_10"] for a, v in resultado["potencial_aritmetico"].items()})
    ganho = ganho.sort_values(2024, ascending=True)
    salvar_tabela(ganho, "q8_potencial_aritmetico_inde")

    fig, eixo = nova_figura(7.5, 4.0)
    valores = ganho[2024]
    cores = [SERIES[0] if PESOS_INDE[i] == 0.2 else "#86b6ef" for i in valores.index]
    barras = eixo.barh(range(len(valores)), valores.values, color=cores, height=0.6)
    for barra, (ind, v) in zip(barras, valores.items()):
        eixo.text(v + 0.01, barra.get_y() + barra.get_height() / 2,
                  f"+{fmt_br(v, 2)}  (peso {fmt_br(PESOS_INDE[ind] * 100, 0)}%)",
                  va="center", fontsize=9, color="#52514e")
    eixo.set_yticks(range(len(valores)))
    eixo.set_yticklabels(valores.index)
    eixo.grid(axis="y", visible=False)
    eixo.grid(axis="x", visible=True)
    eixo.set_xlim(0, max(valores) * 1.45)
    eixo.set_xlabel("Espaço aritmético: ganho de INDE se o indicador fosse 10 (média 2024)")
    eixo.set_title("Potencial aritmético de cada indicador no INDE")
    salvar(fig, "q8_potencial_aritmetico_inde")

    n_altos = pd.DataFrame({a: {k: v["mean"] for k, v in p["por_numero_de_indicadores_altos"].items()}
                            for a, p in resultado["perfis"].items()})
    fig, eixo = nova_figura(7.5, 3.8)
    for ano in n_altos.columns:
        eixo.plot(n_altos.index, n_altos[ano], marker="o", markersize=7, color=CORES_ANO[ano], label=str(ano))
    eixo.set_xticks(range(5))
    eixo.set_xlabel("Quantos de IDA, IEG, IPS e IPP estão na mediana do ano ou acima")
    eixo.set_ylabel("INDE médio")
    eixo.set_title("INDE médio pelo número de dimensões ≥ mediana")
    eixo.legend(loc="upper left")
    salvar(fig, "q8_inde_por_numero_de_dimensoes")
    return resultado


# ---------------------------------------------------------------------------
# Q10 — Pedras e INDE ao longo do tempo
# ---------------------------------------------------------------------------

def reaparecimento(base, validos=None):
    """Percentual de alunos do ano t que NÃO aparecem na base do ano t+1.

    Não é taxa de evasão: a base não distingue desligamento, conclusão,
    interrupção temporária ou falta de avaliação.
    """
    validos = base if validos is None else validos
    saida = {}
    for ano in [2022, 2023]:
        seguinte = set(base.loc[base["ano"] == ano + 1, "ra"])
        atual = validos[validos["ano"] == ano].assign(ausente=lambda d: ~d["ra"].isin(seguinte))
        saida[ano] = atual
    return saida


def q10(base):
    resultado = {"distribuicao_pct": {}, "transicoes": {}, "coorte_por_pedra_inicial": {}}
    validos = base[base["pedra"].isin(PEDRAS)]
    dist = pd.crosstab(validos["ano"], validos["pedra"])[PEDRAS]
    dist_pct = (dist.div(dist.sum(axis=1), axis=0) * 100).round(1)
    salvar_tabela(dist_pct, "q10_distribuicao_pedras_pct")
    resultado["distribuicao_pct"] = {int(a): l.to_dict() for a, l in dist_pct.iterrows()}
    resultado["distribuicao_n"] = {int(a): l.to_dict() for a, l in dist.iterrows()}

    # Limites de INDE observados em cada Pedra oficial, por ano (critérios podem mudar).
    limites = validos.groupby(["ano", "pedra"])["inde"].agg(["min", "max", "count"]).round(3)
    limites = limites.reindex(pd.MultiIndex.from_product([ANOS, PEDRAS], names=["ano", "pedra"]))
    salvar_tabela(limites, "q10_limites_inde_por_pedra")
    resultado["limites_observados"] = {f"{a}|{p}": l.to_dict() for (a, p), l in limites.iterrows()}
    corte_678 = pd.cut(validos["inde"], [-np.inf, 6, 7, 8, np.inf], labels=PEDRAS, right=False).astype(str)
    resultado["divergencias_regra_6_7_8"] = (corte_678 != validos["pedra"]).groupby(validos["ano"]).sum().astype(int).to_dict()

    linhas = []
    for inicio, fim in [(2022, 2023), (2023, 2024), (2022, 2024)]:
        a = validos[validos["ano"] == inicio][["ra", "pedra_nivel", "inde"]]
        b = validos[validos["ano"] == fim][["ra", "pedra_nivel", "inde"]]
        m = a.merge(b, on="ra", suffixes=("_ini", "_fim"))
        direcao = np.sign(m["pedra_nivel_fim"] - m["pedra_nivel_ini"])
        info = {
            "n": int(len(m)),
            "avancou": round(float((direcao > 0).mean() * 100), 1),
            "permaneceu": round(float((direcao == 0).mean() * 100), 1),
            "recuou": round(float((direcao < 0).mean() * 100), 1),
            "delta_inde_medio": round(float((m["inde_fim"] - m["inde_ini"]).mean()), 2),
        }
        resultado["transicoes"][f"{inicio}->{fim}"] = info
        linhas.append({"transicao": f"{inicio}→{fim}", **info})
    salvar_tabela(pd.DataFrame(linhas).set_index("transicao"), "q10_transicoes")

    # Mesmos alunos nos três anos, agrupados pela Pedra de 2022 (INDE contínuo).
    n_anos = validos.groupby("ra")["ano"].nunique()
    coorte = validos[validos["ra"].isin(n_anos[n_anos == 3].index)]
    pedra_inicial = coorte[coorte["ano"] == 2022].set_index("ra")["pedra"]
    coorte = coorte.assign(pedra_2022=coorte["ra"].map(pedra_inicial))
    trajetoria = coorte.pivot_table(index="pedra_2022", columns="ano", values="inde", aggfunc="mean").reindex(PEDRAS).round(2)
    n_coorte = coorte[coorte["ano"] == 2022]["pedra_2022"].value_counts().reindex(PEDRAS)
    salvar_tabela(trajetoria, "q10_coorte_inde_por_pedra_inicial")
    for pedra in PEDRAS:
        resultado["coorte_por_pedra_inicial"][pedra] = {
            "n": int(n_coorte[pedra]), **{int(a): float(v) for a, v in trajetoria.loc[pedra].items()}}
    resultado["coorte_n"] = int(coorte["ra"].nunique())

    indicadores = ["IDA", "IEG_analise", "IAA_analise", "IPS", "IPP", "IPV", "IAN"]
    perfil = validos.groupby(["ano", "pedra"])[indicadores].mean().round(2)
    salvar_tabela(perfil, "q10_indicadores_por_pedra")

    resultado["nao_reaparecimento_por_pedra"] = {
        f"{ano}->{ano + 1}": {
            "pct": d.groupby("pedra")["ausente"].mean().mul(100).round(1).reindex(PEDRAS).to_dict(),
            "n": d.groupby("pedra").size().reindex(PEDRAS).astype(int).to_dict(),
        }
        for ano, d in reaparecimento(base, validos).items()
    }

    fig, eixo = nova_figura(7.5, 3.6)
    acumulado = np.zeros(len(dist_pct))
    for pedra, cor in zip(PEDRAS, ORDINAL):
        valores = dist_pct[pedra].values
        barras = eixo.barh(range(len(dist_pct)), valores, left=acumulado, color=cor,
                           edgecolor=SUPERFICIE, linewidth=2, label=pedra, height=0.6)
        for barra, v in zip(barras, valores):
            eixo.text(barra.get_x() + barra.get_width() / 2, barra.get_y() + barra.get_height() / 2,
                      f"{fmt_br(v)}%", ha="center", va="center", fontsize=9,
                      color="#0b0b0b" if cor == ORDINAL[0] else "white")
        acumulado += valores
    eixo.set_yticks(range(len(dist_pct)))
    eixo.set_yticklabels([f"{a}\n(n={dist.loc[a].sum()})" for a in dist_pct.index])
    eixo.invert_yaxis()
    eixo.set_xlim(0, 100)
    eixo.grid(axis="y", visible=False)
    eixo.grid(axis="x", visible=True)
    eixo.set_xlabel("% dos alunos com Pedra oficial atribuída")
    eixo.set_title("Distribuição das Pedras oficiais por ano")
    eixo.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    salvar(fig, "q10_distribuicao_pedras")

    fig, eixo = nova_figura(7.5, 4.0)
    for pedra, cor in zip(PEDRAS, [SERIES[1], SERIES[3], SERIES[0], SERIES[2]]):
        serie = trajetoria.loc[pedra]
        eixo.plot(range(3), serie.values, marker="o", markersize=7, color=cor,
                  label=f"{pedra} em 2022 (n={int(n_coorte[pedra])})")
        eixo.text(2.08, serie.values[-1], fmt_br(serie.values[-1], 2), va="center", fontsize=9, color="#52514e")
    rotulo_ano(eixo)
    eixo.set_xlim(-0.2, 2.4)
    eixo.set_ylabel("INDE médio")
    eixo.set_title("Mesmos alunos (3 anos): INDE por Pedra de 2022")
    eixo.legend(loc="lower right", fontsize=8.5)
    salvar(fig, "q10_coorte_inde_por_pedra")
    return resultado


# ---------------------------------------------------------------------------
# Q11 — Insights adicionais
# ---------------------------------------------------------------------------

def q11(base):
    resultado = {}
    # Mesmo alvo, escopo e população do modelo (fases 0–7, alunos presentes em t e t+1).
    pares = construir_pares(base)
    cruz = pd.crosstab(pares["promovido"], pares[ALVO])
    resultado["alvo_vs_promocao"] = {
        "nao_promovidos": int(cruz.loc[False].sum()),
        "nao_promovidos_com_evento": int(cruz.loc[False, 1]),
        "nao_promovidos_sem_evento": int(cruz.loc[False, 0]),
        "promovidos": int(cruz.loc[True].sum()),
        "promovidos_com_evento": int(cruz.loc[True, 1]),
        "eventos": int(pares[ALVO].sum()),
    }
    decomposicao = pd.crosstab(pares["ano"], decompor_evento(pares))
    salvar_tabela(decomposicao, "q11_decomposicao_evento")
    resultado["decomposicao_evento"] = {int(a): l.to_dict() for a, l in decomposicao.iterrows()}

    promocao = pares.pivot_table(index="fase", columns="ano", values="promovido", aggfunc="mean").mul(100).round(1)
    n_promo = pares.pivot_table(index="fase", columns="ano", values="promovido", aggfunc="count").fillna(0).astype(int)
    salvar_tabela(promocao, "q11_taxa_promocao_por_fase")
    salvar_tabela(n_promo, "q11_taxa_promocao_por_fase_n")
    resultado["taxa_promocao_por_fase"] = {int(f): {int(a): v for a, v in l.dropna().items()} for f, l in promocao.iterrows()}
    resultado["n_promocao_por_fase"] = {int(f): {int(a): int(v) for a, v in l.items()} for f, l in n_promo.iterrows()}

    # Associação marginal entre INDE e o evento (não prova independência).
    com_inde = pares.dropna(subset=["inde"]).copy()
    partes = []
    for ano, grupo in com_inde.groupby("ano"):
        grupo = grupo.copy()
        grupo["quartil_inde"], _ = faixas_por_valor(grupo["inde"], 4, [1, 2, 3, 4])
        partes.append(grupo)
    com_inde = pd.concat(partes)
    taxa = com_inde.groupby("quartil_inde", observed=True)[ALVO].agg(["size", "mean"])
    resultado["evento_por_quartil_inde"] = {int(k): {"n": int(l["size"]), "pct": round(float(l["mean"] * 100), 1)}
                                            for k, l in taxa.iterrows()}
    resultado["auc_inde_sozinho"] = round(float(roc_auc_score(com_inde[ALVO], -com_inde["inde"])), 3)

    # Não reaparecimento na base do ano seguinte (não é evasão comprovada).
    s22, s23, s24 = [set(base.loc[base["ano"] == a, "ra"]) for a in ANOS]
    nao_reap = {}
    for ano, atual in reaparecimento(base).items():
        nao_reap[f"{ano}->{ano + 1}"] = {
            "n": int(len(atual)),
            "pct": round(float(atual["ausente"].mean() * 100), 1),
            "inde_ausentes": round(float(atual.loc[atual["ausente"], "inde"].mean()), 2),
            "inde_presentes": round(float(atual.loc[~atual["ausente"], "inde"].mean()), 2),
        }
    nao_reap["ausentes_2023_que_reaparecem_2024"] = int(len((s22 - s23) & s24))
    nao_reap["ausentes_2023"] = int(len(s22 - s23))
    resultado["nao_reaparecimento"] = nao_reap

    escola = base.groupby(["ano", "tipo_escola"]).agg(n=("ra", "size"), inde=("inde", "mean"),
                                                     ida=("IDA", "mean"), defasagem=("defasagem", "mean")).round(2)
    salvar_tabela(escola, "q11_tipo_escola")
    resultado["tipo_escola"] = {f"{a}|{t}": l.to_dict() for (a, t), l in escola.iterrows()}

    genero = base.groupby(["ano", "genero"])[["inde", "IDA", "IEG_analise"]].mean().round(2)
    resultado["genero"] = {f"{a}|{g}": l.to_dict() for (a, g), l in genero.iterrows()}

    fig, eixo = nova_figura(7.5, 4.0)
    fases = [f for f in promocao.index if n_promo.loc[f].min() >= N_MINIMO_FASE]
    largura = 0.38
    for i, ano in enumerate([2022, 2023]):
        valores = promocao.loc[fases, ano].values
        eixo.bar(np.arange(len(fases)) + (i - 0.5) * largura, valores, width=largura - 0.04,
                 color=CORES_ANO[ano], label=f"{ano}→{ano + 1}")
    eixo.set_xticks(range(len(fases)))
    eixo.set_xticklabels([f"{rotulo_fase(f)}\nn={n_promo.loc[f, 2022]}|{n_promo.loc[f, 2023]}" for f in fases])
    eixo.set_ylim(0, 100)
    eixo.set_ylabel("% promovidos à fase seguinte")
    eixo.set_title(f"Taxa de promoção de fase (presentes nos dois anos; n ≥ {N_MINIMO_FASE})")
    eixo.legend(loc="upper left", ncol=2)
    salvar(fig, "q11_taxa_promocao")

    fig, eixo = nova_figura(7.5, 3.8)
    validos = base[base["pedra"].isin(PEDRAS)]
    ev = {f"{a}→{a + 1}": d.groupby("pedra")["ausente"].mean().mul(100).round(1).reindex(PEDRAS)
          for a, d in reaparecimento(base, validos).items()}
    largura = 0.38
    for i, (transicao, serie) in enumerate(ev.items()):
        eixo.bar(np.arange(len(PEDRAS)) + (i - 0.5) * largura, serie.values, width=largura - 0.04,
                 color=SERIES[i], label=transicao)
    eixo.set_xticks(range(len(PEDRAS)))
    eixo.set_xticklabels(PEDRAS)
    eixo.set_ylabel("% ausente na base do ano seguinte")
    eixo.set_title("Não reaparecimento na base seguinte, por Pedra")
    eixo.legend(loc="upper right")
    salvar(fig, "q11_nao_reaparecimento_por_pedra")
    return resultado


def converter_chaves(objeto):
    """JSON estrito: chaves texto, tipos nativos e NaN/inf como null."""
    if isinstance(objeto, dict):
        return {str(k): converter_chaves(v) for k, v in objeto.items()}
    if isinstance(objeto, (list, tuple)):
        return [converter_chaves(v) for v in objeto]
    if isinstance(objeto, np.bool_):
        return bool(objeto)
    if isinstance(objeto, np.integer):
        return int(objeto)
    if isinstance(objeto, (float, np.floating)):
        return None if not np.isfinite(objeto) else float(objeto)
    return objeto


def main():
    for figura_antiga in ["q4_alinhamento_iaa_ida", "q7_ipv_determinantes", "q8_potencial_ganho_inde",
                          "q11_evasao_por_pedra"]:
        (PASTA_TABELAS.parent / "figuras" / f"{figura_antiga}.png").unlink(missing_ok=True)
    for tabela_antiga in ["q4_alinhamento_iaa_ida", "q8_potencial_ganho_inde", "q5_quedas_por_tercil_ips"]:
        (PASTA_TABELAS / f"{tabela_antiga}.csv").unlink(missing_ok=True)

    base = carregar()
    resultados = {
        "diagnostico": diagnostico(base),
        "Q1": q1(base),
        "Q2": q2(base),
        "Q3": q3(base),
        "Q4": q4(base),
        "Q5": q5(base),
        "Q6": q6(base),
        "Q7": q7(base),
        "Q8": q8(base),
        "Q10": q10(base),
        "Q11": q11(base),
    }
    RESULTADOS_ANALISES.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTADOS_ANALISES, "w", encoding="utf-8") as arquivo:
        json.dump(converter_chaves(resultados), arquivo, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"Resultados: {RESULTADOS_ANALISES}")


if __name__ == "__main__":
    main()
