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
            
            DATE_INPUT_KEY = "date_input_lf_range_key" 
            if DATE_INPUT_KEY not in st.session_state:
                st.session_state[DATE_INPUT_KEY] = (thirty_days_ago + datetime.timedelta(days=1), today)

            st.date_input(
                "Intervalo de Datas",
                min_value=min_date_selectable,
                max_value=today,
                format="DD/MM/YYYY",
                label_visibility='collapsed',
                key=DATE_INPUT_KEY
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
                # Se status_para_filtragem for None ou vazio, mostrar todos (já que "" foi substituído por "Passivo")
                # Ou, se preferir não filtrar por status algum, pode-se usar df_geral_source.copy()
                # Para manter a lógica de que um filtro vazio deveria mostrar tudo, mas como "" virou "Passivo",
                # o comportamento aqui pode precisar de ajuste dependendo do desejado para um status_para_filtragem "vazio".
                # Assumindo que 'Passivo' é o default se nada for selecionado explicitamente no filtro pills.
                df_geral = df_geral_source[df_geral_source['Status'] == 'Passivo'].copy()


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
                # Correção: o índice original era 3, que corresponde à coluna 4 (CPF/CNPJ)
                elif len(actual_indices) > 3 and cols_to_display_indices[3] < len(df_geral.columns) and df_geral.columns[cols_to_display_indices[3]] == "CPF / CNPJ":
                     st.session_state.cpf_cnpj_col_name_in_lf_filtrado = "CPF / CNPJ"


            except IndexError as e:
                st.error(f"Erro ao selecionar colunas para a tabela de solicitações: {e}.")
                lf_df_filtrado = pd.DataFrame()
                st.session_state.cpf_cnpj_col_name_in_lf_filtrado = None
        else:
            expected_col_names_lf = []
            if 'lf_df' in st.session_state and st.session_state.lf_df is not None and not st.session_state.lf_df.empty:
                base_cols_lf = st.session_state.lf_df.columns
                indices_lf = [0, 1, 2, 4, 8, 7] # Cód, DataSol, TipoProc, Setor, Divisão, CNPJ
                for i_lf in indices_lf:
                    if i_lf < len(base_cols_lf): expected_col_names_lf.append(base_cols_lf[i_lf])
                    else: expected_col_names_lf.append(f"Coluna_{i_lf}")
            else:
                expected_col_names_lf = ["Cód. Solicitação", "Data Solicitação", "Tipo Processo", "CPF / CNPJ", "Setor", "Possível Divisão"]
            lf_df_filtrado = pd.DataFrame(columns=expected_col_names_lf)
            # Ajuste para garantir que o nome da coluna CPF/CNPJ seja pego corretamente
            st.session_state.cpf_cnpj_col_name_in_lf_filtrado = "CPF / CNPJ" if "CPF / CNPJ" in expected_col_names_lf else (expected_col_names_lf[3] if len(expected_col_names_lf) > 3 and expected_col_names_lf[3] == "CPF / CNPJ" else None)


        column_config_lf = {}
        headers_lf_display = ["Cód.", "Data", "Licença", "CPF / CNPJ", "Setor", "Div."]
        if not lf_df_filtrado.empty:
            for i, col_name_actual in enumerate(lf_df_filtrado.columns):
                header_name = headers_lf_display[i] if i < len(headers_lf_display) else col_name_actual
                column_config_lf[col_name_actual] = st.column_config.TextColumn(header_name)
        else:
            # Use expected_col_names_lf se lf_df_filtrado estiver vazio, pois suas colunas foram definidas
            for i, col_name_fallback_lf in enumerate(expected_col_names_lf):
                header_name_lf = headers_lf_display[i] if i < len(headers_lf_display) else col_name_fallback_lf
                column_config_lf[col_name_fallback_lf] = st.column_config.TextColumn(header_name_lf)


        LF_TABLE_KEY = "lf_table_selection"
        st.dataframe(
            lf_df_filtrado, key=LF_TABLE_KEY, on_select="rerun", selection_mode="single-row",
            column_config=column_config_lf, height=142, use_container_width=True, hide_index=True, 
        )
        
        total_exibido_lf = len(lf_df_filtrado)
        badge_text_lf = f"Exibindo: {total_exibido_lf}"
        if 'lf_df' in st.session_state and st.session_state.lf_df is not None and not st.session_state.lf_df.empty:
            base_df_for_badge_lf = st.session_state.lf_df.copy()
            base_df_for_badge_lf['Status'] = base_df_for_badge_lf['Status'].replace("", "Passivo")
            total_passivos_badge_lf = len(base_df_for_badge_lf[base_df_for_badge_lf['Status'] == 'Passivo'])
            
            if "Respondido" in base_df_for_badge_lf.columns:
                total_nao_respondidos_badge_lf = len(base_df_for_badge_lf[base_df_for_badge_lf['Respondido'] == 'Não'])
                badge_text_lf += f" ~ Passivo: {total_passivos_badge_lf} ~ Não respondidos: {total_nao_respondidos_badge_lf}"
            else:
                badge_text_lf += f" ~ Passivo: {total_passivos_badge_lf} ~ Não respondidos: N/A"
            
            st.badge(badge_text_lf, color="blue")
        else:
            st.badge(f"Exibindo: {total_exibido_lf} ~ Total Geral: N/A", color="grey")


        selected_row_lf_df = pd.DataFrame()
        original_selected_index_lf = None
        if LF_TABLE_KEY in st.session_state:
            selection = st.session_state[LF_TABLE_KEY].selection
            if selection.rows:
                selected_df_index = selection.rows[0]
                if selected_df_index < len(lf_df_filtrado):
                    selected_row_lf_df = lf_df_filtrado.iloc[[selected_df_index]]
                    if not selected_row_lf_df.empty and not df_geral.empty:
                        # Certifique-se de que as colunas existem antes de acessá-las
                        if not lf_df_filtrado.empty and not df_geral.empty and lf_df_filtrado.columns.any() and df_geral.columns.any():
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
            st.session_state.df_geral_2025 = load_df_2025() # Supondo que load_df_2025() exista
        df_geral_2025_hist_source = st.session_state.df_geral_2025.copy() if st.session_state.df_geral_2025 is not None else pd.DataFrame()


        def prepare_hist_df(df, source_name):
            expected_cols = ['CPF / CNPJ', 'Protocolo', 'Data Criação', 'Tipo Processo']
            if df.empty:
                return pd.DataFrame(columns=expected_cols + ['OriginalRowIndex', 'Source', 'Index'])
            
            # Garantir que as colunas esperadas existam
            for col in expected_cols:
                if col not in df.columns: df[col] = pd.NA
            
            # Evitar resetar index se já for RangeIndex e não tiver nome 'index' ou 'level_0'
            df_processed = df.copy()
            if not isinstance(df_processed.index, pd.RangeIndex) or 'index' in df_processed.columns or 'level_0' in df_processed.columns:
                df_processed = df_processed.reset_index()

            if 'index' in df_processed.columns and 'OriginalRowIndex' not in df_processed.columns :
                df_processed.rename(columns={'index': 'OriginalRowIndex'}, inplace=True)
            elif 'level_0' in df_processed.columns and 'OriginalRowIndex' not in df_processed.columns:
                df_processed.rename(columns={'level_0': 'OriginalRowIndex'}, inplace=True)
            elif 'OriginalRowIndex' not in df_processed.columns: # Se não houver coluna de índice após reset, use o novo índice
                 df_processed['OriginalRowIndex'] = df_processed.index

            df_processed['Source'] = source_name
            df_processed['Index'] = source_name + '_' + df_processed['OriginalRowIndex'].astype(str)
            return df_processed[expected_cols + ['OriginalRowIndex', 'Source', 'Index']]


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
                # Garantir que todas as colunas de display existam antes de tentar acessá-las
                for col_display in hist_display_cols_ordered:
                    if col_display not in allin_merged_df_hist.columns: 
                        allin_merged_df_hist[col_display] = pd.NA # Ou string vazia, dependendo do tipo esperado
                
                temp_df_hist_display = allin_merged_df_hist[hist_display_cols_ordered].copy()
                if "Data Criação" in temp_df_hist_display.columns:
                    temp_df_hist_display["Data Criação"] = pd.to_datetime(temp_df_hist_display["Data Criação"], format="%d/%m/%Y", errors="coerce")
                    temp_df_hist_display = temp_df_hist_display.sort_values(by="Data Criação", ascending=False)
                    temp_df_hist_display["Data Criação"] = temp_df_hist_display["Data Criação"].dt.strftime("%d/%m/%Y").fillna("")
                st.session_state.aggrid_gh_col2 = temp_df_hist_display
            else:
                st.session_state.aggrid_gh_col2 = pd.DataFrame(columns=hist_display_cols_ordered)

        column_config_merged = {
            "Index": None, "Protocolo": st.column_config.TextColumn("Protocolo"),
            "Data Criação": st.column_config.TextColumn("Data"), "CPF / CNPJ": st.column_config.TextColumn("CPF / CNPJ"),
            "Tipo Processo": st.column_config.TextColumn("Tipo Processo")
        }
        MERGED_TABLE_KEY = "merged_table_selection"
        current_gh_col2_df_display = st.session_state.aggrid_gh_col2.reset_index(drop=True)
        st.dataframe(
            current_gh_col2_df_display, key=MERGED_TABLE_KEY, on_select="rerun", selection_mode="single-row",
            column_config=column_config_merged, height=142, use_container_width=True, hide_index=True
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
            
            # DataFrames originais (com todas as colunas)
            df_geral_2025_dialog_src = st.session_state.df_geral_2025.copy() if st.session_state.df_geral_2025 is not None else pd.DataFrame()
            merged_df_dialog_src = st.session_state.get('merged_df', pd.DataFrame()).copy()

            # DataFrames preparados (com colunas selecionadas por prepare_hist_df), usados para encontrar o OriginalRowIndex
            prepared_source_dfs_for_dialog = {
                '2025_': prepare_hist_df(df_geral_2025_dialog_src.copy(), '2025'), # Passar cópias para prepare_hist_df
                'Merged_': prepare_hist_df(merged_df_dialog_src.copy(), 'Merged')
            }

            full_row_data_series = None

            for prefix, prepared_source_df in prepared_source_dfs_for_dialog.items():
                if isinstance(unique_id_val_dialog, str) and unique_id_val_dialog.startswith(prefix):
                    if not prepared_source_df.empty and 'Index' in prepared_source_df.columns and 'OriginalRowIndex' in prepared_source_df.columns:
                        match_in_prepared_df = prepared_source_df[prepared_source_df['Index'] == unique_id_val_dialog]
                        
                        if not match_in_prepared_df.empty:
                            original_row_index_value = match_in_prepared_df['OriginalRowIndex'].iloc[0]
                            
                            # Determinar qual DataFrame original usar
                            target_original_df = None
                            if prefix == '2025_':
                                target_original_df = df_geral_2025_dialog_src
                            elif prefix == 'Merged_':
                                target_original_df = merged_df_dialog_src

                            if target_original_df is not None and not target_original_df.empty:
                                try:
                                    # OriginalRowIndex pode ser um número (se o índice original era numérico e foi preservado ou resetado para numérico)
                                    # ou uma string/outro tipo se o índice original era assim e foi capturado como string.
                                    # Tentamos converter para int para .iloc, que espera um inteiro posicional.
                                    # Isso assume que OriginalRowIndex é um índice posicional após o reset_index em prepare_hist_df.
                                    idx_val_int = int(original_row_index_value)
                                    if 0 <= idx_val_int < len(target_original_df):
                                        full_row_data_series = target_original_df.iloc[idx_val_int]
                                    else:
                                        st.warning(f"Índice Original {idx_val_int} fora dos limites para o DataFrame de origem (prefixo: {prefix}).")
                                except ValueError:
                                    # Se OriginalRowIndex não for um int (p.ex., se era um ID de string antes do reset_index)
                                    # e o DataFrame original ainda tiver esse índice nomeado, podemos tentar .loc
                                    # No entanto, prepare_hist_df faz reset_index, então .iloc é mais provável.
                                    # Este bloco é um placeholder para lógica de fallback se .iloc falhar devido ao tipo de índice.
                                    st.warning(f"Não foi possível converter OriginalRowIndex '{original_row_index_value}' para int para usar com .iloc. Tentando .loc como fallback (pode não funcionar como esperado).")
                                    try:
                                        if original_row_index_value in target_original_df.index:
                                            full_row_data_series = target_original_df.loc[original_row_index_value]
                                        else:
                                            st.warning(f"Índice Original '{original_row_index_value}' não encontrado com .loc no DataFrame de origem.")
                                    except Exception as e_loc:
                                        st.error(f"Erro ao tentar .loc com índice '{original_row_index_value}': {e_loc}")
                                except IndexError:
                                    st.warning(f"Índice Original {original_row_index_value} (convertido para {idx_val_int}) resultou em IndexError.")
                                except Exception as e:
                                    st.error(f"Erro inesperado ao buscar linha original: {e}")
                            break # Saímos do loop pois encontramos o prefixo e tentamos buscar o dado
            
            if full_row_data_series is not None:
                record_dict = full_row_data_series.to_dict()
                
                # Aplicar formatação da coluna 'Valor' se existir (como na sua lógica original)
                if 'Valor' in record_dict:
                    valor = record_dict['Valor']
                    if pd.notnull(valor) and isinstance(valor, (int, float)):
                        record_dict['Valor'] = f'R$ {float(valor):,.2f}'
                    elif not (isinstance(valor, str) and valor.startswith('R$')):
                         record_dict['Valor'] = 'R$ 0,00' # Ou outra formatação padrão

                st.json(record_dict)
            else:
                st.warning(f"Não foi possível encontrar ou carregar os detalhes completos para o item selecionado (ID: {unique_id_val_dialog}). Pode ser que o OriginalRowIndex não tenha sido mapeado corretamente ou o DataFrame de origem esteja vazio/alterado.")

        if not st.session_state.sel_merged_lf.empty:
            if 'show_details_dialog_trigger' not in st.session_state: st.session_state.show_details_dialog_trigger = False
            if 'last_selected_merged_index' not in st.session_state: st.session_state.last_selected_merged_index = None
            
            current_sel_index_dialog = None
            if not st.session_state.sel_merged_lf.empty and 'Index' in st.session_state.sel_merged_lf.columns:
                 current_sel_index_dialog = st.session_state.sel_merged_lf['Index'].iloc[0]

            if current_sel_index_dialog is not None and current_sel_index_dialog != st.session_state.last_selected_merged_index:
                st.session_state.show_details_dialog_trigger = True
                st.session_state.last_selected_merged_index = current_sel_index_dialog
            elif current_sel_index_dialog is None: 
                st.session_state.last_selected_merged_index = None # Reset se a seleção for limpa
            
            if st.session_state.get('show_details_dialog_trigger', False):
                show_data_dialog(st.session_state.sel_merged_lf)
                st.session_state.show_details_dialog_trigger = False # Resetar o gatilho

if 'lf_empty_df' not in st.session_state:
    if 'lf_df' in st.session_state and st.session_state.lf_df is not None and not st.session_state.lf_df.empty:
        empty_series = pd.Series(index=st.session_state.lf_df.columns, dtype='object').fillna("")
    else:
        fallback_cols = ["Código Solicitação", "Data Solicitação", "Ocorrências", "Tipo Processo", "Setor", "Possível Divisão", "Razão Social", "CPF / CNPJ", "E-mail", "E-mail CC", "Docs. Mesclados 1", "Docs. Mesclados 2", "Observação", "Status", "Divisão", "GDOC", "Valor Manual", "Servidor", "Data Atendimento", "Data Modificação", "Motivo Indeferimento", "Respondido"]
        empty_series = pd.Series(index=fallback_cols, dtype='object').fillna("")
    st.session_state.lf_empty_df = empty_series
treated_line_lf = st.session_state.lf_empty_df.copy()

if original_selected_index_lf is not None and 'lf_df' in st.session_state and st.session_state.lf_df is not None and not st.session_state.lf_df.empty:
    # Certificar que selected_row_lf_df e lf_df_filtrado não estão vazios e possuem colunas
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
    else: 
        st.session_state.selected_index_lf = None
else: 
    st.session_state.selected_index_lf = None

if 'btn_clear_lf' not in st.session_state: st.session_state.btn_clear_lf = False
if st.session_state.btn_clear_lf:
    treated_line_lf = st.session_state.lf_empty_df.copy()
    st.session_state.btn_clear_lf = False
    # Limpar seleções das tabelas
    if LF_TABLE_KEY in st.session_state and hasattr(st.session_state[LF_TABLE_KEY], 'selection'):
         st.session_state[LF_TABLE_KEY].selection.rows = []
    if MERGED_TABLE_KEY in st.session_state and hasattr(st.session_state[MERGED_TABLE_KEY], 'selection'):
         st.session_state[MERGED_TABLE_KEY].selection.rows = []
    st.session_state.sel_merged_lf = pd.DataFrame() # Limpa o DataFrame de linha selecionada do histórico
    st.session_state.last_selected_merged_index = None # Reseta o último índice selecionado do histórico
    original_selected_index_lf = None # Reseta a seleção original
    st.session_state.selected_index_lf = None


show_expander_2 = bool("Código Solicitação" in treated_line_lf and len(str(treated_line_lf.get("Código Solicitação",""))) > 1)

# --- INÍCIO DA MODIFICAÇÃO ---
# Lógica de gerenciamento do Session State para Selectboxes do formulário LF
status_options_form_sel = ['Passivo', 'Deferido', 'Indeferido']
divisao_options_form_sel = ['DVSA', 'DVSE', 'DVSCEP', 'DVSDM']
is_record_loaded_for_form = show_expander_2

# --- Lógica para Selectbox "Status *" ---
if is_record_loaded_for_form:
    status_from_data = str(treated_line_lf.get("Status", "")).strip()
    if status_from_data in status_options_form_sel:
        st.session_state.form_status_lf_sel = status_from_data
    else:
        # Se o status da planilha for "" ou inválido, o placeholder deve ser mostrado.
        # Para isso, a chave do selectbox no session_state não deve existir.
        if 'form_status_lf_sel' in st.session_state:
            del st.session_state.form_status_lf_sel
else:
    # Se nenhum registro estiver carregado, limpa o estado para garantir que o placeholder apareça.
    if 'form_status_lf_sel' in st.session_state:
        del st.session_state.form_status_lf_sel

# --- Lógica para Selectbox "Divisão *" ---
if is_record_loaded_for_form:
    divisao_from_data = str(treated_line_lf.get("Divisão", "")).strip()
    if divisao_from_data in divisao_options_form_sel:
        st.session_state.form_divisao_lf_sel = divisao_from_data
    else:
        # Se a divisão da planilha for "" ou inválida, limpa o estado.
        if 'form_divisao_lf_sel' in st.session_state:
            del st.session_state.form_divisao_lf_sel
else:
    # Se nenhum registro estiver carregado, limpa o estado.
    if 'form_divisao_lf_sel' in st.session_state:
        del st.session_state.form_divisao_lf_sel
# --- FIM DA MODIFICAÇÃO ---


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
                # Supondo que get_ocorrencias exista
                # from your_module import get_ocorrencias
                get_ocorrencias(treated_line_lf.get("CPF / CNPJ", ""), "lf")


            col1_c1_form, col2_c1_form, col3_c1_form = st.columns(3, vertical_alignment="bottom")
            tipo_processo_lf = col1_c1_form.text_input("Tipo Processo", value=treated_line_lf.get("Tipo Processo", ""),key="form_tipo_proc")
            tipo_empresa_lf = col2_c1_form.text_input("Setor", value=treated_line_lf.get("Setor", ""), key="form_setor")
            divisao_declarada_lf = col3_c1_form.text_input("Possível Divisão", value=treated_line_lf.get("Possível Divisão", ""), key="form_poss_div")
            col1_c1_2_form, col2_c1_2_form, col3_c1_2_form = st.columns([1.5,1,0.5], vertical_alignment="bottom")
            cpf_cnpj_val = treated_line_lf.get("CPF / CNPJ", "")
            btn_cnpj_lf_disabled = not (len(str(cpf_cnpj_val)) == 18 or len(str(cpf_cnpj_val)) == 14) # 18 para CNPJ, 14 para CPF com formatação
            razao_social_lf = col1_c1_2_form.text_input("Nome Estab.", value=treated_line_lf.get("Razão Social", ""), key="form_razao_social")
            cpf_cnpj_lf_input = col2_c1_2_form.text_input("CPF / CNPJ", value=cpf_cnpj_val, key="form_cpf_cnpj")
            btn_cnpj_lf = col3_c1_2_form.form_submit_button("🔎", use_container_width=True, disabled=btn_cnpj_lf_disabled, help="Buscar CNPJ/CPF")
            if btn_cnpj_lf:
                if not btn_cnpj_lf_disabled: 
                    # Supondo que get_cnpj exista
                    # from your_module import get_cnpj
                    get_cnpj(cpf_cnpj_lf_input, '', '')
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
            
            # --- INÍCIO DA MODIFICAÇÃO ---
            # Lógica de pré-seleção para Status agora é gerenciada pelo session_state
            status_lf_selectbox = col1_c2_form.selectbox(
                "Status *",
                options=status_options_form_sel,
                index=None,  # Garante que o placeholder seja usado se a key não estiver no session_state
                key="form_status_lf_sel",
                placeholder="..."
            )
            # --- FIM DA MODIFICAÇÃO ---

            # Lógica para habilitar/desabilitar botões e campos baseada no status_lf_selectbox
            disable_file_uploader_form = True
            disable_btn_save_lf_form = True
            disable_btn_send_lf_form = True

            # Tratar status_lf_selectbox == None (placeholder selecionado)
            # Se o placeholder estiver selecionado para Status, consideramos como 'Passivo' para a lógica de UI
            effective_status_for_ui = status_lf_selectbox if status_lf_selectbox is not None else "Passivo"

            if effective_status_for_ui == 'Passivo':
                disable_btn_save_lf_form = False
            elif effective_status_for_ui == 'Deferido':
                disable_file_uploader_form = False
                disable_btn_save_lf_form = False
                disable_btn_send_lf_form = False
            elif effective_status_for_ui == 'Indeferido':
                disable_btn_save_lf_form = False
                disable_btn_send_lf_form = False
            
            # --- INÍCIO DA MODIFICAÇÃO ---
            # Lógica de pré-seleção para Divisão agora é gerenciada pelo session_state
            divisao_lf_selectbox = col2_c2_form.selectbox(
                "Divisão *",
                options=divisao_options_form_sel,
                index=None, # Garante que o placeholder seja usado se a key não estiver no session_state
                key="form_divisao_lf_sel",
                placeholder="..."
            )
            # --- FIM DA MODIFICAÇÃO ---

            gdoc_lf_input = col3_c2_form.text_input("GDOC/Ano (xx/AA) *", value=treated_line_lf.get("GDOC", ""), key="form_gdoc_lf_input")
            valor_manual_val_form = treated_line_lf.get("Valor Manual", "R$ 0,00") # Default para nova entrada
            
            # Garante que, se o setor não for privado ou vazio, o valor seja R$0,00
            # No entanto, o valor carregado de treated_line_lf tem precedência se já existir.
            setor_atual = treated_line_lf.get("Setor", "")
            if setor_atual not in ['', 'Privado'] and valor_manual_val_form == "R$ 0,00" and not treated_line_lf.get("Valor Manual"):
                 valor_manual_val_form = 'R$ 0,00'
            elif setor_atual in ['', 'Privado'] and valor_manual_val_form == "R$ 0,00" and not treated_line_lf.get("Valor Manual"):
                 pass # Permite que o usuário insira o valor se for privado

            valor_manual_lf_input = col4_c2_form.text_input("Valor do DAM *", value=valor_manual_val_form, key="form_valor_manual_lf_input")
            
            col1_c2_2_form, col2_c2_2_form, col3_c2_2_form = st.columns(3, vertical_alignment="bottom")
            servidor_lf_input_form = col1_c2_2_form.text_input("Servidor", value=treated_line_lf.get("Servidor", st.session_state.get("sessao_servidor", "")), key="form_servidor_lf_input_display", disabled=True) 
            data_atendimento_lf_val_form = treated_line_lf.get("Data Atendimento", "")
            data_atendimento_lf_input = col2_c2_2_form.text_input("Data At.", value=data_atendimento_lf_val_form, key="form_data_at_lf_input", disabled=True)
            data_modificacao_lf_input = col3_c2_2_form.text_input("Data Mod.", value=treated_line_lf.get("Data Modificação", ""), key="form_data_mod_lf_input", disabled=True)
            
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
                st.session_state.reload_lf_df = True # Forçar recarregamento do DF principal
                load_lf_df_cached.clear() # Limpar cache do DF
                if rerun: st.rerun()
            
            if btn_clear_lf_form: btn_clear_fn_form_action(rerun=True)
            
            if btn_save_lf_form:
                if codigo_solicitacao_lf_form_input and tipo_processo_lf:
                    with st.spinner("Salvando dados, aguarde..."):
                        divisao_list_save = ['DVSA', 'DVSE', 'DVSCEP', 'DVSDM'] # Divisões válidas
                        
                        # Usar 'Passivo' se o status_lf_selectbox for None (placeholder)
                        status_to_save = status_lf_selectbox if status_lf_selectbox is not None else "Passivo"
                        # Divisão pode ser None se o placeholder for selecionado
                        divisao_to_save = divisao_lf_selectbox 

                        string_formatada_dam_save = extrair_e_formatar_real(valor_manual_lf_input)
                        valor_numerico_convertido_dam_save = None
                        cond_valor_dam_ok_para_deferido_save = False

                        if string_formatada_dam_save and isinstance(string_formatada_dam_save, str) and string_formatada_dam_save.strip() != "":
                            try:
                                str_para_float = string_formatada_dam_save.replace("R$", "").strip()
                                if '.' in str_para_float and ',' in str_para_float: # Formato 1.234,56
                                    str_para_float = str_para_float.replace('.', '').replace(',', '.')
                                elif ',' in str_para_float: # Formato 1234,56
                                    str_para_float = str_para_float.replace(',', '.')
                                valor_numerico_convertido_dam_save = float(str_para_float)
                                if valor_numerico_convertido_dam_save >= 0:
                                    cond_valor_dam_ok_para_deferido_save = True
                            except ValueError:
                                pass 
                        
                        gdoc_is_valid_save = validate_gdoc(gdoc_lf_input, data_solicitacao_lf)

                        save_condition_deferido = (status_to_save == "Deferido" and 
                                                   gdoc_is_valid_save and 
                                                   (divisao_to_save in divisao_list_save) and 
                                                   cond_valor_dam_ok_para_deferido_save)
                        save_condition_indeferido = (status_to_save == "Indeferido" and len(motivo_indeferimento_lf_input or "") > 10)
                        save_condition_passivo = (status_to_save == "Passivo")

                        if save_condition_deferido or save_condition_indeferido or save_condition_passivo:
                            worksheet_save = get_worksheet(2, st.secrets['sh_keys']['geral_major'])
                            cell_save = worksheet_save.find(codigo_solicitacao_lf_form_input, in_column=1) 
                            
                            if cell_save:
                                data_atendimento_to_save = data_atendimento_lf_val_form
                                if not worksheet_save.acell(f'S{cell_save.row}').value: # Se Data Atendimento estiver vazia
                                     data_atendimento_to_save = get_current_datetime()
                                
                                data_modificacao_to_save = get_current_datetime()
                                current_gdoc_link_cartao_save = worksheet_save.acell(f'V{cell_save.row}').value or ""
                                current_respondido_save = worksheet_save.acell(f'Y{cell_save.row}').value or "Não"
                                
                                valor_dam_para_planilha = string_formatada_dam_save if string_formatada_dam_save else valor_manual_lf_input
                                # Se Deferido, mas DAM inválido, mantenha o input original (que pode ser texto como "Isento")
                                if status_to_save == "Deferido" and not cond_valor_dam_ok_para_deferido_save:
                                    valor_dam_para_planilha = valor_manual_lf_input
                                # Se não for Deferido e o valor formatado for vazio, use o input original
                                elif status_to_save != "Deferido" and not string_formatada_dam_save:
                                     valor_dam_para_planilha = valor_manual_lf_input
                                
                                servidor_a_salvar = st.session_state.get("sessao_servidor", "")

                                values_to_update_save = [
                                    codigo_solicitacao_lf_form_input, # Col O (Cód. Solicitação, para referência, não é atualizado)
                                    valor_dam_para_planilha,          # Col P (Valor Manual)
                                    status_to_save,                   # Col Q (Status)
                                    servidor_a_salvar,                # Col R (Servidor)
                                    data_atendimento_to_save,         # Col S (Data Atendimento)
                                    data_modificacao_to_save,         # Col T (Data Modificação)
                                    motivo_indeferimento_lf_input,    # Col U (Motivo Indeferimento)
                                    current_gdoc_link_cartao_save,    # Col V (Link Cartão Protocolo GDrive)
                                    gdoc_lf_input,                    # Col W (GDOC)
                                    divisao_to_save,                  # Col X (Divisão) - pode ser None
                                    current_respondido_save           # Col Y (Respondido)
                                ]
                                # Atualiza as colunas P até Y (índices 15 a 24)
                                # O primeiro valor (cód.sol) é só para achar a linha, não entra no update range
                                range_to_update_save = f"P{cell_save.row}:Y{cell_save.row}"
                                worksheet_save.update(range_name=range_to_update_save, values=[values_to_update_save[1:]])


                                st.session_state.reload_lf_df = True
                                if status_to_save in ["Deferido", "Indeferido"]:
                                    st.session_state.reload_tx_df = True
                                st.session_state.toast_msg_success = True
                                btn_clear_fn_form_action(rerun=True) 
                            else:
                                st.error(f"Código de Solicitação '{codigo_solicitacao_lf_form_input}' não encontrado na planilha para salvar.")
                        else: 
                            # Mensagens de erro específicas
                            if status_to_save == "Deferido":
                                if not gdoc_is_valid_save: st.toast(f"GDOC deve ser no formato xx/AA (ex: {datetime.datetime.now().strftime('%y')}).")
                                elif not (divisao_to_save in divisao_list_save): st.toast("Divisão inválida para Deferimento. Selecione uma divisão.")
                                elif not cond_valor_dam_ok_para_deferido_save:
                                    st.toast("Para Deferimento, o Valor do DAM é obrigatório e deve ser um valor monetário válido (ex: R$ 0,00 ou 150,25).")
                            elif status_to_save == "Indeferido" and not (len(motivo_indeferimento_lf_input or "") > 10): 
                                st.toast("Motivo do indeferimento muito curto.")
                else:
                    st.toast("Erro. Código da Solicitação e Tipo de Processo são obrigatórios.")
            
            if 'is_email_sended_lf' not in st.session_state: st.session_state.is_email_sended_lf = False
            
            def mark_email_as_sent_form_action():
                # Usar 'Passivo' se o status_lf_selectbox for None (placeholder)
                status_for_email_logic = status_lf_selectbox if status_lf_selectbox is not None else "Passivo"

                worksheet_email = get_worksheet(2, st.secrets['sh_keys']['geral_major'])
                cell_email = worksheet_email.find(codigo_solicitacao_lf_form_input, in_column=1) 
                if cell_email:
                    link_do_cartao_gdrive = st.session_state.get("gdrive_link_do_cartao", "")
                    if link_do_cartao_gdrive: 
                        worksheet_email.update_acell(f'V{cell_email.row}', link_do_cartao_gdrive)
                    worksheet_email.update_acell(f'Y{cell_email.row}', "Sim") # Marca como respondido
                st.session_state.reload_lf_df = True
                if status_for_email_logic in ["Deferido", "Indeferido"]: # Usa o status efetivo
                    st.session_state.reload_tx_df = True
                load_lf_df_cached.clear() 
                st.session_state.is_email_sended_lf = False
                st.session_state.pop("gdrive_link_do_cartao", None)
                btn_clear_fn_form_action(rerun=True)
            
            def send_mail_form_action():
                # Usar 'Passivo' se o status_lf_selectbox for None (placeholder)
                status_for_send = status_lf_selectbox if status_lf_selectbox is not None else "Passivo"
                # Divisão pode ser None
                divisao_for_send = divisao_lf_selectbox
                
                # Supondo que email_licenciamento exista
                # from your_module import email_licenciamento
                email_licenciamento(
                    kw_status=status_for_send, 
                    kw_gdoc=gdoc_lf_input, 
                    kd_divisao=divisao_for_send, 
                    kw_protocolo=codigo_solicitacao_lf_form_input, 
                    kw_data_sol=data_solicitacao_lf, 
                    kw_tipo_proc=f'Licenciamento Sanitário ({tipo_processo_lf})', 
                    kw_razao_social=razao_social_lf, 
                    kw_cpf_cnpj=cpf_cnpj_lf_input, 
                    kw_cartao_protocolo=cartao_protocolo_lf_uploader, 
                    kw_email1=email1_lf, 
                    kw_email2=email2_lf, 
                    kw_motivo_indeferimento=motivo_indeferimento_lf_input
                )
            
            if btn_send_lf_form:
                if codigo_solicitacao_lf_form_input and tipo_processo_lf:
                    # Usar 'Passivo' se o status_lf_selectbox for None (placeholder)
                    status_for_send_action = status_lf_selectbox if status_lf_selectbox is not None else "Passivo"
                    # Divisão pode ser None
                    divisao_for_send_action = divisao_lf_selectbox

                    valid_gdoc_for_send_act = validate_gdoc(gdoc_lf_input, data_solicitacao_lf)
                    valid_protocol_file_for_send_act = False
                    if cartao_protocolo_lf_uploader is not None: 
                        valid_protocol_file_for_send_act = validate_protocolo(cartao_protocolo_lf_uploader.name, gdoc_lf_input)
                    
                    valor_manual_ok_for_send_act = False
                    if status_for_send_action == "Deferido":
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
                    
                    send_cond_deferido_act = (status_for_send_action == "Deferido" and 
                                               (divisao_for_send_action in ['DVSA', 'DVSE', 'DVSCEP', 'DVSDM']) and 
                                               valid_gdoc_for_send_act and cartao_protocolo_lf_uploader is not None and 
                                               valid_protocol_file_for_send_act and valor_manual_ok_for_send_act)
                    send_cond_indeferido_act = (status_for_send_action == "Indeferido" and len(motivo_indeferimento_lf_input or "") > 10)

                    if send_cond_deferido_act or send_cond_indeferido_act:
                        st.toast(f"Tentando responder à '{codigo_solicitacao_lf_form_input}'. Aguarde...")
                        send_mail_form_action() # Chama a função que efetivamente envia o e-mail
                        if st.session_state.is_email_sended_lf: # Se o envio foi bem sucedido (controlado dentro de email_licenciamento)
                            mark_email_as_sent_form_action() # Atualiza a planilha
                    else:
                        if status_for_send_action == "Deferido":
                            if not (divisao_for_send_action in ['DVSA', 'DVSE', 'DVSCEP', 'DVSDM']): st.toast(":red[Divisão inválida para envio. Selecione uma divisão.]")
                            elif not valid_gdoc_for_send_act: st.toast(f":red[Formato do GDOC inválido (ex: xx/{datetime.datetime.now().strftime('%y')})]")
                            elif cartao_protocolo_lf_uploader is None: st.toast(":red[Cartão do protocolo não anexado.]")
                            elif not valid_protocol_file_for_send_act: st.toast(":red[Nome do arquivo do protocolo não corresponde ao GDOC.]")
                            elif not valor_manual_ok_for_send_act: 
                                st.toast(":red[Para Deferimento, Valor do DAM não preenchido ou inválido (deve ser um valor monetário >= R$ 0,00).]")
                        if status_for_send_action == "Indeferido" and not (len(motivo_indeferimento_lf_input or "") > 10): 
                            st.toast(":red[Motivo do indeferimento muito curto para envio.]")
                else: st.toast(":red[Erro. Código da Solicitação e Tipo de Processo são obrigatórios para envio.]")
            
            if btn_gdoc_webdriver_form:
                # Divisão pode ser None se placeholder selecionado
                divisao_for_webdriver = divisao_lf_selectbox 
                if cpf_cnpj_lf_input and divisao_for_webdriver: # Verifica se divisão foi selecionada
                    # Supondo que selenium_proc_gdoc exista
                    # from your_module import selenium_proc_gdoc
                    selenium_proc_gdoc(
                        kw_cpf_cnpj=cpf_cnpj_lf_input, 
                        kw_razao_social=razao_social_lf, 
                        kw_email1=email1_lf, kw_email2=email2_lf, 
                        kw_tipoProc=tipo_processo_lf, 
                        kw_divisao=divisao_for_webdriver, 
                        kw_docs1=treated_line_lf.get("Docs. Mesclados 1", ""), 
                        kw_docs2=treated_line_lf.get("Docs. Mesclados 2", ""), 
                        kw_obs=observacao_lf_input
                    )
                else: 
                    toast_message = ":red[**CPF/CNPJ é necessário para sGDOC.**]"
                    if not divisao_for_webdriver:
                        toast_message = ":red[**CPF/CNPJ e Divisão são necessários para sGDOC. Selecione uma divisão.**]"
                    st.toast(toast_message)