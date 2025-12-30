
import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re
from math import radians, sin, cos, sqrt, atan2

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

        lat = root.findtext("lat") or None
        lng = root.findtext("lng") or None

        pistas = []
        for r in root.findall(".//runway"):
            pistas.append({
                "ident": r.findtext("ident"),
                "comprimento_m": r.findtext("length") or "0",
                "largura_m": r.findtext("width") or "0"
            })

        return {
            "lat": lat,
            "lng": lng,
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

def coordenadas_validas(lat, lon):
    try:
        float(lat)
        float(lon)
        return True
    except:
        return False

def calcular_distancia_nm(lat1, lon1, lat2, lon2):
    R = 3440.065  # raio da Terra em milhas náuticas
    dlat = radians(float(lat2) - float(lat1))
    dlon = radians(float(lon2) - float(lon1))
    a = sin(dlat/2)**2 + cos(radians(float(lat1))) * cos(radians(float(lat2))) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def calcular_autonomia(
    lat_o, lon_o,
    lat_d, lon_d,
    combustivel_litros,
    consumo_lph,
    vel_cruzeiro_knots,
    reserva_min
):
    try:
        distancia_nm = calcular_distancia_nm(lat_o, lon_o, lat_d, lon_d)

        tempo_voo_h = distancia_nm / vel_cruzeiro_knots if vel_cruzeiro_knots > 0 else 0

        combustivel_voo = tempo_voo_h * consumo_lph
        combustivel_reserva = consumo_lph * (reserva_min / 60)

        combustivel_total_necessario = combustivel_voo + combustivel_reserva
        autonomia_ok = combustivel_litros >= combustivel_total_necessario

        return {
            "distancia_nm": distancia_nm,
            "tempo_voo_h": tempo_voo_h,
            "combustivel_voo": combustivel_voo,
            "combustivel_reserva": combustivel_reserva,
            "combustivel_total": combustivel_total_necessario,
            "autonomia_ok": autonomia_ok
        }
    except Exception as e:
        return {"erro": str(e)}
    

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
    consumo = st.number_input(
        "Consumo médio da aeronave (L/h)",
        min_value=0.0,
        help="Valor conforme POH/AFM da aeronave"
    )
with col2:
    destino = st.text_input("Aeródromo de Destino (ex: SBRJ)")
    dist_decolagem = st.number_input("Distância mínima de decolagem (m)", min_value=0, step=10)
    dist_pouso = st.number_input("Distância mínima de pouso (m)", min_value=0, step=10)
    reserva_min = st.number_input(
        "Reserva obrigatória (min)",
        value=30,
        help="RBAC 91: VFR diurno ≥ 30 min"
    )


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
    
    lat_o = origem_data["rotaer"]["lat"]
    lon_o = origem_data["rotaer"]["lng"]
    lat_d = destino_data["rotaer"]["lat"]
    lon_d = destino_data["rotaer"]["lng"]

    if coordenadas_validas(lat_o, lon_o) and coordenadas_validas(lat_d, lon_d):
        autonomia = calcular_autonomia(
            float(lat_o), float(lon_o),
            float(lat_d), float(lon_d),
            combustivel,
            consumo,
            vel_cruzeiro,
            reserva_min
        )
    else:
        autonomia = {
            "erro": "Coordenadas indisponíveis no ROTAER",
            "autonomia_ok": False
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

   # ==============================
    # Condição Final para Voo
    # ==============================

    autonomia_disponivel = "erro" not in autonomia

    if pista_ok and not alertas:
        if autonomia_disponivel:
            if autonomia["autonomia_ok"]:
                st.success("✅ CONDIÇÃO SEGURA PARA VOO")
            else:
                st.error("🚫 CONDIÇÃO INSEGURA PARA VOO (Combustível insuficiente)")
        else:
            st.warning(
                "⚠️ CONDIÇÃO CONDICIONAL PARA VOO\n\n"
                "Pistas, meteorologia e NOTAMs estão adequados.\n"
                "⚠️ Autonomia de combustível não pôde ser avaliada automaticamente.\n"
                "➡️ Verifique manualmente o combustível conforme POH/AFM."
            )

    elif pista_ok:
        if autonomia_disponivel:
            if autonomia["autonomia_ok"]:
                st.warning("⚠️ CONDIÇÃO CONDICIONAL - Verifique previsões meteorológicas e NOTAMs")
            else:
                st.error("🚫 CONDIÇÃO INSEGURA PARA VOO (Combustível insuficiente)")
        else:
            st.warning("⚠️ CONDIÇÃO CONDICIONAL - Verifique previsões meteorológicas, NOTAMs e autonomia de combustível")

    else:
        st.error("🚫 CONDIÇÃO INSEGURA PARA VOO")

    # ==============================
    # Avaliação de Autonomia de Combustível
    # ==============================

    st.markdown("### ⛽ Autonomia de Combustível")

    if "erro" in autonomia:
        st.warning(
            "⚠️ Não foi possível avaliar a autonomia de combustível para este voo."
        )
    else:
        exibir_bloco_conteudo(
            f"""
            Distância estimada: {autonomia['distancia_nm']:.1f} NM  
            Tempo estimado de voo: {autonomia['tempo_voo_h']:.2f} h  
            Combustível para o voo: {autonomia['combustivel_voo']:.1f} L  
            Reserva regulamentar: {autonomia['combustivel_reserva']:.1f} L  
            Combustível total necessário: {autonomia['combustivel_total']:.1f} L  
            Combustível disponível: {combustivel:.1f} L
            """
        )

        if autonomia["autonomia_ok"]:
            st.success("✅ Combustível suficiente para o voo (incluindo reserva)")
        else:
            st.error("🚫 Combustível insuficiente considerando a reserva obrigatória")

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
