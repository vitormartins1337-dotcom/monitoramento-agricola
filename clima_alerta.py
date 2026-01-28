import requests
import os
import smtplib
import math
import csv
import random
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES E PARÂMETROS ---
DATA_PLANTIO = datetime(2025, 11, 25) 
T_BASE_BERRIES = 10.0 
GDA_ALVO_COLHEITA = 1200 
KC_ATUAL = 0.75
FUSO_BRASIL = timezone(timedelta(hours=-3))
CIDADE = "Ibicoara, BR"

# Segredos
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"

# --- 2. BANCO DE CONHECIMENTO AGRONÔMICO (ESTÁTICO E SEGURO) ---

# Farmácia Digital (Sugestão de Ativos)
FARMACIA_AGRO = {
    'botrytis': "💊 **PROTOCOLO FITOSSANITÁRIO (Mofo Cinzento):**\n   • Químicos: *Fludioxonil*, *Ciprodinil* ou *Fenhexamida*.\n   • Biológico: *Bacillus subtilis* (alternância para evitar resistência).",
    'antracnose': "💊 **PROTOCOLO FITOSSANITÁRIO (Antracnose):**\n   • Químicos: *Azoxistrobina* + *Difenoconazol* ou *Mancozebe* (multissítio preventivo).",
    'ferrugem': "💊 **PROTOCOLO FITOSSANITÁRIO (Ferrugem):**\n   • Químicos: *Tebuconazol* ou *Protioconazol*.",
    'oídio': "💊 **PROTOCOLO FITOSSANITÁRIO (Oídio):**\n   • Químicos: *Enxofre*, *Metil Tiofanato* ou *Kasugamicina*.",
    'ácaro': "💊 **PROTOCOLO FITOSSANITÁRIO (Ácaros):**\n   • Químicos: *Abamectina*, *Espirodiclofeno* ou *Propargite*.",
    'lagarta': "💊 **PROTOCOLO FITOSSANITÁRIO (Lagartas):**\n   • Químicos: *Spinosad*, *Clorantraniliprole* ou Biológico *Bt* (*Bacillus thuringiensis*).",
    'tripes': "💊 **PROTOCOLO FITOSSANITÁRIO (Tripes):**\n   • Químicos: *Espinosade* ou *Imidacloprido* (Cuidado com polinizadores!)."
}

# Explicações Científicas de VPD
FRASES_VPD = {
    'alto': "⚠️ **ANÁLISE FÍSICA (VPD ALTO > 1.3 kPa):** A atmosfera está exigindo água demais. A planta fecha os estômatos para não desidratar. **Consequência:** Interrupção da fotossíntese (sem entrada de CO2) e bloqueio do transporte de Cálcio para os frutos (Risco de Tip Burn). Evite adubações salinas hoje.",
    'baixo': "⚠️ **ANÁLISE FÍSICA (VPD BAIXO < 0.4 kPa):** O ar está saturado. A planta não consegue transpirar. **Consequência:** A 'bomba hidráulica' do xilema desliga. Nutrientes do solo não sobem para as folhas. Risco altíssimo de gutação e doenças fúngicas.",
    'ideal': "✅ **ANÁLISE FÍSICA (VPD IDEAL):** Termodinâmica perfeita. A planta opera com máxima condutância estomática. Ela está transpirando (resfriando-se) e fixando carbono simultaneamente. É o momento de maior eficiência na absorção de água e nutrientes."
}

# --- 3. FUNÇÕES MATEMÁTICAS ---
def calcular_delta_t_e_vpd(temp, umidade):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umidade / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    delta_t = round(temp - tw, 1)
    return delta_t, vpd

# --- 4. LEITURA DE ARQUIVO ---
def ler_atividades_usuario():
    arquivo_input = 'input_atividades.txt'
    if os.path.exists(arquivo_input):
        with open(arquivo_input, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        if conteudo and conteudo != "Início do caderno de campo":
            with open(arquivo_input, 'w', encoding='utf-8') as f: f.write("")
            return conteudo
    return "Nenhum manejo registrado hoje."

# --- 5. O CÉREBRO DO ESPECIALISTA (GATILHOS) ---
def processar_analise_profissional(texto, vpd_atual):
    texto = texto.lower()
    analise = ""
    
    # GATILHO 1: Chuva e Hídrico
    if any(p in texto for p in ["chuva", "chovendo", "volume", "água", "molhou"]):
        analise += "⛈️ **IMPACTO HÍDRICO E DE SOLOS:**\n"
        analise += "   • O seu relato de chuva sobrepõe a previsão do sensor. O solo está em Saturação.\n"
        analise += "   • **Risco Químico:** Lixiviação (lavagem) de Nitrogênio e Potássio para camadas profundas.\n"
        analise += "   • **Risco Físico:** Anoxia Radicular. A água ocupou os macroporos, expulsando o oxigênio. A raiz para de respirar e absorver.\n\n"

    # GATILHO 2: Nutrição
    if any(p in texto for p in ["adubo", "fertirrigação", "cálcio", "potássio", "nitrato", "map"]):
        analise += "🧪 **EFICIÊNCIA NUTRICIONAL:**\n"
        if "não" in texto and ("chuva" in texto or "volume" in texto):
             analise += "   • **Decisão Técnica Correta:** Suspender a fertirrigação em solo saturado evitou o desperdício de produto e a salinização da rizosfera.\n"
        elif "chuva" in texto:
             analise += "   • **Alerta:** A chuva pós-aplicação provavelmente lixiviou parte do produto. Monitore a EC do solo amanhã.\n"
        elif vpd_atual < 0.4:
             analise += "   • **Alerta:** Com VPD baixo, a planta não transloca Cálcio/Boro eficientemente para o fruto.\n\n"

    # GATILHO 3: Farmácia (Pragas e Doenças)
    encontrou_praga = False
    for praga, protocolo in FARMACIA_AGRO.items():
        if praga in texto:
            analise += f"{protocolo}\n"
            encontrou_praga = True
    
    if encontrou_praga:
        analise += "   ⚠️ *Nota:* Consulte sempre um Eng. Agrônomo para o receituário oficial (ADAB).\n\n"

    # Conclusão Padrão se nada for detectado
    if not analise:
        analise = "✅ **OPERAÇÃO NOMINAL:** O manejo relatado segue o padrão preventivo. Continue monitorando o Delta T para aplicações.\n"
        
    return analise

# --- 6. GERAÇÃO DO RELATÓRIO ---
def gerar_relatorio_final(previsoes, anotacao_usuario):
    hoje = previsoes[0]
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    dias_campo = (datetime.now(FUSO_BRASIL).date() - DATA_PLANTIO.date()).days
    
    # 1. Processa a Análise Profissional (Trigger Logic)
    parecer_especialista = processar_analise_profissional(anotacao_usuario, hoje['vpd'])
    
    # 2. Seleciona a Frase Científica do VPD
    if hoje['vpd'] > 1.3: txt_vpd = FRASES_VPD['alto']
    elif hoje['vpd'] < 0.4: txt_vpd = FRASES_VPD['baixo']
    else: txt_vpd = FRASES_VPD['ideal']

    # 3. Cálculos Fisiológicos
    gda_total = dias_campo * 14.8 
    gda_hoje = max(hoje['temp'] - T_BASE_BERRIES, 0)
    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88 and p['vento'] < 6)
    risco_sanidade = 'ALTO' if horas_molhamento > 2 else 'BAIXO'

    # --- MONTAGEM DO CORPO DO E-MAIL ---
    parecer = f"🚦 **DASHBOARD OPERACIONAL:**\n"
    parecer += f"• Delta T (Pulverização): {hoje['delta_t']}°C | VPD: {hoje['vpd']} kPa\n"
    parecer += f"{txt_vpd}\n\n"
    
    parecer += f"📝 **REGISTRO DE CAMPO & CONSULTORIA DINÂMICA:**\n"
    parecer += f"• Seu Relato: \"{anotacao_usuario}\"\n"
    parecer += f"👨‍🔬 **PARECER TÉCNICO:**\n{parecer_especialista}\n"
    
    parecer += f"🍄 **MONITORAMENTO FITOSSANITÁRIO:**\n"
    parecer += f"• Risco Fúngico: {risco_sanidade} ({horas_molhamento} janelas de orvalho previstas)\n"
    parecer += f"💡 **FUNDAMENTAÇÃO:** Esporos de *Botrytis* e *Antracnose* dependem de filme de água na folha para emitir o tubo germinativo. O monitoramento de orvalho é mais crítico que a chuva total.\n\n"

    parecer += f"🧬 **FISIOLOGIA (Relógio Térmico):**\n"
    parecer += f"• Idade Real: {dias_campo} dias | GDA Acumulado: {gda_total:.0f} (+{gda_hoje:.1f} hoje)\n"
    parecer += f"💡 **FUNDAMENTAÇÃO:** Monitoramos a eficiência enzimática da planta. A conversão de luz em açúcar (Brix) depende do acúmulo de Graus-Dia dentro da faixa ideal de temperatura.\n\n"

    parecer += f"🛒 **SUGESTÃO DE NUTRIÇÃO MINERAL:**\n"
    if dias_campo < 90:
        parecer += "• FASE: Estabelecimento Radicular.\n• FOCO: **Fósforo (P)** e **Cálcio (Ca)**.\n💡 **CIÊNCIA DO SOLO:** O Fósforo é o gerador de ATP (energia celular) vital para o enraizamento. O Cálcio forma os pectatos da lamela média, a 'cola' que dá firmeza às células e resistência a patógenos."
    elif dias_campo < 180:
        parecer += "• FASE: Crescimento Vegetativo.\n• FOCO: **Nitrogênio (N)** e **Magnésio (Mg)**.\n💡 **CIÊNCIA DO SOLO:** O Nitrogênio é o bloco construtor de aminoácidos e proteínas. O Magnésio é o átomo central da molécula de clorofila."
    else:
        parecer += "• FASE: Enchimento e Maturação.\n• FOCO: **Potássio (K)** e **Boro (B)**.\n💡 **CIÊNCIA DO SOLO:** O Potássio atua como regulador osmótico e transportador de fotoassimilados (açúcar). O Boro é crucial para a viabilidade do tubo polínico."
    parecer += "\n\n"

    parecer += f"💧 **MANEJO HÍDRICO DE PRECISÃO:**\n"
    parecer += f"• Reposição Real (ETc): {total_etc:.1f} mm para a semana.\n"
    parecer += f"💡 **EXPLICAÇÃO:** Este valor é a 'transpiração real' da cultura, calculada cruzando a evaporação do ambiente com o coeficiente biológico (Kc) atual.\n"
    
    return parecer

# --- 7. EXECUÇÃO PRINCIPAL ---
def get_agro_data_ultimate():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    try:
        response = requests.get(url); response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Erro API: {e}")
        return []

    previsoes = []
    for i in range(0, min(40, len(data['list'])), 8):
        item = data['list'][i]
        t, u = item['main']['temp'], item['main']['humidity']
        dt, vpd = calcular_delta_t_e_vpd(t, u)
        et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
        chuva = sum([data['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(data['list'])])
        previsoes.append({'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'temp': t, 'umidade': u, 'vpd': vpd, 'delta_t': dt, 'vento': item['wind']['speed']*3.6, 'chuva': round(chuva, 1), 'et0': round(et0, 2)})
    return previsoes

def registrar_log_master(previsoes, anotacao, parecer):
    arquivo = 'caderno_de_campo_master.csv'
    data_br = datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y')
    try:
        with open(arquivo, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not os.path.isfile(arquivo): writer.writerow(['Data', 'Temp', 'VPD', 'Manejo', 'Parecer'])
            # Limpa o parecer para caber numa linha do Excel
            parecer_limpo = parecer.replace("\n", " ").replace("  ", " ")[:500] 
            writer.writerow([data_br, previsoes[0]['temp'], previsoes[0]['vpd'], anotacao, parecer_limpo])
    except: pass

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"💎 CONSULTORIA PROFISSIONAL: {datetime.now(FUSO_BRASIL).strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
            smtp.send_message(msg)
            smtp.quit()
        print("✅ E-mail enviado com sucesso!")
    except Exception as e: print(f"Erro Email: {e}")

if __name__ == "__main__":
    previsoes = get_agro_data_ultimate()
    if previsoes:
        anotacao = ler_atividades_usuario()
        # Gera o relatório sem depender de IA externa
        corpo_email = gerar_relatorio_final(previsoes, anotacao)
        
        # Cabeçalho do E-mail
        cabecalho = f"💎 CONSULTORIA AGRO-INTEL PREMIUM: IBICOARA/BA\n📅 {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y %H:%M')}\n"
        cabecalho += "-"*60 + "\n📈 PREVISÃO (OPENWEATHER):\n"
        for p in previsoes: cabecalho += f"{p['data']} | {p['temp']}°C | Chuva: {p['chuva']}mm\n"
        
        relatorio_completo = cabecalho + "\n" + corpo_email
        
        enviar_email(relatorio_completo)
        registrar_log_master(previsoes, anotacao, corpo_email)
    else:
        print("❌ Falha ao obter dados.")
