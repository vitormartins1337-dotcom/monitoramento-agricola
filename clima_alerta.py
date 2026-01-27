import requests
import os
import smtplib
import math
import csv
from datetime import datetime
from email.message import EmailMessage

# --- CONFIGURAÇÕES DE CAMPO ---
DATA_PLANTIO = datetime(2025, 11, 25) 
T_BASE_BERRIES = 10.0 
GDA_ALVO_COLHEITA = 1200 
KC_ATUAL = 0.75          

# CONFIGURAÇÕES DE API E EMAIL
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
CIDADE = "Ibicoara, BR"

def calcular_delta_t_e_vpd(temp, umidade):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umidade / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    delta_t = round(temp - tw, 1)
    return delta_t, vpd

def ler_atividades_usuario():
    arquivo_input = 'input_atividades.txt'
    if os.path.exists(arquivo_input):
        with open(arquivo_input, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        if conteudo and conteudo != "Início do caderno de campo":
            with open(arquivo_input, 'w', encoding='utf-8') as f:
                f.write("")
            return conteudo
    return "Nenhum manejo registrado hoje."

def processar_gatilhos_inteligentes(texto):
    analise_extra = ""
    texto = texto.lower()
    if "chuva" in texto or "chovendo" in texto or "volume" in texto:
        analise_extra += "⚠️ ALERTA DE LIXIVIAÇÃO: Possível perda de Nitrogênio e Potássio. Monitore a Condutividade Elétrica do solo.\n"
        analise_extra += "⚠️ RISCO FITOSSANITÁRIO: Umidade real alta favorece Botrytis. Atenção ao molhamento foliar prolongado.\n"
    if any(p in texto for p in ["praga", "inseto", "mancha", "lagarta", "ácaro", "fungo"]):
        analise_extra += "🔍 MANEJO MIP: Pressão biológica detectada. Verifique janelas de aplicação via Delta T.\n"
    if any(p in texto for p in ["fertilizante", "adubo", "fertirrigação", "nutriente", "map", "nitrato"]):
        analise_extra += "🧪 EFICIÊNCIA: Adubação em curso. Atenção à saturação do solo para não causar anóxia radicular.\n"
    return analise_extra if analise_extra else "✅ Manejo estável com a fase atual."

def gerar_conclusao_agronomo(hoje, balanco, anotacao, dias_campo):
    """Gera um parecer técnico final simulando a visão do Engenheiro Agrônomo"""
    conclusao = "👨‍🔬 PARECER TÉCNICO DO ENGENHEIRO AGRÔNOMO:\n"
    
    # Lógica de decisão baseada nos dados do dia
    if "chuva" in anotacao.lower():
        conclusao += "Considerando a precipitação real relatada (não prevista), o foco imediato deve ser a drenagem e proteção fungicida. "
    elif hoje['vpd'] > 1.3:
        conclusao += "O alto estresse hídrico atmosférico (VPD) sugere suspensão de fertirrigações pesadas até o conforto térmico retornar. "
    else:
        conclusao += "As condições climáticas atuais favorecem a absorção nutricional. "

    conclusao += f"Com a cultura aos {dias_campo} dias, a prioridade é a manutenção da arquitetura radicular e sanidade das folhas baixeiras."
    
    return conclusao

def analisar_expert_educativo(previsoes, anotacao_usuario):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    balanco = total_chuva - total_etc
    dias_campo = (datetime.now() - DATA_PLANTIO).days
    
    analise_gatilho = processar_gatilhos_inteligentes(anotacao_usuario)
    conclusao_final = gerar_conclusao_agronomo(hoje, balanco, anotacao_usuario, dias_campo)
    
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🔴 CRÍTICO" if hoje['delta_t'] > 8 else "🟡 ALERTA")
    status_hidr = "🟢 OK" if -5 < balanco < 5 else ("🔴 DÉFICIT" if balanco < -10 else "🟡 REVISAR")
    
    parecer = f"🚦 DASHBOARD OPERACIONAL:\n• Pulverização (Delta T): {status_pulv} | Irrigação: {status_hidr}\n\n"
    
    parecer += f"📝 SEU REGISTRO DE CAMPO (GATILHOS):\n• Sua nota: \"{anotacao_usuario}\"\n📢 CONSULTORIA DINÂMICA:\n{analise_gatilho}\n\n"

    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88 and p['vento'] < 6)
    parecer += f"🍄 MONITORAMENTO DE SANIDADE:\n• Índice de Molhamento Foliar: {'ALTO' if horas_molhamento > 2 else 'BAIXO'}\n"
    parecer += f"💡 EXPLICAÇÃO: Fungos requerem umidade. Seu relato sobrepõe a previsão hídrica.\n\n"

    gda_total = dias_campo * 14.8 
    progresso = min(round((gda_total / GDA_ALVO_COLHEITA) * 100, 1), 100)
    parecer += f"🧬 DESENVOLVIMENTO FISIOLÓGICO:\n• Idade: {dias_campo} dias | Progresso: {progresso}%\n\n"
    
    parecer += f"🛒 SUGESTÃO DE FERTILIZAÇÃO MINERAL:\n"
    if dias_campo < 90: parecer += "• FASE: Estabelecimento. FOCO: Fósforo (P) e Cálcio (Ca).\n"
    elif dias_campo < 180: parecer += "• FASE: Crescimento. FOCO: Nitrogênio (N) e Magnésio (Mg).\n"
    else: parecer += "• FASE: Produção. FOCO: Potássio (K) e Boro (B).\n"
    parecer += "💡 EXPLICAÇÃO: Demanda baseada na extração mineral por fase fenológica.\n\n"

    parecer += f"🌿 CONFORTO TÉRMICO (VPD):\n• VPD: {hoje['vpd']} kPa. (Ideal p/ Transpiração)\n\n"
    parecer += f"💧 MANEJO HÍDRICO (Necessidade Real):\n• Consumo Berries (ETc): {total_etc:.1f} mm/semana.\n\n"
    
    # Inserção da Conclusão Final no E-mail
    parecer += "------------------------------------------------------------\n"
    parecer += f"{conclusao_final}\n"

    return parecer, conclusao_final

def get_agro_data_ultimate():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    data = requests.get(url).json()
    previsoes_diarias = []
    for i in range(0, 40, 8):
        item = data['list'][i]
        t, u = item['main']['temp'], item['main']['humidity']
        dt, vpd = calcular_delta_t_e_vpd(t, u)
        previsoes_diarias.append({
            'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
            'temp': t, 'umidade': u, 'vpd': vpd, 'delta_t': dt,
            'vento': item['wind']['speed'] * 3.6,
            'chuva': round(sum([p.get('rain', {}).get('3h', 0) for p in data['list'][i:i+8]]), 1),
            'et0': round(0.0023 * (t + 17.8) * (t ** 0.5) * 0.408, 2)
        })
    return previsoes_diarias

def registrar_log_master(previsoes, anotacao, conclusao):
    arquivo = 'caderno_de_campo_master.csv'
    existe = os.path.isfile(arquivo)
    with open(arquivo, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(['Data', 'VPD', 'Delta_T', 'Manejo_Realizado', 'Parecer_Agronomo'])
        writer.writerow([
            datetime.now().strftime('%d/%m/%Y'), 
            previsoes[0]['vpd'], 
            previsoes[0]['delta_t'], 
            anotacao, 
            conclusao.replace("\n", " ") # Salva o parecer em uma única linha no CSV
        ])

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"💎 PARECER TÉCNICO AGRO: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, os.getenv("GMAIL_PASSWORD"))
        smtp.send_message(msg)

if __name__ == "__main__":
    previsoes = get_agro_data_ultimate()
    anotacao = ler_atividades_usuario()
    # analise agora retorna dois valores: o texto do email e a conclusão separada
    analise_email, conclusao_agronomo = analisar_expert_educativo(previsoes, anotacao)
    
    corpo = f"💎 CONSULTORIA AGRO-INTEL PREMIUM: IBICOARA/BA\n📅 Gerado: {datetime.now().strftime('%d/%m %H:%M')}\n"
    corpo += "------------------------------------------------------------\n"
    corpo += "📈 RESUMO 5 DIAS (TEMPO | CHUVA | CONSUMO PLANTA):\n"
    for p in previsoes:
        etc = round(p['et0'] * KC_ATUAL, 2)
        corpo += f"{p['data']} | {p['temp']}°C | {p['chuva']}mm | Consumo: {etc}mm/dia\n"
    corpo += f"\n{analise_email}"
    
    enviar_email(corpo)
    registrar_log_master(previsoes, anotacao, conclusao_agronomo)
    print("✅ Sistema rodou. Parecer Técnico registrado no Caderno de Campo!")
