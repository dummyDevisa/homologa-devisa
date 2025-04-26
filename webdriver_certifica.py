import requests, shutil, uuid
from webdriver import *
from load_functions import get_client_ip


def selenium_login_portal(matricula, senha):
    url_login = "https://sistemas.belem.pa.gov.br/portaldoservidor/#/login"
    # st.toast("passou url_login")
    
    driver = get_driver()
    # st.toast("passou get_driver")
    # try:
    #     response = requests.get(url_login, timeout=10)
    #     st.write(f"Status Code: {response.status_code}")
    #     st.write("Conteúdo da resposta:", response.text[:500])  # Mostra os primeiros 500 caracteres
    # except requests.exceptions.RequestException as e:
    #     st.write("Erro ao tentar acessar:", e)

    driver.get(url_login)
    # st.toast("passou driver.get driver.get driver.get")
    st.toast("Inicializando o webdriver...")  
    # botão de login
    btn_logon = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/app-root/app-login/cinbesa-form-login/div/div[2]/form/div[3]/cinbesa-botao/button'))
        )
        
    input_matricula = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-login/cinbesa-form-login/div/div[2]/form/div[1]/cinbesa-input-mask/div/input'))
    )
    # input_matricula.click()
    input_matricula.send_keys(matricula)

    input_senha = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-login/cinbesa-form-login/div/div[2]/form/div[2]/cinbesa-input/div/input'))
    )
    input_senha.send_keys(senha)

    # clicar no botão carregado no início
    btn_logon.click()
    

    # confirm_login = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
    #     EC.presence_of_element_located((By.XPATH, '/html/body/app-root/cinbesa-alerta/div/div'))
    # )


def selenium_certifica_doc(**kwargs):
    st.toast("Iniciando o processo de certificação. Aguarde...")
    try:
        # logar no portal
        selenium_login_portal(kwargs['kw_matricula'], kwargs['kw_senha'])

        url_certificaDoc = 'https://sistemas.belem.pa.gov.br/portaldoservidor/#/autenticado/certifica/certificaDoc'
        
        driver = get_driver()
        
        driver.execute_script("window.open('about:blank', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(url_certificaDoc)

        # Adiciona um MutationObserver que ficará observando o DOM para detectar a mensagem de erro.
        driver.execute_script("""
            window.errorOccurred = false;
            var observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === Node.ELEMENT_NODE && node.textContent.includes("Erro no servidor, aguarde alguns minutos e tente novamente.")) {
                        window.errorOccurred = true;
                    }
                });
            });
            });
            observer.observe(document.body, { childList: true, subtree: true });
            window.errorObserver = observer;
        """)

        select_tipo_doc = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-autenticado/app-certificao-documento/div/div/form/div/div[1]/div[2]/div/p-dropdown/div/span'))
        )
        select_tipo_doc.click()
        st.toast("Populando os campos do formulário...") 
        # Licença de Funcionamento 4
        options_tipo_doc = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/app-root/app-autenticado/app-certificao-documento/div/div/form/div/div[1]/div[2]/div/p-dropdown/div/div[3]/div[2]/ul/p-dropdownitem/li"))
        )
        options_tipo_doc.click()
        
        # SESMA
        select_secretaria = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-autenticado/app-certificao-documento/div/div/form/div/div[1]/div[4]/div/p-dropdown/div/span'))
        )
        select_secretaria.click()
        
        options_secretaria = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-autenticado/app-certificao-documento/div/div/form/div/div[1]/div[4]/div/p-dropdown/div/div[3]/div/ul/p-dropdownitem/li'))
        )
        options_secretaria.click()

        # ano expiração
        select_anoExpiracao = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-autenticado/app-certificao-documento/div/div/form/div/div[1]/div[6]/div/p-dropdown/div/span'))
        )
        select_anoExpiracao.click()

        # #
        # # item 1 é 2025 e item 2 é 2026
        # #
        # #
        # st.toast("Selecionando o ano de expiração...") 
        # item_div_gambiarra = 0
        # yyyy = get_current_year_utc3()
        # year = int(yyyy)
        # kw_anoExpiracao = int(kwargs['kw_ano'])
        # if kw_anoExpiracao == year-1:
        #   item_div_gambiarra = 1
        # elif kw_anoExpiracao == year:
        #   item_div_gambiarra = 2


        item_div_gambiarra = 1 # vencimento em 2026
     
        options_anoExpiracao = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, f"/html/body/app-root/app-autenticado/app-certificao-documento/div/div/form/div/div[1]/div[6]/div/p-dropdown/div/div[3]/div/ul/p-dropdownitem[{item_div_gambiarra}]/li"))
        )
        options_anoExpiracao.click()
        #
        #
        # Essa caceta pode dar problema no futuro
        #

        input_diretor = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-autenticado/app-certificao-documento/div/div/form/div/div[2]/div/div/input'))
        )
        input_diretor.send_keys(kwargs['kw_diretor'])

        input_numProc = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-autenticado/app-certificao-documento/div/div/form/div/div[3]/div/div/input'))
        )
        input_numProc.send_keys(kwargs['kw_proc'])

        input_numLf = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-autenticado/app-certificao-documento/div/div/form/div/div[4]/div/div/input'))
        )
        input_numLf.send_keys(kwargs['kw_lf'])

        input_cpfCnpj = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-autenticado/app-certificao-documento/div/div/form/div/div[5]/div/div/input'))
        )
        input_cpfCnpj.send_keys(kwargs['kw_cpfCnpj']) 

        input_nomeEmpresa = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-autenticado/app-certificao-documento/div/div/form/div/div[6]/div/div/input'))
        )
        input_nomeEmpresa.send_keys(kwargs['kw_nomeEmpresa'])

        field_atividades = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-autenticado/app-certificao-documento/div/div/form/div/div[7]/div/div/textarea'))
        )
        field_atividades.send_keys(kwargs['kw_atividades'])


        st.toast("Anexando a LF digitada no Certifica...") 
        # Supondo que kwargs['kw_documento'] seja um objeto de arquivo (por exemplo, de streamlit)
        
        # Certifique-se de que o ponteiro esteja no início do arquivo
        kwargs['kw_documento'].seek(0)

        # Recupera o nome original do arquivo
        original_filename = kwargs['kw_documento'].name  # Isso funciona se o objeto for um arquivo real

        # Cria um arquivo temporário na mesma pasta temporária, mas mantendo o nome original
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, original_filename)

        # Escreve o conteúdo do PDF no novo arquivo temporário
        with open(temp_file_path, "wb") as tmp_file:
            tmp_file.write(kwargs['kw_documento'].read())

        # Aguarda a presença do input de upload
        upload_input = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.presence_of_element_located(
                (By.XPATH, "//span[contains(@class, 'p-fileupload-choose')]//input[@type='file']")
            )
        )


        # Envia o caminho do arquivo temporário para o input de upload
        upload_input.send_keys(temp_file_path)

        # Opcional: Após o upload, remova o arquivo temporário (isso talvez quebre o código, pois o file uploader usa o caminho)
        # os.remove(temp_file_path)

        # Remover o elemento interferente (serve para li_e_concordo e btn_certificar)
        driver.execute_script("""
            var element = document.querySelector('.claro.rodape-container.fixo');
            if (element) {
                element.parentNode.removeChild(element);
            }
        """)

        li_e_concordo = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-autenticado/app-certificao-documento/div/div/form/div/div[11]/div[2]/div/p-checkbox/div/div[2]'))
        )
        # actions.move_to_element(li_e_concordo).click().perform()
        li_e_concordo.click()

        # 2.
        btn_certificar = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-autenticado/app-certificao-documento/div/div/div/div[2]/button'))
        )
        # actions.move_to_element(btn_certificar).click().perform()
        btn_certificar.click()

        # 3. Aguarda um curto período para que o observer possa capturar a inserção (se houver)
        time.sleep(2)

        # 4. Consulta a variável global para saber se o erro ocorreu
        error_occurred = driver.execute_script("return window.errorOccurred;")

        # 5. Opcional: desconecta o observer
        driver.execute_script("if(window.errorObserver) { window.errorObserver.disconnect(); }")

        os.remove(temp_file_path)

        temp_filename = f"{uuid.uuid4()}.pdf"
        unique_filename = ""
        if not temp_filename:
            unique_filename = temp_filename
        
        fixed_file_path = os.path.join(temp_dir, unique_filename)
        # [...] (trecho de código que espera e valida o download)

        # Aguarda o download do arquivo: verifica se ele existe, está estável (tamanho não varia) e tem tamanho compatível (>100KB)
        timeout = 30  # segundos
        start_time = time.time()
        while True:
            if os.path.exists(fixed_file_path):
                size_before = os.path.getsize(fixed_file_path)
                time.sleep(1)
                size_after = os.path.getsize(fixed_file_path)
                if size_before == size_after and size_before > 100 * 1024:
                    break
            if time.time() - start_time > timeout:
                raise Exception("Timeout esperando o arquivo certificado ser baixado.")
            time.sleep(1)

            # Lê o conteúdo do PDF baixado e retorna os dados binários
            with open(fixed_file_path, "rb") as f:
                pdf_data = f.read()

            if not pdf_data:
                st.toast(f":red[Erro. O documento não foi baixado.]")
                raise Exception("Arquivo certificado não foi encontrado ou não foi baixado completamente.")

            if error_occurred:
                st.toast(f":red[Erro no servidor, aguarde alguns minutos e tente novamente (Cinbesa fora do ar, como sempre...)]")
                return None
            else:
                st.toast(":green[Parece que o documento foi certificado...]")

                if platform.system() == "Windows":
                    downloads_dir = os.path.join(os.environ.get("USERPROFILE", ""), "Downloads")
                    print(f"Downloads directory: {downloads_dir}")
                    if os.path.isdir(downloads_dir):
                        # Define um nome fixo para o arquivo de destino na pasta Downloads
                        nome_arquivo_destino = f"LF CERTIFICADA PROC {kwargs['kw_proc']}.pdf"
                        destination_path = os.path.join(downloads_dir, nome_arquivo_destino)
                        shutil.copy(fixed_file_path, destination_path)
                        st.toast(f":blue[Arquivo também salvo em: {destination_path}]")
                        # Após a leitura, exclui o arquivo temporário
                        os.remove(fixed_file_path)
                    else:
                        st.toast(":red[A pasta Downloads não foi encontrada.]")

                time.sleep(2)
                st.toast(":blue[Encerrando o webdriver...]")
                selenium_clear_driver()
                return pdf_data

    except Exception as e:
        st.toast(f":red[Houve um erro: {e}]")
        print(e)
        selenium_clear_driver()
        traceback.print_tb(e.__traceback__)
        return None