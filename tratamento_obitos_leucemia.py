"""
Tratamento de dados de óbitos por leucemia (CIDs C91-C93)
Fonte: SIM/DATASUS - arquivo .xlsx
Autor: gerado via Claude
"""

import pandas as pd
import numpy as np
import logging
import os

# ─── Configuração de logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ─── Funções auxiliares de conversão ─────────────────────────────────────────

def convert_sexo(sexo):
    if sexo == 1 or sexo == "1":
        return "Masculino"
    elif sexo == 2 or sexo == "2":
        return "Feminino"
    return sexo


def convert_raca_cor(raca):
    mapa = {"1": "Branca", "2": "Preta", "3": "Amarela", "4": "Parda", "5": "Indigena"}
    return mapa.get(str(raca), raca)


def convert_estciv(estciv):
    if pd.isna(estciv):
        return np.nan
    mapa = {
        1: "Solteiro", 2: "Casado", 3: "Viuvo",
        4: "Divorciado", 5: "Uniao Estavel", 9: "Ignorado"
    }
    try:
        return mapa.get(int(estciv), np.nan)
    except (ValueError, TypeError):
        return np.nan


def converter_idade(idade):
    if pd.isna(idade):
        return np.nan
    try:
        idade_str = str(int(idade)).zfill(3)
        unidade = int(idade_str[0])
        valor = int(idade_str[1:])
    except (ValueError, TypeError):
        return np.nan

    conversoes = {
        1: valor / (60 * 24 * 365),   # minutos → anos
        2: valor / (24 * 365),         # horas → anos
        3: valor / 12,                  # meses → anos
        4: valor,                        # anos
        5: 100,                          # >100 anos
        9: np.nan,                       # ignorado
    }
    return conversoes.get(unidade, np.nan)


def converter_escolaridade(valor):
    if pd.isna(valor):
        return np.nan
    mapa = {
        0: "Sem escolaridade",
        1: "Fundamental I (1ª a 4ª série)",
        2: "Fundamental II (5ª a 8ª série)",
        3: "Ensino Médio",
        4: "Superior incompleto",
        5: "Superior completo",
        9: "Ignorado",
    }
    try:
        return mapa.get(int(valor), np.nan)
    except (ValueError, TypeError):
        return np.nan


# ─── Função principal ─────────────────────────────────────────────────────────

def tratar_obitos_leucemia(caminho_arquivo: str) -> pd.DataFrame | None:
    """
    Lê um arquivo Excel (.xlsx) do SIM/DATASUS, aplica todos os tratamentos
    necessários e retorna o DataFrame limpo.

    Parâmetros
    ----------
    caminho_arquivo : str
        Caminho completo para o arquivo .xlsx de entrada.

    Retorna
    -------
    pd.DataFrame com os dados tratados, ou None em caso de erro fatal.
    """

    # ── Verificação do arquivo ────────────────────────────────────────────────
    if not os.path.exists(caminho_arquivo):
        log.error("Arquivo não encontrado: %s", caminho_arquivo)
        return None

    # ── Leitura ───────────────────────────────────────────────────────────────
    log.info("Lendo arquivo: %s", caminho_arquivo)
    extensao = os.path.splitext(caminho_arquivo)[-1].lower()
    try:
        if extensao == ".xlsx" or extensao == ".xls":
            df = pd.read_excel(caminho_arquivo, dtype=str)
            log.info("Formato detectado: Excel (%s)", extensao)
        
        elif extensao == ".csv":
            # Tenta com encoding 'latin1' primeiro; se falhar, tenta sem encoding
            try:
                df = pd.read_csv(caminho_arquivo, dtype=str, sep=None, engine="python", encoding='latin1')
                log.info("Formato detectado: CSV (encoding='latin1', separador detectado automaticamente)")
            except (UnicodeDecodeError, Exception) as e:
                log.warning("Falha com encoding='latin1': %s. Tentando sem encoding...", e)
                df = pd.read_csv(caminho_arquivo, dtype=str, sep=None, engine="python")
                log.info("Formato detectado: CSV (encoding padrão, separador detectado automaticamente)")
        else:
            log.error("Formato não suportado: '%s'. Use .xlsx, .xls ou .csv.", extensao)
            return None

        log.info("Arquivo lido com sucesso. Shape inicial: %s", df.shape)
        log.debug("Colunas encontradas: %s", df.columns.tolist())
    except Exception as e:
        log.error("Erro ao ler o arquivo: %s", e)
        return None

    tamanho_inicial = df.shape
    log.info("📊 Dataset inicial: %d linhas × %d colunas", *tamanho_inicial)

    # ── Passo 1 – Selecionar colunas ─────────────────────────────────────────
    colunas = [
        "DTOBITO","NATURAL", "CODMUNNATU", "IDADE", "SEXO", "RACACOR", "ESTCIV",
        "ESC2010", "OCUP", "CODMUNRES", "LOCOCOR", "CODMUNOCOR",
        "CAUSABAS"
    ]
    colunas_existentes = [c for c in colunas if c in df.columns]
    colunas_ausentes   = [c for c in colunas if c not in df.columns]

    if colunas_ausentes:
        log.warning("Colunas não encontradas e ignoradas: %s", colunas_ausentes)

    try:
        df = df[colunas_existentes]
        log.info("Passo 1 ✅ – %d colunas selecionadas.", len(colunas_existentes))
        # log.inf("\n %d",{colunas})
    except Exception as e:
        log.error("Passo 1 ❌ – Erro ao selecionar colunas: %s", e)
        return None

    # ── Passo 2 – Filtrar CIDs (C91, C92, C93) ───────────────────────────────
    cids_base = [
        "C910","C911","C912","C913","C914","C915","C917","C919",
        "C920","C921","C922","C923","C924","C925","C927","C929",
    ]
    cids_c93 = [f"C93{i}" for i in range(10)]
    cids = cids_base + cids_c93

    try:
        antes = len(df)
        df["CAUSABAS"] = df["CAUSABAS"].astype(str).str.strip().str.upper()
        df = df[df["CAUSABAS"].isin(cids)]
        log.info("Passo 2 ✅ – CIDs filtrados: %d → %d linhas.", antes, len(df))
    except Exception as e:
        log.error("Passo 2 ❌ – Erro no filtro de CIDs: %s", e)
        return None

    if df.empty:
        log.warning("Nenhuma linha restou após filtro de CIDs. Verifique os dados.")
        return df

    # ── Passo 3 – Remover linhas com valores ausentes ─────────────────────────
    try:
        antes = len(df)
        df = df.dropna()
        log.info("Passo 3 ✅ – dropna: %d → %d linhas.", antes, len(df))
    except Exception as e:
        log.error("Passo 3 ❌ – Erro no dropna: %s", e)
        return None

    # ── Passo 4 – SEXO ────────────────────────────────────────────────────────
    try:
        df["SEXO"] = df["SEXO"].apply(convert_sexo)
        log.info("Passo 4 ✅ – SEXO convertido. Valores únicos: %s", df["SEXO"].unique().tolist())
    except Exception as e:
        log.error("Passo 4 ❌ – Erro ao converter SEXO: %s", e)

    # ── Passo 5 – RACACOR ─────────────────────────────────────────────────────
    try:
        df["RACACOR"] = df["RACACOR"].apply(convert_raca_cor)
        log.info("Passo 5 ✅ – RACACOR convertida. Valores únicos: %s", df["RACACOR"].unique().tolist())
    except Exception as e:
        log.error("Passo 5 ❌ – Erro ao converter RACACOR: %s", e)

    # ── Passo 6 – ESTCIV ──────────────────────────────────────────────────────
    try:
        df["ESTCIV"] = df["ESTCIV"].apply(convert_estciv)
        log.info("Passo 6 ✅ – ESTCIV convertido. Valores únicos: %s", df["ESTCIV"].unique().tolist())
    except Exception as e:
        log.error("Passo 6 ❌ – Erro ao converter ESTCIV: %s", e)

    # ── Passo 7 – IDADE ───────────────────────────────────────────────────────
    try:
        antes = len(df)
        df["IDADE"] = df["IDADE"].apply(converter_idade)
        df = df.dropna(subset=["IDADE"])
        log.info("Passo 7 ✅ – IDADE convertida: %d → %d linhas. Faixa: %.2f–%.2f anos.",
                 antes, len(df), df["IDADE"].min(), df["IDADE"].max())
    except Exception as e:
        log.error("Passo 7 ❌ – Erro ao converter IDADE: %s", e)

    # ── Passo 8 – ESC2010 ─────────────────────────────────────────────────────
    try:
        df["ESC2010"] = df["ESC2010"].apply(converter_escolaridade)
        log.info("Passo 8 ✅ – ESC2010 convertida. Valores únicos: %s", df["ESC2010"].unique().tolist())
    except Exception as e:
        log.error("Passo 8 ❌ – Erro ao converter ESC2010: %s", e)

    # ── Passo 9 – Localidade (UF_NATURAL e UF_OCOR) ───────────────────────────
    mapa_uf = {
        "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
        "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
        "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
        "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
        "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
        "52": "GO", "53": "DF",
    }
    try:
        df["NATURAL"]     = df["NATURAL"].astype(str).str.zfill(3)
        df["CODMUNOCOR"]  = df["CODMUNOCOR"].astype(str).str.zfill(7)
        df["UF_NATURAL"]  = df["NATURAL"].str[-2:].map(mapa_uf)
        df["UF_OCOR"]     = df["CODMUNOCOR"].str[1:3].map(mapa_uf)
        df.drop(columns = ['NATURAL'])
        log.info("Passo 9 ✅ – UF_NATURAL e UF_OCOR criadas.")
        log.debug("UF_NATURAL nulos: %d | UF_OCOR nulos: %d",
                  df["UF_NATURAL"].isna().sum(), df["UF_OCOR"].isna().sum())
        
    except Exception as e:
        log.error("Passo 9 ❌ – Erro ao tratar localidade: %s", e)

    # ── Passo 10 – LOCOCOR ────────────────────────────────────────────────────
    mapa_lococor = {
        "1": "Hospital",
        "2": "Outro estabelecimento de saúde",
        "3": "Domicílio",
        "4": "Via pública",
        "5": "Outros",
        "6": "Aldeia indígena",
        "9": "Ignorado",
    }
    try:
        df["LOCOCOR"] = df["LOCOCOR"].astype(str).str.strip().map(mapa_lococor)
        log.info("Passo 10 ✅ – LOCOCOR atualizada. Valores únicos: %s",
                 df["LOCOCOR"].unique().tolist())
        
        # df.drop(columns = ["LOCOCOR"])
    except Exception as e:
        log.error("Passo 10 ❌ – Erro ao tratar LOCOCOR: %s", e)

    # ── Resumo final ──────────────────────────────────────────────────────────
    tamanho_final = df.shape
    log.info("=" * 55)
    log.info("📊 Dataset inicial : %d linhas × %d colunas", *tamanho_inicial)
    log.info("📊 Dataset final   : %d linhas × %d colunas", *tamanho_final)
    reducao = (1 - tamanho_final[0] / tamanho_inicial[0]) * 100 if tamanho_inicial[0] > 0 else 0
    log.info("📉 Redução de linhas: %.1f%%", reducao)
    log.info("=" * 55)

    return df


# ─── Execução direta (teste local) ───────────────────────────────────────────
if __name__ == "__main__":
    ARQUIVO = "dados_sim.xlsx"          # ← altere para o caminho real
    resultado = tratar_obitos_leucemia(ARQUIVO)

    if resultado is not None:
        print(resultado.head())
        resultado.to_excel("dados_tratados.xlsx", index=False)
        log.info("Arquivo salvo como dados_tratados.xlsx")