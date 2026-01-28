import requests
import os
import smtplib
import math
import csv
import random
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES ---
DATA_PLANTIO = datetime(2025, 11, 25) 
T_BASE_BERRIES = 10.0 
GDA_ALVO_COLHEITA = 1200 
KC_ATUAL = 0.75
FUSO_BRASIL = timezone(timedelta(hours=-3))

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
CIDADE = "Ibicoara, BR"

# --- 2. BANCO DE INTELIGÊNCIA (FRASES PROFUNDAS) ---

FRASES_VPD = {
    'alto': [
        "⚠️ **ANÁLISE:** O ar está 'sedento' (VPD Alto). Para se proteger da desidratação, a planta fecha os estômatos. Consequência: A fotossíntese para (sem entrada de CO2) e o transporte de Cálcio é interrompido (risco de Tip Burn).",
        "⚠️ **ANÁLISE:** Estresse Hídrico Atmosférico. A planta gasta energia apenas para se resfriar, sacrificando o enchimento de fruto. Evite adubações salinas agora para não queimar as raízes."
    ],
    'baixo': [
        "⚠️ **ANÁLISE:** Atmosfera saturada (VPD Baixo). A planta não consegue transpirar. Sem transpiração, a 'bomba hidráulica' do xilema desliga, impedindo que nutrientes do solo cheguem às folhas. Risco de gutação e doenças.",
        "⚠️ **ANÁLISE:** Umidade excessiva no ar bloqueia a transpiração. A planta fica turgida, mas estagnada metabolicamente. Cuidado com o excesso de água no solo (anoxia)."
    ],
    'ideal': [
        "✅ **ANÁLISE:** Condição Termodinâmica Perfeita. A planta está transpirando com máxima eficiência, puxando água e nutrientes do solo e fixando carbono nas folhas. Momento de ouro para produção.",
        "✅ **ANÁLISE:** Zona de Conforto Metabólico. Os estômatos estão abertos, garantindo máxima taxa fotossintética e transporte de Cálcio/Boro para os frutos."
    ]
}

FRASES_SANIDADE = {
    'risco': [
        "🍄 **ALERTA BIOLÓGICO:** O clima criou uma câmara úmida ideal. Esporos de *Botrytis* e *Antracnose* precisam de apenas 4-6 horas de folha molhada para germinar. A prevenção é a única defesa agora.",
        "🍄 **ALERTA BIOLÓGICO:** Molhamento foliar prolongado detectado. As hifas dos fungos penetram mais facilmente em tecidos túrgidos e úmidos. Monitore o centro da planta onde a ventilação é menor."
    ],
    'seguro': [
        "🛡️ **CENÁRIO:** O ambiente está hostil para fungos. O vento e a baixa umidade relativa estão secando as folhas rapidamente, quebrando o ciclo de infecção.",
        "🛡️ **CENÁRIO:** Baixa pressão de inóculo prevista. A rápida secagem foliar impede que os esporos desenvolvam o tubo germinativo."
    ]
}

FARMACIA_AGRO = {
    'botrytis': "💊 **FARMÁCIA (Mofo Cinzento):** Ativos sugeridos: *Fludioxonil*, *Ciprodinil* ou *Fenhexamida*. Biológico: *Bacillus subtilis*.",
    'antracnose': "💊 **FARMÁCIA (Antracnose):** Ativos sugeridos: *Azoxistrobina*, *Difenoconazol* ou *Mancozebe* (multissítio).",
    'ferrugem': "💊 **FARMÁCIA (Ferrugem):** Ativos sugeridos: *Tebuconazol* ou *Protioconazol*.",
    'oídio': "💊 **FARMÁCIA (Oídio):** Ativos sugeridos: *Enxofre*, *Metil Tiofanato* ou *Kasugamicina*.",
    'ácaro': "💊 **FARMÁCIA (Ácaros):** Ativos sugeridos: *Abamectina*, *Espirodiclofeno* ou *Propargite*.",
    'lagarta': "💊 **FARMÁCIA (Lagartas):** Ativos sugeridos: *Spinosad*, *Clorantraniliprole* ou *Bt* (*Bacillus thuringiensis*).",
    'tripes': "💊 **FARMÁCIA (Tripes):** Ativos sugeridos: *Espinosade* ou *Imidacloprido* (Cuidado c/ abelhas!)."
}

# --- 3. CÁLCULOS ---
def calcular_delta_t_e_vpd(temp, umidade):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umidade / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    delta_t = round(temp - tw, 1)
    return delta_t, vpd

# --- 4. LEITURA E GATILHOS ---
def ler_atividades_usuario():
    arquivo_input = 'input_atividades.txt'
    if os.path.exists(arquivo_input):
        with open(arquivo_input, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        if conteudo and conteudo != "Início do caderno de campo":
            with open(arquivo_input, 'w', encoding='utf-8') as f: f.write("")
            return conteudo
    return "Nenhum manejo registrado hoje."

def processar_gatilhos_inteligentes(texto):
    analise = ""
    texto_lower = texto.lower()
    
    # Chuva
    if any(p in texto_lower for p in ["chuva", "chovendo", "volume", "água"]):
        analise += "⚠️ **IMPACTO DA CHUVA:** O volume de água altera o potencial osmótico do solo. "
        analise += "1) **Lixiviação:** Nitrogênio e Potássio são lavados para longe da raiz. "
        analise += "2) **Anoxia:** A raiz sem oxigênio para de absorver nutrientes e produzir hormônios de crescimento (Citocininas).\n\n"
    
    # Nutrição
    if any(p in texto_lower for p in ["adubo", "fertirrigação", "cálcio", "nitrato"]):
        analise += "🧪 **ANÁLISE NUTRICIONAL:** A eficiência desta aplicação depende do VPD atual. "
        analise += "Se VPD < 0.4, o Cálcio aplicado não subirá para o fruto. Se VPD > 1.2, evite altas concentrações salinas (EC alta).\n\n"

    # Farmácia
    encontrou_praga = False
    for praga, recomendacao in FARMACIA_AGRO.items():
        if praga in texto_lower:
            analise += f"{recomendacao}\n"
            encontrou_praga = True
    
    if encontrou_praga:
        analise += "⚠️ *Nota:* Consulte sempre um Eng. Agrônomo para receituário local.\n"

    return analise if analise else "✅ Operação nominal. O manejo relatado está coerente com a estabilidade climática."

def gerar_conclusao_agronomo(hoje, anotacao, dias_campo):
    conclusao = "👨‍🔬 **PARECER TÉCNICO CONCLUSIVO:**\n"
    if "chuva" in anotacao.lower():
        conclusao += "O evento pluviométrico domina o manejo de hoje. A prioridade muda de 'Nutrição' para 'Drenagem e Proteção'. Risco de lixiviação exige reposição estratégica posterior. "
    elif hoje['vpd'] > 1.3:
        conclusao += "O fator limitante hoje é o Estresse Térmico. A planta está em modo de economia. Suspenda manejos estressantes e priorize a hidratação. "
    else:
        conclusao += "As condições fisiológicas estão ótimas. A planta está receptiva a bioestimulantes e carga de frutificação. "
    
    conclusao += f"Aos {dias_campo} dias, o foco é equilibrar a relação Fonte (Folha) x Dreno (Fruto)."
    return conclusao

# --- 5. ANÁLISE COMPLETA ---
def analisar_expert_educativo(previsoes, anotacao_usuario):
    hoje = previsoes[0]
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    dias_campo = (datetime.now(FUSO_BRASIL).date() - DATA_PLANTIO.date()).days
    
    analise_gatilho = processar_gatilhos_inteligentes(anotacao_usuario)
    conclusao_final = gerar_conclusao_agronomo(hoje, anotacao_usuario, dias_campo)
    
    # Sorteio de Frases Ricas
    if hoje['vpd'] > 1.3: frase_vpd = random.choice(FRASES_VPD['alto'])
    elif hoje['vpd'] < 0.4: frase_vpd = random.choice(FRASES_VPD['baixo'])
    else: frase_vpd = random.choice(FRASES_VPD['ideal'])
    
    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88 and p['vento'] < 6)
    risco_sanidade = 'ALTO' if horas_molhamento > 2 else 'BAIXO'
    frase_sanidade = random.choice(FRASES_SANIDADE['risco']) if risco_sanidade == 'ALTO' else random.choice(FRASES_SANIDADE['seguro'])

    # --- CORPO DO RELATÓRIO ---
    parecer = f"🚦 **DASHBOARD OPERACIONAL:**\n"
    parecer += f"• Delta T: {hoje['delta_t']}°C ({'🟢 IDEAL' if 2<=hoje['delta_t']<=8 else '🔴 CUIDADO'})\n"
    parecer += f"• VPD: {hoje['vpd']} kPa\n"
    parecer += f"{frase_vpd}\n\n" # Frase rica aqui
    
    parecer += f"📝 **REGISTRO DE CAMPO & ANÁLISE:**\n"
    parecer += f"• Nota: \"{anotacao_usuario}\"\n"
    parecer += f"📢 **CONSULTORIA DINÂMICA:**\n{analise_gatilho}\n\n"

    parecer += f"🍄 **SANIDADE VEGETAL:**\n"
    parecer += f"• Risco: {risco_sanidade} ({horas_molhamento} janelas de orvalho)\n"
    parecer += f"{frase_sanidade}\n\n" # Frase rica aqui

    gda_total = dias_campo * 14.8 
    progresso = min(round((gda_total / GDA_ALVO_COLHEITA) * 100, 1), 100)
    
    parecer += f"🧬 **FISIOLOGIA (Relógio da Planta):**\n"
    parecer += f"• Idade: {dias_campo} dias | Safra: {progresso}%\n"
    parecer += f"• GDA Acumulado: {gda_total:.0f} Graus-Dia\n"
    parecer += f"💡 **CIÊNCIA:** O acúmulo de calor (GDA) dita a velocidade das enzimas. Estamos monitorando a eficiência da conversão de energia solar em açúcares (Brix).\n\n"
    
    parecer += f"🛒 **NUTRIÇÃO MINERAL INTELIGENTE:**\n"
    if dias_campo < 90:
        parecer += "• FASE: Enraizamento e Estrutura.\n"
        parecer += "• FOCO: **Fósforo (P)** e **Cálcio (Ca)**.\n"
        parecer += "💡 **FUNDAMENTAÇÃO:** O Fósforo é vital para gerar ATP (energia química) para o crescimento de raízes novas. O Cálcio forma os 'Pectatos' na parede celular, garantindo a firmeza futura do fruto e resistência a fungos."
    elif dias_campo < 180:
        parecer += "• FASE: Vegetativo e Floração.\n"
        parecer += "• FOCO: **Nitrogênio (N)** e **Magnésio (Mg)**.\n"
        parecer += "💡 **FUNDAMENTAÇÃO:** O Nitrogênio é a base dos aminoácidos. O Magnésio é o átomo central da clorofila; sem ele, a planta não faz fotossíntese eficiente mesmo com sol."
    else:
        parecer += "• FASE: Enchimento e Maturação.\n"
        parecer += "• FOCO: **Potássio (K)** e **Boro (B)**.\n"
        parecer += "💡 **FUNDAMENTAÇÃO:** O Potássio regula a abertura dos estômatos e transporta açúcares das folhas para os frutos. O Boro é essencial para a germinação do pólen e pegamento da flor."
    parecer += "\n\n"

    parecer += f"💧 **MANEJO HÍDRICO (ETc):**\n"
    parecer += f"• Reposição Real Necessária: {total_etc:.1f} mm/semana.\n"
    parecer += f"💡 **CIÊNCIA:** ETc = Evapotranspiração da Cultura. Este valor representa exatamente a água que a planta 'suou' e precisa receber de volta para manter a turgidez celular.\n"
    
    parecer += "------------------------------------------------------------\n"
    parecer += f"{conclusao_final}\n"

    return parecer, conclusao_final

# --- 6. EXECUÇÃO ---
def get_agro_data_ultimate():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    try:
        response = requests.get(url); response.raise_for_status()
        data = response.json()
    except: return []

    previsoes = []
    for i in range(0, min(40, len(data['list'])), 8):
        item = data['list'][i]
        t, u = item['main']['temp'], item['main']['humidity']
        dt, vpd = calcular_delta_t_e_vpd(t, u)
        et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
        chuva = sum([data['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(data['list'])])
        previsoes.append({'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'temp': t, 'umidade': u, 'vpd': vpd, 'delta_t': dt, 'vento': item['wind']['speed']*3.6, 'chuva': round(chuva, 1), 'et0': round(et0, 2)})
    return previsoes

def registrar_log_master(previsoes, anotacao, conclusao):
    arquivo = 'caderno_de_campo_master.csv'
    data_br = datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y')
    try:
        with open(arquivo, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not os.path.isfile(arquivo): writer.writerow(['Data', 'Temp', 'VPD', 'Manejo', 'Parecer'])
            writer.writerow([data_br, previsoes[0]['temp'], previsoes[0]['vpd'], anotacao, conclusao.replace("\n", " ")])
    except: pass

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"💎 RELATÓRIO AGRO-INTEL: {datetime.now(FUSO_BRASIL).strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
            smtp.send_message(msg)
        print("✅ E-mail enviado!")
    except Exception as e: print(e)

if __name__ == "__main__":
    previsoes = get_agro_data_ultimate()
    if previsoes:
        anotacao = ler_atividades_usuario()
        analise, conclusao = analisar_expert_educativo(previsoes, anotacao)
        
        corpo = f"💎 CONSULTORIA AGRO-INTEL PREMIUM: IBICOARA/BA\n📅 {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y %H:%M')}\n"
        corpo += "-"*60 + "\n📈 PREVISÃO 5 DIAS:\n"
        for p in previsoes: corpo += f"{p['data']} | {p['temp']}°C | Chuva: {p['chuva']}mm | ETc: {round(p['et0']*KC_ATUAL,2)}mm\n"
        corpo += f"\n{analise}"
        
        enviar_email(corpo)
        registrar_log_master(previsoes, anotacao, conclusao)
