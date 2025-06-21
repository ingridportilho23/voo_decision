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
        "minutes": 1440
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
        return [decodificar_metar(m["mens"]) for m in dados.get("data", {}).get("data", [])]
    except:
        return ["Erro ao consultar METAR"]

def consultar_taf(icao):
    url = f"https://api-redemet.decea.mil.br/mensagens/taf/{icao}?api_key={REDEMET_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        dados = resp.json()
        return [decodificar_taf(m["mens"]) for m in dados.get("data", {}).get("data", [])]
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
    if match := re.search(r"(\d{2})/(\d{2})", partes):
        resumo.append(f"Temperatura: {match[1]} °C / Ponto de orvalho: {match[2]} °C")
    return "\n".join(resumo)

def decodificar_taf(taf):
    partes = taf.replace("\n", " ").replace("=", "").strip()
    resumo = []
    if "CAVOK" in partes:
        resumo.append("Céu limpo durante todo o período")
    if match := re.search(r"(\d{3}|VRB)(\d{2})KT", partes):
        direcao = "variável" if match[1] == "VRB" else match[1]
        resumo.append(f"Vento previsto: {direcao} a {match[2]} kt")
    if "BECMG" in partes:
        resumo.append("Haverá mudanças graduais nas condições")
    return "\n".join(resumo) or "TAF não decodificado"

# ==============================
# Estilos
# ==============================
def exibir_bloco_titulo(texto, cor="#4A90E2"):
    st.markdown(f"<h5 style='color:{cor}; margin-top: 1em'>{texto}</h5>", unsafe_allow_html=True)

def exibir_bloco_conteudo(texto):
    st.markdown(
        f"""
        <div style="
            background-color: #f0f0f0;
            color: #000;
            padding: 12px 18px;
            border-radius: 10px;
            font-size: 15px;
            line-height: 1.6;
            margin-bottom: 1em;
        ">
            {texto.replace('\n', '<br>')}
        </div>
        """,
        unsafe_allow_html=True
    )

# ==============================
# Streamlit Interface
# ==============================
st.set_page_config(page_title="Assistente de Voo", layout="centered")
st.title("🛫 Flight Safety Decision")

col1, col2 = st.columns(2)
with col1:
    origem = st.text_input("Aeródromo de Origem (ex: SBSP)")
    combustivel = st.number_input("Combustível (litros)", min_value=0)
    vel_cruzeiro = st.number_input("Velocidade de Cruzeiro (knots)", min_value=0)
with col2:
    destino = st.text_input("Aeródromo de Destino (ex: SBRJ)")
    dist_decolagem = st.number_input("Distância mínima de decolagem (km)", min_value=0.0, step=0.1)
    dist_pouso = st.number_input("Distância mínima de pouso (km)", min_value=0.0, step=0.1)

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

    def avaliar_pistas(local, pistas, distancia_km):
        relatorio = []
        for pista in pistas:
            comprimento = int(pista["comprimento_m"])
            if comprimento >= distancia_km * 1000:
                relatorio.append(f"✅ Pista {pista['ident']} ({local}): {comprimento}m OK")
            else:
                relatorio.append(f"🚫 Pista {pista['ident']} ({local}): {comprimento}m insuficiente")
        return relatorio

    pista_ok = True
    relatorios = []
    for trecho, dados, dist_min in [("Origem", origem_data, dist_decolagem), ("Destino", destino_data, dist_pouso)]:
        rotaer = dados["rotaer"]
        if not rotaer.get("pistas"):
            relatorios.append(f"⚠️ Sem dados de pista para {trecho}")
            pista_ok = False
        else:
            aval = avaliar_pistas(trecho, rotaer["pistas"], dist_min)
            relatorios.extend(aval)
            if any("🚫" in r for r in aval):
                pista_ok = False

    condicoes_ok = all("Erro" not in x[0] for x in [origem_data["metar"], destino_data["metar"], origem_data["taf"], destino_data["taf"]])

    if pista_ok and condicoes_ok:
        st.success("✅ CONDIÇÃO SEGURA PARA VOO")
    elif pista_ok:
        st.warning("⚠️ CONDIÇÃO CONDICIONAL - Verifique previsões e NOTAMs")
    else:
        st.error("🚫 CONDIÇÃO INSEGURA PARA VOO")

    st.markdown("### Detalhamento")
    for linha in relatorios:
        st.markdown(f"- {linha}")

    # METAR / TAF Origem
    st.markdown("### 🌤️ Condições - Origem")
    exibir_bloco_titulo("📄 METAR decodificado:")
    for m in origem_data["metar"]: exibir_bloco_conteudo(m)
    exibir_bloco_titulo("📡 TAF decodificado:")
    for t in origem_data["taf"]: exibir_bloco_conteudo(t)

    # METAR / TAF Destino
    st.markdown("### 🌥️ Condições - Destino")
    exibir_bloco_titulo("📄 METAR decodificado:")
    for m in destino_data["metar"]: exibir_bloco_conteudo(m)
    exibir_bloco_titulo("📡 TAF decodificado:")
    for t in destino_data["taf"]: exibir_bloco_conteudo(t)

    # NOTAMs
    if origem_data["notam"]:
        st.markdown("#### NOTAMs Origem")
        for n in origem_data["notam"]:
            st.markdown(f"- {n['Codigo']} ({n['DataHora']}) — {n['Informacao']}")

    if destino_data["notam"]:
        st.markdown("#### NOTAMs Destino")
        for n in destino_data["notam"]:
            st.markdown(f"- {n['Codigo']} ({n['DataHora']}) — {n['Informacao']}")

    st.caption(f"Consulta gerada em {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")