import requests
import os
import smtplib
import math
from datetime import datetime
from email.message import EmailMessage

# CONFIGURAÇÕES
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
CIDADE = "Ibicoara, BR"

def calcular_delta_t_e_vpd(temp, umidade):
    # Pressão de saturação de vapor (es)
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    # Pressão real de vapor (ea)
    ea = es * (umidade / 100)
    vpd = round(es - ea, 2)
    
    # Cálculo simplificado de Delta T (Bulbo úmido de Stull)
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    delta_t = round(temp - tw, 1)
    
    return delta_t, vpd

def analisar_premium(previsoes):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    
    # --- 1. SISTEMA DE SEMÁFORO (DASHBOARD VISUAL) ---
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🟡 ALERTA" if hoje['delta_t'] < 2 else "🔴 CRÍTICO")
    status_hidr = "🟢 OK" if -10 < (total_chuva - sum(p['et0'] for p in previsoes)) < 10 else "🟡 REVISAR"
    
    parecer = f"🚦 DASHBOARD DE OPERAÇÃO:\n"
    parecer += f"• Pulverização: {status_pulv} | Irrigação: {status_hidr}\n\n"
    
    # --- 2. CONFORTO TÉRMICO (VPD) ---
    parecer += f"🌿 CONFORTO DA PLANTA (VPD):\n"
    if 0.45 <= hoje['vpd'] <= 1.25:
        parecer += f"• VPD: {hoje['vpd']} kPa (Conforto Ideal). A planta está transpirando e absorvendo nutrientes perfeitamente.\n"
    elif hoje['vpd'] < 0.45:
        parecer += f"• VPD: {hoje['vpd']} kPa (Muito Baixo). Risco de doenças e baixa absorção de cálcio/boro.\n"
    else:
        parecer += f"• VPD: {hoje['vpd']} kPa (Muito Alto). Estresse hídrico! A planta fechou os estômatos para se proteger.\n"

    # --- 3. LOGÍSTICA DE COLHEITA ---
    parecer += f"\n🧺 LOGÍSTICA DE COLHEITA (Amora/Framboesa/Mirtilo):\n"
    chuva_amanha = previsoes[1]['chuva']
    if chuva_amanha > 2:
        parecer += f"• ⚠️ ESTRATÉGIA: Chuva de {chuva_amanha}mm prevista para amanhã. Antecipe a colheita dos frutos maduros HOJE para evitar podridão.\n"
    else:
        parecer += "• ✅ QUALIDADE: Sem previsão de chuva imediata. Frutos manterão boa firmeza pós-colheita.\n"

    # --- 4. PLANO SEMANAL ---
    parecer += f"\n📅 PLANO DE AÇÃO SEMANAL:\n"
    melhor_dia = min(previsoes, key=lambda x: x['vento'])
    parecer += f"• Melhor janela de pulverização: {melhor_dia['data']} (Vento: {melhor_dia['vento']:.1f}km/h).\n"
    if any(p['umidade'] > 88 for p in previsoes):
        parecer += "• Alerta: Risco de fungos nas Berries devido à alta umidade prevista na semana."

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
            'chuva': sum([p.get('rain', {}).get('3h', 0) for p in data['list'][i:i+8]]),
            'et0': round(0.0023 * (t + 17.8) * (t ** 0.5) * 0.408, 2)
        })
    
    analise = analisar_premium(previsoes_diarias)
    corpo = f"💎 AGRO-INTEL PREMIUM: IBICOARA/BA\n"
    corpo += f"📅 Gerado em: {datetime.now().strftime('%d/%m %H:%M')}\n\n"
    corpo += "📈 RESUMO 5 DIAS:\n"
    for p in previsoes_diarias:
        corpo += f"{p['data']}: {p['temp']}°C | Chuva: {p['chuva']:.1f}mm | UR: {p['umidade']}%\n"
    
    corpo += f"\n{analise}"
    return corpo

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"🚀 DASHBOARD AGRO: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    relatorio = get_agro_data_ultimate()
    enviar_email(relatorio)
    print("✅ Sistema Ultimate com Semáforo, VPD e Logística enviado!")
