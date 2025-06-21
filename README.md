# 🛫 Assistente de Decisão de Voo

Este aplicativo fornece um apoio visual e analítico para pilotos avaliarem as condições de voo com base em dados meteorológicos (METAR e TAF), informações de NOTAMs e características das pistas dos aeródromos de origem e destino.

Desenvolvido com [Streamlit](https://streamlit.io/), consumindo dados em tempo real das APIs públicas da **AISWEB** e **REDEMET** (DECEA).

---

## ✈️ Funcionalidades

- Consulta das condições atuais e previstas de METAR/TAF.
- Exibição decodificada e interpretada das mensagens meteorológicas.
- Validação da compatibilidade das pistas com base nas exigências mínimas informadas pelo piloto.
- Consulta de NOTAMs relevantes para origem e destino.
- Decisão final automática sobre a **segurança do voo**, com justificativas visuais.

---

## 🔧 Tecnologias

- `Python 3.10+`
- `Streamlit`
- `Requests`
- `re` e `xml.etree.ElementTree` para processamento de dados
- `APIs públicas DECEA` (AISWEB e REDEMET)

---

## 🚀 Como executar localmente

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/assistente-voo.git
cd assistente-voo
```

### 2. Crie um ambiente virtual e instale as dependências

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure suas credenciais (API keys)

Crie um arquivo chamado `.streamlit/secrets.toml` com o seguinte conteúdo:

```toml
AISWEB_API_KEY = "sua_chave"
AISWEB_API_PASS = "sua_senha"
REDEMET_API_KEY = "sua_chave"
```

> ⚠️ Nunca compartilhe essas credenciais em repositórios públicos.

### 4. Rode o app

```bash
streamlit run app.py
```

---

## ☁️ Como publicar no Streamlit Cloud

1. Crie um repositório no GitHub (público ou privado).
2. Suba seu projeto com o `app.py`, `requirements.txt` e a pasta `.streamlit`.
3. Vá até [https://streamlit.io/cloud](https://streamlit.io/cloud) e conecte seu repositório.
4. Adicione suas credenciais em **Settings > Secrets** com o mesmo formato do `.toml` acima.

---

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
