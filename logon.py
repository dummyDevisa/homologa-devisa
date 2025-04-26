import streamlit as st
import pandas as pd
from load_functions import *
from cookies import *
import time
# from proxy import *
from streamlit_js_eval import streamlit_js_eval

@st.cache_data(ttl=18000, show_spinner="Aguarde...")
def load_auth_usr():
    worksheet = get_worksheet(3, st.secrets['sh_keys']['geral_major'])
    data = worksheet.get_all_records(numericise_ignore=['all'])
    df = pd.DataFrame(data).astype(str)
    return df


def interface_logon(usr_list):
    col1, col2, col3, col4, col5 = st.columns([0.9,0.9,1.4,0.9,0.9], vertical_alignment="bottom")
    col3.html(f"""
    <div style="text-align: left;">
        <img src="https://i.ibb.co/Z8851TY/logo-sesma-chopped.png" style="width: 50px; height: 50px; opacity: 0.8;">
    </div>
    """)
    col3.header("Acesso restrito", anchor=False)
    with col3.form(clear_on_submit=False, enter_to_submit=False, key="form_logon"):
        st.write("")
        st.text_input("Servidor", max_chars=12, key="input_usr")
        st.text_input("Senha", max_chars=20, key="input_psw", type="password")
        st.write("")
        c1, c2, c3, c4 = st.columns(4, vertical_alignment="bottom")
        if c4.form_submit_button("Entrar", type="primary", use_container_width=True):
            usr_name = st.session_state.input_usr
            usr_psw = st.session_state.input_psw
            if len(usr_name) > 4 and len(usr_psw) > 4:
                # verificar se usuário existe
                for selt in usr_list["Salt"]:
                    row_index = usr_list[usr_list["Salt"] == selt].index[0]
                    if usr_name == usr_list.loc[row_index, "Name"]:
                        psw_stored = usr_list.loc[row_index, "Password"]
                        psw_salted = hash_with_salt(selt, usr_psw)
                        usr_privileges = usr_list.loc[row_index, "Privileges"]
                        if psw_salted == psw_stored:
                            signed_cookie = create_auth_cookie(usr_name, psw_salted, usr_privileges)
                            set_cookie(f"usr_sess_{st.session_state.my_ip}", signed_cookie, max_age=900)
                            st.session_state.error = "None"
                            break
                if st.session_state.error == "None":
                    st.session_state.error = ""
                    streamlit_js_eval(js_expressions="parent.window.location.reload()")
                else:
                    st.session_state.error = "Usuário ou senha não existe."
            else:
                st.session_state.error = "Usuário ou senha inválidos."
        if len(st.session_state.error) > 1:
            st.write(f":red-background[{st.session_state.error}]")


def interface_cadastro(usr_list):
    col1, col2, col3, col4, col5 = st.columns([0.9,0.9,1.4,0.9,0.9], vertical_alignment="bottom")
    col3.header("Cadastrar Servidor", anchor=False)
    with col3.form(clear_on_submit=False, enter_to_submit=False, key="form_logon"):
        st.write("")
        st.text_input("Servidor", max_chars=12, key="input_usr")
        st.selectbox("Privilégio", options={"adm", "normal", "leitor", "secretario", "dvse"}, key="input_privileges", index=2)
        st.text_input("Senha", max_chars=20, key="input_psw", type="password")
        st.text_input("Repita a senha", max_chars=20, key="double_input_psw", type="password")
        st.write("")
        c1, c2, c3 = st.columns(3, vertical_alignment="bottom")
        if c2.form_submit_button("Carregar DB", use_container_width=True):
            load_auth_usr.clear()
            st.session_state.usr_list = None # está no main.py
            st.rerun()

        if c3.form_submit_button("Cadastrar", type="primary", use_container_width=True):
            usr_name = st.session_state.input_usr
            usr_psw1 = st.session_state.input_psw
            usr_psw2 = st.session_state.double_input_psw
            input_privileges = st.session_state.input_privileges

            if len(usr_name) > 4 and len(usr_psw1) > 4 and len(usr_psw2) > 4:
                if usr_psw1 == usr_psw2:
                    # verificar se usuário existe  
                    if usr_name in usr_list.values: # usr_name in usr_list.values:
                        st.warning(f"O usuário {usr_name} já existe.")
                    else:
                        last_row = usr_list.index[-1] if not usr_list.empty else None
                        salt = generate_salt()
                        values_salted = [salt, usr_name, hash_with_salt(salt, usr_psw1), input_privileges]
                        print(f"last_row: {last_row}")
                        if last_row != None:
                            worksheet = get_worksheet(3, st.secrets['sh_keys']['geral_major'])
                            #if last_row == 0:
                            range_div = f"A{last_row+3}:D{last_row+3}"
                            #elif last_row > 0:
                                #range_div = f"A{last_row+2}:D{last_row+2}"
                            worksheet.update(range_div, [values_salted])
                            st.success("Salvo com sucesso.")
                            load_auth_usr.clear()
                            st.session_state.usr_list = None # está no main.py
                            st.rerun()
                            #streamlit_js_eval(js_expressions="parent.window.location.reload()")
                        else:
                            # worksheet = get_worksheet(3, st.secrets['sh_keys']['geral_major'])
                            # range_div = "A2:D2"
                            # worksheet.update(range_div, [values_salted])
                            # st.success("Salvo com sucesso.")
                            # load_auth_usr.clear()
                            # streamlit_js_eval(js_expressions="parent.window.location.reload()")
                            st.error("Erro ao carregar a base.")
                            
                else:
                    st.error("Senhas inequivalentes.")
            else:
                st.error("Usuário ou senha inválidos")


def interface_senha(usr_list, usr):
    col1, col2, col3, col4, col5 = st.columns([0.9,0.9,1.4,0.9,0.9], vertical_alignment="bottom")
    col3.header("Redefinir senha", anchor=False)
    with col3.form(clear_on_submit=False, enter_to_submit=False, key="form_psw"):
        st.write("")
        st.text_input("Nova senha", max_chars=20, key="input_psw1", type="password")
        st.text_input("Repita a senha", max_chars=20, key="input_psw2", type="password")
        st.write("")
        c1, c2 = st.columns(2, vertical_alignment="bottom")
        if c2.form_submit_button("Redefinir senha", type="primary", use_container_width=True):
            input_psw1 = st.session_state.input_psw1
            input_psw2 = st.session_state.input_psw2

            if len(input_psw1) > 4 and len(input_psw2) > 4:
                if input_psw1 == input_psw2:
                    for user in usr_list["Name"]:
                        if user == usr:
                            row_index = usr_list[usr_list["Name"] == user].index[0]
                            worksheet = get_worksheet(3, st.secrets['sh_keys']['geral_major'])
                            salted_psw = hash_with_salt(usr_list.loc[row_index, "Salt"], input_psw1)
                            worksheet.update_acell(f"C{row_index+2}", salted_psw)
                            st.success("Senha alterada com sucesso. Saindo...")
                            time.sleep(3)
                            delete_cookie(f"usr_sess_{st.session_state.my_ip}")
                            load_auth_usr.clear()
                            st.session_state.usr_list = None # está no main.py
                            streamlit_js_eval(js_expressions="parent.window.location.reload()")
                            break
                    else:
                        st.error("Usuário não encontrado.")
                else:
                    st.error("As senhas precisam ser iguais.")
            else:
                st.error("A senha tem o mínimo de 5 caracteres.")

