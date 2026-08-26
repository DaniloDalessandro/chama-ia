from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Comparacao, Criterio, FaixaTempoEspera, Intensidade, Termo, VersaoAHP
from .permissions import IsAdminOrReadOnlyAtendente
from .serializers import (
    ComparacaoItemInputSerializer,
    ComparacaoSerializer,
    CriterioSerializer,
    FaixaTempoEsperaSerializer,
    IntensidadeSerializer,
    TermoSerializer,
    VersaoAHPSerializer,
)
from .services.comparison_service import AHPComparisonService, VersaoNaoEditavelError
from .services.hierarchy_service import AHPHierarchyService
from .services.intensity_service import AHPIntensityService
from .services.version_service import AHPVersionService, InvalidStateTransitionError


class CriterioViewSet(viewsets.ModelViewSet):
    queryset = Criterio.objects.all()
    serializer_class = CriterioSerializer
    permission_classes = [IsAdminOrReadOnlyAtendente]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["ativo", "regra_critica", "exige_revisao_humana"]
    search_fields = ["nome", "codigo", "descricao"]
    ordering_fields = ["ordem", "nome", "criado_em"]
    ordering = ["ordem"]

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user, atualizado_por=self.request.user)

    def perform_update(self, serializer):
        serializer.save(atualizado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def inativar(self, request, pk=None):
        criterio = self.get_object()
        criterio.ativo = False
        criterio.atualizado_por = request.user
        criterio.save(update_fields=["ativo", "atualizado_por", "atualizado_em"])
        return Response(self.get_serializer(criterio).data)

    @action(detail=True, methods=["post"])
    def duplicar(self, request, pk=None):
        original = self.get_object()
        clone = Criterio.objects.create(
            nome=f"{original.nome} (copia)",
            codigo=f"{original.codigo}_COPIA_{Criterio.all_objects.count()}",
            descricao=original.descricao,
            orientacao=original.orientacao,
            ordem=original.ordem,
            ativo=False,
            importancia_negocio=original.importancia_negocio,
            regra_critica=original.regra_critica,
            exige_revisao_humana=original.exige_revisao_humana,
            permite_deteccao_semantica=original.permite_deteccao_semantica,
            orientacoes_para_ia=original.orientacoes_para_ia,
            exemplos_positivos=original.exemplos_positivos,
            exemplos_negativos=original.exemplos_negativos,
            cor_identificacao=original.cor_identificacao,
            icone=original.icone,
            criado_por=request.user,
            atualizado_por=request.user,
        )
        for intensidade in original.intensidades.filter(ativo=True):
            Intensidade.objects.create(
                criterio=clone,
                nome=intensidade.nome,
                codigo=intensidade.codigo,
                descricao=intensidade.descricao,
                ordem=intensidade.ordem,
                orientacoes_para_ia=intensidade.orientacoes_para_ia,
                exemplo_positivo=intensidade.exemplo_positivo,
                exemplo_negativo=intensidade.exemplo_negativo,
                criado_por=request.user,
                atualizado_por=request.user,
            )
        return Response(self.get_serializer(clone).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def historico(self, request, pk=None):
        criterio = self.get_object()
        versoes_ids = set(
            Comparacao.objects.filter(criterio_linha=criterio).values_list("versao_ahp_id", flat=True)
        ) | set(
            Comparacao.objects.filter(criterio_coluna=criterio).values_list("versao_ahp_id", flat=True)
        ) | set(
            Comparacao.objects.filter(criterio_contexto=criterio).values_list("versao_ahp_id", flat=True)
        )
        versoes = VersaoAHP.objects.filter(id__in=versoes_ids).order_by("-numero_versao")
        return Response({
            "criado_em": criterio.criado_em,
            "atualizado_em": criterio.atualizado_em,
            "atualizado_por": getattr(criterio.atualizado_por, "email", None),
            "versoes_ahp_participadas": VersaoAHPSerializer(versoes, many=True).data,
        })


class TermoViewSet(viewsets.ModelViewSet):
    queryset = Termo.objects.all()
    serializer_class = TermoSerializer
    permission_classes = [IsAdminOrReadOnlyAtendente]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["criterio", "tipo_correspondencia", "status_aprovacao", "ativo"]
    search_fields = ["termo", "descricao"]

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user, atualizado_por=self.request.user)

    def perform_update(self, serializer):
        serializer.save(atualizado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def aprovar(self, request, pk=None):
        termo = self.get_object()
        termo.status_aprovacao = Termo.StatusAprovacao.APROVADO
        termo.atualizado_por = request.user
        termo.save(update_fields=["status_aprovacao", "atualizado_por", "atualizado_em"])
        return Response(self.get_serializer(termo).data)

    @action(detail=True, methods=["post"])
    def rejeitar(self, request, pk=None):
        termo = self.get_object()
        termo.status_aprovacao = Termo.StatusAprovacao.REJEITADO
        termo.atualizado_por = request.user
        termo.save(update_fields=["status_aprovacao", "atualizado_por", "atualizado_em"])
        return Response(self.get_serializer(termo).data)


class IntensidadeViewSet(viewsets.ModelViewSet):
    queryset = Intensidade.objects.all()
    serializer_class = IntensidadeSerializer
    permission_classes = [IsAdminOrReadOnlyAtendente]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["criterio", "codigo", "ativo"]

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user, atualizado_por=self.request.user)

    def perform_update(self, serializer):
        serializer.save(atualizado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FaixaTempoEsperaViewSet(viewsets.ModelViewSet):
    queryset = FaixaTempoEspera.objects.all()
    serializer_class = FaixaTempoEsperaSerializer
    permission_classes = [IsAdminOrReadOnlyAtendente]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["criterio", "ativo"]

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user, atualizado_por=self.request.user)

    def perform_update(self, serializer):
        serializer.save(atualizado_por=self.request.user)


class ComparacaoViewSet(viewsets.ModelViewSet):
    queryset = Comparacao.objects.all()
    serializer_class = ComparacaoSerializer
    permission_classes = [IsAdminOrReadOnlyAtendente]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["versao_ahp", "tipo", "criterio_contexto"]

    def _assert_editable(self, versao_ahp):
        if versao_ahp.estado != VersaoAHP.Estado.RASCUNHO:
            raise ValidationError("So e possivel editar comparacoes de uma versao AHP em RASCUNHO.")

    def perform_create(self, serializer):
        self._assert_editable(serializer.validated_data["versao_ahp"])
        serializer.save(criado_por=self.request.user, atualizado_por=self.request.user)

    def perform_update(self, serializer):
        self._assert_editable(serializer.instance.versao_ahp)
        serializer.save(atualizado_por=self.request.user)

    def perform_destroy(self, instance):
        self._assert_editable(instance.versao_ahp)
        instance.delete()


class VersaoAHPViewSet(viewsets.ModelViewSet):
    queryset = VersaoAHP.objects.all()
    serializer_class = VersaoAHPSerializer
    permission_classes = [IsAdminOrReadOnlyAtendente]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        serializer.save(
            estado=VersaoAHP.Estado.RASCUNHO, criado_por=self.request.user, atualizado_por=self.request.user
        )

    def perform_update(self, serializer):
        if serializer.instance.estado != VersaoAHP.Estado.RASCUNHO:
            raise ValidationError("So e possivel editar uma versao AHP em RASCUNHO.")
        serializer.save(atualizado_por=self.request.user)

    @action(detail=False, methods=["get"])
    def ativa(self, request):
        versao = AHPVersionService.get_versao_ativa()
        if versao is None:
            return Response({"detail": "Nenhuma versao AHP ativa no momento."}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(versao).data)

    @staticmethod
    def _resolve_valores(itens_ordenados, dados):
        id_to_pos = {item.id: idx for idx, item in enumerate(itens_ordenados)}
        valores = {}
        for entrada in dados:
            i = id_to_pos.get(entrada["item_linha_id"])
            j = id_to_pos.get(entrada["item_coluna_id"])
            if i is None or j is None:
                raise ValidationError(
                    f"Item desconhecido na comparacao: {entrada['item_linha_id']}/{entrada['item_coluna_id']}."
                )
            if i == j:
                raise ValidationError("Nao e permitido comparar um item com ele mesmo.")
            valor = entrada["valor_saaty"]
            if i > j:
                i, j, valor = j, i, 1.0 / valor
            valores[(i, j)] = valor
        return valores

    @action(detail=True, methods=["post"], url_path="comparacoes-criterios")
    def comparacoes_criterios(self, request, pk=None):
        versao = self.get_object()
        serializer = ComparacaoItemInputSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        criterios = list(AHPHierarchyService.get_criterios_ativos())
        valores = self._resolve_valores(criterios, serializer.validated_data)

        try:
            AHPComparisonService.save_comparacoes_criterios(versao, criterios, valores, user=request.user)
        except VersaoNaoEditavelError as exc:
            raise ValidationError(str(exc)) from exc

        return Response({"detail": "Comparacoes de criterios salvas.", "quantidade": len(valores)})

    @action(detail=True, methods=["post"], url_path=r"comparacoes-intensidades/(?P<criterio_codigo>[^/.]+)")
    def comparacoes_intensidades(self, request, pk=None, criterio_codigo=None):
        versao = self.get_object()
        criterio = get_object_or_404(Criterio, codigo=criterio_codigo)
        serializer = ComparacaoItemInputSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        intensidades = list(AHPIntensityService.get_comparable_intensidades(criterio))
        valores = self._resolve_valores(intensidades, serializer.validated_data)

        try:
            AHPComparisonService.save_comparacoes_intensidades(versao, criterio, intensidades, valores, user=request.user)
        except VersaoNaoEditavelError as exc:
            raise ValidationError(str(exc)) from exc

        return Response({"detail": "Comparacoes de intensidades salvas.", "quantidade": len(valores)})

    @action(detail=True, methods=["post"])
    def validar(self, request, pk=None):
        versao = self.get_object()
        erros = AHPVersionService.validar(versao)
        return Response({"valido": not erros, "erros": erros})

    @action(detail=True, methods=["post"])
    def ativar(self, request, pk=None):
        versao = self.get_object()
        try:
            resultado = AHPVersionService.ativar(versao, user=request.user)
        except InvalidStateTransitionError as exc:
            raise ValidationError(str(exc)) from exc

        http_status = status.HTTP_200_OK if resultado.estado == VersaoAHP.Estado.ATIVA else status.HTTP_422_UNPROCESSABLE_ENTITY
        return Response(self.get_serializer(resultado).data, status=http_status)
