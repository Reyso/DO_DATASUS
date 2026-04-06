from tratamento_obitos_leucemia import tratar_obitos_leucemia
import pandas as pd



# df = pd.read_csv("F:\DS\dobr2015.csv", encoding="latin1", low_memory=False)
# basepath = "F:\DS\dobr2015.csv"
# df_limpo = tratar_obitos_leucemia(basepath)
# Opção 1 — r"" (recomendado)
basepath = r"F:\DS\DOBR2016.xlsx"
df_limpo = tratar_obitos_leucemia(basepath)

# ✅ Verifica antes de salvar
if df_limpo is not None:
    df_limpo.to_excel(r"F:\DS\obitos_leucemia_tratados.xlsx", index=False)
    print("✅ Arquivo salvo com sucesso!")
else:
    print("❌ O tratamento falhou. Verifique os logs acima.")