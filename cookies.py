import streamlit as st
from itsdangerous import URLSafeTimedSerializer
import extra_streamlit_components as stx
# import hashlib
# import os

# Criação do gerenciador de cookies
def create_cookie_manager():
    return stx.CookieManager()

cookie_manager = create_cookie_manager()

# Inicialização do serializer para assinar cookies
serializer = URLSafeTimedSerializer(st.secrets['apps_psw']['salt_cookie'])

# Função para assinar dados
def sign_data(data):
    return serializer.dumps(data)

# Função para verificar e carregar dados assinados
def verify_data(signed_data):
    try:
        return serializer.loads(signed_data)
    except Exception as e:
        return None

# Função para definir um cookie
def set_cookie(name, value, max_age=900):
    try:
        cookie_manager.set(
            cookie=name,
            val=value,
            path="/",
            max_age=max_age,
            domain="sysdevisa.streamlit.app",  # Para Streamlit Cloud, mantenha None ou o domínio do app
            secure=True,  # Use True em produção
            same_site="Lax"  # Altere para "Strict" se necessário
        )
        # st.success(f"Cookie '{name}' definido com sucesso!")
    except Exception as e:
        st.error(f"Erro ao definir cookie: {e}")

# Função para obter um cookie
def get_cookie(name):
    try:
        return cookie_manager.get(cookie=name)
    except Exception as e:
        st.error(f"Erro em get_cookie: {e}")
        return None

# Função para deletar um cookie
def delete_cookie(name):
    try:
        cookie_manager.delete(cookie=name)
    except Exception as e:
        st.error(f"Erro em delete_cookie: {e}")
        return None

# Função para criar um cookie com múltiplos valores
def create_auth_cookie(username, password, privilege):
    cookie_data = {
        "username": username,
        "password": password,
        "privilege": privilege,
    }
    return sign_data(cookie_data)

# Função para verificar autenticação na sessão
def verify_session(cookie_name):
    # cookie_name = "dvs_usr_sess__"
    session_cookie = get_cookie(cookie_name)
    if session_cookie:
        data = verify_data(session_cookie)
        if data:
            #st.success("Sessão autenticada!")
            return data
        else:
            #t.error("Sessão inválida. Faça login novamente.")
            delete_cookie(cookie_name)
    else:
        #st.warning("Nenhuma sessão ativa.")
        return None
    return None


