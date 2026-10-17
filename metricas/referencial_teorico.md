# Referencial Teorico — Cham.IA

---

## 1. Gestao de Chamados e Sistemas de Help Desk

Abrange os conceitos fundamentais de sistemas de suporte tecnico (ticketing systems, help desk, service desk), fluxos de atendimento, SLA (Service Level Agreement) e boas praticas de ITIL para gestao de incidentes e requisicoes. Discute a importancia da priorizacao de chamados para cumprimento de SLAs e satisfacao do cliente, e como sistemas modernos evoluiram de filas simples FIFO para modelos de priorizacao dinamica baseados em multiplos criterios.

---

## 2. Tomada de Decisao Multicritério: AHP e Extensao Fuzzy

Apresenta o Processo de Analise Hierarquica (AHP) proposto por Saaty (1980): estrutura hierarquica do problema, comparacoes pareadas, escala de Saaty (1–9), calculo do autovetor principal, indice de consistencia (CI), indice aleatorio (RI) e razao de consistencia (CR ≤ 0,10). Inclui a Medicao Absoluta como variante do AHP para classificar alternativas contra intensidades predefinidas sem compara-las entre si. Em seguida, trata da extensao Fuzzy do AHP (Chang, 1996; Buckley, 1985), numeros triangulares fuzzy (l, m, u), motivacao para incorporar incerteza nas avaliacoes qualitativas e criterios de desambiguacao quando o intervalo fuzzy cruza fronteiras de banda.

---

## 3. Inteligencia Artificial, LLMs, Agentes Inteligentes e Arquitetura de Sistemas de IA

Apresenta os fundamentos da Inteligencia Artificial (IA): definicao, historico e principais paradigmas (IA simbolica, aprendizado de maquina, aprendizado profundo), redes neurais artificiais e a evolucao ate os modelos de linguagem modernos. Contextualiza a aplicacao de IA em sistemas empresariais — automacao de processos, classificacao automatica, apoio a decisao — e os desafios de confiabilidade, explicabilidade e supervisao humana em sistemas criticos. Discute a arquitetura Transformer (Vaswani et al., 2017), pre-treinamento e fine-tuning, e os principais modelos da geracao atual (GPT, DeepSeek, Gemini). Aborda o uso de LLMs para classificacao, extracao de entidades, deteccao de sentimento e reconhecimento de intencao em textos de suporte tecnico, tecnicas de prompt engineering (zero-shot, few-shot, chain-of-thought) e limitacoes como alucinacao e nao-determinismo. Apresenta os conceitos de agente inteligente (Russell & Norvig), ciclo percepcao-raciocinio-acao, taxonomia de agentes e sistemas multi-agente (SMA), abordando o framework LangGraph para orquestracao de grafos de agentes com estado compartilhado, execucao paralela e resiliencia a falhas. Discute padroes arquiteturais para integrar IA em producao: processamento assincrono (Celery + Redis), degradacao gracosa quando componentes de IA estao indisponiveis e auditabilidade de registros de decisao automatizada.

---

## 4. Sistemas Web: Arquitetura, API REST e Comunicacao em Tempo Real

Apresenta os fundamentos de sistemas web modernos: modelo cliente-servidor, protocolo HTTP/HTTPS, arquitetura REST e principios de design de APIs (recursos, verbos, status codes, autenticacao JWT). Discute frameworks backend (Django, DRF) e frontend (Next.js, React) e o padrao de componentizacao de interfaces. Aborda comunicacao em tempo real via WebSocket — protocolo, casos de uso em chat e notificacoes, e implementacao com Django Channels. Contextualiza o papel do processamento assincrono com filas de tarefas (Celery + Redis) para operacoes longas como chamadas a LLMs, evitando bloqueio das requisicoes HTTP.

---

## 5. Metricas de Avaliacao de Sistemas de Classificacao

Apresenta as metricas classicas de avaliacao de classificadores: acuracia, precisao, recall, F1-score e matriz de confusao. Discute o Coeficiente Kappa de Cohen para medir concordancia entre classificador automatico e julgamento humano, descontando concordancias casuais. Aborda analise de sensibilidade — como variacoes no hiperparametro alfa (escala fuzzy) e nos limiares de banda afetam a distribuicao de prioridades e a taxa de encaminhamento para revisao humana. Contextualiza o uso dessas metricas na validacao empirica do sistema com cenarios sinteticos.

---
