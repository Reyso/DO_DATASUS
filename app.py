"""
app.py
Webapp Streamlit — Tratamento de Óbitos por Leucemia (SIM/DATASUS)
Execute com:  streamlit run app.py
"""

import io
import sys
import os
from datetime import datetime

# Garante que os módulos locais sejam encontrados
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import streamlit as st

from pipeline import executar_pipeline
from gerador_relatorio import gerar_pdf_profissional

# ─── Página ───────────────────────────────────────────────────────────────────
st.set_page_config(page_title="SIM · Leucemia", page_icon="🩸", layout="centered")

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

# ─── Helpers de exportação ────────────────────────────────────────────────────

def df_para_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def df_para_excel(df: pd.DataFrame) -> bytes:
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

# Sidebar
with st.sidebar:
    st.markdown("## Versão BETA/experimental")
    st.markdown("#### Os resultados podem conter erros. Compare com a sua base de dados original")
    st.markdown("## Desenvolvido por [@reyso_ct](https://www.instagram.com/reyso_ct/)")
    st.markdown("### Sobre: ")
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
- Relatório do processamento realizado
""")
    st.divider()
    st.markdown("### ⚙️ Configuração")
    chunk_size = st.number_input(
        "Linhas por chunk (CSV grande)",
        min_value=10_000, max_value=500_000, value=100_000, step=10_000,
        help="Reduza se travar (pouca RAM). Aumente para processar mais rápido.",
    )
    st.divider()
    st.caption("Python · Pandas · Streamlit")

# Upload
st.markdown("#### 📂 Carregar arquivo")
st.caption("Suporta `.xlsx` e `.csv` · Arquivos grandes (>50 MB): prefira CSV")

# Instrução sobre conversão de DBF
st.info("""
**📌 Se seus dados são em formato DBF (arquivo .dbf):**
1. Abra o arquivo no Microsoft Excel
2. Clique em **"Arquivo → Salvar como"**
3. Escolha o formato: **"CSV (separado por vírgulas)"** ou **"UTF-8"**
4. Salve o arquivo e faça upload aqui

Essa conversão garante compatibilidade e melhor processamento!
""")

arquivo = st.file_uploader(
    "Arraste ou clique para selecionar",
    type=["xlsx", "xls", "csv"],
    label_visibility="collapsed",
)

if arquivo:
    tam_mb = arquivo.size / (1024**2)
    st.markdown(f"**Arquivo:** `{arquivo.name}`  |  **Tamanho:** {tam_mb:.1f} MB")

    if tam_mb > 50 and arquivo.name.lower().endswith((".xlsx", ".xls")):
        st.warning("⚠️ Excel grande detectado. Prefira salvar como `.csv` para melhor desempenho.")

    st.divider()

    if st.button("⚙️  Processar dados"):
        barra = st.progress(0, text="Lendo arquivo…")
        dados_bytes = arquivo.read()
        barra.progress(20, text="Processando dados…")

        resultado = executar_pipeline(dados_bytes, arquivo.name, int(chunk_size))

        barra.progress(90, text="Finalizando…")

        df_out   = resultado["df"]
        logs     = resultado["logs"]
        metricas = resultado["metricas"]

        # ── Log visual ────────────────────────────────────────────────────────
        st.markdown("#### 📋 Log de processamento")
        icones  = {"ok":"✅","err":"❌","warn":"⚠️","info":"ℹ️"}
        classes = {"ok":"step-ok","err":"step-err","warn":"step-err","info":"step-text"}
        html = "".join(
            f'<div class="step">'
            f'<span class="step-icon">{icones.get(t,"·")}</span>'
            f'<span class="{classes.get(t,"step-text")}">{m}</span>'
            f'</div>'
            for t, m in logs
        )
        st.markdown(html, unsafe_allow_html=True)
        barra.progress(100, text="Concluído!")

        if df_out is not None and not df_out.empty:
            st.divider()

            # ── Prévia ────────────────────────────────────────────────────────
            st.markdown("#### 👁️ Prévia (20 primeiras linhas)")
            st.dataframe(df_out.head(20), width='stretch')

            # ── Métricas ──────────────────────────────────────────────────────
            n_lin = metricas["linhas_final"]
            red   = metricas["reducao_pct"]
            n_ini = metricas["linhas_inicial"]

            st.markdown(f"""
            <div class="metric-row">
              <div class="metric-card">
                <div class="label">Registros finais</div>
                <div class="value">{n_lin:,}</div>
                <div class="sub">de {n_ini:,} originais</div>
              </div>
              <div class="metric-card">
                <div class="label">Redução</div>
                <div class="value">{red}%</div>
                <div class="sub">registros removidos</div>
              </div>
              <div class="metric-card">
                <div class="label">CIDs únicos</div>
                <div class="value">{len(metricas["cids_encontrados"])}</div>
                <div class="sub">{metricas["colunas_final"]} colunas no total</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            st.divider()

            # ── Downloads ─────────────────────────────────────────────────────
            st.markdown("#### ⬇️ Baixar resultados")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.download_button(
                    label="⬇️  CSV",
                    data=df_para_csv(df_out),
                    file_name="dados_leucemia_tratados.csv",
                    mime="text/csv",
                    help="Formato leve, recomendado para arquivos grandes",
                )

            with col2:
                if n_lin <= 500_000:
                    st.download_button(
                        label="⬇️  Excel (.xlsx)",
                        data=df_para_excel(df_out),
                        file_name="dados_leucemia_tratados.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        help="Formato Excel — disponível apenas para até 500k linhas",
                    )
                else:
                    st.info("Excel indisponível para >500k linhas. Use CSV.")

            with col3:
                with st.spinner("Gerando PDF…"):
                    metricas["data_processamento"] = datetime.now().strftime("%d/%m/%Y às %H:%M")
                    pdf_bytes = gerar_pdf_profissional(metricas)

                if pdf_bytes:
                    st.download_button(
                        label="📄 Relatório em PDF",
                        data=pdf_bytes,
                        file_name="relatorio_tratamento_dados.pdf",
                        mime="application/pdf",
                    )
                else:
                    st.error("❌ Erro ao gerar PDF")