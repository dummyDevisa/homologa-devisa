import streamlit as st 
import fitz  # PyMuPDF
from PIL import Image
# from PIL import Image, ImageDraw, ImageFont
# import qrcode
# import tempfile
# import os
import json, time
import segno
import io, re
import zipfile, tempfile
import hashlib, base64
from datetime import datetime, timezone, timedelta
from pyzbar.pyzbar import decode
import pandas as pd
from load_functions import get_worksheet, get_current_datetime, email_aprojeto

main_c1, main_c2, mainc3 = st.columns([0.5, 2, 0.5])

with main_c2:
    st.html("<style>[data-testid='stHeaderActionElements'] {display: none;}</style>")

    if 'off_btn_processo_chancela' not in st.session_state:
    
        # botões
        st.session_state.off_btn_processo_chancela = False
        st.session_state.off_btn_upload = True

        # campos
        st.session_state.ano = ''
        st.session_state.proc = ''
        st.session_state.cod_solicitacao = ''
        st.session_state.dt_solicitacao = ''
        st.session_state.dt_atendimento = ''
        st.session_state.natjur = ''
        st.session_state.dam = ''
        st.session_state.cpf_cnpj = ''
        st.session_state.nome = ''
        st.session_state.email1 = ''
        st.session_state.email2 = ''
        st.session_state.obs = ''

        # diversos
        st.session_state.load_qrcode = False
        st.session_state.df_encontrado = pd.DataFrame()
        st.session_state.json_hash = None
        st.session_state.zip_data = None
        st.session_state.is_email_sended_projeto = False
        st.session_state.certificador = {}
        st.session_state.rerun_duplo = False
        

    # Constante de conversão: 1 mm ≈ 2.83465 pt
    MM_TO_PT = 2.83465

    # Série A (em mm)
    STANDARD_A = {
        'A0': (841, 1189),
        'A1': (594, 841),
        'A2': (420, 594),
        'A3': (297, 420),
        'A4': (210, 297),
        'A5': (148, 210),
        'A6': (105, 148),
        'A7': (74, 105),
        'A8': (52, 74),
        'A9': (37, 52),
        'A10': (26, 37)
    }

    # Série B (em mm)
    STANDARD_B = {
        'B0': (1000, 1414),
        'B1': (707, 1000),
        'B2': (500, 707),
        'B3': (353, 500),
        'B4': (250, 353),
        'B5': (176, 250),
        'B6': (125, 176),
        'B7': (88, 125),
        'B8': (62, 88),
        'B9': (44, 62),
        'B10': (31, 44)
    }

    # Série C – geralmente usada para envelopes (ISO 269)
    STANDARD_C = {
        'C0': (917, 1297),
        'C1': (648, 917),
        'C2': (458, 648),
        'C3': (324, 458),
        'C4': (229, 324),
        'C5': (162, 229),
        'C6': (114, 162),
        'C7': (81, 114),
        'C8': (57, 81),
        'C9': (40, 57),
        'C10': (28, 40)
    }

    # Série D – conforme algumas referências da norma ABNT NBR 14808
    STANDARD_D = {
        'D0': (780, 1090),
        'D1': (545, 780),
        'D2': (385, 545),
        'D3': (272, 385),
        'D4': (192, 272),
        'D5': (136, 192),
        'D6': (96, 136),
        'D7': (68, 96),
        'D8': (48, 68),
        'D9': (33, 48),
        'D10': (23, 33)
    }

    # Série E – valores adotados em referências para formatos de envelopes alternativos
    STANDARD_E = {
        'E0': (635, 935),
        'E1': (465, 635),
        'E2': (335, 465),
        'E3': (235, 335),
        'E4': (165, 235),
        'E5': (115, 165),
        'E6': (80, 115),
        'E7': (55, 80),
        'E8': (40, 55),
        'E9': (28, 40),
        'E10': (20, 28)
    }

    # Converte as dimensões de mm para pontos e unifica em um único dicionário
    def convert_dict(mm_dict):
        return { key: (round(dim[0] * MM_TO_PT, 2), round(dim[1] * MM_TO_PT, 2)) for key, dim in mm_dict.items() }

    STANDARD_A_PT = convert_dict(STANDARD_A)
    STANDARD_B_PT = convert_dict(STANDARD_B)
    STANDARD_C_PT = convert_dict(STANDARD_C)
    STANDARD_D_PT = convert_dict(STANDARD_D)
    STANDARD_E_PT = convert_dict(STANDARD_E)

    STANDARD_PAPERS = { **STANDARD_A_PT, **STANDARD_B_PT, **STANDARD_C_PT, **STANDARD_D_PT, **STANDARD_E_PT }

    def determine_paper_type(width_pt, height_pt, tolerance=20):
        """
        Determina o tipo de papel (ex.: 'A4', 'C2', 'D1', 'E5', etc.) comparando as dimensões fornecidas
        com os padrões. Usa uma tolerância (em pontos) para lidar com desvios.
        Considera também a possibilidade de o papel estar rotacionado.
        Retorna o nome do papel se encontrado ou None se não identificar.
        """
        for paper, (std_width, std_height) in STANDARD_PAPERS.items():
            if (abs(width_pt - std_width) <= tolerance and abs(height_pt - std_height) <= tolerance) or \
            (abs(width_pt - std_height) <= tolerance and abs(height_pt - std_width) <= tolerance):
                return paper
        return None

    def calculate_positions(paper_width, paper_height, safety_margin=10):
        """
        Calcula as posições dos elementos com base no tamanho do papel:
        - A hash: posicionada no centro vertical da margem esquerda (com rotação aplicada).
        - A logo: centralizada na página.
        - O texto com QR code: posicionado no canto inferior direito.
        O safety_margin garante que os elementos não fiquem muito próximos das bordas.
        Retorna um dicionário com as coordenadas.
        """
        positions = {}
        # Origem no canto inferior esquerdo: (0, 0), topo direito: (paper_width, paper_height)

        # Hash: posicionada na margem esquerda, centralizada verticalmente.
        positions['hash'] = {
            'x': safety_margin,
            'y': paper_height / 2,
            'rotation': -90  # Rotacionada 90º no sentido horário
        }
        
        # Logo: centralizada na página.
        positions['logo'] = {
            'x': paper_width / 2,
            'y': paper_height / 2
        }
        
        # Texto com QR code: posicionado no canto inferior direito (considerando a margem de segurança)
        positions['text_qrcode'] = {
            'x': paper_width - safety_margin,
            'y': safety_margin
        }
        
        return positions

    def data_hora_brasilia():
        fuso_brasilia = timezone(timedelta(hours=-3))
        agora = datetime.now(fuso_brasilia)
        data = agora.strftime('%d/%m/%Y')
        hora = agora.strftime('%H:%M')
        return data, hora

    def gerar_hash_sha256(texto):
        return hashlib.sha256(texto.encode()).hexdigest()

    def hash_para_codigo(hash_str):
        hash_bytes = bytes.fromhex(hash_str)
        codigo = base64.urlsafe_b64encode(hash_bytes).decode('utf-8')
        codigo = codigo[:6].lower()
        return codigo
    
    def get_factor(current_area, reference_value):
        """
        Calcula o valor escalado para um elemento com base na área do papel atual.
        
        Para o papel de referência A10 (26 x 37 mm, ou ~73.70 x 104.96 pts, área ≈7733.31 pts²):
        - O texto (hash e ao lado do QR) tem 1 pt;
        - A logo (chancela) tem 25 pt (ou seja, 25x25);
        - O QR code tem 13 pt (13x13).
        
        A escala é calculada como a razão entre as raízes quadradas das áreas.
        """
        MM_TO_PT = 2.83465
        A10_width = 26 * MM_TO_PT      # ≈ 73.70 pts
        A10_height = 37 * MM_TO_PT     # ≈ 104.96 pts
        A10_area = A10_width * A10_height  # ≈ 7733.31 pts²

        scale_factor = (current_area / A10_area) ** 0.5
        return reference_value * scale_factor

    @st.cache_data(ttl=600, show_spinner="Aguarde...")
    def load_div_df():   
        worksheet = get_worksheet(1, st.secrets['sh_keys']['geral_major'])
        data = worksheet.get_values()
        df = pd.DataFrame(data[1:], columns=data[0])  # Define os nomes das colunas manualmente

        # Filtrar onde 'Tipo Processo' contém 'Projeto Arquitetônico' e 'Status' é 'Deferido'
        df_filtered = df[(df['Tipo Processo'].str.contains('Projeto Arquitetônico', na=False)) & (df['Status'] == 'Deferido')]
        return df_filtered

    def procurar_processo(df, proc, ano):
        """Busca um processo na coluna 'GDOC' formatado como 'proc/YY'."""
        yy = str(ano)[-2:]  # Extrai os dois últimos dígitos do ano
        busca = f"{proc}/{yy}"  # Formata como 'proc/YY'
        resultado = df[df['GDOC'] == busca]
        return resultado

    def limpar_tudo(msg):
        st.session_state.cod_solicitacao = ''
        st.session_state.dt_solicitacao = ''
        st.session_state.dt_atendimento = ''
        st.session_state.natjur = ''
        st.session_state.dam = ''
        st.session_state.cpf_cnpj = ''
        st.session_state.nome = ''
        st.session_state.email1 = ''
        st.session_state.email2 = ''
        st.session_state.load_qrcode = False
        st.session_state.df_encontrado = pd.DataFrame()
        st.session_state.json_hash = None
        st.session_state.obs = ''
        st.session_state.zip_data = None
        # timz = get_current_datetime()
        # print(f"limpeza executada em {timz}")
        
        if msg:
            st.toast(f"{msg}")


    def carregar_formulario(df):
        st.session_state.cod_solicitacao = df.iloc[0]['Código Solicitação']
        st.session_state.dt_solicitacao = df.iloc[0]['Data Atendimento']
        st.session_state.dt_atendimento = df.iloc[0]['Data Entrega']
        st.session_state.natjur = df.iloc[0]['Complemento Valor']
        st.session_state.dam = df.iloc[0]['Valor Manual']
        st.session_state.cpf_cnpj = df.iloc[0]['CPF / CNPJ']
        st.session_state.nome = df.iloc[0]['Razão Social']
        st.session_state.email1 = df.iloc[0]['E-mail']
        st.session_state.email2 = df.iloc[0]['E-mail CC']
        st.session_state.obs = df.iloc[0]['Obs Aprovação']

        #
        # certificadores ########################## acrescentar os nomes e cargos aqui ###############################
        #

        match st.session_state.auth_user:
            case 'laurodvse':
                st.session_state.certificador = {'usuario':'Lauro Cesar Nascimento', 'cargo': 'Arquiteta/Téc. em Vigilância Sanitária'}
            case 'tainadvse':
                st.session_state.certificador = {'usuario':'Tainá Marçal dos Santos Menezes', 'cargo': 'Arquiteta/Téc. em Vigilância Sanitária'}
            case 'tancredodvse':
                st.session_state.certificador = {'usuario':'Tancredo Miranda', 'cargo': 'Arquiteto/Téc. em Vigilância Sanitária'}
            case 'raysadvse':
                st.session_state.certificador = {'usuario':'Raysa Ribeiro da Silva', 'cargo': 'Chefe de Divisão'}
            case _:
                st.session_state.certificador = {'usuario':'John Doe', 'cargo': 'XXX nº 0000'}


    # if st.session_state.is_email_sended_projeto:
    #     if st.session_state.email2 != '':
    #         st.toast(f":green[**E-mail enviado a {st.session_state.email1} e {st.session_state.email2}**]")
    #     else:
    #         st.toast(f":green[**E-mail enviado a {st.session_state.email1}**]")
    #     st.session_state.is_email_sended_projeto = False

    try:
        df = load_div_df()
        st.header("Chancela e entrega de documentos - DVSE", anchor=False)
        
    except Exception as e:
        st.error(f"Houve um erro: {e}")
    else:
        st.fragment()
        def qr_code():
            with st.container(border=True):
                with st.spinner("Aguarde..."):
                    st.write("#### Certificação e chancela")
                    load_container_btn = False
                    c1, c2 = st.columns(2, vertical_alignment='top')
                    uploaded_qr_pdf = c1.file_uploader("**1.** Selecione o Parecer Técnico **já certificado**", type="pdf", accept_multiple_files=False)
                    
                    if uploaded_qr_pdf:
                        qr_pdf_bytes = uploaded_qr_pdf.read()
                        doc = fitz.open(stream=qr_pdf_bytes, filetype="pdf")
                        page = doc[0]
                        image_list = page.get_images(full=True)
                        qr_url = None
                        
                        for img_info in image_list:
                            xref = img_info[0]
                            base_image = doc.extract_image(xref)
                            pil_image = Image.open(io.BytesIO(base_image["image"]))
                            decoded_objects = decode(pil_image)
                            
                            for obj in decoded_objects:
                                if obj.type == 'QRCODE':
                                    qr_url = obj.data.decode("utf-8")
                                    break
                            if qr_url:
                                break
                        
                        doc.close()
                        
                        if not qr_url:
                            c1.error("A certificação não foi encontrada. Tem certeza que esse documento é o correto?")
                            uploaded_files = None
                        else:
                            uploaded_files = c2.file_uploader("**2.** Selecione as pranchas PDF para chancela", type="pdf", accept_multiple_files=True, help="")

                            #
                            #  VERIFICA O TAMANHO DOS ARQUIVOS, PARA NÃO EXCEDER O TAMANHO MÁXIMO DE 20MB
                            #
                                
                        def gerar_watermark(file_hash, n_prancha, total_prancha):
                            codigo_hash = hash_para_codigo(file_hash)
                            data, hora = data_hora_brasilia()

                            # Usar fonte padrão do PDF
                            font = fitz.Font("cobo")
                            
                            auth_user = st.session_state.certificador

                            text_lines = [
                                "Documento certificado pela Divisão de Engenharia - DVSE/DEVISA/SESMA/PMB",
                                f"Prancha {n_prancha} de {total_prancha}, referente ao processo GDOC nº {st.session_state.proc}/{st.session_state.ano}",
                                "Verifique o vínculo processual pelo QR Code ao lado",
                                f"Data: {data}; Hora: {hora}; Hash do arquivo: {codigo_hash}",
                                f"Certificador(a): {auth_user['usuario']}, {auth_user['cargo']}",
                            ]

                            # Configurações de layout
                            line_spacing = 4  # Espaçamento entre linhas
                            font_size = 10
                            spacing = 2  # Espaço entre elementos
                            chancela_width = 60  # Largura da chancela
                            qr_size = 80  # Tamanho do QR code

                            # Calcular larguras máximas
                            max_text_width = max(font.text_length(line, fontsize=font_size) for line in text_lines)
                            
                            # Dimensões totais
                            total_width = chancela_width + max_text_width + qr_size + 2 * spacing
                            text_block_height = (font_size + line_spacing) * len(text_lines) - line_spacing
                            
                            return {
                                "text_lines": text_lines,
                                "font": font,
                                "font_size": font_size,
                                "line_spacing": line_spacing,
                                "spacing": spacing,
                                "chancela_width": chancela_width,
                                "qr_size": qr_size,
                                "total_width": total_width,
                                "text_block_height": text_block_height,
                                "codigo_hash": codigo_hash,
                                "max_text_width": max_text_width,
                            }

                        # [...] (código anterior mantido até a seção de processamento dos arquivos)
                        
                        

                        tamanho_total_bytes = 0
                        if uploaded_files:
                            tamanho_total_bytes += uploaded_qr_pdf.size
                            tamanho_total_bytes += sum(f.size for f in uploaded_files)

                            # checagem = f"Tamanho total dos arquivos: {(tamanho_total_bytes / (1024*1024))*1.05:.2f} MB"
                            size_preview = (tamanho_total_bytes / (1024*1024))*1.05

                            with st.spinner("Processando..."):
                                hashes_antes = {}
                                hashes_depois = {}
                                total_prancha = len(uploaded_files)  # Total de pranchas
                                
                                processed_files = []

                                # --- Loop de processamento dos arquivos PDF ---
                                for i, uploaded_file in enumerate(uploaded_files):
                                    n_prancha = i + 1
                                    # Garante que o ponteiro do arquivo esteja no início
                                    uploaded_file.seek(0) 
                                    pdf_bytes = uploaded_file.read()
                                    hash_pdf = hashlib.sha256(pdf_bytes).hexdigest()
                                    hashes_antes[uploaded_file.name] = hash_pdf

                                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                                    # Processa apenas a primeira página (ou itere por 'doc' se precisar de todas)
                                    if len(doc) > 0:
                                        page = doc[0]

                                        # === Extração das dimensões reais da página (em pontos) ===
                                        page_width = page.rect.width
                                        page_height = page.rect.height
                                        print(f"page_width: {page_width}, page_height: {page_height}")

                                        if page_width > page_height:
                                            page.rotation
                                            page_width, page_height = page_height, page_width

                                        # Detecta o tipo de papel usando as dimensões e uma tolerância de 20 pts
                                        paper_type = determine_paper_type(page_width, page_height, tolerance=20)
                                        if paper_type:
                                            print(f"({i}) Tipo de papel detectado: {paper_type}")
                                        else:
                                            print(f"({i}) Tipo de papel não identificado. Usando dimensões informadas.")

                                        # === Escalonamento inteligente com base na área do papel ===
                                        current_area = page_width * page_height

                                        # Tamanhos base para A10:
                                        #   - texto (hash e texto ao lado do QR): 1 pt
                                        #   - logo (chancela): 25 pt
                                        #   - QR code: 13 pt
                                        scaling_text = get_factor(current_area, 1)    # Para o texto
                                        scaling_logo_target = get_factor(current_area, 25) # Tamanho desejado para a logo
                                        scaling_qr   = get_factor(current_area, 9)     # Para o QR code

                                        print(f"scaling_text: {scaling_text}")

                                        # Margem geral (usada no canto inferior direito e borda esquerda)
                                        margin = get_factor(current_area, 2)
                                        # Espaçamento ENTRE as linhas de texto (menor que o anterior para reduzir espaço)
                                        interline_spacing = get_factor(current_area, 1) # Reduzido de 3 para 1
                                        # Espaço horizontal entre texto e QR code
                                        horizontal_spacing_qr_text = get_factor(current_area, 1) # Um valor para o espaço horizontal

                                        # === QR Code e Texto (Bloco no Canto Inferior Direito) ===
                                        
                                        # --- QR Code ---
                                        # Coordenadas do canto inferior direito do QR Code
                                        qr_bottom_right_x = page_width - margin
                                        qr_bottom_right_y = page_height - margin
                                        # Coordenadas do retângulo para inserir a imagem (x0, y0, x1, y1)
                                        qr_rect = fitz.Rect(
                                            qr_bottom_right_x - scaling_qr, # x0 = left
                                            qr_bottom_right_y - scaling_qr, # y0 = top
                                            qr_bottom_right_x,              # x1 = right
                                            qr_bottom_right_y               # y1 = bottom
                                        )

                                        # Geração do QR Code em memória
                                        qr = segno.make(f"{qr_url}{hash_pdf}", error='h') # Inclui o hash na URL
                                        buffer = io.BytesIO()
                                        # Define uma escala base alta e deixa o fitz redimensionar para o Rect
                                        # Ou calcula a escala necessária: target_pixels = scaling_qr * dpi / 72 (e.g., dpi=300)
                                        # Para simplificar, usamos scale=5 (exemplo) e deixamos fitz ajustar
                                        qr.save(buffer, kind='png', scale=1, border=1) 
                                        buffer.seek(0)
                                        page.insert_image(
                                            qr_rect,
                                            stream=buffer.read()
                                        )

                                        # --- Texto à esquerda do QR Code ---
                                        watermark_info = gerar_watermark(hash_pdf, n_prancha, total_prancha)
                                        text_lines = watermark_info['text_lines']
                                        font = fitz.Font("cobo") # Certifique-se que 'cobo' está disponível
                                        fontsize_text = scaling_text

                                        # # Calcula a largura máxima de cada linha com o tamanho escalado
                                        # max_text_width = 0
                                        # if text_lines:
                                        #     max_text_width = max(font.text_length(line, fontsize=fontsize_text) for line in text_lines)
                                        
                                        # # Calcula a altura total do bloco de texto
                                        # # Altura = (Num Linhas * Altura Fonte) + (Num Espaços * Espaço Entre Linhas)
                                        # text_block_height = (len(text_lines) * fontsize_text) + (max(0, len(text_lines) - 1) * interline_spacing)

                                        # Posição X: o texto termina à esquerda do QR Code, considerando o espaçamento
                                        text_block_right_x = qr_rect.x0 - horizontal_spacing_qr_text

                                        # Define a posição X à direita do bloco de texto (lado direito do texto)
                                        text_block_right_x = qr_rect.x0 - horizontal_spacing_qr_text

                                        # A linha de base da última linha alinha com a borda inferior do QR
                                        last_line_baseline_y = qr_bottom_right_y

                                        # ===============================
                                        # 1. Desenha os fundos (caixas) sem borda em um objeto Shape
                                        # ===============================
                                        bg_shape = page.new_shape()

                                        for idx, line in enumerate(reversed(text_lines)):
                                            # Calcula a largura da linha atual
                                            line_width = font.text_length(line, fontsize=fontsize_text)
                                            
                                            # Calcula a linha de base para essa linha: a última linha fica em last_line_baseline_y,
                                            # e as demais sobem (diminuindo Y) conforme o espaçamento e o tamanho da fonte.
                                            y_baseline = last_line_baseline_y - idx * (fontsize_text + interline_spacing)
                                            
                                            # Define o retângulo para a linha:
                                            # - A borda direita é text_block_right_x.
                                            # - A borda esquerda é deslocada para a esquerda em função da largura do texto.
                                            # - A borda inferior é a linha de base (y_baseline)
                                            # - A borda superior é y_baseline - fontsize_text (aproximadamente a altura do texto).
                                            rect_line = fitz.Rect(
                                                text_block_right_x - line_width,  # esquerda
                                                y_baseline - fontsize_text,         # superior
                                                text_block_right_x,                 # direita
                                                y_baseline                          # inferior
                                            )
                                            
                                            # Desenha o retângulo (fundo branco) sem borda (width=0)
                                            bg_shape.draw_rect(rect_line)

                                        # Finaliza e comita os retângulos de fundo
                                        bg_shape.finish(width=0.3*scaling_text, color=(1, 1, 1), fill=(1, 1, 1))
                                        bg_shape.commit()

                                        # ===============================
                                        # 2. Insere o texto sobre o fundo utilizando insert_text
                                        # ===============================
                                        # Aqui, calculamos a posição de inserção de cada linha.
                                        # Lembrando que insert_text usa como referência o ponto de início da linha de base.
                                        for idx, line in enumerate(reversed(text_lines)):
                                            # Calcula a largura da linha atual (não é estritamente necessário para o insert_text, mas usamos para alinhamento)
                                            line_width = font.text_length(line, fontsize=fontsize_text)
                                            
                                            # Calcula a posição Y (linha de base)
                                            y_baseline = last_line_baseline_y - idx * (fontsize_text + interline_spacing)
                                            
                                            # Calcula a posição X para que a borda direita do texto alinhe com text_block_right_x.
                                            # Como insert_text posiciona o texto a partir do ponto de início (canto inferior esquerdo),
                                            # definimos x_pos de forma que: x_pos + line_width = text_block_right_x.
                                            x_pos = text_block_right_x - line_width
                                            
                                            # Insere o texto a partir do ponto (x_pos, y_baseline)
                                            page.insert_text(
                                                (x_pos, y_baseline),
                                                line,
                                                fontsize=fontsize_text,
                                                fontname=font.name,
                                                color=(0, 0, 0)  # Texto em preto
                                            )

                                        # === Chancela / Logo Centralizada ===
                                        chancela_path = 'resources/chancela.png'
                                        try:
                                            with Image.open(chancela_path) as img:
                                                original_width_px, original_height_px = img.size 

                                            # Calcula as dimensões alvo em pontos
                                            # Mantém a proporção original, ajustando ao maior lado alvo
                                            aspect_ratio = original_width_px / original_height_px
                                            if aspect_ratio > 1: # Largura maior
                                                target_width = scaling_logo_target
                                                target_height = scaling_logo_target / aspect_ratio
                                            else: # Altura maior ou igual
                                                target_height = scaling_logo_target
                                                target_width = scaling_logo_target * aspect_ratio
                                                
                                            # Posiciona a imagem centralizada na página
                                            logo_center_x = page_width / 2
                                            logo_center_y = page_height / 2
                                            
                                            x_logo = logo_center_x - target_width / 2
                                            y_logo = logo_center_y - target_height / 2

                                            logo_rect = fitz.Rect(x_logo, y_logo, x_logo + target_width, y_logo + target_height)
                                            page.insert_image(
                                                logo_rect,
                                                filename=chancela_path,
                                                overlay=True # Garante que fique por cima do conteúdo existente
                                            )
                                        except FileNotFoundError:
                                            print(f"Erro: Arquivo da chancela não encontrado em {chancela_path}")
                                        except Exception as e:
                                            print(f"Erro ao processar a imagem da chancela: {e}")


                                        # === Hash Lateral (Centro Vertical, Borda Esquerda) ===
                                        num_paginas = len(doc) # Pega o número total de páginas do doc original
                                        tamanho_arquivo = len(pdf_bytes) / 1024 # Em KB
                                        fontsize_hash = scaling_text
                                        # Use uma fonte monoespaçada como Courier, Helvetica ou Times
                                        # fitz.Font("cour") pode dar erro se não for uma fonte base PDF standard ou registrada
                                        # Usar nomes standard é mais seguro: "Courier", "Helvetica", "Times-Roman"
                                        try:
                                            font_hash = fitz.Font("cour") # Tenta carregar Courier
                                            fontname_hash = "cour"
                                        except:
                                            print("Fonte 'cour' não encontrada, usando 'Courier'.")
                                            # fitz usa nomes de fontes base do PDF se não encontrar a específica
                                            font_hash = fitz.Font("Courier") 
                                            fontname_hash = "Courier"
                                            
                                        hash_text = f"hash original: {hash_pdf}; total páginas: {num_paginas}; tamanho: {tamanho_arquivo:.2f} KB"

                                        # Calcula a largura do texto (que será a altura após rotação)
                                        text_width_hash = font_hash.text_length(hash_text, fontsize=fontsize_hash)

                                        # Correção 1: Posicionamento do Hash
                                        # Ponto de inserção para rotação de 90 graus (sentido anti-horário)
                                        # O ponto (x, y) é o canto inferior esquerdo da linha de base do texto *antes* da rotação.
                                        # Após rotação de 90°, a linha de base fica vertical, começando em (x, y) e indo para cima.
                                        # Queremos o texto centralizado verticalmente (page_height / 2) e alinhado à margem esquerda (margin).
                                        hash_insert_x = margin # Alinhado à margem esquerda
                                        hash_insert_y = page_height / 2 + text_width_hash / 2 # Ponto base para centralizar verticalmente

                                        hash_text_point = fitz.Point(hash_insert_x, hash_insert_y)
                                        
                                        page.insert_text(
                                            hash_text_point,
                                            hash_text,
                                            fontsize=fontsize_hash,
                                            fontname=fontname_hash,
                                            color=(0, 0, 0),
                                            rotate=90  # Rotação anti-horária
                                        )

                                    # === Salvar PDF processado ===
                                    output = io.BytesIO()
                                    # Salva com garbage collection para otimizar o tamanho, se necessário
                                    doc.save(output, garbage=4, deflate=True) 
                                    pdf_final = output.getvalue()
                                    hashes_depois[uploaded_file.name] = hashlib.sha256(pdf_final).hexdigest()
                                    processed_files.append((uploaded_file.name, pdf_final))
                                    doc.close()

                            if processed_files:
                                # Crie a lista de dados para o JSON
                                hashes_info = []
                                for name, pdf_final in processed_files:
                                    
                                    # Obtém os hashes do dicionário
                                    hash_original = hashes_antes.get(name, "N/A")
                                    hash_modificado = hashes_depois.get(name, "N/A")

                                    # Formata o JSON
                                    hashes_info.append({
                                        "Nome arquivo": name,
                                        "Codigo": hash_para_codigo(hash_original),
                                        "Hash original": hash_original,
                                        "Hash derivado": hash_modificado,
                                        "Certificador": st.session_state.certificador["usuario"],
                                    })
                                # Exibe o JSON formatado
                                # st.write("### Informações dos arquivos:")
                                # st.json(hashes_info)
                                if st.session_state.json_hash == None:
                                    st.session_state.json_hash = hashes_info
                                
                                load_container_btn = True


            if load_container_btn:
                with st.container(border=True):
                    with st.spinner("Aguarde..."):
                        # Mantenha o download do ZIP
                        zip_buffer = io.BytesIO()

                        # Cria o ZIP em um arquivo temporário
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                            with zipfile.ZipFile(tmp_zip, 'w') as zip_file:
                                # Adiciona os arquivos processados
                                for name, data in processed_files:
                                    zip_file.writestr(name, data)
                                # Adiciona o arquivo do upload
                                zip_file.writestr(uploaded_qr_pdf.name, qr_pdf_bytes)
                            tmp_zip_path = tmp_zip.name

                        # Armazena o caminho do arquivo ZIP no session_state
                        st.session_state.zip_path = tmp_zip_path

                        # Lê os dados binários do arquivo ZIP quando necessário
                        with open(st.session_state.zip_path, "rb") as f:
                            zip_bytes = f.read()
                            tamanho_zip_bytes = len(zip_bytes)

                            with st.spinner("Aguarde..."):
                                st.write("#### Envio do arquivo")
                                c1, c2, c3 = st.columns(3, vertical_alignment='top')
                                c1.download_button(
                                    "Baixar Arquivo",
                                    data=zip_bytes,
                                    file_name=f"documentos_proc_{st.session_state.proc}-{st.session_state.ano}.zip",
                                    mime="application/zip",
                                    use_container_width=True,
                                    icon=":material/download:"
                                )

                                df_encontrado = st.session_state.df_encontrado

                                # Converta o JSON para string
                                json_str = json.dumps(st.session_state.json_hash)
                                str_ano = str(st.session_state.ano)


                                btn_disabled = False

                                size_attch = tamanho_zip_bytes / (1024*1024)
                                if size_attch > 5.1:
                                    btn_disabled = True


                                print(f"size_attch: {size_attch}")

                                if c2.button(
                                        'Enviar e-mail',
                                        use_container_width=True,
                                        icon=':material/forward_to_inbox:',
                                        type='primary',
                                        disabled=btn_disabled,
                                        on_click=lambda: email_aprojeto(
                                            kw_attachment=zip_bytes,
                                            kw_file_name=f"documentos_proc_{st.session_state.proc}-{str_ano}.zip",
                                            kw_despacho = f"""
                                                O processo GDOC nº <strong>{st.session_state.proc}/{str_ano[2:]}</strong>, 
                                                referente à aprovação do projeto arquitetônico da empresa 
                                                <strong><span style="text-transform: uppercase;">{st.session_state.nome}</span></strong> 
                                                (CPF/CNPJ nº {st.session_state.cpf_cnpj}), <strong><span style="color: #009933;">foi aprovado</span></strong>. 
                                                Segue em anexo o projeto certificado, juntamente com o Parecer Técnico de aprovação do projeto arquitetônico.
                                                """,
                                            kw_email1=df_encontrado.iloc[0]['E-mail'],
                                            kw_email2=df_encontrado.iloc[0]['E-mail CC'],
                                            kw_obs=st.session_state.obs,
                                            kw_ano = str_ano,
                                        )
                                    ):

                                    if not df_encontrado.empty:
                                        st.toast("**Tentando salvar os dados do processo. Aguarde...**")
                                        try:
                                            ws = get_worksheet(1, st.secrets['sh_keys']['geral_major'])
                                            cell = ws.find(df_encontrado.iloc[0]['Código Solicitação'], in_column=1)
                                            range_div = f"AC{cell.row}:AE{cell.row}"
                                            data_entrega = get_current_datetime()
                                            values = [json_str, data_entrega, st.session_state.obs]
                                            ws.update(range_div, [values])
                                        except Exception as e:
                                            st.toast(f":red[**Erro ao salvar os dados:** {e}]")
                                            print(f":red[**Erro ao salvar os dados:** {e}]")
                                        else:
                                            limpar_tudo(":green[**Dados salvos com sucesso!**] **Reiniciando...**")              
                                            load_div_df.clear()
                                            time.sleep(3)
                                            limpar_tudo("")
                                            # st.session_state.rerun_duplo = True
                                            st.rerun()
                                    else:
                                        st.toast(":red[**Houve um erro na leitura dos dados encontrados.**]")

                                if c3.button("Limpar tudo", use_container_width=True, icon=":material/delete_forever:"):
                                    limpar_tudo(":green[**Dados destruídos com sucesso.**]")
                                
                                # desabilitar o botão de envio de arquivo
                                if btn_disabled:
                                    st.error("O tamanho do arquivo ultrapassa o limite de 25 MB.")

        with st.container(border=True):
            st.write("#### Pesquisa")
            c1, c2, c3, c4, c5, c6 = st.columns([1,1,1,1,1,0.3], vertical_alignment='bottom')
            st.session_state.ano = c1.selectbox("Ano:", placeholder='2025', options=[2025, 2026, 2027, 2028])
            st.session_state.proc = c2.text_input("Nº GDOC:", max_chars=6, placeholder='00000', value=st.session_state.proc)
            btn_processo = c3.button("", type="primary", icon=":material/search:", use_container_width=False, key="btn_processo", disabled=st.session_state.off_btn_processo_chancela, help='Pesquisar processo')

            c4.link_button("Certifica", use_container_width=True, url='https://sistemas.belem.pa.gov.br/portaldoservidor/#/autenticado/certifica/certificaDoc', icon=":material/qr_code:", help="Abrir Certifica")
            c5.link_button("GDOC", use_container_width=True, url='https://gdoc.belem.pa.gov.br/gdocprocessos/home', icon=":material/public:", help="Abrir GDOC")

            if c6.button("", type='secondary', icon=':material/restart_alt:', key='btn_loadDb', help='Recarregar banco', use_container_width=False):
                load_div_df.clear()
                limpar_tudo("Recarregando o banco de dados. Aguarde...")
                time.sleep(4)
                st.rerun()

            
            if btn_processo:
                ano = st.session_state.ano
                proc = st.session_state.proc 
                match str(ano):
                    case '2025' | '2026' | '2027' | '2028' | '2029' | '2030' | '2031':
                        try:
                            proc = int(proc)
                        except:
                            limpar_tudo("")
                            st.toast(":red[**Informe um PROCESSO válido para pesquisa.**]")
                        else:
                            if proc >= 1 and proc <= 99999:
                                df_encontrado = procurar_processo(df, proc, ano)
                                
                                if not df_encontrado.empty:
                                    carregar_formulario(df_encontrado)
                                    st.session_state.load_qrcode = True
                                    st.session_state.df_encontrado = df_encontrado
                                else:
                                    limpar_tudo("")
                                    st.toast(f"Nenhum resultado encontrado para {proc}/{ano}")
                            else:
                                limpar_tudo("")
                                st.toast(":red[**Informe um PROCESSO válido para pesquisa.**]")                             
                    case _:
                        limpar_tudo("")
                        st.toast(":red[**Informe um ANO válido para pesquisa.**]")

                # qr_code()

            st.write("")
            
            st.fragment()
            def fragment_input_fields():
                st.write("#### Dados do processo")
                c1, c2, c3, c4, c5 = st.columns(5, vertical_alignment='bottom')
                c1.text_input("Cód. Solicitação", placeholder='', value=st.session_state.cod_solicitacao)
                c2.text_input("Data Criação", placeholder='', value=st.session_state.dt_solicitacao)
                c3.text_input("Data Entrega", placeholder='', value=st.session_state.dt_atendimento)
                c4.text_input("Natureza Jur.", placeholder='', value=st.session_state.natjur)
                c5.text_input("DAM", placeholder='', value=st.session_state.dam)

                c1, c2 = st.columns([0.5, 1.5], vertical_alignment='bottom')
                c1.text_input("CPF/CNPJ", placeholder='', value=st.session_state.cpf_cnpj)
                c2.text_input("Nome empresa", placeholder='', value=st.session_state.nome)

                c1, c2 = st.columns(2, vertical_alignment='bottom')
                c1.text_input("E-mail", placeholder='', value=st.session_state.email1)
                c2.text_input("E-mail CC", placeholder='', value=st.session_state.email2)


                st.session_state.obs = st.text_area("Observação", placeholder='Se quiser enviar este texto por e-mail, escreva "A/C" antes do texto.', value=st.session_state.obs)

            st.fragment()
            def fragment_documents():
                df_e = st.session_state.df_encontrado
                if not df_e.empty:
                    # Verifica se a coluna 'Docs Aprovação de Projeto' existe e não está vazia
                    if 'Docs Aprovação de Projeto' in df_e.columns:
                        all_links = df_e['Docs Aprovação de Projeto'].dropna().tolist()  # Remove valores nulos
                        links = []
                        for link_str in all_links:
                            prime_link = df_e['Docs Mesclados']
                            found_links = re.findall(r"https?://[^\s]+", link_str)  # Extrai todos os links
                            links.extend(prime_link)
                            links.extend(found_links)  # Adiciona os links extraídos à lista final    
                        if links:
                            st.write("#### Documentos de abertura do processo")
                            cols = st.columns(7)  # Define 5 colunas para disposição dos botões

                            # Primeiro botão chamado "Docs mesclados"
                            cols[0].link_button("Docs gerais", links[0], use_container_width=True)  

                            # Botões para os demais links
                            for idx, link in enumerate(links[1:], start=1):
                                col = cols[idx % len(cols)]  # Distribui os botões nas colunas
                                col.link_button(f"Pancha nº {idx}", link, use_container_width=True)
        
        with st.container(border=True):
            fragment_input_fields()
        
        with st.container(border=True):
            fragment_documents()

        if st.session_state.load_qrcode:
            qr_code()
        
        if st.session_state.rerun_duplo:
            st.session_state.rerun_duplo = False
            st.rerun()