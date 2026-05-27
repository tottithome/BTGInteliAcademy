#!/usr/bin/env python3
"""
Coleta de ofertas primarias de Fundos Imobiliarios (FII) na CVM.

Fonte: CVM Dados Abertos (Ofertas Publicas de Distribuicao)
  https://dados.cvm.gov.br/dataset/oferta-distrib

O ZIP contem dois CSVs. Usamos o `oferta_resolucao_160.csv` (rito automatico,
2023 em diante), que tem os dados mais ricos e atuais de cada oferta:
emissor, instituicao lider, volume, datas, publico-alvo, bookbuilding, etc.

Detalhes tecnicos do CSV da CVM:
  - separador: ponto-e-virgula (;)
  - encoding: latin-1 (acentos quebram se lido como utf-8)

Fluxo:
  baixar ZIP -> extrair CSV -> filtrar FIIs -> salvar data/cvm/ofertas_fii.csv

Uso:
    python src/ingestion/cvm_fii.py
"""

import io
import zipfile
import unicodedata
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "cvm"

ZIP_URL = "https://dados.cvm.gov.br/dados/OFERTA/DISTRIB/DADOS/oferta_distribuicao.zip"
CSV_RESOLUCAO_160 = "oferta_resolucao_160.csv"

OUTPUT_CSV = DATA_DIR / "ofertas_fii.csv"


def _normalize(texto: str) -> str:
    """Remove acentos e baixa caixa, para comparacoes robustas."""
    if not isinstance(texto, str):
        return ""
    sem_acento = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


# Normalizacao de entidades: a mesma instituicao aparece com varias razoes
# sociais (ex: BTG tem 3). Consolidamos num "grupo" para comparacao justa.
# A ordem importa: o primeiro padrao que casar vence.
_GRUPOS_LIDER = [
    ("btg", "BTG Pactual"),
    ("xp ", "XP"),
    ("itau", "Itau"),
    ("genial", "Genial"),
    ("bradesco", "Bradesco"),
    ("santander", "Santander"),
    ("safra", "Safra"),
    ("caixa", "Caixa"),
    ("votorantim", "BV (Votorantim)"),
    ("vortx", "Vortx"),
    ("brl trust", "BRL Trust"),
    ("opea", "Opea"),
    ("daycoval", "Daycoval"),
    ("inter", "Inter"),
]


def consolidar_grupo(nome_lider: str) -> str:
    """Mapeia a razao social para o grupo economico. Se nao reconhecer, devolve o nome original."""
    n = _normalize(nome_lider)
    for chave, grupo in _GRUPOS_LIDER:
        if chave in n:
            return grupo
    return nome_lider if isinstance(nome_lider, str) else "N/D"


def baixar_csv_resolucao_160() -> pd.DataFrame:
    """Baixa o ZIP da CVM e devolve o CSV da Resolucao 160 como DataFrame."""
    print(f"Baixando dados da CVM...\n  {ZIP_URL}")
    resp = requests.get(ZIP_URL, timeout=120)
    resp.raise_for_status()
    print(f"  Tamanho: {len(resp.content) / 1e6:.1f} MB")

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        nomes = [n for n in zf.namelist() if n.endswith(".csv")]
        if CSV_RESOLUCAO_160 not in nomes:
            raise FileNotFoundError(
                f"{CSV_RESOLUCAO_160} nao encontrado no ZIP. Disponiveis: {nomes}"
            )
        with zf.open(CSV_RESOLUCAO_160) as f:
            df = pd.read_csv(
                f, sep=";", encoding="latin-1",
                engine="python", on_bad_lines="skip",
            )
    print(f"  {len(df):,} ofertas no total, {len(df.columns)} colunas")
    return df


def filtrar_fii(df: pd.DataFrame) -> pd.DataFrame:
    """Mantem apenas ofertas de cotas de fundo imobiliario (FII).

    ATENCAO: filtramos pela sigla 'fii' (ex: 'Cotas de FII', 'Cotas de FIAGRO - FII').
    NAO usamos a palavra 'imobiliario' porque ela casaria com CRI (Certificados
    de Recebiveis Imobiliarios), que sao titulos de divida, nao fundos.
    """
    print("\nTipos de valor mobiliario disponiveis (top 12):")
    print(df["Valor_Mobiliario"].value_counts().head(12).to_string())

    valor_norm = df["Valor_Mobiliario"].map(_normalize)
    mascara = valor_norm.str.contains(r"\bfii\b", na=False, regex=True)
    fii = df[mascara].copy()
    print(f"\nOfertas de FII encontradas: {len(fii):,}")
    print("Distribuicao por tipo:")
    print(fii["Valor_Mobiliario"].value_counts().to_string())
    return fii


def salvar(df: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False, sep=";", encoding="utf-8")
    print(f"\nSalvo em: {OUTPUT_CSV}")


def main() -> None:
    df = baixar_csv_resolucao_160()
    fii = filtrar_fii(df)

    if fii.empty:
        print("Nenhuma oferta de FII encontrada — verifique o nome da coluna/filtro.")
        return

    fii["Grupo_Lider"] = fii["Nome_Lider"].map(consolidar_grupo)

    colunas_interesse = [
        "Data_Registro", "Valor_Mobiliario", "Nome_Emissor", "Nome_Lider", "Grupo_Lider",
        "Valor_Total_Registrado", "Qtde_Total_Registrada",
        "Publico_alvo", "Regime_distribuicao", "Bookbuilding",
        "Status_Requerimento", "Numero_Requerimento",
    ]
    presentes = [c for c in colunas_interesse if c in fii.columns]
    print(f"\nPrevia das ofertas de FII (colunas principais):")
    print(fii[presentes].head(10).to_string(index=False))

    salvar(fii)


if __name__ == "__main__":
    main()
