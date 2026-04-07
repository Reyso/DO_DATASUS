"""
conversores.py
Funções puras de conversão de variáveis do SIM/DATASUS.
"""

import numpy as np
import pandas as pd


def convert_sexo(sexo):
    if sexo in (1, "1"): return "Masculino"
    if sexo in (2, "2"): return "Feminino"
    return sexo


def convert_raca_cor(raca):
    return {"1":"Branca","2":"Preta","3":"Amarela","4":"Parda","5":"Indigena"}.get(str(raca), raca)


def convert_estciv(estciv):
    if pd.isna(estciv): return np.nan
    try:
        return {1:"Solteiro(a)",2:"Casado(a)",3:"Viuvo(a)",
                4:"Divorciado(a)",5:"Uniao Estavel",9:"Ignorado"}.get(int(estciv), np.nan)
    except: return np.nan


def converter_idade(idade):
    if pd.isna(idade): return np.nan
    try:
        s = str(int(float(idade))).zfill(3)
        u, v = int(s[0]), int(s[1:])
    except: return np.nan
    return {1:v/(60*24*365), 2:v/(24*365), 3:v/12, 4:v, 5:100, 9:np.nan}.get(u, np.nan)


def converter_escolaridade(valor):
    if pd.isna(valor): return np.nan
    try:
        return {0:"Sem escolaridade",
                1:"Fundamental I (1ª a 4ª série)",
                2:"Fundamental II (5ª a 8ª série)",
                3:"Ensino Médio",
                4:"Superior incompleto",
                5:"Superior completo",
                9:"Ignorado"}.get(int(float(valor)), np.nan)
    except: return np.nan


MAPA_UF = {
    "11":"RO","12":"AC","13":"AM","14":"RR","15":"PA","16":"AP","17":"TO",
    "21":"MA","22":"PI","23":"CE","24":"RN","25":"PB","26":"PE","27":"AL",
    "28":"SE","29":"BA","31":"MG","32":"ES","33":"RJ","35":"SP",
    "41":"PR","42":"SC","43":"RS","50":"MS","51":"MT","52":"GO","53":"DF",
}

MAPA_LOCOCOR = {
    "1":"Hospital",
    "2":"Outro estabelecimento de saúde",
    "3":"Domicílio",
    "4":"Via pública",
    "5":"Outros",
    "6":"Aldeia indígena",
    "9":"Ignorado",
}