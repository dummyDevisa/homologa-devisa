import streamlit as st

st.set_page_config(
    page_title="Processos DEVISA 2025",
    page_icon="🍨",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items = None
)

import pandas as pd
from load_functions import *
from cookies import *
from logon import *
from webdriver import *

# variáveis de ambiente para proxy
# from proxy import *

hide_txtform()

if 'my_ip' not in st.session_state:
    # st.session_state.my_ip = rk()
    st.session_state.my_ip = get_client_uuid()

if 'sessao_ip' not in st.session_state:
    st.session_state.sessao_ip = get_client_ip()

if st.session_state.my_ip == None:
   st.session_state.my_ip = get_client_uuid()

# diálogo do sistema
if 'placeholder_dialog' not in st.session_state:
    st.session_state.placeholder_dialog = st.empty()

# tratamento usuários cadastrados
if 'usr_list' not in st.session_state:
    st.session_state.usr_list = None

# usuarios cadastrados
if st.session_state.usr_list is None:
    usr_list = load_auth_usr()
    name_list = usr_list['Name'].tolist()
    st.session_state.usr_list = usr_list

usr_list = st.session_state.usr_list
# print(f'usr_list: {usr_list}')

if 'sessao_servidor' not in st.session_state: 
    st.session_state.sessao_servidor = ''


if 'logo_sesma' not in st.session_state:
    st.session_state.logo_sesma = "resources/logo_sesma_chopped.png"

if 'error' not in st.session_state:
    st.session_state.error = ""

if 'auth_user' not in st.session_state:
    st.session_state.auth_user = None
    st.session_state.privilege = None

if 'df_geral_2025' not in st.session_state:
    st.session_state.df_geral_2025 = None

def cadastro():
    interface_cadastro(usr_list)

def sair():
    delete_cookie(f"usr_sess_{st.session_state.my_ip}")
    st.rerun()
    streamlit_js_eval(js_expressions="parent.window.location.reload()")

def senha():
   interface_senha(usr_list, st.session_state.auth_user)

def open_system(user, privilege):
    st.session_state.auth_user = user
    st.session_state.privilege = privilege
    match privilege:
        case 'adm':
            pages = {
                "Serviços": [
                    st.Page("pages_/servicos/licencas.py", title="Licenciamento", icon=":material/docs:"),
                    st.Page("pages_/servicos/diversos.py", title="Diversos", icon=":material/note_add:"),
                    st.Page("pages_/servicos/taxas.py", title="Taxas", icon=":material/paid:"),
                    st.Page("pages_/servicos/presencial.py", title="Protocolo", icon=":material/auto_stories:"),
                    st.Page("pages_/servicos/suporte.py", title="Canal de suporte", icon=":material/support_agent:"),
                ],
                "Documentos": [
                    st.Page("pages_/documentos/digitacao.py", title="Geração de LFs", icon=":material/contract:"),
                    st.Page("pages_/documentos/certificacao.py", title="Certificação de LFs", icon=":material/qr_code_2_add:"),
                    st.Page("pages_/documentos/pranchas.py", title="Chancela de Pranchas", icon=":material/approval:"),
                ],
                "Recursos": [
                    st.Page("pages_/recursos/pesquisa.py", title="Pesquisa", icon=":material/search:"),
                    st.Page("pages_/recursos/assistente.py", title="Assistente IA", icon=":material/robot_2:"),
                ],
                "Relatórios":[
                    st.Page("pages_/relatorios/overview.py", title="Resumo", icon=":material/wallpaper:", default=True),
                    st.Page("pages_/relatorios/dashboard.py", title="Dashboard", icon=":material/space_dashboard:"),
                ],
                "Sessão": [
                    st.Page(sair, title="Sair", icon=":material/logout:", url_path="/"),
                    st.Page(cadastro, title="Cadastro", icon=":material/person:"),
                    st.Page(senha, title="Mudar senha", icon=":material/passkey:")
                ],
            }
        case 'normal':
            pages = {
                "Serviços": [
                    st.Page("pages_/servicos/licencas.py", title="Licenciamento", icon=":material/docs:"),
                    st.Page("pages_/servicos/diversos.py", title="Diversos", icon=":material/note_add:"),
                    st.Page("pages_/servicos/taxas.py", title="Taxas", icon=":material/paid:"),
                    st.Page("pages_/servicos/presencial.py", title="Protocolo", icon=":material/auto_stories:"),
                    st.Page("pages_/servicos/suporte.py", title="Canal de suporte", icon=":material/support_agent:"),
                ],
                "Documentos": [
                    st.Page("pages_/documentos/digitacao.py", title="Geração de LFs", icon=":material/contract:"),
                    st.Page("pages_/documentos/certificacao.py", title="Certificação de LFs", icon=":material/qr_code_2_add:"),
                ],
                "Recursos": [
                    st.Page("pages_/recursos/pesquisa.py", title="Pesquisa", icon=":material/search:"),
                ],
                "Relatórios":[
                    st.Page("pages_/relatorios/overview.py", title="Resumo", icon=":material/wallpaper:", default=True),
                    st.Page("pages_/relatorios/dashboard.py", title="Dashboard", icon=":material/space_dashboard:"),
                ],
                "Sessão": [
                    st.Page(sair, title="Sair", icon=":material/logout:", url_path="/"),
                    st.Page(senha, title="Mudar senha", icon=":material/passkey:")
                ],
            }
        case 'secretario':
            pages = {
                "Documentos": [
                    st.Page("pages_/documentos/certificacao.py", title="Certificação de LFs", icon=":material/qr_code_2_add:"),
                ],
                "Recursos": [
                    st.Page("pages_/recursos/pesquisa.py", title="Pesquisa", icon=":material/search:"),
                ],
                "Relatórios":[
                    st.Page("pages_/relatorios/overview.py", title="Resumo", icon=":material/wallpaper:", default=True),
                    st.Page("pages_/relatorios/dashboard.py", title="Dashboard", icon=":material/space_dashboard:"),
                ],
                "Sessão": [
                    st.Page(sair, title="Sair", icon=":material/logout:", url_path="/"),
                    st.Page(senha, title="Mudar senha", icon=":material/passkey:")
                ],
            }
        case 'dvse':
            pages = {
                "Documentos": [
                    st.Page("pages_/documentos/pranchas.py", title="Chancela de Pranchas", icon=":material/approval:"),
                ],
                "Relatórios":[
                    st.Page("pages_/relatorios/overview.py", title="Resumo", icon=":material/wallpaper:", default=True),
                ],
                "Sessão": [
                    st.Page(sair, title="Sair", icon=":material/logout:", url_path="/"),
                    st.Page(senha, title="Mudar senha", icon=":material/passkey:")
                ],
            }

        case 'leitor':
            pages = {
                "Recursos": [
                    st.Page("pages_/recursos/pesquisa.py", title="Pesquisa"),
                ],
                "Sessão": [
                    st.Page(sair, title="Sair", icon=":material/logout:", url_path="/"),
                    st.Page(senha, title="Mudar senha", icon=":material/passkey:")
                ],
            }

    st.session_state.sessao_servidor = user
    
    if 'merged_df' not in st.session_state:

        match st.session_state.privilege:

            case 'adm' | 'normal' | 'secretario':
                
                # Exemplo de carregamento de dados (substitua pelos seus dados reais)
                print("Baixando e convertendo os dataframes...")
                # df_proc_2012_2023 = request_data(st.secrets['xlsx']['consolidado_2012_2023'])

                with st.spinner("Aguarde o carregamento e conversão dos dados..."):
                    df_proc_2012_2023_path = 'databases/data_parquet/Consolidado 2012 a 2023.parquet'
                    df_proc_2012_2023 = pd.read_parquet(df_proc_2012_2023_path)
                    # geral_2024 = request_data(st.secrets['xlsx']['consolidado_2024'])
                    
                    @st.cache_data(ttl=420, show_spinner=False)
                    def load_geral_2024():
                        sh_2024 = get_worksheet(5, st.secrets['sh_keys']['geral_2024_v2'])
                        # df_2024 = sh_2024.get_all_records(numericise_ignore=['all'])
                        # df = pd.DataFrame(df_2024)
                        df_2024 = convert_sh_df(sh_2024)
                        return df_2024
                    
                    geral_2024 = load_geral_2024()

                    # Converter datas para o formato datetime
                    # Alguém colocou uma data out of bounds na planilha, e isso crashou o sistema. Cuidado. Tem uma função em algum
                    # dos arquivos que verifica qual á a planilha bichada.
                    #print("Convertendo as colunas específicas...")

                    df_proc_2012_2023['Data Criação'] = pd.to_datetime(df_proc_2012_2023['Data Criação']).dt.strftime('%d/%m/%Y')


                    merged_df = pd.concat(
                        [df_proc_2012_2023, geral_2024],
                        ignore_index=True
                    )

                    # # Converte a coluna para string (caso ainda não seja)
                    # merged_df['Valor'] = merged_df['Valor'].astype(str)

                    # # Substitui vírgulas por pontos
                    # merged_df['Valor'] = merged_df['Valor'].str.replace(',', '.')

                    # # Preencher valores NaN na coluna 'Valor'
                    # merged_df['Valor'] = merged_df['Valor'].fillna(0.0)
                    merged_df['Valor'] = merged_df['Valor'].astype(float)


                    # Adicionar a nova coluna 'Index' com valores de 0 a N-1
                    merged_df['Index'] = range(len(merged_df))

                    # Remover linhas onde 'Protocolo' é None
                    merged_df = merged_df.dropna(subset=['Protocolo'])


                    if 'merged_df' not in st.session_state:
                        st.session_state.merged_df = None # não altere o nome dessa session state, pois está sendo carregada no início.
                        st.session_state.df_2024 = None
                
                    st.session_state.df_2024 = geral_2024
                    st.session_state.merged_df = merged_df


    pg = st.navigation(pages, position="sidebar")
    st.sidebar.info(f"Sessão: **{user}**")
    st.sidebar.caption(f"UUID: {st.session_state.my_ip}")
    
    pg.run()


# agora = datetime.now()
# dez_minutos_antes = agora - timedelta(minutes=10)
# em_duas_horas = agora + timedelta(hours=2)

# if 'agora' not in st.session_state:
#     st.session_state.agora = datetime.now()
#     st.session_state.depois = st.session_state.agora - timedelta(hours=1)

# agora = st.session_state.agora
# depois = st.session_state.depois
# print(f'agora: {agora}')
# print(f'depois: {depois}')
# if agora >= (depois + timedelta(hours=1)):
#     st.session_state.agora = datetime.now()
#     st.session_state.depois = agora + timedelta(hours=1)


session_data = verify_session(f"usr_sess_{st.session_state.my_ip}")

# print(f"st.session_state.my_ip: {st.session_state.my_ip}")

if not session_data:
    interface_logon(usr_list)
else:
    try:
        if session_data:
            for nm in usr_list['Name']:
                if nm == session_data["username"]:
                    index = usr_list[usr_list["Name"] == nm].index[0]
                    psw_stored = usr_list.loc[index, "Password"]
                    if psw_stored == session_data["password"]:
                        open_system(session_data["username"], session_data["privilege"])
                    else:
                        delete_cookie(f"usr_sess_{st.session_state.my_ip}")
                        streamlit_js_eval(js_expressions="parent.window.location.reload()")
    except Exception as e:
        print(e)
        st.error("**Houve um erro inesperado. Consulte os logs.**")

st.session_state.my_ip = None
