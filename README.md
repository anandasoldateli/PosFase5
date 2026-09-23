# Datathon Passos Mágicos — Fase 5

## Sobre o projeto

Projeto desenvolvido para o Datathon da Fase 5 da Pós-Tech, utilizando dados da Associação Passos Mágicos.

O objetivo é aplicar técnicas de análise de dados e modelagem preditiva para identificar padrões relacionados ao desempenho, desenvolvimento e trajetória dos estudantes, gerando informações que possam apoiar decisões da organização.

## Objetivos

A análise busca investigar:

- a defasagem escolar dos estudantes e sua evolução ao longo dos anos;
- a evolução do desempenho acadêmico;
- as relações entre desempenho, engajamento e desenvolvimento;
- a relação entre autopercepção e indicadores de desempenho;
- possíveis padrões psicossociais associados à queda de desempenho ou engajamento;
- a relação entre avaliações psicopedagógicas e defasagem escolar;
- os fatores relacionados à variação do índice de vulnerabilidade;
- combinações de indicadores associadas ao desenvolvimento dos estudantes;
- padrões que possam identificar estudantes em situação de risco antes de uma queda de desempenho;
- a efetividade dos diferentes programas da Associação.

## Dados

O projeto utiliza a base de dados disponibilizada para o Datathon, contemplando informações dos estudantes dos anos de 2022, 2023 e 2024.

Os dados originais não são versionados neste repositório.

## Estrutura do projeto

```text
PosFase5/
├── data/
│   ├── raw/
│   └── processed/
├── notebooks/
├── src/
├── outputs/
├── docs/
├── .gitignore
└── README.md
```

### `data/`

Armazena os dados utilizados no projeto.

- `raw/`: dados originais.
- `processed/`: dados tratados e preparados para análise.

### `notebooks/`

Notebooks utilizados para exploração, análise e modelagem dos dados.

### `src/`

Códigos Python reutilizáveis desenvolvidos durante o projeto.

### `outputs/`

Resultados das análises, como gráficos, tabelas e outros artefatos.

### `docs/`

Documentação e materiais de apoio do projeto.

## Etapas do projeto

1. Preparação e entendimento dos dados
2. Limpeza e tratamento dos dados
3. Análise exploratória
4. Análise dos indicadores
5. Modelagem preditiva
6. Avaliação do modelo
7. Construção da aplicação em Streamlit
8. Storytelling e apresentação dos resultados

## Tecnologias

- Python
- Pandas
- NumPy
- Matplotlib
- Seaborn
- Scikit-learn
- Jupyter Notebook
- Streamlit

## Equipe

Ananda Soares Soldateli
Grecco Teixeira de Morais

---

**Status:** Em desenvolvimento
