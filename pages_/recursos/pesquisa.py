import streamlit as st
from load_functions import pd, load_df_2025

st.header("Consulta de Dados", anchor=False)

st.write("Use a lupa no canto superior direito da tabela para pesquisar.")

st.session_state.df_geral_2025 = load_df_2025()

all_df = pd.concat(
    [st.session_state.merged_df, st.session_state.df_geral_2025],
    ignore_index=True
)

# Remover linhas onde 'CPF / CNPJ' está vazio ou NaN
all_df = all_df.dropna(subset=['CPF / CNPJ'])  # Remove NaN
all_df = all_df[all_df['CPF / CNPJ'].astype(str).str.strip() != '']  # Remove strings vazias

# Remover a última coluna chamada 'Index', se existir
if 'Index' in all_df.columns:
    all_df = all_df.drop(columns=['Index'])

# Ordenar pelo índice do Pandas do maior para o menor número
all_df = all_df.sort_index(ascending=False)

with st.spinner("Aguarde..."):
    st.dataframe(
        all_df, 
        use_container_width=True,  # Opcional, para expandir na largura
        hide_index=True,  # Esconde o índice
    )