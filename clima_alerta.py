import requests
import os
import smtplib
import math
import csv
from datetime import datetime
from email.message import EmailMessage

# --- CONFIGURAÇÕES DE CAMPO ---
DATA_PLANTIO = datetime(2025, 11, 25) 
T_BASE_BERRIES = 10.0 
GDA_ALVO_COLHEITA = 1200 
KC_ATUAL = 0.75          

# CONFIGURAÇÕES DE API E EMAIL
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
CIDADE = "Ibicoara, BR"

def calcular_delta_t_e_vpd(temp, umidade):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umidade / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    delta_t = round(temp - tw, 1)
    return delta_t, vpd

def ler_atividades_usuario():
    arquivo_input = 'input_atividades.txt'
    if os.path.exists(arquivo_input):
        with open(arquivo_input, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        if conteudo and conteudo != "Início do caderno de campo":
            with open(arquivo_input, 'w', encoding='utf-8') as f:
                f.write("")
            return conteudo
    return "Nenhum manejo registrado hoje."

def processar_gatilhos_inteligentes(texto):
    analise_extra = ""
    texto = texto.lower()
    if "chuva" in texto or "chovendo" in texto or "volume" in texto:
        analise_extra += "⚠️ IMPACTO HÍDRICO E NUTRICIONAL: Chuvas volumosas causam a lixiviação (lavagem) de cátions e ânions móveis, como o Nitrato (NO3-) e o Potássio (K+). "
        analise_extra += "Isso altera a condutividade elétrica da solução do solo, podendo gerar uma deficiência momentânea mesmo em solos adubados. "
        analise_extra += "Além disso, a saturação hídrica reduz o oxigênio nas raízes (anóxia), o que interrompe o metabolismo ativo da planta.\n"
    if any(p in texto for p in ["praga", "inseto", "mancha", "lagarta", "ácaro", "fungo"]):
        analise_extra += "🔍 DINÂMICA FITOSSANITÁRIA: A presença de patógenos ou pragas requer uma análise do microclima do dossel. "
        analise_extra += "A eficácia do controle químico ou biológico depende da 'janela de aplicação' definida pelo Delta T, garantindo que o ingrediente ativo permaneça na fase líquida o tempo suficiente para ser absorvido pela cutícula foliar.\n"
    return analise_extra if analise_extra else "✅ Estabilidade operacional: O manejo relatado indica manutenção preventiva sem alertas de estresse biótico imediatos."

def gerar_conclusao_agronomo(hoje, balanco, anotacao, dias_campo):
    conclusao = "👨‍🔬 PARECER TÉCNICO ESTRATÉGICO:\n"
    if "chuva" in anotacao.lower():
        conclusao += "O evento pluviométrico relatado é o fator determinante do dia. Recomendamos priorizar a fiscalização de drenagem em pontos críticos e suspender a fertirrigação nitrogenada nas próximas 24-48h para evitar perdas por lixiviação. "
    elif hoje['vpd'] > 1.3:
        conclusao += "O cenário de estresse hídrico atmosférico (VPD alto) exige cautela. A planta está operando em economia hídrica; qualquer aplicação mineral pesada agora pode causar queima salina devido à baixa taxa de transpiração. "
    else:
        conclusao += "O equilíbrio termodinâmico atual favorece a máxima eficiência da planta. É o momento ideal para aportes nutricionais via fertirrigação. "
    
    conclusao += f"Com a cultura atingindo {dias_campo} dias, o foco deve ser a consolidação da área foliar para suportar a futura demanda de carboidratos dos frutos."
    return conclusao

def analisar_expert_educativo(previsoes, anotacao_usuario):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    balanco = total_chuva - total_etc
    dias_campo = (datetime.now() - DATA_PLANTIO).days
    
    analise_gatilho = processar_gatilhos_inteligentes(anotacao_usuario)
    conclusao_final = gerar_conclusao_agronomo(hoje, balanco, anotacao_usuario, dias_campo)
    
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🔴 CRÍTICO" if hoje['delta_t'] > 8 else "🟡 ALERTA")
    status_hidr = "🟢 OK" if -5 < balanco < 5 else ("🔴 DÉFICIT" if balanco < -10 else "🟡 REVISAR")
    
    parecer = f"🚦 DASHBOARD OPERACIONAL:\n• Pulverização (Delta T): {status_pulv} | Irrigação: {status_hidr}\n"
    parecer += f"💡 ANÁLISE TÉCNICA: O Delta T integra temperatura e umidade para medir a taxa de evaporação da gota. No status {status_pulv}, garantimos a molhabilidade ideal da folha. Já o balanço hídrico de {balanco:.1f}mm orienta a reposição precisa, evitando o desperdício de água e energia.\n\n"
    
    parecer += f"📝 REGISTRO E ANÁLISE DE GATILHOS:\n• Sua nota: \"{anotacao_usuario}\"\n📢 CONSULTORIA DINÂMICA:\n{analise_gatilho}\n\n"

    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88 and p['vento'] < 6)
    parecer += f"🍄 MONITORAMENTO DE SANIDADE (Molhamento Foliar):\n• Índice: {'ALTO' if horas_molhamento > 2 else 'BAIXO'}\n"
    parecer += f"💡 EXPLICAÇÃO: A germinação de esporos fúngicos (Botrytis/Antracnose) requer água livre na superfície vegetal. Com {horas_molhamento} horas previstas de alta umidade, o monitoramento de campo deve focar na detecção precoce de lesões aquosas em tecidos jovens.\n\n"

    gda_total = dias_campo * 14.8 
    progresso = min(round((gda_total / GDA_ALVO_COLHEITA) * 100, 1), 100)
    gda_hoje = max(hoje['temp'] - T_BASE_BERRIES, 0)
    parecer += f"🧬 DESENVOLVIMENTO FISIOLÓGICO (Relógio Térmico):\n• Idade: {dias_campo} dias | Progresso: {progresso}% | GDA Hoje: {gda_hoje:.1f}\n"
    parecer += f"💡 EXPLICAÇÃO: A cultura das Berries é governada pelo acúmulo de energia térmica. O progresso de {progresso}% indica que a planta já cumpriu grande parte de sua fase vegetativa inicial. O 'gargalo' produtivo agora é garantir que a taxa de fotossíntese líquida seja maximizada pelo conforto térmico.\n\n"
    
    parecer += f"🛒 SUGESTÃO DE FERTILIZAÇÃO MINERAL:\n"
    if dias_campo < 90:
        parecer += "• FASE: Estabelecimento Radicular. FOCO: Fósforo (P), Cálcio (Ca) e Magnésio (Mg).\n"
        parecer += "💡 EXPLICAÇÃO: O Fósforo fornece o ATP necessário para a divisão celular nas raízes. O Cálcio é estrutural, compondo a parede das células (pectatos de cálcio), garantindo frutos mais firmes no futuro. O Magnésio é o átomo central da clorofila, essencial para capturar a luz da Chapada Diamantina.\n\n"
    elif dias_campo < 180:
        parecer += "• FASE: Expansão Foliar. FOCO: Nitrogênio (N) e Micronutrientes.\n"
    else:
        parecer += "• FASE: Reprodutiva. FOCO: Potássio (K) e Boro (B).\n"

    parecer += f"🌿 CONFORTO TÉRMICO (VPD - Déficit de Pressão de Vapor):\n• VPD Atual: {hoje['vpd']} kPa.\n"
    parecer += f"💡 EXPLICAÇÃO: O VPD é a força motriz da planta. Entre 0.45 e 1.25 kPa, a planta 'bombeia' água e nutrientes com eficiência. Fora desse intervalo, há um fechamento estomático preventivo, o que reduz o crescimento diário e pode causar distúrbios fisiológicos como o 'tip burn'.\n\n"

    parecer += f"💧 MANEJO HÍDRICO (ETc - Evapotranspiração da Cultura):\n• Necessidade Semanal: {total_etc:.1f} mm.\n"
    parecer += f"💡 EXPLICAÇÃO: Diferente da perda de água do solo genérica, a ETc reflete a demanda real da Berrie em Ibicoara. Manter o solo na 'Capacidade de Campo' sem encharcar é o segredo para o desenvolvimento de mirtilos e framboesas de alta qualidade.\n\n"
    
    parecer += "------------------------------------------------------------\n"
    parecer += f"{conclusao_final}\n"

    return parecer, conclusao_final

# [Funções get_agro_data_ultimate, registrar_log_master e enviar_email permanecem as mesmas]
# ... [Código Principal de Execução igual ao anterior]
