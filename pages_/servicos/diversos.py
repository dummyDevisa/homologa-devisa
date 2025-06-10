import streamlit as st
import pandas as pd
from load_functions import *
import datetime
import json

st.header("Processos Diversos", anchor=False)

if 'reload_div_df' not in st.session_state:
    st.session_state.reload_div_df = False
    st.session_state.reload_tx_df = True
    st.session_state.reload_lf_df = True

st.session_state.reload_tx_df = True
st.session_state.reload_lf_df = True

@st.cache_data(ttl=300, show_spinner="Carregando o banco 'Diversos'...")
def load_div_df():
    worksheet = get_worksheet(1, st.secrets['sh_keys']['geral_major'])
    data = worksheet.get_all_records(numericise_ignore=['all'])
    df = pd.DataFrame(data)
    return df

if 'div_df' not in st.session_state or st.session_state.reload_div_df:
    df_div_aux = load_div_df()
    if not df_div_aux.empty:
        st.session_state.div_df = df_div_aux[df_div_aux["Validade"] != "Inválido"].copy()
        if 'Data Solicitação' in st.session_state.div_df.columns:
            st.session_state.div_df['Data_Solicitacao_dt_div'] = pd.to_datetime(
                st.session_state.div_df['Data Solicitação'],
                format='%d/%m/%y, %H:%M',
                errors='coerce'
            )
        else:
             st.session_state.div_df['Data_Solicitacao_dt_div'] = pd.NaT
        st.session_state.div_df = st.session_state.div_df.reset_index(drop=True)
    else:
        st.session_state.div_df = pd.DataFrame()
    st.session_state.reload_div_df = False


def prepare_hist_df_div(df, source_name):
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

if 'status_selecionado_div' not in st.session_state:
    st.session_state.status_selecionado_div = 'Passivo'
if 'secondary_pills_selection_div' not in st.session_state:
    default_secondary = ["As minhas", "Não resp."] if st.session_state.status_selecionado_div in ['Deferido', 'Indeferido'] else []
    st.session_state.secondary_pills_selection_div = default_secondary

st.session_state.checkbox_minhas_d = "As minhas" in st.session_state.secondary_pills_selection_div
st.session_state.checkbox_nao_respondidas_d = "Não resp." in st.session_state.secondary_pills_selection_div

with st.expander("Registro de Solicitações", expanded=True):
    colx, coly = st.columns(2, vertical_alignment="top")
    
    with colx:
        col_datas_div, col_filtros_sec_div, col_status_div = st.columns([0.9, 1.0, 1.1], vertical_alignment="center", gap="small")
        with col_status_div:
            status_options_div = ['Passivo', 'Deferido', 'Indeferido']
            current_default_status_pills_div = [st.session_state.status_selecionado_div] if st.session_state.status_selecionado_div in status_options_div else [status_options_div[0]]
            selected_status_output_div = st.pills(
                label="Filtro por Status (Diversos):", options=status_options_div,
                default=current_default_status_pills_div, key="status_pills_filter_key_div",
                help="Escolha o status do processo (Diversos)", label_visibility='collapsed'
            )
        if selected_status_output_div and selected_status_output_div != st.session_state.status_selecionado_div:
            st.session_state.status_selecionado_div = selected_status_output_div
            if st.session_state.status_selecionado_div in ['Deferido', 'Indeferido']:
                st.session_state.secondary_pills_selection_div = ["As minhas", "Não resp."]
            else:
                st.session_state.secondary_pills_selection_div = []
            st.session_state.checkbox_minhas_d = "As minhas" in st.session_state.secondary_pills_selection_div
            st.session_state.checkbox_nao_respondidas_d = "Não resp." in st.session_state.secondary_pills_selection_div
            st.rerun()

        status_para_filtragem_div = st.session_state.status_selecionado_div
        disable_secondary_pills_div = not (status_para_filtragem_div in ['Deferido', 'Indeferido'])
        if disable_secondary_pills_div and st.session_state.secondary_pills_selection_div:
            st.session_state.secondary_pills_selection_div = []
            st.session_state.checkbox_minhas_d = False
            st.session_state.checkbox_nao_respondidas_d = False

        with col_filtros_sec_div:
            opcoes_filtros_secundarios_div = ["As minhas", "Não resp."]
            selected_secondary_output_div = st.pills(
                label="Filtros Secundários (Diversos)", options=opcoes_filtros_secundarios_div,
                default=st.session_state.secondary_pills_selection_div, selection_mode="multi",
                key="filtros_pills_secundarios_key_div", help="Selecione os filtros desejados (Diversos)",
                label_visibility='collapsed', disabled=disable_secondary_pills_div
            )
        if not disable_secondary_pills_div:
            if st.session_state.secondary_pills_selection_div != selected_secondary_output_div:
                st.session_state.secondary_pills_selection_div = selected_secondary_output_div
                st.session_state.checkbox_minhas_d = "As minhas" in st.session_state.secondary_pills_selection_div
                st.session_state.checkbox_nao_respondidas_d = "Não resp." in st.session_state.secondary_pills_selection_div
                st.rerun()

        with col_datas_div:
            today_div = datetime.date.today()
            thirty_days_ago_div = today_div - datetime.timedelta(days=30)
            min_date_selectable_div = datetime.date(2020, 1, 1)
            DATE_INPUT_KEY_DIV = "date_input_div_range_key"
            if DATE_INPUT_KEY_DIV not in st.session_state:
                st.session_state[DATE_INPUT_KEY_DIV] = (thirty_days_ago_div + datetime.timedelta(days=1), today_div)
            st.date_input(
                "Intervalo de Datas (Diversos)", min_value=min_date_selectable_div, max_value=today_div,
                format="DD/MM/YYYY", label_visibility='collapsed', key=DATE_INPUT_KEY_DIV
            )
            current_range_dates_div = st.session_state[DATE_INPUT_KEY_DIV]
            if isinstance(current_range_dates_div, (tuple, list)) and len(current_range_dates_div) == 2:
                data_inicio_div, data_fim_div = current_range_dates_div
            else:
                st.toast("🛑 :red[**Intervalo de datas inválido para 'Diversos'. Usando data de hoje.**]")
                data_inicio_div = data_fim_div = today_div

        if 'div_df' not in st.session_state or st.session_state.div_df.empty:
            st.warning("Banco de Processos Diversos está vazio ou não carregado.")
            df_diversos_filtrado_final = pd.DataFrame()
        else:
            df_diversos_para_filtrar = st.session_state.div_df.copy()
            df_diversos_para_filtrar['Status'] = df_diversos_para_filtrar['Status'].replace("", "Passivo")
            if status_para_filtragem_div:
                df_diversos_filtrado_final = df_diversos_para_filtrar[df_diversos_para_filtrar['Status'] == status_para_filtragem_div].copy()
            else:
                df_diversos_filtrado_final = df_diversos_para_filtrar.copy()
            if st.session_state.checkbox_minhas_d and "Servidor" in df_diversos_filtrado_final.columns and "sessao_servidor" in st.session_state:
                df_diversos_filtrado_final = df_diversos_filtrado_final[df_diversos_filtrado_final['Servidor'] == st.session_state.sessao_servidor]
            if st.session_state.checkbox_nao_respondidas_d and "Respondido" in df_diversos_filtrado_final.columns:
                df_diversos_filtrado_final = df_diversos_filtrado_final[df_diversos_filtrado_final['Respondido'] == "Não"]
            if data_inicio_div and data_fim_div and not df_diversos_filtrado_final.empty and 'Data_Solicitacao_dt_div' in df_diversos_filtrado_final.columns:
                df_temp_date_filter = df_diversos_filtrado_final.dropna(subset=['Data_Solicitacao_dt_div'])
                if pd.api.types.is_datetime64_any_dtype(df_temp_date_filter['Data_Solicitacao_dt_div']):
                    df_diversos_filtrado_final = df_temp_date_filter[
                        (df_temp_date_filter['Data_Solicitacao_dt_div'].dt.date >= data_inicio_div) &
                        (df_temp_date_filter['Data_Solicitacao_dt_div'].dt.date <= data_fim_div) ]
                else: st.warning("Coluna 'Data_Solicitacao_dt_div' não está em formato de data para filtro.")

        cols_to_display_div = ["Código Solicitação", "Data Solicitação", "CPF / CNPJ", "Tipo Processo"]
        div_df_display = pd.DataFrame(columns=cols_to_display_div)
        if not df_diversos_filtrado_final.empty:
            actual_cols_div = [col for col in cols_to_display_div if col in df_diversos_filtrado_final.columns]
            if actual_cols_div: div_df_display = df_diversos_filtrado_final[actual_cols_div].reset_index(drop=True)

        column_config_div = {
            "Código Solicitação": st.column_config.TextColumn("Cód.", width=100),
            "Data Solicitação": st.column_config.TextColumn("Data", width=130),
            "CPF / CNPJ": st.column_config.TextColumn("CPF / CNPJ", width=160),
            "Tipo Processo": st.column_config.TextColumn("Tipo Processo", width=None) }
        if not div_df_display.empty:
            for col in div_df_display.columns:
                if col not in column_config_div: column_config_div[col] = st.column_config.TextColumn(col)

        DIV_TABLE_KEY = "div_table_selection"
        st.dataframe(
            div_df_display, key=DIV_TABLE_KEY, on_select="rerun", selection_mode="single-row",
            column_config=column_config_div, height=142, use_container_width=True, hide_index=True )
        
        total_exibido_div = len(div_df_display)
        badge_text_div = f"Exibindo: {total_exibido_div}"
        
        if 'div_df' in st.session_state and not st.session_state.div_df.empty:
            base_df_for_badge_div = st.session_state.div_df.copy()
            base_df_for_badge_div['Status'] = base_df_for_badge_div['Status'].replace("", "Passivo")
            total_passivos_badge_div = len(base_df_for_badge_div[base_df_for_badge_div['Status'] == 'Passivo'])
            if "Respondido" in base_df_for_badge_div.columns:
                total_nao_respondidos_badge_div = len(base_df_for_badge_div[base_df_for_badge_div['Respondido'] == 'Não'])
                badge_text_div += f" ~ Passivo: {total_passivos_badge_div} ~ Não respondidos: {total_nao_respondidos_badge_div}"
            else: badge_text_div += f" ~ Passivo: {total_passivos_badge_div} ~ Não respondidos: N/A"
            st.badge(badge_text_div, color="blue")
        else: st.badge(f"Exibindo: {total_exibido_div} ~ Totais Gerais: N/A", color="grey")

        selected_row_div_df = pd.DataFrame()
        st.session_state.selected_index_div = None
        if DIV_TABLE_KEY in st.session_state:
            selection_div = st.session_state[DIV_TABLE_KEY].selection
            if selection_div.rows:
                selected_df_index_div = selection_div.rows[0]
                if selected_df_index_div < len(div_df_display):
                    selected_row_div_df = div_df_display.iloc[[selected_df_index_div]]
                    if not selected_row_div_df.empty and "Código Solicitação" in selected_row_div_df.columns:
                        cod_sol_sel = selected_row_div_df["Código Solicitação"].iloc[0]
                        if not st.session_state.div_df.empty and "Código Solicitação" in st.session_state.div_df.columns:
                            original_df_matches = st.session_state.div_df[st.session_state.div_df["Código Solicitação"] == cod_sol_sel]
                            if not original_df_matches.empty: st.session_state.selected_index_div = original_df_matches.index[0]
        
        if 'div_clear_clicked' not in st.session_state: st.session_state.div_clear_clicked = False

    with coly:
        col1_y_dummy, col2_y_dummy = st.columns([0.5, 1.5], vertical_alignment="top")
        opcoes_filtro_dummy_div = ['Alfa', 'Beta', 'Gama', 'Delta']
        with col1_y_dummy:
            st.text_input("Teste 1 (desabilitado)", value="", disabled=True, label_visibility='collapsed', key="dummy_test1_coly_div")
        with col2_y_dummy:
            st.selectbox("Teste 2 (desabilitado)", opcoes_filtro_dummy_div, index=1, disabled=True, label_visibility='collapsed', key="dummy_test2_coly_div")

        if 'df_geral_2025' not in st.session_state or st.session_state.df_geral_2025 is None:
            st.session_state.df_geral_2025 = load_df_2025()
        
        df_geral_2025_hist_src = st.session_state.df_geral_2025.copy() if st.session_state.df_geral_2025 is not None else pd.DataFrame()
        div_merged_df_hist_src = st.session_state.get('merged_df', pd.DataFrame()).copy() 
        df_geral_2025_hist_prepared = prepare_hist_df_div(df_geral_2025_hist_src, '2025')
        div_merged_df_hist_prepared = prepare_hist_df_div(div_merged_df_hist_src, 'MergedDiversos')
        allin_merged_df_hist_base = pd.concat([df_geral_2025_hist_prepared, div_merged_df_hist_prepared], ignore_index=True)
        
        allin_merged_df_hist_filtered_cpf = pd.DataFrame()
        if not selected_row_div_df.empty and "CPF / CNPJ" in selected_row_div_df.columns:
            selected_cpf_cnpj_val = selected_row_div_df["CPF / CNPJ"].iloc[0]
            if selected_cpf_cnpj_val and not allin_merged_df_hist_base.empty:
                allin_merged_df_hist_filtered_cpf = allin_merged_df_hist_base[allin_merged_df_hist_base['CPF / CNPJ'] == selected_cpf_cnpj_val].copy()
        
        final_hist_df_to_display = allin_merged_df_hist_filtered_cpf.copy()
        hist_display_cols_ordered_div = ["Protocolo", "Data Criação", "CPF / CNPJ", "Tipo Processo", "Index"]
        
        if 'hist_div_df_display' not in st.session_state: st.session_state.hist_div_df_display = pd.DataFrame(columns=hist_display_cols_ordered_div)
        if st.session_state.div_clear_clicked:
            st.session_state.hist_div_df_display = pd.DataFrame(columns=hist_display_cols_ordered_div)
            st.session_state.div_clear_clicked = False 
        else:
            if not final_hist_df_to_display.empty:
                for col_d in hist_display_cols_ordered_div:
                    if col_d not in final_hist_df_to_display.columns: final_hist_df_to_display[col_d] = pd.NA
                st.session_state.hist_div_df_display = final_hist_df_to_display[hist_display_cols_ordered_div].copy()
                if 'Data Criação' in st.session_state.hist_div_df_display.columns:
                    temp_data_col = pd.to_datetime(st.session_state.hist_div_df_display['Data Criação'], format="%d/%m/%Y", errors='coerce')
                    if not temp_data_col.isna().all():
                        st.session_state.hist_div_df_display = st.session_state.hist_div_df_display.assign(temp_sort_date=temp_data_col).sort_values(by="temp_sort_date", ascending=False).drop(columns="temp_sort_date")
            else: st.session_state.hist_div_df_display = pd.DataFrame(columns=hist_display_cols_ordered_div)

        column_config_merged_div = {
            "Index": None, "Protocolo": st.column_config.TextColumn("Protocolo", width=110),
            "Data Criação": st.column_config.TextColumn("Data", width=100),
            "CPF / CNPJ": st.column_config.TextColumn("CPF / CNPJ", width=160),
            "Tipo Processo": st.column_config.TextColumn("Tipo Processo", width=None) }
        if not st.session_state.hist_div_df_display.empty:
            for col in st.session_state.hist_div_df_display.columns:
                if col not in column_config_merged_div: column_config_merged_div[col] = st.column_config.TextColumn(col)

        MERGED_DIV_TABLE_KEY = "merged_div_table_selection"
        current_hist_div_df_display_final = st.session_state.hist_div_df_display.reset_index(drop=True)
        st.dataframe(
            current_hist_div_df_display_final, key=MERGED_DIV_TABLE_KEY, on_select="rerun", selection_mode="single-row",
            column_config=column_config_merged_div, height=142, use_container_width=True, hide_index=True )
        total_exibido_hist_div = len(current_hist_div_df_display_final)
        st.badge(f"Exibindo Histórico: {total_exibido_hist_div}", color="green")

        if 'sel_merged_div_df' not in st.session_state: st.session_state.sel_merged_div_df = pd.DataFrame()
        if MERGED_DIV_TABLE_KEY in st.session_state:
            selection_merged_div = st.session_state[MERGED_DIV_TABLE_KEY].selection
            if selection_merged_div.rows:
                selected_merged_df_index_div = selection_merged_div.rows[0]
                if selected_merged_df_index_div < len(current_hist_div_df_display_final):
                    st.session_state.sel_merged_div_df = current_hist_div_df_display_final.iloc[[selected_merged_df_index_div]]
                else: st.session_state.sel_merged_div_df = pd.DataFrame()
            else: st.session_state.sel_merged_div_df = pd.DataFrame()

        @st.dialog("Detalhes do Processo Selecionado", width="large")
        def show_data_dialog_div(selected_row_data_df_arg):
            if selected_row_data_df_arg.empty or 'Index' not in selected_row_data_df_arg.columns:
                st.warning("Nenhum dado selecionado ou 'Index' ausente para exibir detalhes."); return
            unique_id_val_dialog = selected_row_data_df_arg['Index'].iloc[0]
            df_to_display_json = pd.DataFrame() 
            df_geral_2025_for_dialog = st.session_state.df_geral_2025.copy() if st.session_state.df_geral_2025 is not None else pd.DataFrame()
            merged_df_for_dialog = st.session_state.get('merged_df', pd.DataFrame()).copy()
            source_from_id = None; original_idx_from_id = None
            if isinstance(unique_id_val_dialog, str):
                parts = unique_id_val_dialog.split('_', 1)
                if len(parts) == 2:
                    source_from_id = parts[0]
                    try: original_idx_from_id = int(parts[1])
                    except ValueError: st.warning(f"ID de histórico inválido: {unique_id_val_dialog}"); return
            if source_from_id and original_idx_from_id is not None:
                temp_df_source = None
                if source_from_id == '2025': temp_df_source = df_geral_2025_for_dialog
                elif source_from_id == 'MergedDiversos': temp_df_source = merged_df_for_dialog
                if temp_df_source is not None and not temp_df_source.empty and original_idx_from_id < len(temp_df_source):
                    df_to_display_json = temp_df_source.iloc[[original_idx_from_id]].copy()
            if df_to_display_json.empty: st.warning(f"Não foi possível carregar detalhes. ID: {unique_id_val_dialog}."); return
            if 'Valor' in df_to_display_json.columns:
                df_to_display_json.loc[:, 'Valor'] = df_to_display_json['Valor'].apply( lambda x: f'R$ {float(x):,.2f}' if pd.notnull(x) and isinstance(x, (int, float)) else (x if isinstance(x, str) and x.startswith('R$') else 'R$ 0,00') )
            cols_to_drop_json = [col for col in ['index', 'level_0', 'OriginalRowIndex', 'Source', 'Index'] if col in df_to_display_json.columns]
            if cols_to_drop_json: df_to_display_json = df_to_display_json.drop(columns=cols_to_drop_json, errors='ignore')
            df_to_display_json = df_to_display_json.ffill() 
            json_data_str = df_to_display_json.to_json(orient='records', lines=False, date_format="iso", default_handler=str)
            try:
                loaded_json = json.loads(json_data_str)
                st.json(loaded_json[0] if isinstance(loaded_json, list) and loaded_json else {})
            except json.JSONDecodeError: st.error("Erro ao decodificar JSON para exibição."); st.text(json_data_str)

        if not st.session_state.sel_merged_div_df.empty:
            if 'show_details_dialog_trigger_div' not in st.session_state: st.session_state.show_details_dialog_trigger_div = False
            if 'last_selected_merged_div_index' not in st.session_state: st.session_state.last_selected_merged_div_index = None
            current_sel_index_dialog_div = None
            if not st.session_state.sel_merged_div_df.empty and 'Index' in st.session_state.sel_merged_div_df.columns:
                 current_sel_index_dialog_div = st.session_state.sel_merged_div_df['Index'].iloc[0]
            if current_sel_index_dialog_div is not None and current_sel_index_dialog_div != st.session_state.last_selected_merged_div_index:
                st.session_state.show_details_dialog_trigger_div = True; st.session_state.last_selected_merged_div_index = current_sel_index_dialog_div
            elif current_sel_index_dialog_div is None: st.session_state.last_selected_merged_div_index = None
            if st.session_state.get('show_details_dialog_trigger_div', False):
                show_data_dialog_div(st.session_state.sel_merged_div_df); st.session_state.show_details_dialog_trigger_div = False

if 'div_empty_df' not in st.session_state:
    if 'div_df' in st.session_state and not st.session_state.div_df.empty:
        empty_series_div = pd.Series(index=st.session_state.div_df.columns, dtype='object').fillna("")
    else:
        fallback_cols_div = ["Código Solicitação", "Data Solicitação", "Tipo Processo", "Ocorrências", "GDOC", "Divisão", "Razão Social", "CPF / CNPJ", "E-mail", "E-mail CC", "Complemento Valor", "Valor Unitário", "Valor Manual", "Status", "Servidor", "Data Atendimento", "Data Modificação", "Observação", "Motivo Indeferimento", "Respondido", "Docs Mesclados", "Decreto de Utilidade Pública", "CCMEI", "Ofício", "Docs Aprovação de Projeto", "Validade", "Data_Solicitacao_dt_div"]
        empty_series_div = pd.Series(index=fallback_cols_div, dtype='object').fillna("")
    st.session_state.div_empty_df = empty_series_div
treated_line_div = st.session_state.div_empty_df.copy()

# --- LÓGICA DE CARREGAMENTO DO FORMULÁRIO (SEM ALTERAÇÃO, MAS IMPORTANTE PARA O CONTEXTO) ---
if st.session_state.get('selected_index_div') is not None and 'div_df' in st.session_state and not st.session_state.div_df.empty:
    idx_to_fetch = st.session_state.selected_index_div
    if idx_to_fetch >= 0 and idx_to_fetch < len(st.session_state.div_df):
        selected_line_series_div = st.session_state.div_df.loc[idx_to_fetch]
        treated_line_div = selected_line_series_div.fillna("").copy()
    else:
        st.warning(f"Índice ({idx_to_fetch}) fora dos limites. Resetando seleção.")
        st.session_state.selected_index_div = None
        if DIV_TABLE_KEY in st.session_state and hasattr(st.session_state[DIV_TABLE_KEY], 'selection'):
             st.session_state[DIV_TABLE_KEY].selection.rows = []

# --- BLOCO PROBLEMÁTICO REMOVIDO/SIMPLIFICADO ---
# A lógica que estava aqui (`if st.session_state.btn_clear_d:`) foi removida, 
# pois a limpeza agora é tratada de forma mais direta.
if 'btn_clear_d' not in st.session_state:
    st.session_state.btn_clear_d = False
    st.session_state.disable_file_uploader = True
    st.session_state.disable_btn_save_d = True
    st.session_state.disable_btn_edit_d = True
    st.session_state.disable_btn_send_d = True

show_expander_2 = bool("Código Solicitação" in treated_line_div and len(str(treated_line_div.get("Código Solicitação",""))) > 1)
with st.expander("Detalhes da solicitação", expanded=show_expander_2):
    st.write("")
    with st.form("form_diversos", border=False):
        codigo_solicitacao_d_form_val = treated_line_div.get("Código Solicitação", "")
        is_record_loaded_for_form = bool(codigo_solicitacao_d_form_val)
        col1_form, col2_form, col3_form, col4_form, col5_form, col6_form, col7_form, col8_form = st.columns([2,0.6,0.6,1.2,0.6,0.6,0.2,0.1], vertical_alignment="bottom")
        tipo_processo_d_form_val = treated_line_div.get("Tipo Processo", "")
        tipo_processo_d_input = col1_form.text_input("Tipo Processo", value=tipo_processo_d_form_val, key="form_d_tipo_proc", disabled=True)
        codigo_solicitacao_d_input = col2_form.text_input("Cód. Solicitação", value=codigo_solicitacao_d_form_val, key="form_d_cod_sol", disabled=is_record_loaded_for_form)
        data_solicitacao_d_form_val = treated_line_div.get("Data Solicitação", "")
        data_solicitacao_d_input = col3_form.text_input("Data Solicitação", value=data_solicitacao_d_form_val, key="form_d_data_sol", disabled=True)
        ocorrencias_d_form_val = treated_line_div.get("Ocorrências", "")
        btn_ocorrencias_label_form = f"{ocorrencias_d_form_val} 👁️" if ocorrencias_d_form_val else "Ocorrências 👁️"
        btn_ocorrencias_disabled_form = not bool(ocorrencias_d_form_val)
        btn_ocorrencias_form = col4_form.form_submit_button(
            btn_ocorrencias_label_form, type="primary", use_container_width=True,
            disabled=btn_ocorrencias_disabled_form, help="Ver Ocorrências"
        )
        gdoc_d_form_val = treated_line_div.get("GDOC", "")
        gdoc_d_form_input = col5_form.text_input("GDOC/Ano (xx/AA) *", value=gdoc_d_form_val, key="form_d_gdoc")
        
        divisao_options_form_d_sel = ['DVSA', 'DVSE', 'DVSCEP', 'DVSDM', 'Visamb', 'Açaí']
        status_options_form_d_sel = ['Passivo', 'Deferido', 'Indeferido']
        
        divisao_index_d_form = None
        if is_record_loaded_for_form:
            divisao_from_data = str(treated_line_div.get("Divisão", "")).strip()
            if divisao_from_data in divisao_options_form_d_sel:
                divisao_index_d_form = divisao_options_form_d_sel.index(divisao_from_data)

        divisao_d_form_selectbox = col6_form.selectbox(
            "Divisão *", 
            options=divisao_options_form_d_sel, 
            index=divisao_index_d_form,
            placeholder="..."
        )

        respondido_val_form = treated_line_div.get("Respondido", "")
        status_icon_d_form = ":material/pending:"
        if respondido_val_form == "Sim": status_icon_d_form = ":material/check_circle:"
        elif respondido_val_form == "Não": status_icon_d_form = ":material/do_not_disturb_on:"
        col7_form.header(status_icon_d_form, anchor=False)
        col1_f2, col2_f2, col3_f2, col4_f2, col5_f2 = st.columns([2,1,0.4,1,1], vertical_alignment="bottom")
        razao_social_d_form_input = col1_f2.text_input("Nome Empresa", value=treated_line_div.get("Razão Social", ""), key="form_d_razao_social_input")
        cpf_cnpj_d_form_input = col2_f2.text_input("CPF / CNPJ", value=treated_line_div.get("CPF / CNPJ", ""), key="form_d_cpf_cnpj_input")
        btn_cnpj_d_form = col3_f2.form_submit_button("🔎", use_container_width=True, help="Buscar CNPJ/CPF")
        email1_d_form_input = col4_f2.text_input("E-mail", value=treated_line_div.get("E-mail", ""), key="form_d_email1_input")
        email2_d_form_input = col5_f2.text_input("E-mail CC", value=treated_line_div.get("E-mail CC", ""), key="form_d_email2_input")
        col1_f3, col2_f3, col3_f3, col4_f3, col5_f3, col6_f3, col7_f3 = st.columns([1.5,0.7,0.7,0.8,1,0.7,0.7], vertical_alignment="bottom")
        comp_valor_un_d_form_input = col1_f3.text_input("Comp. Valor", value=treated_line_div.get("Complemento Valor", ""), key="form_d_comp_valor_input")
        valor_un_d_form_input = col2_f3.text_input("Valor Unit.", value=treated_line_div.get("Valor Unitário", ""), key="form_d_valor_unit_input")
        current_valor_manual_d_form = treated_line_div.get("Valor Manual", "")
        if comp_valor_un_d_form_input not in ['', 'Pessoa Física', 'Empresa Privada'] and not current_valor_manual_d_form :
            current_valor_manual_d_form = 'R$ 0,00'
        valor_manual_d_form_input = col3_f3.text_input("Valor do DAM *", value=current_valor_manual_d_form, key="form_d_valor_manual_input")

        status_index_d_form = None
        if is_record_loaded_for_form:
            status_from_data = treated_line_div.get("Status", "") or "Passivo"
            if status_from_data in status_options_form_d_sel:
                status_index_d_form = status_options_form_d_sel.index(status_from_data)
        
        status_d_form_selectbox = col4_f3.selectbox(
            "Status *", 
            options=status_options_form_d_sel,
            index=status_index_d_form,
            placeholder="..."
        )

        servidor_d_form_input = col5_f3.text_input("Servidor", value=treated_line_div.get("Servidor", st.session_state.get("sessao_servidor","")), key="form_d_servidor_input", disabled=True)
        data_atendimento_d_form_input = col6_f3.text_input("Data At.", value=treated_line_div.get("Data Atendimento", ""), key="form_d_data_at_input", disabled=True)
        data_modificacao_d_form_input = col7_f3.text_input("Data Mod.", value=treated_line_div.get("Data Modificação", ""), key="form_d_data_mod_input", disabled=True)
        col1_f4, col2_f4, col3_f4 = st.columns(3, vertical_alignment="top")
        observacao_d_form_input = col1_f4.text_area("Observação", value=treated_line_div.get("Observação", ""), height=77, key="form_d_obs_input")
        motivo_indeferimento_d_form_input = col2_f4.text_area("Motivo Indeferimento *", value=treated_line_div.get("Motivo Indeferimento", ""), height=77, key="form_d_motivo_ind_input")
        disable_file_uploader_form = True; disable_btn_save_d_form = True
        disable_btn_edit_d_form = True; disable_btn_send_d_form = True
        
        effective_status_form = status_d_form_selectbox
        
        if st.session_state.get('clicou_no_editar_d', False):
            disable_btn_save_d_form = False; disable_btn_edit_d_form = True
            if effective_status_form == 'Deferido': disable_file_uploader_form = False
        else:
            if effective_status_form == 'Passivo':
                disable_btn_save_d_form = False
                if is_record_loaded_for_form: disable_btn_edit_d_form = False
                else: disable_btn_edit_d_form = True
            elif effective_status_form == 'Deferido':
                disable_file_uploader_form = False; disable_btn_send_d_form = False
                if is_record_loaded_for_form: disable_btn_edit_d_form = False
                else: disable_btn_save_d_form = False
            elif effective_status_form == 'Indeferido':
                disable_btn_send_d_form = False
                if is_record_loaded_for_form: disable_btn_edit_d_form = False
                else: disable_btn_save_d_form = False
        if not is_record_loaded_for_form:
            disable_btn_edit_d_form = True
            disable_btn_send_d_form = True
        
        cartao_protocolo_d_form_uploader = col3_f4.file_uploader(
            "Anexar Cartão do Protocolo *", accept_multiple_files=False, type=['pdf'],
            disabled=disable_file_uploader_form, key="form_d_cartao_prot_upload"
        )
        st.write("")
        link_cols_r1_form = st.columns(4); link_cols_r2_form = st.columns(4)
        all_link_cols_form = link_cols_r1_form + link_cols_r2_form; link_idx_form = 0
        cabecalho_url_form_list = ["Docs Mesclados", "Decreto de Utilidade Pública", "CCMEI", "Ofício"]
        for header_key_form in cabecalho_url_form_list:
            url_val_form = treated_line_div.get(header_key_form)
            if isinstance(url_val_form, str) and url_val_form.startswith("http") and link_idx_form < len(all_link_cols_form):
                all_link_cols_form[link_idx_form].link_button(f"🔗 {header_key_form}", url_val_form, use_container_width=True); link_idx_form +=1
        projeto_urls_form_list_val = treated_line_div.get("Docs Aprovação de Projeto", "")
        if "aprovação de Projeto" in tipo_processo_d_input and isinstance(projeto_urls_form_list_val, str) and projeto_urls_form_list_val.strip():
            projeto_urls_list_display = [f"https://{u.strip()}" for u in projeto_urls_form_list_val.split("https://") if u.strip()]
            titulos_projeto_form = ["Localiz. e Situação", "Planta Baixa", "Layout", "Cortes"]
            for i_form, url_proj_form in enumerate(projeto_urls_list_display):
                if link_idx_form < len(all_link_cols_form):
                    titulo_link_proj_form = titulos_projeto_form[i_form] if i_form < len(titulos_projeto_form) else f"Prancha {i_form+1}"
                    all_link_cols_form[link_idx_form].link_button(f"🔗 {titulo_link_proj_form}", url_proj_form, use_container_width=True); link_idx_form +=1
        st.write("")
        action_cols_form = st.columns(8, vertical_alignment="bottom", gap="small")
        btn_clear_d_form_submit = action_cols_form[7].form_submit_button("🧹 Limpar", use_container_width=True, disabled=not is_record_loaded_for_form) # Habilitado se houver registro
        btn_save_d_form_submit = action_cols_form[6].form_submit_button("💾 Salvar", use_container_width=True, disabled=disable_btn_save_d_form, type='primary')
        btn_edit_d_form_submit = action_cols_form[5].form_submit_button("📝 Editar", use_container_width=True, disabled=disable_btn_edit_d_form)
        btn_send_d_form_submit = action_cols_form[4].form_submit_button("📧 Enviar", use_container_width=True, disabled=disable_btn_send_d_form, type='primary')
        action_cols_form[3].link_button("📋 Requisitos", "https://sites.google.com/view/secretariadevisa/in%C3%ADcio/processos/requisitos?authuser=0", use_container_width=True)
        action_cols_form[2].link_button("🌍 GDOC", "https://gdoc.belem.pa.gov.br/gdocprocessos/processo/pesquisarInteressado", use_container_width=True)
        if 'toast_msg_success' not in st.session_state: st.session_state.toast_msg_success = False
        if st.session_state.toast_msg_success: st.toast("Dados salvos ✨✨"); st.session_state.toast_msg_success = False

        # --- FUNÇÃO DE LIMPEZA SIMPLIFICADA (AGORA SÓ PARA O BOTÃO) ---
        def btn_clear_fn_form_d_action():
            st.session_state.selected_index_div = None
            st.session_state.clicou_no_editar_d = False
            st.rerun()

        if btn_clear_d_form_submit: btn_clear_fn_form_d_action()
        
        if btn_ocorrencias_form:
            cpf_cnpj_para_ocorrencia = cpf_cnpj_d_form_input
            if cpf_cnpj_para_ocorrencia: get_ocorrencias(cpf_cnpj_para_ocorrencia, "diversos")
            else: st.toast("CPF/CNPJ necessário para buscar Ocorrências.")
        if btn_cnpj_d_form:
            cpf_cnpj_para_busca = cpf_cnpj_d_form_input
            if cpf_cnpj_para_busca and (len(cpf_cnpj_para_busca) == 14 or len(cpf_cnpj_para_busca) == 18): 
                get_cnpj(cpf_cnpj_para_busca, '', '')
            else: st.toast(":orange[CNPJ/CPF inválido para busca.]")
        if 'clicou_no_editar_d' not in st.session_state: st.session_state.clicou_no_editar_d = False
        if btn_edit_d_form_submit:
            st.session_state.clicou_no_editar_d = True; st.rerun()

        # --- INÍCIO DO BLOCO ALTERADO ---
        # --- FUNÇÃO DE SALVAR COM LÓGICA DE RESET CORRIGIDA ---
        def save_in_sheet_d_action(btn_edit_mode_action: bool):
            st.toast("Tentando salvar os dados. Aguarde...")
            cod_sol_save = codigo_solicitacao_d_input
            tipo_proc_save = tipo_processo_d_input
            data_sol_save = data_solicitacao_d_input
            status_save = status_d_form_selectbox
            
            if not cod_sol_save:
                st.toast("🔴 :red[**Código da Solicitação é obrigatório para salvar.**]"); return
            if not tipo_proc_save:
                 st.toast("🔴 :red[**Tipo de Processo é obrigatório para salvar.**]"); return
            
            divisao_save = divisao_d_form_selectbox
            gdoc_save = gdoc_d_form_input
            valor_manual_save = valor_manual_d_form_input
            motivo_ind_save = motivo_indeferimento_d_form_input
            
            divisao_list_valid_save = divisao_options_form_d_sel
            treated_valor_manual_to_save = extrair_e_formatar_real(valor_manual_save)
            gdoc_is_valid_to_save = validate_gdoc(gdoc_save, data_sol_save)

            # --- MUDANÇA 1: CONDIÇÃO DE INDEFERIDO ALTERADA ---
            # A verificação de 'divisao_save' foi removida. Apenas o motivo é obrigatório.
            cond_deferido_to_save = (status_save == "Deferido" and gdoc_is_valid_to_save and (divisao_save in divisao_list_valid_save) and bool(treated_valor_manual_to_save))
            cond_indeferido_to_save = (status_save == "Indeferido" and len(motivo_ind_save or "") > 10)
            cond_passivo_to_save = (status_save == "Passivo")

            if cond_deferido_to_save or cond_indeferido_to_save or cond_passivo_to_save:
                worksheet_save_d = get_worksheet(1, st.secrets['sh_keys']['geral_major'])
                cell_save_d = worksheet_save_d.find(cod_sol_save, in_column=1)
                is_new_record_form = not bool(cell_save_d)

                if is_new_record_form:
                    # Lógica para novo registro
                    razao_social_save = razao_social_d_form_input; cpf_cnpj_save = cpf_cnpj_d_form_input
                    email1_save = email1_d_form_input; email2_save = email2_d_form_input
                    obs_save = observacao_d_form_input; comp_valor_save = comp_valor_un_d_form_input
                    valor_unit_save = valor_un_d_form_input
                    divisao_to_sheet = divisao_save if divisao_save is not None else ""
                    
                    # --- MUDANÇA 2: VALOR DO DAM PARA NOVO REGISTRO INDEFERIDO ---
                    valor_para_salvar_novo = ""
                    if status_save == "Deferido":
                        valor_para_salvar_novo = treated_valor_manual_to_save
                    elif status_save == "Indeferido":
                        valor_para_salvar_novo = "R$ 0,00" # Força o valor a ser R$ 0,00
                    else: # Passivo
                        valor_para_salvar_novo = valor_manual_save

                    new_row_values = [
                        cod_sol_save, data_sol_save, tipo_proc_save, razao_social_save, cpf_cnpj_save, "Válido",
                        "", valor_unit_save, comp_valor_save, obs_save, email1_save, email2_save, "", "", "", "",
                        cod_sol_save, valor_para_salvar_novo, # Usa a variável definida acima
                        status_save, st.session_state.get("sessao_servidor", ""),
                        get_current_datetime() if status_save != "Passivo" else "",
                        get_current_datetime() if status_save != "Passivo" else "",
                        motivo_ind_save if status_save == "Indeferido" else "", "",
                        gdoc_save if status_save != "Passivo" else "",
                        divisao_to_sheet, "Não", "", "", "", ""
                    ]
                    worksheet_save_d.append_row(new_row_values, value_input_option='USER_ENTERED')
                    
                elif cell_save_d:
                    # Lógica de atualização
                    servidor_atual_ws = worksheet_save_d.cell(cell_save_d.row, 20).value
                    if servidor_atual_ws and servidor_atual_ws != st.session_state.get("sessao_servidor") and not btn_edit_mode_action and status_save != "Passivo":
                        st.toast(f"🔴 :red[**Erro! Sol. já tratada por '{servidor_atual_ws}'.**]"); return
                    
                    current_time = get_current_datetime()
                    
                    if status_save == "Deferido":
                        final_valor = treated_valor_manual_to_save; final_servidor = st.session_state.get("sessao_servidor", "")
                        final_dt_at = current_time; final_dt_mod = current_time
                        final_motivo = ""; final_gdoc = gdoc_save
                        final_divisao = divisao_save or ""
                    
                    elif status_save == "Indeferido":
                        # --- MUDANÇA 3: VALOR DO DAM PARA ATUALIZAÇÃO DE INDEFERIDO ---
                        final_valor = "R$ 0,00" # Força o valor a ser R$ 0,00
                        final_servidor = st.session_state.get("sessao_servidor", "")
                        final_dt_at = current_time; final_dt_mod = current_time
                        final_motivo = motivo_ind_save; final_gdoc = gdoc_save
                        final_divisao = divisao_save or ""
                    
                    else: # Passivo
                        final_valor = valor_manual_save; final_servidor = ""
                        final_dt_at = ""; final_dt_mod = ""
                        final_motivo = ""; final_gdoc = ""
                        final_divisao = ""

                    respondido_original = worksheet_save_d.cell(cell_save_d.row, 27).value or "Não"

                    values_to_update = [
                        cod_sol_save, final_valor, status_save, final_servidor, final_dt_at,
                        final_dt_mod, final_motivo, "", final_gdoc, final_divisao, respondido_original
                    ]
                    
                    range_to_update = f"Q{cell_save_d.row}:AA{cell_save_d.row}"
                    worksheet_save_d.update(range_to_update, [values_to_update])

                # --- LÓGICA DE RESET PÓS-SALVAMENTO (CORRIGIDA) ---
                st.session_state.toast_msg_success = True
                st.session_state.clicou_no_editar_d = False
                st.session_state.reload_div_df = True
                load_div_df.clear()
                st.session_state.selected_index_div = None
                st.rerun()

            else: # Lógica de validação
                if status_save == "Deferido":
                    if not gdoc_is_valid_to_save: st.toast("🔴 Formato GDOC inválido.")
                    elif not (divisao_save in divisao_list_valid_save): st.toast("🔴 Divisão inválida para Deferir.")
                    elif not bool(treated_valor_manual_to_save): st.toast("🔴 Valor do DAM obrigatório e > R$ 0,00 para Deferir.")
                elif status_save == "Indeferido":
                    # --- MUDANÇA 4: REMOÇÃO DA MENSAGEM DE ERRO DE DIVISÃO ---
                    if not (len(motivo_ind_save or "") > 10): st.toast("🔴 Motivo indeferimento curto.")

        if btn_save_d_form_submit: save_in_sheet_d_action(st.session_state.clicou_no_editar_d)
        # --- FIM DO BLOCO ALTERADO ---
        
        # --- LÓGICA DE E-MAIL (COM AJUSTE NA CHAMADA DE LIMPEZA) ---
        if 'is_email_sended_d' not in st.session_state: st.session_state.is_email_sended_d = False
        def mark_email_as_sent_d_action():
            cod_sol_email = codigo_solicitacao_d_input
            ws_email = get_worksheet(1, st.secrets['sh_keys']['geral_major'])
            cell_email = ws_email.find(cod_sol_email, in_column=1)
            if cell_email:
                link_cartao_gdrive_email = st.session_state.get("gdrive_link_do_cartao_d", "")
                if link_cartao_gdrive_email: ws_email.update_acell(f'X{cell_email.row}', link_cartao_gdrive_email)
                ws_email.update_acell(f'AA{cell_email.row}', "Sim")
            
            # --- USA A MESMA LÓGICA DE RESET DO SALVAMENTO ---
            st.session_state.pop("gdrive_link_do_cartao_d", None); st.session_state.is_email_sended_d = False
            st.session_state.clicou_no_editar_d = False
            st.session_state.reload_div_df = True
            load_div_df.clear()
            st.session_state.selected_index_div = None
            st.rerun()

        def send_mail_d_action():
            status_send = status_d_form_selectbox
            gdoc_send = gdoc_d_form_input
            divisao_send = divisao_d_form_selectbox
            email_diversos(
                kw_status=status_send, kw_gdoc=gdoc_send, kd_divisao=divisao_send,
                kw_protocolo=codigo_solicitacao_d_input, kw_data_sol=data_solicitacao_d_input,
                kw_tipo_proc=tipo_processo_d_input, kw_razao_social=razao_social_d_form_input,
                kw_cpf_cnpj=cpf_cnpj_d_form_input, kw_cartao_protocolo=cartao_protocolo_d_form_uploader,
                kw_email1=email1_d_form_input, kw_email2=email2_d_form_input,
                kw_motivo_indeferimento=motivo_indeferimento_d_form_input )

        if btn_send_d_form_submit:
            tipo_proc_send_btn = tipo_processo_d_input; cod_sol_send_btn = codigo_solicitacao_d_input
            status_send_btn = status_d_form_selectbox
            divisao_send_btn = divisao_d_form_selectbox
            gdoc_send_btn = gdoc_d_form_input; data_sol_send_btn = data_solicitacao_d_input
            cartao_send_btn = cartao_protocolo_d_form_uploader; motivo_send_btn = motivo_indeferimento_d_form_input
            valor_manual_send_btn = valor_manual_d_form_input
            if tipo_proc_send_btn and cod_sol_send_btn:
                div_list_send = divisao_options_form_d_sel
                gdoc_valid_send = validate_gdoc(gdoc_send_btn, data_sol_send_btn)
                prot_file_valid_send = False
                if cartao_send_btn: prot_file_valid_send = validate_protocolo(cartao_send_btn.name, gdoc_send_btn)
                val_manual_ok_send = bool(extrair_e_formatar_real(valor_manual_send_btn))
                cond_def_send = (status_send_btn == "Deferido" and (divisao_send_btn in div_list_send) and gdoc_valid_send and cartao_send_btn and prot_file_valid_send and val_manual_ok_send)
                cond_ind_send = (status_send_btn == "Indeferido" and (divisao_send_btn in div_list_send) and len(motivo_send_btn or "") > 10)
                if cond_def_send or cond_ind_send:
                    st.toast(f"Tentando responder '{cod_sol_send_btn}'. Aguarde..."); send_mail_d_action()
                    if st.session_state.is_email_sended_d: mark_email_as_sent_d_action()
                else:
                    if status_send_btn == "Deferido":
                        if not (divisao_send_btn in div_list_send): st.toast("🔴 Divisão inválida p/ Envio Deferido.");
                        elif not gdoc_valid_send: st.toast(f"🔴 Formato GDOC inválido.");
                        elif not cartao_send_btn: st.toast("🔴 Cartão do protocolo não anexado.");
                        elif not prot_file_valid_send: st.toast("🔴 Nome arquivo protocolo não corresponde ao GDOC.");
                        elif not val_manual_ok_send: st.toast("🔴 Para Deferir, Valor DAM > R$ 0,00.");
                    elif status_send_btn == "Indeferido":
                        if not (divisao_send_btn in div_list_send): st.toast("🔴 Divisão inválida p/ Envio Indeferido.");
                        elif not (len(motivo_send_btn or "") > 10): st.toast("🔴 Motivo indeferimento curto p/ Envio.");
            else: st.toast("🔴 Cód. Solicitação e Tipo de Processo obrigatórios p/ Envio.");