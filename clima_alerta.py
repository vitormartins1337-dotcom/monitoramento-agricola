import requests
import os
import smtplib
import math
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES DE ALTA PRECISÃO (GPS) ---
MODO_TESTE = True
DATA_PLANTIO = datetime(2025, 11, 25) 
KC_ATUAL = 0.75 
FUSO_BRASIL = timezone(timedelta(hours=-3))

# Local Principal (Sua Fazenda em Ibicoara)
FAZENDA_PRINCIPAL = {
    "nome": "Ibicoara (Sede)",
    "lat": "-13.414", 
    "lon": "-41.285"
}

# Radar Regional (Vizinhança Georreferenciada)
RADAR_GPS = [
    {"nome": "Mucugê", "lat": "-13.005", "lon": "-41.371"},
    {"nome": "Barra da Estiva", "lat": "-13.623", "lon": "-41.326"},
    {"nome": "Piatã", "lat": "-13.154", "lon": "-41.773"},
    {"nome": "Cascavel (Distrito)", "lat": "-13.196", "lon": "-41.445"}
]

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"

# --- 2. MEMÓRIA ESTRATÉGICA ---
def gerenciar_memoria(chuva_atual):
    arq = 'memoria_chuva.txt'
    chuva_ant = 0.0
    if os.path.exists(arq):
        with open(arq, 'r') as f:
            try: chuva_ant = float(f.read().strip())
            except: chuva_ant = 0.0
    with open(arq, 'w') as f: f.write(str(chuva_atual))
    return abs(chuva_atual - chuva_ant) > 3.0, chuva_ant

# --- 3. MOTOR DE CÁLCULO AGRONÔMICO ---
def calc_agro(temp, umid):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umid / 100)
    vpd = round(es - ea, 2)
    # Cálculo psicrométrico simplificado para Delta T
    tw = temp * math.atan(0.151977 * (umid + 8.313659)**0.5) + \
         math.atan(temp + umid) - math.atan(umid - 1.676331) + \
         0.00391838 * (umid)**1.5 * math.atan(0.023101 * umid) - 4.686035
    dt = round(temp - tw, 1)
    return dt, vpd

# --- 4. GERADOR DE LAUDO PROFISSIONAL (HTML) ---
def gerar_conteudo_html(previsoes, anotacao, mudanca, chuva_ant):
    hoje = previsoes[0]
    hoje_dt = datetime.now(FUSO_BRASIL)
    dias = (hoje_dt.date() - DATA_PLANTIO.date()).days
    chuva_total = sum(p['chuva'] for p in previsoes)
    consumo_total = sum(p['et0'] * KC_ATUAL for p in previsoes)
    balanco = chuva_total - consumo_total

    # Textos Técnicos Dinâmicos
    txt_vpd = "Equilíbrio termodinâmico perfeito. Estômatos abertos e fotossíntese ativa." if 0.45 <= hoje['vpd'] <= 1.25 else \
              "Atmosfera muito seca. Risco de fechamento estomático e cavitação." if hoje['vpd'] > 1.25 else \
              "Atmosfera saturada. Transpiração bloqueada. Risco de doenças."
    
    txt_balanco = "Superávit Hídrico: Solo tende à saturação. Risco de asfixia radicular (anoxia)." if balanco > 0 else \
                  "Déficit Hídrico: Demanda maior que a oferta natural. Aumente a irrigação."

    # ESTILO CSS (Visual de Software)
    css = """
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; color: #333; line-height: 1.6; }
        .header { background-color: #27ae60; color: white; padding: 15px; border-radius: 5px 5px 0 0; }
        h2 { margin: 0; font-size: 22px; }
        .meta { font-size: 14px; opacity: 0.9; }
        .alerta { background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 15px; margin: 20px 0; color: #856404; }
        .danger { background-color: #f8d7da; border-left: 5px solid #dc3545; color: #721c24; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }
        th { background-color: #f8f9fa; color: #2c3e50; padding: 10px; border-bottom: 2px solid #ddd; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #eee; }
        tr:nth-child(even) { background-color: #fafafa; }
        .destaque { font-weight: bold; color: #27ae60; }
        .radar-box { background-color: #f1f8e9; padding: 15px; border-radius: 5px; margin-top: 20px; }
        .footer { font-size: 11px; color: #999; margin-top: 30px; text-align: center; border-top: 1px solid #eee; padding-top: 10px; }
    </style>
    """

    html = f"""
    <html>
    <head>{css}</head>
    <body>
        <div class="header">
            <h2>💎 LAUDO TÉCNICO AGRO-INTEL</h2>
            <div class="meta">📍 {FAZENDA_PRINCIPAL['nome']} (GPS: {FAZENDA_PRINCIPAL['lat']}, {FAZENDA_PRINCIPAL['lon']}) | 📅 {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y %H:%M')}</div>
        </div>
    """

    if mudanca:
        html += f"""
        <div class="alerta danger">
            ⚠️ <strong>ALERTA DE VOLATILIDADE CLIMÁTICA</strong><br>
            A previsão de chuva acumulada mudou bruscamente de <strong>{chuva_ant:.1f}mm</strong> para <strong>{chuva_total:.1f}mm</strong> nas últimas horas. Revise o planejamento de campo.
        </div>
        """

    # Tabela 1: Previsão Semanal
    html += "<h3>📅 Microclima Semanal (Ibicoara)</h3><table><tr><th>Data</th><th>Temp</th><th>Chuva</th><th>Consumo (ETc)</th></tr>"
    for p in previsoes:
        html += f"<tr><td>{p['data']}</td><td>{p['temp']}°C</td><td>{p['chuva']}mm</td><td>{round(p['et0']*KC_ATUAL, 2)}mm</td></tr>"
    html += "</table>"

    # Diário
    html += f"<h3>📝 Diário de Campo</h3><div style='background: #eee; padding: 10px; border-left: 3px solid #999;'><em>\"{anotacao if anotacao else 'Sem apontamentos manuais.'}\"</em></div>"

    # Tabela 2: Análise Técnica Profunda
    html += """
    <h3>🔬 Diagnóstico Fisiológico & Estratégico</h3>
    <table>
        <tr><th width="30%">PARÂMETRO</th><th width="20%">VALOR</th><th>INTERPRETAÇÃO TÉCNICA</th></tr>
    """
    html += f"""
        <tr><td class="destaque">1. Termodinâmica (VPD)</td><td>{hoje['vpd']} kPa</td><td>{txt_vpd}</td></tr>
        <tr><td class="destaque">2. Pulverização (Delta T)</td><td>{hoje['delta_t']} °C</td><td>{'✅ Ideal. Gota protegida contra evaporação.' if 2 <= hoje['delta_t'] <= 8 else '⚠️ Risco. Evite pulverizar sem adjuvantes.'}</td></tr>
        <tr><td class="destaque">3. Balanço Hídrico (7d)</td><td>{balanco:.1f} mm</td><td>{txt_balanco}</td></tr>
        <tr><td class="destaque">4. Pressão Sanitária</td><td>{sum(1 for p in previsoes if p['umid'] > 88)} Janelas</td><td>{'🚨 ALTO RISCO. Condições ideais para germinação de esporos fúngicos.' if sum(1 for p in previsoes if p['umid'] > 88) > 2 else '✅ Baixo Risco. Ausência de molhamento foliar contínuo.'}</td></tr>
        <tr><td class="destaque">5. Nutrição (Fase)</td><td>Vegetativo</td><td><strong>Foco: N + Mg.</strong> Nitrogênio para síntese proteica e Magnésio para o centro da molécula de Clorofila.</td></tr>
        <tr><td class="destaque">6. Maturação (GDA)</td><td>{dias * 14.8:.0f} GDA</td><td>Acúmulo térmico definindo a taxa de conversão enzimática de açúcares.</td></tr>
    </table>
    """

    # Radar Regional GPS
    html += "<div class='radar-box'><h3>🛰️ Radar Regional (Georreferenciado)</h3><ul>"
    for local in RADAR_GPS:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={local['lat']}&lon={local['lon']}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
        try:
            r = requests.get(url).json()
            icone = "🌧️" if "chuva" in r['weather'][0]['description'] or r.get('rain') else "🌤️"
            html += f"<li><strong>{local['nome']}:</strong> {icone} {r['weather'][0]['description'].capitalize()} ({r['main']['temp']}°C)</li>"
        except: continue
    html += "</ul><small><em>*Dados obtidos via satélite nas coordenadas exatas de cada localidade.</em></small></div>"
    
    html += "<div class='footer'>Sistema Agro-Intel v8.0 | Precision Agriculture Module</div></body></html>"
    return html

# --- 5. EXECUÇÃO MESTRA ---
def get_agro_data():
    # Busca por coordenadas da FAZENDA_PRINCIPAL
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={FAZENDA_PRINCIPAL['lat']}&lon={FAZENDA_PRINCIPAL['lon']}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    try:
        r = requests.get(url).json()
        previsoes = []
        for i in range(0, 40, 8):
            item = r['list'][i]
            dt, vpd = calc_agro(item['main']['temp'], item['main']['humidity'])
            et0 = 0.0023 * (item['main']['temp'] + 17.8) * (item['main']['temp'] ** 0.5) * 0.408
            chuva = sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
            
            # Formatação de Data Ajustada
            data_obj = datetime.fromtimestamp(item['dt'], tz=timezone.utc).astimezone(FUSO_BRASIL)
            previsoes.append({
                'data': data_obj.strftime('%d/%m'),
                'temp': item['main']['temp'], 'umid': item['main']['humidity'], 'vpd': vpd, 'delta_t': dt, 'chuva': round(chuva, 1), 'et0': round(et0, 2)
            })
        return previsoes
    except Exception as e:
        print(f"Erro na API: {e}")
        return []

if __name__ == "__main__":
    try:
        prev = get_agro_data()
        if prev:
            c_tot = sum(p['chuva'] for p in prev)
            mudou, c_ant = gerenciar_memoria(c_tot)
            
            # Leitura do Diário
            anot = ""
            if os.path.exists('input_atividades.txt'):
                with open('input_atividades.txt', 'r', encoding='utf-8') as f: anot = f.read().strip()
            
            html_content = gerar_conteudo_html(prev, anot, mudou, c_ant)
            
            # Definição do Assunto
            assunto_base = "⚠️ ALERTA: MUDANÇA CLIMÁTICA" if mudou else "💎 LAUDO TÉCNICO DIÁRIO"
            assunto = f"{assunto_base} - {FAZENDA_PRINCIPAL['nome']} ({datetime.now(FUSO_BRASIL).strftime('%d/%m')})"
            
            # Envio
            msg = EmailMessage()
            msg['Subject'] = assunto
            msg['From'] = EMAIL_DESTINO
            msg['To'] = EMAIL_DESTINO
            msg.set_content("Visualização disponível apenas em HTML.")
            msg.add_alternative(html_content, subtype='html')
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
                smtp.send_message(msg)
                print("Laudo GPS enviado com sucesso.")
                
            # Limpeza
            if anot and not MODO_TESTE:
                with open('input_atividades.txt', 'w') as f: f.write("")
    except Exception as e: print(f"Erro Crítico: {e}")
