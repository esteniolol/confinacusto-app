# ConfinaCusto

Sistema de custos e viabilidade para confinamento bovino, feito em Python com Streamlit.

Projeto da disciplina **Custos nos Agronegócios**, curso de Gestão de Agronegócios da Universidade de Brasília (UnB),
por **Marcos da Silva Oliveira** e **Ana Beatriz Liberal Dionizio**.

> O exemplo que abre no sistema (**Fazenda Modelo**) é fictício. Os números têm ordem de grandeza realista para um
> confinamento em Goiás, mas não pertencem a nenhuma fazenda. O modelo foi validado com dados reais de um
> confinamento goiano, que não estão neste repositório.

## O que o sistema faz

- **Cadastro em 9 passos**: fazenda, currais, lote e desempenho, compra e venda, dieta, custos operacionais,
  combustível, investimento e vendas. O resultado muda enquanto você digita.
- **Custo de produção** no padrão CONAB/IEA:
  - COE: custo operacional efetivo.
  - COT: COE + depreciação.
  - CT: COT + custo de oportunidade do capital.
- **Resultado** por boi e por arroba, DRE, custeio variável, margem de contribuição e preço de equilíbrio.
- **Viabilidade** em 10 anos: VPL, TIR, payback simples e descontado.
- **Risco**: Monte Carlo com 10 mil cenários e gráfico de tornado.
- **Mapa dos currais**, colorido por ocupação, dias de cocho, GMD, custo, margem ou mortes.
- **Relatórios** em Excel ou em versão para imprimir.
- Funciona no computador e no celular. O projeto é salvo e aberto em arquivo `.json`, nada fica guardado na nuvem.

## Rodar no computador

```
pip install -r requirements.txt
python -m streamlit run app.py
```

## Estrutura

```
app.py                         menu e navegação
engine.py                      motor de cálculo (COE/COT/CT, DRE, VPL/TIR, Monte Carlo, tornado)
projeto_io.py                  abrir e salvar projeto (.json) e importar planilha (.xlsx)
pages_projeto.py               tela de entrada, Início e Cadastro
pages_analise.py               Painel, Mapa e Simulador
pages_relatorios.py            Relatórios
ui.py                          estilo, componentes e formatação
dados/exemplo_ilustrativo.json exemplo fictício (Fazenda Modelo)
dados/ilustracoes/             desenhos do sistema
.streamlit/config.toml         tema (cores e fonte)
```

## Metodologia e fontes

- Custo de produção: metodologia CONAB/IEA.
- Custeio variável: margem de contribuição e ponto de equilíbrio.
- Rateio de despesas comuns: critério declarado, com sugestão por cabeças-dia.
- Combustível: L/h ≈ potência (kW) × 0,243, regra prática da Revista Cultivar.
- Benchmark de diária: Benchmarking Confina Brasil 2025, Scot Consultoria.
