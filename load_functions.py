import pandas as pd
from io import StringIO, BytesIO
import pymupdf, pytesseract
from PIL import Image
import streamlit as st
import requests, os, re, gspread, json, hashlib, random, string, time
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


def hint_financial_values_revised(min_val_str, max_val_str, comp_str):
    parts = []
    if min_val_str and min_val_str != "R$ 0,00":
        parts.append(f"Valor mínimo: {min_val_str}")
    if max_val_str and max_val_str != "R$ 0,00":
        # Avoid redundant info if min == max and both are present
        if not (min_val_str and min_val_str != "R$ 0,00" and min_val_str == max_val_str):
            parts.append(f"Valor máximo: {max_val_str}")
    if comp_str:
        parts.append(f"Tipo: {comp_str}")

    if not parts:
        return ""
    return "; ".join(parts) + "."

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


def convert_date(date_str):
    """Converts date string (YYYY-MM-DD or DD/MM/YYYY) to DD/MM/YYYY, handles errors."""
    if not date_str:
        return "N/A"
    try:
        # Try parsing YYYY-MM-DD format (common in APIs)
        dt_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return dt_obj.strftime('%d/%m/%Y')
    except ValueError:
        try:
            # Try parsing DD/MM/YYYY format (already correct)
            # Validate it's a real date this way too
            dt_obj = datetime.strptime(date_str, '%d/%m/%Y')
            return date_str # Return original if valid DD/MM/YYYY
        except ValueError:
            # If neither format works, return the original string or N/A
            return date_str # Or return "Data Inválida"

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
    """
    Exibe os dados do CNPJ formatados a partir de um dicionário padronizado,
    refletindo o resultado da comparação CNAE/DAM.
    """
    if not display_data:
        st.warning("Não há dados para exibir.")
        return

    # Fonte da API (adicionado para informação)
    api_source = display_data.get('_api_source', 'Desconhecida')
    st.caption(f"Dados obtidos via: {api_source}")

    # --- Situação Cadastral e Município ---
    situacao = display_data.get('situacao', 'N/A')
    situacao_cor = ":green" if situacao.upper() == "ATIVA" else ":red"
    motivo_situacao = display_data.get('motivo_situacao', '')
    motivo_str = f", {motivo_situacao}" if motivo_situacao and motivo_situacao != 'SEM MOTIVO' else "" # Evita exibir "SEM MOTIVO"
    data_situacao_fmt = convert_date(display_data.get('data_situacao', ''))
    st.write(f"Situação: **{situacao_cor}[{situacao}{motivo_str} ({data_situacao_fmt})]**")

    municipio = display_data.get('municipio', 'N/A')
    uf = display_data.get('uf', 'N/A')
    municipio_cor = ":green" if municipio.upper() == "BELEM" else ":red" # Usar vermelho se não for Belém
    st.write(f"Município: **{municipio_cor}[{municipio} / {uf}]**")

    # --- Situação MEI ---
    is_mei = display_data.get('opcao_mei', False)
    data_opcao_mei_fmt = convert_date(display_data.get('data_opcao_mei', ''))
    data_exclusao_mei_fmt = convert_date(display_data.get('data_exclusao_mei', ''))

    if is_mei:
        # Se MEI ativo, geralmente é bom (verde), a menos que haja problema com CNAE (this_taxas)
        mei_cor = ":orange" if this_taxas and this_taxas not in ['ok', ''] else ":green"
        st.write(f"Situação MEI: {mei_cor}[**Optante ativo desde {data_opcao_mei_fmt}**]")
    elif data_exclusao_mei_fmt != 'N/A':
        # Se excluído, geralmente não é o desejado (vermelho), mas se CNAEs ok, talvez neutro?
        mei_cor = ":red" # Manter vermelho para exclusão
        st.write(f"Situação MEI: {mei_cor}[Excluído do MEI em {data_exclusao_mei_fmt}]")
    else:
         st.write(f"Situação MEI: :grey[Não optante ou informação indisponível]")

    # --- Dados da Empresa ---
    cod_nj = display_data.get('cod_natureza_juridica', 'N/A')
    desc_nj = display_data.get('natureza_juridica', 'N/A')
    st.write(f"Nat. Jurídica: {cod_nj} - {desc_nj}")

    razao_social = display_data.get('razao_social', 'N/A')
    nome_fantasia = display_data.get('nome_fantasia', '')
    fantasia_str = f" ({nome_fantasia})" if nome_fantasia else ""
    st.write(f"Empresa: **{razao_social}**{fantasia_str}")

    # --- Endereço ---
    tipo_log = display_data.get('tipo_logradouro', '')
    logradouro = display_data.get('logradouro', '')
    logradouro_fmt = f"{tipo_log} {logradouro}".strip()
    numero = display_data.get('numero', 'S/N') # Usar S/N se vazio
    complemento = display_data.get('complemento', '')
    bairro = display_data.get('bairro', '')
    cep = display_data.get('cep', '')
    cep_fmt = f"{cep[:2]}.{cep[2:5]}-{cep[5:]}" if cep and len(cep) == 8 else cep # Formata CEP XXXX-XXX

    endereco_parts = [logradouro_fmt, numero]
    if complemento:
        endereco_parts.append(complemento)
    if bairro:
        endereco_parts.append(bairro)
    if cep_fmt:
         endereco_parts.append(f"CEP: {cep_fmt}")
    # Município/UF já exibido

    st.write(f"Endereço: {', '.join(filter(None, endereco_parts))}.") # Junta partes com vírgula

    # --- CNAEs ---
    # Formata a lista de CNAEs para exibição
    if cnaes_finais and isinstance(cnaes_finais, list):
        lista_cnaes_formatada = []
        for cnae in cnaes_finais:
            cnae_str = str(cnae).strip()
            if cnae_str and len(cnae_str) >= 7:
                 # Formato XXXX-X/XX
                 lista_cnaes_formatada.append(f"{cnae_str[:4]}-{cnae_str[4:5]}/{cnae_str[5:7]}")
            elif cnae_str:
                 lista_cnaes_formatada.append(cnae_str) # Adiciona como está se inválido ou curto
        lista_cnaes_str = ", ".join(lista_cnaes_formatada)
    else:
        # Se cnaes_finais for None, [], ou não for lista
        lista_cnaes_str = None # Indica que não há CNAEs formatados

    # Lógica de exibição de CNAEs baseada em 'this_taxas'
    if this_taxas:
        match this_taxas:
            case 'ok':
                st.write(f"CNAEs (DAM): :green[**{lista_cnaes_str if lista_cnaes_str else 'N/A'}** (Todos os CNAEs constam no CNPJ)]")
            case 'parcial':
                st.write(f"CNAEs (DAM): :orange[**{lista_cnaes_str if lista_cnaes_str else 'N/A'}** (Estes CNAEs NÃO constam no CNPJ)]")
            case 'cnae ausente':
                st.write(f"CNAEs (DAM): :red[**{lista_cnaes_str if lista_cnaes_str else 'N/A'}** (NENHUM destes CNAEs consta no CNPJ)]")
            case 'sem cnae':
                 st.write(f"CNAEs (DAM): :red[**CNPJ não possui CNAEs válidos para comparação.**]")
                 # Opcional: Mostrar os CNAEs da DAM que eram esperados
                 # if lista_cnaes_str: st.write(f"   (CNAEs esperados da DAM: {lista_cnaes_str})")
            case _: # Caso padrão/inesperado ou se this_taxas for '' mas não deveria
                 if lista_cnaes_str:
                     st.write(f"CNAEs (CNPJ): :blue[{lista_cnaes_str}] (Comparação com DAM não realizada ou status desconhecido)")
                 else:
                     st.write("CNAEs (CNPJ): :grey[Não possui ou não encontrado]")
    else:
        # Se this_taxas for '' ou None (sem comparação DAM)
         if lista_cnaes_str:
            st.write(f"CNAEs (CNPJ): :blue[{lista_cnaes_str}]")
         else:
            st.write("CNAEs (CNPJ): :grey[Não possui ou não encontrado]")

    # --- Sócios ---
    if socios and isinstance(socios, list):
        # Filtra nomes vazios ou None antes de juntar
        socios_validos = [s for s in socios if s and isinstance(s, str) and s.strip()]
        if socios_validos:
            lista_socios_str = "; ".join(socios_validos)
            st.write(f"Quadro de Sócios: :grey[{lista_socios_str}]")
        else:
             st.write("Quadro de Sócios: :grey[Nomes de sócios não informados]")
    else:
        st.write("Quadro de Sócios: :grey[Não informado ou indisponível]")

    # --- Contato ---
    email = display_data.get('email', '')
    tel1 = display_data.get('telefone1', '')
    tel2 = display_data.get('telefone2', '')
    contatos = []
    if email and isinstance(email, str) and '@' in email: # Validação básica de email
        contatos.append(email)
    # Formata telefones usando a função helper
    tel1_fmt = format_phone_number(tel1)
    if tel1_fmt:
        contatos.append(tel1_fmt)
    tel2_fmt = format_phone_number(tel2)
    # Adiciona tel2 apenas se for diferente de tel1 e válido
    if tel2_fmt and tel2_fmt != tel1_fmt:
        contatos.append(tel2_fmt)

    if contatos:
        st.write(f"Contato: {', '.join(contatos)}")
    else:
        st.write(f"Contato: :grey[Não informado]")

    # --- Campos Adicionais (Exemplo) ---
    data_inicio_fmt = convert_date(display_data.get('data_inicio_atividade', ''))
    if data_inicio_fmt != 'N/A':
        st.write(f"Início da Atividade: {data_inicio_fmt}")

    porte = display_data.get('porte', '')
    if porte:
        st.write(f"Porte: {porte}")

    capital_social = display_data.get('capital_social')
    if capital_social is not None:
        try:
             # Formata como moeda brasileira
             capital_fmt = f"R$ {float(capital_social):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
             st.write(f"Capital Social: {capital_fmt}")
        except (ValueError, TypeError):
             st.write(f"Capital Social: {capital_social}") # Mostra como string se não for número

    # Atualiza o estado para indicar que o diálogo foi fechado (se aplicável)
    # Mantenha esta linha se ela for necessária para o controle da UI do seu app
    if "dialog_open" in st.session_state:
        st.session_state["dialog_open"] = False


# Helper function to safely clean CNAE codes
def _clean_cnae(code):
    if code is None:
        return ''
    # Remove non-digits and convert to string
    return re.sub(r'\D', '', str(code))

# Helper function to safely format phone numbers
def _format_phone(ddd, num):
    ddd_str = str(ddd).strip() if ddd else ''
    num_str = str(num).strip() if num else ''
    if ddd_str and num_str:
        return f"({ddd_str}) {num_str}"
    elif num_str: # Handle cases where DDD might be embedded or missing
        return num_str
    return ''

def process_cnpj_data(api_data: dict, api_source: str, yy: str, lista_dam: str):
    """
    Processa dados da API (BrasilAPI, ReceitaWS, Publica CNPJ.ws, CNPJá)
    e os padroniza para exibição e processamento posterior.
    """
    if not api_data:
        st.toast(":warning: Nenhum dado de API recebido para processar.")
        print("Erro: process_cnpj_data chamado sem api_data.")
        return # Cannot proceed without data

    display_data = {'_api_source': api_source} # Store the source for reference
    socios = []
    cnaes_secundarios_cod = []
    cnae_principal_cod = None

    print(f"--- Processando dados da fonte: {api_source} ---") # Debug

    try:
        # ============================================
        # Mapeamento Específico por Fonte de API
        # ============================================
        if api_source == 'BrasilAPI':
            display_data['situacao'] = api_data.get('descricao_situacao_cadastral')
            display_data['motivo_situacao'] = api_data.get('descricao_motivo_situacao_cadastral')
            display_data['data_situacao'] = api_data.get('data_situacao_cadastral')
            display_data['municipio'] = api_data.get('municipio')
            display_data['uf'] = api_data.get('uf')
            display_data['opcao_mei'] = api_data.get('opcao_pelo_mei', False)
            display_data['data_opcao_mei'] = api_data.get('data_opcao_pelo_mei')
            display_data['data_exclusao_mei'] = api_data.get('data_exclusao_do_mei')
            display_data['cod_natureza_juridica'] = str(api_data.get('codigo_natureza_juridica', ''))
            display_data['natureza_juridica'] = api_data.get('natureza_juridica')
            display_data['razao_social'] = api_data.get('razao_social')
            display_data['nome_fantasia'] = api_data.get('nome_fantasia')
            display_data['tipo_logradouro'] = api_data.get('descricao_tipo_de_logradouro')
            display_data['logradouro'] = api_data.get('logradouro')
            display_data['numero'] = api_data.get('numero')
            display_data['complemento'] = api_data.get('complemento')
            display_data['bairro'] = api_data.get('bairro')
            display_data['cep'] = _clean_cnae(api_data.get('cep')) # Limpa CEP
            display_data['email'] = api_data.get('email')
            # BrasilAPI retorna DDD e telefone juntos em ddd_telefone_1 / ddd_telefone_2
            display_data['telefone1'] = api_data.get('ddd_telefone_1') # Já vem formatado
            display_data['telefone2'] = api_data.get('ddd_telefone_2') # Já vem formatado
            display_data['data_inicio_atividade'] = api_data.get('data_inicio_atividade')
            display_data['porte'] = api_data.get('porte')
            display_data['capital_social'] = api_data.get('capital_social')

            cnae_principal_cod = _clean_cnae(api_data.get('cnae_fiscal'))
            if "cnaes_secundarios" in api_data and isinstance(api_data["cnaes_secundarios"], list):
                for cnae in api_data["cnaes_secundarios"]:
                    cnaes_secundarios_cod.append(_clean_cnae(cnae.get("codigo")))

            if "qsa" in api_data and isinstance(api_data["qsa"], list):
                for socio in api_data["qsa"]:
                    socios.append(socio.get("nome_socio"))

        elif api_source == 'ReceitaWS':
            display_data['situacao'] = api_data.get('situacao')
            display_data['motivo_situacao'] = api_data.get('motivo_situacao')
            display_data['data_situacao'] = api_data.get('data_situacao')
            display_data['municipio'] = api_data.get('municipio')
            display_data['uf'] = api_data.get('uf')
            # MEI/Simples em objetos aninhados
            mei_info = api_data.get('simei', {}) if api_data.get('simei') else {}
            display_data['opcao_mei'] = mei_info.get('optante', False)
            display_data['data_opcao_mei'] = mei_info.get('data_opcao')
            display_data['data_exclusao_mei'] = mei_info.get('data_exclusao')
            # Parse natureza jurídica "XXX-X - Texto"
            nj_str = api_data.get('natureza_juridica', '')
            display_data['cod_natureza_juridica'] = nj_str.split(' - ')[0] if ' - ' in nj_str else ''
            display_data['natureza_juridica'] = nj_str.split(' - ')[1] if ' - ' in nj_str else nj_str
            display_data['razao_social'] = api_data.get('nome') # Chave 'nome'
            display_data['nome_fantasia'] = api_data.get('fantasia') # Chave 'fantasia'
            display_data['tipo_logradouro'] = '' # Não fornecido separadamente
            display_data['logradouro'] = api_data.get('logradouro')
            display_data['numero'] = api_data.get('numero')
            display_data['complemento'] = api_data.get('complemento')
            display_data['bairro'] = api_data.get('bairro')
            display_data['cep'] = _clean_cnae(api_data.get('cep')) # Limpa CEP
            display_data['email'] = api_data.get('email')
            display_data['telefone1'] = api_data.get('telefone') # Campo único 'telefone'
            display_data['telefone2'] = ''
            display_data['data_inicio_atividade'] = api_data.get('abertura') # Chave 'abertura'
            display_data['porte'] = api_data.get('porte')
            display_data['capital_social'] = api_data.get('capital_social')

            if "atividade_principal" in api_data and isinstance(api_data["atividade_principal"], list) and api_data["atividade_principal"]:
                cnae_principal_cod = _clean_cnae(api_data["atividade_principal"][0].get("code"))
            if "atividades_secundarias" in api_data and isinstance(api_data["atividades_secundarias"], list):
                for cnae in api_data["atividades_secundarias"]:
                     cnaes_secundarios_cod.append(_clean_cnae(cnae.get("code")))

            if "qsa" in api_data and isinstance(api_data["qsa"], list):
                for socio in api_data["qsa"]:
                    socios.append(socio.get("nome"))

        elif api_source == 'Publica CNPJ.ws':
            estab = api_data.get('estabelecimento', {}) # Dados principais estão no estabelecimento
            if not estab:
                 print(f"WARN: Estrutura inesperada da {api_source}, 'estabelecimento' não encontrado.")
                 # Tentar pegar dados do nível raiz se possível
                 display_data['razao_social'] = api_data.get('razao_social')
                 nj = api_data.get('natureza_juridica', {})
                 display_data['cod_natureza_juridica'] = str(nj.get('id', ''))
                 display_data['natureza_juridica'] = nj.get('descricao')
            else:
                display_data['situacao'] = estab.get('situacao_cadastral')
                display_data['motivo_situacao'] = estab.get('motivo_situacao_cadastral', {}).get('descricao') if estab.get('motivo_situacao_cadastral') else '' # Motivo é objeto
                display_data['data_situacao'] = estab.get('data_situacao_cadastral')
                display_data['municipio'] = estab.get('cidade', {}).get('nome')
                display_data['uf'] = estab.get('estado', {}).get('sigla')
                simples_info = api_data.get('simples', {}) # Info de simples/mei está no nível raiz
                display_data['opcao_mei'] = simples_info.get('mei') == 'Sim'
                display_data['data_opcao_mei'] = simples_info.get('data_opcao_mei')
                display_data['data_exclusao_mei'] = simples_info.get('data_exclusao_mei')
                nj = api_data.get('natureza_juridica', {}) # Nível raiz
                display_data['cod_natureza_juridica'] = str(nj.get('id', ''))
                display_data['natureza_juridica'] = nj.get('descricao')
                display_data['razao_social'] = api_data.get('razao_social') # Nível raiz
                display_data['nome_fantasia'] = estab.get('nome_fantasia')
                display_data['tipo_logradouro'] = estab.get('tipo_logradouro')
                display_data['logradouro'] = estab.get('logradouro')
                display_data['numero'] = estab.get('numero')
                display_data['complemento'] = estab.get('complemento')
                display_data['bairro'] = estab.get('bairro')
                display_data['cep'] = _clean_cnae(estab.get('cep')) # Limpa CEP
                display_data['email'] = estab.get('email')
                display_data['telefone1'] = _format_phone(estab.get('ddd1'), estab.get('telefone1'))
                display_data['telefone2'] = _format_phone(estab.get('ddd2'), estab.get('telefone2'))
                display_data['data_inicio_atividade'] = estab.get('data_inicio_atividade')
                display_data['porte'] = api_data.get('porte', {}).get('descricao') # Nível raiz
                display_data['capital_social'] = api_data.get('capital_social') # Nível raiz

                if "atividade_principal" in estab and estab["atividade_principal"]:
                    cnae_principal_cod = _clean_cnae(estab["atividade_principal"].get("id"))
                if "atividades_secundarias" in estab and isinstance(estab["atividades_secundarias"], list):
                    for cnae in estab["atividades_secundarias"]:
                        cnaes_secundarios_cod.append(_clean_cnae(cnae.get("id")))

            # Sócios estão no nível raiz
            if "socios" in api_data and isinstance(api_data["socios"], list):
                for socio in api_data["socios"]:
                    socios.append(socio.get("nome"))

        elif api_source == 'CNPJá': # Nome da fonte 'CNPJá' (verifique se é este no get_cnpj)
            company_info = api_data.get('company', {})
            address_info = api_data.get('address', {})

            display_data['situacao'] = api_data.get('status', {}).get('text')
            display_data['motivo_situacao'] = None # Não parece ter motivo explícito
            display_data['data_situacao'] = api_data.get('statusDate')
            display_data['municipio'] = address_info.get('city')
            display_data['uf'] = address_info.get('state')
            mei_info = company_info.get('simei', {})
            display_data['opcao_mei'] = mei_info.get('optant', False)
            display_data['data_opcao_mei'] = mei_info.get('since') # Usa 'since'
            display_data['data_exclusao_mei'] = None # Não explícito para exclusão MEI
            nj = company_info.get('nature', {})
            display_data['cod_natureza_juridica'] = str(nj.get('id', ''))
            display_data['natureza_juridica'] = nj.get('text')
            display_data['razao_social'] = company_info.get('name')
            display_data['nome_fantasia'] = api_data.get('alias') # Nível raiz
            # Tentar extrair tipo do logradouro (pode ser difícil/impreciso)
            street_full = address_info.get('street', '')
            tipo_logr, logr = street_full.split(' ', 1) if ' ' in street_full else ('', street_full)
            # Heurística simples (pode precisar de melhorias)
            if tipo_logr.upper() in ['RUA', 'AV', 'AVENIDA', 'TRAVESSA', 'ALAMEDA', 'ESTRADA', 'PRACA', 'RODOVIA']:
                 display_data['tipo_logradouro'] = tipo_logr
                 display_data['logradouro'] = logr
            else:
                 display_data['tipo_logradouro'] = ''
                 display_data['logradouro'] = street_full

            display_data['numero'] = address_info.get('number')
            display_data['complemento'] = address_info.get('details') # 'details' como complemento
            display_data['bairro'] = address_info.get('district')
            display_data['cep'] = _clean_cnae(address_info.get('zip')) # Limpa CEP
            emails_list = api_data.get('emails', [])
            display_data['email'] = emails_list[0].get('address') if emails_list else None
            phones_list = api_data.get('phones', [])
            phone1_info = phones_list[0] if phones_list else {}
            display_data['telefone1'] = _format_phone(phone1_info.get('area'), phone1_info.get('number'))
            phone2_info = phones_list[1] if len(phones_list) > 1 else {}
            display_data['telefone2'] = _format_phone(phone2_info.get('area'), phone2_info.get('number'))
            display_data['data_inicio_atividade'] = api_data.get('founded') # Chave 'founded'
            display_data['porte'] = company_info.get('size', {}).get('text')
            display_data['capital_social'] = company_info.get('equity')

            if "mainActivity" in api_data and api_data["mainActivity"]:
                 cnae_principal_cod = _clean_cnae(api_data["mainActivity"].get("id"))
            if "sideActivities" in api_data and isinstance(api_data["sideActivities"], list):
                for cnae in api_data["sideActivities"]:
                    cnaes_secundarios_cod.append(_clean_cnae(cnae.get("id")))

            if "members" in company_info and isinstance(company_info["members"], list):
                 for member in company_info["members"]:
                     person_info = member.get('person', {})
                     socios.append(person_info.get("name"))

        else:
            st.toast(f":warning: Fonte de API desconhecida encontrada: '{api_source}'")
            print(f"Erro: Fonte de API não mapeada: {api_source}")
            # Tentar um mapeamento genérico ou apenas retornar?
            # Por segurança, não faremos nada e a lógica abaixo terá dados vazios.
            pass

        # ============================================
        # Lógica Comum após padronização
        # ============================================

        # Junta todos os CNAEs (apenas códigos numéricos limpos)
        lista_cnaes_numericos = []
        if cnae_principal_cod:
            lista_cnaes_numericos.append(cnae_principal_cod)
        lista_cnaes_numericos.extend(cnaes_secundarios_cod)
        lista_cnaes_numericos = [c for c in lista_cnaes_numericos if c] # Remove vazios/nulos

        # Aplica o filtro intersetorial (certifique-se que a função exista)
        try:
             cnaes_decreto = cnae_intersectorial(lista_cnaes_numericos)
            #  print(f"DANIEL: lista_cnaes_numericos: {lista_cnaes_numericos}")
            #  print(f"DANIEL: cnaes_decreto: {cnaes_decreto}")
        except NameError:
             print("WARN: Função 'cnae_intersectorial' não definida. Usando CNAEs originais.")
             cnaes_decreto = lista_cnaes_numericos


        # print(f"DEBUG: CNAEs do CNPJ (limpos): {lista_cnaes_numericos}")
        # print(f"DEBUG: CNAEs após intersectorial: {cnaes_decreto}") # Debug

        # Lógica de comparação com lista_dam
        this_taxas = ''
        cnaes_finais = cnaes_decreto # Por padrão, exibe os CNAEs do decreto/CNPJ

        if lista_dam and isinstance(lista_dam, str) and len(lista_dam.strip()) > 0:
            lista_taxas = [_clean_cnae(cnae) for cnae in lista_dam.split(",")]
            lista_taxas = [c for c in lista_taxas if c] # Remove vazios após limpeza

            # print(f"DEBUG: Lista DAM (limpa): {lista_taxas}") # Debug

            if not lista_taxas:
                print("DEBUG: Lista DAM vazia ou inválida após limpeza.")
                this_taxas = '' # Nenhuma comparação a fazer
                cnaes_finais = cnaes_decreto
            elif not cnaes_decreto: # Se o CNPJ não tiver CNAEs válidos
                 this_taxas = 'sem cnae'
                 cnaes_finais = lista_taxas # Mostra os que eram esperados
            else:
                intersecao = [cnae for cnae in lista_taxas if cnae in cnaes_decreto]
                nao_contidos = [cnae for cnae in lista_taxas if cnae not in cnaes_decreto]

                # print(f"DEBUG: Interseção: {intersecao}") # Debug
                # print(f"DEBUG: Não contidos (DAM \\ CNPJ): {nao_contidos}") # Debug

                if not intersecao: # Nenhum CNAE da lista_dam está no CNPJ
                    this_taxas = 'cnae ausente'
                    cnaes_finais = nao_contidos # Exibe os CNAEs da lista_dam que não foram encontrados
                elif nao_contidos: # Alguns da lista_dam estão, outros não
                    this_taxas = 'parcial' # Ou 'divergente', 'incompleto' ?
                    cnaes_finais = nao_contidos # Exibe os que faltaram
                    # Ou exibe os que deram match? cnaes_finais = intersecao
                    # Ou exibe ambos? cnaes_finais = {'match': intersecao, 'faltantes': nao_contidos} -> Ajustar show_dadosCnpj
                else: # Todos da lista_dam estão no CNPJ
                    this_taxas = 'ok'
                    cnaes_finais = intersecao # Exibe os CNAEs que deram match
        else: # Se não houver lista_dam para comparar
            cnaes_finais = cnaes_decreto
            this_taxas = '' # Ou talvez 'nao_comparado'?

        # print(f"DEBUG: Final - this_taxas: {this_taxas}, cnaes_finais: {cnaes_finais}") # Debug

        # Chama a função de exibição com os dados padronizados
        try:
            # Certifique-se que show_dadosCnpj exista e aceite estes parâmetros
            show_dadosCnpj(display_data, cnaes_finais, socios, this_taxas)
        except NameError:
            print("ERRO: Função 'show_dadosCnpj' não definida. Não é possível exibir os dados.")
            st.error("Erro interno: Função de exibição não encontrada.")


        # Lógica para preencher campos de digitação (ajustada para dicionário)
        if display_data and yy == 'cnpj_digitacao_lf':
             # Verifica condições (Ex: ATIVA e CEP de Belém '66')
             situacao_ok = display_data.get('situacao', '').upper() == "ATIVA"
             # Garante que CEP seja string antes de startswith
             cep_str = str(display_data.get('cep', ''))
             cep_ok = cep_str.startswith("66")

             if situacao_ok and cep_ok:
                 st.session_state.fi_logradouro = f"{display_data.get('tipo_logradouro', '')} {display_data.get('logradouro', '')}".strip()
                 st.session_state.fi_numero = display_data.get('numero', '')
                 st.session_state.fi_razao_social = display_data.get('razao_social', '')
                 st.session_state.fi_bairro = display_data.get('bairro', '')
                 st.session_state.fi_cep = display_data.get('cep', '')
                 st.session_state.fi_complemento = display_data.get('complemento', '')
                 print("DEBUG: Campos do formulário preenchidos.")
             else:
                 # Limpa os campos se não atender aos critérios
                 st.session_state.fi_logradouro = ""
                 st.session_state.fi_razao_social = ""
                 st.session_state.fi_complemento = ""
                 st.session_state.fi_numero = ""
                 st.session_state.fi_bairro = ""
                 st.session_state.fi_cep = ""
                 print(f"DEBUG: Campos do formulário NÃO preenchidos (Situação: {situacao_ok}, CEP: {cep_ok})")


    except Exception as e:
        st.error(f"Erro inesperado ao processar dados da API {api_source}: {e}")
        print(f"ERRO CRÍTICO em process_cnpj_data ({api_source}): {e}")
        import traceback
        traceback.print_exc() # Log completo do erro para debug



# --- FUNÇÃO NÚCLEO (INTERNA) ---

def _fetch_cnpj_data(t_cnpj: str):
    """
    Função interna que itera sobre as APIs para buscar dados de um CNPJ.

    Args:
        t_cnpj (str): CNPJ limpo, contendo apenas dígitos.

    Returns:
        tuple: Uma tupla contendo (dados_json, nome_da_api) em caso de sucesso,
               ou (None, None, ultima_mensagem_erro) em caso de falha.
    """
    # Ordem de preferência definida pelo usuário
    endpoints_config = [
        {"name": "ReceitaWS", "url": f"https://receitaws.com.br/v1/cnpj/{t_cnpj}"},
        {"name": "Publica CNPJ.ws", "url": f"https://publica.cnpj.ws/cnpj/{t_cnpj}"},
        {"name": "BrasilAPI", "url": f"https://brasilapi.com.br/api/cnpj/v1/{t_cnpj}"},
        {"name": "CNPJá", "url": f"https://open.cnpja.com/office/{t_cnpj}"},
    ]
    
    headers = {'User-Agent': 'MeuAppStreamlit/1.0'}
    timeout = 3  # Timeout reduzido para 3 segundos, mais adequado para UI.

    last_error_message = "Nenhuma API respondeu com sucesso."

    for config in endpoints_config:
        name, url = config["name"], config["url"]
        print(f"Tentando API: {name}...")

        try:
            response = requests.get(url, headers=headers, timeout=timeout)

            if response.status_code == 200:
                try:
                    data = response.json()
                    # Verificação de mensagens de erro dentro de uma resposta 200 OK
                    if isinstance(data, dict):
                        if data.get("status") == "ERROR":
                            last_error_message = f"{name}: {data.get('message', 'Erro interno')}"
                            continue # Tenta a próxima API
                        if "não encontrado" in data.get("message", "").lower():
                            last_error_message = f"{name}: CNPJ não encontrado."
                            continue # Tenta a próxima API

                    print(f"Sucesso com {name}!")
                    return data, name, None  # Sucesso! Retorna dados, fonte e nenhum erro.

                except requests.exceptions.JSONDecodeError:
                    last_error_message = f"{name} retornou uma resposta inválida."
            
            # Tratamento de outros status HTTP
            elif response.status_code == 404:
                last_error_message = f"{name}: CNPJ não encontrado (404)."
            elif response.status_code == 429:
                last_error_message = f"{name}: Limite de requisições atingido (429)."
                time.sleep(0.5) # Pequena pausa antes de tentar a próxima
            else:
                last_error_message = f"{name} falhou (Status {response.status_code})."

        except requests.exceptions.Timeout:
            last_error_message = f"{name} não respondeu a tempo ({timeout}s)."
        except requests.exceptions.RequestException:
            last_error_message = f"Erro de conexão com {name}."
        
        print(f"Falha: {last_error_message}")

    # Se o loop terminar, nenhuma API funcionou
    print(f"Consulta final falhou para o CNPJ {t_cnpj}. Último erro: {last_error_message}")
    return None, None, last_error_message


# --- FUNÇÕES PÚBLICAS REATORADAS ---

def get_cnpj(cnpj: str, yy: str, lista_dam: str):
    """
    Busca e processa dados de um CNPJ, atualizando o formulário do Streamlit.
    Retorna o primeiro resultado bem-sucedido das APIs configuradas.

    Args:
        cnpj (str): O CNPJ a ser consultado (com ou sem máscara).
        yy (str): Identificador do contexto/formulário.
        lista_dam (str): Parâmetro adicional para processamento.

    Returns:
        bool: True se a consulta e o processamento foram bem-sucedidos, False caso contrário.
    """
    try:
        t_cnpj = re.sub(r"\D", "", cnpj)
        if not t_cnpj or len(t_cnpj) != 14:
            st.toast("⚠️ CNPJ inválido ou vazio.")
            return False
    except Exception:
        st.toast("❌ Erro ao formatar o CNPJ.")
        return False

    # Limpa os campos do formulário antes da nova consulta
    if yy == 'cnpj_digitacao_lf':
        for key in ['fi_razao_social', 'fi_logradouro', 'fi_numero', 'fi_complemento', 'fi_bairro', 'fi_cep']:
            if hasattr(st.session_state, key):
                st.session_state[key] = ""
    
    with st.spinner("Consultando CNPJ..."):
        api_data, api_source, error_message = _fetch_cnpj_data(t_cnpj)

    if api_data and api_source:
        st.toast(f"✅ Dados encontrados via {api_source}.")
        try:
            # Chama a função externa para preencher o formulário
            process_cnpj_data(api_data, api_source, yy, lista_dam)
            return True
        except Exception as e:
            st.toast(f"❌ Erro ao processar dados de {api_source}.")
            print(f"Erro em process_cnpj_data: {e}")
            return False
    
    # Se falhou, exibe a mensagem de erro final.
    st.toast(f"❌ Falha na consulta. {error_message}")
    return False


def get_cnpj_raw(cnpj: str):
    """
    Busca e retorna os dados brutos (JSON) de um CNPJ.
    Retorna o primeiro resultado bem-sucedido das APIs configuradas.

    Args:
        cnpj (str): O CNPJ a ser consultado (com ou sem máscara).

    Returns:
        dict or bool: Um dicionário com os dados brutos ou False em caso de falha.
    """
    try:
        t_cnpj = re.sub(r"\D", "", cnpj)
        if not t_cnpj or len(t_cnpj) != 14:
            st.toast("⚠️ CNPJ inválido ou vazio.")
            return False
    except Exception:
        st.toast("❌ Erro ao formatar o CNPJ.")
        return False

    with st.spinner("Consultando dados brutos do CNPJ..."):
        api_data, api_source, error_message = _fetch_cnpj_data(t_cnpj)

    if api_data:
        st.toast(f"✅ Dados brutos encontrados via {api_source}.")
        return api_data
    
    # Se falhou, exibe a mensagem de erro final.
    st.toast(f"❌ Falha na consulta. {error_message}")
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


# @st.dialog("Detalhes do Processo", width="large")
def show_dadosProcesso(df):
    df_conv = df.to_json(orient="records", indent=2)
    return st.json(df_conv)


@st.dialog("Ocorrências", width="large")
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
                    return st.json(result_json)
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