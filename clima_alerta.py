import requests
import os
import smtplib
import math
from datetime import datetime
from email.message import EmailMessage

# --- CONFIGURAÇÕES DE CAMPO ---
DATA_PLANTIO = datetime(2025, 11, 25) 
T_BASE_BERRIES = 10.0 
GDA_ALVO_COLHEITA = 1200  # Estimativa de calor acumulado para início de safra
KC_ATUAL = 0.75          # Coeficiente da cultura para Berries aos 60-90 dias

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

def analisar_expert_ultimate(previsoes):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    balanco = total_chuva - total_etc
    
    dias_campo = (datetime.now() - DATA_PLANTIO).days
    gda_estimado_total = dias_campo * 14.5 # Média histórica aproximada
    progresso_safra = min(round((gda_estimado_total / GDA_ALVO_COLHEITA) * 100, 1), 100)

    # 1. Dashboard de Operação
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🔴 CRÍTICO" if hoje['delta_t'] > 8 else "🟡 ALERTA")
    status_hidr = "🟢 OK" if -5 < balanco < 5 else ("🔴 DÉFICIT" if balanco < -10 else "🟡 REVISAR")
    
    parecer = f"🚦 DASHBOARD OPERACIONAL:\n"
    parecer += f"• Pulverização (Delta T): {status_pulv} | Balanço Hídrico: {status_hidr}\n\n"
    
    # 2. Fisiologia e Previsão de Safra
    parecer += f"🧬 DESENVOLVIMENTO E SAFRA:\n"
    parecer += f"• Idade da Cultura: {dias_campo} dias.\n"
    parecer += f"• Progresso Fisiológico: {progresso_safra}% para maturação.\n"
    parecer += f"• Energia Térmica Acumulada: ~{gda_estimado_total:.0f} Graus-Dia.\n"
    parecer += f"💡 CONSULTORIA: Fase de expansão vegetativa intensa. Mantenha o equilíbrio de Cálcio e Boro.\n\n"
    
    # 3. Sanidade e Doenças (Molhamento Foliar)
    parecer += f"🍄 ALERTA DE SANIDADE (Berries):\n"
    if hoje['umidade'] > 90 and hoje['vento'] < 5:
        parecer += "• ⚠️ RISCO ALTO: Condição ideal para ORVALHO PROLONGADO (Folha Molhada). Risco de Botrytis.\n"
    else:
        parecer += "• ✅ BAIXO RISCO: Sem previsão de molhamento foliar crítico hoje.\n"
        
    # 4. Manejo Hídrico de Precisão
    parecer += f"\n💧 MANEJO HÍDRICO (Necessidade Real):\n"
    parecer += f"• Perda da Planta (ETc) prevista para a semana: {total_etc:.1f} mm.\n"
    if balanco < 0:
        parecer += f"• ⚠️ REPOSIÇÃO: É necessário irrigar o equivalente a {abs(balanco):.1f} mm para zerar o déficit.\n"
    else:
        parecer += f"• ✅ RESERVA: Solo com excedente hídrico de {balanco:.1f} mm.\n"

    # 5. Conforto Planta (VPD)
    parecer += f"\n🌿 CONFORTO TÉRMICO (VPD):\n"
    parecer += f"• Déficit de Pressão de Vapor: {hoje['vpd']} kPa.\n"
    if hoje['vpd'] > 1.3:
        parecer += "💡 ANÁLISE: Estresse hídrico atmosférico. Planta fechando estômatos.\n"
    else:
        parecer += "💡 ANÁLISE: Conforto ideal para fotossíntese.\n"

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
    
    analise = analisar_expert_ultimate(previsoes_diarias)
    corpo = f"💎 INTELIGÊNCIA AGRO-FISIOLÓGICA ULTIMATE: IBICOARA/BA\n"
    corpo += f"📅 Gerado: {datetime.now().strftime('%d/%m %H:%M')}\n"
    corpo += "------------------------------------------------------------\n"
    corpo += "📈 RESUMO 5 DIAS (TEMPO | CHUVA | PERDA DA PLANTA):\n"
    for p in previsoes_diarias:
        etc_dia = round(p['et0'] * KC_ATUAL, 2)
        corpo += f"{p['data']} | {p['temp']}°C | {p['chuva']}mm | ETc: {etc_dia}mm/dia\n"
    
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
    print("✅ Sistema Ultimate com Manejo Hídrico e Safra Ativado!")
