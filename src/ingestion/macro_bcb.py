#!/usr/bin/env python3
"""
Indicadores macroeconomicos do Banco Central (API SGS).

O SGS (Sistema Gerenciador de Series Temporais) e uma API publica em JSON.
Cada indicador tem um codigo numerico:
  - 432  = Meta Selic (% a.a.)
  - 4389 = CDI anualizado (% a.a., base 252)
  - 433  = IPCA - variacao mensal (%)

Endpoint usado (ultimos N valores de uma serie):
  https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/{n}?formato=json

Uso direto (teste):
    python src/ingestion/macro_bcb.py
"""

import requests

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados/ultimos/{n}?formato=json"

COD_SELIC = 432
COD_CDI = 4389
COD_IPCA = 433


def _serie(cod: int, n: int = 1) -> list[dict]:
    url = SGS_URL.format(cod=cod, n=n)
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.json()


def obter_indicadores() -> dict:
    """Busca Selic, CDI e IPCA 12m. Em caso de falha, retorna {'erro': ...}."""
    try:
        selic = _serie(COD_SELIC, 1)[-1]
        cdi = _serie(COD_CDI, 1)[-1]
        ipca_12 = _serie(COD_IPCA, 12)

        # IPCA acumulado 12m: composto, nao soma simples
        acumulado = 1.0
        for item in ipca_12:
            acumulado *= 1 + float(item["valor"]) / 100
        ipca_12m = (acumulado - 1) * 100

        return {
            "selic": float(selic["valor"]),
            "selic_data": selic["data"],
            "cdi": float(cdi["valor"]),
            "ipca_12m": round(ipca_12m, 2),
            "ipca_ref": ipca_12[-1]["data"],
        }
    except Exception as e:  # rede/API fora do ar
        return {"erro": f"Nao foi possivel obter indicadores do BCB: {e}"}


if __name__ == "__main__":
    print(obter_indicadores())
