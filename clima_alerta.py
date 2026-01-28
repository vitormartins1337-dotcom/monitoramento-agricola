import requests
import os
import smtplib
import math
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- CONFIGURAÇÕES ---
MODO_TESTE = True 
DATA_PLANTIO = datetime(2025, 11, 25) 
KC_ATUAL = 0.75 
FUSO_BRASIL = timezone(timedelta(hours=-3))
CIDADE = "Ibicoara, BR"
CIDADES_VIZINHAS = ["Mucugê, BR", "Barra da Estiva, BR", "Piatã, BR"]
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"

# --- MEMÓRIA ESTRATÉGICA ---
def gerenciar_memoria(chuva_atual):
    arq = 'memoria_chuva.txt'
    chuva_ant = 0.0
    if os.path.exists(arq):
        with open(arq, 'r') as f:
            try: chuva_ant = float(f.read().strip())
            except: chuva_ant = 0.0
    with open(arq, 'w') as f: f.write(str(chuva_atual))
    return abs(chuva_atual - chuva_ant) > 3.0, chuva_ant

# --- MOTOR DE CÁLCULO ---
def calc_agro(temp, umid):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umid / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umid + 8.313659)**0.5) + \
         math.atan(temp + umid) - math.atan(umid - 1.676331) + \
         0.00391838 * (umid)**1.5 * math.atan(0.023101 * umid) - 4.686035
    dt = round(temp - tw, 1)
    return dt, vpd

def gerar_laudo_profissional(previsoes, anotacao, mudanca, chuva_ant):
    hoje = previsoes[0]
    hoje_dt = datetime.now(FUSO_BRASIL)
    dias = (hoje_dt.date() - DATA_PLANTIO.date()).days
    chuva_total = sum(p['chuva'] for p in previsoes)
    consumo_total = sum(p['et0'] * KC_ATUAL for p in previsoes)
    balanco = chuva_total - consumo_total

    # Definição dos textos de alta robustez
    txt_vpd = ("Equilíbrio perfeito. Estômatos operando com máxima condutância para fixação de CO2 e termorregulação." 
               if 0.45 <= hoje['vpd'] <= 1.25 else 
               "Risco de cavitação no xilema e fechamento estomático defensivo." if hoje['vpd'] > 1.25 else 
               "Saturação de vapor. Fluxo de massa interrompido por falta de gradiente de pressão.")

    # MONTAGEM DA TABELA PROFISSIONAL
    tabela = (
        "| TÓPICO DE ANÁLISE | DIAGNÓSTICO TÉCNICO | FUNDAMENTAÇÃO CIENTÍFICA E IMPACTO |\n"
        "| :--- | :--- | :--- |\n"
        f"| **1. EQUILÍBRIO TERMICO (VPD)** | {hoje['vpd']} kPa | {txt_vpd} |\n"
        f"| **2. JANELA DE APLICAÇÃO (ΔT)** | {hoje['delta_t']} °C | {'Ideal para preservação da integridade da gota e redução de deriva evaporativa.' if 2 <= hoje['delta_t'] <= 8 else 'Risco de evaporação instantânea ou baixa deposição.'} |\n"
        f"| **3. BALANÇO HÍDRICO (7D)** | {balanco:.1f} mm | {'Superávit: Risco de anoxia radicular e lixiviação de Nitratos. Reduza lâmina.' if balanco > 0 else 'Déficit: Estresse hídrico iminente. Aumente a reposição via ETc.'} |\n"
        f"| **4. RISCO SANITÁRIO** | {sum(1 for p in previsoes if p['umid'] > 88)} Janelas | {'Risco Alto: Umidade favorável à emissão do tubo germinativo de Botrytis.' if sum(1 for p in previsoes if p['umid'] > 88) > 2 else 'Estabilidade: Baixa pressão de inóculo por falta de água livre.'} |\n"
        f"| **5. NUTRIÇÃO (FASE)** | Vegetativo | **Magnésio (Mg):** Atua como átomo central da Clorofila para conversão de ATP. **Nitrogênio (N):** Síntese de proteínas estruturais. |\n"
        f"| **6. FISIOLOGIA (GDA)** | {dias * 14.8:.0f} Acumulado | A taxa de conversão de fotoassimilados em Brix é dependente do somatório térmico acumulado na fenologia atual. |\n"
    )

    # Radar Regional
    radar = "\n### 🛰️ RADAR REGIONAL (DIRECIONAMENTO)\n"
    for v in CIDADES_VIZINHAS:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={v}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
        try:
            r = requests.get(url).json()
            radar += f"- **{v.split(',')[0]}:** {r['weather'][0]['description']} ({r['main']['temp']}°C). "
            if r.get('rain'): radar += "🚨 **Precipitação detectada nos vizinhos.**"
            radar += "\n"
        except: continue

    resumo = f"## 📝 DIÁRIO DE CAMPO\n> {anotacao if anotacao else 'Sem registros manuais.'}\n\n"
    if mudanca:
        resumo = f"### ⚠️ ALERTA: VOLATILIDADE DETECTADA\nPrevisão anterior: {chuva_ant:.1f}mm | Atual: {chuva_total:.1f}mm. Ajuste operacional imediato requerido.\n\n" + resumo

    return resumo + tabela + radar

def get_data():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    r = requests.get(url).json()
    previsoes = []
    for i in range(0, 40, 8):
        item = r['list'][i]
        dt, vpd = calc_agro(item['main']['temp'], item['main']['humidity'])
        et0 = 0.0023 * (item['main']['temp'] + 17.8) * (item['main']['temp'] ** 0.5) * 0.408
        chuva = sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
        previsoes.append({
            'data': datetime.fromtimestamp(item['dt'], tz=timezone.utc).astimezone(FUSO_BRASIL).strftime('%d/%m'),
            'temp': item['main']['temp'], 'umid': item['main']['humidity'], 'vpd': vpd, 'delta_t': dt, 'chuva': round(chuva, 1), 'et0': round(et0, 2)
        })
    return previsoes

if __name__ == "__main__":
    try:
        prev = get_data()
        c_tot = sum(p['chuva'] for p in prev)
        mudou, c_ant = gerenciar_memoria(c_tot)
        
        with open('input_atividades.txt', 'r', encoding='utf-8') as f: anot = f.read().strip()
        
        laudo = gerar_laudo_profissional(prev, anot, mudou, c_ant)
        
        assunto = f"{'⚠️ ALERTA: MUDANÇA' if mudou else '💎 LAUDO'} - {CIDADE} ({datetime.now(FUSO_BRASIL).strftime('%d/%m')})"
        
        # Cabeçalho da Previsão Semanal
        header = f"## 🏛️ LAUDO TÉCNICO AGRO-INTEL\n**Local:** {CIDADE} | **Data:** {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y %H:%M')}\n\n"
        header += "| Data | Temp | Chuva | Consumo (ETc) |\n| :--- | :--- | :--- | :--- |\n"
        for p in prev:
            header += f"| {p['data']} | {p['temp']}°C | {p['chuva']}mm | {round(p['et0']*KC_ATUAL, 2)}mm |\n"
        
        msg = EmailMessage()
        msg.set_content(header + "\n" + laudo)
        msg['Subject'] = assunto
        msg['From'] = EMAIL_DESTINO
        msg['To'] = EMAIL_DESTINO
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
            smtp.send_message(msg)
            
        if anot and not MODO_TESTE:
            with open('input_atividades.txt', 'w') as f: f.write("")
    except Exception as e: print(f"Erro: {e}")
