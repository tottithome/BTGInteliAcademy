#!/usr/bin/env python3
"""
Agente de analise de ofertas primarias de FII (CVM) — usando LangGraph + Groq.

Anatomia (os 3 blocos de um agente moderno):
  1. Tools  — funcoes que consultam os dados reais de FII (a docstring de cada
              uma e o que o LLM le para decidir quando chama-la)
  2. LLM    — ChatGroq decide qual tool usar e como interpretar o retorno
  3. create_react_agent — monta o loop ReAct (pensa -> age -> observa -> repete)

Uso:
    python src/agent/agent.py        # chat interativo no terminal

Requer GROQ_API_KEY no arquivo .env (pegue em https://console.groq.com/keys).
"""

import os
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# Garante que o pacote `ingestion` (em src/) seja importavel
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingestion.macro_bcb import obter_indicadores  # noqa: E402

DATA_FII = PROJECT_ROOT / "data" / "cvm" / "ofertas_fii.csv"

# ─── Carrega os dados uma unica vez (evita reler o CSV a cada chamada) ──────────

_df = pd.read_csv(DATA_FII, sep=";")
_df["Data_Registro"] = pd.to_datetime(_df["Data_Registro"], errors="coerce")
_df["Ano"] = _df["Data_Registro"].dt.year
_df["Valor_Total_Registrado"] = pd.to_numeric(_df["Valor_Total_Registrado"], errors="coerce")


def _normalize(texto: str) -> str:
    if not isinstance(texto, str):
        return ""
    return unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode().lower()


# ─── Tools ──────────────────────────────────────────────────────────────────

@tool
def resumo_mercado_fii() -> str:
    """
    Retorna uma visao geral do mercado de ofertas primarias de Fundos Imobiliarios
    (FII) registradas na CVM de 2023 a 2026: total de ofertas, volume financeiro
    total, volume por ano e os principais bancos lideres de distribuicao.
    Use quando o usuario pedir um panorama geral do mercado de FII.
    """
    total = len(_df)
    volume_bi = _df["Valor_Total_Registrado"].sum() / 1e9

    por_ano = (
        _df.groupby("Ano")["Valor_Total_Registrado"]
        .agg(ofertas="count", volume_bi=lambda x: x.sum() / 1e9)
        .sort_index()
    )
    por_lider = (
        _df.groupby("Grupo_Lider")["Valor_Total_Registrado"]
        .agg(ofertas="count", volume_bi=lambda x: x.sum() / 1e9)
        .sort_values("volume_bi", ascending=False)
        .head(6)
    )

    linhas_ano = [f"  {int(a)}: {int(r.ofertas)} ofertas, R$ {r.volume_bi:.1f}bi"
                  for a, r in por_ano.iterrows()]
    linhas_lider = [f"  {g}: R$ {r.volume_bi:.1f}bi ({int(r.ofertas)})"
                    for g, r in por_lider.iterrows()]

    return (
        f"MERCADO DE FII na CVM (2023-2026)\n"
        f"Total: {total:,} ofertas | Volume: R$ {volume_bi:.1f}bi\n"
        f"Por ano:\n" + "\n".join(linhas_ano) + "\n"
        f"Top 6 lideres (volume):\n" + "\n".join(linhas_lider)
    )


@tool
def buscar_ofertas_fii(emissor: str = "", lider: str = "", ano: int = 0,
                       ordenar_por: str = "data", limite: int = 8) -> str:
    """
    Busca ofertas de FII na base da CVM com filtros opcionais.

    Use APENAS para LISTAR ofertas individuais (quais sao, de quem, quando).
    NAO use esta ferramenta para calcular totais ou volumes agregados — ela
    retorna so uma amostra. Para totais por ano use resumo_mercado_fii; para
    comparar instituicoes use ranking_lideres_fii.

    Parametros:
        emissor — trecho do nome do fundo/emissor (ex: 'Kinea', 'HBC'). Busca parcial.
        lider   — trecho do nome do banco lider (ex: 'BTG', 'XP', 'Itau'). Busca parcial.
        ano     — ano de registro (2023, 2024, 2025, 2026). 0 = todos.
        ordenar_por — 'data' (mais recentes, padrao) ou 'volume' (maiores ofertas).
                      Para perguntas de "maiores ofertas" ou "maior volume", use 'volume'.
        limite  — numero maximo de resultados (padrao 8).

    Retorna data, emissor, lider, volume e status das ofertas encontradas.
    """
    df = _df.copy()
    if emissor:
        df = df[df["Nome_Emissor"].map(_normalize).str.contains(_normalize(emissor), na=False)]
    if lider:
        mask_grupo = df["Grupo_Lider"].map(_normalize).str.contains(_normalize(lider), na=False)
        mask_nome = df["Nome_Lider"].map(_normalize).str.contains(_normalize(lider), na=False)
        df = df[mask_grupo | mask_nome]
    if ano:
        df = df[df["Ano"] == ano]

    if df.empty:
        return "Nenhuma oferta de FII encontrada com esses filtros."

    coluna_ordem = "Valor_Total_Registrado" if ordenar_por == "volume" else "Data_Registro"
    res = df.sort_values(coluna_ordem, ascending=False).head(limite)
    vol_total = df["Valor_Total_Registrado"].sum() / 1e9
    linhas = []
    for _, r in res.iterrows():
        data = r["Data_Registro"].strftime("%d/%m/%Y") if pd.notna(r["Data_Registro"]) else "s/data"
        vol = f"R$ {r['Valor_Total_Registrado']/1e6:.0f}M" if pd.notna(r["Valor_Total_Registrado"]) else "N/D"
        nome = str(r["Nome_Emissor"])[:40]
        linhas.append(f"- {data} | {nome} | {r['Grupo_Lider']} | {vol} | {r['Status_Requerimento']}")

    return (
        f"Encontradas {len(df):,} ofertas (volume total R$ {vol_total:.1f}bi; exibindo {len(res)}):\n"
        + "\n".join(linhas)
    )


@tool
def ranking_lideres_fii(ano: int = 0) -> str:
    """
    Ranking das instituicoes lideres na distribuicao de ofertas de FII,
    por volume financeiro e quantidade de ofertas. Util para comparar o BTG
    Pactual com concorrentes (XP, Itau, Genial, etc.).

    Parametro:
        ano — filtra por ano (2023-2026). 0 = todos os anos.
    """
    df = _df.copy()
    if ano:
        df = df[df["Ano"] == ano]
    if df.empty:
        return "Sem dados para o ano informado."

    ranking = (
        df.groupby("Grupo_Lider")["Valor_Total_Registrado"]
        .agg(ofertas="count", volume_bi=lambda x: x.sum() / 1e9)
        .sort_values("volume_bi", ascending=False)
        .head(8)
    )
    periodo = f"em {ano}" if ano else "(2023-2026)"
    linhas = [f"  {i}. {g}: R$ {r.volume_bi:.1f}bi ({int(r.ofertas)} ofertas)"
              for i, (g, r) in enumerate(ranking.iterrows(), 1)]
    return f"RANKING DE LIDERES NA DISTRIBUICAO DE FII {periodo}:\n" + "\n".join(linhas)


@tool
def contexto_macro() -> str:
    """
    Retorna os principais indicadores macroeconomicos atuais do Brasil (fonte:
    Banco Central): Meta Selic, CDI e IPCA acumulado em 12 meses.
    Use para contextualizar o mercado de FII — por exemplo, explicar por que as
    emissoes crescem ou caem conforme os juros, ou comparar o rendimento de um
    FII com a taxa livre de risco (Selic/CDI).
    """
    ind = obter_indicadores()
    if "erro" in ind:
        return ind["erro"]
    return (
        f"INDICADORES MACRO (Banco Central):\n"
        f"- Meta Selic: {ind['selic']:.2f}% a.a. (ref {ind['selic_data']})\n"
        f"- CDI: {ind['cdi']:.2f}% a.a.\n"
        f"- IPCA 12m: {ind['ipca_12m']:.2f}% (ref {ind['ipca_ref']})"
    )


# ─── Agente ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Voce e um analista especializado em ofertas primarias de Fundos Imobiliarios (FII) no Brasil.

Voce tem acesso a dados reais da CVM: 1.255 ofertas de FII registradas entre 2023 e 2026.

Voce tambem pode consultar indicadores macroeconomicos atuais (Selic, CDI, IPCA)
para contextualizar o mercado.

Qual ferramenta usar:
- Totais e volumes por ano (ex: "quanto foi emitido em 2025"): use resumo_mercado_fii.
- Comparar instituicoes / rankings (ex: "BTG vs XP"): use ranking_lideres_fii.
- Listar ofertas especificas (ex: "ofertas da Kinea", "ultimas ofertas"): use buscar_ofertas_fii.
- "Maiores ofertas" ou "maior volume": use buscar_ofertas_fii com ordenar_por='volume'.
- NUNCA some manualmente os resultados de buscar_ofertas_fii para estimar totais — eles sao so uma amostra.

Ao responder:
- SEMPRE use as ferramentas para obter os numeros antes de responder. Nunca invente valores.
- Cite volumes em reais (ex: R$ 2,3 bilhoes) e use linguagem tecnica mas acessivel.
- Quando for relevante, compare o BTG Pactual com os concorrentes.
- Quando a pergunta envolver juros, cenario economico ou "por que" do movimento das
  emissoes, consulte os indicadores macro e relacione-os com os dados de FII.
- Seja objetivo: numeros primeiro, interpretacao depois.
- Se o usuario pedir algo fora dos dados de FII, diga claramente o que esta fora do escopo."""

TOOLS = [resumo_mercado_fii, buscar_ofertas_fii, ranking_lideres_fii, contexto_macro]


def build_agent(checkpointer=None):
    """Monta o agente ReAct. Passe um checkpointer (ex: MemorySaver) para dar memoria de conversa."""
    if not os.environ.get("GROQ_API_KEY"):
        raise EnvironmentError(
            "GROQ_API_KEY nao encontrada. Crie o arquivo .env e cole sua chave "
            "(pegue gratis em https://console.groq.com/keys)."
        )

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, max_tokens=800)
    return create_react_agent(llm, TOOLS, prompt=SYSTEM_PROMPT, checkpointer=checkpointer)


# ─── Loop interativo ──────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Agente de Analise de Ofertas de FII (CVM 2023-2026)")
    print("  Digite 'sair' para encerrar")
    print("=" * 60)

    agent = build_agent(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "cli"}}

    while True:
        pergunta = input("\nVoce: ").strip()
        if not pergunta or pergunta.lower() in {"sair", "exit", "quit"}:
            print("Encerrando.")
            break

        for step in agent.stream(
            {"messages": [{"role": "user", "content": pergunta}]},
            config=config,
            stream_mode="updates",
        ):
            if "tools" in step:
                for msg in step["tools"]["messages"]:
                    print(f"\n  [tool: {msg.name}] -> {msg.content[:100]}...")
            if "agent" in step:
                last = step["agent"]["messages"][-1]
                if last.content:
                    print(f"\nAgente: {last.content}")


if __name__ == "__main__":
    main()
