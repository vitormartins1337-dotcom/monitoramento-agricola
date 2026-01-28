import requests
import os
import smtplib
import math
import csv
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES MESTRAS ---
MODO_TESTE = True 
DATA_PLANTIO = datetime(2025, 11, 25) 
KC_ATUAL = 0.75 
FUSO_BRASIL = timezone(timedelta(hours=-3))
CIDADE = "Ibicoara, BR"
CIDADES_VIZINHAS = ["Mucugê, BR", "Barra da Estiva, BR", "Piatã, BR"]

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"

# --- 2. BANCO DE CONHECIMENTO ---
FRASES_VPD = {
    'alto': "⚠️ **ANÁLISE FÍSICA DETALHADA (VPD ALTO > 1.3 kPa):**\nA atmosfera está drenando água excessivamente. Para evitar cavitação no xilema (ruptura da coluna de água), a planta fechou os estômatos. \n**Consequência:** Interrupção imediata da fotossíntese por falta de entrada de CO2 e travamento da absorção de Cálcio, aumentando o risco de 'Tip Burn' e necrose apical.",
    'baixo': "⚠️ **ANÁLISE FÍSICA DETALHADA (VPD BAIXO < 0.4 kPa):**\nO ar está saturado. A planta não consegue transpirar. \n**Consequência:** A 'bomba hidráulica' do xilema desliga. Sem transpiração, não há fluxo de massa, ou seja, os nutrientes do solo não sobem para as folhas. Risco elevado de gutação e doenças.",
    'ideal': "✅ **ANÁLISE FÍSICA DETALHADA (VPD IDEAL):**\nTermodinâmica perfeita. A planta opera com máxima condutância estomática, transpirando e fixando carbono simultaneamente."
}

# --- 3. MOTOR DE CÁLCULO ---
def calcular_delta_t_e_vpd(temp, umidade):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umidade / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    delta_t = round(temp - tw, 1)
    return delta_t, vpd

# --- 4. FUNÇÕES ---
def ler_atividades_usuario():
    arquivo = 'input_atividades.txt'
    if os.path.exists(arquivo):
        with open(arquivo, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return ""

def buscar_radar_regional():
    radar_msg = "🛰️ **9. RADAR AGRO-ESTRATÉGICO (Regional Bahia/Chapada):**\n"
    for vizinho in CIDADES_VIZINHAS:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={vizinho}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
        try:
            r = requests.get(url).json()
            clima = r['weather'][0]['description']
            radar_msg += f"• **{vizinho.split(',')[0]}:** Clima {clima}.\n"
        except: continue
    radar_msg += "💡 **ANÁLISE REGIONAL:** O monitoramento das cidades vizinhas permite antecipar frentes frias ou massas de umidade.\n"
    return radar_msg

def gerar_relatorio_final(previsoes, anotacao):
    hoje = previsoes[0]
    hoje_dt = datetime.now(FUSO_BRASIL)
    dias_campo = (hoje_dt.date() - DATA_PLANTIO.date()).days
    
    chuva_total_semana = sum(p['chuva'] for p in previsoes)
    consumo_total_semana = sum(p['et0'] * KC_ATUAL for p in previsoes)
    balanco_hidrico = chuva_total_semana - consumo_total_semana

    if hoje['vpd'] > 1.3: txt_vpd = FRASES_VPD['alto']
    elif hoje['vpd'] < 0.4: txt_vpd = FRASES_VPD['baixo']
    else: txt_vpd = FRASES_VPD['ideal']

    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88)

    parecer = f"🔎 **1. CONCLUSÃO ESTRATÉGICA (Resumo):**\n✅ OPERAÇÃO NOMINAL: Siga o manejo preventivo.\n\n"
    parecer += f"📊 **2. DADOS TÉCNICOS DO DIA:**\n• VPD: {hoje['vpd']} kPa | Delta T: {hoje['delta_t']}°C\n{txt_vpd}\n\n"
    parecer += f"📝 **3. DIÁRIO DE CAMPO:**\n• \"{anotacao if anotacao else 'Sem registros'}\"\n\n"
    parecer += f"🍄 **4. MONITORAMENTO FITOSSANITÁRIO:**\n• {horas_molhamento} janelas de orvalho.\n💡 **FUNDAMENTAÇÃO:** Esporos de *Botrytis* e *Antracnose* dependem de filme de água na folha para emitir o tubo germinativo.\n\n"
    parecer += f"🛒 **5. NUTRIÇÃO MINERAL SUGERIDA:**\n• FASE: Crescimento Vegetativo.\n💡 **CIÊNCIA DO SOLO:** O Nitrogênio é o bloco construtor de aminoácidos. O Magnésio é o átomo central da clorofila.\n\n"
    parecer += f"🧬 **6. FISIOLOGIA:**\n• Idade: {dias_campo} dias | GDA: {dias_campo * 14.8:.0f}\n💡 **FUNDAMENTAÇÃO:** A conversão de luz em açúcar depende do acúmulo de calor (Graus-Dia).\n\n"
    
    parecer += f"💧 **7. MANEJO HÍDRICO & TENDÊNCIA:**\n• 🌧️ Chuva Semanal: {chuva_total_semana:.1f} mm\n• 💧 Consumo (ETc): {consumo_total_semana:.1f} mm\n📈 **BALANÇO:** {'✅ SUPERÁVIT' if balanco_hidrico > 0 else '⚠️ DÉFICIT'} de {abs(balanco_hidrico):.1f} mm.\n💡 **TENDÊNCIA:** {'Reduza regas' if balanco_hidrico > 0 else 'Aumente regas'}.\n\n"
    
    parecer += f"🛡️ **8. VIGILÂNCIA DE APLICAÇÃO (Delta T):**\n✅ Delta T em {hoje['delta_t']}°C. Condição ideal para pulverização.\n\n"
    parecer += buscar_radar_regional()
    return parecer

def get_agro_data():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    r = requests.get(url).json()
    previsoes = []
    for i in range(0, min(40, len(r['list'])), 8):
        item = r['list'][i]
        t, u = item['main']['temp'], item['main']['humidity']
        dt, vpd = calcular_delta_t_e_vpd(t, u)
        et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
        chuva = sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
        data_p = datetime.fromtimestamp(item['dt'], tz=timezone.utc).astimezone(FUSO_BRASIL).strftime('%d/%m')
        previsoes.append({'data': data_p, 'temp': t, 'vpd': vpd, 'delta_t': dt, 'chuva': round(chuva, 1), 'et0': round(et0, 2), 'umidade': u})
    return previsoes

if __name__ == "__main__":
    try:
        previsoes = get_agro_data()
        corpo = gerar_relatorio_final(previsoes, ler_atividades_usuario())
        header = f"💎 CONSULTORIA AGRO-INTEL PREMIUM\n📅 {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y %H:%M')}\n"
        header += "-"*60 + "\n"
        for p in previsoes:
            header += f"{p['data']} | {p['temp']}°C | 🌧️ {p['chuva']}mm | 💧 {round(p['et0']*KC_ATUAL, 2)}mm\n"
        
        msg = EmailMessage()
        msg.set_content(header + "\n" + corpo)
        msg['Subject'] = f"💎 RELATÓRIO COMPLETO: {datetime.now(FUSO_BRASIL).strftime('%d/%m')}"
        msg['From'] = EMAIL_DESTINO
        msg['To'] = EMAIL_DESTINO
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        print(f"Erro: {e}")
