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

def analisar_expert_completo(previsoes):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_perda = sum(p['et0'] * KC_ATUAL for p in previsoes)
    balanco = total_chuva - total_perda
    
    # --- DASHBOARD ---
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🔴 CRÍTICO" if hoje['delta_t'] > 8 else "🟡 ALERTA")
    status_hidr = "🟢 OK" if -5 < balanco < 5 else ("🔴 DÉFICIT" if balanco < -10 else "🟡 REVISAR")
    
    parecer = f"🚦 DASHBOARD OPERACIONAL:\n"
    parecer += f"• Eficiência de Pulverização (Delta T): {status_pulv}\n"
    parecer += f"• Balanço de Irrigação Semanal: {status_hidr}\n\n"
    
    # --- SANIDADE E MOLHAMENTO FOLIAR ---
    parecer += f"🍄 MONITORAMENTO DE SANIDADE (Doenças):\n"
    # Lógica de Molhamento: UR alta e vento calmo impedem a folha de secar
    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88 and p['vento'] < 6)
    parecer += f"• Índice de Molhamento Foliar: {'ALTO' if horas_molhamento > 2 else 'BAIXO'}\n"
    
    if horas_molhamento > 2:
        parecer += "💡 ALERTA: Condições ideais para Orvalho Prolongado. Risco elevado de Botrytis (Mofo Cinzento) e Antracnose. Monitore os frutos maduros.\n\n"
    else:
        parecer += "💡 ANÁLISE: Folhagem com boa taxa de secagem. Risco fúngico reduzido para as próximas horas.\n\n"

    # --- FISIOLOGIA ---
    dias_campo = (datetime.now() - DATA_PLANTIO).days
    gda_total = dias_campo * 14.8 
    progresso = min(round((gda_total / GDA_ALVO_COLHEITA) * 100, 1), 100)
    
    parecer += f"🧬 DESENVOLVIMENTO FISIOLÓGICO:\n"
    parecer += f"• Idade: {dias_campo} dias | Progresso de Safra: {progresso}%\n"
    parecer += f"• Energia Térmica Acumulada: {gda_total:.0f} Graus-Dia.\n\n"
    
    # --- VPD ---
    parecer += f"🌿 CONFORTO PLANTA (VPD):\n"
    parecer += f"• Déficit de Pressão de Vapor: {hoje['vpd']} kPa.\n"
    if hoje['vpd'] > 1.3:
        parecer += "💡 ANÁLISE: VPD Alto. Planta fechando estômatos para evitar desidratação.\n"
    else:
        parecer += "💡 ANÁLISE: Planta em zona de conforto metabólico.\n"

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
    
    analise = analisar_expert_completo(previsoes_diarias)
    corpo = f"💎 CONSULTORIA AGRO-INTEL ULTIMATE: IBICOARA/BA\n"
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
    msg['Subject'] = f"🚀 DASHBOARD OPERACIONAL ULTIMATE: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, os.getenv("GMAIL_PASSWORD"))
        smtp.send_message(msg)

if __name__ == "__main__":
    relatorio = get_agro_data_ultimate()
    enviar_email(relatorio)
    print("✅ Sistema Ultimate com Molhamento Foliar Ativado!")
