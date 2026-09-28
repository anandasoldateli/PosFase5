"""Caminhos e constantes compartilhados pelo pipeline."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

ARQUIVO_BRUTO = RAIZ / "data" / "BASE DE DADOS PEDE 2024 - DATATHON.xlsx"
PASTA_PROCESSADOS = RAIZ / "data" / "processed"
BASE_LONGITUDINAL = PASTA_PROCESSADOS / "base_longitudinal.csv"

PASTA_OUTPUTS = RAIZ / "outputs"
PASTA_FIGURAS = PASTA_OUTPUTS / "figuras"
PASTA_TABELAS = PASTA_OUTPUTS / "tabelas"
RESULTADOS_ANALISES = PASTA_OUTPUTS / "resultados_analises.json"
RESULTADOS_MODELO = PASTA_OUTPUTS / "resultados_modelo.json"

PASTA_MODELOS = RAIZ / "models"
MODELO_RISCO = PASTA_MODELOS / "modelo_risco_defasagem.joblib"

ANOS = [2022, 2023, 2024]
ABAS = {"PEDE2022": 2022, "PEDE2023": 2023, "PEDE2024": 2024}

INDICADORES = ["IAN", "IDA", "IEG", "IAA", "IPS", "IPP", "IPV"]

# Composição oficial do INDE (documento "PEDE: Pontos importantes").
# Fases 0 a 7; na Fase 8 os pesos são IDA 0,4 e IPS 0,2, sem IPP e IPV.
PESOS_INDE = {
    "IAN": 0.1,
    "IDA": 0.2,
    "IEG": 0.2,
    "IAA": 0.1,
    "IPS": 0.1,
    "IPP": 0.1,
    "IPV": 0.2,
}

PEDRAS = ["Quartzo", "Ágata", "Ametista", "Topázio"]
ORDEM_PEDRA = {pedra: i for i, pedra in enumerate(PEDRAS, start=1)}

# Classificação oficial do IAN a partir da defasagem D = fase efetiva - fase ideal.
CLASSES_IAN = {10.0: "Em fase", 5.0: "Moderada", 2.5: "Severa"}
