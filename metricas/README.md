# Cham.IA — Métricas AHP

Análise independente do motor AHP de priorização de chamados.

## Estrutura

```
metricas/
├── ahp_core.py          # Motor AHP puro (sem Django): pesos, síntese, fuzzy
├── cenarios_teste.py    # 7 tabelas com 12 cenários de teste
├── graficos.py          # 6 gráficos gerados em saida/
├── requirements.txt     # Dependências Python
└── saida/               # PNGs gerados (criado automaticamente)
```

## Instalação

```bash
cd metricas
pip install -r requirements.txt
```

## Execução

```bash
# Tabelas no terminal
python cenarios_teste.py

# Gráficos salvos em saida/
python graficos.py
```

---

## Critérios e Pesos

| Critério                | Descrição                              | Peso aprox. |
|-------------------------|----------------------------------------|-------------|
| `URGENCIA`              | Bloqueio total, parcial, degradação    | ~55%        |
| `IMPACTO_NO_CLIENTE`    | Extensão do impacto no negócio         | ~26%        |
| `SENTIMENTO_DO_CLIENTE` | Frustração, pânico, tranquilidade      | ~13%        |
| `TEMPO_DE_ESPERA`       | Tempo decorrido desde a abertura       | ~6%         |

## Intensidades

| Código      | Significado                              |
|-------------|------------------------------------------|
| `ausente`   | Critério não se aplica — contribuição 0  |
| `baixa`     | Situação trivial, sem impacto real       |
| `moderada`  | Situação padrão de suporte               |
| `alta`      | Problema relevante, impacto significativo|
| `critica`   | Situação grave, urgência máxima          |

## Bandas de Prioridade

| Banda          | Índice AHP   | Ação                              |
|----------------|--------------|-----------------------------------|
| P1             | ≥ 80         | Atenção imediata                  |
| P2             | 60 – 79      | Alta prioridade                   |
| P3             | 35 – 59      | Prioridade padrão                 |
| P4             | < 35         | Baixa prioridade                  |
| REVISAO_HUMANA | ±3 pts de fronteira | Zona fuzzy → revisão humana |

## Gráficos Gerados

| Arquivo                   | Conteúdo                                      |
|---------------------------|-----------------------------------------------|
| `pesos_criterios.png`     | Barras dos pesos dos 4 critérios              |
| `pesos_intensidades.png`  | Barras dos pesos das 5 intensidades           |
| `matriz_criterios.png`    | Heatmap da matriz de comparação par-a-par     |
| `cenarios_indice.png`     | Índice AHP dos 12 cenários com bandas P1–P4   |
| `cenarios_fuzzy.png`      | Intervalo de incerteza fuzzy (4 cenários)     |
| `contribuicoes_pizza.png` | Contribuição por critério no cenário crítico  |

## Fórmula de Síntese

```
P(a) = Σ  w_i × p_{i,a}
       i

onde:
  w_i    = peso do critério i  (eigenvector da matriz de Saaty)
  p_{i,a}= peso da intensidade escolhida para o critério i

Índice normalizado = (P(a) / P_max) × 100
```

## Extensão Fuzzy

Quando o LLM reporta baixa confiança, o índice vira um número fuzzy triangular:

```
l_i = max(0,     p_i - α × (1 - c_i))
u_i = min(p_max, p_i + α × (1 - c_i))

α = 0.20  (hiperparâmetro de escala)
c_i ∈ [0, 1] = confiança reportada pelo agente
```
