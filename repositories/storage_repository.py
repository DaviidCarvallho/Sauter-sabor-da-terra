"""Leitura genérica de CSV e JSON.

Função:
    Base compartilhada pelos repositórios de dados estruturados.

Responsabilidades:
    - Ler CSV e JSON a partir do Storage (encoding, separador, parsing)
    - Evitar código duplicado nos demais repositórios

Não deve:
    - Conhecer o significado dos dados de cada arquivo

Relações:
    Usa:        storage (get_storage)
    Usado por:  demais repositórios

Observação:
    Não confundir com a pasta storage/: aqui está o parsing, lá estão os backends de armazenamento.

Status: implementado (Fase 3).
"""

import csv
import io
import json
import re
import unicodedata
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from storage import get_storage
from storage.base import Storage

M = TypeVar("M", bound=BaseModel)


class DadoInvalidoError(ValueError):
    """Arquivo de dados malformado ou com valor inválido.

    Política da camada de dados: a leitura é estrita. Um registro inválido interrompe a
    leitura com a indicação do arquivo e da linha, em vez de ser ignorado em silêncio
    (ignorar uma transação, por exemplo, deixaria um relatório financeiro errado sem aviso).
    Valores sensíveis do registro nunca entram na mensagem.
    """

    def __init__(self, arquivo: str, detalhe: str, posicao: str | None = None) -> None:
        self.arquivo = arquivo
        self.detalhe = detalhe
        self.posicao = posicao
        local = f"{arquivo}, {posicao}" if posicao else arquivo
        super().__init__(f"{local}: {detalhe}")


def ler_csv(
    chave: str, storage: Storage | None = None, delimitador: str = ","
) -> list[dict[str, str]]:
    """Lê um CSV do Storage e devolve uma lista de dicionários (valores sempre texto).

    Aceita BOM do Excel, campos entre aspas com vírgula e linhas em branco; remove espaços
    nas pontas dos nomes das colunas e dos valores. Células vazias ficam como "".
    Linha com número de colunas diferente do cabeçalho gera DadoInvalidoError.
    Arquivo inexistente levanta FileNotFoundError (vindo do Storage).
    """
    texto = (storage or get_storage()).read_text(chave, encoding="utf-8-sig")
    leitor = csv.reader(io.StringIO(texto, newline=""), delimiter=delimitador)
    try:
        cabecalho = next(leitor)
    except StopIteration:
        raise DadoInvalidoError(chave, "arquivo vazio") from None
    colunas = [c.strip() for c in cabecalho]
    if not any(colunas) or "" in colunas:
        raise DadoInvalidoError(chave, "cabeçalho inválido", "linha 1")

    registros: list[dict[str, str]] = []
    for valores in leitor:
        if not valores:  # linha em branco
            continue
        if len(valores) != len(colunas):
            raise DadoInvalidoError(
                chave,
                f"esperadas {len(colunas)} colunas, encontradas {len(valores)}",
                f"linha {leitor.line_num}",
            )
        registros.append(dict(zip(colunas, (v.strip() for v in valores))))
    return registros


def ler_json(chave: str, storage: Storage | None = None) -> Any:
    """Lê um JSON do Storage. JSON malformado gera DadoInvalidoError com a linha do erro."""
    texto = (storage or get_storage()).read_text(chave, encoding="utf-8-sig")
    try:
        return json.loads(texto)
    except json.JSONDecodeError as erro:
        raise DadoInvalidoError(chave, f"JSON inválido ({erro.msg})", f"linha {erro.lineno}") from None


def carregar_modelos(
    chave: str,
    registros: list[dict[str, Any]],
    modelo: type[M],
    *,
    campo_id: str | None = None,
    rotulo: str = "linha",
    inicio: int = 2,
) -> list[M]:
    """Converte registros em objetos do modelo, validando cada um.

    'rotulo' e 'inicio' só servem para a mensagem de erro: em CSV a primeira linha de dados
    é a linha 2 (a 1 é o cabeçalho); em JSON, o primeiro registro é o 1.
    Com 'campo_id', um identificador repetido também gera DadoInvalidoError.
    """
    if not isinstance(registros, list) or not all(isinstance(r, dict) for r in registros):
        raise DadoInvalidoError(chave, "esperada uma lista de objetos")

    objetos: list[M] = []
    vistos: set[str] = set()
    for indice, registro in enumerate(registros, start=inicio):
        posicao = f"{rotulo} {indice}"
        try:
            objeto = modelo.model_validate(registro)
        except ValidationError as erro:
            problemas = "; ".join(
                f"campo '{'.'.join(str(p) for p in e['loc'])}': {e['msg']}"
                if e["loc"]
                else e["msg"]
                for e in erro.errors(include_input=False)
            )
            raise DadoInvalidoError(chave, problemas, posicao) from None
        if campo_id is not None:
            valor_id = str(getattr(objeto, campo_id))
            if valor_id in vistos:
                raise DadoInvalidoError(chave, f"{campo_id} duplicado: {valor_id}", posicao)
            vistos.add(valor_id)
        objetos.append(objeto)
    return objetos


def normalizar_texto(texto: str) -> str:
    """Minúsculas, sem acentos e sem espaços repetidos: para comparar nomes e identificadores."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.casefold().split())


def somente_digitos(texto: str) -> str:
    """Mantém só os dígitos (ex.: '(87) 99812-3456' -> '87998123456')."""
    return re.sub(r"\D", "", texto)