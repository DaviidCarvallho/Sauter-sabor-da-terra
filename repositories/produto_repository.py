"""Repositório de produtos.

Função:
    Acesso a sazonalidade.csv e tabela_precos_outubro_2026.csv com mapa explícito
    de normalização de nomes e resolução da unidade real de cada produto.

Responsabilidades:
    - Consultar disponibilidade por mês (sazonalidade) e preços (convencional/orgânico)
    - Traduzir nomes entre cadastro de produtores, sazonalidade, preços, financeiro e lotes
    - Resolver a unidade real do produto sem usar busca por prefixo

Não deve:
    - Decidir se um pedido é viável (função do pedido_service)

Relações:
    Usa:        repositories.storage_repository, models.produto_model
    Usado por:  services.pedido_service, services.produtor_service, services.relatorio_service
"""

from __future__ import annotations

from models.produto_model import PrecoProduto, SazonalidadeProduto, UnidadeMedida
from repositories.storage_repository import carregar_modelos, ler_csv, normalizar_texto
from storage.base import Storage

ARQUIVO_SAZONALIDADE = "sazonalidade.csv"
ARQUIVO_PRECOS = "tabela_precos_outubro_2026.csv"

MAPA_NOMES_SAZONALIDADE: dict[str, str] = {
    "goiaba": "goiaba paluma",
    "goiaba paluma": "goiaba paluma",
    "goiaba paluma extra": "goiaba paluma",
    "goiaba paluma especial": "goiaba paluma",
    "manga": "manga tommy",
    "manga tommy": "manga tommy",
    "banana": "banana prata",
    "banana prata": "banana prata",
    "tomate": "tomate",
    "tomate santa cruz": "tomate",
    "tomate cereja": "tomate",
    "pimentao": "pimentão",
    "pimentao verde": "pimentão",
    "pimentao colorido": "pimentão",
    "mel": "mel silvestre",
    "mel silvestre": "mel silvestre",
    "mel de abelha jandaira": "mel de jandaíra",
    "mel de jandaira": "mel de jandaíra",
    "mel jandaira": "mel de jandaíra",
    "tapioca": "tapioca/goma",
    "goma": "tapioca/goma",
    "tapioca/goma": "tapioca/goma",
    "queijo": "queijo coalho",
    "manteiga": "manteiga de garrafa",
    "batata-doce": "batata doce",
    "acucar mascavo": "açúcar mascavo",
    "farinha": "farinha de mandioca",
    "frango": "frango caipira",
    "ovos": "ovos caipira",
    "ovo caipira": "ovos caipira",
    "iogurte": "iogurte natural",
}

MAPA_NOMES_PRECOS: dict[str, list[str]] = {
    "goiaba": ["goiaba paluma extra", "goiaba paluma especial"],
    "goiaba paluma": ["goiaba paluma extra", "goiaba paluma especial"],
    "goiaba paluma extra": ["goiaba paluma extra"],
    "goiaba paluma especial": ["goiaba paluma especial"],
    "manga": ["manga tommy"],
    "manga tommy": ["manga tommy"],
    "banana": ["banana prata"],
    "banana prata": ["banana prata"],
    "tomate": ["tomate santa cruz"],
    "tomate santa cruz": ["tomate santa cruz"],
    "tomate cereja": ["tomate cereja"],
    "pimentao": ["pimentão verde", "pimentão colorido"],
    "pimentao verde": ["pimentão verde"],
    "pimentao colorido": ["pimentão colorido"],
    "mel": ["mel silvestre"],
    "mel silvestre": ["mel silvestre"],
    "mel de abelha jandaira": ["mel de jandaíra"],
    "mel de jandaira": ["mel de jandaíra"],
    "mel jandaira": ["mel de jandaíra"],
    "tapioca": ["tapioca/goma"],
    "goma": ["tapioca/goma"],
    "tapioca/goma": ["tapioca/goma"],
}

MAPA_CANONICO_PARA_CADASTRO: dict[str, set[str]] = {
    "goiaba paluma": {"goiaba", "goiaba paluma"},
    "goiaba paluma extra": {"goiaba", "goiaba paluma"},
    "goiaba paluma especial": {"goiaba", "goiaba paluma"},
    "manga tommy": {"manga", "manga tommy"},
    "banana prata": {"banana", "banana prata"},
    "tomate": {"tomate"},
    "tomate santa cruz": {"tomate"},
    "tomate cereja": {"tomate cereja"},
    "pimentao": {"pimentão", "pimentao"},
    "pimentao verde": {"pimentão", "pimentao"},
    "pimentao colorido": {"pimentão", "pimentao"},
    "mel de jandaira": {"mel de abelha jandaíra", "mel de jandaíra"},
    "tapioca/goma": {"tapioca", "goma", "tapioca/goma"},
}


class ProdutoRepository:
    """Leitura de sazonalidade.csv e tabela_precos_outubro_2026.csv (somente leitura)."""

    def __init__(self, storage: Storage | None = None) -> None:
        self._storage = storage

    def listar_sazonalidade(self) -> list[SazonalidadeProduto]:
        linhas = ler_csv(ARQUIVO_SAZONALIDADE, self._storage)
        return carregar_modelos(
            ARQUIVO_SAZONALIDADE, linhas, SazonalidadeProduto, campo_id="produto"
        )

    def listar_precos(self) -> list[PrecoProduto]:
        linhas = ler_csv(ARQUIVO_PRECOS, self._storage)
        return carregar_modelos(ARQUIVO_PRECOS, linhas, PrecoProduto, campo_id="produto")

    def normalizar_para_sazonalidade(self, nome_produto: str) -> str | None:
        """Retorna o nome exato do produto em sazonalidade.csv ou None se não existir."""
        chave = normalizar_texto(nome_produto)
        if not chave:
            return None

        alvo = normalizar_texto(MAPA_NOMES_SAZONALIDADE.get(chave, chave))
        for item in self.listar_sazonalidade():
            if normalizar_texto(item.produto) == alvo:
                return item.produto
        return None

    def buscar_sazonalidade(self, nome_produto: str) -> SazonalidadeProduto | None:
        """Consulta a sazonalidade de um produto usando normalização explícita."""
        nome_canonico = self.normalizar_para_sazonalidade(nome_produto)
        if nome_canonico is None:
            return None
        alvo = normalizar_texto(nome_canonico)
        return next(
            (s for s in self.listar_sazonalidade() if normalizar_texto(s.produto) == alvo),
            None,
        )

    def listar_precos_por_produto(self, nome_produto: str) -> list[PrecoProduto]:
        """Retorna as linhas de preço correspondentes ao produto (ou lista vazia)."""
        chave = normalizar_texto(nome_produto)
        if not chave:
            return []

        precos = self.listar_precos()
        alvos_mapeados = MAPA_NOMES_PRECOS.get(chave)
        if alvos_mapeados is not None:
            alvos_norm = {normalizar_texto(item) for item in alvos_mapeados}
            return [p for p in precos if normalizar_texto(p.produto) in alvos_norm]

        direto = [p for p in precos if normalizar_texto(p.produto) == chave]
        if direto:
            return direto

        canonico = MAPA_NOMES_SAZONALIDADE.get(chave)
        if canonico is not None:
            canonico_norm = normalizar_texto(canonico)
            alvos_canon = MAPA_NOMES_PRECOS.get(canonico_norm, [canonico])
            alvos_norm = {normalizar_texto(item) for item in alvos_canon}
            return [p for p in precos if normalizar_texto(p.produto) in alvos_norm]

        return []

    def resolver_unidade(self, nome_produto: str) -> UnidadeMedida | None:
        """Retorna a unidade oficial da tabela de preços para o produto."""
        precos = self.listar_precos_por_produto(nome_produto)
        if not precos:
            return None
        return precos[0].unidade

    def termos_cadastro_para_produto(self, nome_produto: str) -> set[str]:
        """Retorna os nomes normalizados aceitos na coluna 'produtos' de produtores.csv."""
        chave = normalizar_texto(nome_produto)
        if not chave:
            return set()
        if chave in MAPA_CANONICO_PARA_CADASTRO:
            return {normalizar_texto(t) for t in MAPA_CANONICO_PARA_CADASTRO[chave]}
        canonico = self.normalizar_para_sazonalidade(nome_produto)
        if canonico is not None:
            canonico_norm = normalizar_texto(canonico)
            if canonico_norm in MAPA_CANONICO_PARA_CADASTRO:
                return {normalizar_texto(t) for t in MAPA_CANONICO_PARA_CADASTRO[canonico_norm]}
            return {canonico_norm, chave}
        return {chave}