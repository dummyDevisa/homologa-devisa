import pandas as pd
from io import StringIO, BytesIO
import pymupdf, pytesseract
from PIL import Image
import streamlit as st
import requests, os, re, gspread, json, hashlib, random, string
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from streamlit_javascript import st_javascript
from streamlit_js import st_js, st_js_blocking
import uuid
from gdrive_api import * # gerar lf
from typing import Tuple


# função de digitacao.py
def extrair_descrever_cnaes(
    texto: str,
    json_path: str = "databases/cnae_licenca.json"
) -> Tuple[str, str]:
    """
    Extrai CNAEs de um texto (em qualquer formato), normaliza para ####-#/##,
    consulta suas descrições no arquivo JSON e retorna duas strings enumeradas:
    - códigos:    "1) 1234-5/67; 2) 2345-6/78; …"
    - descrições: "1) Descrição de 1234-5/67; 2) Descrição de 2345-6/78; …"

    Se um código não for encontrado no JSON, ele será ignorado.
    Retorna ("", "") se não houver nenhum CNAE válido.
    """
    # 1) Normaliza espaços e quebras de linha
    texto_norm = re.sub(r"\s+", " ", texto).strip()

    # 2) Extrai sequências de 7 dígitos (com ou sem . - /)
    padrao = r"\b(?:\d[./\-]?){6}\d\b"
    raw_codes = re.findall(padrao, texto_norm)

    # 3) Limpa separadores e formata ####-#/##
    vistos = set()
    codes_fmt = []
    for raw in raw_codes:
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 7 and digits not in vistos:
            vistos.add(digits)
            fmt = f"{digits[:4]}-{digits[4]}/{digits[5:]}"
            codes_fmt.append(fmt)

    if not codes_fmt:
        return "", ""

    # 4) Carrega JSON e monta dicionário código→descrição
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("CNAES 2025", [])
    lookup = { item["Código"]: item["Descrição"] for item in entries }

    # 5) Para cada código formatado, busca descrição (se existir)
    descrs = []
    valid_codes = []
    for code in codes_fmt:
        desc = lookup.get(code)
        if desc:
            valid_codes.append(code)
            descrs.append(desc)

    if not valid_codes:
        return "código inválido", ""

    # 6) Monta as strings enumeradas
    if len(valid_codes) == 1:
        return valid_codes[0], descrs[0]

    codes_enum = "; ".join(f"{i+1}) {c}" for i, c in enumerate(valid_codes))
    descs_enum = "; ".join(f"{i+1}) {d}" for i, d in enumerate(descrs))

    return codes_enum, descs_enum

# @st.cache_data(ttl=3600, show_spinner=False)
def rk(length=11):
    """Gera um código aleatório composto somente por números."""
    return ''.join(random.choice('0123456789') for _ in range(length))

def unique_id():
    unique_id = str(uuid.uuid4())
    return unique_id

def my_ip(k=rk()):
    ip = st_javascript("""
        await fetch('https://api.ipify.org?format=json')
            .then(response => response.json())
            .then(data => data.ip);
    """, key=k)
    return ip

def get_server_ip():
    response = requests.get("https://api.ipify.org?format=json")
    if response.status_code == 200:
        return response.json().get("ip")
    return None

# @st.cache_data
def get_client_ip(key_j=rk()):
    """
    Obtém o IP público do cliente utilizando streamlit-js para executar JavaScript.
    """
    client_ip = st_js_blocking(
        code="""
        // Faz a requisição à API ipify para obter o IP público do cliente
        return await fetch('https://api.ipify.org?format=json')
            .then(response => response.json())
            .then(data => data.ip)
            .catch(() => null);
        """, key=key_j
    )
    return client_ip

def get_client_uuid(key_j=rk()):
    """
    Cria ou lê um UUID único armazenado no localStorage do navegador.
    Retorna apenas o UUID.
    """
    client_uuid = st_js_blocking(
        code="""
        // Gerar ou recuperar UUID do localStorage
        const getOrCreateUUID = () => {
            const storageKey = 'uniqueClientUUID';
            let uuid = localStorage.getItem(storageKey);
            if (!uuid) {
                uuid = crypto.randomUUID();
                localStorage.setItem(storageKey, uuid);
                console.log('Novo UUID gerado e armazenado:', uuid);
            } else {
                console.log('UUID existente encontrado:', uuid);
            }
            return uuid;
        };

        // Retorna o UUID
        return getOrCreateUUID();
        """,
        key=key_j
    )
    
    return client_uuid



def hide_txtform():
    st.markdown(
        """
        <style>
        div[data-testid="InputInstructions"] {
            display: none;  /* Oculta o elemento inteiro que contém o texto */
        }
        </style>
        """,
        unsafe_allow_html=True
    )


conn_google = f"""
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

def get_worksheet(sheet=int, sh_key=str):
    # print(f"get_worksheet acionada, linha {sheet}")
    try:  
        json_obj = json.loads(conn_google)
        gc = gspread.service_account_from_dict(json_obj)
        sh = gc.open_by_key(sh_key)
        worksheet = sh.get_worksheet(sheet)
        return worksheet
    except Exception as e:
        return st.error(e)

# essa merda deu erro
def convert_sh_df(_sheet):
    data = _sheet.get_all_records(numericise_ignore=['all'])
    df = pd.DataFrame(data)
    return df

@st.cache_data(ttl=300, show_spinner="Pera lá...")
def load_df_2025():
    worksheet = get_worksheet(7, st.secrets['sh_keys']['geral_major'])
    data = worksheet.get_all_records(numericise_ignore=['all'])
    df = pd.DataFrame(data)
    return df

# carregar base 2025
# paliativo
# paliativo

def generate_salt():
    return os.urandom(16).hex()

def hash_with_salt(salt: str, string: str) -> str:
    """
    Criptografa uma string com um salt usando SHA-256.

    :param salt: Salt a ser usado na criptografia.
    :param string: String a ser criptografada.
    :return: Hash resultante em formato hexadecimal.
    """
    # Combina o salt e a string
    combined = f"{salt}{string}"
    # Gera o hash SHA-256
    hash_object = hashlib.sha256(combined.encode('utf-8'))
    # Retorna o hash em formato hexadecimal
    return hash_object.hexdigest()

@st.cache_data(ttl=600, show_spinner="Baixando o banco de dados. Pode demorar um pouco. Aguarde...")
def request_data(url: str) -> dict:
    """
    Carrega um arquivo CSV ou todas as abas de um XLSX de uma URL e retorna um dicionário de DataFrames.
    :param url: A URL do arquivo.
    :return: Dicionário com os nomes das abas como chaves e DataFrames como valores.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Verifica se houve erro na requisição

        if url.endswith('csv'):
            # Lê o CSV e retorna como um único DataFrame em um dicionário com chave 'CSV'
            csv_data = StringIO(response.content.decode('utf-8'))
            sheets = pd.read_csv(csv_data)
        elif url.endswith('xlsx'):
            # Lê todas as abas do XLSX e retorna como um dicionário de DataFrames
            xlsx_data = BytesIO(response.content)
            sheets = pd.read_excel(xlsx_data, sheet_name=None)
        else:
            raise ValueError("Formato de arquivo não suportado. Somente CSV e XLSX são aceitos.")
        
        # st.write(sheets)
        
        return sheets
    except Exception as e:
        raise Exception(f"Erro ao carregar o arquivo da URL: {e}")

@st.cache_data(ttl=600, show_spinner="Carregando o documento. Aguarde...")
def load_sheets(file) -> pd.DataFrame:
    """
    Carrega um arquivo CSV ou XLSX localmente e retorna um DataFrame.
    :param file: O arquivo carregado (formato CSV ou XLSX).
    :return: DataFrame com os dados do arquivo.
    """
    try:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file, encoding='utf-8')
        elif file.name.endswith(".xlsx"):
            df = pd.read_excel(file)
        else:
            raise ValueError("Formato de arquivo não suportado. Use CSV ou XLSX.")
        return df
    except Exception as e:
        raise Exception(f"Erro ao carregar arquivo: {e}")

def extract_text_and_ocr_from_pdf(url):
    # Fazer o download do PDF a partir da URL
    response = requests.get(url)
    if response.status_code == 200:
        pdf_data = BytesIO(response.content)
        
        # Abrir o PDF baixado com PyMuPDF
        doc = pymupdf.open(stream=pdf_data, filetype="pdf")
        full_text = ""
        
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            full_text += text

            # Caso não haja texto, fazer OCR
            if not text.strip():
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_text = pytesseract.image_to_string(img)
                full_text += ocr_text
        
        return full_text
    else:
        raise Exception(f"Erro ao baixar o PDF: {response.status_code}")
    

# função usada no certificador
def gerar_pdf_teste(tamanho_kb=100):
    """
    Gera um arquivo binário no formato PDF contendo dados aleatórios.

    Parâmetros:
        tamanho_kb (int): Tamanho do arquivo em KB. Padrão: 100KB.

    Retorna:
        bytes: Conteúdo do arquivo PDF gerado.
    """
    tamanho_bytes = tamanho_kb * 1024  # Converter KB para bytes
    conteudo_binario = os.urandom(tamanho_bytes)  # Dados aleatórios

    # Cabeçalho básico de um PDF para garantir compatibilidade
    cabecalho_pdf = b"%PDF-1.4\n%FakePDF\n"
    rodape_pdf = b"\n%%EOF"

    # Junta o conteúdo com o cabeçalho e rodapé para simular um PDF válido
    pdf_binario = cabecalho_pdf + conteudo_binario + rodape_pdf

    return pdf_binario

# função usada no gdoc webdriver
def codigo_alfabetico():
    """
    Retorna um código alfabético randômico de 6 dígitos.
    As letras são escolhidas entre 'a' a 'z', garantindo que não sejam maiúsculas nem acentuadas.
    """
    return ''.join(random.choices(string.ascii_lowercase, k=6))

def limpando_cpf_cnpj(cnpj):
    cnpj_limpo = re.sub(r'\D', '', cnpj)
    return cnpj_limpo


def save_excel_sheets_as_csv(excel_file_path):
    # Verificar se o arquivo existe
    if not os.path.exists(excel_file_path):
        print(f"O arquivo {excel_file_path} não foi encontrado.")
        return

    # Carregar o arquivo Excel
    xls = pd.ExcelFile(excel_file_path)
    
    # Obter o nome do arquivo sem a extensão
    base_filename = os.path.splitext(os.path.basename(excel_file_path))[0]
    
    # Iterar sobre as abas
    for sheet_name in xls.sheet_names:
        # Ler a aba em um DataFrame
        df = pd.read_excel(xls, sheet_name=sheet_name)
        
        # Definir o nome do arquivo CSV
        csv_file_name = f"{base_filename}_{sheet_name}.csv"
        
        # Salvar o DataFrame como CSV
        df.to_csv(csv_file_name, index=False)
        
        print(f"A aba '{sheet_name}' foi salva como '{csv_file_name}'.")


# Função para obter a data atual no formato UTC-3
def get_this_date():
    # Obtém o horário atual com informação de UTC
    data_atual_utc = datetime.now(timezone.utc)
    # Ajusta para UTC-3
    data_atual_utc_minus_3 = data_atual_utc - timedelta(hours=3)
    # Formata a data
    data_formatada = data_atual_utc_minus_3.strftime("%d/%m/%Y")
    return data_formatada

def get_current_date_utc3():
    tz = timezone(timedelta(hours=-3))  # Define UTC-3
    return datetime.now(tz).strftime('%d/%m/%Y')

def get_current_year_utc3():
    tz = timezone(timedelta(hours=-3))  # Define UTC-3
    return datetime.now(tz).strftime('%Y')  # Retorna apenas o ano no formato yyyy

def format_financial_values(param):
    # Verificar se é uma string no formato esperado (0,00 até 00000,00000)
    if isinstance(param, str) and re.match(r"^\d{1,5},\d+$", param):
        # Converter de string para float (ignorar valores adicionais após 2 casas decimais)
        numeric_value = float(param.replace(",", "."))
        # Formatar no estilo financeiro com 2 casas decimais
        formatted_val = f"R$ {numeric_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted_val
    
    # Verificar se já está no formato financeiro esperado
    if isinstance(param, str) and re.fullmatch(r"R\$ (\d{1,3}(\.\d{3})*|\d+),\d{2}", param):
        return param
    
    # Retornar vazio se não for número válido ou não seguir o formato esperado
    return ''


def extrair_e_formatar_real(valor: str) -> str:
    # Expressão regular para encontrar números no formato brasileiro
    padrao = r"\b\d{1,3}(?:\.\d{3})*,\d{2}\b"
    
    # Encontrar a correspondência
    correspondencia = re.search(padrao, valor)
    
    if correspondencia:
        numero_formatado = correspondencia.group()
        
        # Substituir pontos por nada e a vírgula por ponto
        numero_limpo = numero_formatado.replace('.', '').replace(',', '.')
        
        # Converter para Decimal para evitar problemas de precisão
        numero_decimal = Decimal(numero_limpo)
        
        # Retornar formatado no padrão brasileiro
        return f"R$ {numero_decimal:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    # Retornar vazio se não for número válido ou não seguir o formato esperado
    return ""


def hint_financial_values(min, max, comp):
    resp = ''
    if min:
        if max or comp:
            resp += f'Valor mínimo: {min}; '
        else:
            resp += f'Valor mínimo: {min}.'
    if max:
        if comp:
            resp += f'Valor máximo: {max}; '
        else:
            resp += f'Valor máximo: {max}.' 
    if comp:
        resp += f'Tipo: {comp}.'
    return resp

# Função para obter a data e hora atuais no formato UTC-3
def get_current_datetime():
    # Obtém o horário atual com informação de UTC
    data_hora_utc = datetime.now(timezone.utc)
    # Ajusta para UTC-3
    data_hora_utc_minus_3 = data_hora_utc - timedelta(hours=3)
    # Formata a data e hora
    data_hora_formatada = data_hora_utc_minus_3.strftime("%d/%m/%y, %H:%M")
    return data_hora_formatada

def validate_gdoc(gdoc=str, date=str):
    try:
        pattern = r'^(?:[1-9]|[1-9][0-9]{1,4}|100000)/(?:2[2-9]|[3-4][0-9]|50)$'
        if re.match(pattern, gdoc) and date[6:8] == gdoc[-2:]:
            return True
        else:
            return False
    except:
        return False

def validate_protocolo(cartao_name=str, gdoc=str):
    try:
        pattern = gdoc.split('/')[0]+'_'
        print(f"{pattern}, {cartao_name}")
        if pattern in cartao_name:
            return True
        else:
            return False
    except Exception as e:
        st.toast(e)
        return False
    

def validar_cpf_cnpj(numero: str) -> bool:
    numero_limpo = re.sub(r'\D', '', numero)
    
    if len(numero_limpo) == 11:  # Validação de CPF
        return validar_cpf(numero_limpo)
    elif len(numero_limpo) == 14:  # Validação de CNPJ
        return validar_cnpj(numero_limpo)
    else:
        return False


def validar_cpf(cpf: str) -> bool:
    if len(cpf) != 11 or cpf == cpf[0] * len(cpf):  # Verifica se são todos dígitos iguais
        return False

    # Cálculo dos dígitos verificadores
    def calcular_digito(cpf_parcial, multiplicadores):
        soma = sum(int(cpf_parcial[i]) * multiplicadores[i] for i in range(len(multiplicadores)))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    multiplicadores1 = list(range(10, 1, -1))
    multiplicadores2 = list(range(11, 1, -1))

    digito1 = calcular_digito(cpf[:9], multiplicadores1)
    digito2 = calcular_digito(cpf[:9] + str(digito1), multiplicadores2)

    return cpf[-2:] == f"{digito1}{digito2}"


def validar_cnpj(cnpj: str) -> bool:
    if len(cnpj) != 14 or cnpj == cnpj[0] * len(cnpj):  # Verifica se são todos dígitos iguais
        print(f'deu return false, {cnpj}')
        return False

    # Pesos para os cálculos dos dígitos verificadores
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1

    # Cálculo dos dígitos verificadores
    def calcular_digito(cnpj_parcial, pesos):
        soma = sum(int(cnpj_parcial[i]) * pesos[i] for i in range(len(pesos)))
        digito = soma % 11
        return 0 if digito < 2 else 11 - digito

    digito1 = calcular_digito(cnpj[:12], pesos1)
    digito2 = calcular_digito(cnpj[:12] + str(digito1), pesos2)

    return cnpj[-2:] == f"{digito1}{digito2}"


def cnae_intersectorial(lista_cnae):
    arquivo_json = 'databases/cnae_valores.json'
    with open(arquivo_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    
    # Extrair os códigos do JSON e normalizá-los
    codigos_json = {item["Código"].replace("/", "").replace("-", "") for item in dados["Valores 2025"]}

    
    # Normalizar os valores da lista cnae_valores
    lista_cnae_normalizada = {str(codigo)[:7] for codigo in lista_cnae}
    # Interseção entre os conjuntos
    interseccao = lista_cnae_normalizada.intersection(codigos_json)
    
    return list(interseccao)


def convert_date(date):
    try:
        # Converter para objeto datetime
        data_obj = datetime.strptime(date, "%Y-%m-%d")
        # Formatando para o novo formato
        data_formatada = data_obj.strftime("%d/%m/%Y")
        return data_formatada
    except:
        return "erro em convert_data"

def format_phone_number(number):
    if len(number) == 10:
        formatted = f"({number[:2]}) {number[2:6]}-{number[6:10]}"
        return formatted
    elif len(number) == 11:
        formatted = f"({number[:2]}) {number[2:7]}-{number[7:11]}"
        return formatted
    else:
        return number


@st.dialog("Consulta do CNPJ", width="large")
def show_dadosCnpj(display_data: dict, cnaes_finais: list, socios: list, this_taxas: str):
    """Exibe os dados do CNPJ formatados a partir de um dicionário padronizado."""
    st.write(f"Situação cadastral: **{":green" if display_data.get('situacao') == "ATIVA" else ":red"}[{display_data.get('situacao', 'N/A')}, {display_data.get('motivo_situacao', 'N/A')} ({convert_date(display_data.get('data_situacao', ''))})]**")
    st.write(f"Município: **{":green" if display_data.get('municipio') == "BELEM" else ":red"}[{display_data.get('municipio', 'N/A')}, {display_data.get('uf', 'N/A')}]**")

    # Lógica MEI (ajustada para dicionário)
    is_mei = display_data.get('opcao_mei', False)
    data_opcao_mei = display_data.get('data_opcao_mei', '')
    data_exclusao_mei = display_data.get('data_exclusao_mei', '')

    if is_mei:
        if this_taxas != '': # Assumindo que 'this_taxas' indica algum problema se não for vazio
            st.write(f"Situação MEI: :red[**ATIVA desde {convert_date(data_opcao_mei)}**]")
        else:
            st.write(f"Situação MEI: :green[ATIVA desde {convert_date(data_opcao_mei)}]")
    elif data_exclusao_mei:
        if this_taxas != '':
             st.write(f"Situação MEI: :green[Removido em {convert_date(data_exclusao_mei)}]")
        else:
            st.write(f"Situação MEI: :red[Removido em {convert_date(data_exclusao_mei)}]")
    else:
         st.write(f"Situação MEI: :grey[Não optante ou informação indisponível]")


    st.write(f"Nat. Jurídica: {display_data.get('cod_natureza_juridica', 'N/A')} - {display_data.get('natureza_juridica', 'N/A')}")
    st.write(f"Empresa: {display_data.get('razao_social', 'N/A')} {f"({display_data.get('nome_fantasia')})" if display_data.get('nome_fantasia') else ""}")

    # Endereço (ajustado para dicionário)
    logradouro = f"{display_data.get('tipo_logradouro', '')} {display_data.get('logradouro', '')}".strip()
    numero = display_data.get('numero', '')
    complemento = display_data.get('complemento', '')
    bairro = display_data.get('bairro', '')
    cep = display_data.get('cep', '')
    municipio_uf = f"{display_data.get('municipio', '')} ({display_data.get('uf', '')})"

    endereco_str = f"{logradouro}, {numero}"
    if complemento:
        endereco_str += f", {complemento}"
    endereco_str += f". {bairro} - {cep}. {municipio_uf}"
    st.write(f"Endereço: {endereco_str}")

    # CNAEs
    if cnaes_finais:
        lista_cnaes_formatada = []
        for cnae in cnaes_finais:
            if cnae and len(cnae) >= 7:
                 lista_cnaes_formatada.append(f"{cnae[:4]}-{cnae[4:5]}/{cnae[5:7]}")
            else:
                 lista_cnaes_formatada.append(cnae) # Adiciona como está se não tiver 7 dígitos
        lista_cnaes_str = ", ".join(lista_cnaes_formatada) + "."
    else:
        lista_cnaes_str = ":red[Não possui ou não encontrado]"


    # Lógica de exibição de CNAEs baseada em 'this_taxas'
    if this_taxas:
        match this_taxas:
            case 'sem cnae':
                st.write(f"CNAEs Declarados: :red[**Não encontrei CNAEs válidos no CNPJ**]")
            case 'cnae ausente':
                st.write(f"CNAEs Declarados (Fora do Decreto): :red[**{lista_cnaes_str}**]")
            case 'ok':
                 st.write(f"CNAEs Declarados (Decreto): **:blue[{lista_cnaes_str}] :green[*(ok, passou no filtro)*]**")
            case _: # Caso padrão se this_taxas tiver outro valor inesperado
                 st.write(f"CNAEs no CNPJ: :blue[{lista_cnaes_str}]")
    else:
         st.write(f"CNAEs no CNPJ: :blue[{lista_cnaes_str}]") # Exibe todos se não houver filtro de taxas


    # Sócios
    if socios:
        lista_socios_str = "; ".join(filter(None, socios)) + "." # Filtra Nones/vazios
        st.write(f"Quadro de Sócios: :grey[{lista_socios_str}]")
    else:
        st.write("Quadro de Sócios: :grey[Não informado ou indisponível]")


    # Contato (ajustado para dicionário)
    email = display_data.get('email', '')
    tel1 = display_data.get('telefone1', '')
    tel2 = display_data.get('telefone2', '')
    contatos = []
    if email:
        contatos.append(email)
    if tel1:
        contatos.append(format_phone_number(tel1))
    if tel2 and tel2 != tel1: # Evita duplicidade se APIs retornarem o mesmo tel
        contatos.append(format_phone_number(tel2))

    if contatos:
        st.write(f"Contato: {' e '.join(contatos)}")
    else:
        st.write(f"Contato: :grey[Sem contato informado]")

    # Atualiza o estado para indicar que o diálogo foi fechado
    st.session_state["dialog_open"] = False


def process_cnpj_data(api_data: dict, api_source: str, yy: str, lista_dam: str):
    """Processa dados da API (BrasilAPI ou ReceitaWS) e os padroniza."""

    display_data = {}
    socios = []
    cnaes_secundarios_cod = []
    cnae_principal_cod = None

    if api_source == 'brasilapi':
        # Mapeamento BrasilAPI -> display_data (dicionário padronizado)
        display_data['situacao'] = api_data.get('descricao_situacao_cadastral')
        display_data['motivo_situacao'] = api_data.get('descricao_motivo_situacao_cadastral')
        display_data['data_situacao'] = api_data.get('data_situacao_cadastral')
        display_data['municipio'] = api_data.get('municipio')
        display_data['uf'] = api_data.get('uf')
        display_data['opcao_mei'] = api_data.get('opcao_pelo_mei', False)
        display_data['data_opcao_mei'] = api_data.get('data_opcao_pelo_mei')
        display_data['data_exclusao_mei'] = api_data.get('data_exclusao_do_mei')
        display_data['cod_natureza_juridica'] = api_data.get('codigo_natureza_juridica')
        display_data['natureza_juridica'] = api_data.get('natureza_juridica')
        display_data['razao_social'] = api_data.get('razao_social')
        display_data['nome_fantasia'] = api_data.get('nome_fantasia')
        display_data['tipo_logradouro'] = api_data.get('descricao_tipo_de_logradouro')
        display_data['logradouro'] = api_data.get('logradouro')
        display_data['numero'] = api_data.get('numero')
        display_data['complemento'] = api_data.get('complemento')
        display_data['bairro'] = api_data.get('bairro')
        display_data['cep'] = api_data.get('cep')
        display_data['email'] = api_data.get('email')
        # Combina DDD e telefone se existirem
        ddd1 = api_data.get('ddd_telefone_1', '')
        tel1 = api_data.get('telefone_1', '')
        display_data['telefone1'] = f"{ddd1}{tel1}" if ddd1 or tel1 else ''
        ddd2 = api_data.get('ddd_telefone_2', '')
        tel2 = api_data.get('telefone_2', '')
        display_data['telefone2'] = f"{ddd2}{tel2}" if ddd2 or tel2 else ''

        # Extrai CNAE principal e secundários
        cnae_principal_cod = str(api_data.get('cnae_fiscal', ''))
        if "cnaes_secundarios" in api_data and isinstance(api_data["cnaes_secundarios"], list):
            for cnae in api_data["cnaes_secundarios"]:
                cnaes_secundarios_cod.append(str(cnae.get("codigo", '')))

        # Extrai Sócios
        if "qsa" in api_data and isinstance(api_data["qsa"], list):
            for socio in api_data["qsa"]:
                socios.append(socio.get("nome_socio"))


    elif api_source == 'receitaws':
        # Mapeamento ReceitaWS -> display_data (dicionário padronizado)
        display_data['situacao'] = api_data.get('situacao')
        display_data['motivo_situacao'] = api_data.get('motivo_situacao') # Pode não existir, .get() lida com isso
        display_data['data_situacao'] = api_data.get('data_situacao')
        display_data['municipio'] = api_data.get('municipio')
        display_data['uf'] = api_data.get('uf')
        # ReceitaWS tem estrutura aninhada para MEI/Simples
        is_mei = api_data.get('simei', {}).get('optante', False) if api_data.get('simei') else False
        display_data['opcao_mei'] = is_mei
        display_data['data_opcao_mei'] = api_data.get('simei', {}).get('data_opcao') if api_data.get('simei') else None
        display_data['data_exclusao_mei'] = api_data.get('simei', {}).get('data_exclusao') if api_data.get('simei') else None
        # Pega código da string natureza_juridica "XXX-X - Texto"
        nj_str = api_data.get('natureza_juridica', '')
        display_data['cod_natureza_juridica'] = nj_str.split(' - ')[0] if ' - ' in nj_str else ''
        display_data['natureza_juridica'] = nj_str.split(' - ')[1] if ' - ' in nj_str else nj_str
        display_data['razao_social'] = api_data.get('nome') # Chave diferente
        display_data['nome_fantasia'] = api_data.get('fantasia') # Chave diferente
        display_data['tipo_logradouro'] = '' # ReceitaWS não fornece separado
        display_data['logradouro'] = api_data.get('logradouro')
        display_data['numero'] = api_data.get('numero')
        display_data['complemento'] = api_data.get('complemento')
        display_data['bairro'] = api_data.get('bairro')
        display_data['cep'] = api_data.get('cep')
        display_data['email'] = api_data.get('email')
        display_data['telefone1'] = api_data.get('telefone') # ReceitaWS geralmente tem só um campo telefone
        display_data['telefone2'] = '' # Não tem segundo telefone explícito

        # Extrai CNAE principal e secundários (estrutura diferente)
        if "atividade_principal" in api_data and isinstance(api_data["atividade_principal"], list) and len(api_data["atividade_principal"]) > 0:
            cnae_principal_cod = str(api_data["atividade_principal"][0].get("code", '')).replace('.', '').replace('-', '') # Limpa o código
        if "atividades_secundarias" in api_data and isinstance(api_data["atividades_secundarias"], list):
            for cnae in api_data["atividades_secundarias"]:
                 cnaes_secundarios_cod.append(str(cnae.get("code", '')).replace('.', '').replace('-', '')) # Limpa o código

        # Extrai Sócios (estrutura diferente)
        if "qsa" in api_data and isinstance(api_data["qsa"], list):
            for socio in api_data["qsa"]:
                # Combina nome e qualificação se quiser: f"{socio.get('nome')} ({socio.get('qual')})"
                socios.append(socio.get("nome"))

    # --- Lógica Comum após padronização ---

    # Junta todos os CNAEs (apenas códigos numéricos)
    lista_cnaes_numericos = []
    if cnae_principal_cod:
        lista_cnaes_numericos.append(cnae_principal_cod)
    lista_cnaes_numericos.extend(cnaes_secundarios_cod)

    # Aplica o filtro intersetorial (placeholder)
    cnaes_decreto = cnae_intersectorial(lista_cnaes_numericos)
    print(f"CNAEs após intersectorial: {cnaes_decreto}") # Debug

    # Lógica de comparação com lista_dam
    this_taxas = ''
    cnaes_finais = cnaes_decreto # Por padrão, exibe os CNAEs do decreto/CNPJ

    if lista_dam and len(lista_dam) > 5: # Verifica se lista_dam é válida
        lista_taxas = [cnae.strip().replace("-", "").replace("/", "").replace(".", "") for cnae in lista_dam.split(",")]
        lista_taxas = [c for c in lista_taxas if c] # Remove vazios

        print(f"Lista DAM (limpa): {lista_taxas}") # Debug
        print(f"CNAEs Decreto/CNPJ: {cnaes_decreto}") # Debug


        intersecao = [cnae for cnae in lista_taxas if cnae in cnaes_decreto]
        nao_contidos = [cnae for cnae in lista_taxas if cnae not in cnaes_decreto]

        print(f"Interseção: {intersecao}") # Debug
        print(f"Não contidos: {nao_contidos}") # Debug


        if not cnaes_decreto: # Se o CNPJ não tiver CNAEs válidos
             this_taxas = 'sem cnae'
             cnaes_finais = [] # Nenhum CNAE a exibir
        elif not intersecao and nao_contidos: # Nenhum CNAE da lista_dam está no CNPJ
            this_taxas = 'cnae ausente'
            cnaes_finais = nao_contidos # Exibe os CNAEs da lista_dam que não foram encontrados
        elif nao_contidos: # Alguns da lista_dam estão, outros não
            this_taxas = 'cnae ausente' # Ou poderia ser um status diferente?
            cnaes_finais = nao_contidos # Exibe os que faltaram
            # Alternativa: exibir os que deram match? cnaes_finais = intersecao
        elif intersecao and not nao_contidos: # Todos da lista_dam estão no CNPJ
            this_taxas = 'ok'
            cnaes_finais = intersecao # Exibe os CNAEs que deram match
        else: # Caso não previsto ou lista_dam vazia após limpeza
             cnaes_finais = cnaes_decreto # Volta ao padrão
             this_taxas = ''

    else: # Se não houver lista_dam para comparar
        cnaes_finais = cnaes_decreto
        this_taxas = ''

    print(f"Final - this_taxas: {this_taxas}, cnaes_finais: {cnaes_finais}") # Debug

    # Chama a função de exibição com os dados padronizados
    show_dadosCnpj(display_data, cnaes_finais, socios, this_taxas)

    # Lógica para preencher campos de digitação (ajustada para dicionário)
    if display_data:
        if yy == 'cnpj_digitacao_lf':
            # Verifica condições (Ex: ATIVA e CEP de Belém)
            if display_data.get('situacao') == "ATIVA" and display_data.get('cep', '').startswith("66"):
                st.session_state.fi_logradouro = f"{display_data.get('tipo_logradouro', '')} {display_data.get('logradouro', '')}".strip()
                st.session_state.fi_numero = display_data.get('numero', '')
                st.session_state.fi_razao_social = display_data.get('razao_social', '')
                st.session_state.fi_bairro = display_data.get('bairro', '')
                st.session_state.fi_cep = display_data.get('cep', '')
                st.session_state.fi_complemento = display_data.get('complemento', '')
            else:
                 # Limpa os campos se não atender aos critérios
                 st.session_state.fi_logradouro = ""
                 st.session_state.fi_razao_social = ""
                 st.session_state.fi_complemento = ""
                 st.session_state.fi_numero = ""
                 st.session_state.fi_bairro = ""
                 st.session_state.fi_cep = ""


def get_cnpj(cnpj: str, yy: str, lista_dam: str):
    """Busca dados do CNPJ, tentando BrasilAPI e depois ReceitaWS como fallback."""
    t_cnpj = re.sub(r"\D", "", cnpj)
    if not t_cnpj:
        st.toast(":orange[CNPJ inválido ou vazio.]")
        return False

    # Limpa campos do formulário antes da consulta (se aplicável)
    if yy == 'cnpj_digitacao_lf':
        st.session_state.fi_logradouro = ""
        st.session_state.fi_razao_social = ""
        st.session_state.fi_complemento = ""
        st.session_state.fi_numero = ""
        st.session_state.fi_bairro = ""
        st.session_state.fi_cep = ""

    api_data = None
    api_source = None
    error_msg = None

    # --- Tentativa 1: BrasilAPI ---
    try:
        url_brasilapi = f"https://brasilapi.com.br/api/cnpj/v1/{t_cnpj}"
        headers = {'User-Agent': 'MeuAppStreamlit/1.0'} # Boa prática adicionar User-Agent
        response_brasilapi = requests.get(url_brasilapi, timeout=10, headers=headers) # Timeout de 10s

        if response_brasilapi.status_code == 200:
            api_data = response_brasilapi.json()
            api_source = 'brasilapi'
            st.toast("✅ Consulta via BrasilAPI bem-sucedida.")
        else:
            error_msg = f"⛔ BrasilAPI falhou: {response_brasilapi.status_code}. Tentando ReceitaWS..."
            st.toast(error_msg)

    except requests.exceptions.RequestException as e:
        error_msg = f"⛔ Erro ao conectar à BrasilAPI: {e}. Tentando ReceitaWS..."
        st.toast(error_msg)
        print(f"Erro na BrasilAPI: {e}")


    # --- Tentativa 2: ReceitaWS (se a primeira falhou) ---
    if not api_data:
        try:
            url_receitaws = f"https://receitaws.com.br/v1/cnpj/{t_cnpj}"
            # ReceitaWS pode ter limites mais estritos, atenção ao User-Agent e frequência
            headers_receita = {'User-Agent': 'MeuAppStreamlit/1.0'}
            # A API gratuita pode ter limites de requisição por minuto.
            # A versão paga requer autenticação (Authorization Bearer Token)
            # headers_receita = {'Authorization': f'Bearer SEU_TOKEN_RECEITAWS'}
            response_receitaws = requests.get(url_receitaws, timeout=15, headers=headers_receita) # Timeout maior

            if response_receitaws.status_code == 200:
                # Verifica se a resposta da ReceitaWS não é de erro interno dela
                receita_data = response_receitaws.json()
                if receita_data.get("status") != "ERROR":
                     api_data = receita_data
                     api_source = 'receitaws'
                     st.toast("✅ Consulta via ReceitaWS bem-sucedida.")
                else:
                     # A API retornou 200, mas com uma mensagem de erro dela
                     error_msg = f"ReceitaWS retornou erro: {receita_data.get('message', 'Erro desconhecido')}"
                     st.toast(f":red[{error_msg}]")
                     print(error_msg)

            # Tratar código 429 (Too Many Requests) especificamente se ocorrer com frequência
            elif response_receitaws.status_code == 429:
                 error_msg = "ReceitaWS falhou: Limite de requisições atingido (429)."
                 st.toast(f":red[{error_msg}]")
                 print(error_msg)
            elif response_receitaws.status_code == 404:
                 error_msg = "ReceitaWS falhou: CNPJ não encontrado (404)."
                 st.toast(f":orange[{error_msg}]")
                 print(error_msg)
            else:
                 error_msg = f"ReceitaWS falhou com status: {response_receitaws.status_code}."
                 st.toast(f":red[{error_msg}]")
                 print(error_msg)


        except requests.exceptions.RequestException as e:
            error_msg = f"Erro ao conectar à ReceitaWS: {e}"
            st.toast(f":red[{error_msg}]")
            print(f"Erro na ReceitaWS: {e}")


    # --- Processamento Final ---
    if api_data and api_source:
        try:
            process_cnpj_data(api_data, api_source, yy, lista_dam)
            return True # Indica sucesso
        except Exception as e:
            # Captura erro durante o processamento/exibição
            st.toast(f":red[Erro ao processar dados do CNPJ: {e}]")
            print(f"Erro em process_cnpj_data ou show_dadosCnpj: {e}")
            # Verifica se o erro é específico do dialog já aberto
            error_str = str(e)
            if 'Only one dialog is allowed' in error_str:
                pass # Ignora esse erro específico
            return False
    else:
        # Se ambas as APIs falharam ou retornaram erro
        st.toast(":red[Não foi possível consultar o CNPJ em nenhuma das fontes.]")
        return False


def get_cnpj_raw(cnpj):
    try:
        t_cnpj = re.sub(r"\D", "", cnpj)
        url = f"https://brasilapi.com.br/api/cnpj/v1/{t_cnpj}"
        response = requests.get(url)
        if response.status_code == 200:
            dados = response.json()  
            return dados
        else:
            st.toast(f"Houve um erro na consulta: {response.status_code}.")
            return False
    except Exception as e:
        error = str(e)
        if 'Only one dialog is allowed' in error:
            pass
        else:
            st.toast(f":red[Erro na consulta do CNPJ: {e}]")
        print(f"Erro em get_cnpj: {e}")
        return False

def fill_form_lf(n_proc, ano):     
    result = None
    c_proc = re.sub(r'/.*', '', str(n_proc))

    def fill_2024_digitless():
        # base provisória, deve ser excluída em breve. Até porque ela é redundante. Já existe na condição case abaixo. E é um espelho (IMPORT) da base abaixo
            #df_2024 = st.session_state.lf_digitadas_2024 ########################
            df_2024 = pesquisa_processo_digitacao(n_proc, ano)
            #int_proc = int(c_proc)
            result = df_2024[(df_2024["Número Processo"] == c_proc)]
            if c_proc in result["Número Processo"].values:

                fill_base_2024(result, st.session_state.is_typewrited)
                
                # garantia de que ao menos processo e CNPJ serão os mesmos em base LF
                
                # st.session_state.intern_proc = result.iloc[0]["Processo"]
                clean_proc = str(result.iloc[0]["Número Processo"])
                st.session_state.intern_proc = clean_proc.split('/')[0]
                st.session_state.intern_cpf_cnpj = result.iloc[0]["CPF / CNPJ"]
            else:
                st.toast(f":red[Nenhum processo {c_proc}/{ano} foi encontrado na base de dados.]")
                clear_st_session_state_lf()
    
    def fill_rest_of_all():
        # coloquei o 2024 aqui porque o download do arquivo XLSX da caceta do Excel limita os caracteres máximos
        # a 255. Dessa forma, o despacho às vezes vinha cropado.

        ws = get_worksheet(1, st.secrets['sh_keys']['geral_lfs']) #############################
        
        cells = ws.findall(c_proc, in_column=1)

        if cells:  
            # Obtém o cabeçalho
            header = ws.row_values(1)

            # Lista para armazenar os resultados processados
            results = []    

            # Verifica cada célula encontrada para o segundo critério
            for cell in cells:
                index = cell.row
                # Segundo critério: Verifica se o valor na coluna 17 da mesma linha é '2024'
                if ws.cell(index, 17).value.strip() == str(ano):
                    row = ws.row_values(index)  # Obtém a linha correspondente

                    # Ajustar o comprimento de `row` para corresponder ao `header`
                    if len(row) < len(header):
                        row += [''] * (len(header) - len(row))

                    # Cria um dicionário combinando cabeçalho e linha
                    result = dict(zip(header, row))
                    results.append(result)

            # Converte os resultados em um DataFrame
            if results:
                df = pd.DataFrame(results)
                # Exemplo: Processa o DataFrame com sua função personalizada
                # fill_st_session_state_lf(df, False)
                fill_st_session_state_lf(df, st.session_state.is_typewrited)
                # garantia de que ao menos processo e CNPJ serão os mesmos em base LF

                # st.session_state.intern_proc = df["Processo"]
                clean_proc = str(df["Processo"])
                st.session_state.intern_proc = clean_proc.split('/')[0]
                st.session_state.intern_cpf_cnpj = df["CPF / CNPJ"]
        else:
            # processo não encontrado, deve dar erro.
            fill_base_geral(st.session_state.base_geral, True)
    
    
    match str(ano):
        case '2024':
            if st.session_state.is_typewrited:
                fill_rest_of_all()
            else:
                fill_2024_digitless()
                
        case '2025' | '2026' | '2027' | '2028': # tirei 2024 só p testar em 15/01/2025
            fill_rest_of_all()

        case _:
            st.toast(f"Ano está bugado → {ano}")


# pesquisa de processo na base geral somente. FICA FALTANDO IMPLEMENTAR A PESQUISA NA BASE ATUAL
def pesquisa_processo_digitacao(n_proc, ano_proc):
    # n_proc = int(n_proc) # caceteiro
    n_proc = str(n_proc).strip() # caceteiro
    ano_proc = str(ano_proc).strip()
               
    match ano_proc:

        case '2024':
            # Verificar se o dataframe existe no estado da sessão
            if 'merged_df' not in st.session_state or st.session_state.merged_df is None:
                st.toast(":red[O dataframe 'merged_df' não está disponível no estado da sessão.]")
                return None

            # Obter o dataframe
            df = st.session_state.merged_df
    
            # Garantir que as colunas necessárias estão presentes no dataframe
            if "Número Processo" not in df.columns or "Data Criação" not in df.columns:
                st.toast(":red[As colunas 'Número Processo' ou 'Data Criação' não estão presentes no dataframe.]")
                return None

            # Extrair o ano da coluna 'Data Criação'
            df["Ano Criação"] = df["Data Criação"].str[-4:]
            # print(df["Número Processo"].dtype)

            # Aplicar os filtros
            resultados = df[(df["Tipo Processo"] == "Licença de Funcionamento") & (df["Número Processo"] == n_proc) & (df["Ano Criação"] == str(ano_proc))]
            # indices_encontrados = resultados.index.tolist()
            # print(f"Teste de índices encontrados: {indices_encontrados}")

            if resultados.empty:
                #st.toast(f"red[O processo **{n_proc}** não foi encontrado (base {ano_proc}).]")
                return None
            
            return resultados
            
        case '2025':
            
            ws = get_worksheet(2, st.secrets['sh_keys']['geral_major'])

            if ano_proc == '2024':
                proc_ano = f"{n_proc}/24"
            elif ano_proc == '2025':
                proc_ano = f"{n_proc}/25"
            else:
                st.toast("Erro em load_functions e pesquisa_processo_digitacao, if ano_proc == '2024':")
                return None

            cell = ws.find(proc_ano, in_column=23)

            if cell:
                index = cell.row
                header = ws.row_values(1)  # Captura o cabeçalho
                row = ws.row_values(index)  # Captura a linha do processo

                # Garante que a linha tenha pelo menos 26 colunas (A-Z)
                while len(row) < 26:
                    row.append("")

                result = dict(zip(header, row))  # Cria o dicionário com as colunas corretas
                df = pd.DataFrame([result])

                st.session_state.base_geral = df

                # Salva a linha encontrada
                st.session_state.linha_do_proc_encontrada = index

                return df

            else:
                return None

        case _:
            st.toast("Implemente os outros anos, major...")



@st.dialog("Dados do Processo", width="large")
def show_dadosProcesso(df):
    df_conv = df.to_json(orient="records", indent=2)
    st.json(df_conv)



@st.dialog("Ocorrências", width="large", )
def get_ocorrencias(pessoa: str, type: str):
    sheet = None
    col_pessoa = None

    with st.spinner("Aguarde..."):
        # Define a aba e a coluna para busca com base no tipo
        match type:
            case 'taxas':
                sheet = 0
                col_pessoa = 7
            case 'lf':
                sheet = 2
                col_pessoa = 4
            case 'diversos':
                sheet = 1
                col_pessoa = 4
            case _:
                st.toast(":red[Daniel, chame a função get_ocorrencias corretamente...]")
                return None

        if sheet is not None:
            # Obtém a planilha
            worksheet = get_worksheet(sheet, st.secrets['sh_keys']['geral_major'])
            
            try:
                # Obtém todos os valores da planilha
                data = worksheet.get_all_values()
                df = pd.DataFrame(data[1:], columns=data[0])  # Cria DataFrame com cabeçalho
                
                # Filtra linhas onde a coluna especificada contém o termo 'pessoa'
                filtered_df = df[df.iloc[:, col_pessoa].str.contains(pessoa, na=False, case=False)]
                
                # Seleciona e processa as colunas especificadas
                result_df = pd.DataFrame()

                if type == 'taxas':
                    result_df['Ocorrência'] = filtered_df.iloc[:, 9]
                    result_df['Protocolo'] = filtered_df.iloc[:, 0]
                    result_df['Submissão'] = filtered_df.iloc[:, 1]
                    result_df['Dados'] = filtered_df.iloc[:, 2] + ', ' + filtered_df.iloc[:, 4]
                    result_df['CPF /CNPJ'] = filtered_df.iloc[:, 7]
                    result_df['E-mails'] = filtered_df.iloc[:, 15] + ', ' + filtered_df.iloc[:, 16]
                    result_df['Valor'] = filtered_df.iloc[:, 26]
                    result_df['Status'] = filtered_df.iloc[:, 27]
                    result_df['DAM'] = filtered_df.iloc[:, 32]
                    result_df['Motivo'] = filtered_df.iloc[:, 31]
                    result_df['Resposta'] = filtered_df.iloc[:, 30]
                    result_df['E-mail enviado'] = filtered_df.iloc[:, 33]      
                    
                elif type == 'lf':
                    result_df['Ocorrência'] = filtered_df.iloc[:, 6]
                    result_df['Protocolo'] = filtered_df.iloc[:, 0]
                    result_df['Submissão'] = filtered_df.iloc[:, 1]
                    result_df['Nome da empresa'] = filtered_df.iloc[:, 3]
                    result_df['CPF /CNPJ'] = filtered_df.iloc[:, 4]
                    result_df['Tipo empresa'] = filtered_df.iloc[:, 8]
                    result_df['Valor DAM'] = filtered_df.iloc[:, 15] 
                    result_df['Tipo licenciamento'] = filtered_df.iloc[:, 3]
                    result_df['Status'] = filtered_df.iloc[:, 16]
                    result_df['Motivo'] = filtered_df.iloc[:, 20]
                    result_df['GDOC'] = filtered_df.iloc[:, 22] + ' - ' + filtered_df.iloc[:, 23]
                    result_df['E-mail enviado'] = filtered_df.iloc[:, 24]
                    result_df['E-mails'] = filtered_df.iloc[:, 10] + ', ' + filtered_df.iloc[:, 11] 
                    result_df['Obs. do solicitante'] = filtered_df.iloc[:, 9]

                elif type == 'diversos':
                    result_df['Ocorrência'] = filtered_df.iloc[:, 6]
                    result_df['Tipo processo'] = filtered_df.iloc[:, 2]
                    result_df['Protocolo'] = filtered_df.iloc[:, 0]
                    result_df['Submissão'] = filtered_df.iloc[:, 1]
                    result_df['Nome da empresa'] = filtered_df.iloc[:, 3]
                    result_df['CPF /CNPJ'] = filtered_df.iloc[:, 4]
                    result_df['Tipo empresa'] = filtered_df.iloc[:, 8]
                    result_df['Valor DAM'] = filtered_df.iloc[:, 17]
                    result_df['Status'] = filtered_df.iloc[:, 18]
                    result_df['Motivo'] = filtered_df.iloc[:, 22]
                    result_df['GDOC'] = filtered_df.iloc[:, 24] + ' - ' + filtered_df.iloc[:, 25]
                    result_df['E-mail enviado'] = filtered_df.iloc[:, 26]
                    result_df['E-mails'] = filtered_df.iloc[:, 10] + ', ' + filtered_df.iloc[:, 11] 
                    result_df['Obs. do solicitante'] = filtered_df.iloc[:, 9]


                if not result_df.empty:
                    result_json = result_df.to_json(orient='records', force_ascii=False)
                    st.json(result_json)
                else:
                    st.toast(":red[**Erro, o dataframe result_df está vazio.**]")
            except Exception as e:
                st.error(f"Erro ao buscar dados: {e}")
                return None
        else:
            return None

    st.write("")
    st.write("")


def so_limpezinha_de_leve():
    st.session_state.fi_divisao = None
    st.session_state.fi_via = ""
    # st.session_state.fi_ano = st.session_state.yyyy
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
    st.session_state.url_gen_pdf = 'https://www.example.com/'


def clear_st_session_state_lf():
    st.session_state.fi_proc = ""
    st.session_state.fi_divisao = None
    st.session_state.fi_risco = None
    st.session_state.fi_via = ""
    # st.session_state.fi_ano = st.session_state.yyyy
    # st.session_state.fi_lf = "" não precisa limpar
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

    st.session_state.is_typewrited = False
    st.session_state.intern_proc = ""
    st.session_state.intern_cpf_cnpj = ""

    st.session_state.url_gen_pdf = 'https://www.example.com/'


def fill_base_geral(df, is_typewrited):
    #
    # esta função usa a planilha '15KVRPS8Ch5YEhBA8oGgFhqAohrD6UZwH5r1mC_vk6Uc'
    #
    clear_st_session_state_lf()
    st.session_state.is_typewrited = is_typewrited
    proc = re.sub(r'/.*', '', df.iloc[0]["GDOC"])

    st.session_state.fi_proc = proc
    st.session_state.fi_divisao = df.iloc[0]["Divisão"]
    st.session_state.fi_via = "1ª Via"
    if is_typewrited:
        st.session_state.fi_emissao = st.session_state.dd_mm_yyyy
    else:
        st.session_state.fi_emissao = ""

    st.session_state.fi_cpf_cnpj = df.iloc[0]["CPF / CNPJ"]
    st.session_state.fi_razao_social = df.iloc[0]["Razão Social"]


def fill_base_2024(df, is_typewrited):
    #
    # esta função usa o dataframe st.session_state.merged_df
    #
    print("entrou na fill_base 2024")
    clear_st_session_state_lf()
    st.session_state.is_typewrited = is_typewrited
    st.session_state.fi_proc = df.iloc[0]["Número Processo"]
    st.session_state.fi_divisao = df.iloc[0]["Divisão"]
    st.session_state.fi_via = "1ª Via"

    if is_typewrited:
        print("entrou na is_typewrited fill_base 2024")
        st.session_state.fi_emissao = st.session_state.dd_mm_yyyy
    else:
        st.session_state.fi_emissao = ""

    st.session_state.fi_cpf_cnpj = df.iloc[0]["CPF / CNPJ"]
    st.session_state.fi_razao_social = df.iloc[0]["Nome Empresa"]


# encher os campos do formulário de digitação
def fill_st_session_state_lf(df, is_typewrited):
    # limpar campos digitação LF

    clear_st_session_state_lf()
    st.session_state.is_typewrited = is_typewrited

    df_t = df.fillna("")
    # print(df_t.columns)

    # print(f"data emissão: {df_t.iloc[0]["Emissão"]}")
    if is_typewrited: 
        st.session_state.fi_emissao = df_t.iloc[0]["Emissão"]
    else:
        st.session_state.fi_emissao = st.session_state.dd_mm_yyyy
        

    n_proc = re.sub(r'\.0\b', '', str(df_t.iloc[0]["Número"]))

    n_lf = f"{df_t.iloc[0]["Nº Licença"]}/{str(df_t.iloc[0]["Ano"])[2:4]}"
    # carregar os dados nos campos
    st.session_state.fi_proc = str(df_t.iloc[0]["Processo"])
    st.session_state.fi_divisao = df_t.iloc[0]["Divisão"]
    st.session_state.fi_lf = n_lf
    st.session_state.fi_via = str(df_t.iloc[0]["Via"])
    # st.session_state.fi_emissao = df_t.iloc[0]["Emissão"]
    st.session_state.fi_logradouro = df_t.iloc[0]["Endereço"]
    st.session_state.fi_numero = f"{n_proc}"
    st.session_state.fi_bairro = df_t.iloc[0]["Bairro"]
    st.session_state.fi_cep = df_t.iloc[0]["CEP"]
    st.session_state.fi_cpf_cnpj = df_t.iloc[0]["CPF / CNPJ"]
    st.session_state.fi_razao_social = df_t.iloc[0]["Razão Social"]
    st.session_state.fi_responsavel = df_t.iloc[0]["Responsável"]
    st.session_state.fi_conselho = df_t.iloc[0]["Inscrição Conselho"]
    st.session_state.fi_atividade = df_t.iloc[0]["Atividade"]
    st.session_state.fi_descricao = df_t.iloc[0]["Descrição"]
    # print(st.session_state.fi_descricao)
    # print(df_t.iloc[0]["Descrição"])
    st.session_state.fi_complemento = df_t.iloc[0]["Complemento"]
    st.session_state.fi_comercializar = df_t.iloc[0]["Comercializar"]
    st.session_state.fi_codigo = df_t.iloc[0]["CNAE"]

    # carregar a URL se existir
    # print(f'df_t.iloc[0]["Documento"]:{df_t.iloc[0]["Documento"]}')
    if df_t.iloc[0]["Documento"] == "":    
        st.session_state.url_gen_pdf = 'https://www.example.com/'
    else:
        st.session_state.url_gen_pdf = df_t.iloc[0]["Documento"]
       

def certifica_lf_resetFields():
    st.session_state.lf_document = 'about:blank'
    st.session_state.val_numLf = ""
    st.session_state.val_nomeEmpresa = ""
    st.session_state.val_cpfCnpj = ""
    st.session_state.val_viaLf = ""
    st.session_state.val_divisao = ""
    st.session_state.val_risco = ""
    st.session_state.val_dataEmissao = ""
    st.session_state.val_dataEnvio = ""
    st.session_state.val_email1 = ""
    st.session_state.val_email2 = ""
    st.session_state.val_codigo = ""
    st.session_state.val_descricao = ""
    st.session_state.ano_lf = ""
    st.session_state.val_processo = ""


       
def certifica_carregar_lf(df):
    # st.session_state.val_ano = df.iloc[0]["Ano"]
    # st.session_state.val_proc = df.iloc[0]["Processo"]
    certifica_lf_resetFields()

    if df.iloc[0]["Documento"]:
        st.session_state.lf_document = df.iloc[0]["Documento"]
    else:
        st.session_state.lf_document = 'about:blank'
    
    if df.iloc[0]["Nº Licença"]:
        st.session_state.is_matched = True
    else:
        st.session_state.is_matched = False

    st.session_state.val_processo = f'{df.iloc[0]["Processo"]}/{df.iloc[0]["Ano"]} - {df.iloc[0]["Divisão"]}'
    
    match len(df.iloc[0]["Nº Licença"]):
        case 1:
            st.session_state.val_numLf = f'000{df.iloc[0]["Nº Licença"]}/{df.iloc[0]["Ano"][2:4]}'
        case 2:
            st.session_state.val_numLf = f'00{df.iloc[0]["Nº Licença"]}/{df.iloc[0]["Ano"][2:4]}'
        case 3:
            st.session_state.val_numLf = f'0{df.iloc[0]["Nº Licença"]}/{df.iloc[0]["Ano"][2:4]}'
        case 4:
            st.session_state.val_numLf = f'{df.iloc[0]["Nº Licença"]}/{df.iloc[0]["Ano"][2:4]}'
    
    st.session_state.val_nomeEmpresa = df.iloc[0]["Razão Social"]
    st.session_state.val_cpfCnpj = df.iloc[0]["CPF / CNPJ"]
    st.session_state.val_viaLf = df.iloc[0]["Via"]
    st.session_state.val_divisao = df.iloc[0]["Divisão"]
    st.session_state.val_risco = df.iloc[0]["Risco"]
    st.session_state.val_dataEmissao = df.iloc[0]["Emissão"]
    st.session_state.val_dataEnvio = df.iloc[0]["Data Entrega"]
    st.session_state.val_email1 = df.iloc[0]["E-mail"]
    st.session_state.val_email2 = df.iloc[0]["E-mail CC"]
    st.session_state.val_codigo = df.iloc[0]["CNAE"]
    st.session_state.val_descricao = df.iloc[0]["Descrição"]
    st.session_state.val_obs = df.iloc[0]["Observação"]
    st.session_state.ano_lf = df.iloc[0]["Ano"]
    st.rerun()

# lógica para salvar na planilha de lf
def gerar_num_lf_e_linha_proc(ws, ano, check_lf):
    
    chk_lf = int(check_lf)
    #  try:
    # print(f"check lf é é é é {chk_lf} e {type(chk_lf)}")
    col2 = ws.col_values(2)[1:]  # Ignora o cabeçalho
    col17 = ws.col_values(17)[1:]  # Ignora o cabeçalho

    df = pd.DataFrame({
            'col2': pd.to_numeric(col2, errors='coerce'),
            'col17': pd.to_numeric(col17, errors='coerce')
        })

    df_filtered = df[df['col17'] == int(ano)]
    # print(f"df_filtered: {df_filtered}")
    
    if chk_lf == 0:
        largest = max(df_filtered['col2'], default=0)

        indices = len(ws.col_values(1)) + 1 # última linha da planilha + 1
        num_lf = largest + 1

        # CUIDADO! TENTA VER UMA FORMA DE MANTER O NÚMERO DE LF SE O PROCESSO EXISTIR
        return int(num_lf), indices
    else:
        df_row = df_filtered[df_filtered['col2'] == chk_lf]
        indices = df_row.index.tolist()
        # print(f"indices: {indices}")
        indices[0] = indices[0] + 2 # !!!!!!!!!!!!!!!!!

        num_lf = chk_lf
        return int(num_lf), indices[0]

    
    # except Exception as e:
    #     print(f"Erro ao processar a planilha: {e}")
    #     return None, None


def salvar_lf_digitada(this_date: str, generate_doc: bool):
    # MENSAGEM
    if generate_doc:
        st.toast(f":orange[Iniciando processo de criação de LF do proc. **{st.session_state.fi_proc}**. Aguarde...]")
    else:
        st.toast(f":orange[Tentando salvar o proc. **{st.session_state.fi_proc}**. Aguarde...]")
    
    this_year = this_date[6:10]
    this_year = int(this_year)
    anos = [f'{this_year-1}',f'{this_year}']

    if st.session_state.fi_ano not in anos:
        return st.toast(":red[Há um erro no campo Ano]")
    
    if st.session_state.fi_proc != st.session_state.intern_proc:
        return st.toast(":red[O número do processo não condiz com o processo do banco de dados.]")
    if not st.session_state.fi_divisao:
        return st.toast(":red[Preencha o campo **Divisão**]")
    if not st.session_state.fi_risco:
        return st.toast(":red[Preencha o campo **Risco**]")
    # if not validar_cpf_cnpj(st.session_state.fi_cpf_cnpj):
    #     return st.toast(f":red[O número {st.session_state.fi_cpf_cnpj} é inválido.]")
    if not st.session_state.fi_logradouro:
        return st.toast(":red[Preencha o campo **Logradouro**]")
    if not st.session_state.fi_numero:
        return st.toast(":red[Preencha o campo **Número**]")
    if not st.session_state.fi_bairro:
        return st.toast(":red[Preencha o campo **Bairro**]")
    if len(st.session_state.fi_cep)<10:
        return st.toast(":red[Houve um erro no campo **CEP**]")
    if not st.session_state.fi_responsavel:
        return st.toast(":red[Preencha o campo **Responsável**]")
    if not st.session_state.fi_atividade:
        return st.toast(":red[Preencha o campo **Atividade**]")
    if len(st.session_state.fi_codigo)<9:
        return st.toast(":red[Preencha o campo **Código**]")
    if not st.session_state.fi_descricao:
        return st.toast(":red[Preencha o campo **Descrição**]")
    
    ws = get_worksheet(1, st.secrets['sh_keys']['geral_lfs'])

    #print(f"st.session_state.is_typewrited: {st.session_state.is_typewrited}")
    if st.session_state.is_typewrited:
        check_lf = re.sub(r'/.*', '', str(st.session_state.fi_lf))
    else:
        check_lf = 0

    # print(f"O ano que está causando a bagaceira: {st.session_state.fi_ano}")
    numero_lf, linha_proc = gerar_num_lf_e_linha_proc(ws, st.session_state.fi_ano, check_lf)
    
    print(f"numero_lf: {numero_lf}")
    print(f"linha_proc: {linha_proc}")

    # linha_proc = linha_proc[1] + 3
    # numero_lf = int(numero_lf) + 1

    # print(f"numero_lf: {numero_lf}; e linha_proc: {linha_proc}")

    if numero_lf >= 0:

        receptor_row = linha_proc
        
        range_ws_0 = f"A{receptor_row}:Z{receptor_row}"

        st.session_state.fi_emissao = get_this_date()
        # clean_proc = re.sub(r'/.*', '', st.session_state.intern_proc)
        current_date = get_current_datetime()

        range_AZ = [
            st.session_state.intern_proc, # Processo 
            numero_lf, # Nº Licença
            st.session_state.fi_atividade, # Atividade
            st.session_state.fi_comercializar, # Comercializar
            st.session_state.fi_codigo, # CNAE
            st.session_state.fi_descricao, # Descrição
            st.session_state.fi_razao_social, # Razão Social
            st.session_state.intern_cpf_cnpj, # CPF / CNPJ
            st.session_state.fi_logradouro, # Endereço
            st.session_state.fi_complemento, # Complemento
            st.session_state.fi_numero, # Número
            st.session_state.fi_bairro, # Bairro
            st.session_state.fi_cep, # CEP
            st.session_state.fi_responsavel, # Responsável
            st.session_state.fi_conselho, # Inscrição Conselho
            st.session_state.fi_emissao, # Emissão
            st.session_state.fi_ano, # Ano
            st.session_state.fi_divisao, # Divisão
            '', ## espaço da fórmula na planilha
            st.session_state.lf_ativa, # Status ############## esssa variável pode ser usada para definir se um proc está ativo ou não (sugestão)
            st.session_state.fi_obs, # Observação / Justificativa
            st.session_state.fi_via, # Via
            st.session_state.sessao_servidor, # Servidor
            current_date, # Data modificação
            st.session_state.url_gen_pdf, # coluna Y, url da lf digitada
            st.session_state.fi_risco, # coluna Z, grau de risco
        ]

        # Tornar tudo maiúsculo
        def capitalize(list):
            resultado = []
            # Loop pela lista
            for item in list:
                if isinstance(item, str):  # Verifica se o item é uma string     
                    if item == list[25] or item == list[22] or item == list[21] or item == list[19]: # se for risco ou servidor ou via ou ativo ou risco, não converte
                        # print(f"entrou em capitalize(list) if item == list[22] or item == list[21]. item = {item}")
                        resultado.append(item)   
                    else:
                        resultado.append(item.upper())
                        
                else:
                    resultado.append(item)  # Adiciona o item original à nova list
            return resultado

        range_AZc = capitalize(range_AZ)

        # IMPORTANTÍSSIMO: GERAR DOC DA LF SALVA. DEVO VER OS LIMITES QUOTA DO GOOGLE PORQUE SÃO MUITOS ACESSOS DE GSPREAD E API...
        id_doc_digitado = gerar_doc_lf(range_AZc)

        if not id_doc_digitado:
            return st.toast(f":red[Erro: id_doc_digitado, {id_doc_digitado}]")
        
        st.session_state.url_gen_pdf = f"https://docs.google.com/document/d/{id_doc_digitado}/export?format=pdf"

        #print(f"url_lf_digitada: {st.session_state.url_gen_pdf}")
        range_AZc[24] = st.session_state.url_gen_pdf
        #print(f"range_AZc[24] precisa ser o mesmo da url digitada → {range_AZc[24]}")
        
        # ficou estranho pq primeiro ele gera doc, depois ele gera PDF...

        # MENSAGEM
        st.toast(f"Salvando dados da LF **{numero_lf}** no banco...")    
        ws.update(range_ws_0, [range_AZc], raw=False)

        # salvar numero de lf em geral, independente de já existir LF ou não
        # MENSAGEM
        #st.toast(f"Registrando o nº LF no banco de processos...")    
        if st.session_state.fi_ano == "2025":
            wx = get_worksheet(2, st.secrets['sh_keys']['geral_major'])
            range_major = f"Z{st.session_state.linha_do_proc_encontrada}" # salvar na coluna Z de Licença base geral
            print(f"range_major será salvo em {range_major}")
            wx.update(range_major, numero_lf, raw=False)
        else:
            print(f"Nada de range major. O ano é {st.session_state.fi_ano}")

        # salvar no histório as alterações feitas
        # MENSAGEM
        #st.toast(f"Alimentando o histórico de alterações...")    
        wz = get_worksheet(2, st.secrets['sh_keys']['geral_lfs'])
        last_wz = len(wz.col_values(1))
        last_wz += 1
        range_wz = f"A{last_wz}:Z{last_wz}"
        wz.update(range_wz, [range_AZc], raw=False)

        st.toast(f":green[**Dados salvos na linha {receptor_row}**].")

    else:
        st.toast(":red[Erro desconhecido, linha 1015 load_funcions]")



def save_in_base_geral(df):
    st.warning("Zé da manga")

#
# Automação de e-mails python ################   ##################
# 

def email_taxas(**kwargs):
    if kwargs['kw_status'] == 'Deferido':
        tipo_solicitacao = 'Deferimento'
        email_body = f"""
        <html>
        <body>
            <p style="color:#000066;">| Por favor, <strong>não responda a este e-mail.</strong> Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
            <br>
            <p>Olá,</p>            
            <p>Sua solicitação de <strong>DAM da Vigilância Sanitária</strong> (código <strong>{kwargs['kw_protocolo']}</strong>, feita em <strong>{kwargs['kw_data_sol']}</strong>), para o tipo <strong>{kwargs['kw_tipo_proc']}{kwargs['kw_complemento_1']}</strong>, ao estabelecimento <strong>{kwargs['kw_cpf_cnpj']}</strong> foi <strong><span style="color: #009933;">deferida</span></strong>. Segue abaixo a taxa emitida, conforme solicitação.</p>         
            <p>O DAM é pagável em qualquer banco, aplicativo de pagamento bancário ou casa lotérica, até a data do vencimento.</p>
            <hr>
            <ul style="padding: 0;">
                <li>
                    <strong>Imprima o boleto diretamente na página da SEFIN → </strong>
                    <a href="http://siat.belem.pa.gov.br:8081/arrecadacao/pages/arrecadacao/guiaArrecadacaoDetalheExterno.jsf?id={kwargs['kw_numero_dam']}&op=4" 
                    style="display: inline-block; padding: 3px 8px; color: white; background-color: #00529B; text-decoration: none; 
                    border-radius: 15px; font-weight: bold;">
                    Clique aqui 🔗
                    </a>
                    
                </li>
            </ul>
            <hr>
            <p>Ao acessar a página, clique no botão <strong>Reemitir DAM</strong>.</p>
            <p>
                <span style="display: inline-block; padding: 5px 10px; background-color: #00529B; color: white; 
                border-radius: 15px; font-weight: bold;">
                    Após o pagamento do boleto, solicite o seu processo online em:
                </span>
            </p>
            <ul style="padding: 0;">
                <li>
                    <strong>Primeira licença ou renovação da licença → </strong>
                    <a href="https://sites.google.com/view/secretariadevisa/início/processos" 
                    style="text-decoration: none; font-weight: bold;">
                    Clique aqui 🔗
                    </a>
                </li>
                <li style="margin-top: 10px;">
                    <strong>Demais processos → </strong>
                    <a href="https://sites.google.com/view/secretariadevisa/início/processos/diversos" 
                    style="text-decoration: none; font-weight: bold;">
                    Clique aqui 🔗
                    </a>
                </li>
            </ul>
        <br>
        <ul style="padding: 0;">
            <p><strong>Observações importantes</strong>:</p>
            <li><p>O sistema de emissão de DAMs de Belém <strong>está sob responsabilidade da Secretaria de Finanças (SEFIN)</strong>. Se existir algum problema com o link fornecido ou com o boleto, entre em contato com a SEFIN pelo site https://sefin.belem.pa.gov.br (procure pela seção "Fale conosco"). <mark>A Vigilância Sanitária não possui gerência sobre o sistema.</mark></p></li>
            <li><p>O processo <strong>autenticação / encerramento de livro físico</strong>, é aberto presencialmente, no Protocolo da SESMA.</p></li>
            <li><p><strong> Consulta de boleto é feita SOMENTE pelo sistema da SEFIN</strong>. Acesse pelo link: https://sefin.belem.pa.gov.br/servicos/2-via-consulta-de-dam-tributos-municipais-2/</p></li>
        </ul>

            <br>
            <p>Atenciosamente,</p>
            <img src="cid:signature_image" style="width: auto; height: auto;">
            <br>
            <p style="color:#000066;">| Por favor, <strong>não responda a este e-mail.</strong> Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>

        </body>
        </html>
    """

    elif kwargs['kw_status'] == 'Indeferido':
        tipo_solicitacao = 'Indeferimento'
        email_body = f"""
            <html>
                <body>
                    <p style="color:#000066;">| Por favor, <strong>não responda a este e-mail.</strong> Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
                    <br>
                    <p>Olá,</p>            
                    <p>Sua solicitação de <strong>DAM da Vigilância Sanitária</strong> (código <strong>{kwargs['kw_protocolo']}</strong>, feita em <strong>{kwargs['kw_data_sol']}</strong>), para o tipo <strong>{kwargs['kw_tipo_proc']}{kwargs['kw_complemento_1']}</strong>, ao estabelecimento <strong>{kwargs['kw_cpf_cnpj']}</strong> foi <strong><span style="color: #993300;">indeferida</span></strong>.</p>         
                    <p>Motivo do indeferimento: <mark>{kwargs['kw_motivo_indeferimento']}</mark></p>
                    <p><strong>Solicitações para emissão de taxa indeferidas são descartadas</strong>. Você pode abrir uma nova solicitação através do Formulário de Solicitação de DAM, caso necessite.</p>
                    <br>
                    <p>Atenciosamente,</p>
                    <img src="cid:signature_image" style="width: auto; height: auto;">
                    <br>
                    <p style="color:#000066;">| Por favor, <strong>não responda a este e-mail.</strong> Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
                </body>
            </html>
        """
    else:
        return st.toast("Erro. Verifique o preenchimento dos campos.")
        
    msg = MIMEMultipart("related")
    msg['Subject'] = f"SESMA - Resposta à solicitação {kwargs['kw_protocolo']} ({tipo_solicitacao})"
    msg["From"] = "devisa.taxas@gmail.com"

    if len(kwargs['kw_email2']) > 2:
        to_addresses = [kwargs['kw_email1'], kwargs['kw_email2']]
        msg["To"] = ", ".join(to_addresses)
    else:
        msg["To"] = kwargs['kw_email1']

    image_path = "resources/logo_secretaria.png"

    msg.attach(MIMEText(email_body, "html"))

    with open(image_path, 'rb') as img_file:
        image_mime = MIMEImage(img_file.read(), name="logo_secretaria.png")
        image_mime.add_header("Content-ID", "<signature_image>")
        msg.attach(image_mime)

    password =  st.secrets['apps_psw']['gmail_taxas']
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login(msg["From"], password)
            if len(kwargs['kw_email2']) > 5:
                s.sendmail(msg["From"], to_addresses, msg.as_string())
                st.session_state.is_email_sended_tx = True
                return st.toast(f"Email despachado a {kwargs['kw_email1']} e {kwargs['kw_email2']}.")
            else:
                s.sendmail(msg["From"], msg["To"], msg.as_string())
                st.session_state.is_email_sended_tx = True
                return st.toast(f"Email despachado a {kwargs['kw_email1']}.")
     
    except Exception as e:
        print(f"Erro ao enviar o email: {e}")
        st.toast(f"Falha no envio de e-mail. Daniel, confira o console.")
        return None


def email_diversos(**kwargs):
    if kwargs['kw_status'] == 'Deferido':
        tipo_solicitacao = 'Deferimento'
        match kwargs['kd_divisao']:
            case 'DVSA':
                divisao_nome = "a Divisão de Vigilância Sanitária em Alimentos (DVSA)"
                divisao_email = "dvsa.visa.bel@gmail.com"
            case 'DVSE':
                divisao_nome = "a Divisão de Vigilância Sanitária de Engenharia (DVSE)"
                divisao_email = "devisa.engenharia.sesma@gmail.com"
            case 'DVSCEP':
                divisao_nome = "a Divisão de Vigilância Sanitária das Condições do Exercício Profissional (DVSCEP)"
                divisao_email = "dvscep@yahoo.com.br"
            case 'DVSDM':
                divisao_nome = "a Divisão de Vigilância Sanitária de Drogas e Medicamentos (DVSDM)"
                divisao_email = "devisa.bel@gmail.com"
            case 'Açaí':
                divisao_nome = "o Setor da Casa do Açaí"
                divisao_email = "casadoacai.sesma@gmail.com"
            case 'Visamb':
                divisao_nome = "o Setor de Vigilância em Saúde Ambiental (VISAMB)"
                divisao_email = "devisa.visamb.sesma@gmail.com"
            case _:
                return st.toast("Erro no envio. Problema no campo 'Divisão'.")
            
        email_body = f"""
        <html>
        <body>
            <p style="color:#000066;">| Por favor, <strong>não responda a este e-mail.</strong> Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
            <br>
            <p>Olá,</p>            
            <p>Sua solicitação para abertura de processo eletrônico (código <strong>{kwargs['kw_protocolo']}</strong>, feita em <strong>{kwargs['kw_data_sol']}</strong>), para o tipo <strong>{kwargs['kw_tipo_proc']}</strong>, ao estabelecimento <strong>{kwargs['kw_razao_social']} ({kwargs['kw_cpf_cnpj']})</strong> foi deferida.</p>         
            <p>Segue em anexo o <strong>cartão do protocolo do processo {kwargs['kw_gdoc']}.</strong></p>
            <br>
            <p>Se precisar de ajuda com o processo, ou se deseja consultar sua tramitação, entre em contato diretamente com <strong>{divisao_nome}</strong>, pelo e-mail {divisao_email}, ou pelo telefone (91) 3251-4219.</p>
            <p>Precisa corrigir os dados da empresa no cartão de protocolo? Siga o tutorial deste link ~ <a href="https://sesma.belem.pa.gov.br/wp-content/uploads/2023/11/Ajuste_de_dados_do_Interessado.pdf">Clique para acessar 🔗.</a></p>
            <br>
            <br>
            <p>Atenciosamente,</p>
            <img src="cid:signature_image" style="width: auto; height: auto;">
            <p style="color:#000066;">| Por favor, <strong>não responda a este e-mail.</strong> Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
        </body>
        </html>
        """
    elif kwargs['kw_status'] == 'Indeferido':
        tipo_solicitacao = 'Indeferimento'
        email_body = f"""
            <html>
                <body>
                    <p style="color:#000066;">| Por favor, <strong>não responda a este e-mail.</strong> Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
                    <br>
                    <p>Olá,</p>            
                    <p>Sua solicitação para abertura de processo eletrônico (código <strong>{kwargs['kw_protocolo']}</strong>, feita em <strong>{kwargs['kw_data_sol']}</strong>), para o tipo <strong>{kwargs['kw_tipo_proc']}</strong>, ao estabelecimento <strong>{kwargs['kw_razao_social']} ({kwargs['kw_cpf_cnpj']})</strong> foi indeferida.</p>         
                    <p>Motivo do indeferimento: <mark>{kwargs['kw_motivo_indeferimento']}</mark></p>
                    <br>
                    <p><strong>Todas as solicitações indeferidas são descartadas</strong>. Você pode abrir uma nova solicitação através do Formulário de Processos Diversos, caso necessite.</p>
                    <br>
                    <br>
                    <p>Atenciosamente,</p>
                    <img src="cid:signature_image" style="width: auto; height: auto;">
                    <p style="color:#000066;">| Por favor, <strong>não responda a este e-mail.</strong> Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
                </body>
            </html>
        """
    else:
        return st.toast("Erro. Verifique o preenchimento dos campos.")

    msg = MIMEMultipart("related")
    msg['Subject'] = f"SESMA - Resposta à solicitação {kwargs['kw_protocolo']} ({tipo_solicitacao})"
    msg["From"] = "gdoc.diversos@gmail.com"

    if len(kwargs['kw_email2']) > 2:
        to_addresses = [kwargs['kw_email1'], kwargs['kw_email2']]
        msg["To"] = ", ".join(to_addresses)
    else:
        msg["To"] = kwargs['kw_email1']

    image_path = "resources/logo_secretaria.png"

    msg.attach(MIMEText(email_body, "html"))

    with open(image_path, 'rb') as img_file:
        image_mime = MIMEImage(img_file.read(), name="logo_secretaria.png")
        image_mime.add_header("Content-ID", "<signature_image>")
        msg.attach(image_mime)

    if kwargs['kw_cartao_protocolo']:
        pdf_file = kwargs['kw_cartao_protocolo']
        pdf_mime = MIMEBase('application', 'octet-stream')
        pdf_mime.set_payload(pdf_file.read())
        encoders.encode_base64(pdf_mime)
        pdf_mime.add_header(
            "Content-Disposition", f"attachment; filename={pdf_file.name}"
        )
        msg.attach(pdf_mime)

    password = st.secrets['apps_psw']['gmail_diversos']

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login(msg["From"], password)
            if len(kwargs['kw_email2']) > 5:
                s.sendmail(msg["From"], to_addresses, msg.as_string())
                st.session_state.is_email_sended_d = True
                return st.toast(f"Email despachado a {kwargs['kw_email1']} e {kwargs['kw_email2']}.")
            else:
                s.sendmail(msg["From"], msg["To"], msg.as_string())
                st.session_state.is_email_sended_d = True
                return st.toast(f"Email despachado a {kwargs['kw_email1']}.")
        
    except Exception as e:
        print(f"Erro ao enviar o email: {e}")
        return st.toast("Erro ao enviar o email.")
    

def email_licenciamento(**kwargs):
    if kwargs['kw_status'] == 'Deferido':
        tipo_solicitacao = 'Deferimento'
        match kwargs['kd_divisao']:
            case 'DVSA':
                divisao_nome = "a Divisão de Vigilância Sanitária em Alimentos (DVSA)"
                divisao_email = "dvsa.visa.bel@gmail.com"
            case 'DVSE':
                divisao_nome = "a Divisão de Vigilância Sanitária de Engenharia (DVSE)"
                divisao_email = "devisa.engenharia.sesma@gmail.com"
            case 'DVSCEP':
                divisao_nome = "a Divisão de Vigilância Sanitária das Condições do Exercício Profissional (DVSCEP)"
                divisao_email = "dvscep@yahoo.com.br"
            case 'DVSDM':
                divisao_nome = "a Divisão de Vigilância Sanitária de Drogas e Medicamentos (DVSDM)"
                divisao_email = "devisa.bel@gmail.com"
            case 'Açaí':
                divisao_nome = "o Setor da Casa do Açaí"
                divisao_email = "casadoacai.sesma@gmail.com"
            case 'Visamb':
                divisao_nome = "o Setor de Vigilância em Saúde Ambiental (VISAMB)"
                divisao_email = "devisa.visamb.sesma@gmail.com"
            case _:
                return st.toast("Erro no envio. Problema no campo 'Divisão'.")
            
        email_body = f"""
        <html>
        <body>
            <p style="color:#000066;">| Por favor, <strong>não responda a este e-mail.</strong> Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
            <br>
            <p>Olá,</p>            
            <p>Sua solicitação para abertura de processo eletrônico (código <strong>{kwargs['kw_protocolo']}</strong>, feita em <strong>{kwargs['kw_data_sol']}</strong>), para o tipo <strong>{kwargs['kw_tipo_proc']}</strong>, ao estabelecimento <strong>{kwargs['kw_razao_social']} ({kwargs['kw_cpf_cnpj']})</strong> foi deferida.</p>         
            <p>Segue em anexo o <strong>cartão do protocolo do processo {kwargs['kw_gdoc']}.</strong></p>
            <br>
            <p>Se precisar de ajuda com o processo, ou se deseja consultar sua tramitação, entre em contato diretamente com <strong>{divisao_nome}</strong>, pelo e-mail {divisao_email}, ou pelo telefone (91) 3251-4219.</p>
            <p>Precisa corrigir os dados da empresa no cartão de protocolo? Siga o tutorial deste link ~ <a href="https://sesma.belem.pa.gov.br/wp-content/uploads/2023/11/Ajuste_de_dados_do_Interessado.pdf">Clique para acessar 🔗.</a></p>
            <br>
            <br>
            <p>Atenciosamente,</p>
            <img src="cid:signature_image" style="width: auto; height: auto;">
            <p style="color:#000066;">| Por favor, <strong>não responda a este e-mail.</strong> Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
        </body>
        </html>
        """
    elif kwargs['kw_status'] == 'Indeferido':
        tipo_solicitacao = 'Indeferimento'
        email_body = f"""
            <html>
                <body>
                    <p style="color:#000066;">| Por favor, <strong>não responda a este e-mail.</strong> Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
                    <br>
                    <p>Olá,</p>            
                    <p>Sua solicitação para abertura de processo eletrônico (código <strong>{kwargs['kw_protocolo']}</strong>, feita em <strong>{kwargs['kw_data_sol']}</strong>), para o tipo <strong>{kwargs['kw_tipo_proc']}</strong>, ao estabelecimento <strong>{kwargs['kw_razao_social']} ({kwargs['kw_cpf_cnpj']})</strong> foi indeferida.</p>         
                    <p>Motivo do indeferimento: <mark>{kwargs['kw_motivo_indeferimento']}</mark></p>
                    <br>
                    <p><strong>Todas as solicitações indeferidas são descartadas</strong>. Você pode abrir uma nova solicitação através do Formulário de Licença de Funcionamento, caso necessite.</p>
                    <br>
                    <br>
                    <p>Atenciosamente,</p>
                    <img src="cid:signature_image" style="width: auto; height: auto;">
                    <p style="color:#000066;">| Por favor, <strong>não responda a este e-mail.</strong> Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
                </body>
            </html>
        """
    else:
        return st.toast("Erro. Verifique o preenchimento dos campos.")
    
    msg = MIMEMultipart("related")
    msg['Subject'] = f"SESMA - Resposta à solicitação {kwargs['kw_protocolo']} ({tipo_solicitacao})"
    msg["From"] = "gdoc.licenciamento@gmail.com"

    if len(kwargs['kw_email2']) > 2:
        to_addresses = [kwargs['kw_email1'], kwargs['kw_email2']]
        msg["To"] = ", ".join(to_addresses)
    else:
        msg["To"] = kwargs['kw_email1']

    image_path = "resources/logo_secretaria.png"

    msg.attach(MIMEText(email_body, "html"))

    with open(image_path, 'rb') as img_file:
        image_mime = MIMEImage(img_file.read(), name="logo_secretaria.png")
        image_mime.add_header("Content-ID", "<signature_image>")
        msg.attach(image_mime)

    if kwargs['kw_cartao_protocolo']:
        pdf_file = kwargs['kw_cartao_protocolo']
        pdf_mime = MIMEBase('application', 'octet-stream')
        pdf_mime.set_payload(pdf_file.read())
        encoders.encode_base64(pdf_mime)
        pdf_mime.add_header(
            "Content-Disposition", f"attachment; filename={pdf_file.name}"
        )
        msg.attach(pdf_mime)

    password = st.secrets['apps_psw']['gmail_licenciamento']

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login(msg["From"], password)
            if len(kwargs['kw_email2']) > 5:
                s.sendmail(msg["From"], to_addresses, msg.as_string())
                st.session_state.is_email_sended_lf = True
                return st.toast(f"Email despachado a {kwargs['kw_email1']} e {kwargs['kw_email2']}.")
            else:
                s.sendmail(msg["From"], msg["To"], msg.as_string())
                st.session_state.is_email_sended_lf = True
                return st.toast(f"Email despachado a {kwargs['kw_email1']}.")
        
    except Exception as e:
        print(f"Erro ao enviar o email: {e}")
        return st.toast("Erro ao enviar o email.")
    

def email_enviarLicenca(**kwargs):
    email_body = f"""
        <html>
        <body>
            <p style="color:#000066;">| Por favor, <strong>não responda a este e-mail.</strong> Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
            <br>
            <p>Olá,</p>           
            <p>{kwargs['kw_despacho']}</p>  
            <br>
            <br>
            <p>Atenciosamente,</p>
            <img src="cid:signature_image" style="width: auto; height: auto;">
            <p style="color:#000066;">| Por favor, <strong>não responda a este e-mail.</strong> Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
        </body>
        </html>
        """
    
    msg = MIMEMultipart("related")
    msg['Subject'] = f"Licença de Funcionamento {kwargs['kw_ano']} - SESMA / DEVISA"
    # msg["From"] = "secretariadevisa@gmail.com"
    msg["From"] = "secretariadevisa@yahoo.com"

    if len(kwargs['kw_email2']) > 2:
        to_addresses = [kwargs['kw_email1'], kwargs['kw_email2']]
        msg["To"] = ", ".join(to_addresses)
    else:
        msg["To"] = kwargs['kw_email1']

    image_path = "resources/logo_secretaria.png"

    msg.attach(MIMEText(email_body, "html"))

    with open(image_path, 'rb') as img_file:
        image_mime = MIMEImage(img_file.read(), name="logo_secretaria.png")
        image_mime.add_header("Content-ID", "<signature_image>")
        msg.attach(image_mime)

    if kwargs['kw_licenca']:
        pdf_file = kwargs['kw_licenca']
        pdf_mime = MIMEBase('application', 'octet-stream')
        pdf_mime.set_payload(pdf_file.read())
        encoders.encode_base64(pdf_mime)
        pdf_mime.add_header(
            "Content-Disposition", f'attachment; filename="{pdf_file.name}"'
        )
        msg.attach(pdf_mime)

    # password = st.secrets['apps_psw']['gmail_secretariadevisa']
    password = st.secrets['apps_psw']['yahoo_secretariadevisa']

    try:
        # with smtplib.SMTP('smtp.gmail.com', 587) as s:
        with smtplib.SMTP('smtp.mail.yahoo.com', 587) as s:
            s.starttls()
            s.login(msg["From"], password)
            if len(kwargs['kw_email2']) > 5:
                s.sendmail(msg["From"], to_addresses, msg.as_string())
                st.session_state.is_email_sended_entregalf = True
                return st.toast(f":green[Email despachado a {kwargs['kw_email1']} e {kwargs['kw_email2']}].")
            else:
                s.sendmail(msg["From"], msg["To"], msg.as_string())
                st.session_state.is_email_sended_entregalf = True
                return st.toast(f"Email despachado a {kwargs['kw_email1']}.") 
    except Exception as e:
        print(f"Erro ao enviar o email: {e}")
        return st.toast(":red[Erro ao enviar o email.]")

def email_aprojeto(**kwargs):
    despacho = None
    kw_obs = kwargs['kw_obs'].strip()

    # print(f"kw_obs[:3] = {kw_obs[:3]}")

    if kw_obs[:3] == 'A/C':
        despacho = f"{kwargs['kw_despacho']}</p><br><p><strong>Informações adicionais: </strong>{kw_obs[3:]}"
    else:
        despacho = kwargs['kw_despacho']

    email_body = f"""
    <html>
    <body>
        <p style="color:#000066;">| Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
        <br>
        <p>Olá,</p>           
        <p>{despacho}</p>
        <br>
        <p>Como próximo passo, solicite o <strong>relatório de inspeção</strong> ou a <strong>licença de funcionamento</strong> da empresa pelo site da Vigilância Sanitária.</p>      
        <br>
        <p>At.te</p>
        <img src="cid:signature_image" style="width: auto; height: auto;">
        <p style="color:#000066;">| Acesse o <a href="https://sesma.belem.pa.gov.br/vigilancia-sanitaria">site da Vigilância Sanitária</a> para mais informações.</p>
    </body>
    </html>
    """
    
    msg = MIMEMultipart("related")
    msg['Subject'] = f"Aprovação de Projeto Arquitetônico {kwargs['kw_ano']} - SESMA / DEVISA"
    msg["From"] = "devisa.projeto.sesma@gmail.com" ###################################################

    if len(kwargs['kw_email2']) > 2:
        st.toast("**Criando o e-mail, preparando anexo, e definindo destinatários...**")
        to_addresses = [kwargs['kw_email1'], kwargs['kw_email2']]
        msg["To"] = ", ".join(to_addresses)
    else:
        st.toast("**Criando o e-mail, preparando anexo, e definindo destinatário...**")
        msg["To"] = kwargs['kw_email1']

    match st.session_state.auth_user:
        case 'tainadvse':
            image_path = "resources/logo_dvse_taina.png"
            image_name = "logo_dvse_taina.png"
        case 'tancredodvse':
            image_path = "resources/logo_dvse_tancredo.png"
            image_name = "logo_dvse_tancredo.png"
        case 'raysadvse':
            image_path = "resources/logo_dvse_raysa.png"
            image_name = "logo_dvse_raysa.png"
        case 'laurodvse':
            image_path = "resources/logo_secretaria.png"
            image_name = "logo_secretaria.png"
        case 'engenharia':
            image_path = "resources/logo_dvse_taina.png"
            image_name = "logo_dvse_taina.png"
        case _:
            return st.toast(":red[**Não foi possível enviar o e-mail. Usuário não encontrado. Saindo...**]")


    # image_path = "resources/logo_secretaria.png"

    msg.attach(MIMEText(email_body, "html"))

    with open(image_path, 'rb') as img_file:
        image_mime = MIMEImage(img_file.read(), name=image_name) ########################
        image_mime.add_header("Content-ID", "<signature_image>")
        msg.attach(image_mime)

    if kwargs['kw_attachment']:
        zip_file = kwargs['kw_attachment']
        zip_name = kwargs['kw_file_name']   # nome do arquivo (string)
        zip_mime = MIMEBase('application', 'octet-stream')  # Tipo MIME genérico para binários
        zip_mime.set_payload(zip_file)
        encoders.encode_base64(zip_mime)
        # zip_name = kwargs['kw_file_name']
        zip_mime.add_header(
            "Content-Disposition", f"attachment; filename={zip_name}"
        )
        msg.attach(zip_mime)
    else:
        st.toast(":red[**Binário de anexo não encontrado. Saindo...**]")
        return None

    password = st.secrets['apps_psw']['gmail_projeto'] ########################

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login(msg["From"], password)
            if len(kwargs['kw_email2']) > 5:
                s.sendmail(msg["From"], to_addresses, msg.as_string())
                st.session_state.is_email_sended_projeto = True
                return st.toast(f":green[**E-mail despachado a** {kwargs['kw_email1']} e {kwargs['kw_email2']}].")
            else:
                s.sendmail(msg["From"], msg["To"], msg.as_string())
                st.session_state.is_email_sended_projeto = True
                return st.toast(f":green[**E-mail despachado a** {kwargs['kw_email1']}].") 
    except Exception as e:
        print(f"Erro ao enviar o email: {e}")
        return st.toast(f":red[**Erro ao enviar o email:** {e}]")