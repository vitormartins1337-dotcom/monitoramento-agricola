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
    """Lê as anotações do arquivo de texto e limpa para o próximo dia"""
    arquivo_input = 'input_atividades.txt'
    if os.path.exists(arquivo_input):
        with open(arquivo_input, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        if conteudo and conteudo != "Início do caderno de campo":
            # Limpa o arquivo para o próximo registro
            with open(arquivo_input, 'w', encoding='utf-8') as f:
                f.write("")
            return conteudo
    return "Nenhum manejo registrado hoje."

def analisar_expert_educativo(previsoes, anotacao_usuario):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    balanco = total_chuva - total_etc
    
    # 1. DASHBOARD
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🔴 CRÍTICO" if hoje['delta_t'] > 8 else "🟡 ALERTA")
    status_hidr = "🟢 OK" if -5 < balanco < 5 else ("🔴 DÉFICIT" if balanco < -10 else "🟡 REVISAR")
    
    parecer = f"🚦 DASHBOARD OPERACIONAL:\n"
    parecer += f"• Eficiência de Pulverização (Delta T): {status_pulv}\n"
    parecer += f"• Balanço de Irrigação Semanal: {status_hidr}\n"
    parecer += f"💡 EXPLICAÇÃO: O Delta T indica a vida útil da gota de defensivo. Delta T ideal (2-8) garante que o produto não evapore nem escorra.\n\n"
    
    # 2. MANEJO REALIZADO (O que você escreveu no TXT)
    parecer += f"📝 REGISTRO DE MANEJO REALIZADO:\n"
    parecer += f"• Atividade: {anotacao_usuario}\n"
    parecer += f"💡 EXPLICAÇÃO: Este dado foi extraído do seu arquivo de entrada. Ele serve para criarmos um histórico real entre o que foi aplicado e a resposta da planta.\n\n"

    # 3. SANIDADE
    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88 and p['vento'] < 6)
    parecer += f"🍄 MONITORAMENTO DE SANIDADE (Doenças):\n"
    parecer += f"• Índice de Molhamento Foliar: {'ALTO' if horas_molhamento > 2 else 'BAIXO'}\n"
    parecer += f"💡 EXPLICAÇÃO: Fungos precisam de umidade. O índice ALTO indica risco de doenças como Botrytis.\n\n"

    # 4. FISIOLOGIA
    dias_campo = (datetime.now() - DATA_PLANTIO).days
    gda_total = dias_campo * 14.8 
    progresso = min(round((gda_total / GDA_ALVO_COLHEITA) * 100, 1), 100)
    gda_hoje = max(hoje['temp'] - T_BASE_BERRIES, 0)
    
    parecer += f"🧬 DESENVOLVIMENTO FISIOLÓGICO (Relógio da Planta):\n"
    parecer += f"• Idade Real: {dias_campo} dias | Progresso: {progresso}%\n"
    parecer += f"• Energia Térmica Acumulada: {gda_total:.0f} Graus-Dia.\n"
    parecer += f"💡 EXPLICAÇÃO: Hoje a planta absorveu {gda_hoje:.1f} unidades de calor úteis para o seu crescimento.\n\n"
    
    # 5. NUTRIÇÃO
    parecer += f"🛒 SUGESTÃO DE FERTILIZAÇÃO MINERAL:\n"
    if dias_campo < 90:
        parecer += "• FASE: Estabelecimento. FOCO: Fósforo (P) e Cálcio (Ca).\n"
    elif dias_campo < 180:
        parecer += "• FASE: Crescimento. FOCO: Nitrogênio (N) e Magnésio (Mg).\n"
    else:
        parecer += "• FASE: Produção. FOCO: Potássio (K) e Boro (B).\n"
    parecer += "💡 EXPLICAÇÃO: Sugestão baseada na necessidade fisiológica da idade atual da planta.\n\n"

    # 6. VPD
    parecer += f"🌿 CONFORTO TÉRMICO (VPD):\n"
    parecer += f"• Déficit de Pressão de Vapor: {hoje['vpd']} kPa.\n"
    if hoje['vpd'] > 1.3:
        parecer += "💡 EXPLICAÇÃO: VPD ALTO. A planta pode 'travar' a absorção de nutrientes para se proteger.\n\n"
    else:
        parecer += "💡 EXPLICAÇÃO: VPD em zona de conforto metabólico.\n\n"

    # 7. MANEJO HÍDRICO
    parecer += f"💧 MANEJO HÍDRICO (Necessidade Real):\n"
    parecer += f"• Consumo das Berries (ETc) para a semana: {total_etc:.1f} mm.\n"
    parecer += f"💡 EXPLICAÇÃO: A ETc é a sede real da cultura ajustada pelo Coeficiente da Planta (Kc).\n"

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

def registrar_log_master(previsoes, anotacao):
    arquivo = 'caderno_de_campo_master.csv'
    existe = os.path.isfile(arquivo)
    with open(arquivo, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(['Data', 'Temp_Med', 'VPD', 'Delta_T', 'Manejo_Realizado'])
        writer.writerow([datetime.now().strftime('%d/%m/%Y'), previsoes[0]['temp'], previsoes[0]['vpd'], previsoes[0]['delta_t'], anotacao])

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"🚀 DASHBOARD NUTRICIONAL E MANEJO: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, os.getenv("GMAIL_PASSWORD"))
        smtp.send_message(msg)

if __name__ == "__main__":
    previsoes = get_agro_data_ultimate()
    anotacao = ler_atividades_usuario()
    analise = analisar_expert_educativo(previsoes, anotacao)
    
    corpo = f"💎 CONSULTORIA AGRO-INTEL PREMIUM: IBICOARA/BA\n📅 Gerado: {datetime.now().strftime('%d/%m %H:%M')}\n"
    corpo += "------------------------------------------------------------\n"
    corpo += "📈 RESUMO 5 DIAS (TEMPO | CHUVA | CONSUMO PLANTA):\n"
    for p in previsoes:
        etc = round(p['et0'] * KC_ATUAL, 2)
        corpo += f"{p['data']} | {p['temp']}°C | {p['chuva']}mm | Consumo: {etc}mm/dia\n"
    corpo += f"\n{analise}"
    
    enviar_email(corpo)
    registrar_log_master(previsoes, anotacao)
    print("✅ Sistema rodou e maneio foi registrado!")


