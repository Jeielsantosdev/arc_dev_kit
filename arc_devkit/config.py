"""Carregamento e validação de configuração via variáveis de ambiente."""

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Carregar .env antes de qualquer leitura de os.getenv
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Configurações globais do Arc DevKit, carregadas do ambiente."""

    anthropic_api_key: str
    arc_rpc_url: str
    arc_chain_id: int
    arc_private_key: str | None
    log_level: str


def _require(name: str) -> str:
    """Retorna o valor da variável ou levanta erro descritivo."""
    value = os.getenv(name, "").strip()
    if not value:
        raise EnvironmentError(
            f"\n\n  Variável obrigatória '{name}' não está configurada.\n"
            f"  Crie um arquivo .env baseado no .env.example e defina {name}.\n"
            f"  Exemplo: cp .env.example .env\n"
        )
    return value


def _load_settings() -> Settings:
    """Lê, valida e retorna todas as configurações do ambiente."""
    # Coletar erros de uma só vez para exibição agrupada
    erros: list[str] = []

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    rpc_url = os.getenv("ARC_RPC_URL", "").strip()

    if not api_key:
        erros.append("ANTHROPIC_API_KEY")
    if not rpc_url:
        erros.append("ARC_RPC_URL")

    if erros:
        lista = ", ".join(erros)
        raise EnvironmentError(
            f"\n\n  Variáveis obrigatórias não configuradas: {lista}\n"
            f"  Execute: cp .env.example .env  e preencha os valores.\n"
        )

    return Settings(
        anthropic_api_key=api_key,
        arc_rpc_url=rpc_url,
        arc_chain_id=int(os.getenv("ARC_CHAIN_ID", "5042002")),
        arc_private_key=os.getenv("ARC_PRIVATE_KEY", "").strip() or None,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )


# Objeto global — importado por todos os módulos
settings = _load_settings()

# Configurar logging global com o nível definido no .env
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
