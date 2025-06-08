import os
import time
import platform
import streamlit as st
import tempfile

# Selenium 4 e webdriver-manager imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
# Removido o import de ChromeType, pois usaremos o Chrome padrão

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime, timedelta
import base64
import traceback
import zipfile
# obter a razão social pela consulta CNPJ
from load_functions import get_cnpj_raw, codigo_alfabetico, limpando_cpf_cnpj, get_client_ip

# --- Funções Utilitárias (mantidas) ---
def data_hoje():
    from datetime import datetime
    return datetime.now().strftime("%d/%m/%Y")

def data_vencimento():
    from datetime import datetime, timedelta
    data_futura = datetime.now() + timedelta(days=30)
    return data_futura.strftime("%d/%m/%Y")

def mascara_cnpj_cpf(documento: str) -> str:
    documento = ''.join(filter(str.isdigit, documento))
    if len(documento) == 11:
        return f"{documento[:3]}.{documento[3:6]}.{documento[6:9]}-{documento[9:]}"
    elif len(documento) == 14:
        return f"{documento[:2]}.{documento[2:5]}.{documento[5:8]}/{documento[8:12]}-{documento[12:]}"
    else:
        raise ValueError("O documento deve conter 11 dígitos (CPF) ou 14 dígitos (CNPJ).")


# --- Lógica do Webdriver (Corrigida para ser Direta) ---

SISTEMA = platform.system()
WEBDRIVER_DIR = os.path.join("webdriver", SISTEMA)
os.makedirs(WEBDRIVER_DIR, exist_ok=True)
DEFAULT_WAIT_TIME = 7


def get_driver():
    """
    Inicializa o WebDriver do Google Chrome (Selenium 4) de forma direta,
    forçando o uso da versão 136 do driver sem detectar o browser instalado.
    """
    if "driver" not in st.session_state:
        st.toast("🤖 Inicializando o WebDriver (versão fixa 136)...")
        
        # Define o diretório de cache para o webdriver-manager
        os.environ['WDM_LOCAL'] = WEBDRIVER_DIR
        
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        # options.add_argument("--headless")
        
        temp_dir = tempfile.gettempdir()
        prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": temp_dir}
        options.add_experimental_option("prefs", prefs)

        try:
            # --- ABORDAGEM DIRETA E ROBUSTA ---
            # Define explicitamente a versão do driver a ser usada.
            # Isso evita a detecção do browser, que estava falhando.
            TARGET_DRIVER_VERSION = "136"
            
            st.info(f"Forçando o uso do chromedriver versão **{TARGET_DRIVER_VERSION}**.")

            # O webdriver-manager irá verificar se o driver v136 já existe em WDM_LOCAL.
            # Se existir, usa. Se não, baixa.
            service = Service(
                ChromeDriverManager(
                    driver_version=TARGET_DRIVER_VERSION
                ).install()
            )

            st.session_state.driver = webdriver.Chrome(service=service, options=options)
            st.toast("✅ Driver inicializado com sucesso!")

        except Exception as e:
            st.error("❌ Falha ao inicializar o WebDriver.")
            st.exception(e)
            if "driver" in st.session_state:
                del st.session_state.driver
            return None
    
    return st.session_state.driver


def selenium_clear_driver():
    """
    Fecha o driver do Selenium e o remove da sessão do Streamlit.
    """
    if "driver" in st.session_state:
        try:
            st.session_state.driver.quit()
        except Exception as e:
            print(f"Erro ao fechar o driver (pode já estar fechado): {e}")
        finally:
            del st.session_state.driver
            st.toast(" Driver foi resetado.")