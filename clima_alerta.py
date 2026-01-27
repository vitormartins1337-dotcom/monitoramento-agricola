import requests
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage

# CONFIGURAÇÕES
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
CIDADE = "Ibicoara, BR"

def gerar_analise_profissional(temp, umidade, et0, chuva, vento):
    analise = "🩺 ANÁLISE TÉCNICA: "
    if et0 > 5.0 and chuva < 2:
        analise += "Demanda hídrica alta. Reforce a irrigação. "
    elif chuva > 10:
        analise += "Chuva satisfatória. Suspenda a rega. "
    else:
        analise += "Balanço hídrico moderado. "
        
    if vento > 15:
        analise += "\n🚫 Vento forte! Evite pulverizar."
    else:
        analise += "\n✅ Vento favorável para aplicação."
    return analise

def get_agro_data():
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
        response = requests.get(url)
        data = response.json()
        
        item = data['list'][0]
        temp = item['main']['temp']
        umidade = item['main']['humidity']
        vento = item['wind']['speed'] * 3.6
        chuva = sum([i.get('rain', {}).get('3h', 0) for i in data['list'][:8]])
        et0 = round(0.0023 * (temp + 17.8) * (temp ** 0.5) * 0.408, 2)
        
        analise = gerar_analise_profissional(temp, umidade, et0, chuva, vento)
        
        return (f"📊 RELATÓRIO AGRO - IBICOARA/BA\n"
                f"📅 {datetime.now().strftime('%d/%m/%Y')}\n"
                f"-----------------------------------\n"
                f"🌡️ Temp: {temp}°C | 💧 UR: {umidade}%\n"
                f"🌱 ET0: {et0} mm/dia | 🌧️ Chuva: {chuva}mm\n"
                f"🌬️ Vento: {vento:.1f} km/h\n\n"
                f"{analise}")
    except Exception as e:
        print(f"Erro ao coletar dados: {e}")
        return None

def enviar_email(conteudo):
    try:
        msg = EmailMessage()
        msg.set_content(conteudo)
        msg['Subject'] = f"📊 RELATÓRIO AGRO - {datetime.now().strftime('%d/%m/%Y')}"
        msg['From'] = EMAIL_DESTINO
        msg['To'] = EMAIL_DESTINO

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
            smtp.send_message(msg)
        print("✅ E-mail enviado!")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")

if __name__ == "__main__":
    relatorio = get_agro_data()
    if relatorio:
        enviar_email(relatorio)
