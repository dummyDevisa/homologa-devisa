import streamlit as st
import re, pandas as pd
from load_functions import get_worksheet, convert_sh_df
import numpy as np

@st.cache_data(ttl=120, show_spinner="Aguarde...")
def load_report():
    worksheet = get_worksheet(0, st.secrets['sh_keys']['relatorio'])
    data = worksheet.get('B1:F5')
    df = pd.DataFrame(data[1:], columns=data[0]).astype(str)
    return df

def return_float(texto):
    apenas_numeros = re.sub(r'[^0-9,]', '', texto)
    return apenas_numeros.replace(',', '.')

def formatar_percentual(valor, total):
    return f"{(float(valor)/float(total) * 100):.2f}".replace('.', ',')

sh_relatorio = load_report()
# st.write(sh_relatorio)

st.header("Panorama processos", anchor=False)

a, b, c = st.columns(3)
d, e, f = st.columns(3)
g, h, i = st.columns(3)

valor_total = return_float(sh_relatorio['Arrecadação'].iloc[0])
valor_licenca = return_float(sh_relatorio['Arrecadação'].iloc[1])
valor_diversos = return_float(sh_relatorio['Arrecadação'].iloc[2])

perc_licenciamento = formatar_percentual(valor_licenca, valor_total)
perc_diversos = formatar_percentual(valor_diversos, valor_total)

passivo_licenca = sh_relatorio['Passivo'].iloc[1]
passivo_diversos = sh_relatorio['Passivo'].iloc[2]
passivo_taxas = sh_relatorio['Passivo'].iloc[0]



delta_licenca = ''
delta_diversos = ''
delta_taxas = ''

if passivo_licenca == '0':
    delta_licenca = 'off'
else:
    delta_licenca = 'normal'

if passivo_diversos == '0':
    delta_diversos = 'off'
else:
    delta_diversos = 'normal'

if passivo_taxas == '0':
    delta_taxas = 'off'
else:
    delta_taxas = 'normal'

percind_dam = formatar_percentual(sh_relatorio['Indeferido'].iloc[0], (float(sh_relatorio['Deferido'].iloc[0])+float(sh_relatorio['Indeferido'].iloc[0])))
percind_licenca = formatar_percentual(sh_relatorio['Indeferido'].iloc[1], (float(sh_relatorio['Deferido'].iloc[1])+float(sh_relatorio['Indeferido'].iloc[1])))
percind_diversos = formatar_percentual(sh_relatorio['Indeferido'].iloc[2], (float(sh_relatorio['Deferido'].iloc[2])+float(sh_relatorio['Indeferido'].iloc[2])))
percind_lfs = formatar_percentual(sh_relatorio['Total'].iloc[3], (float(sh_relatorio['Deferido'].iloc[1])))

match st.session_state.privilege:
    case 'adm'| 'normal' | 'secretario':
        a.metric("Solicitações de DAMs", f"{sh_relatorio['Arrecadação'].iloc[0]} ~ (100%)", f"{passivo_taxas} ~ passivo", border=True, delta_color=delta_taxas)
        b.metric("Solicitações de Licenciamento", f"{sh_relatorio['Arrecadação'].iloc[1]} ({perc_licenciamento}%)", f"{passivo_licenca} ~ passivo", border=True, delta_color=delta_licenca)
        c.metric("Outros tipos de Processos", f"{sh_relatorio['Arrecadação'].iloc[2]} ({perc_diversos}%)", f"{passivo_diversos} ~ passivo", border=True, delta_color=delta_diversos)

        d.metric("Solicitações de DAMs", f"{sh_relatorio['Deferido'].iloc[0]} DAMs emitidos", f"-{sh_relatorio['Indeferido'].iloc[0]} ~ solicitações indeferidas ({percind_dam}%)", border=True)
        e.metric("Solicitações de Licenciamento", f"{sh_relatorio['Deferido'].iloc[1]} processos abertos", f"-{sh_relatorio['Indeferido'].iloc[1]} ~ solicitações indeferidas ({percind_licenca}%)", border=True)
        f.metric("Outros tipos de Processos", f"{sh_relatorio['Deferido'].iloc[2]} processos abertos", f"-{sh_relatorio['Indeferido'].iloc[2]} ~ solicitações indeferidas ({percind_diversos}%)", border=True)

        g.metric("Licenças Emitidas", f"{sh_relatorio['Total'].iloc[3]} Licenças Geradas", f"+{percind_lfs}% do total de processos", border=True, delta_color='off')
    case _:
        a.metric("Documento de Arrecadação Municipal", f"{sh_relatorio['Deferido'].iloc[0]} DAMs emitidos", f"-{percind_dam}% das solicitações foram indeferidas", border=True, delta_color='off')
        b.metric("Licença de Funcionamento", f"{sh_relatorio['Deferido'].iloc[1]} processos abertos", f"-{percind_licenca}% das solicitações foram indeferidas", border=True, delta_color='off')
        c.metric("Processos Diversos", f"{sh_relatorio['Deferido'].iloc[2]} processos abertos", f"-{percind_diversos}% das solicitações foram indeferidas", border=True, delta_color='off')
        d.metric("Licenças Emitidas", f"{sh_relatorio['Total'].iloc[3]} Licenças Geradas", f"+{percind_lfs}% do total de processos", border=True, delta_color='off')

# if st.session_state.sessao_servidor == 'Daniel':
#     # st.subheader("Produtividade", anchor=False)
#     # c1, c2, c3 = st.columns(3, gap='small', )
#     # chart_data = pd.DataFrame(np.random.randn(20, 3), columns=["DAM", "Licenciamento", "Diversos"])
#     # c2.bar_chart(chart_data)
    
#     def load_geral_2024():
#         sh_2024 = get_worksheet(2, st.secrets['sh_keys']['geral_2024_v2'])
#         # df_2024 = sh_2024.get_all_records(numericise_ignore=['all'])
#         # df = pd.DataFrame(df_2024)
#         df_2024c = convert_sh_df(sh_2024)
#         return df_2024c
    
#     vai_la = load_geral_2024()
    
#     df_filtrado = vai_la[['Data Solicitação', 'Data Emissão LF']].copy()
#         # Converter para datetime (se necessário)
#     df_filtrado['Data Solicitação'] = pd.to_datetime(df_filtrado['Data Solicitação'], format='%d/%m/%Y')
#     df_filtrado['Data Emissão LF'] = pd.to_datetime(df_filtrado['Data Emissão LF'], format='%d/%m/%Y')

#     # Calcular diferença em dias
#     df_filtrado['Dias_Entrega'] = (df_filtrado['Data Emissão LF'] - df_filtrado['Data Solicitação']).dt.days

#     # Calcular média (ignorando valores negativos ou NaN)
#     media_dias = df_filtrado['Dias_Entrega'].mean()

#     # Exibir no Streamlit
#     st.metric(
#         label="Tempo Médio de Entrega",
#         value=f"{media_dias:.0f} dias",
#         delta=f"{df_filtrado['Dias_Entrega'].std():.0f} dias (desvio padrão)"
#     )