"""Gera a síntese Q1–Q11 a partir dos resultados calculados.

Todos os números vêm de ``outputs/resultados_analises.json`` (gerado por
``analises.py``) e ``outputs/resultados_modelo.json`` (gerado pelo notebook
do modelo). Nenhum valor é digitado à mão.
"""

import json

from config import PASTA_OUTPUTS, RESULTADOS_ANALISES, RESULTADOS_MODELO

SAIDA = PASTA_OUTPUTS / "resultados_q1_q11.md"


def br(valor, casas=1):
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(valor, casas=1):
    return f"{br(valor, casas)}%"


def fmt_p(p):
    if p < 0.001:
        return "p < 0,001"
    return f"p = {br(p, 3)}"


def ic(par, casas=3):
    return f"{br(par[0], casas)}–{br(par[1], casas)}"


def carregar_json(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(f"JSON não estrito: {c}")))


def gerar(a, m):
    d, q1, q2, q3, q4, q5, q6, q7, q8, q10, q11 = (
        a["diagnostico"], a["Q1"], a["Q2"], a["Q3"], a["Q4"], a["Q5"],
        a["Q6"], a["Q7"], a["Q8"], a["Q10"], a["Q11"])
    anos = ["2022", "2023", "2024"]
    L = []
    w = L.append

    w("# Resultados consolidados — Datathon Passos Mágicos (Q1–Q11)\n")
    w("> Arquivo gerado automaticamente por `src/consolidacao.py`. Não editar à mão."
      " Resultados observacionais: associação não implica causalidade.\n")

    w("## Base\n")
    w("- Registros por ano: " + ", ".join(f"{k}: {v}" for k, v in d["registros_por_ano"].items())
      + f"; {d['alunos_distintos']} alunos distintos; {d['alunos_3_anos']} presentes nos três anos.")
    w(f"- INDE/Pedra de 2023 preenchidos para {sum(q10['distribuicao_n']['2023'].values())} alunos"
      " (colunas `INDE 2023`/`Pedra 2023` da aba PEDE2023).")
    w("- IAA = 0: " + ", ".join(f"{k}: {v}" for k, v in d["iaa_zero"].items())
      + " (hipótese de não resposta, a confirmar).")
    w(f"- IEG = 0 em 2024: {d['ieg_zero_2024']} registros, dos quais {d['ieg_sem_avaliacao_2024']} sem nenhuma outra avaliação"
      f" (Fases 8 e 9). IEG médio 2024: {br(d['ieg_medio_2024']['todos'], 2)} com todos,"
      f" {br(d['ieg_medio_2024']['sem_nao_avaliados'], 2)} sem os não avaliados.")
    w(f"- Fase ideal: 2022 e 2023 seguem a mesma correspondência idade → fase; em 2024,"
      f" {d['fase_ideal_diverge_regra']['2024']} registros divergem dela.")
    w(f"- IPS 2023 com distribuição concentrada (valor 2,52 em {d['ips_moda_2023'].get('2.52')} alunos);"
      f" IPP inexistente em 2022; {d['inde_incluir_2024']} alunos com INDE 2024 = \"INCLUIR\";"
      f" {d['defasagem_inconsistente_fonte']} registros com Defasagem ≠ Fase − Fase ideal na fonte.\n")

    w("## Q1 — Adequação do nível (IAN), entre anos\n")
    for ano in anos:
        c, p = q1["contagem"][ano], q1["percentual"][ano]
        w(f"- {ano}: em fase {c['Em fase']} ({pct(p['Em fase'])}), moderada {c['Moderada']} ({pct(p['Moderada'])}),"
          f" severa {c['Severa']} ({pct(p['Severa'])}). IAN médio {br(q1['ian_medio'][ano], 2)}.")
    cf, cr = q1["coorte_pct_defasagem_negativa"], q1["coorte_pct_defasagem_negativa_regra"]
    w(f"- Mesmos {q1['coorte_n']} alunos nos três anos, % com D < 0: fonte {pct(cf['2022'])} → {pct(cf['2023'])} → {pct(cf['2024'])};"
      f" sensibilidade com a regra idade → fase de 2022/23: {pct(cr['2024'])} em 2024.\n")

    w("## Q2 — Desempenho acadêmico (IDA)\n")
    w("- IDA médio: " + "; ".join(f"{a}: {br(q2['media'][a], 2)}" for a in anos)
      + ". IDA ≤ 5: " + "; ".join(f"{a}: {pct(q2['pct_ate_5'][a])}" for a in anos) + ".")
    for k, v in q2["variacao_individual"].items():
        w(f"- Mesmos alunos {k.replace('->', '→')} (n = {v['n']}): variação média {br(v['delta_medio'], 2)},"
          f" mediana {br(v['delta_mediano'], 2)}; Wilcoxon de postos sinalizados {fmt_p(v['p_wilcoxon'])}.")
    w(f"- Fases exibidas (n ≥ 15 em todos os anos): {q2['fases_exibidas']}; excluídas: {q2['fases_excluidas_n_minimo']}.\n")

    w("## Q3 — Engajamento (IEG)\n")
    for ano in anos:
        c = q3["corr"][ano]
        w(f"- {ano}: r(IEG, IDA) = {br(c['IEG_IDA']['r'], 3)} (n = {c['IEG_IDA']['n']}); r(IEG, IPV) = {br(c['IEG_IPV']['r'], 3)}"
          f" (n = {c['IEG_IPV']['n']}); {fmt_p(max(c['IEG_IDA']['p'], c['IEG_IPV']['p']))}.")
    w("")

    w("## Q4 — Autoavaliação (IAA), comparação exploratória\n")
    for ano in anos:
        al = q4["alinhamento"][ano]
        w(f"- {ano} (IAA > 0, n = {al['n']}): IAA mais de 2 pontos acima do IDA em {pct(al['pct_iaa_acima'])};"
          f" diferença mediana {br(al['gap_mediano'], 1)}; r(IAA, IDA) = {br(q4['corr'][ano]['IAA_IDA']['r'], 3)}.")
    w("")

    w("## Q5 — Aspectos psicossociais (IPS)\n")
    for k, v in q5["antecedencia"].items():
        g = v["taxas_por_grupo"]
        o = v["or_queda_IDA_por_dp_IPS"]
        w(f"- {k.replace('->', '→')} (n = {v['n']}): queda de IDA ≥ 1 em {pct(g['IPS baixo']['queda_IDA'])} (IPS baixo, n = {int(g['IPS baixo']['n'])})"
          f" vs {pct(g['Demais']['queda_IDA'])} (demais); razão de chances por 1 DP de IPS {br(o['or'], 2)}"
          f" (IC 95% {ic(o['ic95'], 2)}).")
    w("")

    w("## Q6 — Aspectos psicopedagógicos (IPP)\n")
    for ano in ["2023", "2024"]:
        e = q6["em_fase_vs_defasados"][ano]
        w(f"- {ano}: IPP em fase {br(e['ipp_em_fase'], 2)} (n = {e['n_em_fase']}) vs defasados {br(e['ipp_defasados'], 2)}"
          f" (n = {e['n_defasados']}), Mann-Whitney {fmt_p(e['p_mannwhitney'])}; r(IPP, IAN) = {br(q6['corr'][ano]['pearson'], 3)}.")
    w("")

    w("## Q7 — Ponto de virada (IPV)\n")
    for ano in anos:
        coef = sorted(q7["coef_padronizados"][ano].items(), key=lambda kv: -kv[1])[:3]
        w(f"- {ano} (n = {q7['n'][ano]}, R² = {br(q7['r2'][ano], 2)}): maiores coeficientes padronizados "
          + ", ".join(f"{k} {br(v, 2)}" for k, v in coef) + ".")
    w("")

    w("## Q8 — Multidimensionalidade (INDE)\n")
    for ano, v in q8["verificacao_formula"].items():
        w(f"- Fórmula oficial reproduzida em {ano}: R² = {br(v['r2'], 5)}, erro máximo {br(v['erro_absoluto_max'], 4)} (n = {v['n']}).")
    g = q8["potencial_aritmetico"]["2024"]["ganho_inde_se_10"]
    w("- Potencial aritmético (2024): ganho de INDE se o indicador fosse 10: "
      + ", ".join(f"{k} +{br(v, 2)}" for k, v in sorted(g.items(), key=lambda kv: -kv[1])) + ".")
    p = q8["perfis"]["2024"]["por_numero_de_indicadores_altos"]
    w("- INDE médio (2024) por nº de dimensões (IDA, IEG, IPS, IPP) na mediana ou acima: "
      + ", ".join(f"{k}: {br(v['mean'], 2)} (n = {int(v['count'])})" for k, v in p.items()) + ".\n")

    w("## Q9 — Modelo de risco de redução de D\n")
    t = m["teste_modelo_escolhido"]
    w(f"- Evento: {m['alvo']}. População: {m['populacao']}.")
    w(f"- Treino {m['pares_treino']} pares (2022→23), teste {m['pares_teste']} pares (2023→24). Modelo: {m['modelo_escolhido']}.")
    w(f"- Teste: ROC-AUC {br(t['roc_auc'], 3)} (IC 95% {ic(t['roc_auc_ic95'])}); AP {br(t['ap'], 3)} (IC 95% {ic(t['ap_ic95'])});"
      f" prevalência {pct(m['prevalencia_teste'] * 100)}; Brier {br(t['brier'], 3)}.")
    ma = m["metricas_alto"]
    w(f"- Faixa Alto (limiar {br(m['limiar_alto'], 3)}): precisão {pct(ma['precisão'] * 100)}, recall {pct(ma['recall'] * 100)}.")
    top = m["captura_top"][0]
    w(f"- Acompanhando os {top['acompanhar top']}: {top['eventos capturados']} eventos ({pct(top['% do total de eventos'])}),"
      f" lift {br(top['lift vs aleatório'], 1)}×.")
    s = m["sensibilidade_regra_2024"]
    w(f"- Sensibilidade à regra de fase ideal de 2024: {s['rotulos_alterados_teste']} rótulos mudam; ROC-AUC {br(s['roc_auc_rotulos_regra'], 3)}.")
    anterior = next(v for v in m["sensibilidade_atributos"] if v["variante"].startswith("Alvo anterior"))
    w(f"- Alvo da versão anterior com os mesmos atributos e protocolo: ROC-AUC {br(anterior['ROC-AUC (teste)'], 3)}.\n")

    w("## Q10 — Pedras e INDE\n")
    for ano in anos:
        dist = q10["distribuicao_pct"][ano]
        w(f"- {ano}: " + ", ".join(f"{k} {pct(v)}" for k, v in dist.items()) + ".")
    w("- Aplicar cortes 6/7/8 diverge da Pedra oficial em: "
      + ", ".join(f"{k}: {v}" for k, v in q10["divergencias_regra_6_7_8"].items()) + " registros.")
    for k, v in q10["transicoes"].items():
        w(f"- {k.replace('->', '→')} (n = {v['n']}): avançou {pct(v['avancou'])}, permaneceu {pct(v['permaneceu'])}, recuou {pct(v['recuou'])}.")
    for pedra, v in q10["coorte_por_pedra_inicial"].items():
        w(f"- Coorte {pedra} 2022 (n = {v['n']}): INDE {br(v['2022'], 2)} → {br(v['2023'], 2)} → {br(v['2024'], 2)}.")
    w("")

    w("## Q11 — Insights adicionais\n")
    nr = q11["nao_reaparecimento"]
    ev = nr["2022->2023"]
    w(f"- Não reaparecimento na base de 2023: {pct(ev['pct'])} dos alunos de 2022; INDE {br(ev['inde_ausentes'], 2)} (ausentes)"
      f" vs {br(ev['inde_presentes'], 2)} (presentes). {nr['ausentes_2023_que_reaparecem_2024']} dos {nr['ausentes_2023']} ausentes reaparecem em 2024.")
    evp = q10["nao_reaparecimento_por_pedra"]["2022->2023"]["pct"]
    w("- Não reaparecimento por Pedra (2022→2023): " + ", ".join(f"{k} {pct(v)}" for k, v in evp.items()) + ".")
    tp = q11["taxa_promocao_por_fase"]
    w(f"- Promoção de fase 2023→2024: Fase 5 {pct(tp['5']['2023'])}, Fase 7 {pct(tp['7']['2023'])}, ALFA {pct(tp['0']['2023'])}.")
    w("- Evento por quartil de INDE: " + ", ".join(f"Q{k} {pct(v['pct'])}" for k, v in q11["evento_por_quartil_inde"].items())
      + f"; ROC-AUC do INDE sozinho = {br(q11['auc_inde_sozinho'], 3)}.")
    return "\n".join(L) + "\n"


def main():
    analises = carregar_json(RESULTADOS_ANALISES)
    modelo = carregar_json(RESULTADOS_MODELO)
    SAIDA.write_text(gerar(analises, modelo), encoding="utf-8")
    print(f"Síntese: {SAIDA}")


if __name__ == "__main__":
    main()
