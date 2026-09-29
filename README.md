# Datathon Passos Mágicos — POSTECH Data Analytics, Fase 5

Análise dos dados da PEDE (Pesquisa Extensiva do Desenvolvimento Educacional) de 2022 a 2024 da Associação Passos Mágicos. O projeto responde às 11 perguntas do Datathon e inclui um modelo preditivo do risco de **redução de D = fase efetiva − fase ideal** no ano seguinte, ou seja, de piora da adequação de nível.

## Principais resultados

Resultados observacionais: associação não implica causalidade.

| Tema | Resultado |
|---|---|
| Defasagem (Q1) | Alunos em fase na fonte: 30,1% (2022) → 53,8% (2024). Nos mesmos 468 alunos, D < 0 cai de 67,3% para 34,8% pela fonte, ou para 47,4% aplicando em 2024 a regra idade → fase de 2022/23. |
| Desempenho (Q2) | IDA sobe em 2023 (6,66) e cai em 2024 (6,35). A Fase 3 tem a menor média nos três anos. |
| INDE (Q8) | A fórmula oficial é reproduzida (R² = 1,000). O IDA tem o maior espaço aritmético de ganho. |
| Modelo (Q9) | Random Forest calibrado: ROC-AUC 0,866 (IC 95% 0,831–0,899) no teste temporal 2023→24. Os 10% de maior risco concentram 42% dos eventos. |
| Pedras (Q10) | Nos mesmos alunos, o INDE fica estável, exceto no grupo Quartzo. A distribuição agregada também reflete quem deixa de aparecer na base. |

A síntese completa, gerada a partir dos dados, está em [`outputs/resultados_q1_q11.md`](outputs/resultados_q1_q11.md). O documento Word é gerado em `outputs/`.

## Estrutura

```text
PosFase5/
├── app/
│   └── streamlit_app.py       # aplicação Streamlit
├── data/
│   ├── BASE DE DADOS PEDE 2024 - DATATHON.xlsx   # fonte (não versionada)
│   └── processed/                                # gerado pelo pipeline (não versionado)
├── src/
│   ├── config.py          # caminhos e constantes (pesos do INDE, pedras)
│   ├── preparacao.py      # leitura, harmonização, campos analíticos e contratos da base
│   ├── analises.py        # Q1–Q8, Q10 e Q11 → tabelas, figuras e JSON
│   ├── features.py        # alvo, atributos e validação de entrada (notebook e app)
│   ├── graficos.py        # estilo único das figuras
│   ├── consolidacao.py    # gera outputs/resultados_q1_q11.md a partir dos JSON
│   └── documento.py       # gera o documento Word da síntese (Q1–Q11)
├── notebooks/
│   └── modelo_risco_defasagem.ipynb   # Q9: alvo, atributos, split, modelagem, avaliação, sensibilidades
├── models/
│   └── modelo_risco_defasagem.joblib  # modelo final calibrado + limiares + limitações
├── outputs/
│   ├── figuras/            # PNG usados no documento e na apresentação
│   ├── tabelas/            # CSV de cada análise
│   ├── resultados_analises.json
│   ├── resultados_modelo.json
│   ├── resultados_q1_q11.md
│   └── Datathon_Passos_Magicos_Sintese_Q1_Q11.docx
├── run_pipeline.py
└── requirements.txt
```

## Como reproduzir

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# copie a planilha do Datathon para data/
python run_pipeline.py
```

O pipeline executa, em ordem: `preparacao.py` → `analises.py` → notebook do modelo → `consolidacao.py` → `documento.py`. Os arquivos com dados individuais (base longitudinal e risco por aluno) ficam em `data/processed/`, que não é versionado. A preparação interrompe a execução se houver violação de chave, domínio ou cardinalidade. Todos os números do documento vêm dos arquivos gerados; os JSON são estritos (sem `NaN`).

## Aplicação Streamlit

A aplicação apresenta uma interface para estimar, a partir dos indicadores informados, a faixa de risco de redução da adequação entre a fase efetiva do estudante e a fase ideal no ano seguinte.

### Acesso

A aplicação publicada está disponível em:

https://posfase5-datathon.streamlit.app/

### Execução local

Com o ambiente virtual ativado:

```bash
streamlit run app/streamlit_app.py
```

A aplicação utiliza o modelo calibrado armazenado em `models/modelo_risco_defasagem.joblib`.

A previsão é uma ferramenta de priorização baseada nos critérios do modelo e **não constitui diagnóstico individual**.

## Dados e tratamentos

A planilha tem uma aba por ano, com nomes e codificações diferentes entre elas. `src/preparacao.py` harmoniza e valida os dados. Os **valores da fonte são preservados** e os tratamentos analíticos ficam em colunas separadas.

- **INDE e Pedra do ano:** em 2023 estão em `INDE 2023`/`Pedra 2023`; as colunas `INDE 23`/`Pedra 23` dessa aba estão vazias.
- **Códigos:** fase (`4`, `FASE 4`, `4A` → 4; ALFA → 0), gênero e tipo de escola unificados entre anos.
- **Idade 2023:** parte está gravada como data serial do Excel; o dia da data é a idade.
- **Fase ideal:** 2022 e 2023 seguem a mesma correspondência idade → fase ideal; em 2024, 301 registros divergem e nenhuma data de referência única reproduz a regra. A fonte é mantida; `defasagem_regra` é um cenário de sensibilidade.
- **IEG 2024:** 101 dos 109 zeros ocorrem em registros sem nenhuma outra avaliação (Fases 8 e 9). `IEG_analise` os trata como não avaliados.
- **IAA = 0** (39, 190 e 20 registros por ano): hipótese de não resposta, a confirmar. `IAA_analise` os trata como ausentes; o INDE oficial é mantido.
- **IPS 2023:** distribuição muito diferente dos outros anos; causa não confirmada.
- **Pedras:** usadas como na fonte. Os limites de INDE observados em 2022 diferem dos de 2023/24 (ver `outputs/tabelas/q10_limites_inde_por_pedra.csv`).
- Ausência de um aluno na base do ano seguinte **não** é tratada como evasão comprovada.

## Indicadores (referência PEDE)

| Sigla | Indicador | Peso no INDE (fases 0–7) |
|---|---|---|
| IAN | Adequação de Nível | 10% |
| IDA | Desempenho Acadêmico | 20% |
| IEG | Engajamento | 20% |
| IAA | Autoavaliação | 10% |
| IPS | Psicossocial | 10% |
| IPP | Psicopedagógico | 10% |
| IPV | Ponto de Virada | 20% |

## Equipe

- Ananda Soares Soldateli
- Grecco Teixeira de Morais
