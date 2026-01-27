import requests
import os
from datetime import datetime

# Configurações de acesso (puxando das Secrets do GitHub)
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
PUSHBULLET_TOKEN = os.getenv("PUSHBULLET_TOKEN")
CIDADE = "Mucuge, BR" # Ajuste para sua cidade exata na Chapada

def get_premium_weather():
    # Chamada para dados atuais e previsão
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    response = requests.get(url)
    data = response.json()
    
    if response.status_code != 200:
        return None

    # Dados Atuais (Primeiro bloco da previsão)
    atual = data['list'][0]
    temp = atual['main']['temp']
    umidade = atual['main']['humidity']
    vento = atual['wind']['speed'] * 3.6 # Converter para km/h
    desc = atual['weather'][0]['description'].capitalize()
    
    # Previsão de Chuva (Acumulado das próximas 24h)
    chuva_prevista = sum([item.get('rain', {}).get('3h', 0) for item in data['list'][:8]])
    
    # Cálculo de ET0 (Evapotranspiração de Referência)
    et0 = round(0.0023 * (temp + 17.8) * (temp ** 0.5) * 0.408, 2)
    
    # --- LÓGICA DE MANEJO AGRONÔMICO ---
    status_rega = "✅ Irrigação Normal"
    if et0 > 5.0 and chuva_prevista < 2:
        status_rega = "⚠️ REFORÇAR REGA (ET0 Alta)"
    elif chuva_prevista > 10:
        status_rega = "🌧️ SUSPENDER REGA (Chuva Prevista)"

    status_pulverizacao = "🚀 Ideal para Pulverizar"
    if vento > 15:
        status_pulverizacao = "🚫 VENTO FORTE (Risco de Deriva)"
    elif vento < 3:
        status_pulverizacao = "⚠️ VENTO BAIXO (Risco de Inversão)"

    # Montagem do Relatório Premium
    relatorio = (
        f"📊 RELATÓRIO AGRO: {CIDADE}\n"
        f"---------------------------\n"
        f"🌡️ Temp: {temp}°C | 💧 UR: {umidade}%\n"
        f"🌬️ Vento: {vento:.1f} km/h ({status_pulverizacao})\n"
        f"🌱 ET0: {et0} mm/dia\n"
        f"🌧️ Chuva 24h: {chuva_prevista:.1f} mm\n"
        f"---------------------------\n"
        f"💡 MANEJO: {status_rega}\n"
        f"☁️ Céu: {desc}"
    )
    return relatorio

def send_push(body):
    msg = {"type": "note", "title": "💎 MONITORAMENTO PREMIUM", "body": body}
    headers = {"Access-Token": PUSHBULLET_TOKEN, "Content-Type": "application/json"}
    requests.post("https://api.pushbullet.com/v2/pushes", json=msg, headers=headers)

if __name__ == "__main__":
    relatorio = get_premium_weather()
    if relatorio:
        send_push(relatorio)
