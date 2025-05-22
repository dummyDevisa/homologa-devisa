import streamlit as st
import pandas as pd
from load_functions import *
from webdriver_gdoc import *
import re
import datetime

# ... (código inicial e funções auxiliares como load_lf_df_cached, etc., permanecem os mesmos) ...
st.header("Licença de Funcionamento", anchor=False)

@st.cache_data(ttl=300, show_spinner="Carregando banco de LFs...")
def load_lf_df_cached():
    worksheet = get_worksheet(2, st.secrets['sh_keys']['geral_major'])
    data = worksheet.get_all_records(numericise_ignore=['all'])
    df = pd.DataFrame(data)
    return df

if 'reload_lf_df' not in st.session_state:
    st.session_state.reload_lf_df = False
if 'reload_tx_df' not in st.session_state:
    st.session_state.reload_tx_df = False


if 'lf_df' not in st.session_state or st.session_state.reload_lf_df:
    lf_df_aux = load_lf_df_cached()
    if not lf_df_aux.empty:
        st.session_state.lf_df = lf_df_aux[lf_df_aux["Validade"] != "Inválido"].copy()
        st.session_state.lf_df = st.session_state.lf_df.reset_index(drop=True)
        st.session_state.lf_df['Data_Solicitacao_dt'] = pd.to_datetime(
            st.session_state.lf_df['Data Solicitação'],
            format='%d/%m/%y, %H:%M', errors='coerce'
        )
    else:
        st.session_state.lf_df = pd.DataFrame()
    st.session_state.reload_lf_df = False

if 'status_selecionado_lf' not in st.session_state:
    st.session_state.status_selecionado_lf = 'Passivo'

if 'secondary_pills_selection' not in st.session_state:
    if st.session_state.status_selecionado_lf in ['Deferido', 'Indeferido']:
        st.session_state.secondary_pills_selection = ["As minhas", "Não resp."]
    else:
        st.session_state.secondary_pills_selection = []

st.session_state.checkbox_minhas_lf = "As minhas" in st.session_state.secondary_pills_selection
st.session_state.checkbox_nao_respondidas_lf = "Não resp." in st.session_state.secondary_pills_selection

with st.expander("Registro de Solicitações", expanded=True):
    colx, coly = st.columns(2, vertical_alignment="top")

    with colx:
        col1, col2, col3 = st.columns([0.9, 1.0, 1.1], vertical_alignment="center", gap="small")

        status_options = ['Passivo', 'Deferido', 'Indeferido']
        current_default_for_status_pills = [st.session_state.status_selecionado_lf] if st.session_state.status_selecionado_lf in status_options else [status_options[0]]

        with col3:
            selected_status_output = st.pills(
                label="Filtro por Status:",
                options=status_options,
                default=current_default_for_status_pills,
                key="status_pills_filter_key",
                help="Escolha o status do processo",
                label_visibility='collapsed'
            )

        if selected_status_output and selected_status_output != st.session_state.status_selecionado_lf:
            st.session_state.status_selecionado_lf = selected_status_output
            if st.session_state.status_selecionado_lf in ['Deferido', 'Indeferido']:
                st.session_state.secondary_pills_selection = ["As minhas", "Não resp."]
            else:
                st.session_state.secondary_pills_selection = []
            st.session_state.checkbox_minhas_lf = "As minhas" in st.session_state.secondary_pills_selection
            st.session_state.checkbox_nao_respondidas_lf = "Não resp." in st.session_state.secondary_pills_selection
            st.rerun()

        status_para_filtragem = st.session_state.status_selecionado_lf
        disable_secondary_pills = not (status_para_filtragem in ['Deferido', 'Indeferido'])

        if disable_secondary_pills and st.session_state.secondary_pills_selection:
            st.session_state.secondary_pills_selection = []
            st.session_state.checkbox_minhas_lf = False
            st.session_state.checkbox_nao_respondidas_lf = False

        opcoes_filtros_secundarios = ["As minhas", "Não resp."]

        with col2:
            selected_secondary_output = st.pills(
                label="Filtros Secundários",
                options=opcoes_filtros_secundarios,
                default=st.session_state.secondary_pills_selection,
                selection_mode="multi",
                key="filtros_pills_secundarios_key",
                help="Selecione os filtros desejados",
                label_visibility='collapsed',
                disabled=disable_secondary_pills
            )

        if not disable_secondary_pills:
            if st.session_state.secondary_pills_selection != selected_secondary_output:
                st.session_state.secondary_pills_selection = selected_secondary_output
                st.session_state.checkbox_minhas_lf = "As minhas" in st.session_state.secondary_pills_selection
                st.session_state.checkbox_nao_respondidas_lf = "Não resp." in st.session_state.secondary_pills_selection
                st.rerun()
        else:
            st.session_state.checkbox_minhas_lf = False
            st.session_state.checkbox_nao_respondidas_lf = False

        with col1:
            today = datetime.date.today()
            thirty_days_ago = today - datetime.timedelta(days=30)
            min_date_selectable = datetime.date(2020, 1, 1)
            
            # Simplificação do st.date_input
            DATE_INPUT_KEY = "date_input_lf_range_key" # Chave única para o widget
            if DATE_INPUT_KEY not in st.session_state:
                st.session_state[DATE_INPUT_KEY] = (thirty_days_ago + datetime.timedelta(days=1), today)

            # O widget usa e atualiza st.session_state[DATE_INPUT_KEY] diretamente
            # Se for preciso reagir à mudança aqui, um on_change callback pode ser usado.
            st.date_input(
                "Intervalo de Datas",
                min_value=min_date_selectable,
                max_value=today,
                format="DD/MM/YYYY",
                label_visibility='collapsed',
                key=DATE_INPUT_KEY # Passa a chave única
            )
            current_range_dates = st.session_state[DATE_INPUT_KEY]


            if isinstance(current_range_dates, (tuple, list)) and len(current_range_dates) == 2:
                data_inicio, data_fim = current_range_dates
            else:
                st.toast("🛑 :red[**Intervalo de datas inválido. Usando data de hoje.**]")
                data_inicio = data_fim = today

        if 'lf_df' not in st.session_state or st.session_state.lf_df is None or st.session_state.lf_df.empty:
            st.warning("Banco de LFs está vazio ou não carregado.")
            df_geral = pd.DataFrame()
        else:
            df_geral_source = st.session_state.lf_df.copy()
            df_geral_source['Status'] = df_geral_source['Status'].replace("", "Passivo")
            
            if status_para_filtragem:
                df_geral = df_geral_source[df_geral_source['Status'] == status_para_filtragem].copy()
            else:
                df_geral = df_geral_source

            if st.session_state.checkbox_minhas_lf:
                df_geral = df_geral[df_geral['Servidor'] == st.session_state.get("sessao_servidor")]
            if st.session_state.checkbox_nao_respondidas_lf:
                df_geral = df_geral[df_geral['Respondido'] == "Não"]

            if data_inicio and data_fim and not df_geral.empty and 'Data_Solicitacao_dt' in df_geral.columns:
                 df_geral.loc[:, 'Data_Solicitacao_dt'] = pd.to_datetime(df_geral['Data_Solicitacao_dt'], errors='coerce')
                 
                 df_geral = df_geral[
                    (df_geral['Data_Solicitacao_dt'].dt.date >= data_inicio) &
                    (df_geral['Data_Solicitacao_dt'].dt.date <= data_fim)
                ]

        if not df_geral.empty:
            try:
                cols_to_display_indices = [0, 1, 2, 4, 8, 7]
                actual_indices = [i for i in cols_to_display_indices if i < len(df_geral.columns)]
                lf_df_filtrado = df_geral.iloc[:, actual_indices].reset_index(drop=True)
                st.session_state.cpf_cnpj_col_name_in_lf_filtrado = None
                if "CPF / CNPJ" in lf_df_filtrado.columns:
                    st.session_state.cpf_cnpj_col_name_in_lf_filtrado = "CPF / CNPJ"
                elif len(actual_indices) > 3 and actual_indices[3] < len(df_geral.columns) and df_geral.columns[cols_to_display_indices[3]] == "CPF / CNPJ":
                    st.session_state.cpf_cnpj_col_name_in_lf_filtrado = "CPF / CNPJ"

            except IndexError as e:
                st.error(f"Erro ao selecionar colunas para a tabela de solicitações: {e}.")
                lf_df_filtrado = pd.DataFrame()
                st.session_state.cpf_cnpj_col_name_in_lf_filtrado = None
        else:
            expected_col_names_lf = []
            if 'lf_df' in st.session_state and st.session_state.lf_df is not None and not st.session_state.lf_df.empty:
                base_cols_lf = st.session_state.lf_df.columns
                indices_lf = [0, 1, 2, 4, 8, 7]
                for i_lf in indices_lf:
                    if i_lf < len(base_cols_lf): expected_col_names_lf.append(base_cols_lf[i_lf])
                    else: expected_col_names_lf.append(f"Coluna_{i_lf}")
            else:
                expected_col_names_lf = ["Cód. Solicitação", "Data Solicitação", "Tipo Processo", "CPF / CNPJ", "Setor", "Possível Divisão"]
            lf_df_filtrado = pd.DataFrame(columns=expected_col_names_lf)
            st.session_state.cpf_cnpj_col_name_in_lf_filtrado = "CPF / CNPJ" if "CPF / CNPJ" in expected_col_names_lf else (expected_col_names_lf[3] if len(expected_col_names_lf) > 3 else None)

        st.markdown("##### Solicitações de Licença")
        column_config_lf = {}
        headers_lf_display = ["Cód.", "Data", "Licença", "CPF / CNPJ", "Setor", "Div."]
        if not lf_df_filtrado.empty:
            for i, col_name_actual in enumerate(lf_df_filtrado.columns):
                header_name = headers_lf_display[i] if i < len(headers_lf_display) else col_name_actual
                column_config_lf[col_name_actual] = st.column_config.TextColumn(header_name)
        else:
            for i, col_name_fallback_lf in enumerate(lf_df_filtrado.columns):
                header_name_lf = headers_lf_display[i] if i < len(headers_lf_display) else col_name_fallback_lf
                column_config_lf[col_name_fallback_lf] = st.column_config.TextColumn(header_name_lf)

        LF_TABLE_KEY = "lf_table_selection"
        st.dataframe(
            lf_df_filtrado, key=LF_TABLE_KEY, on_select="rerun", selection_mode="single-row",
            column_config=column_config_lf, height=224, use_container_width=True, hide_index=True
        )
        
        # Lógica do Badge modificada
        total_exibido_lf = len(lf_df_filtrado)
        badge_text_lf = f"Exibindo: {total_exibido_lf}"
        if 'lf_df' in st.session_state and st.session_state.lf_df is not None and not st.session_state.lf_df.empty:
            base_df_for_badge_lf = st.session_state.lf_df.copy()
            base_df_for_badge_lf['Status'] = base_df_for_badge_lf['Status'].replace("", "Passivo")
            total_passivos_badge_lf = len(base_df_for_badge_lf[base_df_for_badge_lf['Status'] == 'Passivo'])
            
            if "Respondido" in base_df_for_badge_lf.columns:
                total_nao_respondidos_badge_lf = len(base_df_for_badge_lf[base_df_for_badge_lf['Respondido'] == 'Não'])
                # Novo formato do badge
                badge_text_lf += f"   ⬗   Passivo: {total_passivos_badge_lf}   ⬗   Não respondidos: {total_nao_respondidos_badge_lf}"
            else:
                badge_text_lf += f"   ⬗   Passivo: {total_passivos_badge_lf}   ⬗   Não respondidos: N/A"
            
            st.badge(badge_text_lf, color="blue")
        else:
            st.badge(f"Exibindo: {total_exibido_lf}   ⬗   Totais Gerais: N/A", color="grey")


        selected_row_lf_df = pd.DataFrame()
        original_selected_index_lf = None
        if LF_TABLE_KEY in st.session_state:
            selection = st.session_state[LF_TABLE_KEY].selection
            if selection.rows:
                selected_df_index = selection.rows[0]
                if selected_df_index < len(lf_df_filtrado):
                    selected_row_lf_df = lf_df_filtrado.iloc[[selected_df_index]]
                    if not selected_row_lf_df.empty and not df_geral.empty:
                        if lf_df_filtrado.columns.any() and df_geral.columns.any():
                            nome_coluna_codigo_lf_sel = lf_df_filtrado.columns[0]
                            cod_solicitacao_selecionado_lf_sel = selected_row_lf_df[nome_coluna_codigo_lf_sel].iloc[0]
                            coluna_codigo_em_df_geral_sel = df_geral.columns[0]
                            match_in_df_geral_sel = df_geral[df_geral[coluna_codigo_em_df_geral_sel] == cod_solicitacao_selecionado_lf_sel]
                            if not match_in_df_geral_sel.empty:
                                 original_selected_index_lf = match_in_df_geral_sel.index[0]
                        else:
                            st.warning("Não foi possível mapear a seleção devido à ausência de colunas em 'lf_df_filtrado' ou 'df_geral'.")
                else:
                    st.warning("Índice de seleção fora dos limites da tabela filtrada (solicitações).")

        if 'aggrid_gh_col2' not in st.session_state:
             st.session_state.aggrid_gh_col2 = pd.DataFrame()
        if 'lf_clear_clicked' not in st.session_state:
            st.session_state.lf_clear_clicked = False

    with coly:
        col1_y, col2_y = st.columns([0.5, 1.5], vertical_alignment="top")
        opcoes_filtro_dummy = ['Alfa', 'Beta', 'Gama', 'Delta']
        with col1_y:
            st.text_input("Teste 1 (desabilitado)", value="", disabled=True, label_visibility='collapsed', key="dummy_test1_coly")
        with col2_y:
            st.selectbox("Teste 2 (desabilitado)", opcoes_filtro_dummy, index=1, disabled=True, label_visibility='collapsed', key="dummy_test2_coly")

        lf_merged_df_hist_source = st.session_state.get('merged_df', pd.DataFrame()).copy()
        if 'df_geral_2025' not in st.session_state or st.session_state.df_geral_2025 is None:
            st.session_state.df_geral_2025 = load_df_2025()
        df_geral_2025_hist_source = st.session_state.df_geral_2025.copy()

        def prepare_hist_df(df, source_name):
            expected_cols = ['CPF / CNPJ', 'Protocolo', 'Data Criação', 'Tipo Processo']
            if df.empty:
                return pd.DataFrame(columns=expected_cols + ['OriginalRowIndex', 'Source', 'Index'])
            for col in expected_cols:
                if col not in df.columns: df[col] = pd.NA
            df_processed = df.reset_index()
            if 'index' in df_processed.columns: df_processed.rename(columns={'index': 'OriginalRowIndex'}, inplace=True)
            elif 'level_0' in df_processed.columns: df_processed.rename(columns={'level_0': 'OriginalRowIndex'}, inplace=True)
            else: df_processed['OriginalRowIndex'] = df_processed.index
            df_processed['Source'] = source_name
            df_processed['Index'] = source_name + '_' + df_processed['OriginalRowIndex'].astype(str)
            return df_processed

        df_geral_2025_hist = prepare_hist_df(df_geral_2025_hist_source, '2025')
        lf_merged_df_hist = prepare_hist_df(lf_merged_df_hist_source, 'Merged')
        allin_merged_df_hist = pd.DataFrame()

        if not selected_row_lf_df.empty and st.session_state.get('cpf_cnpj_col_name_in_lf_filtrado'):
            nome_coluna_cpf_cnpj_para_filtro_hist = st.session_state.cpf_cnpj_col_name_in_lf_filtrado
            if nome_coluna_cpf_cnpj_para_filtro_hist in selected_row_lf_df.columns:
                selected_cpf_cnpj_val_hist = selected_row_lf_df[nome_coluna_cpf_cnpj_para_filtro_hist].iloc[0]
                filtered_geral_2025_hist_result = pd.DataFrame()
                if "CPF / CNPJ" in df_geral_2025_hist.columns and not df_geral_2025_hist.empty:
                    filtered_geral_2025_hist_result = df_geral_2025_hist[df_geral_2025_hist['CPF / CNPJ'] == selected_cpf_cnpj_val_hist]
                filtered_lf_merged_df_hist_result = pd.DataFrame()
                if "CPF / CNPJ" in lf_merged_df_hist.columns and not lf_merged_df_hist.empty:
                    filtered_lf_merged_df_hist_result = lf_merged_df_hist[lf_merged_df_hist["CPF / CNPJ"] == selected_cpf_cnpj_val_hist]
                allin_merged_df_hist = pd.concat([filtered_geral_2025_hist_result, filtered_lf_merged_df_hist_result], ignore_index=True)

        hist_display_cols_ordered = ["Protocolo", "Data Criação", "CPF / CNPJ", "Tipo Processo", "Index"]
        if st.session_state.lf_clear_clicked:
            st.session_state.aggrid_gh_col2 = pd.DataFrame(columns=hist_display_cols_ordered)
            st.session_state.lf_clear_clicked = False
        else:
            if not allin_merged_df_hist.empty:
                for col_display in hist_display_cols_ordered:
                    if col_display not in allin_merged_df_hist.columns: allin_merged_df_hist[col_display] = pd.NA
                temp_df_hist_display = allin_merged_df_hist[hist_display_cols_ordered].copy()
                if "Data Criação" in temp_df_hist_display.columns:
                    temp_df_hist_display["Data Criação"] = pd.to_datetime(temp_df_hist_display["Data Criação"], format="%d/%m/%Y", errors="coerce")
                    temp_df_hist_display = temp_df_hist_display.sort_values(by="Data Criação", ascending=False)
                    temp_df_hist_display["Data Criação"] = temp_df_hist_display["Data Criação"].dt.strftime("%d/%m/%Y").fillna("")
                st.session_state.aggrid_gh_col2 = temp_df_hist_display
            else:
                st.session_state.aggrid_gh_col2 = pd.DataFrame(columns=hist_display_cols_ordered)

        st.markdown("##### Histórico do Contribuinte")
        column_config_merged = {
            "Index": None, "Protocolo": st.column_config.TextColumn("Protocolo"),
            "Data Criação": st.column_config.TextColumn("Data"), "CPF / CNPJ": st.column_config.TextColumn("CPF / CNPJ"),
            "Tipo Processo": st.column_config.TextColumn("Tipo Processo")
        }
        MERGED_TABLE_KEY = "merged_table_selection"
        current_gh_col2_df_display = st.session_state.aggrid_gh_col2.reset_index(drop=True)
        st.dataframe(
            current_gh_col2_df_display, key=MERGED_TABLE_KEY, on_select="rerun", selection_mode="single-row",
            column_config=column_config_merged, height=224, use_container_width=True, hide_index=True
        )
        total_exibido_hist = len(current_gh_col2_df_display)
        st.badge(f"Exibindo: {total_exibido_hist}", color="green")

        if 'sel_merged_lf' not in st.session_state: st.session_state.sel_merged_lf = pd.DataFrame()
        if MERGED_TABLE_KEY in st.session_state:
            selection_merged = st.session_state[MERGED_TABLE_KEY].selection
            if selection_merged.rows:
                selected_merged_df_index = selection_merged.rows[0]
                if selected_merged_df_index < len(current_gh_col2_df_display):
                    st.session_state.sel_merged_lf = current_gh_col2_df_display.iloc[[selected_merged_df_index]]
                else: st.session_state.sel_merged_lf = pd.DataFrame()
            else: st.session_state.sel_merged_lf = pd.DataFrame()

        @st.dialog("Detalhes do Processo", width="large")
        def show_data_dialog(selected_row_data_df_arg):
            if selected_row_data_df_arg.empty or 'Index' not in selected_row_data_df_arg.columns:
                st.warning("Nenhum dado selecionado ou 'Index' ausente para exibir detalhes.")
                return
            unique_id_val_dialog = selected_row_data_df_arg['Index'].iloc[0]
            df_to_process_dialog = pd.DataFrame()
            source_dfs_for_dialog = {
                '2025_': prepare_hist_df(st.session_state.df_geral_2025.copy(), '2025'),
                'Merged_': prepare_hist_df(st.session_state.get('merged_df', pd.DataFrame()).copy(), 'Merged')
            }
            for prefix, source_df_dialog in source_dfs_for_dialog.items():
                if isinstance(unique_id_val_dialog, str) and unique_id_val_dialog.startswith(prefix) and not source_df_dialog.empty and 'Index' in source_df_dialog.columns:
                    match_df_dialog = source_df_dialog[source_df_dialog['Index'] == unique_id_val_dialog]
                    if not match_df_dialog.empty:
                        df_to_process_dialog = match_df_dialog.copy()
                        if 'Valor' in df_to_process_dialog.columns:
                            df_to_process_dialog.loc[:, 'Valor'] = df_to_process_dialog['Valor'].apply(
                                lambda x: f'R$ {float(x):,.2f}' if pd.notnull(x) and isinstance(x, (int, float))
                                else (x if isinstance(x, str) and x.startswith('R$') else 'R$ 0,00')
                            )
                        break
            if df_to_process_dialog.empty and isinstance(unique_id_val_dialog, str):
                 st.warning(f"Não foi possível carregar detalhes. ID: {unique_id_val_dialog}.")
            if not df_to_process_dialog.empty:
                cols_to_drop_dialog = ['Source', 'OriginalRowIndex', 'Index']
                if 'index' in df_to_process_dialog.columns: cols_to_drop_dialog.append('index')
                df_to_display_final_dialog = df_to_process_dialog.drop(columns=[col for col in cols_to_drop_dialog if col in df_to_process_dialog.columns], errors='ignore')
                show_dadosProcesso(df_to_display_final_dialog)
            else: st.warning(f"Não foi possível encontrar os detalhes para o item selecionado (ID: {unique_id_val_dialog}).")

        if not st.session_state.sel_merged_lf.empty:
            if 'show_details_dialog_trigger' not in st.session_state: st.session_state.show_details_dialog_trigger = False
            if 'last_selected_merged_index' not in st.session_state: st.session_state.last_selected_merged_index = None
            current_sel_index_dialog = st.session_state.sel_merged_lf['Index'].iloc[0] if not st.session_state.sel_merged_lf.empty and 'Index' in st.session_state.sel_merged_lf.columns else None
            if current_sel_index_dialog is not None and current_sel_index_dialog != st.session_state.last_selected_merged_index:
                st.session_state.show_details_dialog_trigger = True
                st.session_state.last_selected_merged_index = current_sel_index_dialog
            elif current_sel_index_dialog is None: st.session_state.last_selected_merged_index = None
            if st.session_state.get('show_details_dialog_trigger', False):
                show_data_dialog(st.session_state.sel_merged_lf)
                st.session_state.show_details_dialog_trigger = False

if 'lf_empty_df' not in st.session_state:
    if 'lf_df' in st.session_state and st.session_state.lf_df is not None and not st.session_state.lf_df.empty:
        empty_series = pd.Series(index=st.session_state.lf_df.columns, dtype='object').fillna("")
    else:
        fallback_cols = ["Código Solicitação", "Data Solicitação", "Ocorrências", "Tipo Processo", "Setor", "Possível Divisão", "Razão Social", "CPF / CNPJ", "E-mail", "E-mail CC", "Docs. Mesclados 1", "Docs. Mesclados 2", "Observação", "Status", "Divisão", "GDOC", "Valor Manual", "Servidor", "Data Atendimento", "Data Modificação", "Motivo Indeferimento", "Respondido"]
        empty_series = pd.Series(index=fallback_cols, dtype='object').fillna("")
    st.session_state.lf_empty_df = empty_series
treated_line_lf = st.session_state.lf_empty_df.copy()

if original_selected_index_lf is not None and 'lf_df' in st.session_state and st.session_state.lf_df is not None and not st.session_state.lf_df.empty:
    if not selected_row_lf_df.empty and lf_df_filtrado.columns.any():
        cod_sol_para_buscar = selected_row_lf_df[lf_df_filtrado.columns[0]].iloc[0]
        col_codigo_principal = st.session_state.lf_df.columns[0] if st.session_state.lf_df.columns.any() else None
        if col_codigo_principal:
            linha_original_df = st.session_state.lf_df[st.session_state.lf_df[col_codigo_principal] == cod_sol_para_buscar]
            if not linha_original_df.empty:
                original_index_in_lf_df = linha_original_df.index[0]
                if original_index_in_lf_df < len(st.session_state.lf_df):
                    selected_line_series = st.session_state.lf_df.loc[original_index_in_lf_df]
                    treated_line_lf = selected_line_series.fillna("").copy()
                    st.session_state.selected_index_lf = original_index_in_lf_df
                else:
                    st.warning("Índice da linha original (mapeado) fora dos limites.")
                    st.session_state.selected_index_lf = None
            else:
                st.warning(f"Solicitação '{cod_sol_para_buscar}' não encontrada no DataFrame principal.")
                st.session_state.selected_index_lf = None
        else:
            st.warning("Coluna de código não identificada no DataFrame principal.")
            st.session_state.selected_index_lf = None
    else: st.session_state.selected_index_lf = None
else: st.session_state.selected_index_lf = None

if 'btn_clear_lf' not in st.session_state: st.session_state.btn_clear_lf = False
if st.session_state.btn_clear_lf:
    treated_line_lf = st.session_state.lf_empty_df.copy()
    st.session_state.btn_clear_lf = False
    if LF_TABLE_KEY in st.session_state and hasattr(st.session_state[LF_TABLE_KEY], 'selection'):
         st.session_state[LF_TABLE_KEY].selection.rows = []
    if MERGED_TABLE_KEY in st.session_state and hasattr(st.session_state[MERGED_TABLE_KEY], 'selection'):
         st.session_state[MERGED_TABLE_KEY].selection.rows = []
    st.session_state.sel_merged_lf = pd.DataFrame()
    st.session_state.last_selected_merged_index = None
    original_selected_index_lf = None
    st.session_state.selected_index_lf = None

show_expander_2 = bool("Código Solicitação" in treated_line_lf and len(str(treated_line_lf.get("Código Solicitação",""))) > 1)
with st.expander("Detalhes da solicitação", expanded=show_expander_2):
    st.write("")
    with st.form("form_licencas", border=False):
        container1, container2 = st.columns(2, gap="large")
        with container1:
            col1_form, col2_form, col3_form, col4_form = st.columns([0.3, 0.6, 1, 1.4], vertical_alignment="bottom")
            status_icon = ":material/pending:"
            if "Respondido" in treated_line_lf:
                if treated_line_lf.get("Respondido") == "Sim": status_icon = ":material/check_circle:"
                elif treated_line_lf.get("Respondido") == "Não": status_icon = ":material/do_not_disturb_on:"
            col1_form.header(status_icon, anchor=False)
            codigo_solicitacao_lf_form_input = col2_form.text_input("Cód. Solicitação", value=treated_line_lf.get("Código Solicitação", ""), key="form_cod_sol_input")
            data_solicitacao_lf = col3_form.text_input("Data Solicitação", value=treated_line_lf.get("Data Solicitação", ""), key="form_data_sol")
            
            ocorrencias_lf_val = treated_line_lf.get("Ocorrências", "")
            btn_ocorrencias_label = f"{ocorrencias_lf_val} 👁️" if ocorrencias_lf_val else "Ocorrências 👁️"
            btn_ocorrencias_disabled = not bool(ocorrencias_lf_val)
            btn_ocorrencias = col4_form.form_submit_button(btn_ocorrencias_label, type="primary", use_container_width=True, disabled=btn_ocorrencias_disabled, help="Ver Ocorrências")
            
            if btn_ocorrencias: 
                get_ocorrencias(treated_line_lf.get("CPF / CNPJ", ""), "lf")

            col1_c1_form, col2_c1_form, col3_c1_form = st.columns(3, vertical_alignment="bottom")
            tipo_processo_lf = col1_c1_form.text_input("Tipo Processo", value=treated_line_lf.get("Tipo Processo", ""),key="form_tipo_proc")
            tipo_empresa_lf = col2_c1_form.text_input("Setor", value=treated_line_lf.get("Setor", ""), key="form_setor")
            divisao_declarada_lf = col3_c1_form.text_input("Possível Divisão", value=treated_line_lf.get("Possível Divisão", ""), key="form_poss_div")
            col1_c1_2_form, col2_c1_2_form, col3_c1_2_form = st.columns([1.5,1,0.5], vertical_alignment="bottom")
            cpf_cnpj_val = treated_line_lf.get("CPF / CNPJ", "")
            btn_cnpj_lf_disabled = not (len(str(cpf_cnpj_val)) == 18 or len(str(cpf_cnpj_val)) == 14)
            razao_social_lf = col1_c1_2_form.text_input("Nome Estab.", value=treated_line_lf.get("Razão Social", ""), key="form_razao_social")
            cpf_cnpj_lf_input = col2_c1_2_form.text_input("CPF / CNPJ", value=cpf_cnpj_val, key="form_cpf_cnpj")
            btn_cnpj_lf = col3_c1_2_form.form_submit_button("🔎", use_container_width=True, disabled=btn_cnpj_lf_disabled, help="Buscar CNPJ/CPF")
            if btn_cnpj_lf:
                if not btn_cnpj_lf_disabled: get_cnpj(cpf_cnpj_lf_input, '', '')
                else: st.toast(":orange[CNPJ/CPF inválido para busca.]")
            col1_c1_3_form, col2_c1_3_form = st.columns(2, vertical_alignment="bottom")
            email1_lf = col1_c1_3_form.text_input("E-mail", value=treated_line_lf.get("E-mail", ""), key="form_email1")
            email2_lf = col2_c1_3_form.text_input("E-mail CC", value=treated_line_lf.get("E-mail CC", ""), key="form_email2")
            st.write("")
            col1_c1_4_form, col2_c1_4_form = st.columns(2, vertical_alignment="bottom")
            col_btn_list_form = [col1_c1_4_form, col2_c1_4_form]; col_idx_form = 0
            for header_url_key_form in ["Docs. Mesclados 1", "Docs. Mesclados 2"]:
                url_val_form = treated_line_lf.get(header_url_key_form)
                if isinstance(url_val_form, str) and url_val_form.startswith("http"):
                    col_btn_list_form[col_idx_form].link_button(f"🔗 Abrir {header_url_key_form.replace('Docs. Mesclados ','Doc ')}", url_val_form, use_container_width=True)
                    col_idx_form = (col_idx_form + 1) % 2
            observacao_lf_val_form = treated_line_lf.get("Observação", "")
            observacao_lf_input = st.text_area("Observação", value=observacao_lf_val_form, height=77, key="form_obs")
        with container2:
            col1_c2_form, col2_c2_form, col3_c2_form, col4_c2_form = st.columns(4, vertical_alignment="bottom")
            status_options_form_sel = ['Passivo', 'Deferido', 'Indeferido', '']
            current_status_form_val = treated_line_lf.get("Status", "")
            status_index_lf_form = status_options_form_sel.index(current_status_form_val) if current_status_form_val in status_options_form_sel else 3
            status_lf_selectbox = col1_c2_form.selectbox("Status *", status_options_form_sel, index=status_index_lf_form, key="form_status_lf_sel")
            disable_file_uploader_form = True; disable_btn_save_lf_form = True; disable_btn_send_lf_form = True
            if status_lf_selectbox == 'Passivo' or not status_lf_selectbox: disable_btn_save_lf_form = False
            elif status_lf_selectbox == 'Deferido': disable_file_uploader_form = False; disable_btn_save_lf_form = False; disable_btn_send_lf_form = False
            elif status_lf_selectbox == 'Indeferido': disable_btn_save_lf_form = False; disable_btn_send_lf_form = False
            divisao_options_form_sel = ['DVSA', 'DVSE', 'DVSCEP', 'DVSDM', '']
            current_divisao_form_val = treated_line_lf.get("Divisão", "")
            divisao_index_form = divisao_options_form_sel.index(current_divisao_form_val) if current_divisao_form_val in divisao_options_form_sel else 4
            divisao_lf_selectbox = col2_c2_form.selectbox("Divisão *", divisao_options_form_sel, index=divisao_index_form, key="form_divisao_lf_sel")
            gdoc_lf_input = col3_c2_form.text_input("GDOC/Ano (xx/AA) *", value=treated_line_lf.get("GDOC", ""), key="form_gdoc_lf_input")
            valor_manual_val_form = treated_line_lf.get("Valor Manual", "R$ 0,00")
            if treated_line_lf.get("Setor", "") not in ['', 'Privado']: valor_manual_val_form = 'R$ 0,00'
            valor_manual_lf_input = col4_c2_form.text_input("Valor do DAM *", value=valor_manual_val_form, key="form_valor_manual_lf_input")
            col1_c2_2_form, col2_c2_2_form, col3_c2_2_form = st.columns(3, vertical_alignment="bottom")
            servidor_lf_input_form = col1_c2_2_form.text_input("Servidor", value=treated_line_lf.get("Servidor", st.session_state.get("sessao_servidor", "")), key="form_servidor_lf_input_display") 
            data_atendimento_lf_val_form = treated_line_lf.get("Data Atendimento", "")
            data_atendimento_lf_input = col2_c2_2_form.text_input("Data At.", value=data_atendimento_lf_val_form, key="form_data_at_lf_input")
            data_modificacao_lf_input = col3_c2_2_form.text_input("Data Mod.", value=treated_line_lf.get("Data Modificação", ""), key="form_data_mod_lf_input")
            cartao_protocolo_lf_uploader = st.file_uploader("Anexar Cartão do Protocolo *", accept_multiple_files=False, type=['pdf'], disabled=disable_file_uploader_form, key="form_file_uploader_lf_up")
            motivo_indeferimento_lf_input = st.text_area("Motivo Indeferimento *", value=treated_line_lf.get("Motivo Indeferimento", ""), height=77, key="form_motivo_ind_lf_input")
            st.write("")
            form_col1_btn, form_col2_btn, form_col3_btn, form_col4_btn, form_col5_btn = st.columns(5, vertical_alignment="bottom", gap='small')
            btn_clear_lf_form = form_col4_btn.form_submit_button("🧹 Limpar", use_container_width=True)
            btn_save_lf_form = form_col5_btn.form_submit_button("💾 Salvar", use_container_width=True, disabled=disable_btn_save_lf_form, type='primary')
            btn_send_lf_form = form_col3_btn.form_submit_button("📧 Enviar", use_container_width=True, disabled=disable_btn_send_lf_form, type='primary')
            form_col2_btn.link_button("📋 Checklist", "https://sites.google.com/view/secretariadevisa/in%C3%ADcio/processos/requisitos?authuser=0", use_container_width=True)
            form_col1_btn.link_button("🌍 GDOC", "https://gdoc.belem.pa.gov.br/gdocprocessos/processo/pesquisarInteressado", use_container_width=True)
            btn_gdoc_webdriver_form = None
            if st.session_state.get('auth_user') == 'Daniel': btn_gdoc_webdriver_form = st.form_submit_button('🤖 sGDOC', use_container_width=True)
            if 'toast_msg_success' not in st.session_state: st.session_state.toast_msg_success = False
            if st.session_state.toast_msg_success: st.toast(f"Dados salvos ✨✨"); st.session_state.toast_msg_success = False
            
            def btn_clear_fn_form_action(rerun=True):
                st.session_state.btn_clear_lf = True
                st.session_state.reload_lf_df = True
                load_lf_df_cached.clear()
                if rerun: st.rerun()
            
            if btn_clear_lf_form: btn_clear_fn_form_action(rerun=True)
            
            if btn_save_lf_form:
                if codigo_solicitacao_lf_form_input and tipo_processo_lf:
                    with st.spinner("Salvando dados, aguarde..."):
                        divisao_list_save = ['DVSA', 'DVSE', 'DVSCEP', 'DVSDM']
                        
                        string_formatada_dam_save = extrair_e_formatar_real(valor_manual_lf_input)
                        valor_numerico_convertido_dam_save = None
                        cond_valor_dam_ok_para_deferido_save = False

                        if string_formatada_dam_save and isinstance(string_formatada_dam_save, str) and string_formatada_dam_save.strip() != "":
                            try:
                                str_para_float = string_formatada_dam_save.replace("R$", "").strip()
                                if '.' in str_para_float and ',' in str_para_float:
                                    str_para_float = str_para_float.replace('.', '').replace(',', '.')
                                elif ',' in str_para_float:
                                    str_para_float = str_para_float.replace(',', '.')
                                valor_numerico_convertido_dam_save = float(str_para_float)
                                if valor_numerico_convertido_dam_save >= 0:
                                    cond_valor_dam_ok_para_deferido_save = True
                            except ValueError:
                                pass 
                        
                        gdoc_is_valid_save = validate_gdoc(gdoc_lf_input, data_solicitacao_lf)

                        save_condition_deferido = (status_lf_selectbox == "Deferido" and 
                                                   gdoc_is_valid_save and 
                                                   divisao_lf_selectbox in divisao_list_save and 
                                                   cond_valor_dam_ok_para_deferido_save)
                        save_condition_indeferido = (status_lf_selectbox == "Indeferido" and len(motivo_indeferimento_lf_input or "") > 10)
                        save_condition_passivo = (status_lf_selectbox == "Passivo")

                        if save_condition_deferido or save_condition_indeferido or save_condition_passivo:
                            worksheet_save = get_worksheet(2, st.secrets['sh_keys']['geral_major'])
                            cell_save = worksheet_save.find(codigo_solicitacao_lf_form_input, in_column=1) 
                            
                            if cell_save:
                                data_atendimento_to_save = data_atendimento_lf_val_form
                                if not worksheet_save.acell(f'S{cell_save.row}').value:
                                     data_atendimento_to_save = get_current_datetime()
                                
                                data_modificacao_to_save = get_current_datetime()
                                current_gdoc_link_cartao_save = worksheet_save.acell(f'V{cell_save.row}').value or ""
                                current_respondido_save = worksheet_save.acell(f'Y{cell_save.row}').value or "Não"
                                
                                valor_dam_para_planilha = string_formatada_dam_save if string_formatada_dam_save else valor_manual_lf_input
                                if status_lf_selectbox != "Deferido" and not string_formatada_dam_save:
                                    valor_dam_para_planilha = valor_manual_lf_input
                                elif status_lf_selectbox == "Deferido" and not cond_valor_dam_ok_para_deferido_save:
                                    valor_dam_para_planilha = valor_manual_lf_input
                                
                                servidor_a_salvar = st.session_state.get("sessao_servidor", "")

                                values_to_update_save = [
                                    codigo_solicitacao_lf_form_input,
                                    valor_dam_para_planilha,
                                    status_lf_selectbox,
                                    servidor_a_salvar,
                                    data_atendimento_to_save,
                                    data_modificacao_to_save,
                                    motivo_indeferimento_lf_input,
                                    current_gdoc_link_cartao_save,
                                    gdoc_lf_input, 
                                    divisao_lf_selectbox,
                                    current_respondido_save
                                ]
                                range_to_update_save = f"O{cell_save.row}:Y{cell_save.row}"
                                worksheet_save.update(range_name=range_to_update_save, values=[values_to_update_save])

                                st.session_state.reload_lf_df = True
                                if status_lf_selectbox in ["Deferido", "Indeferido"]:
                                    st.session_state.reload_tx_df = True
                                st.session_state.toast_msg_success = True
                                btn_clear_fn_form_action(rerun=True) 
                            else:
                                st.error(f"Código de Solicitação '{codigo_solicitacao_lf_form_input}' não encontrado na planilha para salvar.")
                        else: 
                            if status_lf_selectbox == "Deferido":
                                if not gdoc_is_valid_save: st.toast(f"GDOC deve ser xx/AA (ex: {datetime.datetime.now().strftime('%y')}).")
                                elif not (divisao_lf_selectbox in divisao_list_save): st.toast("Divisão inválida para Deferimento.")
                                elif not cond_valor_dam_ok_para_deferido_save:
                                    st.toast("Para Deferimento, o Valor do DAM é obrigatório e deve ser um valor monetário válido (ex: R$ 0,00 ou 150,25).")
                            elif status_lf_selectbox == "Indeferido" and not (len(motivo_indeferimento_lf_input or "") > 10): 
                                st.toast("Motivo do indeferimento muito curto.")
                else:
                    st.toast("Erro. Código da Solicitação e Tipo de Processo são obrigatórios.")
            
            if 'is_email_sended_lf' not in st.session_state: st.session_state.is_email_sended_lf = False
            
            def mark_email_as_sent_form_action():
                worksheet_email = get_worksheet(2, st.secrets['sh_keys']['geral_major'])
                cell_email = worksheet_email.find(codigo_solicitacao_lf_form_input, in_column=1) 
                if cell_email:
                    link_do_cartao_gdrive = st.session_state.get("gdrive_link_do_cartao", "")
                    if link_do_cartao_gdrive: 
                        worksheet_email.update_acell(f'V{cell_email.row}', link_do_cartao_gdrive)
                    worksheet_email.update_acell(f'Y{cell_email.row}', "Sim")
                st.session_state.reload_lf_df = True
                if status_lf_selectbox in ["Deferido", "Indeferido"]:
                    st.session_state.reload_tx_df = True
                load_lf_df_cached.clear() 
                st.session_state.is_email_sended_lf = False
                st.session_state.pop("gdrive_link_do_cartao", None); btn_clear_fn_form_action(rerun=True)
            
            def send_mail_form_action():
                email_licenciamento(
                    kw_status=status_lf_selectbox, kw_gdoc=gdoc_lf_input, kd_divisao=divisao_lf_selectbox, 
                    kw_protocolo=codigo_solicitacao_lf_form_input, 
                    kw_data_sol=data_solicitacao_lf, 
                    kw_tipo_proc=f'Licenciamento Sanitário ({tipo_processo_lf})', 
                    kw_razao_social=razao_social_lf, kw_cpf_cnpj=cpf_cnpj_lf_input, 
                    kw_cartao_protocolo=cartao_protocolo_lf_uploader, 
                    kw_email1=email1_lf, kw_email2=email2_lf, 
                    kw_motivo_indeferimento=motivo_indeferimento_lf_input
                )
            
            if btn_send_lf_form:
                if codigo_solicitacao_lf_form_input and tipo_processo_lf:
                    valid_gdoc_for_send_act = validate_gdoc(gdoc_lf_input, data_solicitacao_lf)
                    valid_protocol_file_for_send_act = False
                    if cartao_protocolo_lf_uploader is not None: 
                        valid_protocol_file_for_send_act = validate_protocolo(cartao_protocolo_lf_uploader.name, gdoc_lf_input)
                    
                    valor_manual_ok_for_send_act = False
                    if status_lf_selectbox == "Deferido":
                        string_formatada_dam_send = extrair_e_formatar_real(valor_manual_lf_input)
                        if string_formatada_dam_send and isinstance(string_formatada_dam_send, str) and string_formatada_dam_send.strip() != "":
                            try:
                                str_para_float_send = string_formatada_dam_send.replace("R$", "").strip()
                                if '.' in str_para_float_send and ',' in str_para_float_send:
                                    str_para_float_send = str_para_float_send.replace('.', '').replace(',', '.')
                                elif ',' in str_para_float_send:
                                    str_para_float_send = str_para_float_send.replace(',', '.')
                                
                                valor_numerico_convertido_dam_send = float(str_para_float_send)
                                if valor_numerico_convertido_dam_send >= 0:
                                    valor_manual_ok_for_send_act = True
                            except ValueError:
                                pass
                    
                    send_cond_deferido_act = (status_lf_selectbox == "Deferido" and 
                                               divisao_lf_selectbox in ['DVSA', 'DVSE', 'DVSCEP', 'DVSDM'] and 
                                               valid_gdoc_for_send_act and cartao_protocolo_lf_uploader is not None and 
                                               valid_protocol_file_for_send_act and valor_manual_ok_for_send_act)
                    send_cond_indeferido_act = (status_lf_selectbox == "Indeferido" and len(motivo_indeferimento_lf_input or "") > 10)

                    if send_cond_deferido_act or send_cond_indeferido_act:
                        st.toast(f"Tentando responder à '{codigo_solicitacao_lf_form_input}'. Aguarde...")
                        send_mail_form_action()
                        if st.session_state.is_email_sended_lf: mark_email_as_sent_form_action()
                    else:
                        if status_lf_selectbox == "Deferido":
                            if not (divisao_lf_selectbox in ['DVSA', 'DVSE', 'DVSCEP', 'DVSDM']): st.toast(":red[Divisão inválida para envio.]")
                            if not valid_gdoc_for_send_act: st.toast(f":red[Formato do GDOC inválido (xx/{datetime.datetime.now().strftime('%y')})]")
                            if cartao_protocolo_lf_uploader is None: st.toast(":red[Cartão do protocolo não anexado.]")
                            elif not valid_protocol_file_for_send_act: st.toast(":red[Nome do arquivo do protocolo não corresponde ao GDOC.]")
                            if not valor_manual_ok_for_send_act: 
                                st.toast(":red[Para Deferimento, Valor do DAM não preenchido ou inválido (deve ser um valor monetário >= R$ 0,00).]")
                        if status_lf_selectbox == "Indeferido" and not (len(motivo_indeferimento_lf_input or "") > 10): 
                            st.toast(":red[Motivo do indeferimento muito curto para envio.]")
                else: st.toast(":red[Erro. Código da Solicitação e Tipo de Processo são obrigatórios para envio.]")
            
            if btn_gdoc_webdriver_form:
                if cpf_cnpj_lf_input and divisao_lf_selectbox:
                    selenium_proc_gdoc(kw_cpf_cnpj=cpf_cnpj_lf_input, kw_razao_social=razao_social_lf, kw_email1=email1_lf, kw_email2=email2_lf, kw_tipoProc=tipo_processo_lf, kw_divisao=divisao_lf_selectbox, kw_docs1=treated_line_lf.get("Docs. Mesclados 1", ""), kw_docs2=treated_line_lf.get("Docs. Mesclados 2", ""), kw_obs=observacao_lf_input)
                else: st.toast(":red[**CPF/CNPJ e Divisão são necessários para sGDOC.**]")