
import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

# ==============================
# Configurações de API
# ==============================
AISWEB_API_KEY = st.secrets["apis"]["AISWEB_API_KEY"]
AISWEB_API_PASS = st.secrets["apis"]["AISWEB_API_PASS"]
REDEMET_API_KEY = st.secrets["apis"]["REDEMET_API_KEY"]

# ==============================
# Funções auxiliares
# ==============================
def consultar_rotaer(icao):
    url = f"https://api.decea.mil.br/aisweb/?apiKey={AISWEB_API_KEY}&apiPass={AISWEB_API_PASS}&area=rotaer&icaoCode={icao}"
    try:
        resp = requests.get(url, headers={"User-Agent": "Python"}, timeout=10)
        root = ET.fromstring(resp.content)
        pistas = []
        for r in root.findall(".//runway"):
            pistas.append({
                "ident": r.findtext("ident"),
                "comprimento_m": r.findtext("length") or "0",
                "largura_m": r.findtext("width") or "0"
            })
        return {
            "lat": root.findtext("lat"),
            "lng": root.findtext("lng"),
            "distancia": root.findtext("distance"),
            "pistas": pistas
        }
    except Exception as e:
        return {"erro": str(e)}

def get_notams_por_localidade(icao_code):
    url = "http://aisweb.decea.gov.br/api/"
    params = {
        "apiKey": AISWEB_API_KEY,
        "apiPass": AISWEB_API_PASS,
        "area": "notam",
        "icaocode": icao_code,
        "minutes": 4320
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return []
        root = ET.fromstring(response.text)
        notams = []
        for item in root.findall(".//item"):
            cod = item.findtext("cod")
            info = item.findtext("e")
            loc = item.findtext("loc")
            dt = item.findtext("dt")
            notams.append({
                "Codigo": cod or "N/A",
                "Localidade": loc or icao_code,
                "DataHora": dt or "Desconhecida",
                "Informacao": info or "Sem descrição"
            })
        return notams
    except:
        return []

def consultar_metar(icao):
    url = f"https://api-redemet.decea.mil.br/mensagens/metar/{icao}?api_key={REDEMET_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        dados = resp.json()
        mensagens = dados.get("data", {}).get("data", [])
        if not mensagens:
            return ["Sem informações METAR disponíveis para este aeródromo."]
        return [decodificar_metar(m["mens"]) for m in mensagens]
    except:
        return ["Erro ao consultar METAR"]

def consultar_taf(icao):
    url = f"https://api-redemet.decea.mil.br/mensagens/taf/{icao}?api_key={REDEMET_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        dados = resp.json()
        mensagens = dados.get("data", {}).get("data", [])
        if not mensagens:
            return ["Sem informações TAF disponíveis para este aeródromo."]
        return [decodificar_taf(m["mens"]) for m in mensagens]
    except:
        return ["Erro ao consultar TAF"]

def decodificar_metar(metar):
    partes = metar.replace("\n", " ").replace("=", "").strip()
    resumo = []
    if "CAVOK" in partes:
        resumo.append("Céu limpo (CAVOK)")
    if match := re.search(r"(\d{3}|VRB)(\d{2})KT", partes):
        direcao = "variável" if match[1] == "VRB" else match[1]
        resumo.append(f"Vento: {direcao} a {match[2]} kt")
    if match := re.search(r"(M?\d{2})/(M?\d{2})", partes):
        resumo.append(f"Temperatura: {match[1]} °C / Ponto de orvalho: {match[2]} °C")
    if "TSRA" in partes or "FG" in partes or "SN" in partes:
        resumo.append("Alerta - Fenômeno significativo detectado")
    return "\n".join(resumo) or "METAR não decodificado"

def decodificar_taf(taf):
    partes = taf.replace("\n", " ").replace("=", "").strip()
    resumo = []
    if "CAVOK" in partes:
        resumo.append("Céu limpo durante todo o período")
    if match := re.search(r"(\d{3}|VRB)(\d{2})KT", partes):
        direcao = "variável" if match[1] == "VRB" else match[1]
        resumo.append(f"Vento previsto: {direcao} a {match[2]} kt")
    if "BECMG" in partes:
        resumo.append("\nHaverá mudanças graduais nas condições")
    if any(term in partes for term in ["TSRA", "FG", "SN", "RA"]):
        resumo.append("Alerta - Previsão de fenômenos meteorológicos adversos")
    return "\n".join(resumo) or "TAF não decodificado"

def ha_alertas(textos):
    for t in textos:
        if "Alerta" in t:
            return True
    return False

def ha_alerta_notam(lista_notam):
    return any("FECHADO" in n["Informacao"].upper() or "CANCELADO" in n["Informacao"].upper() for n in lista_notam)

# ==============================
# Estilo visual
# ==============================
def exibir_bloco_titulo(texto, cor="#4A90E2"):
    st.markdown(f"<h5 style='color:{cor}; margin-top: 1em'>{texto}</h5>", unsafe_allow_html=True)

def exibir_bloco_conteudo(texto):
    st.markdown(
        f"""
        <div style="
            background-color: #f7f7f7;
            color: #111;
            padding: 12px 18px;
            border-radius: 12px;
            font-size: 15px;
            line-height: 1.6;
            margin-bottom: 1em;
            border: 1px solid #ddd;
        ">
            {texto.replace('\n', '<br>')}
        </div>
        """,
        unsafe_allow_html=True
    )

# ==============================
# Interface Streamlit
# ==============================
st.set_page_config(page_title="Assistente de Voo", layout="centered")
st.title("🛫 Flight Safety Decision")
st.markdown("<p style='font-size:14px; color:#E69F00;'>⚠️ Versão em Estudos!</p>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    origem = st.text_input("Aeródromo de Origem (ex: SBSP)")
    combustivel = st.number_input("Combustível (litros)", min_value=0)
    vel_cruzeiro = st.number_input("Velocidade de Cruzeiro (knots)", min_value=0)
with col2:
    destino = st.text_input("Aeródromo de Destino (ex: SBRJ)")
    dist_decolagem = st.number_input("Distância mínima de decolagem (m)", min_value=0, step=10)
    dist_pouso = st.number_input("Distância mínima de pouso (m)", min_value=0, step=10)


if origem and destino:
    st.markdown("---")
    st.subheader("🔍 Avaliação das Condições de Voo")

    origem_data = {
        "rotaer": consultar_rotaer(origem),
        "notam": get_notams_por_localidade(origem),
        "metar": consultar_metar(origem),
        "taf": consultar_taf(origem)
    }
    destino_data = {
        "rotaer": consultar_rotaer(destino),
        "notam": get_notams_por_localidade(destino),
        "metar": consultar_metar(destino),
        "taf": consultar_taf(destino)
    }

    def avaliar_pistas(local, pistas, dist_min_decolagem, dist_min_pouso):
        relatorio = []
        pista_ok = True
        for pista in pistas:
            comprimento = int(pista["comprimento_m"])
            if comprimento >= dist_min_decolagem:
                relatorio.append(f"✅ Pista {pista['ident']} ({local}) - Decolagem: {comprimento}m OK")
            else:
                relatorio.append(f"🚫 Pista {pista['ident']} ({local}) - Decolagem: {comprimento}m insuficiente")
                pista_ok = False

            if comprimento >= dist_min_pouso:
                relatorio.append(f"✅ Pista {pista['ident']} ({local}) - Pouso: {comprimento}m OK")
            else:
                relatorio.append(f"🚫 Pista {pista['ident']} ({local}) - Pouso: {comprimento}m insuficiente")
                pista_ok = False
        return relatorio, pista_ok

    relatorios, pista_ok = [], True
    for local, dados in [("Origem", origem_data), ("Destino", destino_data)]:
        rotaer = dados["rotaer"]
        if not rotaer.get("pistas"):
            relatorios.append(f"⚠️ Sem dados de pista para {local}")
            pista_ok = False
        else:
            rel, ok = avaliar_pistas(local, rotaer["pistas"], dist_decolagem, dist_pouso)
            relatorios.extend(rel)
            if not ok:
                pista_ok = False

    alertas = (
        ha_alertas(origem_data["metar"]) or
        ha_alertas(destino_data["metar"]) or
        ha_alertas(origem_data["taf"]) or
        ha_alertas(destino_data["taf"]) or
        ha_alerta_notam(origem_data["notam"]) or
        ha_alerta_notam(destino_data["notam"])
    )

    if pista_ok and not alertas:
        st.success("✅ CONDIÇÃO SEGURA PARA VOO")
    elif pista_ok:
        st.warning("⚠️ CONDIÇÃO CONDICIONAL - Verifique previsões e NOTAMs")
    else:
        st.error("🚫 CONDIÇÃO INSEGURA PARA VOO")

    # Detalhamento visual
    st.markdown("### 📋 Relatório de Pistas")
    for linha in relatorios:
        st.markdown(f"- {linha}")

    # Origem
    st.markdown("### 🌤️ Condições - Origem")
    exibir_bloco_titulo("📄 METAR:")
    for m in origem_data["metar"]:
        exibir_bloco_conteudo(m)

    exibir_bloco_titulo("📡 TAF:")
    for t in origem_data["taf"]:
        exibir_bloco_conteudo(t)

    # Destino
    st.markdown("### 🌥️ Condições - Destino")
    exibir_bloco_titulo("📄 METAR:")
    for m in destino_data["metar"]:
        exibir_bloco_conteudo(m)

    exibir_bloco_titulo("📡 TAF:")
    for t in destino_data["taf"]:
        exibir_bloco_conteudo(t)

    # NOTAMs
    st.markdown("### 📢 NOTAMs Origem")
    if origem_data["notam"]:
        for n in origem_data["notam"]:
            exibir_bloco_conteudo(f"📌 **{n['Codigo']}** ({n['DataHora']}): {n['Informacao']}")
    else:
        st.info("Nenhum NOTAM disponível para o aeródromo de origem.")

    st.markdown("### 📢 NOTAMs Destino")
    if destino_data["notam"]:
        for n in destino_data["notam"]:
            exibir_bloco_conteudo(f"📌 **{n['Codigo']}** ({n['DataHora']}): {n['Informacao']}")
    else:
        st.info("Nenhum NOTAM disponível para o aeródromo de destino.")

    st.caption(f"Consulta gerada em {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
