import streamlit as st
import pandas as pd
from load_functions import get_worksheet
import plotly.express as px
import altair as alt

st.header("Gráficos e indicadores - Protocolo / Secretaria", anchor=False)

st.divider()


@st.cache_data(ttl=900, show_spinner="Aguarde...")
def load_dfs():
    w1 = get_worksheet(1, st.secrets['sh_keys']['relatorio'])
    w2 = get_worksheet(2, st.secrets['sh_keys']['relatorio'])
    w3 = get_worksheet(3, st.secrets['sh_keys']['relatorio'])

    da1 = w1.get("A1:F")
    da2 = w2.get("A1:F")
    da3 = w3.get("A1:F")

    df1 = pd.DataFrame(da1[1:], columns=da1[0])
    df2 = pd.DataFrame(da2[1:], columns=da2[0])
    df3 = pd.DataFrame(da3[1:], columns=da3[0])

    df = pd.concat([df1, df2, df3], ignore_index=True)
    df = df.dropna(how="all")

    df['Data Criação'] = pd.to_datetime(df['Data Criação'], format="%d/%m/%Y", errors='coerce')
    df = df.dropna(subset=['Data Criação'])
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
    df['Tipo Processo'] = df['Tipo Processo'].str.upper()

    return df

df = load_dfs()

c1, c2, c3, c4, c5, c6 = st.columns(6)
btn_limpar = c6.button('*Atualizar dados*', type='tertiary')
if btn_limpar:
    load_dfs.clear()
    st.rerun()

df_licenca = df[df['Tipo Processo'] == 'LICENÇA DE FUNCIONAMENTO']

st.subheader("1. Processos de LF (quantitativo e arrecadação)", anchor=False)
col1, col2 = st.columns(2, vertical_alignment='top')
# Widget para selecionar um ou mais anos
options = col1.multiselect(
    "Selecione pelo menos um ano:",
    [2021, 2022, 2023, 2024, 2025],
    default=2025,
    key='lf_ano',
    placeholder='Escolha um ano'
)

# Define as colunas para os widgets e para o gráfico
col1, col2 = st.columns(2, vertical_alignment='top')

with col1:
    @st.fragment
    def carregar_dados_lf(anos):
        if not anos:
            st.write("Selecione pelo menos um ano para exibir os dados.")
            return

        df_filtrado = df_licenca[df_licenca['Data Criação'].dt.year.isin(anos)].copy()
        df_filtrado['Ano'] = df_filtrado['Data Criação'].dt.year
        df_filtrado['Mês_Num'] = df_filtrado['Data Criação'].dt.month

        df_grouped = df_filtrado.groupby(['Ano', 'Mês_Num']).size().reset_index(name='Total Processos')

        mes_map = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
        df_grouped['Mês'] = df_grouped['Mês_Num'].map(mes_map)

        ordem_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        df_grouped['Mês'] = pd.Categorical(df_grouped['Mês'], categories=ordem_meses, ordered=True)

        ordered_years = sorted(df_grouped['Ano'].unique())
        n_years = len(ordered_years)
        
        # Define a largura das barras relativa ao número de anos
        bar_group_width = 0.8  # Largura total ocupada por todas as barras do mês (pode ser ajustado)
        bar_width_fraction = bar_group_width / max(n_years, 1)  # Evita divisão por zero

        def offset_func(ano):
            i = ordered_years.index(ano)
            return -((n_years - 1) / 2) * bar_width_fraction + i * bar_width_fraction

        df_grouped['offset'] = df_grouped['Ano'].apply(offset_func)
        df_grouped['x_bar'] = df_grouped['Mês'].cat.codes + 1 + df_grouped['offset']

        # Base do gráfico
        base = alt.Chart(df_grouped).encode(
            x=alt.X('x_bar:Q',
                    scale=alt.Scale(domain=[0.5, 12.5]),
                    axis=alt.Axis(
                        title='Mês',
                        tickMinStep=1,
                        values=list(range(1, 13)),
                        labelExpr=(
                            "{'1':'Jan','2':'Fev','3':'Mar','4':'Abr','5':'Mai','6':'Jun',"
                            "'7':'Jul','8':'Ago','9':'Set','10':'Out','11':'Nov','12':'Dez'}[datum.value]"
                        )
                    )),
            y=alt.Y('Total Processos:Q', title='Total Processos'),
            color=alt.Color('Ano:N', title='Ano')
        )

        # Define dinamicamente a espessura das barras com base no número de anos
        bars = base.mark_bar(size=bar_width_fraction * 50).encode(
            tooltip=['Mês', 'Ano', 'Total Processos']
        )

        text = base.mark_text(
            dy=-5, color='black'
        ).encode(
            text=alt.Text('Total Processos:Q', format=".0f")
        )

        chart = bars + text

        st.altair_chart(chart, use_container_width=True)

    carregar_dados_lf(options)

with col2:
    @st.fragment
    def carregar_dados_valor(anos):
        if not anos:
            st.write("Selecione pelo menos um ano para exibir os dados.")
            return

        # Filtra os dados para os anos selecionados e extrai Ano e Mês (numérico)
        df_filtrado = df_licenca[df_licenca['Data Criação'].dt.year.isin(anos)].copy()
        df_filtrado['Ano'] = df_filtrado['Data Criação'].dt.year
        df_filtrado['Mês_Num'] = df_filtrado['Data Criação'].dt.month

        # Agrupa por Ano e Mês, somando os valores na coluna 'Valor'
        df_grouped = df_filtrado.groupby(['Ano', 'Mês_Num'])['Valor'].sum().reset_index(name='Valor Total')

        # Função para abreviar os números
        def abbreviate_number(value):
            if value >= 1e6:
                val = value / 1e6
                if val.is_integer():
                    return f"{int(val)}M"
                else:
                    return f"{val:.1f}M".replace('.', ',')
            elif value >= 1e3:
                val = value / 1e3
                if val.is_integer():
                    return f"{int(val)}K"
                else:
                    return f"{val:.1f}K".replace('.', ',')
            else:
                return str(value)

        # Cria a coluna com o valor abreviado
        df_grouped['Valor_Abrev'] = df_grouped['Valor Total'].apply(abbreviate_number)

        # Mapeia o número do mês para a abreviação em português
        mes_map = {
            1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
        }
        df_grouped['Mês'] = df_grouped['Mês_Num'].map(mes_map)

        # Define a ordem correta dos meses e converte para variável categórica
        ordem_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        df_grouped['Mês'] = pd.Categorical(df_grouped['Mês'], categories=ordem_meses, ordered=True)

        # Cálculo do deslocamento para cada ano para exibir as barras lado a lado
        ordered_years = sorted(df_grouped['Ano'].unique())
        n_years = len(ordered_years)
        bar_group_width = 0.8  # percentual do espaço de cada mês a ser ocupado pelas barras
        bar_width_fraction = bar_group_width / max(n_years, 1)

        def offset_func(ano):
            i = ordered_years.index(ano)
            return -((n_years - 1) / 2) * bar_width_fraction + i * bar_width_fraction

        df_grouped['offset'] = df_grouped['Ano'].apply(offset_func)
        # Converte o mês (categórico) para seu código numérico (Jan=0, Fev=1, etc.) e soma 1 para que Jan seja 1
        df_grouped['x_bar'] = df_grouped['Mês'].cat.codes + 1 + df_grouped['offset']

        # Define a espessura das barras de forma relativa (o valor é um fator multiplicador)
        bar_thickness = bar_width_fraction * 50

        # Base do gráfico: define eixos e cores
        base = alt.Chart(df_grouped).encode(
            x=alt.X('x_bar:Q',
                    scale=alt.Scale(domain=[0.5, 12.5]),
                    axis=alt.Axis(
                        title='Mês',
                        tickMinStep=1,
                        values=list(range(1, 13)),
                        labelExpr=(
                            "{'1':'Jan','2':'Fev','3':'Mar','4':'Abr','5':'Mai','6':'Jun',"
                            "'7':'Jul','8':'Ago','9':'Set','10':'Out','11':'Nov','12':'Dez'}[datum.value]"
                        )
                    )),
            y=alt.Y('Valor Total:Q', title='Valor Total'),
            color=alt.Color('Ano:N', title='Ano')
        )

        # Gráfico de barras com a espessura definida
        bars = base.mark_bar(size=bar_thickness).encode(
            tooltip=['Mês', 'Ano', 'Valor Total']
        )

        # Sobrepõe rótulos com os valores abreviados sobre cada barra
        text = base.mark_text(
            dy=-5,
            color='black'
        ).encode(
            text=alt.Text('Valor_Abrev:N')
        )

        chart = bars + text

        st.altair_chart(chart, use_container_width=True)

    # Chama a função passando os anos selecionados
    carregar_dados_valor(options)


df_diversos = df[~(
    (df['Tipo Processo'] == 'LICENÇA DE FUNCIONAMENTO') | 
    (df['Tipo Processo'].str.contains('TAXA DE', na=False))
)]


st.subheader("2. Processos Diversos (quantitativo e arrecadação)", anchor=False)
col1, col2 = st.columns(2, vertical_alignment='top')
# Widget para selecionar um ou mais anos
options2 = col1.multiselect(
    "Selecione pelo menos um ano:",
    [2021, 2022, 2023, 2024, 2025],
    default=2025,
    key='diversos_ano',
    placeholder='Escolha um ano'
)

# Define as colunas para os widgets e para o gráfico
col1, col2 = st.columns(2, vertical_alignment='top')

with col1:
    @st.fragment
    def carregar_dados_diversos(anos):
        if not anos:
            st.write("Selecione pelo menos um ano para exibir os dados.")
            return
    
        df_filtrado = df_diversos[df_diversos['Data Criação'].dt.year.isin(anos)].copy()
        df_filtrado['Ano'] = df_filtrado['Data Criação'].dt.year
        df_filtrado['Mês_Num'] = df_filtrado['Data Criação'].dt.month

        df_grouped = df_filtrado.groupby(['Ano', 'Mês_Num']).size().reset_index(name='Total Processos')

        mes_map = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
        df_grouped['Mês'] = df_grouped['Mês_Num'].map(mes_map)

        ordem_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        df_grouped['Mês'] = pd.Categorical(df_grouped['Mês'], categories=ordem_meses, ordered=True)

        ordered_years = sorted(df_grouped['Ano'].unique())
        n_years = len(ordered_years)
        
        # Define a largura das barras relativa ao número de anos
        bar_group_width = 0.8  # Largura total ocupada por todas as barras do mês (pode ser ajustado)
        bar_width_fraction = bar_group_width / max(n_years, 1)  # Evita divisão por zero

        def offset_func(ano):
            i = ordered_years.index(ano)
            return -((n_years - 1) / 2) * bar_width_fraction + i * bar_width_fraction

        df_grouped['offset'] = df_grouped['Ano'].apply(offset_func)
        df_grouped['x_bar'] = df_grouped['Mês'].cat.codes + 1 + df_grouped['offset']

        # Base do gráfico
        base = alt.Chart(df_grouped).encode(
            x=alt.X('x_bar:Q',
                    scale=alt.Scale(domain=[0.5, 12.5]),
                    axis=alt.Axis(
                        title='Mês',
                        tickMinStep=1,
                        values=list(range(1, 13)),
                        labelExpr=(
                            "{'1':'Jan','2':'Fev','3':'Mar','4':'Abr','5':'Mai','6':'Jun',"
                            "'7':'Jul','8':'Ago','9':'Set','10':'Out','11':'Nov','12':'Dez'}[datum.value]"
                        )
                    )),
            y=alt.Y('Total Processos:Q', title='Total Processos'),
            color=alt.Color('Ano:N', title='Ano')
        )

        # Define dinamicamente a espessura das barras com base no número de anos
        bars = base.mark_bar(size=bar_width_fraction * 50).encode(
            tooltip=['Mês', 'Ano', 'Total Processos']
        )

        text = base.mark_text(
            dy=-5, color='black'
        ).encode(
            text=alt.Text('Total Processos:Q', format=".0f")
        )

        chart = bars + text

        st.altair_chart(chart, use_container_width=True, theme=None)
    
    carregar_dados_diversos(options2)

with col2:
    @st.fragment
    def carregar_dados_valor_diversos(anos):
        if not anos:
            st.write("Selecione pelo menos um ano para exibir os dados.")
            return

        # Filtra os dados para os anos selecionados e extrai Ano e Mês (numérico)
        df_filtrado = df_diversos[df_diversos['Data Criação'].dt.year.isin(anos)].copy()
        df_filtrado['Ano'] = df_filtrado['Data Criação'].dt.year
        df_filtrado['Mês_Num'] = df_filtrado['Data Criação'].dt.month

        # Agrupa por Ano e Mês, somando os valores na coluna 'Valor'
        df_grouped = df_filtrado.groupby(['Ano', 'Mês_Num'])['Valor'].sum().reset_index(name='Valor Total')

        # Função para abreviar os números
        def abbreviate_number(value):
            if value >= 1e6:
                val = value / 1e6
                if val.is_integer():
                    return f"{int(val)}M"
                else:
                    return f"{val:.1f}M".replace('.', ',')
            elif value >= 1e3:
                val = value / 1e3
                if val.is_integer():
                    return f"{int(val)}K"
                else:
                    return f"{val:.1f}K".replace('.', ',')
            else:
                return str(value)

        # Cria a coluna com o valor abreviado
        df_grouped['Valor_Abrev'] = df_grouped['Valor Total'].apply(abbreviate_number)

        # Mapeia o número do mês para a abreviação em português
        mes_map = {
            1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
        }
        df_grouped['Mês'] = df_grouped['Mês_Num'].map(mes_map)

        # Define a ordem correta dos meses e converte para variável categórica
        ordem_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        df_grouped['Mês'] = pd.Categorical(df_grouped['Mês'], categories=ordem_meses, ordered=True)

        # Cálculo do deslocamento para cada ano para exibir as barras lado a lado
        ordered_years = sorted(df_grouped['Ano'].unique())
        n_years = len(ordered_years)
        bar_group_width = 0.8  # percentual do espaço de cada mês a ser ocupado pelas barras
        bar_width_fraction = bar_group_width / max(n_years, 1)

        def offset_func(ano):
            i = ordered_years.index(ano)
            return -((n_years - 1) / 2) * bar_width_fraction + i * bar_width_fraction

        df_grouped['offset'] = df_grouped['Ano'].apply(offset_func)
        # Converte o mês (categórico) para seu código numérico (Jan=0, Fev=1, etc.) e soma 1 para que Jan seja 1
        df_grouped['x_bar'] = df_grouped['Mês'].cat.codes + 1 + df_grouped['offset']

        # Define a espessura das barras de forma relativa (o valor é um fator multiplicador)
        bar_thickness = bar_width_fraction * 50

        # Base do gráfico: define eixos e cores
        base = alt.Chart(df_grouped).encode(
            x=alt.X('x_bar:Q',
                    scale=alt.Scale(domain=[0.5, 12.5]),
                    axis=alt.Axis(
                        title='Mês',
                        tickMinStep=1,
                        values=list(range(1, 13)),
                        labelExpr=(
                            "{'1':'Jan','2':'Fev','3':'Mar','4':'Abr','5':'Mai','6':'Jun',"
                            "'7':'Jul','8':'Ago','9':'Set','10':'Out','11':'Nov','12':'Dez'}[datum.value]"
                        )
                    )),
            y=alt.Y('Valor Total:Q', title='Valor Total'),
            color=alt.Color('Ano:N', title='Ano')
        )

        # Gráfico de barras com a espessura definida
        bars = base.mark_bar(size=bar_thickness).encode(
            tooltip=['Mês', 'Ano', 'Valor Total']
        )

        # Sobrepõe rótulos com os valores abreviados sobre cada barra
        text = base.mark_text(
            dy=-5,
            color='black'
        ).encode(
            text=alt.Text('Valor_Abrev:N')
        )

        chart = bars + text

        st.altair_chart(chart, use_container_width=True, theme=None)

    # Chama a função passando os anos selecionados
    carregar_dados_valor_diversos(options2)
