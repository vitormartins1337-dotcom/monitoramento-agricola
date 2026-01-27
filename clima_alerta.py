import requests
import os
import smtplib
import math
from datetime import datetime
from email.message import EmailMessage

# --- CONFIGURAÇÕES DE CAMPO ---
DATA_PLANTIO = datetime(2025, 11, 25) 
T_BASE_BERRIES = 10.0 
GDA_ALVO_COLHEITA = 1200  # Meta de calor para início de safra
KC_ATUAL = 0.75          # Coeficiente de consumo de água da planta

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
    
    dias_campo = (datetime.now() - DATA_PLANTIO).days
    gda_hoje = max(hoje['temp'] - T_BASE_BERRIES, 0)
    # Estimativa acumulada (ajustada para o clima de Ibicoara)
    gda_total = dias_campo * 14.8 
    progresso = min(round((gda_total / GDA_ALVO_COLHEITA) * 100, 1), 100)

    # 1. Dashboard
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🔴 CRÍTICO" if hoje['delta_t'] > 8 else "🟡 ALERTA")
    status_hidr = "🟢 OK" if -5 < balanco < 5 else ("🔴 DÉFICIT" if balanco < -10 else "🟡 REVISAR")
    
    parecer = f"🚦 DASHBOARD OPERACIONAL:\n"
    parecer += f"• Eficiência de Pulverização (Delta T): {status_pulv}\n"
    parecer += f"• Balanço de Irrigação Semanal: {status_hidr}\n\n"
    
    # 2. Fisiologia Explicada
    parecer += f"🧬 DESENVOLVIMENTO FISIOLÓGICO (Relógio da Planta):\n"
    parecer += f"• Idade Real: {dias_campo} dias de campo.\n"
    parecer += f"• Energia Térmica Acumulada (Graus-Dia): {gda_total:.0f} GD.\n"
    parecer += f"• Progresso para Safra: {progresso}% concluído.\n"
    parecer += f"💡 EXPLICAÇÃO: As plantas não seguem o calendário humano, mas sim o acúmulo de calor (Energia Térmica). "
    parecer += f"Hoje, a planta absorveu {gda_hoje:.1f} unidades de energia. Quando atingir 1200 GD, ela completará o ciclo para colheita.\n\n"
    
    # 3. VPD Explicado
    parecer += f"🌿 CONFORTO TÉRMICO E TRANSPIRAÇÃO (VPD):\n"
    parecer += f"• VPD Atual: {hoje['vpd']} kPa.\n"
    if hoje['vpd'] > 1.3:
        parecer += "💡 ANÁLISE: VPD ALTO. O ar está 'sequestrando' água da planta muito rápido. "
        parecer += "Para não desidratar, ela fecha os poros (estômatos). Isso interrompe a fotossíntese e a absorção de nutrientes.\n"
    elif hoje['vpd'] < 0.4:
        parecer += "💡 ANÁLISE: VPD BAIXO. O ar está muito úmido. A planta não consegue transpirar, o que para a 'bomba' que puxa Cálcio e Boro das raízes.\n"
    else:
        parecer += "💡 ANÁLISE: CONFORTO IDEAL. A planta está em plena atividade, respirando e se nutrindo perfeitamente.\n"

    # 4. Manejo Hídrico
    parecer += f"\n💧 MANEJO HÍDRICO (Necessidade Real das Berries):\n"
    parecer += f"• Perda da Planta (ETc) nos próximos 5 dias: {total_etc:.1f} mm.\n"
    parecer += f"• Balanço Final: {'Déficit de' if balanco < 0 else 'Superávit de'} {abs(balanco):.1f} mm.\n"
    parecer += f"💡 EXPLICAÇÃO: A ETc é a 'sede' real da sua planta. O status {status_hidr} indica se a chuva será suficiente ou se você precisa completar via irrigação.\n"

    return parecer

def get_agro_data_final():
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
            'chuva': round(sum([p.get('rain', {}).get('3h', 0) for p in data['list'][i:i+8]]), 1),
            'et0': round(0.0023 * (t + 17.8) * (t ** 0.5) * 0.408, 2)
        })
    
    analise = analisar_expert_educativo(previsoes_diarias)
    corpo = f"💎 CONSULTORIA AGRO-DIGITAL: IBICOARA/BA\n"
    corpo += f"📅 Gerado em: {datetime.now().strftime('%d/%m %H:%M')}\n"
    corpo += "------------------------------------------------------------\n"
    corpo += "📈 RESUMO 5 DIAS (TEMPO | CHUVA | CONSUMO DA PLANTA):\n"
    for p in previsoes_diarias:
        etc = round(p['et0'] * KC_ATUAL, 2)
        corpo += f"{p['data']} | {p['temp']}°C | {p['chuva']}mm | Consumo: {etc}mm/dia\n"
    
    corpo += f"\n{analise}"
    return corpo

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"🚀 DASHBOARD FISIOLÓGICO: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, os.getenv("GMAIL_PASSWORD"))
        smtp.send_message(msg)

if __name__ == "__main__":
    relatorio = get_agro_data_final()
    enviar_email(relatorio)
    print("✅ Sistema Educativo de Precisão Ativado!")
