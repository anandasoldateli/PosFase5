# Dados

Coloque aqui a planilha do Datathon: `BASE DE DADOS PEDE 2024 - DATATHON.xlsx` (abas PEDE2022, PEDE2023 e PEDE2024). Ela não é versionada.

`processed/` é gerado pelo pipeline e também não é versionado, porque contém dados por aluno:

- `base_longitudinal.csv`: base aluno × ano (3.030 registros), gerada por `src/preparacao.py`;
- `q9_risco_alunos_2024.csv`: risco estimado por aluno de 2024, gerado pelo notebook do modelo.
