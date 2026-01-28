import requests
import os
import smtplib
import math
import csv
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES MESTRAS ---
# Mude para False quando quiser que o sistema rode sozinho nos horários certos (06h, 11h, 15h)
# Deixe True agora para testar e receber o relatório completo IMEDIATAMENTE.
MODO_TESTE = True 

DATA_PLANTIO = datetime(2025, 11, 25) 
KC_ATUAL = 0.75 
FUSO_BRASIL = timezone(timedelta(hours=-3))
CIDADE = "Ibicoara, BR"

# Credenciais
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"

# --- 2. BANCO DE DADOS DE CONHECIMENTO (KNOWLEDGE BASE) ---
# Aqui reside a "Inteligência" do sistema. Textos profundos e técnicos.

DB_CIENCIA = {
    'vpd_baixo': """
    ⚠️ **ANÁLISE TERMODINÂMICA DETALHADA (VPD < 0.4 kPa): BLOQUEIO HIDRÁULICO**
    • **Fisiologia:** A atmosfera encontra-se saturada. O déficit de pressão de vapor é nulo, impedindo a transpiração estomática.
    • **Consequência Biofísica:** A "bomba hidráulica" do xilema é desligada. Sem transpiração, cessa o fluxo de massa ascendente.
    • **Impacto Nutricional:** Nutrientes de transporte passivo (principalmente **Cálcio** e **Boro**) não chegam aos drenos (frutos e meristemas), mesmo que haja adubo no solo.
    • **Risco Sanitário:** A pressão radicular positiva pode causar gutação (gotas nas bordas da folha), via expressa para entrada de bactérias (*Xanthomonas*) e fungos.
    """,
    'vpd_alto': """
    🔥 **ANÁLISE TERMODINÂMICA DETALHADA (VPD > 1.4 kPa): ESTRESSE ATMOSFÉRICO**
    • **Fisiologia:** O ar apresenta alta demanda evaporativa ("sede"). A planta perde água mais rápido do que a raiz consegue absorver.
    • **Reação de Defesa:** Fechamento estomático imediato para evitar a plasmólise celular (perda de turgor).
    • **Impacto Metabólico:** Com estômatos fechados, cessa a entrada de Carbono (CO2). A fotossíntese é interrompida e a planta passa a consumir reservas de açúcar (respiração) para sobreviver, paralisando o ganho de biomassa.
    """,
    'vpd_ideal': """
    ✅ **ANÁLISE TERMODINÂMICA DETALHADA (VPD IDEAL): EFICIÊNCIA MÁXIMA**
    • **Fisiologia:** Condições perfeitas de temperatura e umidade relativa.
    • **Metabolismo:** A planta opera com máxima condutância estomática. Ocorre transpiração (termorregulação) e fixação de carbono simultaneamente.
    • **Nutrição:** O fluxo xilemático está em velocidade ótima, transportando água e sais minerais do solo para as folhas e frutos com máxima eficiência.
    """,
    'nutri_raiz': """
    🛒 **ESTRATÉGIA NUTRICIONAL: FASE DE ENRAIZAMENTO**
    • **Foco:** Fósforo (P) e Cálcio (Ca).
    • **Fundamentação Bioquímica:** O Fósforo é o constituinte base do ATP (Adenosina Trifosfato), a moeda energética necessária para a divisão celular nas raízes. O Cálcio é estrutural, formando os Pectatos de Cálcio na lamela média, atuando como o "cimento" que confere rigidez aos tecidos novos e resistência física contra patógenos de solo.
    """,
    'nutri_veg': """
    🛒 **ESTRATÉGIA NUTRICIONAL: FASE VEGETATIVA**
    • **Foco:** Nitrogênio (N) e Magnésio (Mg).
    • **Fundamentação Bioquímica:** O Nitrogênio é essencial para a síntese de aminoácidos e enzimas (Rubisco). O Magnésio é o átomo central da molécula de Clorofila. A deficiência de Mg nesta fase impede a conversão de energia luminosa em energia química, travando o desenvolvimento mesmo sob sol pleno.
    """,
    'nutri_fruto': """
    🛒 **ESTRATÉGIA NUTRICIONAL: FASE DE FRUTIFICAÇÃO**
    • **Foco:** Potássio (K) e Boro (B).
    • **Fundamentação Bioquímica:** O Potássio atua na osmorregulação e no transporte de fotoassimilados (açúcares) via floema, do dreno fonte (folha) para o dreno dreno (fruto). O Boro é vital para a germinação do grão de pólen e estabilidade da parede celular do fruto em expansão.
    """
}

DB_FARMACIA = {
    'botrytis': "🦠 **PROTOCOLO FITOSSANITÁRIO (Botrytis cinerea):**\n   Patógeno necrotrófico dependente de molhamento.\n   • **Químico:** *Fludioxonil* (contato) ou *Ciprodinil* (sistêmico).\n   • **Biológico:** *Bacillus subtilis* (competição por sítio).",
    'antracnose': "🦠 **PROTOCOLO FITOSSANITÁRIO (Antracnose):**\n   Disseminação via respingos de chuva (conídios).\n   • **Químico:** *Azoxistrobina* (Estrobilurina) + *Difenoconazol* (Triazol).",
    'ferrugem': "🦠 **PROTOCOLO FITOSSANITÁRIO (Ferrugem):**\n   Identificação: Pústulas pulverulentas.\n   • **Químico:** *Tebuconazol* ou *Protioconazol*.",
}

# --- 3. CÁLCULOS FÍSICOS ---
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
        # Se for teste, não apaga. Se for produção e de manhã, apaga.
        hora = datetime.now(FUSO_BRASIL).hour
        if not MODO_TESTE and (5 <= hora <= 8) and conteudo != "Início do caderno de campo":
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
        print("✅ E-mail enviado com sucesso.")
    except Exception as e: print(f"❌ Erro ao enviar email: {e}")

def get_agro_data():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    try:
        r = requests.get(url); r.raise_for_status()
        return r.json()
    except: return None

# --- 5. O CÉREBRO (MOTOR DE DECISÃO CRUZADA) ---
def gerar_laudo_completo(previsoes, anotacao):
    hoje = previsoes[0]
    dias_campo = (datetime.now(FUSO_BRASIL).date() - DATA_PLANTIO.date()).days
    
    # --- A. ANÁLISE DE CAMPO (INPUT DO USUÁRIO) ---
    texto = anotacao.lower()
    analise_campo = ""
    
    usuario_relatou_chuva = any(x in texto for x in ["chuva", "água", "molhou", "temporal"])
    usuario_adubou = any(x in texto for x in ["adubo", "fertirrigação", "nitrato", "cálcio", "aplicação"])
    solo_saturado = hoje['chuva'] > 5.0 or usuario_relatou_chuva
    vpd_critico = hoje['vpd'] < 0.4
    
    # Lógica de Decisão Profissional
    if usuario_adubou and solo_saturado:
        analise_campo += "🔴 **DIAGNÓSTICO CRÍTICO (ERRO TÉCNICO):**\n"
        analise_campo += "   O relato indica fertirrigação em solo saturado (chuva). Isso resulta em:\n"
        analise_campo += "   1. **Lixiviação:** Os ânions (Nitrato) são repelidos pelas cargas negativas do solo e lavados pela água.\n"
        analise_campo += "   2. **Anoxia:** A raiz sem oxigênio cessa a respiração aeróbica e para de absorver nutrientes.\n\n"
        
    elif usuario_adubou and vpd_critico:
        analise_campo += "🟡 **ALERTA DE INEFICIÊNCIA:**\n"
        analise_campo += "   Aplicação realizada, porém o VPD Baixo (<0.4 kPa) impede a translocação.\n"
        analise_campo += "   **Diagnóstico:** O nutriente está no solo, mas não subirá para a folha/fruto hoje devido à falta de transpiração.\n\n"
        
    elif not usuario_adubou and vpd_critico:
        analise_campo += "⛔ **DIRETRIZ DE BLOQUEIO OPERACIONAL:**\n"
        analise_campo += "   O ar está saturado. A planta não tem capacidade física de puxar solução do solo.\n"
        analise_campo += "   **Ação:** Qualquer irrigação hoje é desperdício de energia e risco sanitário (patógenos de solo).\n\n"
        
    else:
        analise_campo += "✅ **OPERAÇÃO EM REGIME NOMINAL:**\n   O manejo segue padrões preventivos. Acompanhe a evolução do Delta T.\n\n"

    # Verificação de Pragas
    for praga, texto_tec in DB_FARMACIA.items():
        if praga in texto: analise_campo += f"{texto_tec}\n\n"

    # --- B. SELEÇÃO DO CONTEÚDO CIENTÍFICO ---
    if hoje['vpd'] > 1.4: texto_vpd = DB_CIENCIA['vpd_alto']
    elif hoje['vpd'] < 0.4: texto_vpd = DB_CIENCIA['vpd_baixo']
    else: texto_vpd = DB_CIENCIA['vpd_ideal']

    if dias_campo < 45: texto_nutri = DB_CIENCIA['nutri_raiz']
    elif dias_campo < 130: texto_nutri = DB_CIENCIA['nutri_veg']
    else: texto_nutri = DB_CIENCIA['nutri_fruto']

    gda_total = dias_campo * 14.8
    horas_orvalho = sum(1 for p in previsoes if p['umidade'] > 88)
    
    # --- C. MONTAGEM DO LAUDO (ESTRUTURA COMPLETA) ---
    laudo = f"🏛️ **LAUDO TÉCNICO AGRO-INTEL PREMIUM**\n"
    laudo += f"📍 Unidade: {CIDADE} | 📆 Idade da Cultura: {dias_campo} dias\n\n"
    
    laudo += f"🔎 **1. ANÁLISE DO ENGENHEIRO (Manejo vs Clima):**\n"
    laudo += f"• Registro de Campo: \"{anotacao if anotacao else 'Sem registros manuais'}\"\n"
    laudo += f"{analise_campo}"
    laudo += "-"*50 + "\n"
    
    laudo += f"🌡️ **2. FISIOLOGIA VEGETAL E CLIMATOLOGIA:**\n"
    laudo += f"• VPD Atual: {hoje['vpd']} kPa | Delta T: {hoje['delta_t']}°C\n"
    laudo += f"{texto_vpd}\n" 
    
    laudo += f"💊 **3. FITOSSANIDADE (Previsão de Infecção):**\n"
    laudo += f"• Janelas de Orvalho: {horas_orvalho} períodos de risco.\n"
    if horas_orvalho > 2:
        laudo += "⚠️ **RISCO ALTO:** Esporos de fungos (Ex: *Botrytis*) dependem de hidrofilia (água livre na folha) para emitir o tubo germinativo.\n\n"
    else:
        laudo += "✅ **RISCO BAIXO:** Umidade relativa desfavorável à germinação de conídios.\n\n"
        
    laudo += f"{texto_nutri}\n"
    
    laudo += f"🧬 **4. METABOLISMO (Soma Térmica):**\n"
    laudo += f"• GDA Acumulado: {gda_total:.0f} Graus-Dia.\n"
    
    return laudo

# --- 6. FUNÇÃO DE VIGILÂNCIA (RODA À TARDE) ---
def ronda_vigilancia(previsoes):
    # Analisa mudanças drásticas (Watchdog)
    print("🔭 Iniciando Ronda de Vigilância...")
    chuva_imediata = sum(p['chuva'] for p in previsoes[:3])
    vento_max = max(p['vento'] for p in previsoes[:3])
    
    # Critérios de Alerta (Só avisa se for grave)
    if chuva_imediata > 5.0 or vento_max > 25:
        alerta = f"🚨 **ALERTA DE MUDANÇA BRUSCA DE CENÁRIO**\n\n"
        alerta += f"O sistema de vigilância detectou uma alteração crítica não prevista no relatório da manhã.\n"
        alerta += f"• Chuva Iminente: {chuva_imediata}mm\n"
        alerta += f"• Rajada de Vento: {vento_max} km/h\n\n"
        alerta += "⚠️ **AÇÃO RECOMENDADA:** Suspenda aplicações foliares imediatamente para evitar deriva e lavagem de produto."
        enviar_email(f"🚨 ALERTA URGENTE: {datetime.now(FUSO_BRASIL).strftime('%H:%M')}", alerta)
    else:
        print("✅ Vigilância: Sem alterações críticas no clima. Nenhum alerta enviado.")

# --- 7. EXECUTOR PRINCIPAL ---
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
        
        # LÓGICA DE DISPARO:
        # Se MODO_TESTE for True, ele ignora a hora e manda o relatório completo AGORA.
        # Se MODO_TESTE for False, ele obedece a regra: Manhã = Relatório, Tarde = Vigilância.
        
        if MODO_TESTE or (5 <= hora <= 8):
            print("🚀 Gerando Relatório Completo...")
            anotacao = ler_atividades_usuario()
            laudo_completo = gerar_laudo_completo(previsoes, anotacao)
            
            # Cabeçalho Tabela
            header = f"💎 CONSULTORIA AGRO-INTEL PREMIUM\n📅 {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y')}\n"
            header += "-"*60 + "\n"
            for p in previsoes:
                header += f"{p['data']} | {p['temp']}°C | 🌧️ {p['chuva']}mm | 💧 {round(p['et0']*KC_ATUAL, 2)}mm\n"
            
            enviar_email(f"💎 LAUDO TÉCNICO: {datetime.now(FUSO_BRASIL).strftime('%d/%m')}", header + "\n" + laudo_completo)
            
            # Log
            try:
                with open('caderno_de_campo_master.csv', 'a', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerow([datetime.now().strftime('%d/%m/%Y'), previsoes[0]['temp'], anotacao, "Laudo Enviado"])
            except: pass
            
        else:
            # Rotina de Tarde (Apenas Vigilância)
            ronda_vigilancia(previsoes)
            
    else:
        print("❌ Erro ao conectar com API de Clima.")
