import streamlit as st
import pandas as pd
from load_functions import *
# from streamlit_gsheets import GSheetsConnection
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
#import time, re, json, gspread, pyperclip
import json, gspread
#import fitz

st.header("Processos Diversos", anchor=False)

if 'reload_div_df' not in st.session_state: 
    st.session_state.reload_div_df = False
    # declarar primeiro, e recarregar os outros bancos
    st.session_state.reload_tx_df = True
    st.session_state.reload_lf_df = True

# recarregar os outros bancos
st.session_state.reload_tx_df = True
st.session_state.reload_lf_df = True

@st.cache_data(ttl=300, show_spinner="Carregando o banco 'Diversos'...")
def load_div_df():   
    worksheet = get_worksheet(1, st.secrets['sh_keys']['geral_major'])
    data = worksheet.get_all_records(numericise_ignore=['all'])
    df = pd.DataFrame(data)
    return df

if 'div_df'not in st.session_state:
    df_div_aux = load_div_df()
    st.session_state.div_df = df_div_aux[df_div_aux["Validade"] != "Inválido"]
    st.session_state.div_df = st.session_state.div_df.reset_index(drop=True)

if st.session_state.reload_div_df:
    st.session_state.div_df = None
    load_div_df.clear()
    df_div_aux = load_div_df()
    st.session_state.div_df = df_div_aux[df_div_aux["Validade"] != "Inválido"]
    st.session_state.div_df = st.session_state.div_df.reset_index(drop=True)
    st.session_state.reload_div_df = False

if 'checkbox_minhas_d' not in st.session_state:
   st.session_state.checkbox_minhas_d = False
   st.session_state.disable_checkbox_minhas_d = True

if 'checkbox_nao_respondidas_d' not in st.session_state:
    st.session_state.checkbox_nao_respondidas_d = False
    st.session_state.disable_checkbox_nao_respondidas_d = True


with st.expander("Registro de Solicitações", expanded=True):
    colx, coly = st.columns(2, vertical_alignment="top")
    with colx:
        col1, col2, col3, col4 = st.columns(4, vertical_alignment="bottom")
        status_selecionado = col1.selectbox("Status:", options=['Passivo', 'Deferido', 'Indeferido'])
        tipo_processo_opcoes = st.session_state.div_df['Tipo Processo'].unique()  # Valores únicos

        # isso é só p evitar estouro de erro por conta de database vazio
        if 'index_t_proc_div' not in st.session_state:
            st.session_state.index_t_proc_div = None
        match len(tipo_processo_opcoes):
            case 0 | None:
                st.session_state.index_t_proc_div = None
            case _:
                st.session_state.index_t_proc_div = 0  

        tipo_selecionado = col2.selectbox("Tipo Processo:", options=tipo_processo_opcoes, disabled=True, index=st.session_state.index_t_proc_div)

        if status_selecionado == 'Deferido' or status_selecionado == 'Indeferido':
            st.session_state.disable_checkbox_minhas_d = False
            st.session_state.disable_checkbox_nao_respondidas_d = False
        else:
            st.session_state.disable_checkbox_minhas_d = True
            st.session_state.disable_checkbox_nao_respondidas_d = True

        chk_somente_minhas = col3.checkbox("As minhas", value=st.session_state.checkbox_minhas_d, disabled=st.session_state.disable_checkbox_minhas_d, help="Mostrar somente as tratadas por mim")
        
        chk_nao_respondidas = col4.checkbox("Não respondidas", value=st.session_state.checkbox_nao_respondidas_d, disabled=st.session_state.disable_checkbox_nao_respondidas_d)

        st.session_state.div_df['Status'] = st.session_state.div_df['Status'].replace("", "Passivo")
        df_diversos = st.session_state.div_df[st.session_state.div_df['Status'] == status_selecionado] if status_selecionado else st.session_state.div_df
        
        if chk_somente_minhas:
            df_diversos = df_diversos[df_diversos['Servidor'] == st.session_state.sessao_servidor]
        
        if chk_nao_respondidas:
            df_diversos = df_diversos[df_diversos['Respondido'] == "Não"]

        div_df_filtrado = df_diversos.iloc[:, [0, 1, 4, 2]]
        # st.write(div_df_filtrado)
        ge = GridOptionsBuilder.from_dataframe(div_df_filtrado)
        ge.configure_default_column(
            cellStyle={'font-size': '15px'},
            resizable=True,  # Permite redimensionar as colunas
            filterable=False,
            sortable=False,
            groupable=False
        )
        ge.configure_column("Código Solicitação", minWidth=101, maxWidth=101, header_name="Cód.")
        ge.configure_column("Data Solicitação", minWidth=130, maxWidth=130, header_name="Data")
        ge.configure_column("CPF / CNPJ", minWidth=160, maxWidth=160, header_name="CPF / CNPJ")
        ge.configure_column("Tipo Processo", minWidth=290, maxWidth=290, header_name="Tipo Processo")
        ge.configure_selection('single')  # Permite a seleção de uma linha
        ge.configure_pagination(paginationAutoPageSize=False, paginationPageSize=5)
        # Configurar opções do grid
        grid_options = ge.build()
        grid_options["domLayout"] = "print"  # Redimensiona automaticamente o grid
        grid_options["suppressContextMenu"] = True
        grid_options["suppressMenu"] = True
        grid_options["pagination"] = True  # Ativa paginação no grid
        grid_options["paginationPageSizeSelector"] = False

        # Renderizando o AgGrid
        grid_response_d = AgGrid(
            div_df_filtrado,
            height=224,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            theme='streamlit'
        )

        selected_row_div = grid_response_d.get('selected_rows', None)
            
        if not selected_row_div is None: 
            selected_index_div = df_diversos.loc[df_diversos['Código Solicitação'] == selected_row_div['Código Solicitação'].iloc[0]].index

        if 'aggrid_gf_col2' not in st.session_state:
            st.session_state.aggrid_gf_col2 = None
        
        if 'div_clear_clicked' not in st.session_state:
            st.session_state.div_clear_clicked = False

    with coly:
        col5, col6, col7 = st.columns(3, vertical_alignment="bottom")
        teste1 = col5.selectbox("Filtro 1",  options=['Passivo', 'Filtro 1', 'Indeferido'], index=1, disabled=True)
        teste2 = col6.selectbox("Filtro 2",  options=['Passivo', 'Filtro 2', 'Indeferido'], index=1, disabled=True)
        teste3 = col7.selectbox("Filtro 3",  options=['Passivo', 'Filtro 3', 'Indeferido'], index=1, disabled=True)


        div_merged_df = st.session_state.merged_df

        st.session_state.df_geral_2025 = load_df_2025()

        df_geral_2025 = st.session_state.df_geral_2025
        if not 'Index' in df_geral_2025.columns:
            df_geral_2025 = df_geral_2025.ffill()
            df_geral_2025['Index'] = range(len(df_geral_2025))
           
        # Verifica se há uma linha selecionada na tabela da col1
        if not selected_row_div is None:  # Verifica se existe uma linha selecionada
            #selected_cpf_cnpj = selected_rows[0].get("CPF / CNPJ", None)
            selected_cpf_cnpj = selected_row_div['CPF / CNPJ']
            if not selected_cpf_cnpj is None:
                # Filtra o DataFrame para exibir somente linhas com o mesmo CPF / CNPJ
                filtered_div_merged_df = div_merged_df[div_merged_df["CPF / CNPJ"] == selected_cpf_cnpj.iloc[0]]
                filtered_geral_2025 = df_geral_2025[df_geral_2025['CPF / CNPJ'] == selected_cpf_cnpj.iloc[0]]

                allin_merged_df = pd.concat([filtered_geral_2025, filtered_div_merged_df], ignore_index=True)
            else:
                allin_merged_df = pd.DataFrame()  # Nenhuma linha será exibida se CPF / CNPJ não for encontrado
        else:
            allin_merged_df = pd.DataFrame()  # Nenhuma linha será exibida se nada for selecionado

        # Configuração da tabela AgGrid para col2
        
        if st.session_state.div_clear_clicked:
            st.session_state.aggrid_gf_col2 = pd.DataFrame()
            st.session_state.div_clear_clicked = False
        else:
            st.session_state.aggrid_gf_col2 = allin_merged_df.iloc[:, [0, 4, 8, 1, 10]] if not allin_merged_df.empty else pd.DataFrame(columns=["Protocolo", "Data Criação", "CPF / CNPJ", "Tipo Processo"])
            #st.session_state.aggrid_gf_col2["Data Criação"] = pd.to_datetime(st.session_state.aggrid_gf_col2["Data Criação"], format="%d/%m/%Y", errors="coerce")
            st.session_state.aggrid_gf_col2 = st.session_state.aggrid_gf_col2.copy() # fazer uma cópia do df evita o warning fdp
            st.session_state.aggrid_gf_col2["Data Criação"] = pd.to_datetime(
                st.session_state.aggrid_gf_col2["Data Criação"], 
                format="%d/%m/%Y", 
                errors="coerce"
            )                    
            st.session_state.aggrid_gf_col2 = st.session_state.aggrid_gf_col2.sort_values(by="Data Criação", ascending=False)
            st.session_state.aggrid_gf_col2["Data Criação"] = st.session_state.aggrid_gf_col2["Data Criação"].dt.strftime("%d/%m/%Y")

        gf = GridOptionsBuilder.from_dataframe(st.session_state.aggrid_gf_col2)
        gf.configure_column("Index", hide=True)
        gf.configure_default_column(cellStyle={'font-size': '15px'})
        gf.configure_default_column(resizable=False, filterable=False, sortable=False, groupable=False)
        gf.configure_column("Protocolo", minWidth=101, maxWidth=101, header_name="Protocolo")
        gf.configure_column("Data Criação", minWidth=130, maxWidth=130, header_name="Data")
        gf.configure_column("CPF / CNPJ", minWidth=160, maxWidth=160, header_name="CPF / CNPJ")
        gf.configure_column("Tipo Processo", minWidth=290, maxWidth=290, header_name="Tipo Processo")
        gf.configure_selection('single')
        gf.configure_pagination(paginationAutoPageSize=False, paginationPageSize=5)
        gf.configure_grid_options(onCellClicked=True)

        # Configurar opções do grid
        grid_options_merged = gf.build()
        grid_options_merged["domLayout"] = "print"
        grid_options_merged["suppressContextMenu"] = True
        grid_options_merged["suppressMenu"] = True
        grid_options_merged["suppressRowClickSelection"] = False
       
        grid_options_merged["pagination"] = True
        grid_options_merged["paginationPageSizeSelector"] = False

        grid_response_merged_d = AgGrid(
            st.session_state.aggrid_gf_col2,
            height=224,
            gridOptions=grid_options_merged,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            theme='streamlit'
        )

        if 'sel_merged_div' not in st.session_state:
            st.session_state.sel_merged_div = None
            st.session_state.sel_merged_div_clear = False

        st.session_state.sel_merged_div = grid_response_merged_d.get('selected_rows', None)
        
        if 'close_this_damn_json' not in st.session_state:
            st.session_state.close_this_damn_json = False

        @st.dialog("Detalhes do Processo selecionado:", width="large")
        def show_data():
            if '2025' in str(st.session_state.sel_merged_div['Data Criação']):
                selected_index_div_merged = df_geral_2025.loc[df_geral_2025.loc[:,'Index'] == st.session_state.sel_merged_div['Index'].iloc[0]]
                selected_index_div_merged.loc[:, 'Valor'] = selected_index_div_merged['Valor'].map(
                    lambda x: x if isinstance(x, str) and x.startswith('R$') else f'R$ {x:,.2f}' if isinstance(x, (int, float)) else 'R$ 0,00'
                )
            else:
                selected_index_div_merged = div_merged_df.loc[div_merged_df.loc[:,'Index'] == st.session_state.sel_merged_div['Index'].iloc[0]]          
                selected_index_div_merged.loc[:, 'Valor'] = selected_index_div_merged['Valor'].map(
                    lambda x: f'R$ {x:,.2f}' if isinstance(x, (int, float)) else 'R$ 0,00'
                )
            
            selected_index_div_merged.loc[:,'Data Criação'] = selected_index_div_merged['Data Criação']
            selected_index_div_merged = selected_index_div_merged.ffill()
            json_data = selected_index_div_merged.to_json(orient='records', lines=False)
            return st.json(json_data)

        if not st.session_state.close_this_damn_json and not st.session_state.sel_merged_div is None and not st.session_state.sel_merged_div_clear:
            show_data()
            st.session_state.sel_merged_div = None
            st.session_state.sel_merged_div_clear = False
        else:
            st.session_state.close_this_damn_json = False
            st.session_state.sel_merged_div_clear = False

#
# 
# to ride the storm, and damn the rest, oblivion.
#

if 'div_empty_df' not in st.session_state: 
    selected_line = st.session_state.div_df.iloc[0].copy()
    selected_line.iloc[:] = ""
    st.session_state.div_empty_df = selected_line.fillna("")
    treated_line_div = st.session_state.div_empty_df
else:
    treated_line_div = st.session_state.div_empty_df

if selected_row_div is not None and len(selected_row_div) > 0:
    st.session_state.selected_index_div = int(selected_index_div[0])
    selected_line = st.session_state.div_df.iloc[st.session_state.selected_index_div]
    treated_line_div = selected_line.fillna("")

# Tratamento dos botões do formulário enchedo linguiça
if 'btn_clear_d' not in st.session_state:
    st.session_state.btn_clear_d = False
    st.session_state.disable_file_uploader = True
    st.session_state.disable_btn_save_d = True
    st.session_state.disable_btn_edit_d = True
    st.session_state.disable_btn_send_d = True

if st.session_state.btn_clear_d:
    treated_line_div = st.session_state.div_empty_df
    st.session_state.btn_clear_d = False

#
#
#
#

show_expander_2 = False
if len(treated_line_div["Código Solicitação"]) > 1:
    show_expander_2 = True

with st.expander("Detalhes da solicitação", expanded=show_expander_2):
    st.write("")
    with st.form("form_diversos", enter_to_submit=False, border=False, clear_on_submit=True):
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([2,0.6,0.6,0.6,0.4,0.6,0.6,0.2], vertical_alignment="bottom")
        tipo_processo_d = col1.text_input("Tipo Processo", value=treated_line_div["Tipo Processo"])
        codigo_solicitacao_d = col2.text_input("Cód. Solicitação", value=treated_line_div["Código Solicitação"])
        data_solicitacao_d = col3.text_input("Data Solicitação", value=treated_line_div["Data Solicitação"])
        ocorrencias_d = col4.text_input("Ocorrências", value=treated_line_div["Ocorrências"])

        if 'disable_btn_ocorrencias' not in st.session_state:
            st.session_state.disable_btn_ocorrencias = True

        if treated_line_div["Ocorrências"] == "":
            st.session_state.disable_btn_ocorrencias = True
        else:
            st.session_state.disable_btn_ocorrencias = False

        btn_ocorrencias = col5.form_submit_button(":material/eye_tracking:", type="secondary",
                                use_container_width=True, disabled=st.session_state.disable_btn_ocorrencias)

        if btn_ocorrencias:
            get_ocorrencias(treated_line_div["CPF / CNPJ"], "diversos")
            btn_ocorrencias = False

        gdoc_d = col6.text_input("GDOC/Ano (xx/25) *", value=treated_line_div["GDOC"])
        
        match treated_line_div["Respondido"]:
            case "Sim":
                col8.header(":material/check_circle:", anchor=False)
                #col7.header("🟢", anchor=False)
            case "Não":
                col8.header(":material/do_not_disturb_on:", anchor=False)
                #col7.header("🔴", anchor=False)
            case _:
                col8.header(":material/pending:", anchor=False)
                #col7.header("⚪️", anchor=False)
        
        divisao_index = None
        match treated_line_div["Divisão"]:
            case 'DVSA':
                divisao_index = 0
            case 'DVSE':
                divisao_index = 1
            case 'DVSCEP':
                divisao_index = 2
            case 'DVSDM':
                divisao_index = 3
            case 'Visamb':
                divisao_index = 4
            case 'Açaí':
                divisao_index = 5
            case _:
                divisao_index = 6
        
        divisao_d = col7.selectbox("Divisão *", ('DVSA', 'DVSE', 'DVSCEP', 'DVSDM', 'Visamb', 'Açaí', ''), index=divisao_index)



        col1, col2, col3, col4, col5 = st.columns([2,1,0.4,1,1], vertical_alignment="bottom")
        razao_social_d = col1.text_input("Nome Empresa", value=treated_line_div["Razão Social"])
        cpf_cnpj_d = col2.text_input("CPF / CNPJ", value=treated_line_div["CPF / CNPJ"])
                
        btn_cnpj_d = col3.form_submit_button("", use_container_width=True, icon=":material/search:")
        email1_d = col4.text_input("E-mail", value=treated_line_div["E-mail"])
        email2_d = col5.text_input("E-mail CC", value=treated_line_div["E-mail CC"])
        

        if btn_cnpj_d:
            if len(treated_line_div["CPF / CNPJ"]) == 18:
                get_cnpj(treated_line_div["CPF / CNPJ"], '', '')
            else:
                st.toast(":red[Não vai rolar. Desculpe. 🙂‍↔️]")

        col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5,0.7,0.7,0.8,1,0.7,0.7], vertical_alignment="bottom")   
        comp_valor_un_d = col1.text_input("Comp. Valor", value=treated_line_div["Complemento Valor"])
        valor_un_d = col2.text_input("Valor Unit.", value=treated_line_div["Valor Unitário"])

        match treated_line_div["Complemento Valor"]:

            case '' | 'Pessoa Física' | 'Empresa Privada':
                treated_line_div["Valor Manual"] = treated_line_div["Valor Manual"]
            case _:
                treated_line_div["Valor Manual"] = 'R$ 0,00'

        valor_manual_d = col3.text_input("Valor do DAM *", value=treated_line_div["Valor Manual"])

        status_index_d = 3

        match treated_line_div["Status"]:
            case 'Passivo':
                status_index_d = 0
                st.session_state.disable_btn_edit_d = True
                st.session_state.disable_btn_save_d = False
                st.session_state.disable_btn_send_d = True
                st.session_state.disable_file_uploader = True
            case 'Deferido':
                status_index_d = 1
                st.session_state.disable_file_uploader = False
                st.session_state.disable_btn_edit_d = False
                st.session_state.disable_btn_save_d = True
                st.session_state.disable_btn_send_d = False
            case 'Indeferido':
                status_index_d = 2
                st.session_state.disable_btn_edit_d = False
                st.session_state.disable_btn_save_d = True
                st.session_state.disable_btn_send_d = False
                st.session_state.disable_file_uploader = True
            case _:
                status_index_d = 3

        status_d = col4.selectbox("Status *", ('Passivo', 'Deferido', 'Indeferido', ''), index=status_index_d)
        
        servidor_d = col5.text_input("Servidor", value=treated_line_div["Servidor"])
        data_atendimento_d = col6.text_input("Data At.", value=treated_line_div["Data Atendimento"])
        data_modificacao_d = col7.text_input("Data Mod.", value=treated_line_div["Data Modificação"])

        col1, col2, col3 = st.columns(3, vertical_alignment="top")
        observacao_d = col1.text_area("Observação", value=treated_line_div["Observação"], height=77)
        motivo_indeferimento_d = col2.text_area("Motivo Indeferimento *", value=treated_line_div["Motivo Indeferimento"], height=77)

        cartao_protocolo_d = col3.file_uploader(
            "Anexar Cartão do Protocolo *", accept_multiple_files=False, type=['pdf'], disabled=st.session_state.disable_file_uploader
        )

        #if cartao_protocolo_d is not None:
        #    bytes_data = cartao_protocolo_d.getvalue()
        #    st.write(bytes_data)

        col1, col2, col3, col4, col5, col6 = st.columns(6, vertical_alignment='bottom')
        col7, col8, col9, col10, col11, col12 = st.columns(6, vertical_alignment='bottom', gap='small')      

        col_btn = [col1, col2]
        col_btn_projeto = [col3, col4, col5, col6, col7, col8, col9, col10, col11, col12]
        col_index = 0

        cabecalho_url = ["Docs Mesclados", "Decreto de Utilidade Pública", "CCMEI", "Ofício"]

        # Adiciona os dois primeiros botões normalmente
        for col in cabecalho_url:
            url = treated_line_div.get(col)
            if isinstance(url, str) and url.startswith("http"):  # Verifica se a célula tem um URL válido
                with col_btn[col_index]:
                    col_btn[col_index].link_button(f"{col}", url, icon=":material/link:", use_container_width=True)
                col_index = (col_index + 1) % 2

        # Verifica se o tipo de processo contém "Projeto" e se há URLs na coluna correspondente
        projeto_urls = treated_line_div.get("Docs Aprovação de Projeto", "")
        if "aprovação de Projeto" in treated_line_div.get("Tipo Processo", "") \
        and isinstance(projeto_urls, str) and projeto_urls.strip():

            # -- aqui a mágica --
            projeto_urls = [
                f"https://{u.strip()}"
                for u in projeto_urls.split("https://")
                if u.strip()
            ]

            # Verifica se col2 foi usada
            start_index = 0 if col_index == 0 else 1
            col_btn_projeto = col_btn[start_index:] + col_btn_projeto

            titulos_iniciais = ["Localiz. e Situação", "Planta Baixa", "Layout", "Cortes"]
            for i, url in enumerate(projeto_urls):
                if i >= len(col_btn_projeto):
                    break
                # url já começa com http:// ou https://
                if url.startswith("http"):
                    titulo = titulos_iniciais[i] if i < len(titulos_iniciais) else f"Prancha {i+1}"
                    with col_btn_projeto[i]:
                        col_btn_projeto[i].link_button(
                            titulo,
                            url,
                            icon=":material/link:",
                            use_container_width=True
                        )
        st.write("")
        st.write("")

        if 'clicou_no_editar' not in st.session_state:
            st.session_state.clicou_no_editar = False
        
        if st.session_state.clicou_no_editar:
            st.session_state.disable_btn_edit_d = True
            st.session_state.disable_btn_save_d = False
            st.session_state.clicou_no_editar = False
        

        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8, vertical_alignment="bottom")
        btn_clear_d = col8.form_submit_button("Limpar", use_container_width=True, disabled=False, icon=":material/ink_eraser:")
        btn_save_d = col7.form_submit_button("Salvar", use_container_width=True, disabled=st.session_state.disable_btn_save_d, icon=":material/save:", type='primary')
        btn_edit_d = col6.form_submit_button("Editar", use_container_width=True, disabled=st.session_state.disable_btn_edit_d, icon=":material/edit_note:")
        btn_send_d = col5.form_submit_button("Enviar", use_container_width=True, disabled=st.session_state.disable_btn_send_d, icon=":material/mail:", type='primary')
        btn_checklist = col4.link_button("Requisitos", "https://sites.google.com/view/secretariadevisa/in%C3%ADcio/processos/requisitos?authuser=0",
                                        use_container_width=True, disabled=False, icon=":material/manage_search:")
        btn_gdoc_d = col3.link_button("GDOC", "https://gdoc.belem.pa.gov.br/gdocprocessos/processo/pesquisarInteressado", 
                                use_container_width=True, disabled=False, icon=":material/public:")
        
        
        if 'toast_msg_success' not in st.session_state:
            st.session_state.toast_msg_success = False

        if st.session_state.toast_msg_success:
            st.toast(f"Dados salvos ✨✨")
            st.session_state.toast_msg_success = False

        def btn_clear_fn(rerun=bool):
            st.session_state.disable_btn_save_d = True
            st.session_state.disable_btn_edit_d = True
            st.session_state.disable_btn_send_d = True
            st.session_state.close_this_damn_json = True # janelinha json
            st.session_state.disable_file_uploader = True

            if rerun:
                st.session_state.reload_div_df = True
                st.session_state.btn_clear_d = True
                st.rerun()
        
        if btn_clear_d:
            st.session_state.close_this_damn_json = True # janelinha json
            btn_clear_fn(rerun=True)


        def save_in_sheet(btn_edit: bool):
            if tipo_processo_d and treated_line_div["Tipo Processo"]:  
                # valor manual, status, motivo indeferimento e cartão do protocolo
                divisao_list = ['DVSA', 'DVSE', 'DVSCEP', 'DVSDM', 'Açaí', 'Visamb']
                treated_valor_manual_d = extrair_e_formatar_real(valor_manual_d)
                if ((status_d == "Deferido" and validate_gdoc(gdoc_d, data_solicitacao_d) and divisao_d in divisao_list and treated_valor_manual_d) or 
                    (status_d == "Indeferido" and len(motivo_indeferimento_d) > 10)):
                    # sessao_servidor = "Daniel"

                    worksheet = get_worksheet(1, st.secrets['sh_keys']['geral_major'])
                    cell = worksheet.find(codigo_solicitacao_d, in_column=1)
                    
                    if cell:
                        # Verifica a célula correspondente na coluna AC
                        col_ac_index = 19  # Se a coluna AC é a 29ª (1-indexada), então a col T é 19
                        ac_value = worksheet.cell(cell.row, col_ac_index).value
                        if ac_value and not btn_edit:
                            st.toast(f"**:red[Erro. Esta solicitação já foi salva pelo usuário {ac_value}.]**") 
                        else:
                            if status_d == 'Passivo':
                               st.toast(f"**:red[Não é possível retornar a solicitação para a caixa 'Passivo'.]**")
                            else:     
                                range_div = f"Q{cell.row}:AA{cell.row}"
                                
                                data_atendimento_d = worksheet.acell(f'U{cell.row}').value
                                if not data_atendimento_d:
                                    data_atendimento_d = get_current_datetime()

                                data_modificacao_d = get_current_datetime()
                                cartao_protocolo_empty = ""
                                response_d = "Não"

                                # a ordem de save depende diretamente da ordem da tabela. Cuidado!
                                values = [codigo_solicitacao_d, treated_valor_manual_d, status_d, st.session_state.sessao_servidor, data_atendimento_d, data_modificacao_d, motivo_indeferimento_d,
                                        cartao_protocolo_empty, gdoc_d, divisao_d, response_d]
                                worksheet.update(range_div, [values])
                                st.session_state.load_div_df = True
                                st.session_state.toast_msg_success = True
                                btn_clear_fn(rerun=True)
                    else:
                        st.toast(f"**:red[Registro não salvo. cell está vazia]**")
                else:
                    if not validate_gdoc(gdoc_d, data_solicitacao_d):
                        ano_atual = datetime.now().year
                        dois_digitos = ano_atual % 100
                        st.toast(f"O formato do núm. GDOC deve ser xx/{dois_digitos}.")
            else:
                st.toast("Erro. Preencha todos os campos obrigatórios.")

        
        
        if btn_edit_d:
            # st.session_state.close_this_damn_json = True # janelinha json
            # st.session_state.clicou_no_editar = True   
            # st.rerun()
            save_in_sheet(btn_edit=True)
             
        if btn_save_d:
            save_in_sheet(btn_edit=False)           
            
    
        # enviar email
        
        if 'is_email_sended_d' not in st.session_state:
            st.session_state.is_email_sended_d = False
        
        def is_email_sended():
            worksheet = get_worksheet(1, st.secrets['sh_keys']['geral_major'])
            cell = worksheet.find(codigo_solicitacao_d, in_column=1)
            range_div = f"AA{cell.row}"
            value = "Sim"
            worksheet.update(range_div, value)
            st.session_state.load_div_df = True
            st.session_state.is_email_sended_d = False
            btn_clear_fn(rerun=True)

        def send_mail():
            email_diversos(
                kw_status = status_d,
                kw_gdoc = gdoc_d,
                kd_divisao = divisao_d,
                kw_protocolo = codigo_solicitacao_d,
                kw_data_sol = data_solicitacao_d,
                kw_tipo_proc = tipo_processo_d,
                kw_razao_social = razao_social_d,
                kw_cpf_cnpj = cpf_cnpj_d,
                kw_cartao_protocolo = cartao_protocolo_d,
                kw_email1 = email1_d,
                kw_email2 = email2_d,
                kw_motivo_indeferimento = motivo_indeferimento_d,
                )
        
        if btn_send_d:
            # 
            # refazer essa bagunça depois...
            #
            if tipo_processo_d and treated_line_div["Tipo Processo"] and valor_manual_d:

                if status_d == "Deferido" and cartao_protocolo_d is None:
                    st.toast(":red[**Cadê o cartão do protocolo?**]")
                else:
                    divisao_list = ['DVSA', 'DVSE', 'DVSCEP', 'DVSDM', 'Açaí', 'Visamb']
                    if (divisao_d in divisao_list and
                        (status_d == "Deferido" and validate_gdoc(gdoc_d, data_solicitacao_d) and cartao_protocolo_d and validate_protocolo(cartao_protocolo_d.name, gdoc_d)) or 
                        (status_d == "Indeferido" and len(motivo_indeferimento_d) > 10)):
                            st.toast(f"Tentando responder à '{codigo_solicitacao_d}'. Aguarde...")
                            send_mail()
                            if st.session_state.is_email_sended_d:
                                is_email_sended()
                                st.session_state.is_email_sended_d = False
                    else: 
                        if cartao_protocolo_d is None or not validate_protocolo(cartao_protocolo_d.name, gdoc_d):
                            st.toast(":red[Tem certeza que o **cartão do protocolo** ou o **nº do processo** está correto?]")

                        if not validate_gdoc(gdoc_d, data_solicitacao_d):
                            ano_atual = datetime.now().year
                            dois_digitos = ano_atual % 100
                            st.toast(f"O formato do núm. GDOC deve ser xx/{dois_digitos}.")
                                             
            else:
                st.toast(":red[Erro. Preencha todos os campos obrigatórios.]")
