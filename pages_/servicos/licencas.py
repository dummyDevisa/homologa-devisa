import streamlit as st
import pandas as pd
from load_functions import *
from webdriver_gdoc import *
# from streamlit_gsheets import GSheetsConnection
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import json, gspread

st.header("Licença de Funcionamento", anchor=False)

if 'reload_lf_df' not in st.session_state:
    st.session_state.reload_lf_df = False
    # declarar primeiro, e recarregar os outros bancos
    st.session_state.reload_div_df = True
    st.session_state.reload_tx_df = True

# recarregar os outros bancos
st.session_state.reload_div_df = True
st.session_state.reload_tx_df = True

@st.cache_data(ttl=300, show_spinner="Carregando banco de LFs...")
def load_lf_df():   
    worksheet = get_worksheet(2, st.secrets['sh_keys']['geral_major'])
    data = worksheet.get_all_records(numericise_ignore=['all'])
    df = pd.DataFrame(data)
    return df

if 'lf_df' not in st.session_state:
    lf_df_aux = load_lf_df()
    st.session_state.lf_df = lf_df_aux[lf_df_aux["Validade"] != "Inválido"]
    st.session_state.lf_df = st.session_state.lf_df.reset_index(drop=True)

if st.session_state.reload_lf_df:
    st.session_state.lf_df = None
    load_lf_df.clear()
    df_lf_aux = load_lf_df()
    st.session_state.lf_df = df_lf_aux[df_lf_aux["Validade"] != "Inválido"]
    st.session_state.lf_df = st.session_state.lf_df.reset_index(drop=True)
    st.session_state.reload_lf_df = False

if 'checkbox_minhas_lf' not in st.session_state:
   st.session_state.checkbox_minhas_lf = False
   st.session_state.disable_checkbox_minhas_lf = True

if 'checkbox_nao_respondidas_lf' not in st.session_state:
    st.session_state.checkbox_nao_respondidas_lf = False
    st.session_state.disable_checkbox_nao_respondidas_lf = True

with st.expander("Registro de Solicitações", expanded=True):

    colx, coly = st.columns(2, vertical_alignment="top")

    if 'status_checker_lf' not in st.session_state:
        status_checker_lf = None
        index_status_lf = 0

    match status_checker_lf:
        case 'Passivo':
            index_status_lf = 0
        case 'Deferido':
            index_status_lf = 1
        case 'Indeferido':
            index_status_lf = 2

    with colx:
        # Layout de colunas
        # col1, col2, col3 = st.columns(3, vertical_alignment="bottom")
        col1, col2 = st.columns(2, vertical_alignment="bottom")

        # Inicializa estado para filtro de Status (licenças finais)
        if 'status_checker_lf' not in st.session_state:
            status_checker_lf = 'Passivo'
            index_status_lf = 0

        # Atualiza índice com base no status anterior
        match status_checker_lf:
            case 'Passivo':
                index_status_lf = 0
            case 'Deferido':
                index_status_lf = 1
            case 'Indeferido':
                index_status_lf = 2

        # Opções de Status e default list para pills
        status_options = ['Passivo', 'Deferido', 'Indeferido']
        default_status_list = [status_options[index_status_lf]]

        # Pill de Status
        with col1:
            selected_status_list = st.pills(
                label="Status:",
                options=status_options,
                selection_mode="single",
                default=default_status_list,
                key="status_lf_pills",
                help="Selecione o status do processo"
            )
        # Atualiza session_state apenas se houver mudança
        if selected_status_list and selected_status_list[0] != status_checker_lf:
            status_checker_lf = selected_status_list

        # Pill de Tipo de Processo (desabilitado)
        # tipo_options = st.session_state.lf_df['Tipo Processo'].unique().tolist()
        # default_tipo_list = [tipo_options[1]] if len(tipo_options) > 1 else [tipo_options[0]]
        # with col2:
        #     selected_tipo = st.pills(
        #         label="Tipo Processo:",
        #         options=tipo_options,
        #         selection_mode="single",
        #         default=default_tipo_list,
        #         disabled=True,
        #         key="tipo_lf_pills",
        #         help="Filtro de tipo de processo (fixo)"
        #     )

        # # Habilita/desabilita filtros adicionais com base no status
        # is_def_inde = status_checker_lf in ['Deferido', 'Indeferido']
        # st.session_state.disable_minhas_lf = not is_def_inde
        # st.session_state.disable_nao_respondidas_lf = not is_def_inde

        # Pills adicionais: "As minhas" & "Não respondidas"
        with col2:
            filtros_opts = ["As minhas", "Não respondidas"]
            # default_filters = []
            # if is_def_inde:
            #     default_filters = filtros_opts.copy()
            selected_filters = st.pills(
                label="Filtros adicionais:",
                options=filtros_opts,
                selection_mode="multi",
                # default=default_filters,
                key="filtros_adicionais_lf",
                help="Selecione filtros adicionais"
            )
        chk_somente_minhas = "As minhas" in selected_filters
        chk_nao_respondidas = "Não respondidas" in selected_filters

        # Prepara e filtra DataFrame
        st.session_state.lf_df['Status'] = st.session_state.lf_df['Status'].replace("", "Passivo")
        df_licencas = st.session_state.lf_df.copy()
        # Filtra por status selecionado
        if status_checker_lf:
            df_licencas = df_licencas[df_licencas['Status'] == status_checker_lf]

        # Aplica filtros adicionais
        if chk_somente_minhas:
            df_licencas = df_licencas[df_licencas['Servidor'] == st.session_state.sessao_servidor]
        if chk_nao_respondidas:
            df_licencas = df_licencas[df_licencas['Respondido'] == "Não"]

        # Exibe DataFrame final
        lf_df_filtrado = df_licencas.iloc[:, [0, 1, 4, 2, 8, 7]]


        gg = GridOptionsBuilder.from_dataframe(lf_df_filtrado)
        gg.configure_default_column(
            cellStyle={'font-size': '15px'},
            resizable=True,  # Permite redimensionar as colunas
            filterable=False,
            sortable=False,
            groupable=False
        )
        gg.configure_column("Código Solicitação", minWidth=101, maxWidth=101, header_name="Cód.")
        gg.configure_column("Data Solicitação", minWidth=130, maxWidth=130, header_name="Data")
        gg.configure_column("CPF / CNPJ", minWidth=160, maxWidth=160, header_name="CPF / CNPJ")
        gg.configure_column("Tipo Processo", minWidth=120, maxWidth=120, header_name="Licença")
        gg.configure_column("Setor", minWidth=80, maxWidth=80, header_name="Setor")
        gg.configure_column("Possível Divisão", minWidth=90, maxWidth=90, header_name="Div.")
        gg.configure_selection('single')  # Permite a seleção de uma linha
        gg.configure_pagination(paginationAutoPageSize=False, paginationPageSize=5)
        # Configurar opções do grid
        grid_options = gg.build()
        grid_options["domLayout"] = "print"  # Redimensiona automaticamente o grid
        grid_options["suppressContextMenu"] = True
        grid_options["suppressMenu"] = True
        grid_options["pagination"] = True  # Ativa paginação no grid
        grid_options["paginationPageSizeSelector"] = False

        # Renderizando o AgGrid
        grid_response_lf = AgGrid(
            lf_df_filtrado,
            height=224,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            theme='streamlit'
        )

        selected_row_lf = grid_response_lf.get('selected_rows', None)
            
        if not selected_row_lf is None: 
            selected_index_lf = df_licencas.loc[df_licencas['Código Solicitação'] == selected_row_lf['Código Solicitação'].iloc[0]].index

        if 'aggrid_gh_col2' not in st.session_state:
            st.session_state.aggrid_gh_col2 = None
        
        if 'lf_clear_clicked' not in st.session_state:
            st.session_state.lf_clear_clicked = False

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


        lf_merged_df = st.session_state.merged_df
        
        st.session_state.df_geral_2025 = load_df_2025()

        df_geral_2025 = st.session_state.df_geral_2025
        if not 'Index' in df_geral_2025.columns:
            df_geral_2025 = df_geral_2025.ffill()
            df_geral_2025['Index'] = range(len(df_geral_2025))

        # Verifica se há uma linha selecionada na tabela da col1
        if not selected_row_lf is None:  # Verifica se existe uma linha selecionada
            #selected_cpf_cnpj = selected_rows[0].get("CPF / CNPJ", None)
            selected_cpf_cnpj = selected_row_lf['CPF / CNPJ']

            if not selected_cpf_cnpj is None:
                # Filtra o DataFrame para exibir somente linhas com o mesmo CPF / CNPJ
                filtered_lf_merged_df = lf_merged_df[lf_merged_df["CPF / CNPJ"] == selected_cpf_cnpj.iloc[0]]
                filtered_geral_2025 = df_geral_2025[df_geral_2025['CPF / CNPJ'] == selected_cpf_cnpj.iloc[0]]

                allin_merged_df = pd.concat([filtered_geral_2025, filtered_lf_merged_df], ignore_index=True)
            else:
                allin_merged_df = pd.DataFrame()  # Nenhuma linha será exibida se CPF / CNPJ não for encontrado
        else:
            allin_merged_df = pd.DataFrame()  # Nenhuma linha será exibida se nada for selecionado

        # Configuração da tabela AgGrid para col2
        
        if st.session_state.lf_clear_clicked:
            st.session_state.aggrid_gh_col2 = pd.DataFrame()
            st.session_state.lf_clear_clicked = False
        else:
            st.session_state.aggrid_gh_col2 = allin_merged_df.iloc[:, [0, 4, 8, 1, 10]] if not allin_merged_df.empty else pd.DataFrame(columns=["Protocolo", "Data Criação", "CPF / CNPJ", "Tipo Processo"])
            st.session_state.aggrid_gh_col2 = st.session_state.aggrid_gh_col2.copy() # fazer uma cópia do df evita o warning fdp
            st.session_state.aggrid_gh_col2["Data Criação"] = pd.to_datetime(
                st.session_state.aggrid_gh_col2["Data Criação"], 
                format="%d/%m/%Y", 
                errors="coerce"
            )
            st.session_state.aggrid_gh_col2 = st.session_state.aggrid_gh_col2.sort_values(by="Data Criação", ascending=False)
            st.session_state.aggrid_gh_col2["Data Criação"] = st.session_state.aggrid_gh_col2["Data Criação"].dt.strftime("%d/%m/%Y")

        gh = GridOptionsBuilder.from_dataframe(st.session_state.aggrid_gh_col2)
        gh.configure_column("Index", hide=True)
        gh.configure_default_column(cellStyle={'font-size': '15px'})
        gh.configure_default_column(resizable=False, filterable=False, sortable=False, groupable=False)
        gh.configure_column("Protocolo", minWidth=101, maxWidth=101, header_name="Protocolo")
        gh.configure_column("Data Criação", minWidth=130, maxWidth=130, header_name="Data")
        gh.configure_column("CPF / CNPJ", minWidth=160, maxWidth=160, header_name="CPF / CNPJ")
        gh.configure_column("Tipo Processo", minWidth=290, maxWidth=290, header_name="Tipo Processo")
        gh.configure_selection('single')
        gh.configure_pagination(paginationAutoPageSize=False, paginationPageSize=5)
        gh.configure_grid_options(onCellClicked=True)

        # Configurar opções do grid
        grid_options_merged = gh.build()
        grid_options_merged["domLayout"] = "print"
        grid_options_merged["suppressContextMenu"] = True
        grid_options_merged["suppressMenu"] = True
        grid_options_merged["suppressRowClickSelection"] = False
       
        grid_options_merged["pagination"] = True
        grid_options_merged["paginationPageSizeSelector"] = False

        grid_response_merged_lf = AgGrid(
            st.session_state.aggrid_gh_col2,
            height=224,
            gridOptions=grid_options_merged,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            theme='streamlit'
        )

        if 'sel_merged_lf' not in st.session_state:
            st.session_state.sel_merged_lf = None
            st.session_state.sel_merged_lf_clear = False

        st.session_state.sel_merged_lf = grid_response_merged_lf.get('selected_rows', None)
        
        if 'close_this_damn_json' not in st.session_state:
            st.session_state.close_this_damn_json = False

        @st.dialog("Detalhes do Processo selecionado:", width="large")
        def show_data():
            if '2025' in str(st.session_state.sel_merged_lf['Data Criação']):
                selected_index_lf_merged = df_geral_2025.loc[df_geral_2025.loc[:,'Index'] == st.session_state.sel_merged_lf['Index'].iloc[0]]
                selected_index_lf_merged.loc[:, 'Valor'] = selected_index_lf_merged['Valor'].map(
                    lambda x: x if isinstance(x, str) and x.startswith('R$') else f'R$ {x:,.2f}' if isinstance(x, (int, float)) else 'R$ 0,00'
                )
            else:
                selected_index_lf_merged = lf_merged_df.loc[lf_merged_df.loc[:,'Index'] == st.session_state.sel_merged_lf['Index'].iloc[0]]
                selected_index_lf_merged.loc[:, 'Valor'] = selected_index_lf_merged['Valor'].map(
                    lambda x: f'R$ {x:,.2f}' if isinstance(x, (int, float)) else 'R$ 0,00'
                )

            selected_index_lf_merged.loc[:,'Data Criação'] = selected_index_lf_merged['Data Criação']
            json_data = selected_index_lf_merged.to_json(orient='records', lines=False)
            return st.json(json_data)

        if not st.session_state.close_this_damn_json and not st.session_state.sel_merged_lf is None and not st.session_state.sel_merged_lf_clear:
            show_data()
            st.session_state.sel_merged_lf = None
            st.session_state.sel_merged_lf_clear = False
        else:
            st.session_state.close_this_damn_json = False
            st.session_state.sel_merged_lf_clear = False



# st.write(st.session_state.merged_df) ##################################################################################################



#
# 
# to ride the storm, and damn the rest, oblivion.
#

if 'lf_empty_df' not in st.session_state: 
    selected_line = st.session_state.lf_df.iloc[1].copy()
    selected_line.iloc[:] = ""
    st.session_state.lf_empty_df = selected_line.fillna("")
    treated_line_lf = st.session_state.lf_empty_df
else:
    treated_line_lf = st.session_state.lf_empty_df

if selected_row_lf is not None and len(selected_row_lf) > 0:
    st.session_state.selected_index_lf = int(selected_index_lf[0])
    selected_line = st.session_state.lf_df.iloc[st.session_state.selected_index_lf]
    treated_line_lf = selected_line.fillna("")

# Tratamento dos botões do formulário enchedo linguiça
if 'btn_clear_lf' not in st.session_state:
    st.session_state.btn_clear_lf = False
    st.session_state.disable_file_uploader = True
    st.session_state.disable_btn_save_lf = True
    #st.session_state.disable_btn_edit_lf = True
    st.session_state.disable_btn_send_lf = True

if st.session_state.btn_clear_lf:
    treated_line_lf = st.session_state.lf_empty_df
    st.session_state.btn_clear_lf = False

#
#
#
#

show_expander_2 = False
if len(treated_line_lf["Código Solicitação"]) > 1:
    show_expander_2 = True

with st.expander("Detalhes da solicitação", expanded=show_expander_2):
    st.write("")
    with st.form("form_licencas", enter_to_submit=False, border=False, clear_on_submit=True):
        container1, container2 = st.columns(2, gap="large")
        with container1:

            col1, col2, col3, col4, col5 = st.columns([0.3,0.6,1,1,0.4], vertical_alignment="bottom")
            
            match treated_line_lf["Respondido"]:
                case "Sim":
                    col1.header(":material/check_circle:", anchor=False)
                    #col1.header("🟢", anchor=False)
                case "Não":
                    col1.header(":material/do_not_disturb_on:", anchor=False)
                    #col1.header("🔴", anchor=False)
                case _:
                    col1.header(":material/pending:", anchor=False)
                    #col1.header("⚪️", anchor=False)

            codigo_solicitacao_lf = col2.text_input("Cód. Solicitação", value=treated_line_lf["Código Solicitação"])
            data_solicitacao_lf = col3.text_input("Data Solicitação", value=treated_line_lf["Data Solicitação"])
            ocorrencias_lf = col4.text_input("Ocorrências", value=treated_line_lf["Ocorrências"])

            if 'disable_btn_ocorrencias' not in st.session_state:
                st.session_state.disable_btn_ocorrencias = True

            if treated_line_lf["Ocorrências"] == "":
                st.session_state.disable_btn_ocorrencias = True
            else:
                st.session_state.disable_btn_ocorrencias = False

            btn_ocorrencias = col5.form_submit_button(":material/eye_tracking:", type="secondary",
                                    use_container_width=True, disabled=st.session_state.disable_btn_ocorrencias)
            
            if btn_ocorrencias:
                get_ocorrencias(treated_line_lf["CPF / CNPJ"], "lf")
                btn_ocorrencias = False



            col1, col2, col3 = st.columns(3, vertical_alignment="bottom")
            
            tipo_processo_lf = col1.text_input("Tipo Processo", value=treated_line_lf["Tipo Processo"])
            tipo_empresa_lf = col2.text_input("Setor", value=treated_line_lf["Setor"])
            divisao_declarada_lf = col3.text_input("Possível Divisão", value=treated_line_lf["Possível Divisão"])

            col1, col2, col3 = st.columns([1.5,1,0.5], vertical_alignment="bottom")

            razao_social_lf = col1.text_input("Nome Estab.", value=treated_line_lf["Razão Social"])
            cpf_cnpj_lf = col2.text_input("CPF / CNPJ", value=treated_line_lf["CPF / CNPJ"])             
            btn_cnpj_lf = col3.form_submit_button("", use_container_width=True, icon=":material/search:")

            if btn_cnpj_lf:
                if len(treated_line_lf["CPF / CNPJ"]) == 18:
                    get_cnpj(treated_line_lf["CPF / CNPJ"], '', '')
                else:
                    st.toast(":orange[Não vai rolar. Desculpe. 🙂‍↔️]")


            col1, col2 = st.columns(2, vertical_alignment="bottom")
            email1_lf = col1.text_input("E-mail", value=treated_line_lf["E-mail"])
            email2_lf = col2.text_input("E-mail CC", value=treated_line_lf["E-mail CC"])

            st.write("")
            col1, col2 = st.columns(2, vertical_alignment="bottom")
            col_btn = [col1, col2]
            col_index = 0
            cabecalho_url = ["Docs. Mesclados 1", "Docs. Mesclados 2"]
            for col in cabecalho_url:
                url = treated_line_lf.get(col)
                if isinstance(url, str) and url.startswith("http"):  # Verifica se a célula tem um URL válido
                    with col_btn[col_index]:
                        col_btn[col_index].link_button(f" Abrir {col}", url, icon=":material/link:", use_container_width=True)
                    col_index = (col_index + 1) % 2

            if len(treated_line_lf["Observação"])>5:
                observacao_lf = st.text_area("Observação", value=treated_line_lf["Observação"], height=77)


        with container2:

            col1, col2, col3, col4 = st.columns(4, vertical_alignment="bottom")

            #
            #
            # tentando tratar o estado dos botões...
            #
            #
            status_index_lf = 3

            match treated_line_lf["Status"]:
                case 'Passivo':
                    #st.session_state.status_lf = 'Passivo'
                    status_index_lf = 0
                    #st.session_state.disable_btn_edit_lf = True
                    st.session_state.disable_btn_save_lf = False
                    st.session_state.disable_btn_send_lf = True
                    st.session_state.disable_file_uploader = True
                case 'Deferido':
                    status_index_lf = 1
                    st.session_state.status_lf = 'Deferido'
                    st.session_state.disable_file_uploader = False
                    #st.session_state.disable_btn_edit_lf = False
                    st.session_state.disable_btn_save_lf = False
                    st.session_state.disable_btn_send_lf = False
                case 'Indeferido':
                    status_index_lf = 2
                    st.session_state.status_lf = 'Indeferido'
                    #st.session_state.disable_btn_edit_lf = False
                    st.session_state.disable_btn_save_lf = False
                    st.session_state.disable_btn_send_lf = False
                    st.session_state.disable_file_uploader = True
                case _:
                    status_index_lf = 3
                    st.session_state.status_lf = ''
           
            status_lf = col1.selectbox("Status *", ('Passivo', 'Deferido', 'Indeferido', ''), index=status_index_lf)
            
            divisao_index = None
            match treated_line_lf["Divisão"]:
                case 'DVSA':
                    divisao_index = 0
                case 'DVSE':
                    divisao_index = 1
                case 'DVSCEP':
                    divisao_index = 2
                case 'DVSDM':
                    divisao_index = 3
                case _:
                    divisao_index = 4

            divisao_lf = col2.selectbox("Divisão *", ('DVSA', 'DVSE', 'DVSCEP', 'DVSDM', ''), index=divisao_index)          
            gdoc_lf = col3.text_input("GDOC/Ano (xx/25) *", value=treated_line_lf["GDOC"])
            
            match treated_line_lf["Setor"]:
                case ''| 'Privado':
                    treated_line_lf["Valor Manual"] = treated_line_lf["Valor Manual"]
                case _:
                    treated_line_lf["Valor Manual"] = 'R$ 0,00'

            valor_manual_lf = col4.text_input("Valor do DAM *", value=treated_line_lf["Valor Manual"])

            col1, col2, col3 = st.columns(3, vertical_alignment="bottom")
           
            servidor_lf = col1.text_input("Servidor", value=treated_line_lf["Servidor"])
            data_atendimento_lf = col2.text_input("Data At.", value=treated_line_lf["Data Atendimento"])
            data_modificacao_lf = col3.text_input("Data Mod.", value=treated_line_lf["Data Modificação"])

            cartao_protocolo_lf = st.file_uploader(
                "Anexar Cartão do Protocolo *", accept_multiple_files=False, type=['pdf'], disabled=st.session_state.disable_file_uploader
            )

            motivo_indeferimento_lf = st.text_area("Motivo Indeferimento *", value=treated_line_lf["Motivo Indeferimento"], height=77)

            st.write("")

            # if 'clicou_no_editar' not in st.session_state:
            #     st.session_state.clicou_no_editar = False
            
            # if st.session_state.clicou_no_editar:
            #     st.session_state.disable_btn_edit_lf = True
            #     st.session_state.disable_btn_save_lf = False
            #     st.session_state.clicou_no_editar = False
                
            
            col1, col2, col3, col4, col5 = st.columns(5, vertical_alignment="bottom", gap='small')
            btn_clear_lf = col4.form_submit_button("Limpar", use_container_width=True, disabled=False, icon=":material/ink_eraser:")
            btn_save_lf = col5.form_submit_button("Salvar", use_container_width=True, disabled=st.session_state.disable_btn_save_lf, icon=":material/save:", type='primary')
            btn_send_lf = col3.form_submit_button("Enviar", use_container_width=True, disabled=st.session_state.disable_btn_send_lf, icon=":material/mail:", type='primary')
            #btn_edit_lf = col2.form_submit_button("Editar", use_container_width=True, disabled=True, icon=":material/edit_note:")
            btn_checklist = col2.link_button("Checklist", "https://sites.google.com/view/secretariadevisa/in%C3%ADcio/processos/requisitos?authuser=0",
                                        use_container_width=True, disabled=False, icon=":material/manage_search:")
            btn_gdoc_lf = col1.link_button("GDOC", "https://gdoc.belem.pa.gov.br/gdocprocessos/processo/pesquisarInteressado", 
                                    use_container_width=True, disabled=False, icon=":material/public:")
            
            if st.session_state.auth_user == 'Daniel':
                col1, col2, col3, col4, col5 = st.columns(5, vertical_alignment="bottom", gap='small')
                btn_gdoc_webdriver = col1.form_submit_button('sGDOC', use_container_width=True, icon=":material/smart_toy:")
            else:
                btn_gdoc_webdriver = None          
            
            if 'toast_msg_success' not in st.session_state:
                st.session_state.toast_msg_success = False

            if st.session_state.toast_msg_success:
                st.toast(f"Dados salvos ✨✨")
                st.session_state.toast_msg_success = False

            def btn_clear_fn(rerun=bool):
                st.session_state.disable_btn_save_lf = True
                # st.session_state.disable_btn_edit_lf = True
                st.session_state.disable_btn_send_lf = True
                st.session_state.close_this_damn_json = True # janelinha json
                st.session_state.disable_file_uploader = True
                if rerun:       
                    st.session_state.btn_clear_lf = True
                    st.session_state.reload_lf_df = True
                    status_checker_lf = selected_status_list
                    st.rerun()
            
            if btn_clear_lf:    
                btn_clear_fn(rerun=True)
            
            # if btn_edit_lf:
            #     st.session_state.close_this_damn_json = True # janelinha json
            #     st.session_state.clicou_no_editar = True
            #     st.rerun()
                
            if btn_save_lf:     
                if tipo_processo_lf and  treated_line_lf["Tipo Processo"]:  
                    divisao_list = ['DVSA', 'DVSE', 'DVSCEP', 'DVSDM']
                    treated_valor_manual_lf = ''
                    
                    if valor_manual_lf:
                        treated_valor_manual_lf = extrair_e_formatar_real(valor_manual_lf)
                    
                    if ((status_lf == "Deferido" and validate_gdoc(gdoc_lf, data_solicitacao_lf) and divisao_lf in divisao_list and treated_valor_manual_lf) or 
                        (status_lf == "Indeferido" and len(motivo_indeferimento_lf) > 10)):
                        
                        worksheet = get_worksheet(2, st.secrets['sh_keys']['geral_major'])
                        cell = worksheet.find(codigo_solicitacao_lf, in_column=1)
                        range_lf = f"O{cell.row}:Y{cell.row}"
                        
                        if not worksheet.acell(f'S{cell.row}').value:
                            data_atendimento_lf = get_current_datetime()

                        data_modificacao_lf = get_current_datetime()
                        cartao_protocolo_empty = ""
                        response_lf = "Não"

                        # a ordem de save depende diretamente da ordem da tabela. Cuidado!
                        values = [codigo_solicitacao_lf, treated_valor_manual_lf, status_lf, st.session_state.sessao_servidor, data_atendimento_lf, data_modificacao_lf, motivo_indeferimento_lf,
                                cartao_protocolo_empty, gdoc_lf, divisao_lf, response_lf]
                        worksheet.update(range_lf, [values])

                        worksheet.update(range_lf, [values])
                        st.session_state.load_lf_df = True
                        st.session_state.toast_msg_success = True
                        
                        st.session_state.reload_lf_df = True

                        btn_clear_fn(rerun=True)
                    else:
                        if not validate_gdoc(gdoc_lf, data_solicitacao_lf):
                            ano_atual = datetime.now().year
                            dois_digitos = ano_atual % 100
                            st.toast(f"O formato do núm. GDOC deve ser xx/{dois_digitos}.")
                        else:
                            st.toast("Caiu no dorge do else en 460")
                else:
                    st.toast("Erro. Preencha todos os campos obrigatórios.")
        
            # enviar email
            
            if 'is_email_sended_lf' not in st.session_state:
                st.session_state.is_email_sended_lf = False
            
            def is_email_sended():
                worksheet = get_worksheet(2, st.secrets['sh_keys']['geral_major'])
                cell = worksheet.find(codigo_solicitacao_lf, in_column=1)
                range_lf = f"Y{cell.row}"
                value = "Sim"
                worksheet.update(range_lf, value)
                st.session_state.load_lf_df = True
                st.session_state.is_email_sended_lf = False
                btn_clear_fn(rerun=True)

            def send_mail():
                email_licenciamento(
                    kw_status = status_lf,
                    kw_gdoc = gdoc_lf,
                    kd_divisao = divisao_lf,
                    kw_protocolo = codigo_solicitacao_lf,
                    kw_data_sol = data_solicitacao_lf,
                    kw_tipo_proc = f'Licenciamento Sanitário ({tipo_processo_lf})',
                    kw_razao_social = razao_social_lf,
                    kw_cpf_cnpj = cpf_cnpj_lf,
                    kw_cartao_protocolo = cartao_protocolo_lf,
                    kw_email1 = email1_lf,
                    kw_email2 = email2_lf,
                    kw_motivo_indeferimento = motivo_indeferimento_lf,
                    )
            
            if btn_send_lf:
                # 
                # refazer essa bagunça depois...
                #
                if tipo_processo_lf and treated_line_lf["Tipo Processo"]:
                    if status_lf == "Deferido" and cartao_protocolo_lf is None:
                        st.toast(":red[Falta o cartão do protocolo?]")
                    else:
                        divisao_list = ['DVSA', 'DVSE', 'DVSCEP', 'DVSDM']
                        if (divisao_lf in divisao_list and
                            (status_lf == "Deferido" and validate_gdoc(gdoc_lf, data_solicitacao_lf) and cartao_protocolo_lf and validate_protocolo(cartao_protocolo_lf.name, gdoc_lf) and valor_manual_lf) or 
                            (status_lf == "Indeferido" and len(motivo_indeferimento_lf) > 10)):
                                st.toast(f"Tentando responder à '{codigo_solicitacao_lf}'. Aguarde...")
                                send_mail()
                                if st.session_state.is_email_sended_lf:
                                    is_email_sended()
                                    st.session_state.is_email_sended_lf = False
                        else: 
                            if cartao_protocolo_lf is None or not validate_protocolo(cartao_protocolo_lf.name, gdoc_lf):
                                st.toast(":red[Tem certeza que o **cartão do protocolo** ou o **nº do processo** está correto?]")

                            if not validate_gdoc(gdoc_lf, data_solicitacao_lf):
                                ano_atual = datetime.now().year
                                dois_digitos = ano_atual % 100
                                st.toast(f"O formato do núm. GDOC deve ser xx/{dois_digitos}.")
                                                
                else:
                    st.toast(":red[Erro. Preencha todos os campos obrigatórios.]")
            

            # automação gdoc
            if btn_gdoc_webdriver:
                if treated_line_lf["CPF / CNPJ"] and divisao_lf:
                    selenium_proc_gdoc(
                        kw_cpf_cnpj = treated_line_lf["CPF / CNPJ"],
                        kw_razao_social = treated_line_lf["Razão Social"],
                        kw_email1 = treated_line_lf["E-mail"],
                        kw_email2 = treated_line_lf["E-mail CC"],
                        kw_tipoProc = treated_line_lf["Tipo Processo"],
                        kw_divisao = divisao_lf,
                        kw_docs1 = treated_line_lf["Docs. Mesclados 1"],
                        kw_docs2 = treated_line_lf["Docs. Mesclados 2"],
                        kw_obs = treated_line_lf["Observação"]
                    )
                else:
                    st.toast(":red[**Carregue um processo e escolha a divisão.**]")

                st.toast('zé da manga')

