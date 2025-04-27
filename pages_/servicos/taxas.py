import streamlit as st
from webdriver_etax import selenium_generate_dam
import pandas as pd
from load_functions import *
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import re, time #, pyperclip
import datetime
# from st_copy_to_clipboard import st_copy_to_clipboard

st.header("Emissão de DAM", anchor=False)

if 'reload_tx_df' not in st.session_state:
    st.session_state.reload_tx_df = False 
    # declarar primeiro, e recarregar os outros bancos
    st.session_state.reload_div_df = True
    st.session_state.reload_lf_df = True

# recarregar os outros bancos
st.session_state.reload_div_df = True
st.session_state.reload_lf_df = True

@st.cache_data(ttl=300, show_spinner="Carregando o banco 'Taxas'...")
def load_df():
    worksheet = get_worksheet(0, st.secrets['sh_keys']['geral_major'])
    data = worksheet.get_all_records(numericise_ignore=['all'])
    df = pd.DataFrame(data)
    return df

    
if 'tx_df' not in st.session_state:
    tx_df_aux = load_df()
    st.session_state.tx_df = tx_df_aux[tx_df_aux["Validade"] != "Inválido"]
    st.session_state.tx_df = st.session_state.tx_df.reset_index(drop=True)
    st.session_state.tx_df['Data_Solicitacao_dt'] = pd.to_datetime(
        st.session_state.tx_df['Data Solicitação'],
        format='%d/%m/%y, %H:%M'
    )
    

if st.session_state.reload_tx_df:
    st.session_state.tx_df = None
    load_df.clear()
    df_div_aux = load_df()
    st.session_state.tx_df = df_div_aux[df_div_aux["Validade"] != "Inválido"]
    st.session_state.tx_df = st.session_state.tx_df.reset_index(drop=True)
    st.session_state.reload_tx_df = False

if 'checkbox_minhas_tx' not in st.session_state:
   st.session_state.checkbox_minhas_tx = False
   st.session_state.disable_checkbox_minhas_tx = True

if 'checkbox_nao_respondidas_tx' not in st.session_state:
    st.session_state.checkbox_nao_respondidas_tx = False
    st.session_state.disable_checkbox_nao_respondidas_tx = True


with st.expander("Registro de Solicitações", expanded=True):
    colx, coly = st.columns(2, vertical_alignment="top")
    with colx:

        col1, col2, col3 = st.columns([0.8,1,1.2], vertical_alignment="center", gap="small")

        # Inicializando o session_state se necessário
        if 'status_checker' not in st.session_state:
            st.session_state.status_checker = None
            st.session_state.index_status_tx = 0

        # Atualizando o índice com base no status_checker
        match st.session_state.status_checker:
            case 'Passivo':
                st.session_state.index_status_tx = 0
            case 'Deferido':
                st.session_state.index_status_tx = 1
            case 'Indeferido':
                st.session_state.index_status_tx = 2

        # Definindo as opções
        status_options = ['Passivo', 'Deferido', 'Indeferido']

        # Pegando valor default baseado no índice
        default_status = [status_options[st.session_state.index_status_tx]]

        # Filtro de Status usando PILLS
        with col3:
            status_selecionado_pills = st.pills(
                label="Filtro por Status:",
                options=status_options,
                selection_mode="single",
                default=default_status,
                key="status_selecionado_pills",
                help="Escolha o status do processo",
                label_visibility='collapsed'
            )

        # Atualiza o session_state.status_checker para refletir a escolha atual
        if status_selecionado_pills:
            st.session_state.status_checker = status_selecionado_pills[0]
        else:
            st.session_state.status_checker = None

        # Filtro de Tipo Processo (continuando o que você já tinha)
        tipo_processo_opcoes = st.session_state.tx_df['Tipo Processo'].unique()  # Valores únicos
        
        status_selecionado_tx = status_selecionado_pills

        if st.session_state.status_checker in ['Deferido', 'Indeferido']:
            st.session_state.disable_checkbox_minhas_tx = False
            st.session_state.disable_checkbox_nao_respondidas_tx = False

            st.session_state.checkbox_nao_respondidas_tx = True
            st.session_state.checkbox_minhas_tx = True
        else:
            st.session_state.disable_checkbox_minhas_tx = True
            st.session_state.disable_checkbox_nao_respondidas_tx = True

            st.session_state.checkbox_nao_respondidas_tx = False
            st.session_state.checkbox_minhas_tx = False


        # chk_somente_minhas = col3.checkbox("As minhas", value=st.session_state.checkbox_minhas_tx, disabled=st.session_state.disable_checkbox_minhas_tx, help="Mostrar somente as tratadas por mim")
        # chk_nao_respondidas = col4.checkbox("Não respondidas", value=st.session_state.checkbox_nao_respondidas_tx, disabled=st.session_state.disable_checkbox_nao_respondidas_tx)

        # Defina as opções disponíveis
        opcoes = ["As minhas", "Não respondidas"]

        # Determine as opções selecionadas com base no estado atual
        selecionadas = []
        if st.session_state.checkbox_minhas_tx:
            selecionadas.append("As minhas")
        if st.session_state.checkbox_nao_respondidas_tx:
            selecionadas.append("Não respondidas")

        # Exiba as pílulas para seleção múltipla
        with col2:
            selecionadas = st.pills(
                label="Filtros",
                options=opcoes,
                selection_mode="multi",
                default=selecionadas,
                key="filtros_pills",
                help="Selecione os filtros desejados",
                label_visibility='collapsed'
            )
        
        with col1:
            # limites para o picker
            today = datetime.date.today()
            next_year = today.year
            jan_1 = datetime.date(next_year, 1, 1)
            dec_31 = datetime.date(next_year, 12, 31)

            data_inicio, data_fim = st.date_input(
                "Intervalo de Datas",
                value=(jan_1, jan_1 + datetime.timedelta(days=6)),
                min_value=jan_1,
                max_value=dec_31,
                format="DD/MM/YYYY",
                label_visibility='collapsed'
            )


        # Atualize os estados com base nas seleções
        st.session_state.checkbox_minhas_tx = "As minhas" in selecionadas
        st.session_state.checkbox_nao_respondidas_tx = "Não respondidas" in selecionadas
        
        st.session_state.tx_df['Status'] = st.session_state.tx_df['Status'].replace("", "Passivo")



        # Filtrando os dados com base no status selecionado
        df_geral = st.session_state.tx_df[st.session_state.tx_df['Status'] == status_selecionado_tx] if status_selecionado_tx else st.session_state.tx_df

        if not df_geral.empty:
            data_min = df_geral['Data_Solicitacao_dt'].min().date()
            data_max = df_geral['Data_Solicitacao_dt'].max().date()
        else:
            # caso df_geral fique vazio, define defaults razoáveis
            hoje = datetime.date.today()
            data_min = data_max = hoje



        # Filtro: "As minhas"
        if "As minhas" in selecionadas:
            df_geral = df_geral[df_geral['Servidor'] == st.session_state.sessao_servidor]
        
        # Filtro: "Não respondidas"
        if "Não respondidas" in selecionadas:
            df_geral = df_geral[df_geral['Respondido'] == "Não"]
        
        if data_inicio and data_fim:
            print(f"data_inicio: {data_inicio}, data_fim: {data_fim}")
            # — filtro por data usando a coluna datetime
            df_geral = df_geral[
                (df_geral['Data_Solicitacao_dt'].dt.date >= data_inicio) &
                (df_geral['Data_Solicitacao_dt'].dt.date <= data_fim)
            ]


        # Selecionando as colunas desejadas
        tx_df_filtrado = df_geral.iloc[:, [0, 1, 7, 2]]

        # Configuração do AgGrid
        gb = GridOptionsBuilder.from_dataframe(tx_df_filtrado)
        
        gb.configure_default_column(
            cellStyle={'font-size': '15px'},
            resizable=True,  # Permite redimensionar as colunas
            filterable=False,
            sortable=False,
            groupable=False
        )

        gb.configure_column("Código Solicitação", minWidth=101, maxWidth=101, header_name="Cód.")
        gb.configure_column("Data Solicitação", minWidth=130, maxWidth=130, header_name="Data")
        gb.configure_column("CPF / CNPJ", minWidth=160, maxWidth=160, header_name="CPF / CNPJ")
        gb.configure_column("Tipo Processo", minWidth=290, maxWidth=290, header_name="Tipo Processo")
        gb.configure_selection('single')  # Permite a seleção de uma linha
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=5)  # Paginação automática

        # Configurar opções do grid
        grid_options = gb.build()
        grid_options["domLayout"] = "print"  # Redimensiona automaticamente o grid
        grid_options["suppressContextMenu"] = True
        grid_options["suppressMenu"] = True
        grid_options["pagination"] = True  # Ativa paginação no grid
        grid_options["paginationPageSizeSelector"] = False

        # Renderizando o AgGrid
        grid_response = AgGrid(
            tx_df_filtrado,
            height=230,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            theme='streamlit'
        )

    if 'option_index' not in st.session_state:
        st.session_state.option_index = None
        st.session_state.option_index_loader = False

    selected_row = grid_response.get('selected_rows', None)

        
    if not selected_row is None: 
        selected_index = df_geral.loc[df_geral['Código Solicitação'] == selected_row['Código Solicitação'].iloc[0]].index


    if 'aggrid_gc_col2' not in st.session_state:
        st.session_state.aggrid_gc_col2 = None
        st.session_state.clear_clicked = False

    with coly:
        col1, col2 = st.columns(2, vertical_alignment="bottom")

        # Definindo opções
        opcoes_filtro = ['Alfa', 'Beta', 'Gama', 'Delta']

        # Filtro 1 usando Pills
        with col1:
            teste1 = st.segmented_control(
                label="Ivory tower 1",
                options=opcoes_filtro,
                selection_mode="single",
                default=["Alfa"],
                disabled=True,
                key="teste1_pills"
            )

        # Filtro 2 usando Pills
        with col2:
            teste2 = st.segmented_control(
                label="Ivory tower 2",
                options=opcoes_filtro,
                selection_mode="single",
                default=["Beta"],
                disabled=True,
                key="teste2_pills"
            )
        merged_df = st.session_state.merged_df
        st.session_state.df_geral_2025 = load_df_2025()

        df_geral_2025 = st.session_state.df_geral_2025
        if not 'Index' in df_geral_2025.columns:
            df_geral_2025 = df_geral_2025.ffill()
            df_geral_2025['Index'] = range(len(df_geral_2025))
        
            # Verifica se há uma linha selecionada na tabela da col1
        if not selected_row is None:  # Verifica se existe uma linha selecionada
            selected_cpf_cnpj = selected_row['CPF / CNPJ']
            if not selected_cpf_cnpj is None:
                # Filtra o DataFrame para exibir somente linhas com o mesmo CPF / CNPJ
                filtered_merged_df = merged_df[merged_df["CPF / CNPJ"] == selected_cpf_cnpj.iloc[0]]
                filtered_geral_2025 = df_geral_2025[df_geral_2025['CPF / CNPJ'] == selected_cpf_cnpj.iloc[0]]


                allin_merged_df = pd.concat([filtered_geral_2025, filtered_merged_df], ignore_index=True)

            else:
                allin_merged_df = pd.DataFrame()  # Nenhuma linha será exibida se CPF / CNPJ não for encontrado
        else:
            allin_merged_df = pd.DataFrame()  # Nenhuma linha será exibida se nada for selecionado

        # Configuração da tabela AgGrid para col2
        
        if st.session_state.clear_clicked:
            st.session_state.aggrid_gc_col2 = pd.DataFrame()
            st.session_state.clear_clicked = False
        else:
            st.session_state.aggrid_gc_col2 = allin_merged_df.iloc[:, [0, 4, 8, 1, 10]] if not allin_merged_df.empty else pd.DataFrame(columns=["Protocolo", "Data Criação", "CPF / CNPJ", "Tipo Processo"])
            #st.session_state.aggrid_gc_col2["Data Criação"] = pd.to_datetime(st.session_state.aggrid_gc_col2["Data Criação"], format="%d/%m/%Y", errors="coerce")
            st.session_state.aggrid_gc_col2 = st.session_state.aggrid_gc_col2.copy() # fazer uma cópia do df evita o warning fdp
            st.session_state.aggrid_gc_col2["Data Criação"] = pd.to_datetime(
                st.session_state.aggrid_gc_col2["Data Criação"], 
                format="%d/%m/%Y", 
                errors="coerce"
            )    
            st.session_state.aggrid_gc_col2 = st.session_state.aggrid_gc_col2.sort_values(by="Data Criação", ascending=False)
            st.session_state.aggrid_gc_col2["Data Criação"] = st.session_state.aggrid_gc_col2["Data Criação"].dt.strftime("%d/%m/%Y")


    
        gc = GridOptionsBuilder.from_dataframe(st.session_state.aggrid_gc_col2)
        gc.configure_column("Index", hide=True)
        gc.configure_default_column(cellStyle={'font-size': '15px'})
        gc.configure_default_column(resizable=False, filterable=False, sortable=False, groupable=False)
        gc.configure_column("Protocolo", minWidth=101, maxWidth=101, header_name="Protocolo")
        gc.configure_column("Data Criação", minWidth=130, maxWidth=130, header_name="Data")
        gc.configure_column("CPF / CNPJ", minWidth=160, maxWidth=160, header_name="CPF / CNPJ")
        gc.configure_column("Tipo Processo", minWidth=290, maxWidth=290, header_name="Tipo Processo")
        gc.configure_selection('single')  # Permite a seleção de uma linha
        gc.configure_pagination(paginationAutoPageSize=False, paginationPageSize=5)
        gc.configure_grid_options(onCellClicked=True)

        # Configurar opções do grid
        grid_options_merged = gc.build()
        grid_options_merged["suppressContextMenu"] = True
        grid_options_merged["suppressMenu"] = True
        grid_options_merged["suppressRowClickSelection"] = False
        grid_options_merged["domLayout"] = "print"
        grid_options_merged["pagination"] = True
        grid_options_merged["paginationPageSizeSelector"] = False

        grid_response_merged = AgGrid(
            st.session_state.aggrid_gc_col2,
            height=230,
            gridOptions=grid_options_merged,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            theme='streamlit'                   
        )

if 'sel_merged_tx' not in st.session_state:
    st.session_state.sel_merged_tx = None
    st.session_state.sel_merged_tx_clear = False

st.session_state.sel_merged_tx = grid_response_merged.get('selected_rows', None)

# print(f"st.session_state.sel_merged_tx: {st.session_state.sel_merged_tx}")

def show_data():
    @st.dialog("Detalhes do Registro selecionado:", width="large")
    def aux_show_data():
        # selecionar o df de 2025
        if '2025' in str(st.session_state.sel_merged_tx['Data Criação']):
            selected_index_merged = df_geral_2025.loc[df_geral_2025.loc[:,'Index'] == st.session_state.sel_merged_tx['Index'].iloc[0]]
            selected_index_merged.loc[:, 'Valor'] = selected_index_merged['Valor'].map(
                lambda x: x if isinstance(x, str) and x.startswith('R$') else f'R$ {x:,.2f}' if isinstance(x, (int, float)) else 'R$ 0,00'
            )
        else:
            selected_index_merged = merged_df.loc[merged_df.loc[:,'Index'] == st.session_state.sel_merged_tx['Index'].iloc[0]]
            selected_index_merged.loc[:, 'Valor'] = selected_index_merged['Valor'].apply(
                lambda x: f'R$ {x:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')
            )           

        selected_index_merged.loc[:,'Data Criação'] = selected_index_merged['Data Criação']
        json_data = selected_index_merged.to_json(orient='records', lines=False)
        return st.json(json_data)
    aux_show_data()


if not st.session_state.sel_merged_tx is None and not st.session_state.sel_merged_tx_clear and not st.session_state.nao_execute_esta_merda:
    show_data()
 
    st.session_state.sel_merged_tx = None
    st.session_state.sel_merged_tx_clear = False
    
else:
    st.session_state.sel_merged_tx_clear = False
    st.session_state.nao_execute_esta_merda = False


#
#
# A MERDA DO SESSION STATE
#
#

if 'expander' not in st.session_state:
    st.session_state.expander = False

if 'empty_df' not in st.session_state: 
    selected_line = st.session_state.tx_df.iloc[1].copy()
    selected_line.iloc[:] = ""
    st.session_state.empty_df = selected_line.fillna("")
    treated_line = st.session_state.empty_df
else:
    treated_line = st.session_state.empty_df

if 'selected_index' not in st.session_state:
    st.session_state.selected_index = 0

if selected_row is not None and len(selected_row) > 0:
    st.session_state.expander = True
    st.session_state.selected_index = int(selected_index[0])
    selected_line = st.session_state.tx_df.iloc[st.session_state.selected_index]
    treated_line = selected_line.fillna("")
else:
    st.session_state.expander = False

if 'btn_clear' not in st.session_state:
    st.session_state.btn_clear = False
    st.session_state.disable_btn_edit = False
    st.session_state.disable_btn_save = False
    st.session_state.disable_btn_submit = False
    st.session_state.disable_btn_clear = False
    st.session_state.disable_btn_emitirDam = True

if st.session_state.btn_clear:
    treated_line = st.session_state.empty_df
    st.session_state.btn_clear = False

#
#
# A MERDA DO SESSION STATE
#
#

st.write("")


with st.expander("Detalhes da solicitação", expanded=st.session_state.expander):
    st.write("")
    with st.form("form_taxas", enter_to_submit=False, border=False, clear_on_submit=True):  
        container1, container2 = st.columns(2, gap="large")

        with container1:
            col1, col2, col3, col4 = st.columns([1.6, 0.6, 0.6, 0.2], vertical_alignment="bottom")
            tipo_processo = col1.text_input("Tipo Processo", value=treated_line["Tipo Processo"])
            codigo_solicitacao = col2.text_input("Cód. Solicitação", value=treated_line["Código Solicitação"])
            data_solicitacao = col3.text_input("Data Solicitação", value=treated_line["Data Solicitação"])
            match treated_line["Respondido"]:
                case "Sim":
                    col4.header(":material/check_circle:", anchor=False)
                    #col4.header("🟢", anchor=False)
                case "Não":
                    col4.header(":material/do_not_disturb_on:", anchor=False)
                    #col4.header("🔴", anchor=False)
                case _:
                    col4.header(":material/pending:", anchor=False)
                    # col4.header("⚪️", anchor=False)

            if not codigo_solicitacao:
                st.session_state.disable_btn_edit = True
                st.session_state.disable_btn_clear = True
                st.session_state.disable_btn_submit = True
                st.session_state.disable_btn_save = True
            else:
                st.session_state.disable_btn_edit = False
                st.session_state.disable_btn_clear = False
                st.session_state.disable_btn_submit = False
                st.session_state.disable_btn_save = False


            col1, col2, col3 = st.columns([1.3,1.4,0.3], vertical_alignment="bottom")
            complemento_1 = col1.text_input("Complemento Processo (1)", value=treated_line["Complemento Processo (1)"])
            complemento_3 = col2.text_input("Complemento Processo (3)", value=treated_line["Complemento Processo (3)"])
            
            if 'disable_btn_cnpj_tx' not in st.session_state:
                st.session_state.disable_btn_cnpj_tx = True

            if len(treated_line["CPF / CNPJ"]) == 18:
                st.session_state.disable_btn_cnpj_tx = False
            else:
                st.session_state.disable_btn_cnpj_tx = True

            btn_cnpj_tx = col3.form_submit_button(":material/search:", use_container_width=True,
                                                  disabled=st.session_state.disable_btn_cnpj_tx)

            if btn_cnpj_tx:
                get_cnpj(treated_line["CPF / CNPJ"], '', complemento_3)

            complemento_2 = st.text_area("Complemento Processo (4)", value=treated_line["Complemento Processo (4)"])

            col1, col2, col3, col4, col5 = st.columns([1.5, 0.9, 0.4, 1, 1], vertical_alignment="bottom")
            cpf_cnpj = col1.text_input("CPF / CNPJ", value=treated_line["CPF / CNPJ"])

            #validade_cpf_cnpj = col2.text_input("Validade", value=treated_line["Validade"])

            ocorrencias_solicitacao = col2.text_input("Ocorrências", value=treated_line["Ocorrências"])
            
            if 'disable_btn_ocorrencias' not in st.session_state:
                st.session_state.disable_btn_ocorrencias = True

            if treated_line["Ocorrências"] == "":
                st.session_state.disable_btn_ocorrencias = True
            else:
                st.session_state.disable_btn_ocorrencias = False
            
            btn_ocorrencias = col3.form_submit_button(":material/eye_tracking:", type="secondary",
                                                      use_container_width=True, disabled=st.session_state.disable_btn_ocorrencias)
            
            if btn_ocorrencias:
                get_ocorrencias(treated_line["CPF / CNPJ"], "taxas")
                btn_ocorrencias = False

            

            #col1, col2, col3, col4, col5 = st.columns(5, vertical_alignment="bottom")
            f_vmin = format_financial_values(treated_line["Valor Mínimo"])
            f_vmax = format_financial_values(treated_line["Valor Máximo"])
            f_vtotal = format_financial_values(treated_line["Valor Total"])

            if "R$" not in treated_line["Valor Manual"]:
                f_vmanual = format_financial_values(treated_line["Valor Manual"])
            else:
                f_vmanual = treated_line["Valor Manual"]
            
            # operador ternário
            valor_dam = f_vtotal if f_vtotal else f_vmanual

            complem_valor = col4.text_input("Complemento", value=treated_line["Complemento Valor"])
            valor_manual = col5.text_input("Valor do DAM *", value=valor_dam)


            if len(treated_line["CPF / CNPJ"]) == 14:
                nome_pf_para_webdriver = st.text_input("Nome da Pessoa Física *")

            # if validade_cpf_cnpj:
            #     st.error(f"O número {cpf_cnpj} é inválido. Não é possível continuar.")
            # elif not validade_cpf_cnpj and cpf_cnpj:
            #     hint_values = hint_financial_values(f_vmin, f_vmax, treated_line["Complemento Valor"])
            #     st.write(f"````{hint_values}````")
            
            
            if cpf_cnpj and treated_line["CPF / CNPJ"]:
                hint_values = hint_financial_values(f_vmin, f_vmax, treated_line["Complemento Valor"])
                st.write(f"````{hint_values}````")

            col1, col2 = st.columns(2, vertical_alignment="bottom")        
            col_btn = [col2, col1]
            col_index = 0
            cabecalho_url = ["Identidade", "Endereço", "CNPJ", "CISC", "Notificação", "Alvará SEFIN", "DAM"]
            for col in cabecalho_url:
                url = treated_line.get(col)
                if isinstance(url, str) and url.startswith("http"):  # Verifica se a célula tem um URL válido
                    with col_btn[col_index]:
                        col_btn[col_index].link_button(f" Abrir {col}", url, icon=":material/link:", use_container_width=True)
                    col_index = (col_index + 1) % 2
            
            # if validade_cpf_cnpj == '' and len(cpf_cnpj) == 18:
            #     # Depois faço a consulta do CNPJ, tenho que entregar o MVP.
            #     st.write("")
            # col1, col2 = st.columns(2, vertical_alignment="bottom")
            # email1 = col1.text_input("E-mail", value=treated_line["E-mail"])
            # email2 = col2.text_input("E-mail CC", value=treated_line["E-mail CC"])

            if len(cpf_cnpj) == 18:
                # Depois faço a consulta do CNPJ, tenho que entregar o MVP.
                st.write("")
            col1, col2 = st.columns(2, vertical_alignment="bottom")
            email1 = col1.text_input("E-mail", value=treated_line["E-mail"])
            email2 = col2.text_input("E-mail CC", value=treated_line["E-mail CC"])


        with container2:

            obs = st.text_area("Observação", value=treated_line["Observação"])
            col1, col2, col3, col4, col5 = st.columns([1.2, 1.1, 1, 0.9, 0.9], vertical_alignment="bottom")
            # status = col1.text_input("Status", value=treated_line["Status"])

            if not st.session_state.option_index_loader:
                match treated_line["Status"]:
                    case 'Passivo':
                        st.session_state.option_index = 1
                    case 'Deferido':
                        st.session_state.option_index = 2
                    case 'Indeferido':
                        st.session_state.option_index = 3
                    case _:
                        st.session_state.option_index = 0
                     
            status = col1.selectbox("Status *", ('', 'Passivo', 'Deferido', 'Indeferido'), index=st.session_state.option_index)
     
            servidor = col3.text_input("Servidor", value=treated_line["Servidor"])

            data_atendimento = col4.text_input("Data Atend.", value=treated_line["Data Atendimento"])
            data_modificacao = col5.text_input("Data Mod.", value=treated_line["Data Modificação"])

            if not data_atendimento:
                st.session_state.disable_btn_edit = True

            numero_dam = col2.text_input("Nº do DAM *", value=str(treated_line["Nº do DAM"]).replace(".0", ""))

            motivo_indeferimento = st.text_area("Justificativa do Indeferimento *", value=treated_line["Motivo Indeferimento"])
  
            comp_despacho = f"Cód: {treated_line["Código Solicitação"]} ~ {treated_line["Data Solicitação"]}; Tipo: {treated_line["Tipo Processo"]}"

            if treated_line["Complemento Processo (1)"]:
                comp_despacho += "; "+treated_line["Complemento Processo (1)"]
            if treated_line["Complemento Processo (2)"] and treated_line["Tipo Processo"] != 'Licença de Funcionamento':
                comp_despacho += "; "+treated_line["Complemento Processo (2)"]
            if treated_line["Complemento Processo (3)"]:
                comp_despacho += "; cnae(s) declarado(s) pelo solicitante: "+treated_line["Complemento Processo (3)"]

            if treated_line["Tipo Processo"] == 'Auto de Infração':
                comp_despacho += "; Referente ao processo _/20_, vinculado ao auto de infração nº 0_/20_. com a observação do art. 21 da lei federal 6.437/1977"
            
            comp_despacho = f"{comp_despacho}. No caso de vencimento, solicite novo DAM no site da Vigilância Sanitária. Consulta de boleto somente pelo site https://sefin.belem.pa.gov.br/servicos/2-via-consulta-de-dam-tributos-municipais-2/"

            st.write("")

            # Lista com os nomes dos botões para inicializar o estado de cada um
            btn_names = ['disable_btn_clear', 'disable_btn_edit', 'disable_btn_save', 'disable_btn_submit']

            for btn in btn_names:
                if btn not in st.session_state:
                    st.session_state[btn] = False

            col1, col2, col3, col4 = st.columns(4, vertical_alignment="bottom")
            col5, col6, col7, col8 = st.columns(4, vertical_alignment="bottom")

            if 'clicou_no_edit' not in st.session_state:
                st.session_state.clicou_no_edit = False 

            if codigo_solicitacao and treated_line["Código Solicitação"] and (treated_line["Status"] == 'Deferido' or treated_line["Status"] == 'Indeferido'):
                if st.session_state.clicou_no_edit:
                    # st.session_state.disable_btn_edit = False
                    st.session_state.disable_btn_save = False
                    st.session_state.clicou_no_edit = False
                else:
                    st.session_state.disable_btn_edit = False
                    st.session_state.disable_btn_save = True

            if treated_line["Status"] == "Deferido" or treated_line["Status"] == "Indeferido": # se no formulário for deferido ou indeferido, habilita o botão 'enviar'
                st.session_state.disable_btn_submit = False
            else:
                st.session_state.disable_btn_submit = True

            btn_emissao = col1.link_button("e-tax", "http://siat.belem.pa.gov.br:8081/acesso/login.jsf", use_container_width=True, disabled=False, icon=":material/public:")
            # btn_despacho = col2.form_submit_button("Copiar", use_container_width=True, icon=":material/content_paste:", disabled=True)
            
            btn_enviar_lote = col2.form_submit_button("Enviar Lote", use_container_width=True, icon=":material/stacked_email:", disabled=st.session_state.disable_btn_submit)

            match status_selecionado_tx:
                case 'Deferido' | 'Indeferido':
                    st.session_state.disable_btn_save = True
                    if st.session_state.auth_user == 'Daniel':
                        st.session_state.disable_btn_emitirDam = True
                case 'Passivo':
                    st.session_state.disable_btn_save = False
                    if st.session_state.auth_user == 'Daniel':
                        st.session_state.disable_btn_emitirDam = False
        
            btn_save = col3.form_submit_button("Salvar", use_container_width=True, disabled=st.session_state.disable_btn_save, icon=":material/save:", type='primary')
            btn_edit = col4.form_submit_button("Editar", use_container_width=True, disabled=st.session_state.disable_btn_edit, icon=":material/edit_note:")
            btn_clear = col7.form_submit_button("Limpar", use_container_width=True, disabled=st.session_state.disable_btn_clear, icon=":material/ink_eraser:")
            btn_submit = col8.form_submit_button("Enviar", use_container_width=True, disabled=st.session_state.disable_btn_submit, icon=":material/mail:", type='primary')
            bnt_emitirDam = col5.form_submit_button("Gerar DAM", use_container_width=True, disabled=st.session_state.disable_btn_emitirDam, icon=":material/fingerprint:")
                       
            
            if 'btn_dam' not in st.session_state:
                st.session_state.btn_dam = True
            
            if len(treated_line["Nº do DAM"]) > 10:
                st.session_state.btn_dam = False
            else:
                st.session_state.btn_dam = True

            # btn_dam = col5.link_button("DAM", f"http://siat.belem.pa.gov.br:8081/arrecadacao/pages/arrecadacao/guiaArrecadacaoDetalheExterno.jsf?id={treated_line["Nº do DAM"]}&op=4", use_container_width=True, disabled=st.session_state.btn_dam, icon=":material/attach_file:")
            btn_rerun = col6.form_submit_button("Reload", use_container_width=True, disabled=True, icon=":material/database:")
            
            # col1, col2 = st.columns(2, vertical_alignment="top")
            # with col1:
            #     st_copy_to_clipboard(comp_despacho)
            st.code(body=comp_despacho, line_numbers=1, language=None)

            if btn_rerun:
                load_df.clear()
                st.session_state.tx_df = load_df()
                st.rerun()

            #if btn_despacho:
               # st_copy_to_clipboard(comp_despacho)

            # Tentando trabalhar com alterações dinâmicas no streamlit. É algo parecido com tentar martelar prego com serrote... 
            if 'nao_execute_esta_merda' not in st.session_state:
                st.session_state.nao_execute_esta_merda = False

            if 'toast_registro_salvo' not in st.session_state:
                st.session_state.toast_registro_salvo = False
                st.session_state.status_salvo = None

            if st.session_state.toast_registro_salvo:
                st.toast(f"**:green[Despacho salvo com sucesso como '{st.session_state.status_salvo}]**")
                st. session_state.toast_registro_salvo = False
                st.session_state.status_salvo = None


            def btn_clear_fn(rerun=bool):
                st.session_state.nao_execute_esta_merda = True
                st.session_state.disable_btn_edit = False
                st.session_state.disable_btn_save = False          
                st.session_state.clear_clicked = True
                st.session_state.sel_merged_tx_clear = True
                
                if rerun:
                    st.session_state.btn_clear = True
                    st.session_state.reload_tx_df = True # recarregar a planilha para refletir as alterações
                    st.session_state.status_checker = status_selecionado_tx
                    st.rerun()

            if btn_clear:
                btn_clear_fn(rerun=True)


            # @st.dialog("_", width="small")
            # def confirmar_dam(codigo_solicitacao):
            #     st.write(f"Salvando em '{codigo_solicitacao}'. Aguarde...")

            # enviar email
            if 'is_email_sended_tx' not in st.session_state:
                st.session_state.is_email_sended_tx = False

                       
            def is_email_sended():
                worksheet = get_worksheet(0, st.secrets['sh_keys']['geral_major'])
                cell = worksheet.find(codigo_solicitacao, in_column=1)
                range_div = f"AH{cell.row}"
                value = "Sim"
                worksheet.update(range_div, value)
                st.session_state.load_tx_df = True
                st.session_state.is_email_sended_tx = False
                btn_clear_fn(rerun=True)

            def send_mail():
                if complemento_1:
                    comp_1 = f" ({complemento_1})"
                else:
                    comp_1 = ""

                email_taxas(
                    kw_status = status,
                    kw_protocolo = codigo_solicitacao,
                    kw_data_sol = data_solicitacao,
                    kw_tipo_proc = tipo_processo,
                    kw_complemento_1 = comp_1,
                    kw_cpf_cnpj = cpf_cnpj,
                    kw_numero_dam = numero_dam,
                    kw_email1 = email1,
                    kw_email2 = email2,
                    kw_motivo_indeferimento = motivo_indeferimento,
                    )

            def save_in_sheet(btn_edit: bool, dam_z: str, val_dam: str):
                # isso salva os dados de despacho, mas não gera data de resposta nem envia o e-mail.
                # a resposta ao usuário está salva no e-mail. A única coisa q vai p a planilha é o motivo indeferimento
                valor_dam_aux = valor_manual
                status_sel = status
                dam_num_sel = numero_dam
                
                if len(dam_z)>10:
                    valor_dam_aux = val_dam
                    dam_num_sel = dam_z
                    status_sel = 'Deferido'



                # if (((codigo_solicitacao and treated_line["Código Solicitação"] and status_sel != "" and status_sel != "Passivo") and 
                #         (re.fullmatch(r"-?\d+", dam_num_sel) and len(dam_num_sel) > 10) and
                #         (re.fullmatch(r"R\$ (\d{1,3}(\.\d{3})*|\d+),\d{2}", valor_dam_aux) and
                #         float(valor_dam_aux.replace('R$', '').replace('.', '').replace(',', '.').strip()) >= 0.01)) 
                #         or 
                #         (status_sel == "Indeferido" and motivo_indeferimento)):
                #         # Bloco de código para executar caso a condição seja atendida

                # Verificações auxiliares para legibilidade
                is_valid_codigo = codigo_solicitacao and treated_line.get("Código Solicitação")
                is_valid_status = status_sel and status_sel != "Passivo"
                is_valid_dam_num = re.fullmatch(r"-?\d+", dam_num_sel) and len(dam_num_sel) > 10
                # Tenta extrair e formatar o valor
                valor_formatado = extrair_e_formatar_real(valor_dam_aux)
                # Verifica se a extração foi bem-sucedida e se o valor é maior ou igual a 0.01
                is_valid_valor = valor_formatado != "" and \
                                float(valor_formatado.replace('R$', '').replace('.', '').replace(',', '.').strip()) >= 0.01
                is_indeferido = status_sel == "Indeferido" and motivo_indeferimento

                # Verificação final otimizada
                if (is_valid_codigo and is_valid_status and is_valid_dam_num and is_valid_valor) or is_indeferido:
                    # Executa a lógica necessária

                    if treated_line["Status"] == "Passivo":
                        # confirmar_dam(codigo_solicitacao)
                        st.toast(f"**Salvando a solicitação '{codigo_solicitacao}'. Aguarde...**")

                    if status_sel == "Indeferido":
                        valor_dam_aux = ''
                    elif status_sel == 'Deferido':
                        valor_dam_aux = valor_formatado
                    
                    despacho_dam = ""
                    
                    match status_sel:
                        case 'Passivo':
                            st.session_state.option_index = 1
                            despacho_dam = comp_despacho
                        case 'Deferido':
                            st.session_state.option_index = 2
                            despacho_dam = comp_despacho
                        case 'Indeferido':
                            st.session_state.option_index = 3
                        case _:
                            st.session_state.option_index = 0
                   
                    worksheet = get_worksheet(0, st.secrets['sh_keys']['geral_major'])
                    cell = worksheet.find(codigo_solicitacao, in_column=1)

                    if cell:
                        # Verifica a célula correspondente na coluna AC
                        col_ac_index = 29  # A coluna AC é a 29ª (1-indexada)
                        ac_value = worksheet.cell(cell.row, col_ac_index).value

                        if ac_value and not btn_edit:
                            st.toast(f"**:red[Erro. Esta solicitação já foi salva pelo usuário {ac_value}.]**")        
                        else:
                            if status_sel == 'Passivo':
                               st.toast(f"**:red[Não é possível retornar a solicitação para a caixa 'Passivo'.]**")
                            else:  
                                data_atendimento = worksheet.acell(f'AD{cell.row}').value
                                if not data_atendimento:
                                    data_atendimento = get_current_datetime()
                                
                                data_modificacao = get_current_datetime()
                                response = "Não"
                                
                                rangz=f"Y{cell.row}:AH{cell.row}"
                                values=[codigo_solicitacao, despacho_dam, valor_dam_aux, status_sel, st.session_state.sessao_servidor, data_atendimento, data_modificacao, motivo_indeferimento, dam_num_sel, response]
                                worksheet.update(rangz, [values])

                                st.session_state.option_index_loader = False # vai limpar o status persistente
                                st.session_state.nao_execute_esta_merda = True
                                st.session_state.disable_btn_edit = False
                                st.session_state.toast_registro_salvo = True
                                st.session_state.status_salvo = status_sel
                                st.session_state.load_tx_df = True # ativa o carregamento da base 2024.
                                st.session_state.registro_salvo = True
                                
                                # send_mail()                     
                                btn_clear_fn(rerun=True)
                    else:
                        st.toast(f"**:red[Registro não salvo. cell está vazia]**")

                else:
                    st.toast(":red[Preencha todos os campos obrigatórios.]")


            if 'registro_salvo' not in st.session_state:
                st.session_state.registro_salvo = False
            
            # if st.session_state.registro_salvo:
            #     st.toast(":green[Registro salvo com sucesso.]")
            #     st.session_state.registro_salvo = False

            if btn_edit:

                # st.session_state.nao_execute_esta_merda = True
                # st.session_state.disable_btn_edit = True
                # st.session_state.disable_btn_clear = False
                # st.session_state.clicou_no_edit = True
                # st.rerun()
                save_in_sheet(btn_edit=True, dam_z='0', val_dam=valor_dam)


            if 'btn_save' in locals() and btn_save:
                save_in_sheet(btn_edit=False, dam_z='0', val_dam=valor_manual)


            if btn_submit:
                st.toast(f"Tentando responder à {codigo_solicitacao}. Aguarde...")
                send_mail()
                if st.session_state.is_email_sended_tx:
                    is_email_sended()
                    st.session_state.is_email_sended_tx = False
            
#
#
# DAM CONSULTA DANIEL
#
# 
            def save_numero_dam(num_dam, valor_dam):
                if (int(num_dam) and len(num_dam) > 10):
                    st.toast("Salvando número do DAM...")
                    # worksheet = get_worksheet(0, st.secrets['sh_keys']['geral_major'])
                    # cell = worksheet.find(codigo_solicitacao, in_column=1)
                    # if cell:
                    #     rang1 = f"AG{cell.row}"
                    #     worksheet.update(rang1, num_dam)
                    save_in_sheet(btn_edit=False, dam_z=num_dam, val_dam=valor_dam)

                    # else:
                    #   st.toast(f":red[Erro no if cell.]")  
                else:
                    st.toast(f":red[Número do DAM inválido ({num_dam}).]")
            
            def load_driver_save(nome_pf):
                if valor_manual and comp_despacho:
                    list_usr = {
                        'cpf_cnpj': treated_line["CPF / CNPJ"],
                        'nome_pf': nome_pf,
                        'valor': valor_manual,
                        'despacho': comp_despacho,
                    }
                    
                    numero_dam_aut = selenium_generate_dam(list_usr)

                    if numero_dam_aut:
                        # treated_line["Nº do DAM"] = numero_dam_aut
                        # st.session_state.numero_dam = numero_dam_aut
                        save_numero_dam(numero_dam_aut, list_usr['valor'])
                    else:
                       st.toast(":red[Erro ao emitir o DAM.]") 
                else:
                    st.toast(":red[Preencha os campos obrigatórios para gerar o DAM.]")

########################
            if bnt_emitirDam and status_selecionado_tx == 'Passivo':
                nome_pf = ''
                match len(treated_line["CPF / CNPJ"]):    
                    case 14:
                        if len(nome_pf_para_webdriver) > 5:
                            nome_pf = nome_pf_para_webdriver.strip()
                            load_driver_save(nome_pf)
                        else:
                            st.toast(":red[Preencha o **nome da Pessoa Física**]")   
                    case 18:
                        load_driver_save(nome_pf)
                    case _:
                        st.toast(':red[Problema com len(treated_line["CPF / CNPJ"]]')

# st.write(st.session_state.tx_df)
# trix = st.session_state.tx_df
# print(trix.columns.values.tolist())



def batch_send_mail():
    st.toast("Verificando se há e-mail para responder...")
    worksheet = get_worksheet(0, st.secrets['sh_keys']['geral_major'])
    
    # Recupera todos os valores da planilha (lista de listas)
    data = worksheet.get_all_values()
    
    # Cria um DataFrame, considerando a primeira linha como cabeçalho
    df = pd.DataFrame(data[1:], columns=data[0])
    
    # Define a lista de colunas desejadas
    colunas_desejadas = [
        'Status', 'Código Protocolo', 'Data Solicitação', 'Tipo Processo', 
        'Complemento Processo (1)', 'CPF / CNPJ', 'Nº do DAM', 'E-mail', 
        'E-mail CC', 'Motivo Indeferimento', 'Respondido'
    ]
    
    # Seleciona somente as colunas desejadas
    df_subset = df[colunas_desejadas]
    
    # Filtra as linhas onde a coluna "Respondido" possui o valor "Não"
    df_filtered = df_subset[df_subset['Respondido'] == 'Não']
    
    # for index, row in df_filtered.iterrows():
    #     print(f"Linha {index + 1}: Status -> {row['Status']}")

    if df_filtered.empty:
        st.toast(":red[**Nenhum e-mail pendente para resposta.**]")
    else:

        total = 0
        enviados = 0
        erro = 0

        for index, row in df_filtered.iterrows():
            total += 1
            st.toast(f"Tentando responder à {total}ª solicitação, {row['Código Protocolo']}...")
            
            try:
                if complemento_1:
                    comp_1 = f" ({row['Complemento Processo (1)']})"
                else:
                    comp_1 = ""

                email_taxas(
                    kw_status = row['Status'],
                    kw_protocolo = row['Código Protocolo'],
                    kw_data_sol = row['Data Solicitação'],
                    kw_tipo_proc = row['Tipo Processo'],
                    kw_complemento_1 = comp_1,
                    kw_cpf_cnpj = row['CPF / CNPJ'],
                    kw_numero_dam = row['Nº do DAM'],
                    kw_email1 = row['E-mail'],
                    kw_email2 = row['E-mail CC'],
                    kw_motivo_indeferimento = row['Motivo Indeferimento'],
                    )
                
                time.sleep(2)
                
                cell = worksheet.find(row['Código Protocolo'], in_column=1)
                range_div = f"AH{cell.row}"
                value = "Sim"
                worksheet.update(range_div, value)
                
                enviados += 1

            except Exception as e:
                st.toast(f"Erro em {total}: {e}")
                erro += 1
            
            finally: # else executa se não tiver erro, finally executa tendo erro ou não
                time.sleep(5)
            
    st.toast(f"Automação finalizada. :blue[Total: **{total}**]; :green[Enviados: **{enviados}**]; :red[Erro: **{erro}**].")
    time.sleep(5)
    btn_clear_fn(rerun=True)
    print(f"Envio em lotes de taxa finalizado. Total: {total}; Enviados: {enviados}; Erro: {erro}.")
        
       
            

        

          



    
if btn_enviar_lote:
    batch_send_mail()
