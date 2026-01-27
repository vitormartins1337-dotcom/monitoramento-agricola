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

def analisar_expert_educativo(previsoes):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    balanco = total_chuva - total_etc
    
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🔴 CRÍTICO" if hoje['delta_t'] > 8 else "🟡 ALERTA")
    status_hidr = "🟢 OK" if -5 < balanco < 5 else ("🔴 DÉFICIT" if balanco < -10 else "🟡 REVISAR")
    
    parecer = f"🚦 DASHBOARD OPERACIONAL:\n"
    parecer += f"• Eficiência de Pulverização (Delta T): {status_pulv}\n"
    parecer += f"• Balanço de Irrigação Semanal: {status_hidr}\n"
    parecer += f"💡 EXPLICAÇÃO: O Delta T indica a vida útil da gota de defensivo. Se estiver fora do ideal (2-8), a gota evapora antes de atingir o alvo ou escorre da folha, causando desperdício de insumos.\n\n"
    
    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88 and p['vento'] < 6)
    parecer += f"🍄 MONITORAMENTO DE SANIDADE (Doenças):\n"
    parecer += f"• Índice de Molhamento Foliar: {'ALTO' if horas_molhamento > 2 else 'BAIXO'}\n"
    parecer += f"💡 EXPLICAÇÃO: Fungos como a Botrytis precisam de folha molhada para germinar. O índice ALTO indica que a folha demorará a secar devido à alta umidade e falta de vento.\n\n"

    dias_campo = (datetime.now() - DATA_PLANTIO).days
    gda_total = dias_campo * 14.8 
    progresso = min(round((gda_total / GDA_ALVO_COLHEITA) * 100, 1), 100)
    gda_hoje = max(hoje['temp'] - T_BASE_BERRIES, 0)
    
    parecer += f"🧬 DESENVOLVIMENTO FISIOLÓGICO (Relógio da Planta):\n"
    parecer += f"• Idade Real: {dias_campo} dias de campo.\n"
    parecer += f"• Energia Térmica Acumulada: {gda_total:.0f} Graus-Dia.\n"
    parecer += f"• Progresso para Safra: {progresso}% concluído.\n"
    parecer += f"💡 EXPLICAÇÃO: Hoje a planta absorveu {gda_hoje:.1f} unidades de energia térmica.\n\n"
    
    parecer += f"🛒 SUGESTÃO DE FERTILIZAÇÃO MINERAL:\n"
    if dias_campo < 90:
        parecer += "• FASE: Estabelecimento. FOCO: Fósforo (P) e Cálcio (Ca).\n"
        parecer += "💡 EXPLICAÇÃO: O Fósforo é o combustível das raízes. Garanta o Cálcio via fertirrigação.\n\n"
    elif dias_campo < 180:
        parecer += "• FASE: Crescimento. FOCO: Nitrogênio (N) e Magnésio (Mg).\n"
    else:
        parecer += "• FASE: Produção. FOCO: Potássio (K) e Boro (B).\n"

    parecer += f"🌿 CONFORTO TÉRMICO E TRANSPIRAÇÃO (VPD):\n"
    parecer += f"• Déficit de Pressão de Vapor: {hoje['vpd']} kPa.\n"
    if hoje['vpd'] > 1.3:
        parecer += "💡 EXPLICAÇÃO: VPD ALTO. Estresse hídrico atmosférico.\n\n"
    else:
        parecer += "💡 EXPLICAÇÃO: VPD em zona de conforto.\n\n"

    parecer += f"💧 MANEJO HÍDRICO (Necessidade Real):\n"
    parecer += f"• Consumo das Berries (ETc) para a semana: {total_etc:.1f} mm.\n"
    parecer += f"💡 EXPLICAÇÃO: A ETc é a sede real da sua cultura.\n"

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
    return previsoes_diarias

def registrar_log_automatico(previsoes):
    hoje = previsoes[0]
    arquivo = 'caderno_de_campo.csv'
    existe = os.path.isfile(arquivo)
    with open(arquivo, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(['Data', 'Temp_Media', 'VPD', 'Delta_T', 'Chuva_Prevista', 'Status_Monitoramento'])
        writer.writerow([datetime.now().strftime('%d/%m/%Y'), hoje['temp'], hoje['vpd'], hoje['delta_t'], hoje['chuva'], 'Monitoramento Diario Enviado'])

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"🚀 DASHBOARD COMPLETO: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, os.getenv("GMAIL_PASSWORD"))
        smtp.send_message(msg)

if __name__ == "__main__":
    previsoes = get_agro_data_ultimate()
    analise = analisar_expert_educativo(previsoes)
    
    corpo = f"💎 CONSULTORIA AGRO-INTEL PREMIUM: IBICOARA/BA\n📅 Gerado: {datetime.now().strftime('%d/%m %H:%M')}\n"
    corpo += "------------------------------------------------------------\n"
    corpo += "📈 RESUMO 5 DIAS:\n"
    for p in previsoes:
        etc = round(p['et0'] * KC_ATUAL, 2)
        corpo += f"{p['data']} | {p['temp']}°C | {p['chuva']}mm | Consumo: {etc}mm/dia\n"
    corpo += f"\n{analise}"
    
    enviar_email(corpo)
    registrar_log_automatico(previsoes)
    print("✅ Sistema rodou e log foi salvo automaticamente!")
