import streamlit as st
from load_functions import *
from webdriver_certifica import selenium_certifica_doc
import gspread

if 'raw_lf_digitadas' not in st.session_state:
    st.session_state.val_ano = str(get_current_year_utc3())
    st.session_state.val_proc = ""
    st.session_state.val_processo = ""
    st.session_state.val_numLf = ""
    st.session_state.val_nomeEmpresa = ""
    st.session_state.val_cpfCnpj = ""
    st.session_state.val_viaLf = ""
    st.session_state.val_risco = ""
    st.session_state.val_dataEmissao = ""
    st.session_state.val_dataEnvio = ""
    st.session_state.val_email1 = ""
    st.session_state.val_email2 = ""
    st.session_state.val_obs = ""
    st.session_state.val_codigo = ""
    st.session_state.val_descricao = ""
    st.session_state.ano_lf = ""
    st.session_state['val_matricula'] = ''
    st.session_state['val_senha'] = ''
    st.session_state.is_email_sended_entregalf = False
    st.session_state.raw_lf_digitadas = None

    st.session_state.msg_clearFields = False

    st.session_state.df_proc = None
    st.session_state.val_obis = ''
    

    st.session_state.is_matched = None

if 'lf_document' not in st.session_state:
    st.session_state.lf_document = 'about:blank'
    st.session_state.cert_document = None
    st.session_state.dummy_doc = gerar_pdf_teste(100)
    st.session_state.cert_document_name = 'ERRO.pdf'

if 'dbtn_pesquisar' not in st.session_state:
    # st.session_state.dbtn_lf = True
    st.session_state.dbtn_enviar = True
    st.session_state.dbtn_fileUp = True
    st.session_state.dbtn_certificar = True

if 'lf_digitadas' not in st.session_state:
    st.session_state.lf_digitadas = None
    st.session_state.licencas_25 = None



@st.cache_data(ttl=480, show_spinner="Aguarde...")
def load_duas_bases():
    ws_lf = get_worksheet(1, st.secrets['sh_keys']['geral_lfs'])
    st.session_state.raw_lf_digitadas = ws_lf
    ws_proc = get_worksheet(2, st.secrets['sh_keys']['geral_major'])
    data_lf = ws_lf.get_all_records(numericise_ignore=['all'])
    data_proc = ws_proc.get_all_records(numericise_ignore=['all'])
    df_lf = pd.DataFrame(data_lf)
    df_proc = pd.DataFrame(data_proc)
    return df_lf, df_proc

st.session_state.lf_digitadas, st.session_state.licencas_25 = load_duas_bases()


# Função para extrair e-mails
def extract_emails(metadados):

    # Regex para capturar e-mails
    email_pattern = r"E-mail: '(.*?)'"
    email_cc_pattern = r"E-mail CC: '(.*?)'"
    
    # Extrair e-mails
    email = re.search(email_pattern, metadados)
    email_cc = re.search(email_cc_pattern, metadados)

     # Depuração: imprimir correspondências encontradas
    # print(f"E-mail encontrado: {email.group(1) if email else None}")
    # print(f"E-mail CC encontrado: {email_cc.group(1) if email_cc else None}")

    # print(f"E-mail encontrado: {email if email else None}")
    # print(f"E-mail CC encontrado: {email_cc if email_cc else None}")
    
   # Criar um DataFrame com os e-mails encontrados
    df = pd.DataFrame({
        'E-mail': [email.group(1) if email else None],
        'E-mail CC': [email_cc.group(1) if email_cc else None]
    })

    return df


def pesquisar_lf(ano, proc):
    val_ano_ = str(ano)
    val_proc_ = str(proc)
    df1 = st.session_state.lf_digitadas
    df2 = st.session_state.licencas_25
    df3 = st.session_state.df_2024

    certifica_lf_resetFields()

    pesquisa_lf = df1[(df1["Processo"] == val_proc_) & (df1["Ano"] == val_ano_)]

    pesquisa_lf = pesquisa_lf.copy()

    val_proc_barra = f'{val_proc_}/{val_ano_[2:4]}'

    if pesquisa_lf.empty:
        st.toast(f":orange[**Nenhum resultado encontrado para {val_proc_barra}**]")
        st.session_state.df_proc = None
        return None
   

    if val_ano_ == '2024':
        metadados = df3[
                (df3["Tipo Processo"] == "Licença de Funcionamento") &
                (df3["Número Processo"] == val_proc_) &
                (df3["Data Criação"].str.contains('/2024', na=False))
            ]
        
        if metadados.empty and val_proc_ != '98765':
            st.toast(f":orange[**Nenhum resultado encontrado para {val_proc_barra}**]")
            st.session_state.df_proc = None
            return certifica_lf_resetFields()
        else:
            if val_proc_ == '98765':
                emails_df = pd.DataFrame({'E-mail': ['devisa.processos@gmail.com'], 'E-mail CC': ['']})
            else:
                emails_df = extract_emails(metadados['Metadados'].values[0])
           
            pesquisa_lf = pd.concat([pesquisa_lf, emails_df], axis=1)
            pesquisa_lf['E-mail'] = emails_df['E-mail'].values[0]
            pesquisa_lf['E-mail CC'] = emails_df['E-mail CC'].values[0]

    else:
        emails = df2[df2['GDOC'] == val_proc_barra][['E-mail', 'E-mail CC']]
        if emails.empty:
            st.toast(f":orange[**Não foram encontrados e-mails para o processo {val_proc_barra}**]")
            st.session_state.df_proc = None
            return certifica_lf_resetFields()
        else:
            pesquisa_lf['E-mail'] = emails['E-mail'].values[0]
            pesquisa_lf['E-mail CC'] = emails['E-mail CC'].values[0]

    st.session_state.df_proc = pesquisa_lf
    certifica_carregar_lf(pesquisa_lf)


atividades_liberadas = ""

if st.session_state.val_codigo == "":
    atividades_liberadas = ""
else:
    atividades_liberadas = f"CÓDIGO: {st.session_state.val_codigo} DESCRIÇÃO: {st.session_state.val_descricao}"


st.header("Certificação de LFs", anchor=False)

with st.container(border=True):
    # st.button("Testar webdriver", on_click=selenium_certifica_doc, use_container_width=True)
    # st.subheader("Envio de LF", anchor=False)
    div1, div2 = st.columns([1, 1], gap='small', vertical_alignment="bottom")
    with div1:
        with st.container(border=True):
            c1, c2, c3, c4, c5, c6 = st.columns([0.5,0.6,0.5,0.6,1,1], gap='small', vertical_alignment="bottom")
            val_viaLf = c1.text_input("Via", max_chars=7, value=st.session_state.val_viaLf)
            c2.text_input("**Risco**", max_chars=5, value=st.session_state.val_risco, key='val_risc')
            val_ano = c3.text_input("Ano", max_chars=4, value=st.session_state.val_ano)
            c4.text_input("**Nº GDOC**", max_chars=5, key='val_proc', value=st.session_state.val_proc)
            btn_pesquisar = c5.button("Pesquisar", key='btn_pesquisar', type='primary', icon=':material/search:', use_container_width=True)
            c6.link_button("Baixar LF", url=st.session_state.lf_document, icon=':material/download:', use_container_width=True)

    with div2:
        with st.container(border=True):

            @st.fragment
            def carregar_certificador():
                c1, c2, c3, c4 = st.columns(4, gap='small', vertical_alignment="bottom")
                c1.text_input("Matrícula", max_chars=7, key='val_matricula', value=st.session_state.get('val_matricula', ''))
                c2.text_input("Senha", max_chars=20, type='password', key='val_senha', value=st.session_state.get('val_senha', ''))
                
                if st.session_state.sessao_servidor == 'Daniel':
                    st.session_state.dbtn_certificar = False
                else:
                    st.session_state.dbtn_certificar = True
                
                btn_certificar = c3.button("Certificar LF", icon=':material/qr_code:', 
                                        type='primary', 
                                        use_container_width=True,
                                        disabled=st.session_state.dbtn_certificar)

                if st.session_state.cert_document == None:
                    st.session_state.cert_document = st.session_state.dummy_doc


                c4.download_button(label='Baixar Cert.',
                                    icon=':material/download:', 
                                    data=st.session_state.cert_document,
                                    file_name = st.session_state.cert_document_name,
                                    mime="application/pdf",
                                    use_container_width=True)
                
                if btn_certificar:
                    if not st.session_state.df_proc is None:
                        # st.toast("Tem algo no dataframe!")
                        if st.session_state.val_matricula and st.session_state.val_senha:
                            if st.session_state.lf_document.startswith("http"):
                                if st.session_state.btn_lfDigitada:
                                    metadado_pdf = st.session_state.btn_lfDigitada
                                    if metadado_pdf:                            
                                        processed_pdf = selenium_certifica_doc(
                                                            kw_matricula = st.session_state.val_matricula,
                                                            kw_senha = st.session_state.val_senha,
                                                            kw_diretor = 'RENAN PUYAL RIBEIRO',
                                                            kw_ano = st.session_state.val_ano,
                                                            kw_proc = st.session_state.val_processo,
                                                            kw_lf = st.session_state.val_numLf,
                                                            kw_nomeEmpresa = st.session_state.val_nomeEmpresa,
                                                            kw_cpfCnpj = st.session_state.val_cpfCnpj,
                                                            kw_atividades = atividades_liberadas,
                                                            kw_documento = metadado_pdf,
                                                        )
                                        if processed_pdf:
                                            st.session_state.cert_document = processed_pdf
                                            st.session_state.cert_document_name = metadado_pdf.name
                                        else:
                                            st.session_state.cert_document = st.session_state.dummy_doc
                                            st.session_state.cert_document_name = 'ERRO.pdf'

                                else:
                                    st.toast(":red[Faça o upload da LF digitada antes de prosseguir.]")   
                            else:
                                st.toast(":red[Não existe LF digitada no campo de documento.]")  
                        else:
                            st.toast(":red[Preencha corretamente a sua matrícula e senha.]") 
                    else:
                        st.toast(":red[Erro. Não há licença para certificar.]")

            carregar_certificador()    


    if btn_pesquisar:

        try:
            v_ano = int(val_ano)
            v_proc = int(st.session_state.val_proc)
            if (v_ano == 2024 or v_ano == 2025) and (v_proc >= 1 and v_proc <= 99999):
                pesquisar_lf(v_ano, v_proc)
            else:
                st.toast(":red[Preencha corretamente os campos de Ano e GDOC (1).]")
                st.session_state.is_matched = None
        except Exception as e:
            print(e)
            st.toast(":red[Preencha corretamente os campos de Ano e GDOC (2).]")
            st.session_state.is_matched = None
        finally:
            if st.session_state.is_matched:
                st.toast(f":green[Processo {st.session_state.val_proc}/{st.session_state.val_ano} encontrado]")
                st.session_state.is_matched = None
            elif not st.session_state.is_matched:
                #st.toast(f":red[Processo {st.session_state.val_proc}/{st.session_state.val_ano} não encontrado]")
                st.session_state.is_matched = None


    c1, c2, c3, c4, c5, c6 = st.columns([0.8, 0.8, 0.8, 0.8, 1.8, 1], gap="medium", vertical_alignment="bottom")
    val_numProc = c1.text_input("Núm. Processo", max_chars=20, value=st.session_state.val_processo)
    val_numLf = c2.text_input("Núm. Licença", max_chars=7, value=st.session_state.val_numLf)
    val_dataEmissao = c3.text_input("Data Emissão", max_chars=10, value=st.session_state.val_dataEmissao)
    val_dataEnvio = c4.text_input("Data Envio LF", max_chars=10, value=st.session_state.val_dataEnvio)
    val_nomeEmpresa = c5.text_input("Nome Empresa", max_chars=40, value=st.session_state.val_nomeEmpresa)
    val_cpfCnpj= c6.text_input("CPF / CNPJ", max_chars=18, value=st.session_state.val_cpfCnpj)
    
    st.text_area("Atividades Liberadas", height=76, max_chars=1500, value=atividades_liberadas)

    c1, c2, c3 = st.columns(3, gap="medium", vertical_alignment='top')
    
    c1.text_area("Observações", height=76, max_chars=255, placeholder="Campo opcional", value=st.session_state.val_obs,
                    key='val_obis')
    
    c2.file_uploader("***Anexar a LF Digitada***",
                    key='btn_lfDigitada',
                    #disabled=st.session_state.dbtn_fileUp,
                    disabled=False,
                    type='pdf',
                    )

    c3.file_uploader("**Anexar a LF certificada**",
                        key='btn_fileUploader',
                        #disabled=st.session_state.dbtn_fileUp,
                        disabled=False,
                        type='pdf',
                        )
    
    c1, c2, c3, c4 = st.columns(4, gap="medium", vertical_alignment="bottom")
    val_email1 = c3.text_input("E-mail Principal", max_chars=20, value=st.session_state.val_email1)
    val_email2 = c4.text_input("E-mail CC", max_chars=20, value=st.session_state.val_email2)

    st.divider()

    
    def validar_licenca():
        if st.session_state.btn_fileUploader is None:
            return st.toast(":red[Anexe a Licença de Funcionamento no botão de Upload.]")
        
        if not st.session_state.df_proc.iloc[0]["Processo"]:
            return st.toast(":red[Pesquise por um processo antes de continuar.]")
        
        grau_risco = st.session_state.val_risc

        match grau_risco:
            case 'Baixo' | 'Médio' | 'Alto':
                st.toast(f"Tentando enviar a LF {st.session_state.val_numLf}. Aguarde...")
            case _:
                return st.toast(":red[Preencha o campo de Risco (Alto, Médio ou Baixo)]")

        # Captura valores obrigatórios
        num_lf = st.session_state.val_numLf
        data_emissao = st.session_state.val_dataEmissao
        num_proc = val_numProc
        nome_empresa = st.session_state.val_nomeEmpresa
        cpf_cnpj = st.session_state.val_cpfCnpj
        email1 = st.session_state.val_email1

        # Verifica preenchimento
        for val in (num_lf, data_emissao, num_proc, nome_empresa, cpf_cnpj, email1):
            if not val:
                return st.toast(":red[Os campos 'número LF', 'data emissão', 'número processo', 'nome empresa', 'CPF/CNPJ' e 'E-mail' precisam estar preenchidos]")

        # Prepara despacho e envia e-mail
        despacho = (
            f"Segue em anexo a Licença de Funcionamento <strong>{num_lf}</strong>, emitida em <strong>{data_emissao}</strong> e referente ao Processo <strong>{num_proc}</strong> (Empresa <strong>{nome_empresa}</strong>, CPF/CNPJ <strong>{cpf_cnpj}</strong>)."
        )

        email_enviarLicenca(
            kw_despacho=despacho,
            kw_ano=st.session_state.ano_lf,
            kw_email1=email1,
            kw_email2=st.session_state.val_email2,
            kw_licenca=st.session_state.btn_fileUploader,
        )


        st.toast("**Salvando dados na base de LFs...**")
        # Seleciona worksheet correta
        if not st.session_state.raw_lf_digitadas:
            worksheet = get_worksheet(1, st.secrets['sh_keys']['geral_lfs'])
        else:
            worksheet = st.session_state.raw_lf_digitadas


        # # procs = [17679, 9881, 7982, 12391, 18120, 3619, 8429, 7897, 6552, 18689, 18116, 18109, 18119, 16225, 16476, 15394,
        # #          8222, 8155, 8102, 6256, 5935, 3969, 3110, 7487, 6891, 3277, 12206, 3327, 4372, 8222, 8105, 8102]

        # # procs = [
        # #          8222, 8155, 8102, 6256, 5935, 3969, 3110, 7487, 6891, 3277, 12206, 3327, 4372, 8222, 8105, 8102]

        # procs = [18109, 18119, 16225, 16476, 15394]

        # for num_proc in procs:
        #     proc_str = str(num_proc)
        #     year_str = str(st.session_state.ano_lf)
        #     cells = worksheet.findall(proc_str, in_column=1)
        #     updated = 0

            

        #     for cell in cells:
        #         print(f"cell {cell}")
        #         row = cell.row
        #         print(f"worksheet.cell(row, 2).: {worksheet.cell(row, 17).value} e year_str: {year_str}")
        #         if worksheet.cell(row, 17).value == year_str:
        #             # Atualiza somente 3 colunas: Q (risco), R (data), S (observação)
        #             range_lf = f"AA{row}:AB{row}"
        #             # valores = [[grau_risco, get_current_date_utc3(), st.session_state.val_obis]]
        #             valores = [["26/04/2025", st.session_state.val_obis]]
        #             worksheet.update(range_lf, valores, raw=False)
        #             updated += 1
        #         print(f"Zé {updated}")

        # # Feedback ao usuário
        # if updated:
        #     st.toast(f":green[Dados salvos na base de LFs em {updated} linha(s)]")
        # else:
        #     st.warning("Nenhuma linha encontrada para esse processo e ano.")

        # load_duas_bases.clear()
        # certifica_lf_resetFields()

        
        # Atualiza dados na planilha
        proc_str = str(st.session_state.val_proc)
        year_str = str(st.session_state.ano_lf)
        cells = worksheet.findall(proc_str, in_column=1)
        updated = 0

        for cell in cells:
            row = cell.row
            if worksheet.cell(row, 17).value == year_str:
                # Atualiza somente 3 colunas: Z (risco), AA (data), AB (observação)
                range_lf = f"Z{row}:AB{row}"
                valores = [[grau_risco, get_current_date_utc3(), st.session_state.val_obis]]
                worksheet.update(range_lf, valores, raw=False)
                updated += 1

        # Feedback ao usuário
        if updated:
            # st.toast(f":green[Dados salvos na base de LFs em {updated} linha(s)]")
            st.toast(f":green[**Dados salvos na base de LFs**")
        else:
            st.toast(":red[**Nenhuma linha encontrada para esse processo e ano.**]")

        load_duas_bases.clear()
        certifica_lf_resetFields()

    def clear_fields():
        st.session_state.val_ano = str(get_current_year_utc3())
        st.session_state.val_proc = ""
        st.session_state.val_processo = ""
        st.session_state.val_numLf = ""
        st.session_state.val_nomeEmpresa = ""
        st.session_state.val_cpfCnpj = ""
        st.session_state.val_viaLf = ""
        st.session_state.val_risco = ""
        st.session_state.val_dataEmissao = ""
        st.session_state.val_dataEnvio = ""
        st.session_state.val_email1 = ""
        st.session_state.val_email2 = ""
        st.session_state.val_obs = ""
        st.session_state.val_codigo = ""
        st.session_state.val_descricao = ""
        st.session_state.ano_lf = ""
        st.session_state.is_email_sended_entregalf = False
        st.session_state.raw_lf_digitadas = None
        st.session_state.df_proc = None
        st.session_state.val_obis = ''
        st.session_state.is_matched = None
        st.session_state.msg_clearFields = True

    if st.session_state.msg_clearFields:
        st.toast("Formulário limpo com sucesso.")
        st.session_state.msg_clearFields = False

        

    c1, c2, c3, c4, c5 = st.columns(5, gap="small", vertical_alignment="bottom")
    c2.button("Limpar Campos", on_click=clear_fields, use_container_width=True, icon=':material/delete:')
    c3.link_button("Abrir GDOC", url='https://gdoc.belem.pa.gov.br/gdocprocessos/processos/meusprocessos', use_container_width=True, icon=':material/language:')
    c4.link_button("Abrir Certifica", url='https://sistemas.belem.pa.gov.br/portaldoservidor/#/login', use_container_width=True, icon=':material/verified_user:')
    # c5.button("Enviar LF", key='btn_enviarLf', type='primary', use_container_width=True, icon=':material/send:', disabled=st.session_state.dbtn_enviar)
    c5.button("Enviar LF", key='btn_enviarLf', type='primary', on_click=validar_licenca, use_container_width=True, icon=':material/send:', disabled=False)