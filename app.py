import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# ==============================
# Configurações de API
# ==============================
AISWEB_API_KEY = ""
AISWEB_API_PASS = ""
REDEMET_API_KEY = ""

# ==============================
# Funções auxiliares para consumo das APIs
# ==============================
def get_notams_por_localidade(icao_code):
    url = "http://aisweb.decea.gov.br/api/"
    params = {
        "apiKey": AISWEB_API_KEY,
        "apiPass": AISWEB_API_PASS,
        "area": "notam",
        "icaocode": icao_code,
        "minutes": 1440  # últimas 24h
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return [f"Erro HTTP {response.status_code}"]

        root = ET.fromstring(response.text)
        notams = []

        for item in root.findall(".//item"):
            cod = item.findtext("cod")
            info = item.findtext("e")
            dt = item.findtext("dt")
            loc = item.findtext("loc")

            notams.append(f"📌 Código: {cod} | Local: {loc or icao_code} | Data: {dt}\n🔹 {info or '(sem descrição)'}")

        return notams if notams else ["Nenhum NOTAM encontrado."]
    except Exception as e:
        return [f"Erro ao processar NOTAM: {e}"]

def consultar_rotaer(icao):
    url = (
        f"https://api.decea.mil.br/aisweb/?apiKey={AISWEB_API_KEY}&apiPass={AISWEB_API_PASS}"
        f"&area=rotaer&icaoCode={icao}"
    )
    try:
        resp = requests.get(url, headers={"User-Agent": "Python"}, timeout=10)
        root = ET.fromstring(resp.content)
        pistas = []
        for r in root.findall(".//runway"):
            pistas.append({
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

def consultar_metar(icao):
    url = f"https://api-redemet.decea.mil.br/mensagens/metar/{icao}?api_key={REDEMET_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        dados = resp.json()
        return [m["mens"] for m in dados.get("data", {}).get("data", [])]
    except Exception as e:
        return [f"Erro ao consultar METAR: {e}"]

def consultar_taf(icao):
    url = f"https://api-redemet.decea.mil.br/mensagens/taf/{icao}?api_key={REDEMET_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        dados = resp.json()
        return [m["mens"] for m in dados.get("data", {}).get("data", [])]
    except Exception as e:
        return [f"Erro ao consultar TAF: {e}"]

# ==============================
# Interface Streamlit
# ==============================
st.set_page_config(page_title="Assistente de Decisão de Voo", layout="centered")
st.title("🛫 Assistente de Decisão de Voo")

col1, col2 = st.columns(2)
with col1:
    origem = st.text_input("Aeródromo de Origem (ex: SBSP)")
    combustivel = st.number_input("Combustível (litros)", min_value=0)
    vel_cruzeiro = st.number_input("Velocidade de Cruzeiro (knots)", min_value=0)
with col2:
    destino = st.text_input("Aeródromo de Destino (ex: SBRJ)")
    dist_decolagem = st.number_input("Distância mínima de decolagem (km)", min_value=0)
    dist_pouso = st.number_input("Distância mínima de pouso (km)", min_value=0)

if origem and destino:
    st.subheader("🔍 Análise do Voo")

    dados_origem = {
        "rotaer": consultar_rotaer(origem),
        "notams": get_notams_por_localidade(origem),
        "metar": consultar_metar(origem),
        "taf": consultar_taf(origem)
    }

    dados_destino = {
        "rotaer": consultar_rotaer(destino),
        "notams": get_notams_por_localidade(destino),
        "metar": consultar_metar(destino),
        "taf": consultar_taf(destino)
    }

    try:
        comp_ori = int(dados_origem["rotaer"]["pistas"][0]["comprimento_m"])
        comp_dest = int(dados_destino["rotaer"]["pistas"][0]["comprimento_m"])

        if comp_ori < dist_decolagem * 1000:
            st.error(f"🚫 Pista de decolagem ({origem}) insuficiente: {comp_ori}m < {dist_decolagem * 1000}m")
        else:
            st.success(f"✅ Pista de decolagem ({origem}) compatível")

        if comp_dest < dist_pouso * 1000:
            st.error(f"🚫 Pista de pouso ({destino}) insuficiente: {comp_dest}m < {dist_pouso * 1000}m")
        else:
            st.success(f"✅ Pista de pouso ({destino}) compatível")

    except Exception as e:
        st.warning(f"Erro ao comparar pistas: {e}")

    # Exibir dados relevantes
    st.subheader(f"📄 NOTAM - {origem}")
    for notam in dados_origem["notams"]:
        st.markdown(f"- {notam}")

    st.subheader(f"🌤️ METAR - {origem}")
    for m in dados_origem["metar"]:
        st.code(m)

    st.subheader(f"📡 TAF - {origem}")
    for t in dados_origem["taf"]:
        st.code(t)

    st.markdown(f"---")

    st.subheader(f"📄 NOTAM - {destino}")
    for notam in dados_destino["notams"]:
        st.markdown(f"- {notam}")

    st.subheader(f"🌤️ METAR - {destino}")
    for m in dados_destino["metar"]:
        st.code(m)

    st.subheader(f"📡 TAF - {destino}")
    for t in dados_destino["taf"]:
        st.code(t)

    st.caption(f"Consulta em {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
