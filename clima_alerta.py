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

def gerar_conteudo_html(previsoes, anotacao, mudanca, chuva_ant):
    hoje = previsoes[0]
    hoje_dt = datetime.now(FUSO_BRASIL)
    dias = (hoje_dt.date() - DATA_PLANTIO.date()).days
    chuva_total = sum(p['chuva'] for p in previsoes)
    consumo_total = sum(p['et0'] * KC_ATUAL for p in previsoes)
    balanco = chuva_total - consumo_total

    # Textos de Análise
    txt_vpd = "Equilíbrio perfeito. Estômatos operando com máxima condutância." if 0.45 <= hoje['vpd'] <= 1.25 else \
              "Risco de cavitação no xilema." if hoje['vpd'] > 1.25 else \
              "Saturação de vapor. Fluxo de massa interrompido."
    
    txt_dt = "Ideal para preservação da gota e redução de deriva." if 2 <= hoje['delta_t'] <= 8 else \
             "Risco de evaporação instantânea ou baixa deposição."
             
    txt_balanco = "Superávit: Risco de anoxia radicular. Reduza lâmina." if balanco > 0 else \
                  "Déficit: Estresse hídrico. Aumente a reposição."

    # ESTILO CSS (Design Profissional)
    css = """
    <style>
        body { font-family: Arial, sans-serif; color: #333; }
        h2 { color: #2c3e50; border-bottom: 2px solid #27ae60; padding-bottom: 5px; }
        .alerta { background-color: #ffe6e6; border: 1px solid #ffcccc; padding: 10px; color: #cc0000; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th { background-color: #27ae60; color: white; padding: 10px; text-align: left; }
        td { border: 1px solid #ddd; padding: 8px; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .destaque { font-weight: bold; color: #2c3e50; }
        .footer { font-size: 12px; color: #777; margin-top: 20px; text-align: center; }
    </style>
    """

    # CONSTRUÇÃO DO HTML
    html = f"""
    <html>
    <head>{css}</head>
    <body>
        <h2>🏛️ LAUDO TÉCNICO AGRO-INTEL</h2>
        <p><strong>Local:</strong> {CIDADE} | <strong>Data:</strong> {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y %H:%M')}</p>
    """

    if mudanca:
        html += f"""
        <div class="alerta">
            ⚠️ ALERTA: VOLATILIDADE DETECTADA<br>
            Previsão anterior: {chuva_ant:.1f}mm | Atual: {chuva_total:.1f}mm. Ajuste operacional requerido.
        </div>
        """

    # Tabela de Previsão
    html += "<h3>📅 Previsão Semanal (Microclima)</h3><table><tr><th>Data</th><th>Temp</th><th>Chuva</th><th>Consumo (ETc)</th></tr>"
    for p in previsoes:
        html += f"<tr><td>{p['data']}</td><td>{p['temp']}°C</td><td>{p['chuva']}mm</td><td>{round(p['et0']*KC_ATUAL, 2)}mm</td></tr>"
    html += "</table>"

    # Diário
    html += f"<h3>📝 Diário de Campo</h3><p><em>\"{anotacao if anotacao else 'Sem registros manuais.'}\"</em></p>"

    # Tabela de Análise Técnica
    html += """
    <h3>🔬 Diagnóstico e Fundamentação</h3>
    <table>
        <tr>
            <th style="width: 25%;">TÓPICO</th>
            <th style="width: 20%;">VALOR</th>
            <th>DIAGNÓSTICO & CIÊNCIA</th>
        </tr>
    """
    html += f"""
        <tr>
            <td class="destaque">1. VPD (Termodinâmica)</td>
            <td>{hoje['vpd']} kPa</td>
            <td>{txt_vpd}</td>
        </tr>
        <tr>
            <td class="destaque">2. Delta T (Aplicação)</td>
            <td>{hoje['delta_t']} °C</td>
            <td>{txt_dt}</td>
        </tr>
        <tr>
            <td class="destaque">3. Balanço Hídrico (7d)</td>
            <td>{balanco:.1f} mm</td>
            <td>{txt_balanco}</td>
        </tr>
        <tr>
            <td class="destaque">4. Risco Sanitário</td>
            <td>{sum(1 for p in previsoes if p['umid'] > 88)} Janelas</td>
            <td>{'Risco Alto: Umidade favorável ao tubo germinativo.' if sum(1 for p in previsoes if p['umid'] > 88) > 2 else 'Estabilidade: Baixa pressão de inóculo.'}</td>
        </tr>
        <tr>
            <td class="destaque">5. Nutrição (Fisiologia)</td>
            <td>Vegetativo</td>
            <td><strong>Magnésio (Mg):</strong> Centro da Clorofila (ATP). <strong>Nitrogênio (N):</strong> Proteínas estruturais.</td>
        </tr>
        <tr>
            <td class="destaque">6. Relógio Térmico</td>
            <td>{dias * 14.8:.0f} GDA</td>
            <td>Conversão de fotoassimilados em Brix depende do acúmulo térmico.</td>
        </tr>
    </table>
    """

    # Radar
    html += "<h3>🛰️ Radar Regional</h3><ul>"
    for v in CIDADES_VIZINHAS:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={v}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
        try:
            r = requests.get(url).json()
            alerta_vizinho = "🚨" if r.get('rain') else "✅"
            html += f"<li><strong>{v.split(',')[0]}:</strong> {alerta_vizinho} {r['weather'][0]['description']} ({r['main']['temp']}°C)</li>"
        except: continue
    html += "</ul>"
    
    html += "<div class='footer'>Gerado automaticamente pelo Sistema Agro-Intel v7.0</div></body></html>"
    return html

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
        
        # Leitura segura do arquivo
        if os.path.exists('input_atividades.txt'):
             with open('input_atividades.txt', 'r', encoding='utf-8') as f: anot = f.read().strip()
        else: anot = ""
        
        html_content = gerar_conteudo_html(prev, anot, mudou, c_ant)
        
        assunto = f"{'⚠️ ALERTA: MUDANÇA' if mudou else '💎 LAUDO'} - {CIDADE} ({datetime.now(FUSO_BRASIL).strftime('%d/%m')})"
        
        msg = EmailMessage()
        msg['Subject'] = assunto
        msg['From'] = EMAIL_DESTINO
        msg['To'] = EMAIL_DESTINO
        msg.set_content("Seu cliente de e-mail não suporta HTML.") # Fallback
        msg.add_alternative(html_content, subtype='html') # O segredo está aqui
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
            smtp.send_message(msg)
            
        if anot and not MODO_TESTE:
            with open('input_atividades.txt', 'w') as f: f.write("")
    except Exception as e: print(f"Erro: {e}")
