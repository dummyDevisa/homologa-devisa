import streamlit as st
import pandas as pd
from load_functions import * # Assume que selenium_generate_dam, get_cnpj, get_ocorrencias, etc. estão aqui
import datetime
import re
import json # Para o diálogo de detalhes
import time
from webdriver_etax import selenium_generate_dam

st.header("Emissão de DAM", anchor=False)

# Inicialização e recarregamento de DFs
if 'reload_tx_df' not in st.session_state:
    st.session_state.reload_tx_df = False
    st.session_state.reload_div_df = True
    st.session_state.reload_lf_df = True

# Inicializa o estado da seleção se não existir
if 'selected_index_tx' not in st.session_state:
    st.session_state.selected_index_tx = None

st.session_state.reload_div_df = True
st.session_state.reload_lf_df = True

@st.cache_data(ttl=300, show_spinner="Carregando o banco 'Taxas'...")
def load_tx_df_cached():
    worksheet = get_worksheet(0, st.secrets['sh_keys']['geral_major'])
    data = worksheet.get_all_records(numericise_ignore=['all'])
    df = pd.DataFrame(data)
    return df

# Chaves de tabela (definidas globalmente para serem acessíveis)
TX_TABLE_KEY = "tx_table_selection"
MERGED_TX_TABLE_KEY = "merged_tx_table_selection"


if 'tx_df' not in st.session_state or st.session_state.reload_tx_df:
    df_tx_aux = load_tx_df_cached()
    if not df_tx_aux.empty:
        st.session_state.tx_df = df_tx_aux[df_tx_aux["Validade"] != "Inválido"].copy()
        if 'Data Solicitação' in st.session_state.tx_df.columns:
            st.session_state.tx_df['Data_Solicitacao_dt'] = pd.to_datetime(
                st.session_state.tx_df['Data Solicitação'],
                format='%d/%m/%y, %H:%M',
                errors='coerce'
            )
        else:
            st.session_state.tx_df['Data_Solicitacao_dt'] = pd.NaT
        st.session_state.tx_df = st.session_state.tx_df.reset_index(drop=True)
    else:
        st.session_state.tx_df = pd.DataFrame()
    st.session_state.reload_tx_df = False

if 'status_selecionado_tx' not in st.session_state:
    st.session_state.status_selecionado_tx = 'Passivo'
if 'secondary_pills_selection_tx' not in st.session_state:
    default_secondary_tx = ["As minhas", "Não resp."] if st.session_state.status_selecionado_tx in ['Deferido', 'Indeferido'] else []
    st.session_state.secondary_pills_selection_tx = default_secondary_tx

st.session_state.checkbox_minhas_tx = "As minhas" in st.session_state.secondary_pills_selection_tx
st.session_state.checkbox_nao_respondidas_tx = "Não resp." in st.session_state.secondary_pills_selection_tx

def prepare_hist_df_tx(df, source_name):
    expected_cols = ['CPF / CNPJ', 'Protocolo', 'Data Criação', 'Tipo Processo', 'Valor', 'Status', 'Servidor', 'Respondido']
    if df.empty:
        return pd.DataFrame(columns=expected_cols + ['OriginalRowIndex', 'Source', 'Index'])
    df_processed = df.copy()
    for col in expected_cols:
        if col not in df_processed.columns:
            df_processed[col] = pd.NA
    current_index_name = df_processed.index.name
    df_processed = df_processed.reset_index()
    if 'index' in df_processed.columns and 'OriginalRowIndex' not in df_processed.columns:
         df_processed.rename(columns={'index': 'OriginalRowIndex'}, inplace=True)
    elif current_index_name and current_index_name in df_processed.columns and 'OriginalRowIndex' not in df_processed.columns :
         df_processed.rename(columns={current_index_name: 'OriginalRowIndex'}, inplace=True)
    elif 'OriginalRowIndex' not in df_processed.columns :
        df_processed['OriginalRowIndex'] = df_processed.index
    df_processed['Source'] = source_name
    df_processed['Index'] = source_name + '_' + df_processed['OriginalRowIndex'].astype(str)
    return df_processed

def hint_financial_values_revised(min_val_str, max_val_str, comp_str):
    parts = []
    if min_val_str and min_val_str != "R$ 0,00":
        parts.append(f"Valor mínimo: {min_val_str}")
    if max_val_str and max_val_str != "R$ 0,00":
        if not (min_val_str and min_val_str != "R$ 0,00" and min_val_str == max_val_str):
            parts.append(f"Valor máximo: {max_val_str}")
    if comp_str:
        parts.append(f"Tipo: {comp_str}")
    if not parts:
        return ""
    return "; ".join(parts) + "."

if 'tx_empty_df' not in st.session_state:
    if 'tx_df' in st.session_state and not st.session_state.tx_df.empty:
        empty_series_tx = pd.Series(index=st.session_state.tx_df.columns, dtype='object').fillna("")
    else:
        fallback_cols_tx = [
            "Tipo Processo", "Código Solicitação", "Data Solicitação", "Respondido",
            "Complemento Processo (1)", "Complemento Processo (3)", "Complemento Processo (4)",
            "CPF / CNPJ", "Ocorrências", "Valor Mínimo", "Valor Máximo", "Valor Total", "Valor Manual",
            "Complemento Valor", "E-mail", "E-mail CC", "Observação", "Status", "Servidor",
            "Data Atendimento", "Data Modificação", "Nº do DAM", "Motivo Indeferimento",
            "Identidade", "Endereço", "CNPJ", "CISC", "Notificação", "Alvará SEFIN", "DAM",
            "Data_Solicitacao_dt", "Validade"
        ]
        empty_series_tx = pd.Series(index=fallback_cols_tx, dtype='object').fillna("")
    st.session_state.tx_empty_df = empty_series_tx


with st.expander("Registro de Solicitações", expanded=True):
    colx, coly = st.columns(2, vertical_alignment="top")
    
    with colx:
        col_datas_tx, col_filtros_sec_tx, col_status_tx = st.columns([0.9, 1.0, 1.1], vertical_alignment="center", gap="small")
        with col_status_tx:
            status_options_tx = ['Passivo', 'Deferido', 'Indeferido']
            current_default_status_pills_tx = [st.session_state.status_selecionado_tx] if st.session_state.status_selecionado_tx in status_options_tx else [status_options_tx[0]]
            selected_status_output_tx = st.pills(
                label="Filtro por Status (Taxas):", options=status_options_tx,
                default=current_default_status_pills_tx, key="status_pills_filter_key_tx",
                help="Escolha o status do processo (Taxas)", label_visibility='collapsed'
            )
        if selected_status_output_tx and selected_status_output_tx != st.session_state.status_selecionado_tx:
            st.session_state.status_selecionado_tx = selected_status_output_tx
            if st.session_state.status_selecionado_tx in ['Deferido', 'Indeferido']:
                st.session_state.secondary_pills_selection_tx = ["As minhas", "Não resp."]
            else:
                st.session_state.secondary_pills_selection_tx = []
            st.session_state.checkbox_minhas_tx = "As minhas" in st.session_state.secondary_pills_selection_tx
            st.session_state.checkbox_nao_respondidas_tx = "Não resp." in st.session_state.secondary_pills_selection_tx
            st.rerun()

        status_para_filtragem_tx = st.session_state.status_selecionado_tx
        disable_secondary_pills_tx = not (status_para_filtragem_tx in ['Deferido', 'Indeferido'])
        if disable_secondary_pills_tx and st.session_state.secondary_pills_selection_tx:
            st.session_state.secondary_pills_selection_tx = []
            st.session_state.checkbox_minhas_tx = False
            st.session_state.checkbox_nao_respondidas_tx = False

        with col_filtros_sec_tx:
            opcoes_filtros_secundarios_tx = ["As minhas", "Não resp."]
            selected_secondary_output_tx = st.pills(
                label="Filtros Secundários (Taxas)", options=opcoes_filtros_secundarios_tx,
                default=st.session_state.secondary_pills_selection_tx, selection_mode="multi",
                key="filtros_pills_secundarios_key_tx", help="Selecione os filtros desejados (Taxas)",
                label_visibility='collapsed', disabled=disable_secondary_pills_tx
            )
        if not disable_secondary_pills_tx:
            if st.session_state.secondary_pills_selection_tx != selected_secondary_output_tx:
                st.session_state.secondary_pills_selection_tx = selected_secondary_output_tx
                st.session_state.checkbox_minhas_tx = "As minhas" in st.session_state.secondary_pills_selection_tx
                st.session_state.checkbox_nao_respondidas_tx = "Não resp." in st.session_state.secondary_pills_selection_tx
                st.rerun()

        with col_datas_tx:
            today_tx = datetime.date.today()
            thirty_days_ago_tx = today_tx - datetime.timedelta(days=30)
            min_date_selectable_tx = datetime.date(2020, 1, 1)
            DATE_INPUT_KEY_TX = "date_input_tx_range_key"
            st.date_input(
                "Intervalo de Datas (Taxas)",
                value=(thirty_days_ago_tx + datetime.timedelta(days=1), today_tx),
                min_value=min_date_selectable_tx,
                max_value=today_tx,
                format="DD/MM/YYYY",
                label_visibility='collapsed',
                key=DATE_INPUT_KEY_TX
            )
            current_range_dates_tx = st.session_state[DATE_INPUT_KEY_TX]
            if isinstance(current_range_dates_tx, (tuple, list)) and len(current_range_dates_tx) == 2:
                data_inicio_tx, data_fim_tx = current_range_dates_tx
            else:
                st.toast("🛑 :red[**Intervalo de datas inválido.** Escolha duas datas.]")
                data_inicio_tx = data_fim_tx = today_tx
            
        if 'tx_df' not in st.session_state or st.session_state.tx_df.empty:
            st.warning("Banco de Taxas está vazio ou não carregado.")
            df_taxas_filtrado_final = pd.DataFrame()
        else:
            df_taxas_para_filtrar = st.session_state.tx_df.copy()
            df_taxas_para_filtrar['Status'] = df_taxas_para_filtrar['Status'].replace("", "Passivo")
            if status_para_filtragem_tx:
                df_taxas_filtrado_final = df_taxas_para_filtrar[df_taxas_para_filtrar['Status'] == status_para_filtragem_tx].copy()
            else:
                df_taxas_filtrado_final = df_taxas_para_filtrar.copy()
            if st.session_state.checkbox_minhas_tx and "Servidor" in df_taxas_filtrado_final.columns and "sessao_servidor" in st.session_state:
                df_taxas_filtrado_final = df_taxas_filtrado_final[df_taxas_filtrado_final['Servidor'] == st.session_state.sessao_servidor]
            if st.session_state.checkbox_nao_respondidas_tx and "Respondido" in df_taxas_filtrado_final.columns:
                df_taxas_filtrado_final = df_taxas_filtrado_final[df_taxas_filtrado_final['Respondido'] == "Não"]
            if data_inicio_tx and data_fim_tx and not df_taxas_filtrado_final.empty and 'Data_Solicitacao_dt' in df_taxas_filtrado_final.columns:
                df_temp_date_filter_tx = df_taxas_filtrado_final.dropna(subset=['Data_Solicitacao_dt'])
                if pd.api.types.is_datetime64_any_dtype(df_temp_date_filter_tx['Data_Solicitacao_dt']):
                    df_taxas_filtrado_final = df_temp_date_filter_tx[
                        (df_temp_date_filter_tx['Data_Solicitacao_dt'].dt.date >= data_inicio_tx) &
                        (df_temp_date_filter_tx['Data_Solicitacao_dt'].dt.date <= data_fim_tx)
                    ]
                else:
                    st.warning("Coluna 'Data_Solicitacao_dt' não está em formato de data para filtro (Taxas).")

        cols_to_display_tx = ["Código Solicitação", "Data Solicitação", "CPF / CNPJ", "Tipo Processo"]
        tx_df_display = pd.DataFrame(columns=cols_to_display_tx)
        if not df_taxas_filtrado_final.empty:
            actual_cols_tx = [col for col in cols_to_display_tx if col in df_taxas_filtrado_final.columns]
            if actual_cols_tx:
                tx_df_display = df_taxas_filtrado_final[actual_cols_tx].reset_index(drop=False)

        column_config_tx = {
            "index": None,
            "Código Solicitação": st.column_config.TextColumn("Cód.", width="small"),
            "Data Solicitação": st.column_config.TextColumn("Data", width="medium"),
            "CPF / CNPJ": st.column_config.TextColumn("CPF / CNPJ", width="medium"),
            "Tipo Processo": st.column_config.TextColumn("Tipo Processo", width="large")
        }
        if not tx_df_display.empty:
            for col in tx_df_display.columns:
                if col not in column_config_tx:
                    column_config_tx[col] = st.column_config.TextColumn(col)

        st.dataframe(
            tx_df_display,
            key=TX_TABLE_KEY,
            on_select="rerun",
            selection_mode="single-row",
            column_config=column_config_tx,
            height=142,
            use_container_width=True,
            hide_index=True
        )

        total_exibido_tx = len(tx_df_display)
        badge_text_tx = f"Exibindo: {total_exibido_tx}"
        if 'tx_df' in st.session_state and not st.session_state.tx_df.empty:
            base_df_for_badge_tx = st.session_state.tx_df.copy()
            base_df_for_badge_tx['Status'] = base_df_for_badge_tx['Status'].replace("", "Passivo")
            total_passivos_badge_tx = len(base_df_for_badge_tx[base_df_for_badge_tx['Status'] == 'Passivo'])
            if "Respondido" in base_df_for_badge_tx.columns:
                total_nao_respondidos_badge_tx = len(base_df_for_badge_tx[(base_df_for_badge_tx['Status'] != 'Passivo') & (base_df_for_badge_tx['Respondido'] == 'Não')])
                badge_text_tx += f" ~ Passivo: {total_passivos_badge_tx} ~ Não respondidos (Def/Ind): {total_nao_respondidos_badge_tx}"
            else:
                badge_text_tx += f" ~ Passivo: {total_passivos_badge_tx} ~ Não respondidos: N/A"
            st.badge(badge_text_tx, color="blue")
        else:
            st.badge(f"Exibindo: {total_exibido_tx} ~ Totais Gerais: N/A", color="grey")

        selected_row_tx_df = pd.DataFrame()
        st.session_state.selected_index_tx = None

        if TX_TABLE_KEY in st.session_state:
            selection_tx = st.session_state[TX_TABLE_KEY].selection
            if selection_tx.rows:
                selected_df_index_tx = selection_tx.rows[0]
                if not tx_df_display.empty and selected_df_index_tx < len(tx_df_display):
                    selected_row_tx_df = tx_df_display.drop(columns=['index']).iloc[[selected_df_index_tx]]
                    original_index = tx_df_display.iloc[selected_df_index_tx]['index']
                    st.session_state.selected_index_tx = original_index

        if 'tx_clear_clicked' not in st.session_state: 
            st.session_state.tx_clear_clicked = False
    
    with coly:
        col1_y_dummy_tx, col2_y_dummy_tx = st.columns([0.5, 1.5], vertical_alignment="top")
        opcoes_filtro_dummy_tx = ['Alfa', 'Beta', 'Gama', 'Delta']
        with col1_y_dummy_tx:
            st.text_input("Teste 1 (desabilitado)", value="", disabled=True, label_visibility='collapsed', key="dummy_test1_coly_tx")
        with col2_y_dummy_tx:
            st.selectbox("Teste 2 (desabilitado)", opcoes_filtro_dummy_tx, index=1, disabled=True, label_visibility='collapsed', key="dummy_test2_coly_tx")

        if 'df_geral_2025' not in st.session_state or st.session_state.df_geral_2025 is None:
            st.session_state.df_geral_2025 = load_df_2025()
        
        merged_df_hist_src_tx = st.session_state.get('merged_df', pd.DataFrame()).copy()
        df_geral_2025_hist_src_tx = st.session_state.df_geral_2025.copy() if st.session_state.df_geral_2025 is not None else pd.DataFrame()

        df_geral_2025_hist_prepared_tx = prepare_hist_df_tx(df_geral_2025_hist_src_tx, 'df2025Taxas')
        merged_df_hist_prepared_tx = prepare_hist_df_tx(merged_df_hist_src_tx, 'dfMergedTaxas')

        allin_merged_df_hist_base_tx = pd.concat([df_geral_2025_hist_prepared_tx, merged_df_hist_prepared_tx], ignore_index=True)
        allin_merged_df_hist_filtered_cpf_tx = pd.DataFrame()

        if not selected_row_tx_df.empty and "CPF / CNPJ" in selected_row_tx_df.columns:
            selected_cpf_cnpj_val_tx = selected_row_tx_df["CPF / CNPJ"].iloc[0]
            if selected_cpf_cnpj_val_tx and not allin_merged_df_hist_base_tx.empty:
                allin_merged_df_hist_filtered_cpf_tx = allin_merged_df_hist_base_tx[
                    allin_merged_df_hist_base_tx['CPF / CNPJ'] == selected_cpf_cnpj_val_tx
                ].copy()
        
        final_hist_df_to_display_tx = allin_merged_df_hist_filtered_cpf_tx.copy()
        hist_display_cols_ordered_tx = ["Protocolo", "Data Criação", "CPF / CNPJ", "Tipo Processo", "Index"]
        if 'hist_tx_df_display' not in st.session_state:
            st.session_state.hist_tx_df_display = pd.DataFrame(columns=hist_display_cols_ordered_tx)

        if st.session_state.get('tx_clear_clicked', False): 
            st.session_state.hist_tx_df_display = pd.DataFrame(columns=hist_display_cols_ordered_tx)
            st.session_state.tx_clear_clicked = False 
        else:
            if not final_hist_df_to_display_tx.empty:
                for col_d_tx in hist_display_cols_ordered_tx:
                    if col_d_tx not in final_hist_df_to_display_tx.columns:
                        final_hist_df_to_display_tx[col_d_tx] = pd.NA
                st.session_state.hist_tx_df_display = final_hist_df_to_display_tx[hist_display_cols_ordered_tx].copy()
                
                if 'Data Criação' in st.session_state.hist_tx_df_display.columns:
                    st.session_state.hist_tx_df_display.loc[:, 'Data Criação'] = pd.to_datetime(
                        st.session_state.hist_tx_df_display['Data Criação'],
                        format="%d/%m/%Y",
                        errors='coerce'
                    )
                    if not st.session_state.hist_tx_df_display['Data Criação'].isna().all():
                        st.session_state.hist_tx_df_display = st.session_state.hist_tx_df_display.sort_values(
                            by="Data Criação",
                            ascending=False,
                            na_position='last'
                        )
            else:
                st.session_state.hist_tx_df_display = pd.DataFrame(columns=hist_display_cols_ordered_tx)

        column_config_merged_tx = {
            "Index": None, "Protocolo": st.column_config.TextColumn("Protocolo", width="small"),
            "Data Criação": st.column_config.DateColumn("Data", format="DD/MM/YYYY", width="medium"),
            "CPF / CNPJ": st.column_config.TextColumn("CPF / CNPJ", width="medium"),
            "Tipo Processo": st.column_config.TextColumn("Tipo Processo", width="large") }
        if not st.session_state.hist_tx_df_display.empty:
            for col_tx_hist in st.session_state.hist_tx_df_display.columns:
                if col_tx_hist not in column_config_merged_tx:
                    column_config_merged_tx[col_tx_hist] = st.column_config.TextColumn(col_tx_hist)

        current_hist_tx_df_display_final = st.session_state.hist_tx_df_display.reset_index(drop=True)
        st.dataframe(
            current_hist_tx_df_display_final, key=MERGED_TX_TABLE_KEY, on_select="rerun", selection_mode="single-row",
            column_config=column_config_merged_tx, height=142, use_container_width=True, hide_index=True )
        total_exibido_hist_tx = len(current_hist_tx_df_display_final)
        st.badge(f"Exibindo Histórico: {total_exibido_hist_tx}", color="green")

        if 'sel_merged_tx_df' not in st.session_state:
            st.session_state.sel_merged_tx_df = pd.DataFrame()

        if MERGED_TX_TABLE_KEY in st.session_state:
            selection_merged_tx = st.session_state[MERGED_TX_TABLE_KEY].selection
            if selection_merged_tx.rows:
                selected_merged_df_index_tx = selection_merged_tx.rows[0]
                if selected_merged_df_index_tx < len(current_hist_tx_df_display_final):
                    st.session_state.sel_merged_tx_df = current_hist_tx_df_display_final.iloc[[selected_merged_df_index_tx]]
                else:
                    st.session_state.sel_merged_tx_df = pd.DataFrame()
            else:
                st.session_state.sel_merged_tx_df = pd.DataFrame()

        @st.dialog("Detalhes do Processo Histórico", width="large")
        def show_data_dialog_tx(selected_row_data_df_arg):
            if selected_row_data_df_arg.empty or 'Index' not in selected_row_data_df_arg.columns:
                st.warning("Nenhum dado selecionado ou 'Index' ausente para exibir detalhes.")
                return

            unique_id_val_dialog = selected_row_data_df_arg['Index'].iloc[0]
            df_to_display_json = pd.DataFrame()
            
            df_geral_2025_for_dialog = st.session_state.get('df_geral_2025', pd.DataFrame()).copy()
            merged_df_for_dialog = st.session_state.get('merged_df', pd.DataFrame()).copy()
            
            source_from_id = None
            original_idx_from_id = None
            if isinstance(unique_id_val_dialog, str):
                parts = unique_id_val_dialog.split('_', 1)
                if len(parts) == 2:
                    source_from_id = parts[0]
                    try:
                        original_idx_from_id = int(parts[1])
                    except ValueError:
                        st.warning(f"ID de histórico inválido: {unique_id_val_dialog}")
                        return

            if source_from_id and original_idx_from_id is not None:
                temp_df_source = None
                if source_from_id == 'df2025Taxas':
                    temp_df_source = df_geral_2025_for_dialog
                elif source_from_id == 'dfMergedTaxas':
                    temp_df_source = merged_df_for_dialog
                
                if temp_df_source is not None and not temp_df_source.empty and original_idx_from_id < len(temp_df_source):
                    df_to_display_json = temp_df_source.iloc[[original_idx_from_id]].copy()

            if df_to_display_json.empty:
                st.warning(f"Não foi possível carregar detalhes. ID: {unique_id_val_dialog}.")
                return

            if 'Valor' in df_to_display_json.columns:
                df_to_display_json.loc[:, 'Valor'] = df_to_display_json['Valor'].apply(
                    lambda x: f'R$ {float(x):,.2f}' if pd.notnull(x) and isinstance(x, (int, float)) else (x if isinstance(x, str) and x.startswith('R$') else 'R$ 0,00')
                )
            
            cols_to_drop_json = [col for col in ['index', 'level_0', 'OriginalRowIndex', 'Source', 'Index'] if col in df_to_display_json.columns]
            if cols_to_drop_json:
                df_to_display_json = df_to_display_json.drop(columns=cols_to_drop_json, errors='ignore')
            
            df_to_display_json = df_to_display_json.fillna("")

            json_data_str = df_to_display_json.to_json(orient='records', lines=False, date_format="iso", default_handler=str)
            try:
                loaded_json = json.loads(json_data_str)
                st.json(loaded_json[0] if isinstance(loaded_json, list) and loaded_json else {})
            except json.JSONDecodeError:
                st.error("Erro ao decodificar JSON para exibição.")
                st.text(json_data_str)

        if not st.session_state.get('sel_merged_tx_df', pd.DataFrame()).empty:
            if 'show_details_dialog_trigger_tx' not in st.session_state:
                st.session_state.show_details_dialog_trigger_tx = False
            if 'last_selected_merged_tx_index' not in st.session_state:
                st.session_state.last_selected_merged_tx_index = None

            current_sel_index_dialog_tx = None
            if not st.session_state.sel_merged_tx_df.empty and 'Index' in st.session_state.sel_merged_tx_df.columns:
                 current_sel_index_dialog_tx = st.session_state.sel_merged_tx_df['Index'].iloc[0]

            if current_sel_index_dialog_tx is not None and current_sel_index_dialog_tx != st.session_state.last_selected_merged_tx_index:
                st.session_state.show_details_dialog_trigger_tx = True
                st.session_state.last_selected_merged_tx_index = current_sel_index_dialog_tx
            elif current_sel_index_dialog_tx is None:
                st.session_state.last_selected_merged_tx_index = None

            if st.session_state.get('show_details_dialog_trigger_tx', False):
                show_data_dialog_tx(st.session_state.sel_merged_tx_df)
                st.session_state.show_details_dialog_trigger_tx = False
        
# --- Fim do Expander ---

treated_line_tx = st.session_state.tx_empty_df.copy()

if st.session_state.get('btn_clear_tx_form_active', False):
    treated_line_tx = st.session_state.tx_empty_df.copy()
    st.session_state.clicou_no_editar_tx = False
    st.session_state.btn_clear_tx_form_active = False

if st.session_state.get('selected_index_tx') is not None and 'tx_df' in st.session_state and not st.session_state.tx_df.empty:
    idx_to_fetch_tx = st.session_state.selected_index_tx
    if 0 <= idx_to_fetch_tx < len(st.session_state.tx_df):
        selected_line_series_tx = st.session_state.tx_df.loc[idx_to_fetch_tx]
        treated_line_tx = selected_line_series_tx.fillna("").copy()
    else:
        st.warning(f"Índice de seleção ({idx_to_fetch_tx}) tornou-se inválido. Limpando formulário.")
        st.session_state.selected_index_tx = None

is_record_loaded_for_form = bool(treated_line_tx.get("Código Solicitação", ""))

# #################### INÍCIO DA CORREÇÃO ####################
# O bloco de código que manipulava 'st.session_state.form_tx_status_sel' foi removido daqui,
# pois causava o erro de redefinir o status a cada interação.
# #################### FIM DA CORREÇÃO ####################

show_expander_2_tx = is_record_loaded_for_form
st.write("")

with st.expander("Detalhes da solicitação", expanded=show_expander_2_tx):
    st.write("")
    with st.form("form_taxas", border=False):
        container1_form, container2_form = st.columns(2, gap="large")

        with container1_form:
            col1_f1_c1, col2_f1_c1, col3_f1_c1, col4_f1_c1 = st.columns([1.6, 0.6, 0.6, 0.2], vertical_alignment="bottom")
            tipo_processo_tx_form_val = treated_line_tx.get("Tipo Processo", "")
            tipo_processo_tx_input = col1_f1_c1.text_input("Tipo Processo", value=tipo_processo_tx_form_val, key="form_tx_tipo_proc", disabled=True)
            codigo_solicitacao_tx_form_val = treated_line_tx.get("Código Solicitação", "")
            codigo_solicitacao_tx_input = col2_f1_c1.text_input("Cód. Solicitação", value=codigo_solicitacao_tx_form_val, key="form_tx_cod_sol", disabled=bool(codigo_solicitacao_tx_form_val))
            data_solicitacao_tx_form_val = treated_line_tx.get("Data Solicitação", "")
            data_solicitacao_tx_input = col3_f1_c1.text_input("Data Solicitação", value=data_solicitacao_tx_form_val, key="form_tx_data_sol", disabled=True)
            respondido_val_form_tx = treated_line_tx.get("Respondido", "")
            status_icon_tx_form = ":material/pending:"
            if respondido_val_form_tx == "Sim": status_icon_tx_form = ":material/check_circle:"
            elif respondido_val_form_tx == "Não": status_icon_tx_form = ":material/do_not_disturb_on:"
            col4_f1_c1.header(status_icon_tx_form, anchor=False)

            col1_f2_c1, col2_f2_c1, col3_f2_c1 = st.columns([1.3,1.4,0.3], vertical_alignment="bottom")
            complemento_1_tx_input = col1_f2_c1.text_input("Complemento Processo (1)", value=treated_line_tx.get("Complemento Processo (1)", ""), key="form_tx_comp1")
            complemento_3_tx_input = col2_f2_c1.text_input("Complemento Processo (3)", value=treated_line_tx.get("Complemento Processo (3)", ""), key="form_tx_comp3")
            cpf_cnpj_tx_form_val_for_btn = treated_line_tx.get("CPF / CNPJ", "")
            disable_btn_cnpj_tx_form = not (isinstance(cpf_cnpj_tx_form_val_for_btn, str) and (len(cpf_cnpj_tx_form_val_for_btn) == 18 or len(cpf_cnpj_tx_form_val_for_btn) == 14))
            btn_cnpj_tx_form_submit = col3_f2_c1.form_submit_button("🔎", use_container_width=True, help="Buscar CNPJ/CPF", disabled=disable_btn_cnpj_tx_form)

            complemento_4_tx_input = st.text_area("Complemento Processo (4)", value=treated_line_tx.get("Complemento Processo (4)", ""), height=77, key="form_tx_comp4")
            
            col1_f3_c1, col2_f3_c1_new_btn_occ, col3_f3_c1_new_comp_val, col4_f3_c1_new_valor_dam = st.columns([1.5, 1.0, 1.0, 1.0], vertical_alignment="bottom")
            cpf_cnpj_tx_form_val = treated_line_tx.get("CPF / CNPJ", "")
            cpf_cnpj_tx_input = col1_f3_c1.text_input("CPF / CNPJ", value=cpf_cnpj_tx_form_val, key="form_tx_cpf_cnpj")
            ocorrencias_tx_form_val = treated_line_tx.get("Ocorrências", "")
            btn_ocorrencias_label_tx_form = f"{ocorrencias_tx_form_val} 👁️" if ocorrencias_tx_form_val else "Ocorrências 👁️"
            btn_ocorrencias_disabled_tx_form = not bool(ocorrencias_tx_form_val)
            btn_ocorrencias_tx_form_submit = col2_f3_c1_new_btn_occ.form_submit_button(
                btn_ocorrencias_label_tx_form, type="secondary", use_container_width=True,
                disabled=btn_ocorrencias_disabled_tx_form, help="Ver Ocorrências"
            )
            f_vmin_tx = format_financial_values(treated_line_tx.get("Valor Mínimo", ""))
            f_vmax_tx = format_financial_values(treated_line_tx.get("Valor Máximo", ""))
            f_vtotal_tx = format_financial_values(treated_line_tx.get("Valor Total", ""))
            current_valor_manual_tx_form = treated_line_tx.get("Valor Manual", "")
            if not isinstance(current_valor_manual_tx_form, str) or "R$" not in current_valor_manual_tx_form :
                f_vmanual_tx = format_financial_values(current_valor_manual_tx_form)
            else: f_vmanual_tx = current_valor_manual_tx_form
            valor_dam_display_tx = f_vtotal_tx if f_vtotal_tx and f_vtotal_tx != "R$ 0,00" else f_vmanual_tx
            comp_valor_tx_input = col3_f3_c1_new_comp_val.text_input("Complemento Valor", value=treated_line_tx.get("Complemento Valor", ""), key="form_tx_comp_valor")
            valor_manual_tx_input = col4_f3_c1_new_valor_dam.text_input("Valor do DAM *", value=valor_dam_display_tx, key="form_tx_valor_manual")

            hint_text_to_display = ""
            is_record_selected_for_hint = bool(codigo_solicitacao_tx_form_val)
            is_valor_dam_field_initially_empty = not valor_dam_display_tx or valor_dam_display_tx == "R$ 0,00"
            complemento_valor_from_record = treated_line_tx.get("Complemento Valor", "")
            if is_record_selected_for_hint and is_valor_dam_field_initially_empty:
                if complemento_valor_from_record == "CISC":
                    valor_total_str_cisc = treated_line_tx.get("Valor Total", "")
                    if valor_total_str_cisc and isinstance(valor_total_str_cisc, str):
                        valores_cisc = [v.strip() for v in valor_total_str_cisc.split(';') if v.strip()]
                        valores_cisc_numeric = []
                        for val_str in valores_cisc:
                            try:
                                numeric_val = float(val_str.replace("R$", "").replace(".", "").replace(",", ".").strip())
                                valores_cisc_numeric.append((numeric_val, val_str))
                            except ValueError: valores_cisc_numeric.append((float('inf'), val_str))
                        valores_cisc_numeric.sort(key=lambda x: x[0])
                        valores_cisc_ordenados_str = [item[1] for item in valores_cisc_numeric]
                        if valores_cisc_ordenados_str:
                            hint_text_to_display = f"Valores possíveis para CISC: {'; '.join(valores_cisc_ordenados_str)}."
                        else: hint_text_to_display = "Tipo: CISC (valores específicos não encontrados)."
                    else: hint_text_to_display = "Tipo: CISC (lista de valores não encontrada)."
                else: hint_text_to_display = hint_financial_values_revised(f_vmin_tx, f_vmax_tx, complemento_valor_from_record)
            if hint_text_to_display: st.write(f"````{hint_text_to_display}````")

            nome_pf_para_webdriver_tx_input = ""
            if isinstance(cpf_cnpj_tx_input, str) and len(cpf_cnpj_tx_input) == 14:
                nome_pf_para_webdriver_tx_input_val = treated_line_tx.get("Nome Pessoa Fisica para DAM", "")
                nome_pf_para_webdriver_tx_input = st.text_input("Nome da Pessoa Física (para DAM CPF) *", value=nome_pf_para_webdriver_tx_input_val, key="form_tx_nome_pf_webdriver")

            st.write("")
            link_cols_r1_tx_form = st.columns(4); link_cols_r2_tx_form = st.columns(4)
            all_link_cols_tx_form = link_cols_r1_tx_form + link_cols_r2_tx_form
            link_idx_tx_form = 0
            cabecalho_url_tx_form_list = ["Identidade", "Endereço", "CNPJ", "CISC", "Notificação", "Alvará SEFIN", "DAM"]
            for header_key_tx_form in cabecalho_url_tx_form_list:
                url_val_tx_form = treated_line_tx.get(header_key_tx_form)
                if isinstance(url_val_tx_form, str) and url_val_tx_form.startswith("http") and link_idx_tx_form < len(all_link_cols_tx_form):
                    all_link_cols_tx_form[link_idx_tx_form].link_button(f"🔗 {header_key_tx_form}", url_val_tx_form, use_container_width=True)
                    link_idx_tx_form +=1

            col1_f4_c1, col2_f4_c1 = st.columns(2, vertical_alignment="bottom")
            email1_tx_input = col1_f4_c1.text_input("E-mail", value=treated_line_tx.get("E-mail", ""), key="form_tx_email1")
            email2_tx_input = col2_f4_c1.text_input("E-mail CC", value=treated_line_tx.get("E-mail CC", ""), key="form_tx_email2")

        with container2_form:
            obs_tx_input = st.text_area("Observação", value=treated_line_tx.get("Observação", ""), height=77, key="form_tx_obs")
            col1_f1_c2, col2_f1_c2, col3_f1_c2, col4_f1_c2, col5_f1_c2 = st.columns([1.2, 1.1, 1, 0.9, 0.9], vertical_alignment="bottom")
            
            # #################### INÍCIO DA CORREÇÃO ####################
            status_options_form_tx_sel = ['Passivo', 'Deferido', 'Indeferido']
            
            # Define o índice inicial para o selectbox.
            # `None` para registros novos (mostra o placeholder), ou o índice correspondente para registros existentes.
            status_index = None
            if is_record_loaded_for_form:
                # Se um registro está carregado, busca o status atual dele.
                status_from_data = treated_line_tx.get("Status", "Passivo")
                if status_from_data == "": # Trata caso de string vazia como 'Passivo'
                    status_from_data = "Passivo"
                try:
                    # Encontra o índice (0, 1, ou 2) do status na lista de opções.
                    status_index = status_options_form_tx_sel.index(status_from_data)
                except ValueError:
                    # Se o status do registro não estiver na lista (improvável), usa 'Passivo' como fallback.
                    status_index = 0
            
            # A `key` foi removida para que o Streamlit gere uma chave aleatória,
            # evitando que o estado seja sobrescrito incorretamente ao salvar.
            # O `index` é usado para definir a seleção inicial.
            status_tx_form_selectbox = col1_f1_c2.selectbox(
                "Status *",
                status_options_form_tx_sel,
                index=status_index,
                placeholder="Selecione o status..."
            )
            # #################### FIM DA CORREÇÃO ####################

            numero_dam_tx_form_val = str(treated_line_tx.get("Nº do DAM", "")).replace(".0", "")
            numero_dam_tx_input = col2_f1_c2.text_input("Nº do DAM *", value=numero_dam_tx_form_val, key="form_tx_num_dam")
            servidor_tx_form_val = treated_line_tx.get("Servidor", st.session_state.get("sessao_servidor",""))
            servidor_tx_input = col3_f1_c2.text_input("Servidor", value=servidor_tx_form_val, key="form_tx_servidor", disabled=True)
            data_atendimento_tx_form_val = treated_line_tx.get("Data Atendimento", "")
            data_atendimento_tx_input = col4_f1_c2.text_input("Data Atend.", value=data_atendimento_tx_form_val, key="form_tx_data_at", disabled=True)
            data_modificacao_tx_form_val = treated_line_tx.get("Data Modificação", "")
            data_modificacao_tx_input = col5_f1_c2.text_input("Data Mod.", value=data_modificacao_tx_form_val, key="form_tx_data_mod", disabled=True)
            motivo_indeferimento_tx_input = st.text_area("Justificativa do Indeferimento *", value=treated_line_tx.get("Motivo Indeferimento", ""), height=77, key="form_tx_motivo_ind")
            comp_despacho_tx = f"Cód: {codigo_solicitacao_tx_input} ~ {data_solicitacao_tx_input}; Tipo: {tipo_processo_tx_input}"
            if complemento_1_tx_input: comp_despacho_tx += f"; {complemento_1_tx_input}"
            if complemento_3_tx_input: comp_despacho_tx += f"; cnae(s) declarado(s) pelo solicitante: {complemento_3_tx_input}"
            if tipo_processo_tx_input == 'Auto de Infração':
                comp_despacho_tx += "; Referente ao processo _/20_, vinculado ao auto de infração nº 0_/20_. com a observação do art. 21 da lei federal 6.437/1977"
            comp_despacho_tx += ". No caso de vencimento, solicite novo DAM no site da Vigilância Sanitária. Consulta de boleto somente pelo site https://sefin.belem.pa.gov.br/servicos/2-via-consulta-de-dam-tributos-municipais-2/"
            st.code(body=comp_despacho_tx, line_numbers=False, language=None)

            disable_btn_save_tx_form = True; disable_btn_edit_tx_form = True
            disable_btn_send_tx_form = True; disable_btn_emitir_dam_tx_form = True
            effective_status_form_tx = status_tx_form_selectbox if status_tx_form_selectbox is not None else "Passivo"
            is_existing_record_tx = bool(codigo_solicitacao_tx_form_val)

            if st.session_state.get('clicou_no_editar_tx', False):
                disable_btn_save_tx_form = False; disable_btn_edit_tx_form = True
                if effective_status_form_tx == 'Deferido': disable_btn_send_tx_form = False
                elif effective_status_form_tx == 'Indeferido': disable_btn_send_tx_form = False
            else:
                if effective_status_form_tx == 'Passivo':
                    disable_btn_save_tx_form = False
                    if is_existing_record_tx: disable_btn_edit_tx_form = False
                    else: disable_btn_edit_tx_form = True
                    if is_existing_record_tx:
                        if st.session_state.get("auth_user") == 'Daniel': disable_btn_emitir_dam_tx_form = False
                        else: disable_btn_emitir_dam_tx_form = True
                    else: disable_btn_emitir_dam_tx_form = True
                elif effective_status_form_tx == 'Deferido':
                    disable_btn_send_tx_form = False
                    if is_existing_record_tx: disable_btn_edit_tx_form = False
                    else: disable_btn_save_tx_form = False
                elif effective_status_form_tx == 'Indeferido':
                    disable_btn_send_tx_form = False
                    if is_existing_record_tx: disable_btn_edit_tx_form = False
                    else: disable_btn_save_tx_form = False
            if not is_existing_record_tx:
                disable_btn_edit_tx_form = True; disable_btn_send_tx_form = True
                disable_btn_emitir_dam_tx_form = True

            action_cols_tx_form_r1 = st.columns(4, vertical_alignment="bottom", gap="small")
            action_cols_tx_form_r2 = st.columns(4, vertical_alignment="bottom", gap="small")
            btn_clear_tx_form_submit = action_cols_tx_form_r2[3].form_submit_button("🧹 Limpar", use_container_width=True, disabled=True)
            btn_save_tx_form_submit = action_cols_tx_form_r1[2].form_submit_button("💾 Salvar", use_container_width=True, disabled=disable_btn_save_tx_form, type='primary')
            btn_edit_tx_form_submit = action_cols_tx_form_r1[3].form_submit_button("📝 Editar", use_container_width=True, disabled=disable_btn_edit_tx_form)
            btn_send_tx_form_submit = action_cols_tx_form_r2[2].form_submit_button("📧 Enviar", use_container_width=True, disabled=disable_btn_send_tx_form, type='primary')
            action_cols_tx_form_r1[0].link_button("🌍 e-Tax", "http://siat.belem.pa.gov.br:8081/acesso/login.jsf", use_container_width=True)
            btn_enviar_lote_tx_form_submit = action_cols_tx_form_r1[1].form_submit_button("📤 Lote", use_container_width=True, help="Enviar Emails em Lote")
            btn_emitir_dam_tx_form_submit = action_cols_tx_form_r2[0].form_submit_button("💵 Gerar DAM", use_container_width=True, disabled=disable_btn_emitir_dam_tx_form, help="Gerar DAM via automação (apenas para status Passivo e usuário autorizado)")
            action_cols_tx_form_r2[1].link_button("📋 Requisitos", "https://sites.google.com/view/secretariadevisa/in%C3%ADcio/processos/requisitos?authuser=0", use_container_width=True)

        if 'toast_msg_success_tx' not in st.session_state:
            st.session_state.toast_msg_success_tx = False
        if st.session_state.toast_msg_success_tx:
            st.toast(f"Dados salvos ✨✨ (Taxas - {st.session_state.get('last_saved_status_tx', '')})")
            st.session_state.toast_msg_success_tx = False
            st.session_state.pop('last_saved_status_tx', None)

        def btn_clear_fn_form_tx_action(rerun=True):
            # Limpa o índice da linha selecionada
            st.session_state.selected_index_tx = None
            
            # Limpa explicitamente a seleção no próprio widget da tabela
            if TX_TABLE_KEY in st.session_state:
                st.session_state[TX_TABLE_KEY].selection.rows = []

            # Continua com as outras ações de limpeza
            st.session_state.btn_clear_tx_form_active = True
            st.session_state.tx_clear_clicked = True
            st.session_state.reload_tx_df = True
            load_tx_df_cached.clear()
            st.session_state.clicou_no_editar_tx = False
            
            if rerun: st.rerun()

        if btn_clear_tx_form_submit:
            btn_clear_fn_form_tx_action(rerun=True)

        if btn_cnpj_tx_form_submit:
            if cpf_cnpj_tx_input:
                get_cnpj(cpf_cnpj_tx_input, '', complemento_3_tx_input)
                st.toast(f"Buscando dados para CNPJ/CPF: {cpf_cnpj_tx_input}")
            else: st.toast(":orange[CNPJ/CPF não informado para busca.]")

        if btn_ocorrencias_tx_form_submit:
            if cpf_cnpj_tx_input: get_ocorrencias(cpf_cnpj_tx_input, "taxas")
            else: st.toast("CPF/CNPJ necessário para buscar Ocorrências (Taxas).")

        if 'clicou_no_editar_tx' not in st.session_state:
            st.session_state.clicou_no_editar_tx = False
        if btn_edit_tx_form_submit:
            st.session_state.clicou_no_editar_tx = True
            st.rerun()

        def save_in_sheet_tx_action(btn_edit_mode_action: bool):
            cod_sol_save = codigo_solicitacao_tx_input; tipo_proc_save = tipo_processo_tx_input
            comp1_save = complemento_1_tx_input; comp3_save = complemento_3_tx_input
            cpf_cnpj_save = cpf_cnpj_tx_input; valor_manual_save_form = valor_manual_tx_input
            email1_save = email1_tx_input; email2_save = email2_tx_input
            obs_save = obs_tx_input
            status_save = status_tx_form_selectbox if status_tx_form_selectbox is not None else "Passivo"
            num_dam_save_form = numero_dam_tx_input; motivo_ind_save = motivo_indeferimento_tx_input

            if not cod_sol_save: st.toast("🔴 :red[**Cód. Solicitação obrigatório.**]"); return
            if not tipo_proc_save: st.toast("🔴 :red[**Tipo Processo obrigatório.**]"); return

            valor_dam_final_to_save = ""; num_dam_final_to_save = num_dam_save_form
            motivo_ind_final_to_save = motivo_ind_save
            if status_save == "Deferido":
                valor_dam_final_to_save = extrair_e_formatar_real(valor_manual_save_form)
                if not valor_dam_final_to_save or float(valor_dam_final_to_save.replace('R$', '').replace('.', '').replace(',', '.').strip()) < 0.01:
                    st.toast("🔴 :red[**Deferir: Valor DAM > R$ 0,00.**]"); return
                if not (num_dam_save_form and re.fullmatch(r"-?\d+", num_dam_save_form) and len(num_dam_save_form) > 10):
                    st.toast("🔴 :red[**Deferir: Nº DAM válido.**]"); return
                motivo_ind_final_to_save = ""
            elif status_save == "Indeferido":
                if not (motivo_ind_save and len(motivo_ind_save) > 10):
                    st.toast("🔴 :red[**Indeferir: Motivo (mín. 10 chars).**]"); return
                num_dam_final_to_save = ""; valor_dam_final_to_save = ""
            elif status_save == "Passivo": valor_dam_final_to_save = valor_manual_save_form
            
            worksheet_save_tx = get_worksheet(0, st.secrets['sh_keys']['geral_major'])
            cell_save_tx = worksheet_save_tx.find(cod_sol_save, in_column=1)
            if not cell_save_tx: st.toast(f"🔴 :red[**Erro: Sol. '{cod_sol_save}' não encontrada.**]"); return
            servidor_atual_ws_tx = worksheet_save_tx.cell(cell_save_tx.row, 29).value
            if servidor_atual_ws_tx and servidor_atual_ws_tx != st.session_state.get("sessao_servidor") and not btn_edit_mode_action and status_save != "Passivo":
                st.toast(f"🔴 :red[**Erro! Sol. tratada por '{servidor_atual_ws_tx}'. Use Editar.**]"); return

            despacho_final_save = comp_despacho_tx if status_save != "Deferido" else ""; status_sheet = status_save
            servidor_sheet = st.session_state.get("sessao_servidor", "") if status_save != "Passivo" else treated_line_tx.get("Servidor", "")
            data_at_ws_val = worksheet_save_tx.cell(cell_save_tx.row, 30).value
            data_at_sheet = data_at_ws_val
            if status_save != "Passivo":
                if not data_at_ws_val: data_at_sheet = get_current_datetime()
            else: data_at_sheet = data_atendimento_tx_input
            data_mod_sheet = get_current_datetime() if status_save != "Passivo" else treated_line_tx.get("Data Modificação", "")
            respondido_sheet = worksheet_save_tx.cell(cell_save_tx.row, 34).value or "Não"
            
            values_upd_status_block_tx = [
                cod_sol_save, despacho_final_save, valor_dam_final_to_save, status_sheet,
                servidor_sheet, data_at_sheet, data_mod_sheet, motivo_ind_final_to_save,
                num_dam_final_to_save, respondido_sheet
            ]
            range_upd_status_block_tx = f"Y{cell_save_tx.row}:AH{cell_save_tx.row}"
            worksheet_save_tx.update(range_name=range_upd_status_block_tx, values=[values_upd_status_block_tx])
            st.session_state.toast_msg_success_tx = True
            st.session_state.last_saved_status_tx = status_save
            st.session_state.clicou_no_editar_tx = False
            btn_clear_fn_form_tx_action(rerun=True)

        if btn_save_tx_form_submit:
            save_in_sheet_tx_action(st.session_state.clicou_no_editar_tx)

        if 'is_email_sended_tx' not in st.session_state:
            st.session_state.is_email_sended_tx = False
        def mark_email_as_sent_tx_action():
            cod_sol_email = codigo_solicitacao_tx_input
            if not cod_sol_email: return
            ws_email_tx = get_worksheet(0, st.secrets['sh_keys']['geral_major'])
            cell_email_tx = ws_email_tx.find(cod_sol_email, in_column=1)
            if cell_email_tx: ws_email_tx.update_acell(f'AH{cell_email_tx.row}', "Sim")
            st.session_state.is_email_sended_tx = False
            st.session_state.clicou_no_editar_tx = False
            btn_clear_fn_form_tx_action(rerun=True)

        def send_mail_tx_action():
            comp1_email = f" ({complemento_1_tx_input})" if complemento_1_tx_input else ""
            email_taxas(
                kw_status=status_tx_form_selectbox, kw_protocolo=codigo_solicitacao_tx_input,
                kw_data_sol=data_solicitacao_tx_input, kw_tipo_proc=tipo_processo_tx_input,
                kw_complemento_1=comp1_email, kw_cpf_cnpj=cpf_cnpj_tx_input,
                kw_numero_dam=numero_dam_tx_input, kw_email1=email1_tx_input,
                kw_email2=email2_tx_input, kw_motivo_indeferimento=motivo_indeferimento_tx_input,
            )

        if btn_send_tx_form_submit:
            status_send = status_tx_form_selectbox; num_dam_send = numero_dam_tx_input
            valor_manual_send_form = valor_manual_tx_input; motivo_ind_send = motivo_indeferimento_tx_input
            can_send = False
            if status_send == "Deferido":
                valor_ok = extrair_e_formatar_real(valor_manual_send_form)
                if valor_ok and float(valor_ok.replace('R$', '').replace('.', '').replace(',', '.').strip()) >= 0.01 and \
                   num_dam_send and re.fullmatch(r"-?\d+", num_dam_send) and len(num_dam_send) > 10: can_send = True
                else: st.toast("🔴 Enviar Deferido: Valor DAM e Nº DAM válidos obrigatórios.")
            elif status_send == "Indeferido":
                if motivo_ind_send and len(motivo_ind_send) > 10: can_send = True
                else: st.toast("🔴 Enviar Indeferido: Motivo (mín. 10 chars) obrigatório.")
            else: st.toast("🔴 Status Passivo não envia e-mail por esta ação.")
            if can_send:
                st.toast(f"Tentando responder '{codigo_solicitacao_tx_input}'. Aguarde...")
                send_mail_tx_action()
                if st.session_state.is_email_sended_tx: mark_email_as_sent_tx_action()

        def save_numero_dam_tx_action(num_dam_gerado, valor_dam_usado):
            cod_sol_dam = codigo_solicitacao_tx_input;
            if not cod_sol_dam: return
            if num_dam_gerado and len(str(num_dam_gerado)) > 10 :
                st.toast(f"DAM {num_dam_gerado} gerado. Salvando...")
                worksheet_dam = get_worksheet(0, st.secrets['sh_keys']['geral_major'])
                cell_dam = worksheet_dam.find(cod_sol_dam, in_column=1)
                if cell_dam:
                    current_servidor = st.session_state.get("sessao_servidor", "")
                    current_datetime = get_current_datetime(); despacho_dam_gen = comp_despacho_tx
                    valor_dam_formatado = extrair_e_formatar_real(valor_dam_usado) if valor_dam_usado else "R$ 0,00"
                    values_dam_block = [
                        cod_sol_dam, despacho_dam_gen, valor_dam_formatado, "Deferido",
                        current_servidor, current_datetime, current_datetime, "",
                        str(num_dam_gerado), "Não"
                    ]
                    range_dam_block = f"Y{cell_dam.row}:AH{cell_dam.row}"
                    worksheet_dam.update(range_name=range_dam_block, values=[values_dam_block])
                    st.session_state.toast_msg_success_tx = True
                    st.session_state.last_saved_status_tx = "Deferido (DAM Gerado)"
                    btn_clear_fn_form_tx_action(rerun=True)
                else: st.toast(f"🔴 :red[**Erro: Sol. '{cod_sol_dam}' não encontrada.**]")
            else: st.toast(f"🔴 :red[**Nº DAM gerado ('{num_dam_gerado}') inválido.**]")

        def load_driver_and_save_dam_tx_action(nome_pf_webdriver):
            cpf_cnpj_dam = cpf_cnpj_tx_input; valor_manual_dam = valor_manual_tx_input
            if not cpf_cnpj_dam: st.toast("🔴 CPF/CNPJ obrigatório."); return
            valor_manual_dam_float_str = extrair_e_formatar_real(valor_manual_dam)
            if not valor_manual_dam_float_str or float(valor_manual_dam_float_str.replace('R$', '').replace('.', '').replace(',', '.').strip()) < 0.01 :
                st.toast("🔴 Valor DAM (> R$ 0,00) obrigatório."); return
            if len(cpf_cnpj_dam) == 14 and not nome_pf_webdriver:
                 st.toast("🔴 Nome Pessoa Física obrigatório para DAM CPF."); return
            list_usr_dam = {
                'cpf_cnpj': cpf_cnpj_dam, 'nome_pf': nome_pf_webdriver if len(cpf_cnpj_dam) == 14 else "",
                'valor': valor_manual_dam, 'despacho': comp_despacho_tx,
            }
            st.toast("🤖 Iniciando automação DAM. Aguarde...")
            numero_dam_aut_tx = selenium_generate_dam(list_usr_dam)
            if numero_dam_aut_tx: save_numero_dam_tx_action(numero_dam_aut_tx, list_usr_dam['valor'])
            else: st.toast("🔴 :red[**Falha ao gerar DAM.** Verifique console.]")

        if btn_emitir_dam_tx_form_submit:
            if status_tx_form_selectbox == 'Passivo':
                nome_pf_val = nome_pf_para_webdriver_tx_input if isinstance(cpf_cnpj_tx_input, str) and len(cpf_cnpj_tx_input) == 14 else ""
                load_driver_and_save_dam_tx_action(nome_pf_val)
            else: st.toast("🔴 :red[**Geração DAM apenas para status 'Passivo'.**]")

        def batch_send_mail_tx():
            st.toast("Verificando e-mails pendentes (Taxas)...")
            worksheet_batch = get_worksheet(0, st.secrets['sh_keys']['geral_major'])
            data_batch = worksheet_batch.get_all_records(numericise_ignore=['all'])
            df_batch = pd.DataFrame(data_batch)
            if df_batch.empty: st.toast(":orange[Planilha Taxas vazia.]"); return
            df_to_send = df_batch[
                (df_batch['Status'].isin(['Deferido', 'Indeferido'])) &
                (df_batch['Respondido'] == 'Não')
            ].copy()
            if df_to_send.empty: st.toast(":blue_book: Nenhum e-mail pendente (Taxas)."); return
            total_batch = len(df_to_send); enviados_batch = 0; erros_batch = 0
            st.toast(f"📧 Encontrados {total_batch} e-mails. Iniciando...")
            indexz = 0
            for indexz, row_data in df_to_send.iterrows():
                st.toast(f"Processando {indexz + 1}/{total_batch}: {row_data.get('Código Solicitação', 'N/A')}...")
                try:
                    comp1_email_batch = f" ({row_data.get('Complemento Processo (1)', '')})" if row_data.get('Complemento Processo (1)') else ""
                    email_taxas(
                        kw_status=row_data.get('Status'), kw_protocolo=row_data.get('Código Solicitação'),
                        kw_data_sol=row_data.get('Data Solicitação'), kw_tipo_proc=row_data.get('Tipo Processo'),
                        kw_complemento_1=comp1_email_batch, kw_cpf_cnpj=row_data.get('CPF / CNPJ'),
                        kw_numero_dam=str(row_data.get('Nº do DAM', "")).replace(".0",""),
                        kw_email1=row_data.get('E-mail'), kw_email2=row_data.get('E-mail CC'),
                        kw_motivo_indeferimento=row_data.get('Motivo Indeferimento'),
                    )
                    if st.session_state.get('is_email_sended_tx', False):
                        cell_batch_update = worksheet_batch.find(row_data.get('Código Solicitação'), in_column=1)
                        if cell_batch_update: worksheet_batch.update_acell(f'AH{cell_batch_update.row}', "Sim")
                        enviados_batch += 1; st.session_state.is_email_sended_tx = False
                    else: erros_batch += 1; st.toast(f"⚠️ Falha envio {row_data.get('Código Solicitação', 'N/A')}.")
                except Exception as e: erros_batch += 1; st.toast(f"🛑 Erro {row_data.get('Código Solicitação', 'N/A')}: {e}")
                time.sleep(2)
            st.toast(f"🏁 Lote finalizado: {enviados_batch} enviados, {erros_batch} falhas de {total_batch}.")
            btn_clear_fn_form_tx_action(rerun=True)

        if btn_enviar_lote_tx_form_submit: batch_send_mail_tx()