#!/usr/bin/env python3
"""
Aplicacao Streamlit — Agente de Analise de Ofertas de FII (CVM).

Duas abas:
  - Chat com o Agente: conversa com o LLM (Groq) que consulta os dados reais.
  - Dashboard: metricas, graficos e tabela com filtros interativos.

Conceitos Streamlit:
  - o script roda de cima a baixo a CADA interacao;
  - @st.cache_data guarda os dados (nao rele o CSV toda vez);
  - @st.cache_resource guarda o agente (objeto pesado, construido uma vez);
  - st.session_state mantem estado entre reruns (historico do chat, thread_id).

Uso:
    streamlit run src/app.py
"""

import sys
import uuid
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Garante que o pacote `agent` (em src/) seja importavel
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent.agent import build_agent  # noqa: E402
from ingestion.macro_bcb import obter_indicadores  # noqa: E402
from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_FII = PROJECT_ROOT / "data" / "cvm" / "ofertas_fii.csv"

st.set_page_config(page_title="Agente de Ofertas de FII", page_icon="🏢", layout="wide")


# ─── Carregamento de dados e do agente (cacheados) ──────────────────────────────

@st.cache_data
def carregar_dados() -> pd.DataFrame:
    df = pd.read_csv(DATA_FII, sep=";")
    df["Data_Registro"] = pd.to_datetime(df["Data_Registro"], errors="coerce")
    df["Ano"] = df["Data_Registro"].dt.year.astype("Int64")
    df["Valor_Total_Registrado"] = pd.to_numeric(df["Valor_Total_Registrado"], errors="coerce")
    return df


@st.cache_data(ttl=3600)
def carregar_macro() -> dict:
    """Indicadores do BCB, cacheados por 1h (evita bater na API a cada interacao)."""
    return obter_indicadores()


@st.cache_resource
def obter_agente():
    """Constroi o agente uma unica vez. MemorySaver guarda o historico por thread_id."""
    return build_agent(checkpointer=MemorySaver())


def responder(agent, config, texto: str):
    """Roda o agente e devolve (resposta_final, lista_de_tools_usadas)."""
    tools_usadas = []
    resposta = ""
    try:
        for step in agent.stream(
            {"messages": [{"role": "user", "content": texto}]},
            config=config,
            stream_mode="updates",
        ):
            if "tools" in step:
                for m in step["tools"]["messages"]:
                    tools_usadas.append((m.name, m.content))
            if "agent" in step:
                last = step["agent"]["messages"][-1]
                if last.content:
                    resposta = last.content
    except Exception as e:
        msg = str(e)
        if "rate_limit" in msg or "413" in msg or "too large" in msg:
            resposta = ("⚠️ Limite de tokens por minuto da Groq (free tier) atingido. "
                        "Aguarde alguns segundos e tente uma pergunta mais simples, "
                        "ou limpe a conversa para reduzir o histórico.")
        else:
            resposta = f"⚠️ Erro ao consultar o agente: {msg}"
    return resposta, tools_usadas


df = carregar_dados()

st.title("🏢 Agente de Análise de Ofertas Primárias de FII")
st.caption("Fonte: CVM — Ofertas Públicas (Resolução 160) · 2023 a 2026")

tab_chat, tab_dash = st.tabs(["💬 Chat com o Agente", "📊 Dashboard"])


# ─── Aba: Chat ──────────────────────────────────────────────────────────────────

with tab_chat:
    st.markdown(
        "Converse com o agente sobre o mercado de FII. Ele consulta os dados "
        "reais da CVM antes de responder — não inventa números."
    )

    # Estado da sessao: thread_id (memoria) e historico para exibir
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "chat" not in st.session_state:
        st.session_state.chat = []

    # Sugestoes de perguntas
    st.markdown("**Sugestões:**")
    sugestoes = [
        "Faça um resumo geral do mercado de FII.",
        "Como o BTG se compara com a XP em 2025?",
        "Quais as maiores ofertas de FII de 2025?",
    ]
    cols = st.columns(len(sugestoes))
    pergunta_clicada = None
    for col, s in zip(cols, sugestoes):
        if col.button(s, width="stretch"):
            pergunta_clicada = s

    try:
        agent = obter_agente()
    except EnvironmentError as e:
        st.error(str(e))
        st.stop()

    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    # Renderiza o historico
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("tools"):
                with st.expander("🔧 Ferramentas consultadas"):
                    for nome, conteudo in msg["tools"]:
                        st.markdown(f"**{nome}**")
                        st.code(conteudo, language="text")

    # Entrada do usuario (campo de chat ou botao de sugestao)
    pergunta = st.chat_input("Pergunte sobre ofertas de FII...") or pergunta_clicada

    if pergunta:
        st.session_state.chat.append({"role": "user", "content": pergunta})
        with st.chat_message("user"):
            st.markdown(pergunta)

        with st.chat_message("assistant"):
            with st.spinner("Analisando os dados da CVM..."):
                resposta, tools_usadas = responder(agent, config, pergunta)
            st.markdown(resposta)
            if tools_usadas:
                with st.expander("🔧 Ferramentas consultadas"):
                    for nome, conteudo in tools_usadas:
                        st.markdown(f"**{nome}**")
                        st.code(conteudo, language="text")

        st.session_state.chat.append(
            {"role": "assistant", "content": resposta, "tools": tools_usadas}
        )

    if st.session_state.chat:
        if st.button("🗑️ Limpar conversa"):
            st.session_state.chat = []
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()


# ─── Aba: Dashboard ─────────────────────────────────────────────────────────────

with tab_dash:
    st.sidebar.header("Filtros do dashboard")

    st.sidebar.caption("Sem filtro = considera tudo.")

    anos = sorted(df["Ano"].dropna().unique().tolist())
    ano_sel = st.sidebar.multiselect("Ano", anos, default=[])

    grupos = sorted(df["Grupo_Lider"].dropna().unique().tolist())
    grupo_sel = st.sidebar.multiselect("Instituição líder", grupos, default=[])

    tipos = sorted(df["Valor_Mobiliario"].dropna().unique().tolist())
    tipo_sel = st.sidebar.multiselect("Tipo", tipos, default=[])

    status = sorted(df["Status_Requerimento"].dropna().unique().tolist())
    status_sel = st.sidebar.multiselect("Status", status, default=[])

    f = df.copy()
    if ano_sel:
        f = f[f["Ano"].isin(ano_sel)]
    if grupo_sel:
        f = f[f["Grupo_Lider"].isin(grupo_sel)]
    if tipo_sel:
        f = f[f["Valor_Mobiliario"].isin(tipo_sel)]
    if status_sel:
        f = f[f["Status_Requerimento"].isin(status_sel)]

    # Cenario macro (BCB) — contexto para interpretar as emissoes
    macro = carregar_macro()
    if "erro" not in macro:
        st.markdown("**Cenário macroeconômico atual** (Banco Central)")
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Meta Selic", f"{macro['selic']:.2f}%")
        mc2.metric("CDI", f"{macro['cdi']:.2f}%")
        mc3.metric("IPCA 12m", f"{macro['ipca_12m']:.2f}%")
        st.divider()

    st.markdown("**Ofertas de FII (filtro aplicado)**")
    col1, col2, col3 = st.columns(3)
    col1.metric("Ofertas", f"{len(f):,}".replace(",", "."))
    col2.metric("Volume total", f"R$ {f['Valor_Total_Registrado'].sum() / 1e9:.1f} bi")
    ticket = f["Valor_Total_Registrado"].mean() / 1e6 if len(f) else 0
    col3.metric("Ticket médio", f"R$ {ticket:.1f} M")

    st.divider()

    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Volume por ano")
        por_ano = (
            f.groupby("Ano")["Valor_Total_Registrado"].sum().div(1e9).reset_index()
            .rename(columns={"Valor_Total_Registrado": "Volume (R$ bi)"})
        )
        st.plotly_chart(px.bar(por_ano, x="Ano", y="Volume (R$ bi)", text_auto=".1f"),
                        width="stretch")
    with g2:
        st.subheader("Top 10 instituições líderes (volume)")
        por_lider = (
            f.groupby("Grupo_Lider")["Valor_Total_Registrado"].sum().div(1e9)
            .sort_values(ascending=True).tail(10).reset_index()
            .rename(columns={"Valor_Total_Registrado": "Volume (R$ bi)"})
        )
        fig2 = px.bar(por_lider, x="Volume (R$ bi)", y="Grupo_Lider", orientation="h")
        fig2.update_layout(yaxis_title="")
        st.plotly_chart(fig2, width="stretch")

    st.divider()

    st.subheader("Evolução mensal do volume emitido")
    mensal = f.dropna(subset=["Data_Registro"]).copy()
    if not mensal.empty:
        mensal["Mês"] = mensal["Data_Registro"].dt.to_period("M").dt.to_timestamp()
        serie = (
            mensal.groupby("Mês")["Valor_Total_Registrado"].sum().div(1e9).reset_index()
            .rename(columns={"Valor_Total_Registrado": "Volume (R$ bi)"})
        )
        fig3 = px.area(serie, x="Mês", y="Volume (R$ bi)", markers=True)
        st.plotly_chart(fig3, width="stretch")
    else:
        st.info("Sem dados de data para os filtros selecionados.")

    st.divider()

    st.subheader(f"Ofertas ({len(f):,} resultados)".replace(",", "."))
    tabela = f[[
        "Data_Registro", "Nome_Emissor", "Grupo_Lider",
        "Valor_Total_Registrado", "Publico_alvo", "Status_Requerimento",
    ]].sort_values("Data_Registro", ascending=False).copy()
    tabela["Data_Registro"] = tabela["Data_Registro"].dt.strftime("%d/%m/%Y")
    tabela["Valor_Total_Registrado"] = tabela["Valor_Total_Registrado"].apply(
        lambda v: f"R$ {v/1e6:.1f}M" if pd.notna(v) else "N/D"
    )
    tabela.columns = ["Data", "Emissor", "Líder", "Volume", "Público-alvo", "Status"]
    st.dataframe(tabela, width="stretch", hide_index=True)
