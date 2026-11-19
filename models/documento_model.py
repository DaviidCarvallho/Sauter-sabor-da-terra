"""Schemas de consulta documental.

Função:
    Representa trechos recuperados, fontes e o resultado de uma consulta ao RAG.

Responsabilidades:
    - Trecho recuperado: conteúdo, fonte (arquivo), página, tipo do documento e score
    - Consulta documental: trechos, fontes citáveis e indicação de evidência suficiente

Não deve:
    - Conter lógica de busca

Relações:
    Usa:        pydantic
    Usado por:  services.documento_service, agents.tools

Contrato (docs/CONTRATOS_ARQUITETURAIS.md, seção 5.4):
    Cada trecho preserva `content`, `source` e `page`. `page` é None quando o formato do
    documento não tem página (ex.: .txt); nunca se inventa um número.
"""

from pydantic import BaseModel, ConfigDict, Field


class TrechoDocumento(BaseModel):
    """Evidência recuperada de um documento da cooperativa."""

    model_config = ConfigDict(frozen=True)

    id: str
    content: str
    source: str = Field(description="Documento de origem (chave lógica, ex.: contratos/arquivo.txt).")
    document_type: str | None = None
    page: int | None = None
    score: float = Field(description="Similaridade (1 - distância); maior é mais relevante.")


class FonteCitavel(BaseModel):
    """Fonte que o assistente pode citar na resposta."""

    model_config = ConfigDict(frozen=True)

    source: str
    page: int | None = None


class ConsultaDocumental(BaseModel):
    """Resultado de uma consulta ao acervo documental."""

    model_config = ConfigDict(frozen=True)

    pergunta: str
    trechos: list[TrechoDocumento] = Field(default_factory=list)
    fontes: list[FonteCitavel] = Field(default_factory=list)
    evidencia_suficiente: bool
    mensagem: str | None = Field(
        default=None, description="Explica a ausência de evidência, quando for o caso."
    )
