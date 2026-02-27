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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import userService, { User, UserCreate, UserUpdate } from "@/services/userService"

interface UserDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  user: User | null
  onSave: () => void
}

export function UserDialog({
  open,
  onOpenChange,
  user,
  onSave,
}: UserDialogProps) {
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState<UserCreate>({
    email: "",
    name: "",
    role: "cliente",
    cpf: "",
    phone: "",
    password: "",
    password_confirm: "",
    is_active: true,
    is_staff: false,
  })

  useEffect(() => {
    if (user) {
      setFormData({
        email: user.email,
        name: user.name,
        role: user.role,
        cpf: user.cpf || "",
        phone: user.phone || "",
        password: "",
        password_confirm: "",
        is_active: user.is_active,
        is_staff: user.is_staff,
      })
    } else {
      setFormData({
        email: "",
        name: "",
        role: "cliente",
        cpf: "",
        phone: "",
        password: "",
        password_confirm: "",
        is_active: true,
        is_staff: false,
      })
    }
  }, [user, open])

  const formatCPF = (value: string) => {
    const numbers = value.replace(/\D/g, "")
    if (numbers.length <= 3) return numbers
    if (numbers.length <= 6) return `${numbers.slice(0, 3)}.${numbers.slice(3)}`
    if (numbers.length <= 9)
      return `${numbers.slice(0, 3)}.${numbers.slice(3, 6)}.${numbers.slice(6)}`
    return `${numbers.slice(0, 3)}.${numbers.slice(3, 6)}.${numbers.slice(6, 9)}-${numbers.slice(9, 11)}`
  }

  const handleCPFChange = (value: string) => {
    const formatted = formatCPF(value)
    setFormData({ ...formData, cpf: formatted })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validações
    if (!formData.name.trim()) {
      toast.error("Nome é obrigatório")
      return
    }

    if (!formData.email.trim()) {
      toast.error("Email é obrigatório")
      return
    }

    if (!user) {
      // Criação - senha é obrigatória
      if (!formData.password) {
        toast.error("Senha é obrigatória")
        return
      }

      if (formData.password.length < 6) {
        toast.error("Senha deve ter no mínimo 6 caracteres")
        return
      }

      if (formData.password !== formData.password_confirm) {
        toast.error("As senhas não coincidem")
        return
      }
    }

    try {
      setLoading(true)

      if (user) {
        // Atualização - não envia senha
        const updateData: UserUpdate = {
          name: formData.name,
          role: formData.role,
          cpf: formData.cpf || undefined,
          phone: formData.phone || undefined,
          is_active: formData.is_active,
          is_staff: formData.is_staff,
        }
        await userService.update(user.id, updateData)
        toast.success("Usuário atualizado com sucesso")
      } else {
        // Criação
        await userService.create(formData)
        toast.success("Usuário cadastrado com sucesso")
      }

      onSave()
      onOpenChange(false)
    } catch (error: any) {
      console.error("Erro ao salvar usuário:", error)

      if (error.response?.data) {
        const errorData = error.response.data
        if (errorData.email) {
          toast.error("Este email já está cadastrado")
        } else if (errorData.password_confirm) {
          toast.error(errorData.password_confirm[0])
        } else {
          toast.error("Erro ao salvar usuário. Tente novamente.")
        }
      } else {
        toast.error("Erro ao salvar usuário. Tente novamente.")
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
            {user ? "Editar Usuário" : "Novo Usuário"}
          </DialogTitle>
          <DialogDescription>
            {user
              ? "Atualize as informações do usuário"
              : "Preencha os dados para cadastrar um novo usuário"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Nome */}
            <div className="col-span-2">
              <Label htmlFor="name">
                Nome completo <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="Ex: João Silva"
                required
              />
            </div>

            {/* Email */}
            <div className="col-span-2">
              <Label htmlFor="email">
                Email <span className="text-destructive">*</span>
              </Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) =>
                  setFormData({ ...formData, email: e.target.value })
                }
                placeholder="usuario@email.com"
                required
                disabled={!!user}
              />
              {user && (
                <p className="text-xs text-muted-foreground mt-1">
                  O email não pode ser alterado
                </p>
              )}
            </div>

            {/* Perfil */}
            <div>
              <Label htmlFor="role">
                Perfil <span className="text-destructive">*</span>
              </Label>
              <Select
                value={formData.role}
                onValueChange={(value: any) =>
                  setFormData({ ...formData, role: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Administrador</SelectItem>
                  <SelectItem value="atendente">Atendente</SelectItem>
                  <SelectItem value="cliente">Cliente</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* CPF */}
            <div>
              <Label htmlFor="cpf">CPF</Label>
              <Input
                id="cpf"
                value={formData.cpf}
                onChange={(e) => handleCPFChange(e.target.value)}
                placeholder="000.000.000-00"
                maxLength={14}
              />
            </div>

            {/* Telefone */}
            <div className="col-span-2">
              <Label htmlFor="phone">Telefone</Label>
              <Input
                id="phone"
                value={formData.phone}
                onChange={(e) =>
                  setFormData({ ...formData, phone: e.target.value })
                }
                placeholder="(00) 00000-0000"
              />
            </div>

            {/* Senha - Apenas na criação */}
            {!user && (
              <>
                <div>
                  <Label htmlFor="password">
                    Senha <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="password"
                    type="password"
                    value={formData.password}
                    onChange={(e) =>
                      setFormData({ ...formData, password: e.target.value })
                    }
                    placeholder="Mínimo 6 caracteres"
                    required={!user}
                    minLength={6}
                  />
                </div>

                <div>
                  <Label htmlFor="password_confirm">
                    Confirmar senha <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="password_confirm"
                    type="password"
                    value={formData.password_confirm}
                    onChange={(e) =>
                      setFormData({ ...formData, password_confirm: e.target.value })
                    }
                    placeholder="Digite a senha novamente"
                    required={!user}
                  />
                </div>
              </>
            )}
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
              {loading ? "Salvando..." : user ? "Atualizar" : "Cadastrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
