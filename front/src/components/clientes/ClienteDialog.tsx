"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "sonner"
import clienteService, { Cliente, ClienteCreate } from "@/services/clienteService"

interface ClienteDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  cliente: Cliente | null
  onSave: () => void
}

export function ClienteDialog({
  open,
  onOpenChange,
  cliente,
  onSave,
}: ClienteDialogProps) {
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState<ClienteCreate>({
    nome: "",
    nome_fantasia: "",
    cnpj: "",
    nome_responsavel: "",
    email: "",
    telefone: "",
    endereco: "",
    ativo: true,
  })

  useEffect(() => {
    if (cliente) {
      setFormData({
        nome: cliente.nome,
        nome_fantasia: cliente.nome_fantasia || "",
        cnpj: cliente.cnpj,
        nome_responsavel: cliente.nome_responsavel,
        email: cliente.email || "",
        telefone: cliente.telefone || "",
        endereco: cliente.endereco || "",
        ativo: cliente.ativo,
      })
    } else {
      setFormData({
        nome: "",
        nome_fantasia: "",
        cnpj: "",
        nome_responsavel: "",
        email: "",
        telefone: "",
        endereco: "",
        ativo: true,
      })
    }
  }, [cliente, open])

  const formatCNPJ = (value: string) => {
    // Remove tudo que não é número
    const numbers = value.replace(/\D/g, "")

    // Formata como XX.XXX.XXX/XXXX-XX
    if (numbers.length <= 2) return numbers
    if (numbers.length <= 5) return `${numbers.slice(0, 2)}.${numbers.slice(2)}`
    if (numbers.length <= 8)
      return `${numbers.slice(0, 2)}.${numbers.slice(2, 5)}.${numbers.slice(5)}`
    if (numbers.length <= 12)
      return `${numbers.slice(0, 2)}.${numbers.slice(2, 5)}.${numbers.slice(5, 8)}/${numbers.slice(8)}`
    return `${numbers.slice(0, 2)}.${numbers.slice(2, 5)}.${numbers.slice(5, 8)}/${numbers.slice(8, 12)}-${numbers.slice(12, 14)}`
  }

  const handleCNPJChange = (value: string) => {
    const formatted = formatCNPJ(value)
    setFormData({ ...formData, cnpj: formatted })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validações
    if (!formData.nome.trim()) {
      toast.error("Nome/Razão Social é obrigatório")
      return
    }

    if (!formData.cnpj.trim()) {
      toast.error("CNPJ é obrigatório")
      return
    }

    if (!formData.nome_responsavel.trim()) {
      toast.error("Nome do Responsável é obrigatório")
      return
    }

    // Valida CNPJ (14 dígitos)
    const cnpjNumbers = formData.cnpj.replace(/\D/g, "")
    if (cnpjNumbers.length !== 14) {
      toast.error("CNPJ deve conter 14 dígitos")
      return
    }

    try {
      setLoading(true)

      if (cliente) {
        await clienteService.update(cliente.id, formData)
        toast.success("Cliente atualizado com sucesso")
      } else {
        await clienteService.create(formData)
        toast.success("Cliente cadastrado com sucesso")
      }

      onSave()
      onOpenChange(false)
    } catch (error: any) {
      console.error("Erro ao salvar cliente:", error)

      // Trata erros específicos
      if (error.response?.data?.cnpj) {
        toast.error("Este CNPJ já está cadastrado")
      } else {
        toast.error("Erro ao salvar cliente. Tente novamente.")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {cliente ? "Editar Cliente" : "Novo Cliente"}
          </DialogTitle>
          <DialogDescription>
            {cliente
              ? "Atualize as informações do cliente"
              : "Preencha os dados para cadastrar um novo cliente"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Nome/Razão Social */}
            <div className="col-span-2">
              <Label htmlFor="nome">
                Nome/Razão Social <span className="text-destructive">*</span>
              </Label>
              <Input
                id="nome"
                value={formData.nome}
                onChange={(e) =>
                  setFormData({ ...formData, nome: e.target.value })
                }
                placeholder="Ex: Empresa Exemplo LTDA"
                required
              />
            </div>

            {/* Nome Fantasia */}
            <div className="col-span-2">
              <Label htmlFor="nome_fantasia">Nome Fantasia</Label>
              <Input
                id="nome_fantasia"
                value={formData.nome_fantasia}
                onChange={(e) =>
                  setFormData({ ...formData, nome_fantasia: e.target.value })
                }
                placeholder="Ex: Empresa Exemplo"
              />
            </div>

            {/* CNPJ */}
            <div>
              <Label htmlFor="cnpj">
                CNPJ <span className="text-destructive">*</span>
              </Label>
              <Input
                id="cnpj"
                value={formData.cnpj}
                onChange={(e) => handleCNPJChange(e.target.value)}
                placeholder="00.000.000/0000-00"
                maxLength={18}
                required
              />
            </div>

            {/* Nome do Responsável */}
            <div>
              <Label htmlFor="nome_responsavel">
                Nome do Responsável <span className="text-destructive">*</span>
              </Label>
              <Input
                id="nome_responsavel"
                value={formData.nome_responsavel}
                onChange={(e) =>
                  setFormData({ ...formData, nome_responsavel: e.target.value })
                }
                placeholder="Ex: João Silva"
                required
              />
            </div>

            {/* Email */}
            <div>
              <Label htmlFor="email">E-mail</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) =>
                  setFormData({ ...formData, email: e.target.value })
                }
                placeholder="contato@empresa.com"
              />
            </div>

            {/* Telefone */}
            <div>
              <Label htmlFor="telefone">Telefone</Label>
              <Input
                id="telefone"
                value={formData.telefone}
                onChange={(e) =>
                  setFormData({ ...formData, telefone: e.target.value })
                }
                placeholder="(00) 0000-0000"
              />
            </div>

            {/* Endereço */}
            <div className="col-span-2">
              <Label htmlFor="endereco">Endereço</Label>
              <Textarea
                id="endereco"
                value={formData.endereco}
                onChange={(e) =>
                  setFormData({ ...formData, endereco: e.target.value })
                }
                placeholder="Rua, número, bairro, cidade, estado"
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Salvando..." : cliente ? "Atualizar" : "Cadastrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
