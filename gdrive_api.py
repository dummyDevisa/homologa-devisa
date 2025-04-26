import json
from googleapiclient.discovery import build
from google.oauth2 import service_account
import streamlit as st
# from proxy import *

conn_service_account = f"""
{{
  "type": "{st.secrets["conn_google"]["type"]}",
  "project_id": "{st.secrets["conn_google"]["project_id"]}",
  "private_key_id": "{st.secrets["conn_google"]["private_key_id"]}",
  "private_key": "{st.secrets["conn_google"]["private_key"]}",
  "client_email": "{st.secrets["conn_google"]["client_email"]}",
  "client_id": "{st.secrets["conn_google"]["client_id"]}",
  "auth_uri": "{st.secrets["conn_google"]["auth_uri"]}",
  "token_uri": "{st.secrets["conn_google"]["token_uri"]}",
  "auth_provider_x509_cert_url": "{st.secrets["conn_google"]["auth_provider_x509_cert_url"]}",
  "client_x509_cert_url": "{st.secrets["conn_google"]["client_x509_cert_url"]}",
  "universe_domain": "{st.secrets["conn_google"]["universe_domain"]}"
}}
"""

# Converter a string JSON para um dicionário
credentials_dict = json.loads(conn_service_account)

# Criar credenciais usando o dicionário
credentials = service_account.Credentials.from_service_account_info(
    credentials_dict,
    scopes=[
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/documents"
    ]
)

id_folder_24 = '1uzZRh31e4REfQ-iNdc2gWOIgoDn3xZmr'
id_folder_25 = '14mKMpOxXTe-JmymtqQn0mTTabIRhXuDB'
id_folder_26 = '1GiQD7bR4KrPDlxHTGlDuzrmAANxECrYb'
id_folder_27 = '1wUEOoCqW7XgxI_fmfwvsSln4vTVr9uR3'
id_folder_28 = '1jZXkTunyWA2llWWlFeHXLvxU2pUqaDQU'

# ID do modelo de LF Google Drive (com e sem assinatura)
FILE_WITH_SUB = "1e8MZ7wjgT-xwA_QerNfSVCzgP2djE8B6_trlSTOR6WU"
FILE_WITHOUT_SUB = "1pAdilPZk3c5bR8qRL5BRgRD7n8rAb-eSn2NfYJWPlQA"

# [proc, num_lf, atividade, comercializar, CNAE, descricao, razao_social, CPF-CNPJ, endereco, complemento,
    # numero, bairro, CEP, responsavel, conselho, data_emissao, ano_lf, divisao, formula_planilha, status,
    # obs, via, servidor, data_modificacao, url_lf_digitada]
def gerar_doc_lf(list_repl: list):
    st.toast(f":orange[Criando o arquivo da LF {st.session_state.fi_lf}...]")

    yy = str(list_repl[16][2:4])  # Ano YY do processo em questão
    FILE_ID = FILE_WITHOUT_SUB
    
    match yy:
        case '24':
            parent_id = id_folder_24
            FILE_ID = FILE_WITH_SUB
        case '25':
            parent_id = id_folder_25
        case '26':
            parent_id = id_folder_26
        case '27':
            parent_id = id_folder_27
        case '28':
            parent_id = id_folder_28


    # # if 'cli_gdrive' not in st.session_state:
    # #     st.session_state.cli_gdrive = False

    # if not st.session_state.cli_gdrive: 
    #     # Inicializar o cliente Google Drive e Google Docs     
    #     drive_service = build("drive", "v3", credentials=credentials)
    #     docs_service = build("docs", "v1", credentials=credentials)

    #     st.session_state.cli_gdrive = True
    
  
    # Inicializar o cliente Google Drive e Google Docs     
    drive_service = build("drive", "v3", credentials=credentials)
    docs_service = build("docs", "v1", credentials=credentials)


    # Nome da cópia a ser criada
    # dd/mm/yy, hh:mm
    #[0:2] / [3:5] / [6:8] / [10:12]- [13:15]
    # PROC_XXXX-ANO_XXXX_XVIA_TIMESTAMP_dd-mm-yy-hhh-mm

    COPY_NAME = f"P{list_repl[0]}_Y{list_repl[16]}_{list_repl[21][:1]}VIA_T{list_repl[23][:2]}{list_repl[23][3:5]}{list_repl[23][6:8]}_{list_repl[23][10:12]}H{list_repl[23][13:15]}"

    # Criar uma cópia do arquivo
    st.toast(f"Criando cópia do modelo de LF...")

    copied_file = drive_service.files().copy(
        fileId=FILE_ID,
        body={
            "name": COPY_NAME,
            "parents": [parent_id]  # Define a pasta onde o arquivo será salvo
        }
    ).execute()

    copied_file_id = copied_file["id"]
    #print(f"Cópia criada com sucesso: {COPY_NAME} (ID: {copied_file_id})")
    
    # Texto a ser substituído e os respectivos substitutos
    placeholders = ["{proc}", "{YYYY}", "{divisao}", "{LF}", "{YY}",
                    "{validade}", "{atividade}", "{comercializar}",
                    "{código}", "{descricao}", "{razao social}",
                    "{cpf/cnpj}", "{logradouro}", "{complemento}", "{numero}",
                    "{bairro}", "{cep}", "{responsavel}", "{conselho}", "{emissao}", "{n-via}"]
    
    # [proc, num_lf, atividade, comercializar, CNAE, descricao, razao_social, CPF-CNPJ, endereco, complemento,
    # numero, bairro, CEP, responsavel, conselho, data_emissao, ano_lf, divisao, formula_planilha, status,
    # obs, via, servidor, data_modificacao, url_lf_digitada]

    n_lf = str(list_repl[1])
    if not n_lf.isdigit():
        raise ValueError("Gdrive: A entrada deve ser uma string contendo apenas dígitos.")
    
    list_repl[1] = n_lf.zfill(4)
    

    replacements = [
        str(value) if value is not None else ""
        for value in [
            list_repl[0], list_repl[16], list_repl[17], list_repl[1], list_repl[16][2:4],
            f"31/03/{int(list_repl[16])+1}", list_repl[2], list_repl[3],
            list_repl[4], list_repl[5], list_repl[6],
            list_repl[7], list_repl[8], list_repl[9], list_repl[10],
            list_repl[11], list_repl[12], list_repl[13], list_repl[14], list_repl[15], list_repl[21]
        ]
    ]

    #print(f"replacements: {replacements}")

    concat_cod_desc = f"CÓDIGO:_{list_repl[4]}_______DESCRIÇÃO:_{list_repl[5]}"
    lenght_above = [list_repl[0], list_repl[21], list_repl[1], list_repl[17], list_repl[2], list_repl[3]]
    
    total_alguns = 0
    
    for x in lenght_above:
      total_alguns += len(x)

    cod_desc_len = len(concat_cod_desc)

    # Definir os índices do texto a ser substituído
    # start_index = 410
    start_index = 341 - 30 + 45 + total_alguns
    end_index = (start_index + cod_desc_len) - 4

    # Determinar o tamanho da fonte com base no comprimento do texto
    if 480 <= cod_desc_len <= 670:
        font_size = 10
    elif 670 < cod_desc_len <= 835:
        font_size = 9
    elif 835 < cod_desc_len <= 906:
        font_size = 8
    elif cod_desc_len > 906:
        font_size = 7
    else:
        font_size = 12  # Valor padrão para textos curtos

    # Criar a lista de operações de substituição
    #st.toast(f"Editando e salvando o documento...")
    requests = [
        {
            "replaceAllText": {
                "containsText": {
                    "text": placeholder,
                    "matchCase": True,
                },
                "replaceText": replacement,
            }
        }
        for placeholder, replacement in zip(placeholders, replacements)
    ]

    # Adicionar operação para alterar o tamanho da fonte do texto inserido
    requests.append(
        {
            "updateTextStyle": {
                "range": {
                    "startIndex": start_index,
                    "endIndex": end_index,
                },
                "textStyle": {
                    "fontSize": {
                        "magnitude": font_size,
                        "unit": "PT",
                    }
                },
                "fields": "fontSize",
            }
        }
    )

    # Adicionar operação para justificar o alinhamento
    requests.append(
        {
            "updateParagraphStyle": {
                "range": {
                    "startIndex": start_index,
                    "endIndex": end_index,
                },
                "paragraphStyle": {
                    "alignment": "JUSTIFIED",  # Alinhamento justificado
                },
                "fields": "alignment",
            }
        }
    )


    # Enviar todas as operações em uma única requisição
    result = docs_service.documents().batchUpdate(
        documentId=copied_file_id, body={"requests": requests}
    ).execute()

    st.toast(":green[Documento criado com sucesso.]")
    return copied_file_id
