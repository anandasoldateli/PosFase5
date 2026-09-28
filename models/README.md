# Modelos

`modelo_risco_defasagem.joblib` é um dicionário com:

- `modelo`: Random Forest com calibração sigmoide (scikit-learn), treinado com os pares 2022→23 e 2023→24 (fases 0–7);
- `atributos`, `limiar_medio`, `limiar_alto`: limiares obtidos por validação cruzada agrupada por aluno;
- `evento`, `uso`, `limitacoes`: o que o modelo prevê, como usá-lo (fechamento do ano t → risco em t+1) e seus limites;
- `versao_sklearn` e `medianas_referencia`.

Gerado pelo notebook `notebooks/modelo_risco_defasagem.ipynb`. Deve ser carregado com a versão do scikit-learn indicada em `requirements.txt`. A probabilidade é condicional a o aluno permanecer na base; use a faixa e a ordenação para priorizar, não o valor exato.
