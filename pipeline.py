"""
pipeline.py
Pipeline de tratamento de dados do SIM/DATASUS.
Recebe bytes do arquivo, retorna DataFrame tratado + logs + métricas.
"""

import gc
import io
import os
import tempfile

import pandas as pd

from conversores import (
    convert_sexo, convert_raca_cor, convert_estciv,
    converter_idade, converter_escolaridade,
    MAPA_UF, MAPA_LOCOCOR,
)

# ─── Constantes ───────────────────────────────────────────────────────────────

COLUNAS = [
    "IDADE","SEXO","RACACOR","DTOBITO","CAUSABAS","NATURAL","CODMUNNATU","ESTCIV",
    "ESC2010","OCUP","CODMUNRES","LOCOCOR","CODMUNOCOR"
]

CIDS = (
    ["C910","C911","C912","C913","C914","C915","C917","C919",
     "C920","C921","C922","C923","C924","C925","C927","C929"] +
    [f"C93{i}" for i in range(10)]
)


# ─── Tratamento de um chunk ───────────────────────────────────────────────────

def tratar_chunk(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica todos os passos de tratamento em um DataFrame ou chunk."""

    # Passo 1 – Colunas
    cols = [c for c in COLUNAS if c in df.columns]
    df = df[cols].copy()

    # Passo 2 – Filtro CIDs
    df["CAUSABAS"] = df["CAUSABAS"].astype(str).str.strip().str.upper()
    df = df[df["CAUSABAS"].isin(CIDS)]
    if df.empty:
        return df

    # Passo 3 – Remove valores ausentes
    df = df.dropna()

    # Passo 4 – SEXO
    df["SEXO"] = df["SEXO"].apply(convert_sexo)

    # Passo 5 – RACACOR
    df["RACACOR"] = df["RACACOR"].apply(convert_raca_cor)

    # Passo 6 – ESTCIV
    df["ESTCIV"] = df["ESTCIV"].apply(convert_estciv)

    # Passo 7 – IDADE
    df["IDADE"] = df["IDADE"].apply(converter_idade)
    df = df.dropna(subset=["IDADE"])

    # Passo 8 – ESC2010
    df["ESC2010"] = df["ESC2010"].apply(converter_escolaridade)

    # Passo 9 – UF
    df["NATURAL"]    = df["NATURAL"].astype(str).str.zfill(3)
    df["CODMUNOCOR"] = df["CODMUNOCOR"].astype(str).str.zfill(7)
    df["UF_NATURAL"] = df["NATURAL"].str[-2:].map(MAPA_UF)
    df["UF_OCOR"]    = df["CODMUNOCOR"].str[1:3].map(MAPA_UF)
    
    df.drop(columns=["NATURAL"])
    # Passo 10 – LOCOCOR
    df["LOCOCOR_DESC"] = df["LOCOCOR"].astype(str).str.strip().map(MAPA_LOCOCOR)

    return df


# ─── Pipeline principal ───────────────────────────────────────────────────────

def executar_pipeline(arquivo_bytes: bytes, nome_arquivo: str,
                      chunk_size: int = 100_000) -> dict:
    """
    Executa o pipeline completo de tratamento.

    Retorna um dicionário com:
        df        → DataFrame tratado (ou None)
        logs      → lista de (tipo, mensagem)
        metricas  → dict com números para o relatório
    """
    logs    = []
    ok      = lambda m: logs.append(("ok",   m))
    erro    = lambda m: logs.append(("err",  m))
    info    = lambda m: logs.append(("info", m))
    warn    = lambda m: logs.append(("warn", m))

    metricas = {
        "nome_arquivo":    nome_arquivo,
        "tamanho_mb":      round(len(arquivo_bytes) / (1024**2), 1),
        "linhas_inicial":  0,
        "colunas_inicial": 0,
        "linhas_final":    0,
        "colunas_final":   0,
        "reducao_pct":     0.0,
        "cids_encontrados": [],
        "modo_leitura":    "",
    }

    ext    = os.path.splitext(nome_arquivo)[-1].lower()
    tam_mb = metricas["tamanho_mb"]

    info(f"Arquivo recebido: {nome_arquivo}  ({tam_mb} MB)")

    # Salva em disco temporário para não duplicar na RAM
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp.write(arquivo_bytes)
    tmp.flush()
    tmp_path = tmp.name
    tmp.close()
    del arquivo_bytes
    gc.collect()

    linhas_inicial  = 0
    chunks_prontos  = []

    try:
        # ── Excel ──────────────────────────────────────────────────────────────
        if ext in (".xlsx", ".xls"):
            if tam_mb > 200:
                warn(f"Arquivo Excel grande ({tam_mb} MB). Prefira CSV para arquivos acima de 200 MB.")
            metricas["modo_leitura"] = "Excel (leitura completa)"
            ok(f"Lendo arquivo Excel ({tam_mb} MB)…")
            df_raw = pd.read_excel(tmp_path, dtype=str)
            linhas_inicial             = len(df_raw)
            metricas["colunas_inicial"] = df_raw.shape[1]
            info(f"Dataset inicial: {linhas_inicial:,} linhas × {df_raw.shape[1]} colunas")
            resultado = tratar_chunk(df_raw)
            del df_raw; gc.collect()
            chunks_prontos.append(resultado)

        # ── CSV com chunks ─────────────────────────────────────────────────────
        elif ext == ".csv":
            metricas["modo_leitura"] = f"CSV em chunks de {chunk_size:,} linhas"
            if tam_mb > 50:
                info(f"Arquivo grande ({tam_mb} MB) — processando em chunks de {chunk_size:,} linhas")
            n = 0
            for chunk in pd.read_csv(tmp_path, dtype=str, sep=None,
                                      engine="python", chunksize=chunk_size):
                if n == 0:
                    metricas["colunas_inicial"] = chunk.shape[1]
                linhas_inicial += len(chunk)
                resultado = tratar_chunk(chunk)
                if not resultado.empty:
                    chunks_prontos.append(resultado)
                n += 1
                del chunk, resultado; gc.collect()
            ok(f"CSV processado em {n} chunk(s)  |  {linhas_inicial:,} linhas no total")

        else:
            erro(f"Formato '{ext}' não suportado. Use .xlsx ou .csv")
            return {"df": None, "logs": logs, "metricas": metricas}

    except Exception as e:
        erro(f"Erro ao processar arquivo: {e}")
        return {"df": None, "logs": logs, "metricas": metricas}
    finally:
        os.unlink(tmp_path)

    if not chunks_prontos:
        erro("Nenhuma linha com CIDs C91/C92/C93 encontrada no arquivo.")
        return {"df": None, "logs": logs, "metricas": metricas}

    df_final = pd.concat(chunks_prontos, ignore_index=True)
    del chunks_prontos; gc.collect()

    # ── Métricas finais ────────────────────────────────────────────────────────
    metricas["linhas_inicial"]   = linhas_inicial
    metricas["linhas_final"]     = len(df_final)
    metricas["colunas_final"]    = df_final.shape[1]
    metricas["reducao_pct"]      = round((1 - len(df_final) / linhas_inicial) * 100, 1) if linhas_inicial > 0 else 0
    metricas["cids_encontrados"] = sorted(df_final["CAUSABAS"].unique().tolist())

    ok("Passo 1  — Colunas relevantes selecionadas")
    ok("Passo 2  — Filtro por CIDs C91/C92/C93 aplicado")
    ok("Passo 3  — Registros com dados ausentes removidos")
    ok("Passo 4  — SEXO convertido para texto")
    ok("Passo 5  — RACACOR convertida para texto")
    ok("Passo 6  — Estado civil (ESTCIV) convertido para texto")
    ok("Passo 7  — IDADE convertida para anos decimais")
    ok("Passo 8  — Escolaridade (ESC2010) convertida para texto")
    ok("Passo 9  — UF de naturalidade e ocorrência criadas")
    ok("Passo 10 — Local de ocorrência (LOCOCOR_DESC) criado")
    info(f"Dataset final: {len(df_final):,} linhas × {df_final.shape[1]} colunas  |  redução: {metricas['reducao_pct']}%")

    return {"df": df_final, "logs": logs, "metricas": metricas}