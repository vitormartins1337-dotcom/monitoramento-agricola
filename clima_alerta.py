import requests
import os
import smtplib
import math
import csv
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES AGRONÔMICAS E DO SISTEMA ---
DATA_PLANTIO = datetime(2025, 11, 25) 
T_BASE_BERRIES = 10.0 
GDA_ALVO_COLHEITA = 1200 
KC_ATUAL = 0.75

# DEFINIÇÃO DE FUSO HORÁRIO (BAHIA/BRASÍLIA = UTC-3)
FUSO_BRASIL = timezone(timedelta(hours=-3))

# Chaves e Endereços
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
CIDADE = "Ibicoara, BR"

# --- 2. FUNÇÕES DE CÁLCULO FÍSICO E MATEMÁTICO ---

def calcular_delta_t_e_vpd(temp, umidade):
    """Calcula Delta T e VPD usando equação de Tetens."""
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umidade / 100)
    vpd = round(es - ea, 2)
    
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    
    delta_t = round(temp - tw, 1)
    return delta_t, vpd

# --- 3. FUNÇÕES DE LEITURA E INTERPRETAÇÃO (GATILHOS) ---

def ler_atividades_usuario():
    """Lê o arquivo de texto do usuário e limpa o conteúdo após a leitura."""
    arquivo_input = 'input_atividades.txt'
    if os.path.exists(arquivo_input):
        with open(arquivo_input, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        
        if conteudo and conteudo != "Início do caderno de campo":
            with open(arquivo_input, 'w', encoding='utf-8') as f:
                f.write("") # Limpa o arquivo
            return conteudo
    return "Nenhum manejo registrado pelo usuário hoje."

def processar_gatilhos_inteligentes(texto):
    """Analisa semanticamente o texto do usuário e gera alertas agronômicos."""
    analise_extra = ""
    texto = texto.lower()
    
    if any(p in texto for p in ["chuva", "chovendo", "volume", "água"]):
        analise_extra += "⚠️ ALERTA CRÍTICO (HIDROLOGIA E SOLOS): O evento de precipitação relatado altera drasticamente a dinâmica da rizosfera. "
        analise_extra += "1) Risco de Lixiviação: Nutrientes móveis (Nitrato NO3- e Potássio K+) podem ter sido carreados para camadas profundas. "
        analise_extra += "2) Anoxia Radicular: A saturação expulsa o oxigênio, impedindo a respiração da raiz. Suspenda fertirrigação até drenagem.\n"
    
    if any(p in texto for p in ["praga", "inseto", "mancha", "lagarta", "ácaro", "fungo", "oídio", "botrytis"]):
        analise_extra += "🔍 MANEJO INTEGRADO (MIP) DE ALTA PRECISÃO: Pressão biótica identificada. "
        analise_extra += "Para aplicações de contato, busque janelas com Delta T entre 2 e 8. "
        analise_extra += "Para sistêmicos, garanta turgor na planta para translocação via xilema.\n"
    
    if any(p in texto for p in ["fertilizante", "adubo", "fertirrigação", "nutriente", "map", "nitrato", "potássio", "cálcio"]):
        analise_extra += "🧪 DINÂMICA NUTRICIONAL: O aporte realizado entrará na solução do solo. "
        analise_extra += "Atenção: A absorção de Cálcio (Ca) depende diretamente da transpiração (VPD > 0.4 kPa). Em dias saturados, a eficiência cai drasticamente.\n"

    return analise_extra if analise_extra else "✅ STATUS OPERACIONAL: O manejo segue o cronograma padrão, sem alertas críticos imediatos."

def gerar_conclusao_agronomo(hoje, balanco, anotacao, dias_campo):
    """Gera um parecer técnico executivo."""
    conclusao = "👨‍🔬 PARECER TÉCNICO ESTRATÉGICO:\n"
    
    if "chuva" in anotacao.lower():
        conclusao += "Devido ao aporte hídrico não previsto (chuva), o manejo migra para 'drenagem e sanidade'. Risco alto de lixiviação de N e K. "
    elif hoje['vpd'] > 1.4:
        conclusao += "Estresse atmosférico elevado (VPD Alto) limita a fotossíntese. Evite adubações salinas hoje. Priorize irrigação de resfriamento. "
    else:
        conclusao += "Condições termo-hídricas ideais para atividade metabólica. Momento oportuno para bioestimulantes e nutrição. "
    
    conclusao += f"Aos {dias_campo} dias, a cultura demanda estabilidade para consolidar a estrutura produtiva."
    return conclusao

# --- 4. ANÁLISE COMPLETA E GERAÇÃO DO RELATÓRIO ---

def analisar_expert_educativo(previsoes, anotacao_usuario):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    balanco = total_chuva - total_etc
    
    # Cálculo de dias usando datas limpas para evitar erro de fuso horário
    dias_campo = (datetime.now(FUSO_BRASIL).date() - DATA_PLANTIO.date()).days
    
    analise_gatilho = processar_gatilhos_inteligentes(anotacao_usuario)
    conclusao_final = gerar_conclusao_agronomo(hoje, balanco, anotacao_usuario, dias_campo)
    
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🔴 CRÍTICO" if hoje['delta_t'] > 8 else "🟡 ALERTA")
    status_hidr = "🟢 EQUILIBRADO" if -5 < balanco < 5 else ("🔴 DÉFICIT SEVERO" if balanco < -10 else "🟡 REVISAR")
    
    parecer = f"🚦 DASHBOARD OPERACIONAL DE ALTA PERFORMANCE:\n"
    parecer += f"• Janela de Pulverização (Delta T): {status_pulv}\n"
    parecer += f"• Balanço Hídrico Semanal: {status_hidr}\n"
    parecer += f"💡 ANÁLISE TÉCNICA: O Delta T (2-8 ideal) assegura que o defensivo atinja o alvo sem evaporar (deriva térmica) nem escorrer, maximizando o ROI da aplicação.\n\n"
    
    parecer += f"📝 REGISTRO DE CAMPO E ANÁLISE DE GATILHOS:\n"
    parecer += f"• Sua anotação: \"{anotacao_usuario}\"\n"
    parecer += f"📢 CONSULTORIA DINÂMICA:\n{analise_gatilho}\n\n"

    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88 and p['vento'] < 6)
    risco_sanidade = 'ALTO' if horas_molhamento > 2 else 'BAIXO'
    parecer += f"🍄 MONITORAMENTO DE SANIDADE (Índice de Molhamento):\n"
    parecer += f"• Risco Fúngico: {risco_sanidade} ({horas_molhamento} janelas de orvalho)\n"
    parecer += f"💡 FUNDAMENTAÇÃO: Esporos de Botrytis e Antracnose dependem de água livre. Índice ALTO exige fungicidas protetores ou sistêmicos preventivos.\n\n"

    gda_total = dias_campo * 14.8 
    progresso = min(round((gda_total / GDA_ALVO_COLHEITA) * 100, 1), 100)
    gda_hoje = max(hoje['temp'] - T_BASE_BERRIES, 0)
    
    parecer += f"🧬 FISIOLOGIA (Relógio Térmico):\n"
    parecer += f"• Idade: {dias_campo} dias | Progresso: {progresso}% | GDA Hoje: {gda_hoje:.1f}\n"
    parecer += f"💡 FUNDAMENTAÇÃO: Monitoramos a eficiência da conversão de luz e calor em biomassa. O acúmulo de GDA dita a velocidade enzimática da planta.\n\n"
    
    parecer += f"🛒 RECOMENDAÇÃO DE NUTRIÇÃO MINERAL:\n"
    if dias_campo < 90:
        parecer += "• FASE: Estabelecimento Radicular.\n• FOCO: Fósforo (P), Cálcio (Ca) e Magnésio (Mg).\n"
        parecer += "💡 CIÊNCIA DO SOLO: Fósforo = ATP (energia). Cálcio = Parede Celular (firmeza). Magnésio = Clorofila (fotossíntese).\n\n"
    elif dias_campo < 180:
        parecer += "• FASE: Crescimento Vegetativo.\n• FOCO: Nitrogênio (N) e Micronutrientes.\n"
        parecer += "💡 CIÊNCIA DO SOLO: Nitrogênio gera aminoácidos. Atenção ao Molibdênio para metabolizar esse N.\n\n"
    else:
        parecer += "• FASE: Reprodutiva.\n• FOCO: Potássio (K) e Boro (B).\n"
        parecer += "💡 CIÊNCIA DO SOLO: Potássio transporta açúcares para o fruto. Boro garante a viabilidade do pólen.\n\n"

    parecer += f"🌿 CONFORTO TÉRMICO (VPD):\n"
    parecer += f"• VPD Atual: {hoje['vpd']} kPa.\n"
    if hoje['vpd'] > 1.3:
        parecer += "💡 ANÁLISE: VPD ALTO (>1.3). Ar seco. Fechamento estomático preventivo. Interrupção da absorção de Cálcio. Irrigação pulsada recomendada.\n\n"
    elif hoje['vpd'] < 0.4:
        parecer += "💡 ANÁLISE: VPD BAIXO (<0.4). Ar saturado. Transpiração cessa. Risco de gutação e doenças.\n\n"
    else:
        parecer += "💡 ANÁLISE: VPD IDEAL. Planta funcionando como bomba hidráulica eficiente, fixando carbono em taxa máxima.\n\n"

    parecer += f"💧 MANEJO HÍDRICO (ETc):\n"
    parecer += f"• Demanda Real (Semana): {total_etc:.1f} mm.\n"
    parecer += f"💡 FUNDAMENTAÇÃO: Valor exato de perda de água (ET0 x Kc {KC_ATUAL}). Repor para manter turgor celular sem encharcar.\n\n"
    
    parecer += "------------------------------------------------------------\n"
    parecer += f"{conclusao_final}\n"

    return parecer, conclusao_final

# --- 5. EXECUÇÃO PRINCIPAL (API, LOG E ENVIO) ---

def get_agro_data_ultimate():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Erro ao conectar na API: {e}")
        return []

    previsoes_diarias = []
    for i in range(0, min(40, len(data['list'])), 8):
        item = data['list'][i]
        t = item['main']['temp']
        u = item['main']['humidity']
        dt, vpd = calcular_delta_t_e_vpd(t, u)
        
        chuva_acumulada = 0
        for j in range(8):
            if i + j < len(data['list']):
                chuva_acumulada += data['list'][i+j].get('rain', {}).get('3h', 0)
        
        et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408

        previsoes_diarias.append({
            'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
            'temp': t, 'umidade': u, 'vpd': vpd, 'delta_t': dt,
            'vento': item['wind']['speed'] * 3.6,
            'chuva': round(chuva_acumulada, 1),
            'et0': round(et0, 2)
        })
    return previsoes_diarias

def registrar_log_master(previsoes, anotacao, conclusao):
    arquivo = 'caderno_de_campo_master.csv'
    existe = os.path.isfile(arquivo)
    
    # Usa o horário do Brasil para o registro
    data_br = datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y')
    
    try:
        with open(arquivo, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not existe:
                writer.writerow(['Data', 'Temp_C', 'VPD_kPa', 'DeltaT', 'Chuva_mm', 'Manejo_Usuario', 'Parecer_Tecnico'])
            
            conclusao_limpa = conclusao.replace("\n", " | ")
            writer.writerow([
                data_br, 
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
    # Ajusta o horário do título do e-mail
    data_br_formatada = datetime.now(FUSO_BRASIL).strftime('%d/%m')
    
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"💎 RELATÓRIO AGRO-INTEL: {data_br_formatada}"
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
    previsoes = get_agro_data_ultimate()
    
    if previsoes:
        anotacao = ler_atividades_usuario()
        analise_email, conclusao_agronomo = analisar_expert_educativo(previsoes, anotacao)
        
        # Ajusta horário no corpo do e-mail
        data_hora_br = datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y %H:%M')
        
        corpo = f"💎 CONSULTORIA AGRO-INTEL PREMIUM: IBICOARA/BA\n"
        corpo += f"📅 Data/Hora (Bahia): {data_hora_br}\n"
        corpo += "------------------------------------------------------------\n"
        corpo += "📈 PREVISÃO E MONITORAMENTO (5 DIAS):\n"
        for p in previsoes:
            etc = round(p['et0'] * KC_ATUAL, 2)
            corpo += f"{p['data']} | {p['temp']}°C | Chuva: {p['chuva']}mm | ETc (Consumo): {etc}mm\n"
        corpo += f"\n{analise_email}"
        
        enviar_email(corpo)
        registrar_log_master(previsoes, anotacao, conclusao_agronomo)
        print("✅ Processo concluído com precisão.")
    else:
        print("❌ Falha ao obter dados.")
