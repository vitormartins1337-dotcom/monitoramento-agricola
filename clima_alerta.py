import requests
import os
from datetime import datetime

# Configurações Atualizadas
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
CIDADE = "Ibicoara, BR" # Sua localização na Bahia

def gerar_analise_profissional(temp, umidade, et0, chuva, vento):
    """Gera uma recomendação técnica personalizada para manejo em Ibicoara."""
    analise = "🩺 ANÁLISE TÉCNICA DO DIA: "
    
    # Lógica de Irrigação
    if et0 > 5.0 and chuva < 2:
        analise += "Evapotranspiração alta. Atenção ao estresse hídrico; reforce a irrigação. "
    elif chuva > 10:
        analise += "Chuva significativa detectada. Considere suspender a irrigação para evitar lixiviação. "
    else:
        analise += "Condições de umidade do solo moderadas. Siga o manejo planejado. "
        
    # Lógica de Pulverização (Janela de aplicação)
    if vento > 15:
        analise += "\n🚫 Vento forte ({:.1f}km/h). Alto risco de deriva. Não pulverizar!".format(vento)
    elif vento >= 3 and vento <= 12:
        analise += "\n✅ Janela ideal para pulverização detectada (Vento estável)."
    else:
        analise += "\n⚠️ Ventos muito baixos. Risco de inversão térmica em áreas de baixada."
        
    return analise

def get_agro_data():
    # Busca dados específicos para Ibicoara
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    response = requests.get(url)
    data = response.json()
    
    if response.status_code != 200: 
        return "Erro ao acessar dados climáticos. Verifique a chave da API."

    # Pega os dados atuais/previsão imediata
    item = data['list'][0]
    temp = item['main']['temp']
    umidade = item['main']['humidity']
    vento = item['wind']['speed'] * 3.6 # Converte m/s para km/h
    chuva = sum([i.get('rain', {}).get('3h', 0) for i in data['list'][:8]]) # Próximas 24h
    
    # Cálculo simplificado de ET0 (Hargreaves-Samani)
    et0 = round(0.0023 * (temp + 17.8) * (temp ** 0.5) * 0.408, 2)
    
    analise = gerar_analise_profissional(temp, umidade, et0, chuva, vento)
    
    return (f"📊 RELATÓRIO AGRO - IBICOARA/BA\n"
            f"📅 {datetime.now().strftime('%d/%m/%Y')}\n"
            f"-----------------------------------\n"
            f"🌡️ Temp: {temp}°C | 💧 UR: {umidade}%\n"
            f"🌱 ET0: {et0} mm/dia | 🌧️ Chuva: {chuva}mm\n"
            f"🌬️ Vento: {vento:.1f} km/h\n\n"
            f"{analise}")

if __name__ == "__main__":
    relatorio = get_agro_data()
    print(relatorio)
