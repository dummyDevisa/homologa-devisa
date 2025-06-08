from webdriver import *


def selenium_login_etax():
    #PLACEHOLDER.toast("Executando selenium_login_etax...")
    
    # URL de acesso
    url_login = "http://siat.belem.pa.gov.br:8081/acesso/login.jsf"
  
    driver = get_driver()

    try:
        # Acessar a página inicial
        driver.get(url=url_login)
        # Preencher o formulário de login
        WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.presence_of_element_located((By.ID, "userNameCpf"))
        )
        # por enquanto projetado para logar somente com a conta Dan
        driver.execute_script(f'document.getElementById("userNameCpf").value = "{st.secrets['dany']['usr']}";')
        driver.execute_script(f'document.getElementById("password").value = "{st.secrets['dany']['psw']}";')

        # Clicar no botão de login
        button = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.element_to_be_clickable((By.ID, "j_idt40"))
        )
        actions = ActionChains(driver)
        actions.move_to_element(button).click().perform()

        # Verificar se é necessário confirmar a sessão ativa
        try:
            WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
                EC.visibility_of_element_located((By.ID, "j_idt43"))
            )
            driver.execute_script(f'document.getElementById("password").value = "{st.secrets['dany']['psw']}";')
            button = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
                EC.element_to_be_clickable((By.ID, "j_idt43"))
            )
            actions.move_to_element(button).click().perform()
        except Exception:
            print("Já tem sessão ativa. Relogando...")

        # Acessar o menu de permissões
        # PLACEHOLDER.toast("Acessando o menu de permissões...")
        
        modulo = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="panelMenuPermissoes"]'))
        )
        modulo.click()

        # Acessar o módulo de arrecadação
        modulo_arrecadacao = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="panelMenuPermissoes_0"]'))
        )
        modulo_arrecadacao.click()

        # Esperar até que a nova aba seja aberta
        WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            lambda d: len(d.window_handles) > 1
        )

        # Trocar para a nova aba
        driver.switch_to.window(driver.window_handles[-1])

        # # Aguardar o carregamento completo da nova aba
        # WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        #     EC.presence_of_element_located((By.XPATH, '//*[@id="formHome"]'))  # Substitua pelo seletor correto
        # )

        # executar a emissão do DAM
        selenium_emissao_dam()

    except Exception as e:
        # print(f"Erro encontrado: {e}")
        selenium_clear_driver()
        traceback.print_tb(e.__traceback__)


def selenium_emissao_dam():
    # PLACEHOLDER.toast("Executando selenium_emissao_dam...")
    
    driver = get_driver()
    actions = ActionChains(driver) # alternativa ao .click(), a caceta do siat tem incompatibilidade

    time.sleep(4)
    url_emissao = "http://siat.belem.pa.gov.br:8081/arrecadacao/pages/arrecadacao/guiaArrecadacaoEmissao.jsf"
    
    # Abrir nova aba e acessar a URL desejada
    driver.execute_script("window.open('about:blank', '_blank');")
    driver.switch_to.window(driver.window_handles[-1])
    driver.get(url_emissao)

    # Aguardar o carregamento completo da nova página
    WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    # PLACEHOLDER.toast("Verificando o CPF ou CNPJ...")
    
    # CAMPO CNPJ
    if len(st.session_state.list_usr['cpf_cnpj']) == 18:
        radio_cnpj = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="j_idt51"]/tbody/tr/td[3]/div/div[2]/span'))
        )
        radio_cnpj.click()

        field_cnpj = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="inputCNPJ"]'))
        )
        field_cnpj.click()
        field_cnpj.send_keys(st.session_state.list_usr['cpf_cnpj'])

    elif len(st.session_state.list_usr['cpf_cnpj']) == 14:
        radio_cpf = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="j_idt51"]/tbody/tr/td[1]/div/div[2]/span'))
        )
        radio_cpf.click()
    
        field_cpf = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="inputCPF"]'))
        )
        field_cpf.click()
        field_cpf.send_keys(st.session_state.list_usr['cpf_cnpj'])

    # CAMPO NOME
    field_name = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, 'nomePagInput'))
    )
    field_name.click()
    
    # field_name.send_keys(Keys.TAB) # necessário, infelizmente
    # PLACEHOLDER.toast("Aguardando rótulo clicável...")
    
    # Esperar até que o rótulo esteja clicável e clicar nele para abrir o dropdown
    dropdown_sesma = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, 'selectInstituicao'))
    )
    dropdown_sesma.click()
    actions.move_to_element(dropdown_sesma).click().perform()

    # checar se nome existe no campo. Se não existir usar o nome obtido no payload
    field_name = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(EC.visibility_of_element_located((By.ID, 'nomePagInput')))
    # verificar se o nome existe de fato
    check_if_name = field_name.get_attribute("value")
    
    
    if not check_if_name:
        if len(st.session_state.list_usr['cpf_cnpj']) == 18:
            json_cnpj = get_cnpj_raw(st.session_state.list_usr['cpf_cnpj'])
            #st.write(razao_cnpj['razao_social'])
            razao_cnpj = json_cnpj['razao_social']
            if razao_cnpj:
                field_name.click()
                field_name.send_keys(razao_cnpj)
            else:
                st.toast(f":red[**Erro na consulta do CNPJ para obtenção de nome. Saindo...**]")
                raise Exception("Erro na consulta do CNPJ para obtenção de nome. Saindo...")
        elif len(st.session_state.list_usr['cpf_cnpj']) == 14:
            field_name.click()
            field_name.send_keys(st.session_state.list_usr['nome_pf'])
        else:
            st.toast(f":red[**Erro: O nome de pessoa física não foi carregado no e-tax. Faça a emissão desse DAM manualmente.**]")
            raise Exception("Erro: O nome de pessoa física não foi carregado no e-tax. Faça a emissão desse DAM manualmente.")

    # PLACEHOLDER.toast("Aguardando o painel no DOM...")
    
    # Esperar até que o painel esteja visível e não apenas presente no DOM
    WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.visibility_of_element_located((By.ID, 'selectInstituicao_panel'))
    )

    painel_sesma = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.visibility_of_element_located((By.XPATH, '//*[@id="selectInstituicao_panel"]/div/ul/li[3]'))
    )
    actions.move_to_element(painel_sesma).click().perform()


    dropdown_tributo = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, 'selectTributo'))
    )
    actions.move_to_element(dropdown_tributo).click().perform()

    # Esperar até que o painel esteja visível e não apenas presente no DOM
    WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.visibility_of_element_located((By.ID, 'selectTributo_panel'))
    )

    painel_tributo = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.visibility_of_element_located((By.XPATH, '//*[@id="selectTributo_panel"]/div/ul/li[2]'))
    )
    actions.move_to_element(painel_tributo).click().perform()


    # 1. Esperar o elemento que dispara o dropdown ficar clicável e clicar nele
    dropdown_trigger = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, 'selectImpostos'))
    )
    actions.move_to_element(dropdown_trigger).click().perform()

    # 2. Esperar o painel de opções ficar visível
    panel_locator = (By.ID, 'selectImpostos_panel')
    WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.visibility_of_element_located(panel_locator)
    )

    # 3. Construir um XPath para localizar o elemento <li> desejado DENTRO do painel,
    #    baseado no texto ou em um atributo como 'data-label' (se existir - inspecione o <li>).
    #    Usar o texto é mais comum. O XPath procura um <li> dentro do painel
    #    cujo texto *comece* com "1614". Use normalize-space() para ignorar espaços extras.
    option_xpath = "//div[@id='selectImpostos_panel']//li[starts-with(normalize-space(.), '1614')]"
    # Alternativa (se o <li> tiver um atributo data-label exato, pode ser mais preciso):
    # option_xpath = "//div[@id='selectImpostos_panel']//li[@data-label='1614 - TAXA DE VIGILÂNCIA SANITÁRIA']"

    # 4. Esperar especificamente pela opção desejada ficar clicável dentro do painel
    option_element = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, option_xpath))
    )

    time.sleep(2)
    
    # 5. Mover para a opção e clicar nela
    #    Usar ActionChains é mais seguro aqui, caso o painel precise de rolagem.
    actions.move_to_element(option_element).click().perform()
    # Alternativa: option_element.click() # Pode funcionar se não houver rolagem

    print("Opção '1614 - TAXA DE VIGILÂNCIA SANITÁRIA' selecionada com sucesso.")

    time.sleep(1)

    field_date = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, 'inputDataVencimento_input'))
    )
    field_date.click()
    dt_vencimento = data_vencimento()
    field_date.send_keys(dt_vencimento)


    dropdown_Identificacao = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, 'selectTipoIdentificacao'))
    )
    actions.move_to_element(dropdown_Identificacao).click().perform()

    # Esperar até que o painel esteja visível e não apenas presente no DOM
    WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.visibility_of_element_located((By.ID, 'selectTipoIdentificacao_panel'))
    )

    # CAMPO CNPJ
    xpath_identificacao = ''
    if len(st.session_state.list_usr['cpf_cnpj']) == 18:
        xpath_identificacao = '//*[@id="selectTipoIdentificacao_panel"]/div/ul/li[3]'
        
    elif len(st.session_state.list_usr['cpf_cnpj']) == 14:
        xpath_identificacao = '//*[@id="selectTipoIdentificacao_panel"]/div/ul/li[2]'
    
    # PLACEHOLDER.toast("Acessando a base pelo xpath...")
    
    painel_identificacao = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.visibility_of_element_located((By.XPATH, xpath_identificacao))
    )
    actions.move_to_element(painel_identificacao).click().perform()

    # valor DAM
    field_valordam = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, 'inputValorPrincipal_input'))
    )
    field_valordam.click()
    field_valordam.send_keys(st.session_state.list_usr['valor'])

    # infoAdicionais
    field_despacho = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, 'infoAdicionais'))
    )
    field_despacho.click()
    field_despacho.send_keys(st.session_state.list_usr['despacho']) 

    # PLACEHOLDER.toast("Clicando no botão btnNewItem...")
    
    # Clicar no botão btnNewItem
    btnNewItem = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, "btnNewItem"))
    )
    btnNewItem.click()
    actions.move_to_element(btnNewItem).click().perform()


    # PLACEHOLDER.toast("Clicando no botão emitir DAM...")
    
    # clicar no botão emitir DAM 'btnEmitirDAM'
    btnEmitirDAM = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, "btnEmitirDAM"))
    )
    btnEmitirDAM.click()
    # actions.move_to_element(btnEmitirDAM).click().perform()
    
    time.sleep(1)
    
    actions.move_to_element(btnEmitirDAM).click().perform()
    
    time.sleep(6)

    selenium_get_numeroDam()
    
    # page_source = driver.page_source
    # st.code(page_source, language="html")


def selenium_get_numeroDam():
    st.toast("Executando a consulta do DAM...")
    
    driver = get_driver()
    actions = ActionChains(driver) # alternativa ao .click(), a caceta do siat tem incompatibilidade
    url_consulta = "http://siat.belem.pa.gov.br:8081/arrecadacao/pages/arrecadacao/guiaArrecadacaoConsulta.jsf"

    # Abrir nova aba e acessar a URL desejada
    driver.execute_script("window.open('about:blank', '_blank');")
    driver.switch_to.window(driver.window_handles[-1])
    driver.get(url_consulta)

    # Aguardar o carregamento completo da nova página
    WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    field_identificacao = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, 'inputNrIdentificacao'))
    )
    field_identificacao.click()
    field_identificacao.send_keys(st.session_state.list_usr['cpf_cnpj'])
    
    btnBuscar = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, "btnBuscar"))
    )
    btnBuscar.click()

    # Aguarde até que a tabela esteja visível
    table = WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.ui-datatable-tablewrapper table"))
    )

    # listar todos os elementos da tabela
    list_50 =  WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
        EC.visibility_of_element_located((By.XPATH, "/html/body/div[3]/div[3]/div/form/div/fieldset[2]/div/div/div[2]/select"))
    )
    
    # Cria um objeto Select com o elemento encontrado
    select = Select(list_50)

    # Seleciona a opção com valor "50"
    select.select_by_value("50")

    time.sleep(2)

    # Encontre as linhas do corpo da tabela
    rows = table.find_elements(By.CSS_SELECTOR, "tbody.ui-datatable-data tr")

    # PLACEHOLDER.toast("Carregando a tabela de registros do e-tax..")
    
    # Itere sobre as linhas da tabela
    table_data = []
    for row in rows:
        # Encontre todas as células da linha
        cells = row.find_elements(By.CSS_SELECTOR, "td")
        # Extraia o texto de cada célula
        row_data = [cell.text.strip() for cell in cells]
        # Adicione a linha extraída à lista de dados
        table_data.append(row_data)

    # print(table_data)

    # Dados para verificação
    dt_vencimento = data_vencimento()
    data_atual = data_hoje()
    ano_atual = data_atual[8:10]
    validador_dam = f"{ano_atual}0307"
    valor_formatado = ''.join(c for c in st.session_state.list_usr['valor'] if c.isdigit() or c in {',', '.'})

    # Inicialize um indicador para saber se a verificação foi bem-sucedida
    verificacao_sucesso = False

    # PLACEHOLDER.toast("Iniciando a validação dos valores...")
    
    # Verifique todas as linhas da tabela
    for row in table_data:
        table_data_cnpj = ''.join(filter(str.isdigit, row[1]))
        table_data_cnpj = mascara_cnpj_cpf(table_data_cnpj)
        table_data_dam = row[0]
        
        if ((table_data_dam[0:6] == validador_dam) 
            and (dt_vencimento == row[2])
            and (st.session_state.list_usr['cpf_cnpj'] == table_data_cnpj)
            and (valor_formatado == row[3])):
            # Se a linha passar na verificação, salve o valor e interrompa o loop
            st.session_state.numero_dam = table_data_dam
            verificacao_sucesso = True
            break

    # Resultado da verificação
    if verificacao_sucesso:
        st.toast(f":green[Passou na verificação. Núm. DAM: {st.session_state.numero_dam}. Saindo...]")
    else:
        st.toast(":red[Falhou na verificação. Veja o console.]")
        # Debugging: imprima os detalhes para todas as linhas que falharam
        for row in table_data:
            print(f"""
            'row[0][0:6]': {row[0][0:6]},\n
            'validador_dam': {validador_dam},\n
            'dt_vencimento': {dt_vencimento},\n
            'row[2]': {row[2]},\n
            'st.session_state.list_usr['cpf_cnpj']': {st.session_state.list_usr['cpf_cnpj']},\n
            'table_data_cnpj': {''.join(filter(str.isdigit, row[1]))},\n
            'valor_formatado e row[3]': {valor_formatado} e {row[3]}, 
            """)



    selenium_clear_driver()


def selenium_generate_dam(list_usr):
   # print(list_usr)
    if 'list_usr' not in st.session_state:
        st.session_state.list_usr = None
        st.session_state.numero_dam = None
    st.session_state.list_usr = list_usr

    selenium_login_etax()

    num_dam = st.session_state.numero_dam
    st.session_state.numero_dam = None
    print(f"num_dam: {num_dam}")
    st.session_state.list_usr = None

    if num_dam:
        print(f"DAM gerado com sucesso (Núm. {num_dam}).")
        return num_dam
    else:
        st.toast(f":red[**O número do DAM não foi gerado.**]")
