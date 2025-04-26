import os, time
import tempfile
import streamlit as st
import platform
from selenium import webdriver

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime, timedelta
import base64
import traceback
import zipfile
# obter a razão social pela consulta CNPJ
from load_functions import get_cnpj_raw, codigo_alfabetico, limpando_cpf_cnpj, get_client_ip

os.environ["NO_PROXY"] = "localhost,127.0.0.1"

DEFAULT_WAIT_TIME = 15 # Tempo de espera padrão (em segundos)

# Detecta o sistema operacional
sistema = platform.system()
# Cria um diretório específico para cada sistema dentro da pasta "webdriver"
WEBDRIVER_DIR = os.path.join("webdriver", sistema)
os.makedirs(WEBDRIVER_DIR, exist_ok=True, )

def data_hoje():
     # Obter a data atual
    data_atual = datetime.now()
    return data_atual.strftime("%d/%m/%Y")

def data_vencimento():
    # Obter a data atual
    data_atual = datetime.now()

    # Adicionar 30 dias à data atual
    data_futura = data_atual + timedelta(days=30)
    return data_futura.strftime("%d/%m/%Y")

def mascara_cnpj_cpf(documento: str) -> str:
     # Remover qualquer caractere que não seja dígito
    documento = ''.join(filter(str.isdigit, documento))
    if len(documento) == 11:  # CPF
        return f"{documento[:3]}.{documento[3:6]}.{documento[6:9]}-{documento[9:]}"
    elif len(documento) == 14:  # CNPJ
        return f"{documento[:2]}.{documento[2:5]}.{documento[5:8]}/{documento[8:12]}-{documento[12:]}"
    else:
        raise ValueError("O documento deve conter 11 dígitos (CPF) ou 14 dígitos (CNPJ).")


def criar_extensao_proxy(proxy_host, proxy_port, proxy_user, proxy_pass):
    # Caminho completo para a extensão
    plugin_dir = "webdriver/Windows/extensions"
    plugin_file = os.path.join(plugin_dir, "proxy_extension.zip")
    
    # Verifica se a extensão já existe
    if os.path.exists(plugin_file):
        print(f"Usando extensão existente em: {plugin_file}")
        return plugin_file

    # Cria o diretório se não existir
    os.makedirs(plugin_dir, exist_ok=True)

    manifest_json = """
    {
        "name": "Chrome Proxy",
        "description": "Use proxy with auth",
        "version": "1.0.0",
        "manifest_version": 3,
        "permissions": [
            "proxy",
            "storage",
            "scripting",
            "tabs",
            "unlimitedStorage",
            "webRequest",
            "webRequestAuthProvider"
        ],
        "host_permissions": [
            "<all_urls>"
        ],
        "background": {
            "service_worker": "background.js"
        },
        "action": {
            "default_title": "Proxy Extension"
        }
    }
    """

    background_js = f"""
    chrome.runtime.onInstalled.addListener(() => {{
        const config = {{
            mode: "fixed_servers",
            rules: {{
                singleProxy: {{
                    scheme: "http",
                    host: "{proxy_host}",
                    port: parseInt({proxy_port})
                }},
                bypassList: ["localhost"]
            }}
        }};
        chrome.proxy.settings.set(
            {{value: config, scope: "regular"}},
            () => {{}}
        );
    }});

    chrome.webRequest.onAuthRequired.addListener(
        function(details) {{
            return {{
                authCredentials: {{
                    username: "{proxy_user}",
                    password: "{proxy_pass}"
                }}
            }};
        }},
        {{urls: ["<all_urls>"]}},
        ["blocking"]
    );
    """

    # Cria o arquivo ZIP da extensão
    with zipfile.ZipFile(plugin_file, "w") as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)
    
    print(f"Nova extensão criada em: {plugin_file}")
    return plugin_file

def get_driver():
    if "driver" not in st.session_state:
        # Obtém a versão do Chrome instalada. A função get_chrome_version() retorna algo como "113.0.5672.63".
        chrome_version_full = chromedriver_autoinstaller.get_chrome_version()
        
        if chrome_version_full is None:
            raise EnvironmentError("Não foi possível detectar a versão do Google Chrome instalada.")
        
        # Extrai a versão principal (por exemplo, "113").
        chrome_version = chrome_version_full.split('.')[0]

        # Para ambientes Linux (Streamlit Community Cloud)
        if sistema == "Linux":
            chromedriver_path = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        else:        
            # Instala automaticamente o ChromeDriver compatível e o salva no diretório do sistema
            chromedriver_path = chromedriver_autoinstaller.install(path=WEBDRIVER_DIR)
        
        options = Options()
        options.add_argument("--disable-gpu")
        # options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        try:
            if sistema == "Windows":
                # my_ip12 = get_client_ip()  
                my_ip = st.session_state.sessao_ip
                # st.toast(f"st.session_state.sessao_ip: {st.session_state.sessao_ip}")
                if '200.151' in str(my_ip):
                    # st.toast("Entrou no meu ip")
                    proxy_host = "10.26.0.1"
                    proxy_port = "3128"
                    proxy_user = "rede"
                    proxy_pass = "suporte@@nati"
                    options.add_argument(f"--proxy-server={proxy_host}:{proxy_port}")
                    plugin_file = criar_extensao_proxy(proxy_host, proxy_port, proxy_user, proxy_pass)
                    options.add_extension(plugin_file)
                    options.add_argument("--proxy-bypass-list=127.0.0.1,localhost")
                    options.add_argument("--disable-safe-browsing")
                    # st.toast("gera a extensão")

        except Exception as e:
            st.toast(f"Erro em get_driver: {e}")
            pass
        
        # Configuração para forçar o download de PDFs (desabilita o visualizador interno)
        temp_dir = tempfile.gettempdir()
        prefs = {
            "plugins.always_open_pdf_externally": True,
            "download.default_directory": temp_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
        }
        options.add_experimental_option("prefs", prefs)

        # Define a localização do binário do Chrome conforme o sistema operacional
        if sistema == "Windows":
            st.toast("binário chrome")
            options.binary_location = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        elif sistema == "Linux":
            options.binary_location = "/usr/bin/chromium"
            options.add_argument("--headless")
            options.add_argument("--remote-debugging-port=9222")  # Opcional, mas pode ajudar
            options.page_load_strategy = 'eager'
        elif sistema == "Darwin":  # macOS
            options.add_argument("--headless")
            options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        
        # Inicializa o WebDriver e armazena em session_state
        st.session_state.driver = webdriver.Chrome(
            service=Service(chromedriver_path),
            options=options,
        )
        st.toast("Driver inicializado com sucesso!")
    
    # st.toast(f"Driver vai ser retornado: {st.session_state.driver}")
    return st.session_state.driver


def selenium_clear_driver():
    # Fechar o driver ao terminar (opcional, dependendo de quando você deseja fechar)
    if "driver" in st.session_state:
        st.session_state.driver.quit()
        del st.session_state.driver
        st.toast("*Driver resetado.*")


#
#
# AUTOMAÇÃO PARA GDOC...
#
#