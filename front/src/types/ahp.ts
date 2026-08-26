/**
 * Tipos compartilhados do domínio AHP (administração de Critérios, Termos,
 * Intensidades, Faixas de Tempo de Espera e Versões). Espelham exatamente os
 * serializers de `backend/ahp/serializers.py`.
 */

export type Orientacao = "positiva" | "negativa"
export type ImportanciaNegocio = "baixa" | "media" | "alta"

export interface Criterio {
  id: number
  nome: string
  codigo: string
  descricao: string
  orientacao: Orientacao
  ordem: number
  ativo: boolean
  importancia_negocio: ImportanciaNegocio
  regra_critica: boolean
  exige_revisao_humana: boolean
  permite_deteccao_semantica: boolean
  orientacoes_para_ia: string
  exemplos_positivos: string
  exemplos_negativos: string
  cor_identificacao: string
  icone: string
  criado_em: string
  criado_por: number | null
  atualizado_em: string
  atualizado_por: number | null
  excluido_em: string | null
  excluido_por: number | null
}

export type IntensidadeCodigo =
  | "ausente"
  | "muito_baixa"
  | "baixa"
  | "moderada"
  | "alta"
  | "critica"
  | "inconclusiva"

export interface Intensidade {
  id: number
  criterio: number
  nome: string
  codigo: IntensidadeCodigo
  codigo_display: string
  descricao: string
  ordem: number
  orientacoes_para_ia: string
  exemplo_positivo: string
  exemplo_negativo: string
  ativo: boolean
  criado_em: string
  criado_por: number | null
  atualizado_em: string
  atualizado_por: number | null
  excluido_em: string | null
  excluido_por: number | null
}

export type TipoCorrespondencia = "exato" | "contem" | "expressao" | "regex_segura" | "semantico"
export type StatusAprovacao = "pendente_aprovacao" | "aprovado" | "rejeitado"

export interface Termo {
  id: number
  criterio: number
  termo: string
  descricao: string
  tipo_correspondencia: TipoCorrespondencia
  intensidade_base: number
  exige_contexto: boolean
  regra_critica: boolean
  considerar_mensagem_atual: boolean
  considerar_historico: boolean
  considerar_anexos: boolean
  considerar_imagens: boolean
  status_aprovacao: StatusAprovacao
  ativo: boolean
  criado_em: string
  criado_por: number | null
  atualizado_em: string
  atualizado_por: number | null
  excluido_em: string | null
  excluido_por: number | null
}

export interface FaixaTempoEspera {
  id: number
  criterio: number
  minutos_min: number
  minutos_max: number | null
  intensidade: number
  ordem: number
  ativo: boolean
  criado_em: string
  criado_por: number | null
  atualizado_em: string
  atualizado_por: number | null
}

export type EstadoVersaoAHP =
  | "pendente_configuracao"
  | "rascunho"
  | "processando"
  | "valida"
  | "inconsistente"
  | "ativa"
  | "arquivada"
  | "erro"

/**
 * A matemática (pesos, matrizes, CI/CR, lambda_max) nunca é renderizada na
 * UI -- por isso os campos numéricos crus não são declarados aqui.
 * `ConsistenciaBadge`/`EstadoVersaoBadge` derivam tudo a partir de `estado`.
 */
export interface VersaoAHP {
  id: number
  numero_versao: number
  estado: EstadoVersaoAHP
  descricao: string
  ativada_em: string | null
  ativada_por: number | null
  arquivada_em: string | null
  mensagens_erro: string[]
  criado_em: string
  criado_por: number | null
  atualizado_em: string
  atualizado_por: number | null
}

export interface ComparacaoPar {
  item_linha_id: number
  item_coluna_id: number
  valor_saaty: number
}

export interface ComparacaoSubmitResult {
  detail: string
  quantidade: number
}

export interface ValidarVersaoResult {
  valido: boolean
  erros: string[]
}
