"""
Webapp – Tratamento de Óbitos por Leucemia (SIM/DATASUS)
Execute com:  streamlit run app.py
"""

import io
import os
import gc
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

/* ───────── SIDEBAR BASE ───────── */
section[data-testid="stSidebar"] {
    background-color: #0d0d0d !important;
}

/* ───────── TEXTO ───────── */
section[data-testid="stSidebar"] * {
    color: #f9f9f7 !important;
}

/* ───────── INPUTS (CORREÇÃO REAL) ───────── */

/* Text input / number input / textarea */
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea {
    background-color: #1a1a1a !important;
    color: #ffffff !important;   /* ← FORÇA TEXTO BRANCO */
    -webkit-text-fill-color: #ffffff !important; /* ← resolve bug de “texto apagado” */
    border: 1px solid #3a3a3a !important;
    border-radius: 8px !important;
}

/* Placeholder */
section[data-testid="stSidebar"] input::placeholder,
section[data-testid="stSidebar"] textarea::placeholder {
    color: #888 !important;
    opacity: 1 !important;
}

/* SELECTBOX (BaseWeb) */
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background-color: #1a1a1a !important;
    color: #ffffff !important;
}

/* Texto dentro do select */
section[data-testid="stSidebar"] div[data-baseweb="select"] span {
    color: #ffffff !important;
}

/* Dropdown */
section[data-testid="stSidebar"] ul {
    background-color: #1a1a1a !important;
}

section[data-testid="stSidebar"] li {
    color: #ffffff !important;
}

section[data-testid="stSidebar"] li:hover {
    background-color: #2a2a2a !important;
}

/* ───────── NUMBER INPUT (+ / -) ───────── */

/* Container */
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] > div {
    background-color: #1a1a1a !important;
    border: 1px solid #3a3a3a !important;
    border-radius: 8px !important;
}

/* Campo interno */
section[data-testid="stSidebar"] input[type="number"] {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

/* Botões + e - (AGORA FUNCIONA) */
section[data-testid="stSidebar"] button {
    color: #ffffff !important;
    background-color: #2a2a2a !important;
    border-left: 1px solid #3a3a3a !important;
}

/* Hover nos botões */
section[data-testid="stSidebar"] button:hover {
    background-color: #e05c5c !important;
    color: #ffffff !important;
}

/* ───────── FOCUS BONITO ───────── */
section[data-testid="stSidebar"] input:focus,
section[data-testid="stSidebar"] textarea:focus,
section[data-testid="stSidebar"] div[data-baseweb="select"]:focus-within {
    border: 1px solid #e05c5c !important;
    box-shadow: 0 0 0 2px rgba(224,92,92,0.25) !important;
    outline: none !important;
}


/* Destaque para extensões (.csv, .xlsx) */
code {
    background: #1e1e1e !important;
    color: #f9f9f7 !important;
    padding: 2px 6px !important;
    border-radius: 6px !important;
    font-size: 0.85rem !important;
    border: 1px solid #f9f9f7 !important;
}
</style>
    
""", unsafe_allow_html=True)


# ─── Funções de conversão ─────────────────────────────────────────────────────

def convert_sexo(sexo):
    if sexo in (1, "1"): return "Masculino"
    if sexo in (2, "2"): return "Feminino"
    return sexo

def convert_raca_cor(raca):
    return {"1":"Branca","2":"Preta","3":"Amarela","4":"Parda","5":"Indigena"}.get(str(raca), raca)

def convert_estciv(estciv):
    if pd.isna(estciv): return np.nan
    try: return {1:"Solteiro",2:"Casado",3:"Viuvo",4:"Divorciado",5:"Uniao Estavel",9:"Ignorado"}.get(int(estciv), np.nan)
    except: return np.nan

def converter_idade(idade):
    if pd.isna(idade): return np.nan
    try:
        s = str(int(float(idade))).zfill(3)
        u, v = int(s[0]), int(s[1:])
    except: return np.nan
    return {1:v/(60*24*365),2:v/(24*365),3:v/12,4:v,5:100,9:np.nan}.get(u, np.nan)

def converter_escolaridade(valor):
    if pd.isna(valor): return np.nan
    try: return {0:"Sem escolaridade",1:"Fundamental I (1ª a 4ª série)",
                 2:"Fundamental II (5ª a 8ª série)",3:"Ensino Médio",
                 4:"Superior incompleto",5:"Superior completo",9:"Ignorado"}.get(int(float(valor)), np.nan)
    except: return np.nan


# ─── Constantes ───────────────────────────────────────────────────────────────

COLUNAS = ["NATURAL","CODMUNNATU","IDADE","SEXO","RACACOR","ESTCIV",
           "ESC2010","OCUP","CODMUNRES","LOCOCOR","CODMUNOCOR","CAUSABAS","STDONOVA"]

CIDS = (["C910","C911","C912","C913","C914","C915","C917","C919",
          "C920","C921","C922","C923","C924","C925","C927","C929"] +
        [f"C93{i}" for i in range(10)])

MAPA_UF = {
    "11":"RO","12":"AC","13":"AM","14":"RR","15":"PA","16":"AP","17":"TO",
    "21":"MA","22":"PI","23":"CE","24":"RN","25":"PB","26":"PE","27":"AL",
    "28":"SE","29":"BA","31":"MG","32":"ES","33":"RJ","35":"SP",
    "41":"PR","42":"SC","43":"RS","50":"MS","51":"MT","52":"GO","53":"DF",
}

MAPA_LOC = {"1":"Hospital","2":"Outro estabelecimento de saúde","3":"Domicílio",
            "4":"Via pública","5":"Outros","6":"Aldeia indígena","9":"Ignorado"}


# ─── Tratamento por chunk ─────────────────────────────────────────────────────

def tratar_chunk(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in COLUNAS if c in df.columns]
    df = df[cols].copy()

    df["CAUSABAS"] = df["CAUSABAS"].astype(str).str.strip().str.upper()
    df = df[df["CAUSABAS"].isin(CIDS)]
    if df.empty:
        return df

    df = df.dropna()
    df["SEXO"]    = df["SEXO"].apply(convert_sexo)
    df["RACACOR"] = df["RACACOR"].apply(convert_raca_cor)
    df["ESTCIV"]  = df["ESTCIV"].apply(convert_estciv)
    df["IDADE"]   = df["IDADE"].apply(converter_idade)
    df = df.dropna(subset=["IDADE"])
    df["ESC2010"] = df["ESC2010"].apply(converter_escolaridade)

    df["NATURAL"]    = df["NATURAL"].astype(str).str.zfill(3)
    df["CODMUNOCOR"] = df["CODMUNOCOR"].astype(str).str.zfill(7)
    df["UF_NATURAL"] = df["NATURAL"].str[-2:].map(MAPA_UF)
    df["UF_OCOR"]    = df["CODMUNOCOR"].str[1:3].map(MAPA_UF)
    df["LOCOCOR_DESC"] = df["LOCOCOR"].astype(str).str.strip().map(MAPA_LOC)

    return df


# ─── Pipeline principal ───────────────────────────────────────────────────────

def tratar_dados(arquivo_bytes: bytes, nome_arquivo: str, chunk_size: int = 100_000):
    logs = []
    ok   = lambda m: logs.append(("ok",   m))
    erro = lambda m: logs.append(("err",  m))
    info = lambda m: logs.append(("info", m))
    warn = lambda m: logs.append(("warn", m))

    ext        = os.path.splitext(nome_arquivo)[-1].lower()
    tam_mb     = len(arquivo_bytes) / (1024 ** 2)
    eh_grande  = tam_mb > 50

    info(f"Arquivo: {nome_arquivo}  ({tam_mb:.1f} MB)")

    # Salva em disco temporário para não duplicar na RAM
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp.write(arquivo_bytes)
    tmp.flush()
    tmp_path = tmp.name
    tmp.close()
    del arquivo_bytes
    gc.collect()

    linhas_inicial = 0
    chunks_processados = []

    try:
        # ── Excel ──────────────────────────────────────────────────────────────
        if ext in (".xlsx", ".xls"):
            if eh_grande:
                warn(f"Excel grande ({tam_mb:.0f} MB) — considere converter para CSV para melhor desempenho.")
            ok(f"Lendo Excel... ({tam_mb:.0f} MB)")
            df_raw = pd.read_excel(tmp_path, dtype=str)
            linhas_inicial = len(df_raw)
            info(f"Dataset inicial: {linhas_inicial:,} linhas × {df_raw.shape[1]} colunas")
            resultado = tratar_chunk(df_raw)
            del df_raw; gc.collect()
            chunks_processados.append(resultado)

        # ── CSV (com chunks para arquivos grandes) ────────────────────────────
        elif ext == ".csv":
            if eh_grande:
                info(f"Arquivo grande — processando em chunks de {chunk_size:,} linhas")
            n = 0
            for chunk in pd.read_csv(tmp_path, dtype=str, sep=None,
                                      engine="python", chunksize=chunk_size):
                linhas_inicial += len(chunk)
                resultado = tratar_chunk(chunk)
                if not resultado.empty:
                    chunks_processados.append(resultado)
                n += 1
                del chunk, resultado; gc.collect()
            ok(f"CSV lido em {n} chunk(s)  |  {linhas_inicial:,} linhas no total")

        else:
            erro(f"Formato '{ext}' não suportado.")
            return None, logs, 0

    except Exception as e:
        erro(f"Erro ao processar: {e}")
        return None, logs, linhas_inicial
    finally:
        os.unlink(tmp_path)

    if not chunks_processados:
        erro("Nenhuma linha com CIDs C91/C92/C93 encontrada.")
        return None, logs, linhas_inicial

    df_final = pd.concat(chunks_processados, ignore_index=True)
    del chunks_processados; gc.collect()

    reducao = (1 - len(df_final) / linhas_inicial) * 100 if linhas_inicial > 0 else 0
    ok("Passos 1–10 aplicados com sucesso")
    info(f"Dataset final: {len(df_final):,} linhas × {df_final.shape[1]} colunas  |  redução: {reducao:.1f}%")

    return df_final, logs, linhas_inicial


# ─── Exportação ───────────────────────────────────────────────────────────────

def df_para_csv(df):
    return df.to_csv(index=False).encode("utf-8")

def df_para_excel(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Dados Tratados")
    return buf.getvalue()


# ─── Interface ────────────────────────────────────────────────────────────────

st.markdown("""
<div class="header-block">
  <h1>🩸 SIM · Leucemia</h1>
  <p>Tratamento automatizado de dados de óbitos por leucemia (CIDs C91–C93) · SIM/DATASUS</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Sobre: ")
    st.markdown("Desenvolvido por @reyso_ct")
    st.markdown("""
Processa `.xlsx` ou `.csv` do SIM/DATASUS:
- Seleção de colunas relevantes
- Filtro por CIDs C91, C92, C93
- Remoção de valores ausentes
- Conversão de SEXO, RACACOR, ESTCIV
- Conversão de IDADE para anos decimais
- Conversão de ESC2010
- Criação de UF_NATURAL e UF_OCOR
- Descrição de LOCOCOR
""")
    st.divider()
    st.markdown("### ⚙️ Configuração")
    chunk_size = st.number_input(
        "Linhas por chunk (CSV grande)",
        min_value=5_000, max_value=500_000,
        value=100_000, step=10_000,
        help="Reduza se travar (pouca RAM). Aumente para processar mais rápido."
    )
    st.divider()
    st.caption("Python · Pandas · Streamlit")

st.markdown("#### 📂 Carregar arquivo")
st.caption("Suporta `.xlsx` e `.csv` · Arquivos grandes (>50 MB): prefira CSV, processa em chunks e consome menos memória")

arquivo = st.file_uploader(
    "Arraste ou clique para selecionar",
    type=["xlsx", "xls", "csv"],
    label_visibility="collapsed",
)

if arquivo:
    tam_mb = arquivo.size / (1024**2)
    st.markdown(f"**Arquivo:** `{arquivo.name}`  |  **Tamanho:** {tam_mb:.1f} MB")

    if tam_mb > 50 and arquivo.name.lower().endswith((".xlsx", ".xls")):
        st.warning("⚠️ Excel grande detectado. Se possível, salve como `.csv` — usa muito menos memória.")

    st.divider()

    if st.button("⚙️  Processar dados"):
        barra = st.progress(0, text="Lendo arquivo...")
        dados = arquivo.read()
        barra.progress(20, text="Processando...")

        df_out, logs, n_inicial = tratar_dados(dados, arquivo.name, int(chunk_size))

        barra.progress(95, text="Quase lá...")

        # Log visual
        st.markdown("#### 📋 Log de processamento")
        icones  = {"ok":"✅","err":"❌","warn":"⚠️","info":"ℹ️"}
        classes = {"ok":"step-ok","err":"step-err","warn":"step-err","info":"step-text"}
        html = "".join(
            f'<div class="step"><span class="step-icon">{icones.get(t,"·")}</span>'
            f'<span class="{classes.get(t,"step-text")}">{m}</span></div>'
            for t, m in logs
        )
        st.markdown(html, unsafe_allow_html=True)
        barra.progress(100, text="Concluído!")

        if df_out is not None and not df_out.empty:
            st.divider()
            st.markdown("#### 👁️ Prévia (20 primeiras linhas)")
            st.dataframe(df_out.head(20), use_container_width=True)

            n_lin = len(df_out)
            red   = (1 - n_lin / n_inicial) * 100 if n_inicial > 0 else 0

            st.markdown(f"""
            <div class="metric-row">
              <div class="metric-card">
                <div class="label">Linhas</div>
                <div class="value">{n_lin:,}</div>
                <div class="sub">registros no dataset final</div>
              </div>
              <div class="metric-card">
                <div class="label">Redução</div>
                <div class="value">{red:.1f}%</div>
                <div class="sub">de {n_inicial:,} linhas iniciais</div>
              </div>
              <div class="metric-card">
                <div class="label">CIDs únicos</div>
                <div class="value">{df_out['CAUSABAS'].nunique()}</div>
                <div class="sub">{df_out.shape[1]} colunas no total</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            st.divider()
            st.markdown("#### ⬇️ Baixar resultado")
            col1, col2 = st.columns(2)

            with col1:
                st.download_button(
                    label="⬇️  Baixar como CSV",
                    data=df_para_csv(df_out),
                    file_name="dados_leucemia_tratados.csv",
                    mime="text/csv",
                )
            with col2:
                if n_lin <= 500_000:
                    st.download_button(
                        label="⬇️  Baixar como Excel",
                        data=df_para_excel(df_out),
                        file_name="dados_leucemia_tratados.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                else:
                    st.info("Excel desabilitado para >500k linhas. Use o CSV.")