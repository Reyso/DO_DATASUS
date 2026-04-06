"""
Webapp – Tratamento de Óbitos por Leucemia (SIM/DATASUS)
Execute com:  streamlit run app.py
"""

import io
import os
import logging
import tempfile

import numpy as np
import pandas as pd
import streamlit as st

# ─── Página ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SIM · Leucemia",
    page_icon="🩸",
    layout="centered",
)

# ─── Estilo visual ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Mono', monospace;
    background-color: #0d0d0d;
    color: #e8e2d5;
}

h1, h2, h3 {
    font-family: 'Syne', sans-serif;
    letter-spacing: -0.03em;
}

/* Cabeçalho */
.header-block {
    background: linear-gradient(135deg, #1a0a0a 0%, #2d0f0f 100%);
    border: 1px solid #5c1a1a;
    border-radius: 12px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
}
.header-block h1 { color: #e05c5c; font-size: 2.2rem; margin: 0 0 .4rem 0; }
.header-block p  { color: #a08080; margin: 0; font-size: .9rem; }

/* Cards de métricas */
.metric-row { display: flex; gap: 1rem; margin: 1.5rem 0; }
.metric-card {
    flex: 1;
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
}
.metric-card .label { font-size: .75rem; color: #666; text-transform: uppercase; letter-spacing: .1em; }
.metric-card .value { font-size: 1.8rem; font-family: 'Syne', sans-serif; color: #e8e2d5; margin-top: .2rem; }
.metric-card .sub   { font-size: .8rem; color: #888; margin-top: .2rem; }

/* Passos */
.step {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    padding: .7rem 0;
    border-bottom: 1px solid #1e1e1e;
    font-size: .88rem;
}
.step:last-child { border-bottom: none; }
.step-icon { font-size: 1.1rem; min-width: 1.5rem; }
.step-text { color: #b0a090; }
.step-ok   { color: #5ecfa0; }
.step-err  { color: #e05c5c; }

/* Upload zone */
section[data-testid="stFileUploadDropzone"] {
    background: #111 !important;
    border: 2px dashed #3a1f1f !important;
    border-radius: 10px !important;
}

/* Botão download */
.stDownloadButton > button {
    background: #e05c5c !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: .75rem 2rem !important;
    width: 100% !important;
    margin-top: 1rem;
    transition: background .2s;
}
.stDownloadButton > button:hover { background: #c94444 !important; }

/* Botão processar */
.stButton > button {
    background: #1e1e1e !important;
    color: #e8e2d5 !important;
    border: 1px solid #3a3a3a !important;
    border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: .9rem !important;
    padding: .65rem 1.5rem !important;
    width: 100% !important;
}
.stButton > button:hover {
    border-color: #e05c5c !important;
    color: #e05c5c !important;
}

/* Dataframe */
.stDataFrame { border-radius: 8px; overflow: hidden; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0d0d0d !important;
    border-right: 1px solid #1e1e1e !important;
            
}
            
/* Texto geral do sidebar */
[data-testid="stSidebar"] * {
    color: #f9f9f7 !important;
}

/* Labels (ex: st.selectbox, st.radio) */
[data-testid="stSidebar"] label {
    color: #f9f9f7 !important;
}

/* Inputs e textos menores */
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stText {
    color: #f9f9f7 !important;
}
            
/* Destaque para extensões (.csv, .xlsx) */
code {
    background: #1e1e1e !important;
    color: #e05c5c !important;
    padding: 2px 6px !important;
    border-radius: 6px !important;
    font-size: 0.85rem !important;
    border: 1px solid #3a1f1f !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Funções de conversão ─────────────────────────────────────────────────────

def convert_sexo(sexo):
    if sexo in (1, "1"): return "Masculino"
    if sexo in (2, "2"): return "Feminino"
    return sexo

def convert_raca_cor(raca):
    mapa = {"1": "Branca", "2": "Preta", "3": "Amarela", "4": "Parda", "5": "Indigena"}
    return mapa.get(str(raca), raca)

def convert_estciv(estciv):
    if pd.isna(estciv): return np.nan
    mapa = {1:"Solteiro",2:"Casado",3:"Viuvo",4:"Divorciado",5:"Uniao Estavel",9:"Ignorado"}
    try: return mapa.get(int(estciv), np.nan)
    except: return np.nan

def converter_idade(idade):
    if pd.isna(idade): return np.nan
    try:
        s = str(int(float(idade))).zfill(3)
        u, v = int(s[0]), int(s[1:])
    except: return np.nan
    return {1: v/(60*24*365), 2: v/(24*365), 3: v/12, 4: v, 5: 100, 9: np.nan}.get(u, np.nan)

def converter_escolaridade(valor):
    if pd.isna(valor): return np.nan
    mapa = {0:"Sem escolaridade",1:"Fundamental I (1ª a 4ª série)",
            2:"Fundamental II (5ª a 8ª série)",3:"Ensino Médio",
            4:"Superior incompleto",5:"Superior completo",9:"Ignorado"}
    try: return mapa.get(int(float(valor)), np.nan)
    except: return np.nan


# ─── Pipeline principal ───────────────────────────────────────────────────────

def tratar_dados(arquivo_bytes: bytes, nome_arquivo: str):
    logs   = []
    ok     = lambda msg: logs.append(("ok",  msg))
    erro   = lambda msg: logs.append(("err", msg))
    info   = lambda msg: logs.append(("info", msg))

    # Leitura
    ext = os.path.splitext(nome_arquivo)[-1].lower()
    try:
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(io.BytesIO(arquivo_bytes), dtype=str)
            ok(f"Arquivo Excel lido ({ext})")
        elif ext == ".csv":
            df = pd.read_csv(io.BytesIO(arquivo_bytes), dtype=str, sep=None, engine="python")
            ok("Arquivo CSV lido (separador detectado automaticamente)")
        else:
            erro(f"Formato '{ext}' não suportado. Use .xlsx ou .csv")
            return None, logs
    except Exception as e:
        erro(f"Erro ao ler arquivo: {e}")
        return None, logs

    inicial = df.shape
    info(f"Dataset inicial: {inicial[0]:,} linhas × {inicial[1]} colunas")

    # Passo 1 – Colunas
    colunas = ["NATURAL","CODMUNNATU","IDADE","SEXO","RACACOR","ESTCIV",
               "ESC2010","OCUP","CODMUNRES","LOCOCOR","CODMUNOCOR","CAUSABAS","STDONOVA"]
    ausentes = [c for c in colunas if c not in df.columns]
    colunas  = [c for c in colunas if c in df.columns]
    if ausentes: logs.append(("warn", f"Colunas não encontradas: {ausentes}"))
    df = df[colunas]
    ok(f"Passo 1 – {len(colunas)} colunas selecionadas")

    # Passo 2 – Filtro CIDs
    cids = (["C910","C911","C912","C913","C914","C915","C917","C919",
              "C920","C921","C922","C923","C924","C925","C927","C929"] +
            [f"C93{i}" for i in range(10)])
    antes = len(df)
    df["CAUSABAS"] = df["CAUSABAS"].astype(str).str.strip().str.upper()
    df = df[df["CAUSABAS"].isin(cids)]
    ok(f"Passo 2 – CIDs filtrados: {antes:,} → {len(df):,} linhas")

    if df.empty:
        erro("Nenhuma linha com CIDs C91/C92/C93 encontrada.")
        return None, logs

    # Passo 3 – Dropna
    antes = len(df)
    df = df.dropna()
    ok(f"Passo 3 – Valores ausentes removidos: {antes:,} → {len(df):,} linhas")

    # Passo 4 – SEXO
    df["SEXO"] = df["SEXO"].apply(convert_sexo)
    ok("Passo 4 – SEXO convertido")

    # Passo 5 – RACACOR
    df["RACACOR"] = df["RACACOR"].apply(convert_raca_cor)
    ok("Passo 5 – RACACOR convertida")

    # Passo 6 – ESTCIV
    df["ESTCIV"] = df["ESTCIV"].apply(convert_estciv)
    ok("Passo 6 – ESTCIV convertido")

    # Passo 7 – IDADE
    antes = len(df)
    df["IDADE"] = df["IDADE"].apply(converter_idade)
    df = df.dropna(subset=["IDADE"])
    ok(f"Passo 7 – IDADE convertida: {antes:,} → {len(df):,} linhas")

    # Passo 8 – ESC2010
    df["ESC2010"] = df["ESC2010"].apply(converter_escolaridade)
    ok("Passo 8 – ESC2010 convertida")

    # Passo 9 – UF
    mapa_uf = {
        "11":"RO","12":"AC","13":"AM","14":"RR","15":"PA","16":"AP","17":"TO",
        "21":"MA","22":"PI","23":"CE","24":"RN","25":"PB","26":"PE","27":"AL",
        "28":"SE","29":"BA","31":"MG","32":"ES","33":"RJ","35":"SP",
        "41":"PR","42":"SC","43":"RS","50":"MS","51":"MT","52":"GO","53":"DF",
    }
    df["NATURAL"]    = df["NATURAL"].astype(str).str.zfill(3)
    df["CODMUNOCOR"] = df["CODMUNOCOR"].astype(str).str.zfill(7)
    df["UF_NATURAL"] = df["NATURAL"].str[-2:].map(mapa_uf)
    df["UF_OCOR"]    = df["CODMUNOCOR"].str[1:3].map(mapa_uf)
    ok("Passo 9 – UF_NATURAL e UF_OCOR criadas")

    # Passo 10 – LOCOCOR
    mapa_loc = {"1":"Hospital","2":"Outro estabelecimento de saúde","3":"Domicílio",
                "4":"Via pública","5":"Outros","6":"Aldeia indígena","9":"Ignorado"}
    df["LOCOCOR_DESC"] = df["LOCOCOR"].astype(str).str.strip().map(mapa_loc)
    ok("Passo 10 – LOCOCOR_DESC criada")

    reducao = (1 - len(df) / inicial[0]) * 100
    info(f"Dataset final: {len(df):,} linhas × {df.shape[1]} colunas  |  redução: {reducao:.1f}%")

    return df, logs


def df_para_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dados Tratados")
    return buf.getvalue()


# ─── Interface ────────────────────────────────────────────────────────────────

st.markdown("""
<div class="header-block">
  <h1>🩸 SIM · Leucemia</h1>
  <p>Tratamento automatizado de dados de óbitos por leucemia (CIDs C91–C93) · SIM/DATASUS</p>
</div>
""", unsafe_allow_html=True)

# Sidebar – info

with st.sidebar:
    
    st.markdown("### Sobre")
    st.markdown("Processa arquivos `.xlsx` ou `.csv` do SIM/DATASUS aplicando:")
    st.markdown("""


- Seleção de colunas relevantes  
- Filtro por CIDs C91, C92, C93  
- Remoção de valores ausentes  
- Conversão de SEXO, RACACOR, ESTCIV  
- Conversão de IDADE para anos decimais  
- Conversão de ESC2010  
- Criação de UF_NATURAL e UF_OCOR  
- Descrição de LOCOCOR  
""")
    st.markdown('@reyso_ct')
    st.divider()
    st.caption("Desenvolvido com Python · Pandas · Streamlit")

# Upload
st.markdown("#### 📂 Carregar arquivo")
arquivo = st.file_uploader(
    "Arraste ou clique para selecionar",
    type=["xlsx", "xls", "csv"],
    label_visibility="collapsed",
)

if arquivo:
    st.markdown(f"**Arquivo:** `{arquivo.name}`  |  **Tamanho:** {arquivo.size / 1024:.1f} KB")
    st.divider()

    if st.button("⚙️  Processar dados"):
        with st.spinner("Processando..."):
            df_out, logs = tratar_dados(arquivo.read(), arquivo.name)

        # Log visual
        st.markdown("#### 📋 Log de processamento")
        icones = {"ok": "✅", "err": "❌", "warn": "⚠️", "info": "ℹ️"}
        classes = {"ok": "step-ok", "err": "step-err", "warn": "step-err", "info": "step-text"}
        html_steps = ""
        for tipo, msg in logs:
            html_steps += f"""
            <div class="step">
              <span class="step-icon">{icones.get(tipo,'·')}</span>
              <span class="{classes.get(tipo,'step-text')}">{msg}</span>
            </div>"""
        st.markdown(html_steps, unsafe_allow_html=True)

        if df_out is not None and not df_out.empty:
            st.divider()
            st.markdown("#### 👁️ Prévia dos dados tratados")
            st.dataframe(df_out.head(20), use_container_width=True)

            # Métricas
            n_linhas = len(df_out)
            n_colunas = df_out.shape[1]
            st.markdown(f"""
            <div class="metric-row">
              <div class="metric-card">
                <div class="label">Linhas</div>
                <div class="value">{n_linhas:,}</div>
                <div class="sub">registros no dataset final</div>
              </div>
              <div class="metric-card">
                <div class="label">Colunas</div>
                <div class="value">{n_colunas}</div>
                <div class="sub">variáveis disponíveis</div>
              </div>
              <div class="metric-card">
                <div class="label">CIDs</div>
                <div class="value">{df_out['CAUSABAS'].nunique()}</div>
                <div class="sub">CIDs únicos presentes</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            st.divider()
            st.markdown("#### ⬇️ Baixar resultado")
            excel_bytes = df_para_excel(df_out)
            st.download_button(
                label="⬇️  Baixar dados tratados (.xlsx)",
                data=excel_bytes,
                file_name="dados_leucemia_tratados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )