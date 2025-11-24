import streamlit as st
import base64
import mimetypes
import json
import requests
import re
from google import genai
from dotenv import load_dotenv
import os

# -----------------------------------------------------------
# CONFIG
# -----------------------------------------------------------

# Carrega o arquivo .env
load_dotenv()

# Chave da API do Google Gemini
GEMINI_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_KEY:
    raise ValueError("GOOGLE_API_KEY não encontrada no arquivo .env")

# Endpoints da API .NET
DOTNET_LOCAL = os.getenv("DOTNET_LOCAL")
DOTNET_IP = os.getenv("DOTNET_IP")
if not DOTNET_LOCAL or not DOTNET_IP:
    raise ValueError("DOTNET_LOCAL ou DOTNET_IP não encontradas no arquivo .env")

# Função para detectar endpoint ativo
def detect_dotnet_api():
    endpoints = [DOTNET_LOCAL, DOTNET_IP]
    for url in endpoints:
        try:
            r = requests.get(url + "/health")
            if r.status_code == 200:
                return url
        except:
            pass
    raise RuntimeError("Nenhum endpoint da API .NET está ativo!")

# Detecta o endpoint ativo
DOTNET_API = detect_dotnet_api()

# Cliente Gemini
client = genai.Client(api_key=GEMINI_KEY)



# -----------------------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------------------

def file_to_base64(file):
    return base64.b64encode(file.read()).decode()

def extract_json(raw):
    raw = raw.replace("\ufeff", "").strip()
    match = re.search(r"{[\s\S]*}", raw)
    if match:
        json_str = match.group(0).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Erro ao decodificar JSON: {e}\nConteúdo: {json_str}")
    raise ValueError("Nenhum JSON válido foi encontrado na resposta da IA.\nRAW Recebido:\n" + raw)

# -----------------------------------------------------------
# Gemini — Análise do CV
# -----------------------------------------------------------

def analyze_cv(base64_file, mime_type):
    prompt = """
    Analise este currículo e retorne SOMENTE o JSON abaixo.
    Você é um modelo que DEVE retornar apenas JSON puro SEM markdown, SEM explicações.

    {
        "skills": [],
        "career": "",
        "recommendation": "",
        "career_meta": {
            "type": 0,
            "estimatedYears": 0,
            "averageSalary": 0,
            "jobGrowth": 0,
            "futureCareer": true
        }
    }

    Regras:
    - type: 0=Tech, 1=Business, 2=Saúde, 3=Criativo, 4=Operacional
    - estimatedYears: anos para iniciar
    - salary: média no Brasil
    - jobGrowth: 0–100
    """
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[{
            "role": "user",
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime_type, "data": base64_file}}
            ]
        }]
    )

    raw = response.text.strip()
    st.subheader("RAW do Gemini:")
    st.code(raw)
    json_data = extract_json(raw)
    return json_data

# -----------------------------------------------------------
# .NET API — SKILLS
# -----------------------------------------------------------

def send_skill(skill):
    url = f"{DOTNET_API}/api/v1/Skills"
    payload = {
        "name": skill,
        "description": f"Habilidade extraída: {skill}",
        "category": 1,
        "level": 1,
        "inDemand": True,
        "futureProof": True
    }

    st.write("➡️ Enviando skill:")
    st.json(payload)

    r = requests.post(url, json=payload)
    st.write("Status:", r.status_code)
    st.write("Resposta:", r.text)

    if r.status_code not in (200, 201):
        st.error(f"Erro ao salvar skill '{skill}' (status {r.status_code})")
        return None

    try:
        resp = r.json()
        if resp.get("success") and resp.get("data"):
            skill_id = resp["data"]["id"]
            st.success(f"Skill '{skill}' salva com sucesso! ID={skill_id}")
            return skill_id
        else:
            st.warning(f"API retornou sucesso=False ou sem dados ao salvar skill '{skill}'")
            return None
    except Exception as e:
        st.error(f"Erro ao processar resposta da API ao salvar skill '{skill}': {e}")
        return None

def get_skill(skill_id):
    r = requests.get(f"{DOTNET_API}/api/v1/Skills/{skill_id}")
    try:
        return r.json().get("data", {})
    except:
        return {}

# -----------------------------------------------------------
# .NET API — CAREER PATHS
# -----------------------------------------------------------

def send_career(career, meta):
    url = f"{DOTNET_API}/api/v1/CareerPaths"
    payload = {
        "title": career,
        "description": f"Carreira recomendada pela IA: {career}",
        "type": meta["type"],
        "estimatedYears": meta["estimatedYears"],
        "averageSalary": meta["averageSalary"],
        "jobGrowth": meta["jobGrowth"],
        "futureCareer": meta["futureCareer"]
    }

    st.write("➡️ Enviando carreira:")
    st.json(payload)

    r = requests.post(url, json=payload)
    st.write("Status:", r.status_code)
    st.write("Resposta:", r.text)

    if r.status_code not in (200, 201):
        st.error(f"Erro ao salvar carreira '{career}' (status {r.status_code})")
        return None

    try:
        resp = r.json()
        if resp.get("success") and resp.get("data"):
            career_id = resp["data"]["id"]
            st.success(f"Carreira '{career}' salva com sucesso! ID={career_id}")
            return career_id
        else:
            st.warning(f"API retornou sucesso=False ou sem dados ao salvar carreira '{career}'")
            return None
    except Exception as e:
        st.error(f"Erro ao processar resposta da API ao salvar carreira '{career}': {e}")
        return None

def get_career(career_id):
    r = requests.get(f"{DOTNET_API}/api/v1/CareerPaths/{career_id}")
    try:
        return r.json().get("data", {})
    except:
        return {}

# -----------------------------------------------------------
# .NET API — PREDICTIONS (ML.NET)
# -----------------------------------------------------------

def create_prediction(user_id, career_id):
    url = f"{DOTNET_API}/api/v1/CareerPredictions/generate"
    payload = {
        "userId": user_id,
        "careerPathId": career_id,
        "type": 1
    }

    st.write("➡️ Enviando previsão:")
    st.json(payload)

    r = requests.post(url, json=payload)
    st.write("Status:", r.status_code)
    st.write("Resposta:", r.text)

    if r.status_code not in (200, 201):
        st.error(f"Erro ao gerar previsão (status {r.status_code})")
        return None

    try:
        resp = r.json()
        if resp.get("success") and resp.get("data"):
            prediction_id = resp["data"]["id"]
            st.success(f"Previsão gerada com sucesso! ID={prediction_id}")
            return prediction_id
        else:
            st.warning("API retornou sucesso=False ou sem dados ao gerar previsão")
            return None
    except Exception as e:
        st.error(f"Erro ao processar resposta da API ao gerar previsão: {e}")
        return None

def get_prediction(prediction_id):
    url = f"{DOTNET_API}/api/v1/CareerPredictions/{prediction_id}"
    r = requests.get(url)
    st.write("➡️ Recuperando previsão:")
    st.write("Status:", r.status_code)
    st.write("Resposta:", r.text)

    if r.status_code != 200:
        st.error(f"Erro ao recuperar previsão ID={prediction_id} (status {r.status_code})")
        return None

    try:
        resp = r.json()
        if resp.get("success") and resp.get("data"):
            data = resp["data"]
            # Exibir de forma legível
            st.subheader("📊 Previsão de Carreira")
            st.write(f"**Análise:** {data.get('analysis')}")
            st.write(f"**Recomendações:** {data.get('recommendations')}")
            st.write(f"**Skills a desenvolver:** {data.get('skillsToDevelop')}")
            st.write(f"**Pontuação de compatibilidade:** {data.get('compatibilityScore')}")
            st.write(f"**Gerado em:** {data.get('predictedAt')}")
            return data
        else:
            st.warning("API retornou sucesso=False ou sem dados")
            return None
    except Exception as e:
        st.error(f"Erro ao processar resposta da API ao recuperar previsão: {e}")
        return None

# -----------------------------------------------------------
# STREAMLIT
# -----------------------------------------------------------

st.title("📄 IA de Currículo → Carreira (.NET + Gemini + ML.NET)")
st.caption(f"API .NET detectada: **{DOTNET_API}**")

user_id = st.number_input("ID do Usuário", min_value=1, value=1)
uploaded = st.file_uploader("Envie seu currículo (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded:
    mime_type = mimetypes.guess_type(uploaded.name)[0]
    base64_file = file_to_base64(uploaded)

    if st.button("🔍 Analisar Currículo"):
        with st.spinner("IA analisando..."):

            # ---------- ANALISAR CV ----------
            result = analyze_cv(base64_file, mime_type)
            st.success("JSON interpretado com sucesso!")
            st.json(result)

            skills = result.get("skills", [])
            career = result.get("career", "")
            meta = result.get("career_meta", {})

            # ---------- SKILLS ----------
            st.subheader("💾 Salvando skills")
            skill_ids = []
            for skill in skills:
                sid = send_skill(skill)
                if sid:
                    skill_ids.append(sid)

            if skill_ids:
                st.success(f"{len(skill_ids)} skills salvas com sucesso!")
                for sid in skill_ids:
                    skill_data = get_skill(sid)
                    st.write(f"- {skill_data.get('name')} (ID={sid})")
            else:
                st.warning("Nenhuma skill foi salva.")

            # ---------- CAREER ----------
            st.subheader("💾 Salvando carreira recomendada")
            career_id = None
            if career and meta:
                career_id = send_career(career, meta)
                if career_id:
                    career_data = get_career(career_id)
                    st.write(f"**Título:** {career_data.get('title')}")
                    st.write(f"**Descrição:** {career_data.get('description')}")
                    st.write(f"**Tipo:** {career_data.get('type')}")
                    st.write(f"**Salário Médio:** {career_data.get('averageSalary')}")
                else:
                    st.warning("Carreira não foi salva.")
            else:
                st.warning("Nenhuma carreira detectada para salvar.")

            # ---------- PREDICTION ----------
            st.subheader("📊 Gerando previsão ML.NET")
            if career_id:
                prediction_id = create_prediction(user_id, career_id)
                if prediction_id:
                    get_prediction(prediction_id)
                else:
                    st.warning("Previsão não foi gerada.")
            else:
                st.warning("Previsão não pode ser gerada sem carreira.")

        st.success("🎉 Processo FINALIZADO!")
