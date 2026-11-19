"""Seleção do modelo Gemini dos agentes.

O nome do modelo vem de MODEL (.env). Sem MODEL, usa o modelo padrão do projeto.
Os parâmetros de amostragem (temperature, top_p, top_k) não são alterados: nos modelos
Gemini 3.x o raciocínio é otimizado para os valores padrão.
"""

from utils.config import get_settings

# Identificador confirmado na documentação oficial em 19/11/2026 (GA).
MODELO_PADRAO = "gemini-3.5-flash-lite"


def obter_modelo() -> str:
    return get_settings().model or MODELO_PADRAO
