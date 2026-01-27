import requests
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage

# CONFIGURAÇÕES PROFISSIONAIS
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com" # Seu e-mail
CIDADE = "Ibicoara, BR"

def gerar_analise_profissional(temp, umidade, et0, chuva, vento):
    analise = "🩺 ANÁLISE TÉCNICA DO DIA: "
    if et0 > 5.0 and chuva < 2:
        analise += "Demanda hídrica alta. Reforce a irrigação. "
    elif chuva > 10:
        analise += "Volume de chuva satisfatório. Pode-se suspender a rega. "
    else:
        analise += "Balanço hídrico moderado. Manter cronograma padrão. "
        
    if vento > 15:
        analise += "\n🚫 Risco de deriva elevado! Evite pulverizações."
    else:
        analise += "\n✅ Condições de vento favoráveis para aplicação."
    return analise

def get_agro_data():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    response = requests.get(url)
    data = response.json()
    if response.status_code != 200: return None

    item = data['list'][0]
    temp = item['main']['temp']
    umidade = item['main']['humidity']
    vento = item['wind']['speed'] * 3.6
    chuva = sum([i.get('rain', {}).get('3h', 0) for i in data['list'][:8]])
    et0 = round(0.0023 * (temp + 17.8) * (temp ** 0.5) * 0.408, 2)
    
    analise = gerar_analise_profissional(temp, umidade, et0, chuva, vento)
    
    corpo = (f"📊 RELATÓRIO AGRO - IBICOARA/BA\n"
             f"📅 {datetime.now().strftime('%d/%m/%Y')}\n"
             f"-----------------------------------\n"
             f"🌡️ Temp: {temp}°C | 💧 UR: {umidade}%\n"
             f"🌱 ET0: {et0} mm/dia | 🌧️ Chuva: {chuva}mm\n"
             f"🌬️ Vento: {vento:.1f} km/h\n\n"
             f"{analise}")
    return corpo

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"📊 RELATÓRIO AGRO: {datetime.now().strftime('%d/%m/%Y')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    relatorio = get_agro_data()
    if relatorio:
        enviar_email(relatorio)
        print("✅ Relatório enviado com sucesso!")
