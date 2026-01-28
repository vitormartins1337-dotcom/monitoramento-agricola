    import requests
import os
import smtplib
import math
import csv
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES GERAIS ---
DATA_PLANTIO = datetime(2025, 11, 25) 
KC_ATUAL = 0.75 
FUSO_BRASIL = timezone(timedelta(hours=-3))
CIDADE = "Ibicoara, BR"

# Credenciais
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"

# --- 2. BIBLIOTECA DE CONHECIMENTO CIENTÍFICO (HARD-CODED) ---
# Este é o "Cérebro" que garante a profundidade das explicações.

TEXTOS_CIENCIA = {
    'vpd_baixo': """
    🔴 **ANÁLISE TERMODINÂMICA (VPD < 0.4 kPa): BLOQUEIO DE TRANSPIRAÇÃO**
    • **O Fenômeno:** A atmosfera está saturada de umidade. O déficit de pressão de vapor é nulo.
    • **Impacto Fisiológico:** A planta perde a capacidade de transpirar. Sem transpiração, a "bomba hidráulica" do xilema desliga.
    • **Consequência Nutricional:** O fluxo de massa para. O Cálcio e o Boro (imóveis) NÃO sobem do solo para os frutos/folhas novas.
    • **Risco Sanitário:** A ausência de transpiração gera pressão radicular positiva, causando "Gutação" (gotas nas bordas das folhas), porta de entrada para bactérias.
    """,
    'vpd_alto': """
    🔥 **ANÁLISE TERMODINÂMICA (VPD > 1.4 kPa): ESTRESSE HÍDRICO ATMOSFÉRICO**
    • **O Fenômeno:** O ar está excessivamente seco ("sedento" por água).
    • **Impacto Fisiológico:** Para evitar a desidratação (plasmólise), a planta fecha os estômatos imediatamente.
    • **Consequência Metabólica:** Com estômatos fechados, cessa a entrada de CO2. A fotossíntese para. A planta consome suas reservas de açúcar apenas para respirar e se manter viva, sem gerar crescimento.
    """,
    'vpd_ideal': """
    ✅ **ANÁLISE TERMODINÂMICA (VPD IDEAL): MÁXIMA EFICIÊNCIA METABÓLICA**
    • **O Cenário:** Equilíbrio perfeito entre temperatura e umidade.
    • **Fisiologia:** Os estômatos estão 100% abertos. A planta transpira (resfria-se) e absorve CO2 simultaneamente.
    • **Nutrição:** O fluxo de xilema está em velocidade máxima, transportando nutrientes do solo para os drenos (frutos/folhas) com eficiência total.
    """,
    'nutri_raiz': """
    🛒 **RECOMENDAÇÃO NUTRICIONAL (Fase: Estabelecimento/Enraizamento)**
    • **Elementos Chave:** Fósforo (P) e Cálcio (Ca).
    • **Explicação Bioquímica:** O Fósforo é o componente base do ATP (Adenosina Trifosfato), a "moeda de energia" que a planta gasta para emitir raízes novas no solo. O Cálcio é estrutural: ele forma os Pectatos de Cálcio na lamela média, agindo como o "cimento" que cola as células novas, garantindo tecidos firmes e resistentes a fungos de solo.
    """,
    'nutri_veg': """
    🛒 **RECOMENDAÇÃO NUTRICIONAL (Fase: Crescimento Vegetativo)**
    • **Elementos Chave:** Nitrogênio (N) e Magnésio (Mg).
    • **Explicação Bioquímica:** O Nitrogênio é a base para a síntese de Aminoácidos e Proteínas, vitais para a expansão foliar. O Magnésio é o átomo central da molécula de Clorofila. Sem Mg suficiente, a planta não consegue converter a luz solar em energia química, mesmo com sol pleno (Clorose intervenal).
    """,
    'nutri_fruto': """
    🛒 **RECOMENDAÇÃO NUTRICIONAL (Fase: Frutificação/Maturação)**
    • **Elementos Chave:** Potássio (K) e Boro (B).
    • **Explicação Bioquímica:** O Potássio é o "caminhoneiro" da planta: ele carrega os fotoassimilados (açúcares) da folha para o dreno (fruto), garantindo Brix e peso. O Boro é essencial para a viabilidade do tubo polínico e divisão celular no fruto jovem.
    """
}

FARMACIA_AGRO = {
    'botrytis': "🦠 **ALERTA DE PATÓGENO (Botrytis cinerea):** Fungo necrotrófico. Exige filme de água para germinar. \n   • **Controle Químico:** *Fludioxonil* (contato) ou *Ciprodinil* (sistêmico).\n   • **Controle Biológico:** *Bacillus subtilis* (competição por espaço).",
    'antracnose': "🦠 **ALERTA DE PATÓGENO (Colletotrichum spp):** Esporos se espalham por respingos.\n   • **Controle:** *Azoxistrobina* (Estrobilurina) + *Difenoconazol* (Triazol).",
    'ferrugem': "🦠 **ALERTA DE PATÓGENO (Ferrugem):** Pústulas alaranjadas.\n   • **Controle:** *Tebuconazol* ou *Ciproconazol*.",
}

# --- 3. CÁLCULOS FÍSICOS ---
def calcular_delta_t_e_vpd(temp, umidade):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umidade / 100)
    vpd = round(es - ea, 2)
    
    # Cálculo Delta T (Wet Bulb)
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
        # Limpa arquivo apenas se for processamento matinal (05-08h)
        hora = datetime.now(FUSO_BRASIL).hour
        if 5 <= hora <= 8 and conteudo != "Início do caderno de campo":
            with open(arquivo, 'w', encoding='utf-8') as f: f.write("")
            return conteudo
    return ""

def enviar_email(assunto, corpo):
    msg = EmailMessage()
    msg.set_content(corpo)
    msg['Subject'] = assunto
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
            smtp.send_message(msg)
            smtp.quit()
        print("✅ E-mail enviado.")
    except Exception as e: print(f"Erro Email: {e}")

def get_agro_data():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    try:
        r = requests.get(url); r.raise_for_status()
        return r.json()
    except: return None

# --- 5. INTELIGÊNCIA DE ANÁLISE PROFUNDA ---
def gerar_laudo_tecnico(previsoes, anotacao):
    hoje = previsoes[0]
    dias_campo = (datetime.now(FUSO_BRASIL).date() - DATA_PLANTIO.date()).days
    
    # --- A. ANÁLISE DE CAMPO (INPUT DO USUÁRIO) ---
    texto = anotacao.lower()
    analise_campo = ""
    
    # Lógica de Decisão Cruzada
    usuario_relatou_chuva = any(x in texto for x in ["chuva", "água", "molhou"])
    usuario_adubou = any(x in texto for x in ["adubo", "fertirrigação", "nitrato", "cálcio"])
    solo_saturado = hoje['chuva'] > 5.0 or usuario_relatou_chuva
    
    if usuario_adubou and solo_saturado:
        analise_campo += "🔴 **DIAGNÓSTICO CRÍTICO (ERRO DE MANEJO):**\n"
        analise_campo += "   O relato indica fertirrigação em solo saturado. Isso resulta em:\n"
        analise_campo += "   1. **Lixiviação:** Os ânions (Nitrato, Sulfato) são repelidos pelas cargas negativas do solo e lavados pela água.\n"
        analise_campo += "   2. **Anoxia:** A raiz sem oxigênio não produz ATP para absorção ativa de nutrientes.\n\n"
    elif not usuario_adubou and solo_saturado:
        analise_campo += "✅ **DECISÃO TÉCNICA ASSERTIVA:**\n"
        analise_campo += "   A suspensão da fertirrigação foi correta. Em solos saturados, a aplicação aumentaria a condutividade elétrica (EC) sem absorção, causando estresse salino.\n\n"
    elif not usuario_adubou and hoje['vpd'] < 0.4:
        analise_campo += "⛔ **DIRETRIZ DE BLOQUEIO OPERACIONAL:**\n"
        analise_campo += "   O ar está saturado. A planta não tem capacidade física de puxar solução do solo. Qualquer irrigação hoje é desperdício e risco sanitário.\n\n"
    else:
        analise_campo += "✅ **OPERAÇÃO EM REGIME NOMINAL:**\n   O manejo segue padrões preventivos. Acompanhe a evolução do Delta T.\n\n"

    # Verificação de Pragas no texto
    for praga, texto_tec in FARMACIA_AGRO.items():
        if praga in texto: analise_campo += f"{texto_tec}\n\n"

    # --- B. SELEÇÃO DOS TEXTOS CIENTÍFICOS ---
    if hoje['vpd'] > 1.4: texto_vpd = TEXTOS_CIENCIA['vpd_alto']
    elif hoje['vpd'] < 0.4: texto_vpd = TEXTOS_CIENCIA['vpd_baixo']
    else: texto_vpd = TEXTOS_CIENCIA['vpd_ideal']

    if dias_campo < 45: texto_nutri = TEXTOS_CIENCIA['nutri_raiz']
    elif dias_campo < 130: texto_nutri = TEXTOS_CIENCIA['nutri_veg']
    else: texto_nutri = TEXTOS_CIENCIA['nutri_fruto']

    # --- C. DADOS COMPLEMENTARES ---
    gda_total = dias_campo * 14.8
    horas_orvalho = sum(1 for p in previsoes if p['umidade'] > 88)
    
    # --- D. MONTAGEM DO LAUDO FINAL ---
    laudo = f"🏛️ **LAUDO TÉCNICO AGRO-INTEL PREMIUM**\n"
    laudo += f"📍 Unidade: {CIDADE} | 📆 Idade: {dias_campo} dias\n\n"
    
    laudo += f"🔎 **1. ANÁLISE DO ENGENHEIRO (Manejo vs Clima):**\n"
    laudo += f"Registro: \"{anotacao if anotacao else 'Sem registros'}\"\n"
    laudo += f"{analise_campo}"
    laudo += "-"*50 + "\n"
    
    laudo += f"🌡️ **2. FISIOLOGIA E CLIMATOLOGIA:**\n"
    laudo += f"• VPD Atual: {hoje['vpd']} kPa | Delta T: {hoje['delta_t']}°C\n"
    laudo += f"{texto_vpd}\n" # Aqui entra o texto gigante e explicativo
    
    laudo += f"💊 **3. FITOSSANIDADE (Previsão de Infecção):**\n"
    laudo += f"• Janelas de Orvalho: {horas_orvalho} períodos de risco.\n"
    if horas_orvalho > 2:
        laudo += "⚠️ **RISCO ALTO:** Esporos de fungos dependem de hidrofilia (água livre) para emitir o tubo germinativo e penetrar a cutícula da folha.\n\n"
    else:
        laudo += "✅ **RISCO BAIXO:** Baixa umidade impede a germinação de conídios.\n\n"
        
    laudo += f"{texto_nutri}\n" # Texto gigante de nutrição
    
    laudo += f"🧬 **4. METABOLISMO (Soma Térmica):**\n"
    laudo += f"• GDA Acumulado: {gda_total:.0f} Graus-Dia.\n"
    laudo += f"• ETc (Consumo Hídrico): {sum(p['et0']*KC_ATUAL for p in previsoes):.1f} mm/semana.\n"
    
    return laudo

# --- 6. FUNÇÃO DE VIGILÂNCIA (TARDE) ---
def ronda_vespertina(previsoes):
    # Analisa mudanças drásticas para alertas de emergência
    chuva_prox = sum(p['chuva'] for p in previsoes[:3])
    vento_max = max(p['vento'] for p in previsoes[:3])
    
    if chuva_prox > 5.0 or vento_max > 20:
        alerta = f"🚨 **ALERTA DE MUDANÇA BRUSCA DE CENÁRIO**\n\n"
        alerta += f"O sistema de vigilância detectou uma alteração crítica não prevista pela manhã.\n"
        alerta += f"• Chuva Iminente: {chuva_prox}mm\n"
        alerta += f"• Vento: {vento_max} km/h\n\n"
        alerta += "⚠️ RECOMENDAÇÃO: Suspenda aplicações foliares imediatamente para evitar deriva e lavagem."
        enviar_email(f"🚨 ALERTA URGENTE: {datetime.now(FUSO_BRASIL).strftime('%H:%M')}", alerta)
    else:
        print("Vigilância: Sem alterações críticas.")

# --- 7. EXECUTOR ---
if __name__ == "__main__":
    raw = get_agro_data()
    if raw:
        previsoes = []
        for i in range(0, min(40, len(raw['list'])), 8):
            item = raw['list'][i]
            t, u = item['main']['temp'], item['main']['humidity']
            dt, vpd = calcular_delta_t_e_vpd(t, u)
            et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
            chuva = sum([raw['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(raw['list'])])
            previsoes.append({'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'temp': t, 'umidade': u, 'vpd': vpd, 'delta_t': dt, 'vento': item['wind']['speed']*3.6, 'chuva': round(chuva, 1), 'et0': round(et0, 2)})

        hora = datetime.now(FUSO_BRASIL).hour
        
        # ROTINA MATINAL (RELATÓRIO COMPLETO)
        if 5 <= hora <= 8:
            anotacao = ler_atividades_usuario()
            laudo_completo = gerar_laudo_tecnico(previsoes, anotacao)
            
            # Tabela Resumo no Topo do E-mail
            header = f"💎 CONSULTORIA AGRO-INTEL PREMIUM\n📅 {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y')}\n"
            header += "-"*60 + "\n"
            for p in previsoes:
                header += f"{p['data']} | {p['temp']}°C | 🌧️ {p['chuva']}mm | 💧 {round(p['et0']*KC_ATUAL, 2)}mm\n"
            
            enviar_email(f"💎 LAUDO TÉCNICO: {datetime.now(FUSO_BRASIL).strftime('%d/%m')}", header + "\n" + laudo_completo)
            
            # Log CSV
            try:
                with open('caderno_de_campo_master.csv', 'a', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerow([datetime.now().strftime('%d/%m/%Y'), previsoes[0]['temp'], anotacao, "Laudo Enviado"])
            except: pass
            
        # ROTINA VESPERTINA (VIGILÂNCIA)
        else:
            ronda_vespertina(previsoes)
