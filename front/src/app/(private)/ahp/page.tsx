"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { CriteriosPanel } from "@/components/ahp/CriteriosPanel"
import { TermosPanel } from "@/components/ahp/TermosPanel"
import { IntensidadesPanel } from "@/components/ahp/IntensidadesPanel"
import { FaixasTempoEsperaPanel } from "@/components/ahp/FaixasTempoEsperaPanel"
import { VersoesPanel } from "@/components/ahp/VersoesPanel"

export default function AHPPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Administração AHP</h1>
        <p className="text-muted-foreground">
          Gerencie critérios, termos, intensidades, faixas de tempo de espera e versões da hierarquia de priorização
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Configuração</CardTitle>
          <CardDescription>
            Os cálculos (pesos, matrizes, CI/CR) permanecem encapsulados -- esta área só expõe os
            dados de negócio administráveis
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="criterios">
            <TabsList>
              <TabsTrigger value="criterios">Critérios</TabsTrigger>
              <TabsTrigger value="termos">Termos</TabsTrigger>
              <TabsTrigger value="intensidades">Intensidades</TabsTrigger>
              <TabsTrigger value="faixas">Faixas de Tempo</TabsTrigger>
              <TabsTrigger value="versoes">Versões</TabsTrigger>
            </TabsList>

            <TabsContent value="criterios" className="pt-4">
              <CriteriosPanel />
            </TabsContent>
            <TabsContent value="termos" className="pt-4">
              <TermosPanel />
            </TabsContent>
            <TabsContent value="intensidades" className="pt-4">
              <IntensidadesPanel />
            </TabsContent>
            <TabsContent value="faixas" className="pt-4">
              <FaixasTempoEsperaPanel />
            </TabsContent>
            <TabsContent value="versoes" className="pt-4">
              <VersoesPanel />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
