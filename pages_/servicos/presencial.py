import streamlit as st
import pandas as pd
from load_functions import *
import re

st.title("Processos Diversos", anchor=False)

# Função para verificar todas as colunas
def verificar_coluna_proc(df):
    df = df.fillna("")  
    # Verifica se há células vazias, nulas ou vazias em todas as colunas
    colunas_obrigatorias = ["Proc.", "Data Criação", "Divisão", "CPF / CNPJ", "Razão / Nome", "Tipo", "Valor", "Qtde"]
    for coluna in colunas_obrigatorias:
        if coluna not in df.columns:
            st.toast(f":red[**Erro: A coluna '{coluna}' não existe no DataFrame.**]")
            return False
        if df[coluna].isnull().any() or df[coluna].eq("").any():
            st.toast(f":red[**Erro: A coluna '{coluna}' contém células vazias ou nulas.**]")
            return False
    
    # Verifica se há valores duplicados
    if df["Proc."].duplicated().any():
        st.toast(":red[**Erro: A coluna 'Proc.' contém valores duplicados.**]")
        return False

    # Verifica o formato de 'Data Criação' (dd/mm/yyyy)
    if not df["Data Criação"].apply(lambda x: bool(re.match(r"^\d{2}/\d{2}/\d{4}$", x))).all():
        st.toast(":red[**Erro: A coluna 'Data Criação' deve estar no formato dd/mm/yyyy.**]")
        return False

    # Verifica o formato de 'CPF / CNPJ' (000.000.000-00 ou 00.000.000/0000-00)
    if not df["CPF / CNPJ"].apply(lambda x: bool(re.match(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$|^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$", x))).all():
        st.toast(":red[**Erro: A coluna 'CPF / CNPJ' deve estar no formato 000.000.000-00 (CPF) ou 00.000.000/0000-00 (CNPJ).**]")
        return False

    # Verifica o formato de 'Valor' (1,00 a 2000,99)
    if not df["Valor"].apply(lambda x: 0.00 <= float(x.replace(",", ".")) <= 2000.99).all():
        st.toast(":red[**Erro: A coluna 'Valor' deve estar no formato de número real entre 1,00 e 2000,99.**]")
        return False

    # Verifica o formato de 'Data Retorno' e 'Data Entrega' (dd/mm/yyyy ou vazias)
    colunas_data_opcionais = ["Data Retorno", "Data Entrega"]
    for coluna in colunas_data_opcionais:
        if coluna in df.columns:
            if not df[coluna].apply(lambda x: x == "" or bool(re.match(r"^\d{2}/\d{2}/\d{4}$", x))).all():
                st.toast(f":red[**Erro: A coluna '{coluna}' deve estar no formato dd/mm/yyyy ou vazia.")
                return False

    # Se todas as verificações passarem
    return True

c1, c2 = st.columns([0.5,1.5], vertical_alignment='bottom')
option = c1.selectbox(
    "**Base a ser exibida:**",
    ("Base 2025", "Base 2024"), index=None, placeholder="Escolha o ano..."
)


@st.cache_data(ttl=120, show_spinner="Carregando...")
def load_presencial(yyyy: str):
    if yyyy == '2025':   
        worksheet = get_worksheet(5, st.secrets['sh_keys']['geral_major'])
    elif yyyy == '2024':
        worksheet = get_worksheet(3, st.secrets['sh_keys']['geral_2024'])
    data = worksheet.get_all_records(numericise_ignore=['all'])
    df = pd.DataFrame(data)
    return df

df = pd.DataFrame()

# Verifica qual opção foi selecionada
if option == "Base 2025":
    df = load_presencial('2025')
elif option == "Base 2024":
    df = load_presencial('2024')


if not df.empty:
    df["Valor"] = df["Valor"].str.replace(",", ".")
    df = df.fillna("")

    df_edited = st.data_editor(
        df,
        column_config={
            "Data Criação": st.column_config.TextColumn(
                "Data Criação",
                validate=r"^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/2025$",
                required=True,
            ),
            "Data Retorno": st.column_config.TextColumn(
                "Data Retorno",
                validate=r"^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/2025$",
            ),
            "Data Entrega": st.column_config.TextColumn(
                "Data Entrega",
                validate=r"^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/2025$",
            ),
            "CPF / CNPJ": st.column_config.TextColumn(
                "CPF / CNPJ",
                help="Digite um CPF ou CNPJ válido.",
                validate=r"^\d{3}\.\d{3}\.\d{3}-\d{2}$|^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$",
                required=True,
            ),
            "Divisão": st.column_config.SelectboxColumn(
                "Divisão",
                help="Selecione uma Divisão",
                width="small",
                options=["DVSA", "DVSE", "DVSCEP", "DVSDM", "Visamb"],
                required=True,
            ),
            "Tipo": st.column_config.SelectboxColumn(
                "Tipo",
                help="Selecione uma Divisão",
                width="medium",
                options=['Aprovação de projeto (≤ 100m²)',
                        'Aprovação de projeto (≥ 101m² e ≤ 500m²)',
                        'Aprovação de projeto (> 500m²)',
                        'Autenticação (fechamento de livro)',
                        'Autenticação (abertura de livro)',
                        'Visto em receita',
                        'Outro'],
                required=True,
            ),
            "Valor": st.column_config.NumberColumn(
                "Valor",
                help="Valor do DAM",
                min_value=0.00,
                max_value=2000.00,
                step=0.01,
                format="R$ %.2f",
                required=True,
            ),
            "Qtde": st.column_config.NumberColumn(
                "Qtde",
                help="Quantos?",
                min_value=1,
                max_value=99,
                step=1,
                required=True,
            )
        },
        hide_index=True,
        num_rows="dynamic",
    )

    if st.button("Salvar Alterações"):

        df = df_edited.fillna("")  
        if verificar_coluna_proc(df):
            df["Valor"] = df["Valor"].str.replace(".", ",") 
            df_list = df.values.tolist()

            try:
                if option == "Base 2025":
                    ws = get_worksheet(5, st.secrets['sh_keys']['geral_major'])
                    ws.update("A2", df_list, raw=False)
                elif option == "Base 2024":
                    ws = get_worksheet(3, st.secrets['sh_keys']['geral_2024'])
                    ws.update("A2", df_list, raw=False)

            except Exception as e:
                st.toast(f":red[**{e}**]")
            else:
                st.toast(":green[**Dados atualizados com sucesso!**]")
                
        # else:
        #     print(":red[**Corrija os problemas antes de prosseguir.**]")