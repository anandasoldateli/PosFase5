# Código-fonte

| Módulo | Função |
|---|---|
| `config.py` | Caminhos e constantes (pesos oficiais do INDE, Pedras, classes do IAN) |
| `preparacao.py` | Lê a planilha, harmoniza os três anos e valida contra as regras da PEDE |
| `analises.py` | Q1–Q8, Q10 e Q11: tabelas, figuras e `outputs/resultados_analises.json` |
| `features.py` | Alvo e atributos do modelo de risco (compartilhado com o app) |
| `graficos.py` | Estilo e paleta das figuras |
| `consolidacao.py` | Gera `outputs/resultados_q1_q11.md` a partir dos JSON |
| `documento.py` | Gera o documento Word da síntese a partir dos JSON e das figuras |

Execute tudo pelo `run_pipeline.py` na raiz.
