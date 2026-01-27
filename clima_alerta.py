import requests
import os
import smtplib
import math
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

def analisar_expert_educativo(previsoes):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    balanco = total_chuva - total_etc
    
    # 1. DASHBOARD OPERACIONAL
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🔴 CRÍTICO" if hoje['delta_t'] > 8 else "🟡 ALERTA")
    status_hidr = "🟢 OK" if -5 < balanco < 5 else ("🔴 DÉFICIT" if balanco < -10 else "🟡 REVISAR")
    
    parecer = f"🚦 DASHBOARD OPERACIONAL:\n"
    parecer += f"• Eficiência de Pulverização (Delta T): {status_pulv}\n"
    parecer += f"• Balanço de Irrigação Semanal: {status_hidr}\n"
    parecer += f"💡 EXPLICAÇÃO: O Delta T indica a vida útil da gota de defensivo. Se estiver fora do ideal (2-8), a gota evapora antes de atingir o alvo ou escorre da folha, causando desperdício de insumos.\n\n"
    
    # 2. SANIDADE E DOENÇAS
    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88 and p['vento'] < 6)
    parecer += f"🍄 MONITORAMENTO DE SANIDADE (Doenças):\n"
    parecer += f"• Índice de Molhamento Foliar: {'ALTO' if horas_molhamento > 2 else 'BAIXO'}\n"
    parecer += f"💡 EXPLICAÇÃO: Fungos como a Botrytis precisam de folha molhada para germinar. O índice ALTO indica que a folha demorará a secar devido à alta umidade e falta de vento, criando a 'ponte' para a infecção nas frutas.\n\n"

    # 3. FISIOLOGIA
    dias_campo = (datetime.now() - DATA_PLANTIO).days
    gda_total = dias_campo * 14.8 
    progresso = min(round((gda_total / GDA_ALVO_COLHEITA) * 100, 1), 100)
    gda_hoje = max(hoje['temp'] - T_BASE_BERRIES, 0)
    
    parecer += f"🧬 DESENVOLVIMENTO FISIOLÓGICO (Relógio da Planta):\n"
    parecer += f"• Idade Real: {dias_campo} dias de campo.\n"
    parecer += f"• Energia Térmica Acumulada: {gda_total:.0f} Graus-Dia.\n"
    parecer += f"• Progresso para Safra: {progresso}% concluído.\n"
    parecer += f"💡 EXPLICAÇÃO: As plantas não seguem o calendário humano, mas sim o acúmulo de calor (Energia Térmica). Hoje, a planta absorveu {gda_hoje:.1f} unidades de energia. Quando atingir {GDA_ALVO_COLHEITA} GD, ela completará o ciclo para colheita.\n\n"
    
    # 4. SUGESTÃO DE FERTILIZAÇÃO MINERAL (NOVO TÓPICO)
    parecer += f"🛒 SUGESTÃO DE FERTILIZAÇÃO MINERAL:\n"
    if dias_campo < 90:
        parecer += "• FASE: Estabelecimento e Enraizamento.\n"
        parecer += "• FOCO DO DIA: Fósforo (P) para energia radicular e Cálcio (Ca) para estrutura celular.\n"
        parecer += "💡 EXPLICAÇÃO: Nesta fase (60-90 dias), a planta está construindo a fundação. O Fósforo é o combustível das raízes. Como o VPD está variável, garanta o Cálcio via fertirrigação, pois ele só se move com a transpiração da planta.\n\n"
    elif dias_campo < 180:
        parecer += "• FASE: Crescimento Vegetativo Ativo.\n"
        parecer += "• FOCO DO DIA: Nitrogênio (N) para biomassa e Magnésio (Mg) para fotossíntese.\n"
        parecer += "💡 EXPLICAÇÃO: A planta está expandindo folhas. O Magnésio é o coração da clorofila; sem ele, a luz de Ibicoara não se transforma em crescimento.\n\n"
    else:
        parecer += "• FASE: Pré-Floração e Frutificação.\n"
        parecer += "• FOCO DO DIA: Potássio (K) para transporte de açúcares e Boro (B) para o pegamento das flores.\n"
        parecer += "💡 EXPLICAÇÃO: O foco agora é encher o fruto. O Potássio é o 'caminhão' que leva o açúcar das folhas para as amoras e mirtilos.\n\n"

    # 5. VPD
    parecer += f"🌿 CONFORTO TÉRMICO E TRANSPIRAÇÃO (VPD):\n"
    parecer += f"• Déficit de Pressão de Vapor: {hoje['vpd']} kPa.\n"
    if hoje['vpd'] > 1.3:
        parecer += "💡 EXPLICAÇÃO: O VPD ALTO indica estresse hídrico atmosférico. A planta fecha os estômatos (poros) para não perder água, o que interrompe a fotossíntese e a absorção de nutrientes como Cálcio e Boro.\n\n"
    else:
        parecer += "💡 EXPLICAÇÃO: O VPD está em zona de conforto. Isso significa que a 'bomba' de transpiração está funcionando, puxando água e nutrientes do solo para os frutos com eficiência máxima.\n\n"

    # 6. MANEJO HÍDRICO
    parecer += f"💧 MANEJO HÍDRICO (Necessidade Real):\n"
    parecer += f"• Consumo das Berries (ETc) para a semana: {total_etc:.1f} mm.\n"
    parecer += f"💡 EXPLICAÇÃO: A ETc é a sede real da sua cultura. Se a chuva não atingir esse valor, você deve suprir a diferença via irrigação para evitar que a planta use suas reservas e diminua o tamanho dos frutos.\n"

    return parecer

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
    
    analise = analisar_expert_educativo(previsoes_diarias)
    corpo = f"💎 CONSULTORIA AGRO-INTEL PREMIUM: IBICOARA/BA\n"
    corpo += f"📅 Gerado em: {datetime.now().strftime('%d/%m %H:%M')}\n"
    corpo += "------------------------------------------------------------\n"
    corpo += "📈 RESUMO 5 DIAS (TEMPO | CHUVA | CONSUMO PLANTA):\n"
    for p in previsoes_diarias:
        etc = round(p['et0'] * KC_ATUAL, 2)
        corpo += f"{p['data']} | {p['temp']}°C | {p['chuva']}mm | Consumo: {etc}mm/dia\n"
    
    corpo += f"\n{analise}"
    return corpo

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"🚀 DASHBOARD NUTRICIONAL: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, os.getenv("GMAIL_PASSWORD"))
        smtp.send_message(msg)

if __name__ == "__main__":
    relatorio = get_agro_data_ultimate()
    enviar_email(relatorio)
    print("✅ Sistema Expert com Nutrição Fisiológica Ativado!")
