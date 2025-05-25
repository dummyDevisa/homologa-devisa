import openai
import asyncio
import streamlit as st
from typing import AsyncGenerator

# Erro na API: Error code: 401 - {'error': {'message': "team not allowed to access model. This team can "
# "only access models=['DeepSeek-R1-Distill-Qwen-32B', 'Meta-Llama-3-2-3B-Instruct', 'DeepSeek-R1', 'DeepSeek-R1-Distill-Qwen-14B', "
# "'BAAI-bge-large-en-v1-5', 'Meta-Llama-3-1-8B-Instruct-FP8', 'DeepSeek-R1-Distill-Llama-70B', 'Meta-Llama-3-3-70B-Instruct', "
# "'Meta-Llama-4-Maverick-17B-128E-Instruct-FP8']. Tried to access Meta-Llama-3-8B-Instruct", 'type': 'team_model_access_denied', 
# 'param': 'model', 'code': '401'}}

options = ["DeepSeek-R1-Distill-Qwen-32B", "Meta-Llama-3-2-3B-Instruct", "DeepSeek-R1", "DeepSeek-R1-Distill-Qwen-14B", 
           "BAAI-bge-large-en-v1-5", "Meta-Llama-3-1-8B-Instruct-FP8", "DeepSeek-R1-Distill-Llama-70B", "Meta-Llama-3-3-70B-Instruct", 
           "Meta-Llama-4-Maverick-17B-128E-Instruct-FP8"]

selection = st.pills("Modelos", options, selection_mode="single", default="Meta-Llama-4-Maverick-17B-128E-Instruct-FP8")

# --- Configuração da API ---
# Tenta carregar a chave da API Akash primeiro
try:
    api_key = st.secrets['dany']['akash_api']
    base_url = "https://chatapi.akash.network/api/v1"
    # Modelo disponível na Akash (ajuste se necessário)
    # Meta-Llama-3-2-3B-Instruct
    # DeepSeek-R1-Distill-Qwen-32B (comentários e tools)
    # Meta-Llama-3-3-70B-Instruct
    MODEL_NAME = selection
    # MODEL_NAME = "gpt-3.5-turbo" # Use um modelo comum como fallback ou ajuste
    print(f"INFO: Usando API Akash com base_url: {base_url}")
except KeyError:
    # Se a chave Akash não for encontrada, tenta a chave OpenAI padrão
    try:
        api_key = st.secrets['dany']['openai_api']
        base_url = None # Usa o padrão da OpenAI
        MODEL_NAME = "gpt-3.5-turbo" # Modelo padrão da OpenAI
        print("INFO: Chave Akash não encontrada. Usando API OpenAI padrão.")
    except KeyError:
        st.error("Erro: Nenhuma chave de API encontrada em st.secrets. Configure 'akash_api' ou 'openai_api' em .streamlit/secrets.toml")
        st.stop()
        api_key = None # Para evitar erros posteriores se st.stop() falhar por algum motivo
        base_url = None
        MODEL_NAME = None

# Instancia o cliente Async OpenAI (só precisa ser feito uma vez)
# Verifica se api_key foi definida antes de criar o cliente
if api_key:
    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url=base_url # Será None se estiver usando a API OpenAI padrão
    )
else:
    # O st.stop() deveria ter encerrado, mas por segurança:
    client = None
    st.error("Cliente OpenAI não pôde ser inicializado devido à falta de API key.")
    st.stop()


async def get_chat_response_async(messages: list) -> AsyncGenerator[str, None]:
    """
    Obtém a resposta do chatbot de forma assíncrona e em streaming.

    Parâmetros:
    - messages: Lista de mensagens da conversa (histórico).

    Retorna:
    - Um gerador assíncrono que produz pedaços (chunks) da resposta.
    """
    if not client or not MODEL_NAME:
         yield "[Erro: Cliente ou modelo não configurado]"
         return

    try:
        # Cria a chamada para a API com streaming habilitado
        stream = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7, # Ajuste conforme necessário
            max_tokens=1024, # Ajuste conforme necessário
            stream=True,
        )

        # Itera sobre os chunks recebidos da API
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content is not None:
                yield content # Retorna cada pedaço de texto

    except Exception as e:
        print(f"Erro na API: {e}") # Logar o erro no console para depuração
        yield f"[Erro ao comunicar com a API: {str(e)}]"

# --- Interface Streamlit ---

# st.set_page_config(page_title="Chatbot com Memória", layout="wide")
st.title("🧪 Chatbot com Memória (Sessão)")
st.caption(f"Usando modelo: {MODEL_NAME} via {'Akash' if base_url else 'OpenAI'}")

# Inicializa o histórico da conversa na session state se não existir
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Olá! Como posso te ajudar hoje?"}]

# Exibe as mensagens do histórico
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Campo de entrada para o usuário
if prompt := st.chat_input("Digite sua mensagem..."):
    # Adiciona a mensagem do usuário ao histórico e exibe
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepara para receber e exibir a resposta do assistente em streaming
    with st.chat_message("assistant"):
        # Usa st.write_stream para exibir os chunks da resposta
        # Passa a função geradora assíncrona diretamente
        # É crucial passar o histórico COMPLETO para o modelo ter contexto
        response_stream = get_chat_response_async(st.session_state.messages)

        # st.write_stream lida com a execução assíncrona e exibe os chunks
        # Ele também retorna a resposta completa quando o stream termina
        full_response = st.write_stream(response_stream)

    # Adiciona a resposta completa do assistente ao histórico da sessão
    # Isso garante que a memória seja mantida para a próxima interação
    if full_response: # Garante que não adicionamos uma resposta vazia ou de erro mal formatado
       st.session_state.messages.append({"role": "assistant", "content": full_response})

    # Nota: O Streamlit automaticamente re-executa o script após o st.chat_input,
    # o que redesenha a interface com a nova mensagem do usuário e a resposta do assistente.
    # O loop 'for message in st.session_state.messages:' no início garante que
    # todo o histórico atualizado seja exibido a cada interação.

# Para rodar: streamlit run app.py