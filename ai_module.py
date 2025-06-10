import openai
import streamlit as st

# --- PASSO 1: Inicializar o CLIENTE SÍNCRONO e armazená-lo na sessão ---
# Isso garante que o cliente seja criado apenas uma vez, evitando múltiplas conexões.
if 'akash_client' not in st.session_state:
    try:
        api_key = st.secrets['dany']['akash_api']
        # Usando o cliente SÍNCRONO, como no exemplo da Akash.
        st.session_state.akash_client = openai.OpenAI(
            api_key=api_key,
            base_url="https://chatapi.akash.network/api/v1",
            timeout=45.0
        )
        print("INFO: Cliente SÍNCRONO da Akash inicializado e armazenado na sessão.")
    except Exception as e:
        st.session_state.akash_client = None
        st.error(f"Falha ao inicializar o cliente da API: {e}")

# --- PASSO 2: Criar a função de correção SÍNCRONA ---
# Esta função é agora uma função Python normal, sem async/await.
def corrigir_texto_sync(client: openai.OpenAI, texto: str) -> str:
    """
    Corrige texto usando uma chamada de API síncrona (bloqueante).
    """
    if not client:
        return "[Erro: Cliente da API não foi inicializado corretamente.]"
    
    try:
        prompt = (
            f"Você é um robô que recebe um texto e o formata da seguinte forma: "
            f"remove quebras de linha e espaços duplicados, organiza todo o texto num único parágrafo sem quebras de linha,"
            f"e sem acrescentar palavra nova. Retorne como resposta somente o texto formatado, mais nada. O texto: "
            f"\"\"\"\n{texto}\n\"\"\""
        )

        # Chamada de API síncrona e bloqueante. O script espera aqui.
        response = client.chat.completions.create(
            model="Meta-Llama-3-3-70B-Instruct", # Modelo do exemplo, parece ser estável.
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=7000 # Otimizado para um valor razoável
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        # A exceção agora será mais clara (ex: TimeoutError, APIError).
        return f"[Erro ao processar o texto]: {str(e)}"