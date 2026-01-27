import requests
import os
import smtplib
import math
import csv
from datetime import datetime
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES AGRONÔMICAS E DO SISTEMA ---
DATA_PLANTIO = datetime(2025, 11, 25) 
T_BASE_BERRIES = 10.0 
GDA_ALVO_COLHEITA = 1200 
KC_ATUAL = 0.75          

# Chaves e Endereços (Puxados dos Secrets do GitHub)
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
CIDADE = "Ibicoara, BR"

# --- 2. FUNÇÕES DE CÁLCULO FÍSICO E MATEMÁTICO ---

def calcular_delta_t_e_vpd(temp, umidade):
    """
    Calcula o Delta T (diferença entre bulbo seco e úmido) e 
    o VPD (Déficit de Pressão de Vapor) com base na equação de Tetens.
    """
    # Pressão de Saturação de Vapor (es)
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    # Pressão Atual de Vapor (ea)
    ea = es * (umidade / 100)
    # VPD
    vpd = round(es - ea, 2)
    
    # Cálculo aproximado do Bulbo Úmido (Tw) via Stull (1973)
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    
    # Delta T
    delta_t = round(temp - tw, 1)
    return delta_t, vpd

# --- 3. FUNÇÕES DE LEITURA E INTERPRETAÇÃO (GATILHOS) ---

def ler_atividades_usuario():
    """Lê o arquivo de texto do usuário e limpa o conteúdo após a leitura."""
    arquivo_input = 'input_atividades.txt'
    if os.path.exists(arquivo_input):
        with open(arquivo_input, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        
        # Se houver conteúdo novo (diferente do padrão), retorna e limpa
        if conteudo and conteudo != "Início do caderno de campo":
            with open(arquivo_input, 'w', encoding='utf-8') as f:
                f.write("") # Limpa o arquivo
            return conteudo
    return "Nenhum manejo registrado pelo usuário hoje."

def processar_gatilhos_inteligentes(texto):
    """
    Analisa semanticamente o texto do usuário e gera alertas agronômicos 
    profundos baseados em palavras-chave.
    """
    analise_extra = ""
    texto = texto.lower()
    
    # Gatilho: Chuva / Água em Excesso
    if any(p in texto for p in ["chuva", "chovendo", "volume", "água"]):
        analise_extra += "⚠️ ALERTA CRÍTICO (HIDROLOGIA E SOLOS): O evento de precipitação relatado altera drasticamente a dinâmica da rizosfera. "
        analise_extra += "1) Risco de Lixiviação: Nutrientes móveis (Nitrato NO3- e Potássio K+) podem ter sido carreados para camadas profundas, longe das raízes absorventes. "
        analise_extra += "2) Anoxia Radicular: A saturação dos macroporos do solo expulsa o oxigênio, impedindo a respiração da raiz e travando a absorção de nutrientes. Suspenda fertirrigação até a drenagem natural.\n"
    
    # Gatilho: Pragas e Doenças
    if any(p in texto for p in ["praga", "inseto", "mancha", "lagarta", "ácaro", "fungo", "oídio", "botrytis"]):
        analise_extra += "🔍 MANEJO INTEGRADO (MIP) DE ALTA PRECISÃO: A pressão biótica relatada exige ação corretiva imediata. "
        analise_extra += "Para fungicidas ou inseticidas de contato, busque janelas com Delta T entre 2 e 8 para evitar evaporação rápida da gota. "
        analise_extra += "Para sistêmicos, garanta que o solo tenha umidade para que a planta transloque o produto via xilema.\n"
    
    # Gatilho: Nutrição
    if any(p in texto for p in ["fertilizante", "adubo", "fertirrigação", "nutriente", "map", "nitrato", "potássio", "cálcio"]):
        analise_extra += "🧪 DINÂMICA NUTRICIONAL: O aporte realizado hoje entrará na solução do solo. "
        analise_extra += "Lembre-se: O Cálcio (Ca) só sobe para o fruto se houver transpiração ativa (VPD > 0.4 kPa). Se o dia estiver muito úmido, a eficiência dessa adubação será reduzida.\n"

    return analise_extra if analise_extra else "✅ STATUS OPERACIONAL: O manejo relatado segue o cronograma padrão, sem alertas críticos de interação imediata."

def gerar_conclusao_agronomo(hoje, balanco, anotacao, dias_campo):
    """Gera um parecer técnico executivo."""
    conclusao = "👨‍🔬 PARECER TÉCNICO ESTRATÉGICO:\n"
    
    if "chuva" in anotacao.lower():
        conclusao += "Devido ao aporte hídrico não previsto (chuva), o manejo deve migrar de 'irrigação' para 'drenagem e sanidade'. Risco alto de lixiviação de N e K. "
    elif hoje['vpd'] > 1.4:
        conclusao += "O estresse atmosférico elevado (VPD Alto) está limitando a fotossíntese. Não force a planta com adubações salinas hoje. Priorize irrigação de resfriamento. "
    else:
        conclusao += "As condições termo-hídricas estão ideais para a atividade metabólica. O momento é oportuno para bioestimulantes e nutrição foliar. "
    
    conclusao += f"Aos {dias_campo} dias, a cultura demanda estabilidade para consolidar a estrutura produtiva."
    return conclusao

# --- 4. ANÁLISE COMPLETA E GERAÇÃO DO RELATÓRIO ---

def analisar_expert_educativo(previsoes, anotacao_usuario):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    balanco = total_chuva - total_etc
    dias_campo = (datetime.now() - DATA_PLANTIO).days
    
    # Processamentos lógicos
    analise_gatilho = processar_gatilhos_inteligentes(anotacao_usuario)
    conclusao_final = gerar_conclusao_agronomo(hoje, balanco, anotacao_usuario, dias_campo)
    
    # Status Dashboard
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🔴 CRÍTICO" if hoje['delta_t'] > 8 else "🟡 ALERTA")
    status_hidr = "🟢 EQUILIBRADO" if -5 < balanco < 5 else ("🔴 DÉFICIT SEVERO" if balanco < -10 else "🟡 REVISAR")
    
    # --- CONSTRUÇÃO DO TEXTO DO E-MAIL ---
    parecer = f"🚦 DASHBOARD OPERACIONAL DE ALTA PERFORMANCE:\n"
    parecer += f"• Janela de Pulverização (Delta T): {status_pulv}\n"
    parecer += f"• Balanço Hídrico Semanal (Chuva - Consumo): {status_hidr}\n"
    parecer += f"💡 ANÁLISE TÉCNICA: O Delta T integra a temperatura e a umidade para determinar a vida útil da gota. "
    parecer += f"Valores ideais (2-8) asseguram que o defensivo atinja o alvo sem evaporar (perda por deriva térmica) e sem escorrer (lavagem), maximizando o ROI da aplicação.\n\n"
    
    parecer += f"📝 REGISTRO DE CAMPO E ANÁLISE DE GATILHOS:\n"
    parecer += f"• Sua anotação: \"{anotacao_usuario}\"\n"
    parecer += f"📢 CONSULTORIA DINÂMICA:\n{analise_gatilho}\n\n"

    # Sanidade
    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88 and p['vento'] < 6)
    risco_sanidade = 'ALTO' if horas_molhamento > 2 else 'BAIXO'
    parecer += f"🍄 MONITORAMENTO DE SANIDADE (Índice de Molhamento):\n"
    parecer += f"• Risco Fúngico: {risco_sanidade} ({horas_molhamento} janelas de orvalho previstas)\n"
    parecer += f"💡 FUNDAMENTAÇÃO: Esporos de Botrytis cinerea e Antracnose dependem de água livre na folha para emitir o tubo germinativo. "
    parecer += f"Se o índice for ALTO, recomenda-se o uso de fungicidas protetores ou sistêmicos preventivos, pois o microclima está favorável à infecção.\n\n"

    # Fisiologia
    gda_total = dias_campo * 14.8 # Estimativa média ajustada para o local
    progresso = min(round((gda_total / GDA_ALVO_COLHEITA) * 100, 1), 100)
    gda_hoje = max(hoje['temp'] - T_BASE_BERRIES, 0)
    
    parecer += f"🧬 FISIOLOGIA E FENOLOGIA (O Relógio da Planta):\n"
    parecer += f"• Idade Real: {dias_campo} dias | Progresso de Safra: {progresso}%\n"
    parecer += f"• Energia Térmica Acumulada (GDA): {gda_total:.0f} Graus-Dia (Hoje: +{gda_hoje:.1f})\n"
    parecer += f"💡 FUNDAMENTAÇÃO: A fenologia é regida pela soma térmica. O acúmulo de GDA determina a velocidade das reações enzimáticas. "
    parecer += f"Estamos monitorando a eficiência com que a planta converte luz e calor em biomassa e açúcares (Brix).\n\n"
    
    # Nutrição
    parecer += f"🛒 RECOMENDAÇÃO DE NUTRIÇÃO MINERAL:\n"
    if dias_campo < 90:
        parecer += "• FASE: Estabelecimento Radicular.\n• FOCO: Fósforo (P), Cálcio (Ca) e Magnésio (Mg).\n"
        parecer += "💡 CIÊNCIA DO SOLO: O Fósforo é essencial para a síntese de ATP (energia) e crescimento radicular. "
        parecer += "O Cálcio estrutura a parede celular (pectatos), vital para a firmeza futura do fruto. Aplique via fertirrigação para atingir a zona de absorção.\n\n"
    elif dias_campo < 180:
        parecer += "• FASE: Crescimento Vegetativo.\n• FOCO: Nitrogênio (N) e Micronutrientes.\n"
        parecer += "💡 CIÊNCIA DO SOLO: O Nitrogênio impulsiona a produção de aminoácidos e proteínas. Atenção ao Molibdênio, necessário para a planta metabolizar esse Nitrogênio.\n\n"
    else:
        parecer += "• FASE: Reprodutiva/Maturação.\n• FOCO: Potássio (K) e Boro (B).\n"
        parecer += "💡 CIÊNCIA DO SOLO: O Potássio atua na osmorregulação e transporte de fotoassimilados (açúcar) para o fruto. O Boro garante a viabilidade do tubo polínico.\n\n"

    # VPD
    parecer += f"🌿 CONFORTO TÉRMICO (VPD - Déficit de Pressão de Vapor):\n"
    parecer += f"• VPD Atual: {hoje['vpd']} kPa.\n"
    if hoje['vpd'] > 1.3:
        parecer += "💡 ANÁLISE: VPD ALTO (>1.3). O ar está 'seco' para a planta. Ela fecha os estômatos para não desidratar, o que interrompe a entrada de CO2 (fotossíntese) e a subida de nutrientes (Cálcio/Boro). Irrigação pulsada ajuda a reduzir a temperatura.\n\n"
    elif hoje['vpd'] < 0.4:
        parecer += "💡 ANÁLISE: VPD BAIXO (<0.4). Ar saturado. A transpiração cessa. Sem transpiração, a planta não 'puxa' água e nutrientes do solo. Risco de gutação e doenças.\n\n"
    else:
        parecer += "💡 ANÁLISE: VPD IDEAL. A planta está funcionando como uma bomba hidráulica eficiente, transpirando e fixando carbono em taxa máxima.\n\n"

    # Manejo Hídrico
    parecer += f"💧 MANEJO HÍDRICO DE PRECISÃO (ETc):\n"
    parecer += f"• Demanda Real da Cultura (Semana): {total_etc:.1f} mm.\n"
    parecer += f"💡 FUNDAMENTAÇÃO: A ETc (Evapotranspiração da Cultura) é calculada multiplicando a referência (ET0) pelo coeficiente biológico da planta (Kc={KC_ATUAL}). "
    parecer += f"Este é o valor exato de água que a planta perderá para a atmosfera e que precisa ser reposto para manter o turgor celular.\n\n"
    
    parecer += "------------------------------------------------------------\n"
    parecer += f"{conclusao_final}\n"

    return parecer, conclusao_final

# --- 5. EXECUÇÃO PRINCIPAL (API, LOG E ENVIO) ---

def get_agro_data_ultimate():
    """Busca dados na API OpenWeatherMap e processa as variáveis."""
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    try:
        response = requests.get(url)
        response.raise_for_status() # Garante que paramos se der erro na API
        data = response.json()
    except Exception as e:
        print(f"Erro ao conectar na API: {e}")
        return []

    previsoes_diarias = []
    # Pega uma amostra a cada 24h (índices 0, 8, 16...)
    for i in range(0, min(40, len(data['list'])), 8):
        item = data['list'][i]
        t = item['main']['temp']
        u = item['main']['humidity']
        dt, vpd = calcular_delta_t_e_vpd(t, u)
        
        # Chuva acumulada nas 24h (8 blocos de 3h)
        chuva_acumulada = 0
        for j in range(8):
            if i + j < len(data['list']):
                chuva_acumulada += data['list'][i+j].get('rain', {}).get('3h', 0)
        
        # ET0 Estimada (Hargreaves-Samani simplificado)
        et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408

        previsoes_diarias.append({
            'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
            'temp': t, 
            'umidade': u, 
            'vpd': vpd, 
            'delta_t': dt,
            'vento': item['wind']['speed'] * 3.6,
            'chuva': round(chuva_acumulada, 1),
            'et0': round(et0, 2)
        })
    return previsoes_diarias

def registrar_log_master(previsoes, anotacao, conclusao):
    """Salva os dados no CSV histórico."""
    arquivo = 'caderno_de_campo_master.csv'
    existe = os.path.isfile(arquivo)
    
    try:
        with open(arquivo, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not existe:
                writer.writerow(['Data', 'Temp_C', 'VPD_kPa', 'DeltaT', 'Chuva_mm', 'Manejo_Usuario', 'Parecer_Tecnico'])
            
            # Limpa quebras de linha da conclusão para não quebrar o CSV
            conclusao_limpa = conclusao.replace("\n", " | ")
            
            writer.writerow([
                datetime.now().strftime('%d/%m/%Y'), 
                previsoes[0]['temp'], 
                previsoes[0]['vpd'], 
                previsoes[0]['delta_t'], 
                previsoes[0]['chuva'],
                anotacao, 
                conclusao_limpa
            ])
    except Exception as e:
        print(f"Erro ao salvar log: {e}")

def enviar_email(conteudo):
    """Envia o relatório via SMTP do Gmail."""
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"💎 RELATÓRIO AGRO-INTEL: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
            smtp.send_message(msg)
        print("✅ E-mail enviado com sucesso!")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")

if __name__ == "__main__":
    print("🔄 Iniciando Sistema Agro-Intel...")
    
    # 1. Obter Dados
    previsoes = get_agro_data_ultimate()
    
    if previsoes:
        # 2. Ler Inputs do Usuário
        anotacao = ler_atividades_usuario()
        
        # 3. Processar Análise
        analise_email, conclusao_agronomo = analisar_expert_educativo(previsoes, anotacao)
        
        # 4. Montar Corpo do E-mail
        corpo = f"💎 CONSULTORIA AGRO-INTEL PREMIUM: IBICOARA/BA\n"
        corpo += f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        corpo += "------------------------------------------------------------\n"
        corpo += "📈 PREVISÃO E MONITORAMENTO (5 DIAS):\n"
        for p in previsoes:
            etc = round(p['et0'] * KC_ATUAL, 2)
            corpo += f"{p['data']} | {p['temp']}°C | Chuva: {p['chuva']}mm | ETc (Consumo): {etc}mm\n"
        corpo += f"\n{analise_email}"
        
        # 5. Enviar e Registrar
        enviar_email(corpo)
        registrar_log_master(previsoes, anotacao, conclusao_agronomo)
        print("✅ Processo concluído com precisão.")
    else:
        print("❌ Falha ao obter dados meteorológicos. Verifique a API Key.")
