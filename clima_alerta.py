import requests
import os
from datetime import datetime

# As chaves serão puxadas das "Secrets" do GitHub por segurança
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
PUSHBULLET_TOKEN = os.getenv("PUSHBULLET_TOKEN")
CIDADE = "Sua Cidade, BR" 

def get_weather():
    url = f"https://api.openweathermap.org/data/2.5/weather?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    response = requests.get(url)
    data = response.json()
    
    if response.status_code != 200:
        return None

    temp = data['main']['temp']
    umidade = data['main']['humidity']
    desc = data['weather'][0]['description'].capitalize()
    
    # Cálculo simplificado de ET0 (Evapotranspiração)
    et0 = round(0.0023 * (temp + 17.8) * (temp ** 0.5) * 0.408, 2)
    
    return f"🌡️ {temp}°C | 💧 {umidade}% UR\n☁️ {desc}\n🌱 ET0: {et0} mm/dia"

def send_push(body):
    msg = {"type": "note", "title": f"Relatório Diário: {CIDADE}", "body": body}
    headers = {"Access-Token": PUSHBULLET_TOKEN, "Content-Type": "application/json"}
    requests.post("https://api.pushbullet.com/v2/pushes", json=msg, headers=headers)

if __name__ == "__main__":
    relatorio = get_weather()
    if relatorio:
        send_push(relatorio)
