import openai
import asyncio
import streamlit as st

async def corrigir_texto_async(texto: str) -> str:
    """
    Corrige ortograficamente um texto desformatado, usando API da Akash de forma assíncrona.

    Parâmetros:
    - texto: Texto com espaços duplicados, quebras de linha e erros ortográficos.
    - api_key: Chave da API da Akash.

    Retorna:
    - Texto corrigido e formatado em um único parágrafo.
    """

    api_key = st.secrets['dany']['akash_api']

    try:
        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url="https://chatapi.akash.network/api/v1"
        )

        prompt = (
            # "Corrija apenas a ortografia do texto a seguir, "
            # "remova espaços duplicados e quebras de linha, "
            # "reescreva como um único parágrafo, sem quebras de linha, "
            # "retornando apenas o texto corrigido."
            # "Não reescreva nem resuma, apenas normalize e corrija erros ortográficos:\n\n"
            f"\"\"\"\n{texto}\n\"\"\""
        )

        response = await client.chat.completions.create(
            model="Meta-Llama-3-2-3B-Instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=5000
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"[Erro ao processar o texto]: {str(e)}"
    

# if __name__ == "__main__":
#     texto = """
# drogaria. * Dispensação de medicamentos não sujeitos a controle especial;

# * Dispensação de medicamentos sujeitos a controle especial (Portaria 344/98); incluindo retinóides de uso sistêmico.

# * Comercialização de cosméticos, perfumes, produtos de higiene, correlatos de uso do público em geral e alimentos permitidos pela lei estadual nº8593/2018;

# * AFE Nº: 0.57113-2

# * CNAE: 47.71-7-01
#     """
#     chave = st.secrets['dany']['akash_api']

#     # Rodar a função assíncrona no ambiente síncrono
#     texto_corrigido = asyncio.run(corrigir_texto_async(texto))
#     print(texto_corrigido)