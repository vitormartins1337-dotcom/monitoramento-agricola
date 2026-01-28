import requests
import os
import smtplib
import math
import csv
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES MESTRAS ---
MODO_TESTE = True # Mantenha True para receber o relatório completo agora
DATA_PLANTIO = datetime(2025, 11, 25) 
KC_ATUAL = 0.75 
FUSO_BRASIL = timezone(timedelta(hours=-3))
CIDADE = "Ibicoara, BR"
CIDADES_VIZINHAS = ["Mucugê, BR", "Barra da Estiva, BR", "Piatã, BR"]

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"

# --- 2. BANCO DE CONHECIMENTO CIENTÍFICO (SEM RESUMOS) ---
FARMACIA_AGRO = {
    'botrytis': "💊 **TRATAMENTO (Botrytis):** *Fludioxonil*, *Ciprodinil* ou *Bacillus subtilis*.",
    'antracnose': "💊 **TRATAMENTO (Antracnose):** *Azoxistrobina* + *Difenoconazol*.",
    'ferrugem': "💊 **TRATAMENTO (Ferrugem):** *Tebuconazol*.",
    'ácaro': "💊 **TRATAMENTO (Ácaros):** *Abamectina* ou *Espirodiclofeno*."
}

FRASES_VPD = {
    'alto': "⚠️ **ANÁLISE FÍSICA DETALHADA (VPD ALTO > 1.3 kPa):**\nA atmosfera está drenando água excessivamente. Para evitar cavitação no xilema, a planta fechou os estômatos. \n**Consequência:** Interrupção imediata da fotossíntese (sem entrada de CO2) e travamento da absorção de Cálcio (risco de Tip Burn).",
    'baixo': "⚠️ **ANÁLISE FÍSICA DETALHADA (VPD BAIXO < 0.4 kPa):**\nO ar está saturado. A planta não consegue transpirar. \n**Consequência:** A 'bomba hidráulica' do xilema desliga. Sem transpiração, não há fluxo de massa, ou seja, os nutrientes do solo não sobem para as folhas. Risco elevado de gutação e doenças.",
    'ideal': "✅ **ANÁLISE FÍSICA DETALHADA (VPD IDEAL):**\nTermodinâmica perfeita. A planta opera com máxima condutância estomática, transpirando e fixando carbono simultaneamente. É o momento de maior eficiência no uso da água e fertilizantes."
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

# --- 4. FUNÇÕES DE SUPORTE ---
def ler_atividades_usuario():
    arquivo = 'input_atividades.txt'
    if os.path.exists(arquivo):
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        hora = datetime.now(FUSO_BRASIL).hour
        if not MODO_TESTE and (5 <= hora <= 8) and conteudo and conteudo != "Início do caderno de campo":
            with open(arquivo, 'w', encoding='utf-8') as f: f.write("")
        return conteudo
    return ""

def buscar_radar_regional():
    radar_msg = "🛰️ **9. RADAR AGRO-ESTRATÉGICO (Regional Bahia/Chapada):**\n"
    alerta_v = False
    for vizinho in CIDADES_VIZINHAS:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={vizinho}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
        try:
            r = requests.get(url).json()
            clima = r['weather'][0]['description']
            chuva = r.get('rain', {}).get('1h', 0)
            if chuva > 1.0 or "chuva" in clima:
                radar_msg += f"• **{vizinho.split(',')[0]} (Cerca de 50-80km):** Detectada {clima} ({chuva}mm/h). Monitorar deslocamento de frentes úmidas para Ibicoara.\n"
                alerta_v = True
            else:
                radar_msg += f"• **{vizinho.split(',')[0]}:** Clima {clima}. Sem ameaças imediatas por deslocamento.\n"
        except: continue
    
    radar_msg += "💡 **ANÁLISE REGIONAL:** O monitoramento das cidades vizinhas permite antecipar janelas de pulverização e prever a chegada de frentes frias que alteram a umidade relativa local.\n"
    return radar_msg

def revisor_estrategico(vpd, chuva_s, texto):
    texto = texto.lower()
    usuario_relatou_chuva = any(p in texto for p in ["chuva", "água", "molhou"])
    usuario_adubou = any(p in texto for p in ["adubo", "fertirrigação", "nitrato", "cálcio"])
    tem_praga = any(p in texto for p in FARMACIA_AGRO.keys())
    vpd_baixo = vpd < 0.4
    solo_saturado = chuva_s > 5.0 or usuario_relatou_chuva

    if usuario_adubou and solo_saturado:
        return "🔴 **ERRO ESTRATÉGICO:** Fertirrigação em solo saturado. Ocorre lixiviação (perda) de nutrientes e anoxia radicular."
    elif usuario_adubou and vpd_baixo:
        return "🟡 **ALERTA DE INEFICIÊNCIA:** Nutrição aplicada com VPD Baixo. Sem transpiração, o Cálcio não sobe para o fruto."
    elif not usuario_adubou and vpd_baixo:
        return "⛔ **DIRETRIZ DE BLOQUEIO:** Ar saturado. A planta desligou o metabolismo. **NÃO IRRIGUE HOJE**."
    elif solo_saturado:
        return "🌧️ **MODO DRENAGEM:** Solo com excesso de água. Priorize a oxigenação da raiz (drenagem)."
    elif tem_praga:
        return "🛡️ **ALERTA FITOSSANITÁRIO:** Praga detectada. Verifique o Delta T antes de aplicar defensivos."
    else:
        return "✅ **OPERAÇÃO NOMINAL:** Condições estáveis. Siga o manejo preventivo."

# --- 5. GERAÇÃO DO LAUDO COMPLETO ---
def gerar_relatorio_final(previsoes, anotacao):
    hoje = previsoes[0]
    dias_campo = (datetime.now(FUSO_BRASIL).date() - DATA_PLANTIO.date()).days
    
    sintese = revisor_estrategico(hoje['vpd'], hoje['chuva'], anotacao)
    radar = buscar_radar_regional()
    
    if hoje['vpd'] > 1.3: txt_vpd = FRASES_VPD['alto']
    elif hoje['vpd'] < 0.4: txt_vpd = FRASES_VPD['baixo']
    else: txt_vpd = FRASES_VPD['ideal']

    gda_total = dias_campo * 14.8 
    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88)
    
    # --- MONTAGEM DO E-MAIL ---
    parecer = f"🔎 **1. CONCLUSÃO ESTRATÉGICA (Resumo):**\n"
    parecer += f"{sintese}\n\n"
    
    parecer += f"📊 **2. DADOS TÉCNICOS DO DIA:**\n"
    parecer += f"• VPD: {hoje['vpd']} kPa | Delta T: {hoje['delta_t']}°C\n"
    parecer += f"{txt_vpd}\n\n"
    
    parecer += f"📝 **3. DIÁRIO DE CAMPO:**\n"
    parecer += f"• \"{anotacao if anotacao else 'Sem registros'}\"\n\n"

    parecer += f"🍄 **4. MONITORAMENTO FITOSSANITÁRIO:**\n"
    parecer += f"• {horas_molhamento} janelas de orvalho (Risco {'ALTO' if horas_molhamento > 2 else 'BAIXO'}).\n"
    parecer += f"💡 **FUNDAMENTAÇÃO:** Esporos de *Botrytis* e *Antracnose* dependem de filme de água na folha para emitir o tubo germinativo. O monitoramento de orvalho é mais crítico que a chuva total.\n\n"
    
    parecer += f"🛒 **5. NUTRIÇÃO MINERAL SUGERIDA:**\n"
    if dias_campo < 45:
        parecer += "• FASE: Enraizamento (Início).\n• FOCO: **Fósforo (P)** e **Cálcio (Ca)**.\n"
        parecer += "💡 **CIÊNCIA DO SOLO:** O Fósforo é o gerador de ATP (energia celular) vital para o enraizamento. O Cálcio forma os pectatos da lamela média, a 'cola' que dá firmeza às células."
    elif dias_campo < 130:
        parecer += "• FASE: Crescimento Vegetativo.\n• FOCO: **Nitrogênio (N)** e **Magnésio (Mg)**.\n"
        parecer += "💡 **CIÊNCIA DO SOLO:** O Nitrogênio é o bloco construtor de aminoácidos e proteínas. O Magnésio é o átomo central da molécula de clorofila; sem ele, não há conversão de luz em energia."
    else:
        parecer += "• FASE: Frutificação.\n• FOCO: **Potássio (K)** e **Boro (B)**.\n"
        parecer += "💡 **CIÊNCIA DO SOLO:** O Potássio atua como regulador osmótico e transportador de fotoassimilados (açúcar) da folha para o dreno (fruto). O Boro é crucial para a viabilidade do pólen."
    parecer += "\n\n"
    
    parecer += f"🧬 **6. FISIOLOGIA (Relógio Térmico):**\n"
    parecer += f"• Idade: {dias_campo} dias | GDA Acumulado: {gda_total:.0f}\n"
    parecer += f"💡 **FUNDAMENTAÇÃO:** Monitoramos a eficiência enzimática da planta. A conversão de luz em açúcar (Brix) depende do acúmulo de calor (Graus-Dia).\n\n"
    
    parecer += f"💧 **7. MANEJO HÍDRICO (ETc):**\n"
    parecer += f"• Reposição Real: {sum(p['et0']*KC_ATUAL for p in previsoes):.1f} mm/semana.\n"
    parecer += f"💡 **EXPLICAÇÃO:** É a 'transpiração real', calculada cruzando a evaporação do ambiente com o coeficiente biológico (Kc) da planta.\n\n"

    parecer += f"🛡️ **8. VIGILÂNCIA DE APLICAÇÃO (Delta T):**\n"
    if 2 <= hoje['delta_t'] <= 8:
        parecer += f"✅ Delta T em {hoje['delta_t']}°C. Condição ideal para pulverização. O tamanho da gota será preservado contra evaporação precoce.\n\n"
    else:
        parecer += f"⚠️ Delta T em {hoje['delta_t']}°C. Risco de evaporação rápida (se alto) ou baixa absorção (se baixo). Reavalie o uso de adjuvantes.\n\n"

    parecer += f"{radar}"
    
    return parecer

# --- 6. EXECUÇÃO ---
def get_agro_data():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    try:
        r = requests.get(url).json()
        previsoes = []
        for i in range(0, min(40, len(r['list'])), 8):
            item = r['list'][i]
            t, u = item['main']['temp'], item['main']['humidity']
            dt, vpd = calcular_delta_t_e_vpd(t, u)
            et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
            chuva = sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
            previsoes.append({'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'temp': t, 'vpd': vpd, 'delta_t': dt, 'chuva': round(chuva, 1), 'et0': round(et0, 2), 'umidade': u, 'vento': item['wind']['speed']*3.6})
        return previsoes
    except: return []

def enviar_email(assunto, conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = assunto
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
            smtp.send_message(msg)
    except: pass

if __name__ == "__main__":
    previsoes = get_agro_data()
    if previsoes:
        hora = datetime.now(timezone(timedelta(hours=-3))).hour
        if MODO_TESTE or (5 <= hora <= 8):
            anotacao = ler_atividades_usuario()
            corpo = gerar_relatorio_final(previsoes, anotacao)
            header = f"💎 CONSULTORIA AGRO-INTEL PREMIUM\n📅 {datetime.now(timezone(timedelta(hours=-3))).strftime('%d/%m/%Y %H:%M')}\n"
            header += "-"*60 + "\n"
            for p in previsoes:
                header += f"{p['data']} | {p['temp']}°C | 🌧️ {p['chuva']}mm | 💧 {round(p['et0']*KC_ATUAL, 2)}mm\n"
            enviar_email(f"💎 RELATÓRIO COMPLETO: {datetime.now(timezone(timedelta(hours=-3))).strftime('%d/%m')}", header + "\n" + corpo)
        else:
            # Vigilância vespertina (Alertas rápidos)
            chuva_imediata = previsoes[0]['chuva']
            if chuva_imediata > 3.0:
                enviar_email("🚨 ALERTA DE CHUVA IMINENTE", f"Vigilância detectou {chuva_imediata}mm previstos. Reavalie manejos de campo.")
