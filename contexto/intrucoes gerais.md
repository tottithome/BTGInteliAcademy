Alguns pontos importantes da entrega:

* Enviar o repositório do projeto no GitHub com documentação apropriada

Upload dos slides em PDF
* Os slides devem conter:
* Capa
* Arquitetura do sistema
* Exemplo de saída do agente
* Demo em vídeo
* Desafios, aprendizados e próximos passos
* QR Codes do LinkedIn e do repositório

site que ta no exemplo, troque o g1.globo pela url que vcs quiserem
https://r.jina.ai/g1.globo.com

https://docs.langchain.com/langsmith/prompt-engineering

IMPORTANTE GERAL
tenho algumas anotacoes:
o escopo inicial vai ser apenas com fundos imobiliarios





Skip to main content
Logo
Autoestudos
Mascote Inteli Academy
GitHub

Bem-vindo aos Autoestudos
Aulas
Conceitos Básicos de LLM
Funcionamento das LLMs
Tokens
Janela de Contexto
Parâmetros
Temperatura
Prompting
Alucinação
Function Calling
Projetos
BTG Pactual
Materiais
Fontes de Estudo
ProjetosBTG PactualMateriaisFontes de Estudo
Fontes de Estudo
Recursos de estudo para as tecnologias utilizadas no projeto do BTG Pactual para fazer um agente inteligente de análise e contextualização de ofertas primárias.

As ferramentas estão organizadas em duas categorias: principais, que formam o núcleo do sistema, e complementares, que estendem suas capacidades em áreas específicas.

Ferramentas Principais
LangChain
Parte central do projeto: orquestra o agente, conecta o modelo de linguagem às ferramentas de coleta e análise, e gerencia a memória vetorial para recuperação semântica de comparáveis históricos.

Documentação
Visão geral — Arquitetura do framework e como seus componentes se conectam.
Quickstart — Primeira aplicação funcional passo a passo. Ponto de partida recomendado.
Agents — Como criar agentes que tomam decisões e encadeiam ações de forma autônoma.
Tools — Integração do agente com funções externas como scraping, APIs e bancos de dados.
GitHub oficial — Código-fonte e exemplos prontos para explorar.
Vídeos
LangChain IA — Introdução.
Tutorial básico — Guia direto ao ponto para primeiros contatos.
Criando Agentes de IA — Implementação prática de agentes com ferramentas customizadas.
Curso COMPLETO LangChain — Do básico ao avançado, cobrindo todos os componentes principais.
Streamlit
Interface do projeto: o dashboard interativo que permite ao usuário explorar diferenças de taxas por instituição, filtrar por tipo de ativo, indexador e período, e visualizar os insights gerados pelo agente.

Documentação
Documentação principal — Central da ferramenta com todos os guias disponíveis.
Get Started — Primeiro app funcional em minutos. Ponto de partida recomendado.
API Reference — Catálogo completo de componentes disponíveis (gráficos, tabelas, filtros, etc.).
Session State — Gerenciamento de estado entre interações do usuário — necessário para filtros dinâmicos no dashboard.
Cache Data — Otimização de performance para evitar reprocessar dados a cada interação.
GitHub oficial — Código-fonte e exemplos.
Vídeos
Streamlit em 10 min — Introdução rápida aos conceitos essenciais.
Dashboard em 30 min — Criação prática de um dashboard completo.
Alternativa ao Power BI — Como construir dashboards analíticos com Python puro.
Dashboards profissionais — Layouts avançados e boas práticas de apresentação.
Curso completo — Conteúdo aprofundado para ir além do básico.
Ferramentas Complementares
Playwright
Usado em conjunto com o LangChain para a coleta automatizada de dados em plataformas que não disponibilizam APIs públicas.

Introdução — Setup e primeiros scripts.
Locators — Seleção de elementos da página.
Codegen — Gera código automaticamente a partir da navegação gravada.
Automação Python — Tutorial prático focado em Python.
Plotly
Usado dentro do Streamlit para gerar os gráficos interativos do dashboard.

Plotly Express — API simplificada para criação rápida de visualizações.
Time Series — Gráficos de séries temporais, aplicável à evolução das taxas no projeto.
Criar gráficos — Tutorial direto e prático.
python-bcb
Usado junto ao LangChain para coletar indicadores macroeconômicos do Banco Central (Selic, IPCA, CDI, câmbio).

Documentação oficial — Guia completo com todos os módulos disponíveis.
SGS — Séries Temporais — Como buscar séries como IPCA, Selic e CDI em um DataFrame pandas.
Catálogo SGS (BCB) — Encontre o código numérico de qualquer indicador disponível.
Coletando Dados Do Banco Central Usando o Python — Introdução prática ao SGS.
st-aggrid
Extensão do Streamlit para tabelas interativas com filtragem, ordenação e seleção de linhas.

GitHub oficial — Código-fonte e exemplos de uso.
Documentação oficial — Referência da API do AgGrid e do GridOptionsBuilder.
Streamlit Ag-Grid Tutorial — Select Rows, Drilldown & Plotly Charts — Demonstração com integração direta ao Plotly.
Previous
Function Calling
Ferramentas Principais
LangChain
Streamlit
Ferramentas Complementares
Playwright
Plotly
python-bcb
st-aggrid