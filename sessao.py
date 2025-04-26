import pandas as pd
import streamlit as st
from load_functions import *

def inspect_and_convert(df, column_name, date_format='%d/%m/%Y', dayfirst=True):
    """
    Inspeciona uma coluna de DataFrame, identifica valores inválidos para conversão de data,
    e tenta converter os valores válidos.
    """
    invalid_rows = []
    for index, value in df[column_name].items():
        try:
            # Tenta converter o valor para datetime
            pd.to_datetime(value, dayfirst=dayfirst)
        except Exception as e:
            # Registra o índice e o valor que falhou
            invalid_rows.append((index, value, str(e)))
    
    if invalid_rows:
        print(f"Valores inválidos na coluna '{column_name}' do DataFrame:")
        for idx, val, err in invalid_rows:
            print(f"  Linha {idx}: '{val}' - Erro: {err}")
    else:
        print(f"Tudo certo na coluna '{column_name}' do DataFrame.")
    
    # Converte os valores válidos
    df[column_name] = pd.to_datetime(df[column_name], dayfirst=dayfirst, errors='coerce').dt.strftime(date_format)
    return df

df_proc_2012_2023 = request_data(st.secrets['xlsx']['consolidado_2012_2023'])
geral_2024 = request_data(st.secrets['xlsx']['consolidado_2024'])
# Aplicando a função em cada DataFrame
df_proc_2012_2023 = inspect_and_convert(df_proc_2012_2023, 'Data Criação')
geral_2024['LF 2024'] = inspect_and_convert(geral_2024['LF 2024'], 'Data Criação')
geral_2024['Diversos 2024'] = inspect_and_convert(geral_2024['Diversos 2024'], 'Data Criação')
geral_2024['Taxas 2024'] = inspect_and_convert(geral_2024['Taxas 2024'], 'Data Criação')
