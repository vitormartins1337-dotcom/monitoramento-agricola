import requests
import os
import smtplib
import math
import csv
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES ---
DATA_PLANTIO = datetime(2025, 11, 25) 
KC_ATUAL = 0.75 
FUSO_BRASIL = timezone(timedelta(hours=-3))
CIDADE = "Ibicoara, BR"
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"

# --- 2. BANCO DE CONHECIMENTO CIENTÍFICO (FIEL À SUA BASE) ---
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

# --- 4. LEITURA ---
def ler_atividades_usuario():
    arquivo_input = 'input_atividades.txt'
    if os.path.exists(arquivo_input):
        with open(arquivo_input, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        
        # Só limpa o arquivo no relatório da manhã (05h às 08h)
        hora = datetime.now(FUSO_BRASIL).hour
        if (5 <= hora <= 8) and conteudo and conteudo != "Início do caderno de campo":
            with open(arquivo_input, 'w', encoding='utf-8') as f: f.write("")
        return conteudo
    return ""

# --- 5. O CÉREBRO (DECISOR CRUZADO) ---
def revisor_estrategico(vpd, chuva_sensor, texto_usuario):
    texto = texto_usuario.lower()
    usuario_relatou_chuva = any(p in texto for p in ["chuva", "água", "molhou"])
    usuario_adubou = any(p in texto for p in ["adubo", "fertirrigação", "nitrato", "cálcio"])
    tem_praga = any(p in texto for p in FARMACIA_AGRO.keys())
    vpd_baixo = vpd < 0.4
    solo_saturado = chuva_sensor > 5.0 or usuario_relatou_chuva

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

# --- 6. GERAÇÃO DO RELATÓRIO COMPLETO ---
def gerar_relatorio_final(previsoes, anotacao_usuario):
    hoje = previsoes[0]
    dias_campo = (datetime.now(FUSO_BRASIL).date() - DATA_PLANTIO.date()).days
    sintese = revisor_estrategico(hoje['vpd'], hoje['chuva'], anotacao_usuario)
    
    if hoje['vpd'] > 1.3: txt_vpd = FRASES_VPD['alto']
    elif hoje['vpd'] < 0.4: txt_vpd = FRASES_VPD['baixo']
    else: txt_vpd = FRASES_VPD['ideal']

    gda_total = dias_campo * 14.8 
    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88)
    
    parecer = f"🔎 **CONCLUSÃO ESTRATÉGICA (Resumo):**\n"
    parecer += f"{sintese}\n\n"
    parecer += f"📊 **DADOS TÉCNICOS:**\n• VPD: {hoje['vpd']} kPa | Delta T: {hoje['delta_t']}°C\n{txt_vpd}\n\n"
    parecer += f"📝 **DIÁRIO DE CAMPO:**\n• \"{anotacao_usuario if anotacao_usuario else 'Sem registros'}\"\n\n"
    parecer += f"🍄 **MONITORAMENTO FITOSSANITÁRIO:**\n• {horas_molhamento} janelas de orvalho (Risco {'ALTO' if horas_molhamento > 2 else 'BAIXO'}).\n"
    parecer += f"💡 **FUNDAMENTAÇÃO:** Esporos de *Botrytis* e *Antracnose* dependem de filme de água na folha.\n\n"
    
    parecer += f"🛒 **NUTRIÇÃO MINERAL SUGERIDA:**\n"
    if dias_campo < 45:
        parecer += "• FASE: Enraizamento (Início).\n• FOCO: **Fósforo (P)** e **Cálcio (Ca)**.\n💡 **CIÊNCIA DO SOLO:** P = ATP (energia). Ca = Pectatos (firmeza)."
    elif dias_campo < 130:
        parecer += "• FASE: Crescimento Vegetativo.\n• FOCO: **Nitrogênio (N)** e **Magnésio (Mg)**.\n💡 **CIÊNCIA DO SOLO:** N = Aminoácidos. Mg = Centro da Clorofila."
    else:
        parecer += "• FASE: Frutificação.\n• FOCO: **Potássio (K)** e **Boro (B)**.\n💡 **CIÊNCIA DO SOLO:** K = Transporte de açúcares. B = Viabilidade do pólen."
    
    parecer += f"\n\n🧬 **FISIOLOGIA:** Idade {dias_campo} dias | GDA: {gda_total:.0f}\n"
    parecer += f"💧 **HÍDRICO:** Reposição de {sum(p['et0']*KC_ATUAL for p in previsoes):.1f} mm/semana.\n"
    return parecer

# --- 7. NOVA FUNÇÃO: VIGILÂNCIA DE MUDANÇA BRUSCA ---
def verificar_mudanca_brusca(previsoes):
    # Analisa as próximas 6 horas
    proximas = previsoes[:2]
    chuva_imediata = sum(p['chuva'] for p in proximas)
    vento_max = max(p['vento'] for p in proximas)
    
    if chuva_imediata > 3.0 or vento_max > 22.0:
        alerta = f"🚨 **ALERTA DE MUDANÇA BRUSCA DE TEMPO**\n\n"
        alerta += f"O sistema de vigilância detectou condições críticas não previstas:\n"
        alerta += f"• Chuva Iminente: {chuva_imediata} mm\n"
        alerta += f"• Rajadas de Vento: {vento_max} km/h\n\n"
        alerta += "⚠️ **RECOMENDAÇÃO:** Se planejava pulverizar ou fertirrigar agora, REAVALIE IMEDIATAMENTE."
        enviar_email(f"🚨 ALERTA URGENTE: {datetime.now(FUSO_BRASIL).strftime('%H:%M')}", alerta)
    else:
        print("✅ Vigilância: Sem alterações críticas.")

# --- 8. EXECUÇÃO ---
def get_agro_data_ultimate():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    try:
        response = requests.get(url); response.raise_for_status()
        data = response.json()
        previsoes = []
        for i in range(0, min(40, len(data['list'])), 8):
            item = data['list'][i]
            t, u = item['main']['temp'], item['main']['humidity']
            dt, vpd = calcular_delta_t_e_vpd(t, u)
            et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
            chuva = sum([data['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(data['list'])])
            previsoes.append({'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'temp': t, 'umidade': u, 'vpd': vpd, 'delta_t': dt, 'vento': item['wind']['speed']*3.6, 'chuva': round(chuva, 1), 'et0': round(et0, 2)})
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
    previsoes = get_agro_data_ultimate()
    if previsoes:
        hora_agora = datetime.now(FUSO_BRASIL).hour
        
        # RELATÓRIO MATINAL (05h às 08h)
        if 5 <= hora_agora <= 8:
            anotacao = ler_atividades_usuario()
            corpo = gerar_relatorio_final(previsoes, anotacao)
            cabecalho = f"💎 CONSULTORIA AGRO-INTEL PREMIUM\n📅 {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y %H:%M')}\n"
            cabecalho += "-"*60 + "\n"
            for p in previsoes:
                cabecalho += f"{p['data']} | {p['temp']}°C | 🌧️ {p['chuva']}mm | 💧 {round(p['et0']*KC_ATUAL, 2)}mm\n"
            enviar_email(f"💎 RELATÓRIO COMPLETO: {datetime.now(FUSO_BRASIL).strftime('%d/%m')}", cabecalho + "\n" + corpo)
        
        # VIGILÂNCIA (Resto do dia)
        else:
            verificar_mudanca_brusca(previsoes)
