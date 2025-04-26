from webdriver import *

def selenium_login_gdoc():
    # URL de acesso
    url_login = "https://gdoc.belem.pa.gov.br/gdocprocessos/login/"
    driver = get_driver()
    actions = ActionChains(driver)

    # Acessar a página inicial
    driver.get(url_login)
    # Preencher o formulário de login
    matricula = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[2]/div[2]/form/input[2]'))
    )
    # driver.execute_script(f'document.getElementById("matricula").value = "{st.secrets['dany']['mtrc']}";')
    matricula.send_keys(st.secrets['dany']['mtrc'])


    senha = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[2]/div[2]/form/input[3]"))
    )
    # driver.execute_script(f'document.getElementById("senha").value = "{st.secrets['dany']['psw']}";')
    senha.send_keys(st.secrets['dany']['psw'])


    # Clicar no botão de login
    btn_login = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[2]/div[2]/form/div/div[2]/button"))
    )

# dict_gdoc = {
#     'cpf_cnpj': '25.474.580/0001-80',
#     'nome_empresa': 'EMPRESA DE TESTE PARA O GDOC',
#     # 'cep': '66130685',
#     # 'endereco': 'RUA BATRACO SURULI',
#     # 'numero': '80',
#     # 'complemento': 'ESTE E O COMPLEMENTO',
#     # 'bairro': 'ICOARACI',
#     # 'cidade': 'BELEM',
#     # 'uf': 'PA',
#     'email': 'segov.emaildaempresa@gmail.com',
# }

def clean_value(value):
    """
    Retorna uma string vazia se o valor for None, vazio ou 'NaN' (ignorando maiúsculas/minúsculas);
    caso contrário, retorna o próprio valor.
    """
    if value is None or (isinstance(value, str) and (value.strip() == '' or value.strip().lower() == 'nan')):
        return ""
    return value

def extrair_dados(data):
    """
    A partir do dicionário 'data' (obtido do JSON), extrai os seguintes campos:
      - cnpj
      - razao_social
      - cep
      - (descricao_tipo_de_logradouro + logradouro) concatenados com um espaço
      - numero
      - complemento
      - bairro
      - municipio
      - uf
      - email
      
    Valores que sejam NULL, vazio ou 'NaN' são substituídos por string vazia.
    """
    # Extração e limpeza dos campos individuais
    cnpj = clean_value(data.get("cnpj"))
    razao_social = clean_value(data.get("razao_social"))
    cep = clean_value(data.get("cep"))
    descricao_tipo_de_logradouro = clean_value(data.get("descricao_tipo_de_logradouro"))
    logradouro = clean_value(data.get("logradouro"))
    # Concatenando os valores para formar o endereço
    endereco = "{} {}".format(descricao_tipo_de_logradouro, logradouro).strip()
    numero = clean_value(data.get("numero"))
    complemento = clean_value(data.get("complemento"))
    bairro = clean_value(data.get("bairro"))
    municipio = clean_value(data.get("municipio"))
    uf = clean_value(data.get("uf"))
    email = clean_value(data.get("email"))
    
    # Construindo o dicionário final com os dados desejados
    return {
        "cnpj": cnpj,
        "razao_social": razao_social,
        "cep": cep,
        "logradouro": endereco,
        "numero": numero,
        "complemento": complemento,
        "bairro": bairro,
        "municipio": municipio,
        "uf": uf,
        "email": email
    }

def selenium_proc_gdoc(**kwargs):
    # URL de acesso
    url_login = "https://gdoc.belem.pa.gov.br/gdocprocessos/login/"
    driver = get_driver()
    actions = ActionChains(driver)

    # Acessar a página inicial
    driver.get(url_login)
    
    # Preencher o formulário de login
    field_matricula = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[2]/div[2]/form/input[2]'))
    )
    # driver.execute_script(f'document.getElementById("matricula").value = "{st.secrets['dany']['mtrc']}";')
    field_matricula.send_keys(st.secrets['dany']['mtrc'])

    field_senha = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[2]/div[2]/form/input[3]"))
    )
    # driver.execute_script(f'document.getElementById("senha").value = "{st.secrets['dany']['psw']}";')
    field_senha.send_keys(st.secrets['dany']['psw'])

    # Clicar no botão de login
    btn_login = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[2]/div[2]/form/div/div[2]/button"))
    )

    btn_login.click()

    WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/form/div[1]/ul/li[1]/a")) # menu inicio
    )

    driver.execute_script("window.open('about:blank', '_blank');")
    driver.switch_to.window(driver.window_handles[-1])
    url_pesquisarInteressado = 'https://gdoc.belem.pa.gov.br/gdocprocessos/processo/pesquisarInteressado'
    driver.get(url_pesquisarInteressado)
    json_cnpj = None

    field_cpf_cnpj = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/fieldset/div/table[1]/tbody/tr[2]/td[2]/input"))
    )

    cpf_cnpj_limpo = limpando_cpf_cnpj(kwargs['kw_cpf_cnpj'])

    field_cpf_cnpj.send_keys(cpf_cnpj_limpo)

    btn_pesquisarInteressado = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/fieldset/div/table[1]/tbody/tr[3]/td[2]/button/span"))
    )
    btn_pesquisarInteressado.click()  

    try:
        # testar se há interessado...
        btn_abrirProcesso = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/div/div[2]/table/tbody/tr/td[3]/button"))
        )
    except:
        # Não há interessado. Cadastrar um novo
        if len(kwargs['kw_cpf_cnpj']) != 18:
            driver.quit()
            return st.toast(":orange[**Cadastre primeiro a pessoa física no GDOC antes de continuar.**]")
        else:
            btn_cadastrarInteressado = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/fieldset/div/table[1]/tbody/tr[4]/td[2]/button[2]"))
            )
            btn_cadastrarInteressado.click()

            select_all = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/fieldset/div/table/tbody/tr[2]/td[2]/div/label")))
            select_all.click()

            select_cnpj = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[9]/div/ul/li[2]")))
            select_cnpj.click()

            time.sleep(2)

            raw_json = get_cnpj_raw(kwargs['kw_cpf_cnpj'])
            json_cnpj = extrair_dados(raw_json)

            btn_salvarInteressado = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
                EC.element_to_be_clickable((By.ID, "j_idt204")) # pode alterar com o tempo, mas o xpath não estava funcionando então...
            )
            

        field_cnpj = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/fieldset/div/table/tbody/tr[3]/td[2]/div/input")))
        field_cnpj.send_keys(json_cnpj['cnpj'])

        field_nome = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/fieldset/div/table/tbody/tr[1]/td[2]/input")))
        field_nome.send_keys(json_cnpj['razao_social'])

        field_cep = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/fieldset/div/fieldset[1]/div/table/tbody/tr[1]/td[2]/input")))
        field_cep.send_keys(json_cnpj['cep'])

        field_endereco = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/fieldset/div/fieldset[1]/div/table/tbody/tr[2]/td[2]/input")))
        field_endereco.send_keys(json_cnpj['logradouro'])

        field_numero = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/fieldset/div/fieldset[1]/div/table/tbody/tr[3]/td[2]/input")))
        field_numero.send_keys(json_cnpj['numero'])

        field_complemento = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/fieldset/div/fieldset[1]/div/table/tbody/tr[4]/td[2]/input")))
        field_complemento.send_keys(json_cnpj['complemento'])

        field_bairro = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/fieldset/div/fieldset[1]/div/table/tbody/tr[5]/td[2]/input")))
        field_bairro.send_keys(json_cnpj['bairro'])

        field_cidade = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/fieldset/div/fieldset[1]/div/table/tbody/tr[6]/td[2]/input")))
        field_cidade.send_keys(json_cnpj['municipio'])

        field_uf = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/fieldset/div/fieldset[1]/div/table/tbody/tr[7]/td[2]/input")))
        field_uf.send_keys(json_cnpj['uf'])

        randir = codigo_alfabetico()
        email_avacalhado = randir + kwargs['kw_email1']
        
        field_email = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/div[4]/div[1]/div[2]/form/fieldset/div/fieldset[2]/div/table/tbody/tr/td[2]/input')))
        field_email.send_keys(email_avacalhado)

        time.sleep(1)

        btn_salvarInteressado.click()

        driver.get(url_pesquisarInteressado)

        #  Repetindo pesquisa de interessado e abrir processo
        field_cpf_cnpj = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/fieldset/div/table[1]/tbody/tr[2]/td[2]/input"))
        )

        field_cpf_cnpj.send_keys(cpf_cnpj_limpo)

        btn_pesquisarInteressado = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/div/div[2]/table/tbody/tr/td[3]/button"))
        )
        btn_pesquisarInteressado.click()

        btn_abrirProcesso = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div[1]/div[2]/form/div/div[2]/table/tbody/tr/td[3]/button"))
        )

    # Abrir processo em interessado já existente
    btn_abrirProcesso.click()

    check_digital = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/div[4]/div[1]/div[2]/form/fieldset/div/table/tbody/tr[3]/td[2]/div'))
    )
    check_digital.click()

    doc_origem = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.presence_of_element_located((By.ID, 'form:tfNumeroOrigem'))
    )
    doc_origem.send_keys(kwargs['kw_cpf_cnpj'])

    select_processo = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/div[4]/div[1]/div[2]/form/fieldset/div/table/tbody/tr[7]/td[2]/div'))
    )
    select_processo.click()

    time.sleep(1)

    select_processoField = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.presence_of_element_located((By.XPATH, '/html/body/div[10]/div[1]/input'))
    )
    select_processoField.send_keys('LICENÇA DE FUNCIONAMENTO - DEVISA')
    time.sleep(1)
    select_processoField.send_keys(Keys.ENTER)

    textarea_instrucInicial = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.presence_of_element_located((By.ID, 'form:tfInstrucao'))
    )
    
    sending_text = f"{kwargs['kw_cpf_cnpj']} - {kwargs['kw_divisao']}. Empresa: {kwargs['kw_razao_social']}. E-mail(s): {kwargs['kw_email1']}; {kwargs['kw_email2']}"
    print(f"sending_text → {sending_text}")
    
    time.sleep(1)
    actions.click(textarea_instrucInicial)
    actions.send_keys(sending_text)
    actions.perform()
    # textarea_instrucInicial.send_keys(sending_text)

    time.sleep(1)

    btn_salvarProcesso = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, '/html/body/div[4]/div[1]/div[2]/form/button[1]'))
    )
    btn_salvarProcesso.click()

    # Espera o elemento <td> que contém os dois <span> (localizado dentro do fieldset pelo id)
    td_element = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.presence_of_element_located((By.XPATH, '//fieldset[@id="j_idt126"]//tr[1]/td[2]'))
    )

    # Busca por todos os elementos <span> dentro do <td>
    spans = td_element.find_elements(By.XPATH, ".//span")
    if spans:
        numero_processo_texto = spans[0].text  # Extrai o texto do primeiro <span>
        print(numero_processo_texto)  # Deve imprimir: 16906/2025 - SESMA
    else:
        print("Nenhum elemento <span> encontrado no <td>.")
    
    btn_anexos = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, "j_idt222")) # pode alterar com o tempo, mas o xpath não estava funcionando então...
    )
    btn_anexos.click()

    nome_anexo = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.presence_of_element_located((By.ID, 'documentoC'))
    )
    nome_anexo.send_keys('docs iniciais')

    select_anexoField = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, 'especieC_label'))
        )
    select_anexoField.click()
    time.sleep(1)
    anexo_filter = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.presence_of_element_located((By.ID, 'especieC_filter'))
    )
    anexo_filter.send_keys('DOCUMENTOS')
    time.sleep(1)
    anexo_filter.send_keys(Keys.ENTER)



    st.toast(f"**Fim da automação (processo {numero_processo_texto}). Vai fechar o driver...**")
    # time.sleep(10)
    # driver.quit()
    
    

    
        