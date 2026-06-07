"""API REST do Arc DevKit — FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arc_devkit import __version__
from arc_devkit.api.routes import agents, copilot, debugger

app = FastAPI(
    title="Arc DevKit API",
    description=(
        "API REST para ferramentas de desenvolvimento na Arc blockchain. "
        "Expõe os módulos Dev Copilot, Agent Kit e Tx Debugger via HTTP."
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS para desenvolvimento local (ajuste allow_origins em produção)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # React CRA
        "http://localhost:5173",   # Vite
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(copilot.router, prefix="/copilot", tags=["Dev Copilot"])
app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(debugger.router, prefix="/debug", tags=["Tx Debugger"])


@app.get("/health", tags=["Infra"])
def health() -> dict:
    """Verifica se a API está respondendo."""
    return {"status": "ok", "version": __version__}
