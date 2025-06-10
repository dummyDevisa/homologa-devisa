import streamlit as st
from load_functions import *
from ai_module import *

# pode ser que de problema
# from proxy import *

st.header("Geração de LFs", anchor=False)
#
#
# inicializando todos os widgets
#

def this_time(t):
    now = datetime.now()  # Obter a data e hora atuais
    match t:
        case 'dd':  # Dia do mês
            return now.day
        case 'mm':  # Mês
            return now.month
        case 'yy':  # Ano no formato de dois dígitos
            return str(now.year)[2:4]
        case 'yyyy':  # Ano completo
            return now.year
        case 'dd/mm/yyyy':  # Data no formato dd/mm/yyyy
            return now.strftime("%d/%m/%Y")
        case 'dd/mm/yy, hh:mm':  # Data e hora no formato dd/mm/yy, hh:mm
            return now.strftime("%d/%m/%y, %H:%M")
        case _:  # Caso padrão para entradas inválidas
            return ''

if 'fi_cpf_cnpj' not in st.session_state:
    this_year = f"{this_time("yyyy")}"
    this_date = str(this_time("dd/mm/yyyy"))

    st.session_state.yyyy = this_year

    st.session_state.base_geral = None

    st.session_state.dd_mm_yyyy = this_date
    st.session_state.fi_ano = st.session_state.yyyy
    st.session_state.fi_proc = ""
    st.session_state.fi_lf = ""
    st.session_state.fi_divisao = None
    st.session_state.fi_via = "1ª Via"
    st.session_state.fi_emissao = ""
    st.session_state.fi_logradouro = ""
    st.session_state.fi_numero = ""
    st.session_state.fi_bairro = ""
    st.session_state.fi_cep = ""
    st.session_state.fi_cpf_cnpj = ""
    st.session_state.fi_razao_social = ""
    st.session_state.fi_responsavel = ""
    st.session_state.fi_conselho = ""
    st.session_state.fi_atividade = ""
    st.session_state.fi_descricao = ""
    st.session_state.fi_complemento = ""
    st.session_state.fi_comercializar = ""
    st.session_state.fi_codigo = ""
    st.session_state.fi_cnae = ""
    st.session_state.fi_obs = ""

    st.session_state.off_btn_cnae = True
    st.session_state.off_btn_cpf_cnpj = True
    st.session_state.off_btn_cep = True
    st.session_state.off_btn_processo = True
    
    st.session_state.off_btn_gen_doc = False
    st.session_state.off_btn_edit_sheet = True
    st.session_state.off_btn_erase_all = False
    st.session_state.off_btn_gen_pdf = True
    
    st.session_state.url_gen_pdf = 'https://www.example.com/'

    st.session_state.approve_proc = False
    st.session_state.approve_ano = False

    st.session_state.is_typewrited = False
    st.session_state.intern_proc = ""
    st.session_state.intern_cpf_cnpj = ""

    st.session_state.lf_ativa = "Ativo"

    st.session_state.linha_do_proc_encontrada = None


if 'lf_digitadas_2024' not in st.session_state:
    st.session_state.lf_digitadas_2024 = None


# criar o dataframe de LFs digitadas 2024
@st.cache_data(ttl=240, show_spinner="Aguarde...")
def load_lf_digitadas_2024():
    sh_lf_2024 = get_worksheet(4, st.secrets['sh_keys']['geral_2024_v2'])
    df_lf_digitadas_2024 = convert_sh_df(sh_lf_2024)
    # Preencher valores NaN
    df_lf_digitadas_2024 = df_lf_digitadas_2024.ffill()
    # Adicionar a nova coluna 'Index' com valores de 0 a N-1
    df_lf_digitadas_2024['Index'] = range(len(df_lf_digitadas_2024))
    return df_lf_digitadas_2024

lf_digitadas_2024 = load_lf_digitadas_2024()

#st.write(lf_digitadas_2024)

# Armazenar no estado da sessão
st.session_state.lf_digitadas_2024 = lf_digitadas_2024


##
## Funções de apoio
##
def load_cnae(codigo):
    arquivo_json = "databases/cnae_licenca.json"
    try:
        with open(arquivo_json, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        # Percorre a lista de CNAES
        for cnae in dados.get("CNAES 2025", []):
            if cnae.get("Código") == codigo:
                return cnae.get("Descrição", "")     
        return st.toast(":orange[Código não encontrado.]")
    except FileNotFoundError:
        return st.toast(":orange[Arquivo JSON não encontrado.]")
    except json.JSONDecodeError:
        return st.toast(":orange[Erro ao decodificar o arquivo JSON.]")


def processar_strings(cnae, descricao):
    # Função para encontrar o último número seguido de ')' (padrão "0)")
    def encontrar_ultimo_numero(s):
        # Encontra todos os números seguidos de ')'
        numeros = re.findall(r'(\d+)\)', s)
        return int(numeros[-1]) if numeros else 0  # Retorna o último número ou 0 se não encontrado

    # Função para numerar os itens
    def numerar_itens(itens, ultimo_numero):
        return "; ".join([f"{ultimo_numero + i}) {item.strip()}" for i, item in enumerate(itens)])

    # Verificar se já há o padrão "2)" nas strings
    if "2)" in cnae and "2)" in descricao:
        # Encontrar o último número seguido de ')' em ambas as strings
        ultimo_numero_cnae = encontrar_ultimo_numero(cnae)
        ultimo_numero_descricao = encontrar_ultimo_numero(descricao)

        # Separar os itens de CNAE e Descrição
        cnae_itens = [item.strip() for item in cnae.split(";") if item.strip()]
        descricao_itens = [item.strip() for item in descricao.split(";") if item.strip()]

        # Verificar a posição do último número encontrado
        if ultimo_numero_cnae == ultimo_numero_descricao:
            # Numerar apenas o último item
            cnae_itens[-1] = f"{ultimo_numero_cnae + 1}) {cnae_itens[-1].split(') ', 1)[-1]}"
            descricao_itens[-1] = f"{ultimo_numero_descricao + 1}) {descricao_itens[-1].split(') ', 1)[-1]}"
        else:
            # Numerar todos os itens
            cnae_itens = numerar_itens(cnae_itens, ultimo_numero_cnae)
            descricao_itens = numerar_itens(descricao_itens, ultimo_numero_descricao)

        # Reunir os itens numerados
        cnae_numerado = "; ".join(cnae_itens)
        descricao_numerado = "; ".join(descricao_itens)

    else:
        # Caso não haja "2)", numerar todos os itens
        cnae_itens = [item.strip() for item in cnae.split(";") if item.strip()]
        descricao_itens = [item.strip() for item in descricao.split(";") if item.strip()]
        
        cnae_numerado = "; ".join([f"{i+1}) {item}" for i, item in enumerate(cnae_itens)])
        descricao_numerado = "; ".join([f"{i+1}) {item}" for i, item in enumerate(descricao_itens)])

    return cnae_numerado, descricao_numerado

#
# validação do formulário. Streamlit é uma merda, viu? Inputs em cima, e botões só callback...
#

# print(f"intern process caceta: {st.session_state.intern_proc}")
# print(f"st.session_state.is_typewrited: {st.session_state.is_typewrited}")

def btn_gen_doc():
    # pesquisa na base o processo e o ano.
    # se encontrar, então salva na respectiva base, que no caso sempre será a 2024-2028
    # st.warning(f"intern_proc {st.session_state.intern_proc} e intern_cpf {st.session_state.intern_cpf_cnpj}")
    if st.session_state.intern_proc and st.session_state.intern_cpf_cnpj: # se existe processo em alguma base de dados
        # if st.session_state.is_typewrited:
        salvar_lf_digitada(st.session_state.dd_mm_yyyy, True)
    else:
        st.toast(":red[**Carregue um processo e preencha todos os campos obrigatórios.**]")


def btn_edit_sheet():
    # pesquisa SOMENTE. Na base o processo e o ano.
    # se encontrar, então salva na respectiva base, que no caso sempre será a 2024-2028
    if st.session_state.intern_proc and st.session_state.intern_cpf_cnpj: # se existe processo em alguma base de dados
        # if st.session_state.is_typewrited:
        salvar_lf_digitada(st.session_state.dd_mm_yyyy, False)
    else:
        st.toast(":red[**Carregue um processo e preencha todos os campos obrigatórios.**]")


def btn_erase_all():
    st.toast("Formulário limpo.")
    clear_st_session_state_lf()



def btn_cpf_cnpj():
    cnpj = st.session_state.fi_cpf_cnpj
    if validar_cpf_cnpj(cnpj):
        st.session_state.off_btn_processo = True
        get_cnpj(cnpj, 'cnpj_digitacao_lf', lista_dam='') 
    else:
        st.toast(":red[CNPJ inválido]")


def btn_processo():

    if st.session_state.fi_ano and st.session_state.fi_proc:
        so_limpezinha_de_leve() # que porra é essa marreco
        st.toast(f":orange[Pesquisando proc. **{st.session_state.fi_proc}/{st.session_state.fi_ano}**. Aguarde...]")
        df = pesquisa_processo_digitacao(st.session_state.fi_proc, st.session_state.fi_ano)
        if not df is None:

            match st.session_state.fi_ano:
                case '2024':
                  
                    if df.iloc[0]["Número Processo"]:
                       
                        if 'Metadados' in df.columns:
                            
                            if "Data Emissão LF: ''" not in df.iloc[0]['Metadados']:
                                # significa que o processo está com a data de emissão preenchida
                                # Planilha '1EftLvaFlWV4K_uoatZTq8jz83O_Q0a8XnLCrHdj-oPo'
                      
                                st.session_state.is_typewrited = True

                                if isinstance(df.iloc[0]["Número Processo"], float):
                                    n_proc = int(float(df.iloc[0]["Número Processo"]))
                                else:
                                    n_proc = int(df.iloc[0]["Número Processo"])

                                fill_form_lf(n_proc, st.session_state.fi_ano)
                                
                            elif "Data Emissão LF: ''" in df.iloc[0]['Metadados']:
                                st.session_state.is_typewrited = False

                                if isinstance(df.iloc[0]["Número Processo"], float):
                                    n_proc = int(float(df.iloc[0]["Número Processo"]))
                                else:
                                    n_proc = int(df.iloc[0]["Número Processo"])

                                fill_form_lf(n_proc, st.session_state.fi_ano)

                            else:   
                                st.session_state.is_typewrited = False
                                print("Erro. resultado contrário a if Data Emissão LF: '' not in df.iloc[0]['Metadados']:")
                                st.toast("Erro. resultado contrário a if Data Emissão LF: '' not in df.iloc[0]['Metadados']:")
                                
                                
                        else:
                            print("Caiu no else btn_processo() e executar fill_base_2024")
                            st.session_state.is_typewrited = False
                            # st.session_state.merged_df
                            fill_base_2024(df, False)

                        # sinaliza que há processo carregado
                        clean_proc = re.sub(r"[/.].*", "", str(df.iloc[0]["Número Processo"]))
                        st.session_state.intern_proc = clean_proc
                        st.session_state.intern_cpf_cnpj =  df.iloc[0]["CPF / CNPJ"]

                    else:
                        st.toast(f"red[O processo **{st.session_state.fi_proc}** não foi encontrado.]")

                case '2025' | '2026' | '2027' | '2028':
                    if 'GDOC' in df.columns:
                        if df.iloc[0]["GDOC"]:
                            if len(df.iloc[0]['Nº LF']) > 0:
                                fill_form_lf(df.iloc[0]["GDOC"], st.session_state.fi_ano)
                                st.session_state.is_typewrited = True
                            else:
                                fill_base_geral(df, False)
                                st.session_state.is_typewrited = False
                            
                            # sinaliza que há processo carregado
                            clean_proc = re.sub(r"[/.].*", "", str(df.iloc[0]["GDOC"]))
                            st.session_state.intern_proc = clean_proc
                            st.session_state.intern_cpf_cnpj =  df.iloc[0]["CPF / CNPJ"]

                        else:
                            st.toast(f":red[O processo **{st.session_state.fi_proc}** não foi encontrado.]")
                    else:
                        st.toast(f":red[Deve haver algum erro na lógica de carregamento das planilhas, pois GDOC não foi encontrado.]")

                case _:
                    st.toast(f":red[Houve um erro com o campo data, cujo valor é {st.session_state.fi_ano}]")
                
            st.toast(f"Pesquisa finalizada.")

            show_dadosProcesso2(df)

        else:
            st.toast(f":red[Nenhum resultado encontrado para {st.session_state.fi_proc}/{st.session_state.fi_ano}]")        

    else:
        st.toast(":red[Preecha os campos Processo e Ano]")


def btn_cnae():
    if len(st.session_state.fi_cnae) == 9 and re.match(r"^\d{4}-\d/\d{2}$", st.session_state.fi_cnae):
        cnae = st.session_state.fi_cnae
        if cnae not in st.session_state.fi_codigo:
            load_desc = load_cnae(cnae)
            try: 
                if len(load_desc) > 3:
                    cod = st.session_state.fi_codigo 
                    desc = st.session_state.fi_descricao
                    if len(cod) < 9 and len(desc) < 4:
                        st.session_state.fi_codigo = cnae
                        st.session_state.fi_descricao = load_desc
                    else:
                        fi_codigo = st.session_state.fi_codigo
                        fi_descricao = st.session_state.fi_descricao
                        fi_codigo += f'; {cnae}'
                        fi_descricao += f'; {load_desc}'
                        st.session_state.fi_codigo = ""
                        st.session_state.fi_descricao = ""
                        st.session_state.fi_codigo, st.session_state.fi_descricao = processar_strings(fi_codigo, fi_descricao)
                else:
                    st.toast(":orange[A descrição é muito pequena.]")
            except Exception as e:
                st.toast(":red[O valor digitado não foi encontrado.]")
                print(e)
        else:
            st.toast(":orange[O cnae já esta na lista.]")
    else:
       st.session_state.off_btn_cnae = True 


def btn_trim_cnae():
    if len(st.session_state.fi_codigo) >= 7:
        codigo, descricao = extrair_descrever_cnaes(texto=st.session_state.fi_codigo)
        st.session_state.fi_codigo = codigo
        st.session_state.fi_descricao = descricao

        if codigo != "" and "inválido" not in codigo:
            if "1)" in st.session_state.fi_codigo:
                st.session_state.fi_atividade = 'Conforme os cnaes abaixo especificados'
            else:
                st.session_state.fi_atividade = 'Conforme o cnae abaixo especificado'
        
    else:
        st.toast(f":red[Erro. Preencha os dados do CNAE]")
        st.session_state.fi_atividade = ''


def btn_ai_organizer():
    if len(st.session_state.fi_descricao) > 10:
        corrigido = corrigir_texto_sync(
            st.session_state.akash_client,
            st.session_state.fi_descricao)
        st.session_state.fi_descricao = corrigido
    else:
        st.toast(f":red[Erro. Preencha os dados da descrição]")


def btn_cep():
    st.toast("Zé da manga")


### ativar o botão cnae
if len(st.session_state.fi_cnae) >= 7:
    cnae = re.sub(r"[^\d]", "", st.session_state.fi_cnae)
    if len(cnae) == 7:
        st.session_state.off_btn_cnae = False
        st.session_state.fi_cnae = f"{cnae[:4]}-{cnae[4]}/{cnae[5:7]}"
    else:
        st.session_state.off_btn_cnae = True
else:
    st.session_state.off_btn_cnae = True

### tratar o campo cnpj
cpf_cnpj = st.session_state.fi_cpf_cnpj
if len(cpf_cnpj) == 11:
    clean_cpf = re.sub(r'\D', '', cpf_cnpj)
    st.session_state.fi_cpf_cnpj = f"{clean_cpf[:3]}.{clean_cpf[3:6]}.{clean_cpf[6:9]}-{clean_cpf[9:11]}"
elif (len(cpf_cnpj) == 14 and "-" not in cpf_cnpj) or len(cpf_cnpj) == 18:
    clean_cnpj = re.sub(r'\D', '', cpf_cnpj)
    st.session_state.fi_cpf_cnpj = f"{clean_cnpj[:2]}.{clean_cnpj[2:5]}.{clean_cnpj[5:8]}/{clean_cnpj[8:12]}-{clean_cnpj[12:14]}"


### ativar o botão consulta cnpj
cpf_cnpj = st.session_state.fi_cpf_cnpj
if len(cpf_cnpj) == 18:
    if validar_cnpj(clean_cnpj):
        st.session_state.off_btn_cpf_cnpj = False
    else:
        st.session_state.off_btn_cpf_cnpj = True
else:
    st.session_state.off_btn_cpf_cnpj = True

# mexendo com ano e processo
#
#   
fi_ano = str(st.session_state.fi_ano)
fi_proc = str(st.session_state.fi_proc)

if len(fi_ano) > 0:
    year = st.session_state.yyyy
    fi_ano = re.sub(r'\D', '', fi_ano)
    if not ((str(fi_ano) == str(year)) or (str(fi_ano) == str(int(year)-1))):
        st.session_state.fi_ano = year
        st.session_state.approve_ano = False
    else:
        st.session_state.approve_ano = True
        

if len(fi_proc) > 0:
    clean_proc = re.sub(r'\D', '', fi_proc)
    if clean_proc:
        if type(clean_proc) is str:
            clean_proc = int(clean_proc)
        if not ((clean_proc >= 1 and clean_proc <= 70000)):
            st.session_state.fi_proc = ""
            st.session_state.approve_proc = False
        else:
            st.session_state.approve_proc = True
    else:
        st.session_state.approve_proc = False
        st.session_state.fi_proc = ""
    
## ativar o botão de consulta
if st.session_state.approve_proc and st.session_state.approve_ano:
    st.session_state.off_btn_processo = False
else:
    st.session_state.off_btn_processo = True


    
#### tratar o campo cep
match len(st.session_state.fi_cep):
    case 8 | 10:
        clean_cep = re.sub(r'\D', '', st.session_state.fi_cep)
        if clean_cep[:2] == "66":
            st.session_state.fi_cep = f"{clean_cep[:2]}.{clean_cep[2:5]}-{clean_cep[5:8]}"
        else:
            st.session_state.fi_cep = ""
    case _:
        st.session_state.fi_cep = "" 


#### tirar as quebras de linha
# if len(st.session_state.fi_descricao) > 10:
#     treat_desc = st.session_state.fi_descricao.replace("\n", "").replace("\r", "")
#     treat_desc = " ".join(treat_desc.split())
#     st.session_state.fi_descricao = treat_desc


### ativar ou não o botão download PDF...
if 'https://docs.google.com/document' in st.session_state.url_gen_pdf:
    st.session_state.off_btn_gen_pdf = False
else:
    st.session_state.off_btn_gen_pdf = True

### ativar ou não o botão editar...
if st.session_state.intern_proc and st.session_state.intern_cpf_cnpj: # se existe processo em alguma base de dados
    st.session_state.off_btn_edit_sheet = False
else:
    st.session_state.off_btn_edit_sheet = True




with st.container(border=True):

    div1, div2 = st.columns(2, gap="medium", vertical_alignment="top")
    with div1:
        col1, col2, col3, col4, col5, col6, col7 = st.columns([0.5, 0.6, 0.4, 1, 1, 0.6, 0.8], gap="small", vertical_alignment="bottom")
        col1.text_input("Ano", max_chars=4, key="fi_ano")
        col2.text_input("Processo", max_chars=7, key="fi_proc")
        col3.button("", type="primary", icon=":material/search:", use_container_width=True, on_click=btn_processo, key="btn_processo", disabled=st.session_state.off_btn_processo)
        col4.selectbox("Divisão", options={'DVSA', 'DVSE', 'DVSCEP', 'DVSDM'}, index=None, placeholder="DVS*", key="fi_divisao")
        col5.selectbox("Risco", options={'Baixo', 'Médio', 'Alto'}, index=None, placeholder="B/M/A", key="fi_risco")
        col6.text_input("Via", max_chars=7, key="fi_via")
        col7.text_input("Emissão", max_chars=10, key="fi_emissao", disabled=True)
        
        if st.session_state.is_typewrited:
            st.write(f":green-background[**LF Digitada**] &nbsp; &nbsp; :green-background[**{st.session_state.fi_lf}**] &nbsp; &nbsp; :green-background[**{st.session_state.fi_via}**]")
        else:
            st.divider()


        col1, col2, col3 = st.columns([0.8,0.3,1.9], gap="small", vertical_alignment="bottom")       
        col1.text_input("CNPJ/CPF", max_chars=18, key="fi_cpf_cnpj")
        col2.button("", type="primary", icon=":material/search:", use_container_width=True, on_click=btn_cpf_cnpj, key="btn_cpf_cnpj", disabled=st.session_state.off_btn_cpf_cnpj)
        col3.text_input("Logradouro", max_chars=40, key="fi_logradouro")
        st.text_input("Nome", max_chars=40, key="fi_razao_social")

        col1, col2, col3, col4, col5 = st.columns([1.2,0.5,1.2,0.7,0.4], gap="small", vertical_alignment="bottom")
        col1.text_input("Complemento", max_chars=40, key="fi_complemento")
        col2.text_input("Nº", max_chars=7, key="fi_numero") 
        col3.text_input("Bairro", max_chars=15, key="fi_bairro")
        col4.text_input("CEP", max_chars=10, key="fi_cep")
        col5.button("", type="secondary", icon=":material/search:", use_container_width=True, on_click=btn_cep, key="btn_cep", disabled=st.session_state.off_btn_cep)

        col1, col2 = st.columns([1.5,0.5], gap="small", vertical_alignment="bottom")
        col1.text_input("Responsável", max_chars=70, key="fi_responsavel")
        col2.text_input("Conselho", max_chars=40, key="fi_conselho")

    with div2:

        if (st.session_state.fi_codigo != '' and st.session_state.fi_emissao == ''):
            if (st.session_state.fi_divisao != 'DVSDM' and st.session_state.fi_divisao != 'DVSCEP'):
                if '1)' in st.session_state.fi_codigo:
                    st.session_state.fi_atividade = 'Conforme os cnaes abaixo especificados'
                else:
                    st.session_state.fi_atividade = 'Conforme o cnae abaixo especificado'
            if (st.session_state.fi_divisao == 'DVSDM' and '4771-7/01' in st.session_state.fi_codigo):
                st.session_state.fi_atividade = 'COMÉRCIO VAREJISTA'
                st.session_state.fi_comercializar = 'PRODUTOS FARMACÊUTICOS, SEM MANIPULAÇÃO DE FÓRMULAS'

        col1, col2, col3, col4 = st.columns([0.7, 0.3, 1.5, 1.5], gap="small", vertical_alignment="bottom")
        col1.text_input("CNAE", max_chars=9, key="fi_cnae")
        col2.button("", type="primary", icon=":material/add:", use_container_width=True, on_click=btn_cnae, key="btn_cnae", disabled=st.session_state.off_btn_cnae)
        col3.text_input("Atividade", max_chars=90, key="fi_atividade")
        col4.text_input("Comercializar", max_chars=180, key="fi_comercializar")
        
        col1, col2, col3 = st.columns([2.6, 0.2, 0.2], gap="small", vertical_alignment="bottom")
        col1.text_input("Código", max_chars=500, key="fi_codigo")
        col2.button("", type='secondary', icon=":material/format_list_bulleted:", use_container_width=True, 
                    key='btn_trim_cnae', on_click=btn_trim_cnae, help='Organiza e lista os cnaes')
        col3.button("", type='secondary', icon=":material/notes:", use_container_width=True, 
                    key='btn_ai_organizer', on_click=btn_ai_organizer, help='Peça para a IA organizar o texto')
        st.text_area("Descrição", max_chars=1320, height=136, key="fi_descricao")
        # st.caption("Falta o campo de Obs.")
        st.divider()
        col1, col2, col3, col4 = st.columns(4, gap="small", vertical_alignment="bottom")
        col1.button("Limpar campos", type="secondary", icon=":material/ink_eraser:", use_container_width=True, on_click=btn_erase_all, key="btn_erase_all", disabled=st.session_state.off_btn_erase_all)
        col2.button("Criar Doc.", type="primary", icon=":material/note_add:", use_container_width=True, on_click=btn_gen_doc, key="btn_gen_doc", disabled=st.session_state.off_btn_gen_doc)
        col3.button("Editar...", type="secondary", icon=":material/edit_document:", use_container_width=True, on_click=btn_edit_sheet, key="btn_edit_sheet", disabled=st.session_state.off_btn_edit_sheet)
        col4.link_button("Baixar PDF", type="secondary", icon=":material/picture_as_pdf:", use_container_width=True, url=st.session_state.url_gen_pdf, disabled=st.session_state.off_btn_gen_pdf)