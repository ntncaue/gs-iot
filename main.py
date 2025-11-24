import streamlit as st
import base64
import mimetypes
import json
import requests
import re
import google.generativeai as genai

# -----------------------------------------------------------
# CONFIG
# -----------------------------------------------------------

GEMINI_KEY = "AIzaSyDB4vy-oTmnhb83XVg3r_03Rm_RarbZofM"

def detect_dotnet_api():
    endpoints = [
        "http://localhost:5193",
        "http://192.168.0.109:5193"
    ]
    for url in endpoints:
        try:
            r = requests.get(url + "/health")
            if r.status_code == 200:
                return url
        except:
            pass
    return endpoints[0]

DOTNET_API = detect_dotnet_api()

genai.configure(api_key=GEMINI_KEY)


# -----------------------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------------------




# -----------------------------------------------------------
# EXTRATOR BRUTAL™ — Recupera QUALQUER JSON do texto
# -----------------------------------------------------------

def extract_json(text):
    """
    Extrator extremamente tolerante.
    Remove markdown, caracteres invisíveis, e tenta validar TODOS os blocos JSON possíveis.
    """

    # Remove blocos ```json ... ```
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

    # Remove caracteres invisíveis
    text = text.replace("\ufeff", "").strip()

    # PRIMEIRA TENTATIVA — procurar blocos entre { }
    candidates = re.findall(r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}", text, flags=re.DOTALL)

    # Testa cada bloco encontrado
    for c in candidates:
        try:
            return json.loads(c)
        except:
            pass

    # SEGUNDA TENTATIVA — procurar arrays []
    candidates = re.findall(r"\[.*?\]", text, flags=re.DOTALL)
    for c in candidates:
        try:
            return json.loads(c)
        except:
            pass

    # ERRO FINAL — mostra o RAW inteiro
    raise ValueError("Nenhum JSON válido encontrado.\nRAW Recebido:\n" + text)


# -----------------------------------------------------------
# Gemini — Análise do CV
# -----------------------------------------------------------

def analyze_cv(uploaded_file):
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

    model = genai.GenerativeModel('gemini-1.5-flash')

    response = model.generate_content(
        [prompt, uploaded_file]
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
    url = f"{DOTNET_API}/api/v1/skills"
    payload = {
        "name": skill,
        "description": f"Habilidade extraída: {skill}",
        "category": 1,
        "level": 1,
        "inDemand": True,
        "futureProof": True
    }

    r = requests.post(url, json=payload)

    if r.status_code not in (200, 201):
        st.error(f"Erro ao salvar skill {skill}: {r.text}")
        return None

    try:
        return r.json()["data"]["id"]
    except:
        st.error("A API respondeu sem o campo data.id")
        st.code(r.text)
        return None


def get_skill(id):
    r = requests.get(f"{DOTNET_API}/api/v1/skills/{id}")
    try:
        return r.json().get("data", {})
    except:
        return {}


# -----------------------------------------------------------
# .NET API — CAREER PATHS
# -----------------------------------------------------------

def send_career(career, meta):
    url = f"{DOTNET_API}/api/v1/career-paths"
    payload = {
        "title": career,
        "description": f"Carreira recomendada pela IA: {career}",
        "type": meta["type"],
        "estimatedYears": meta["estimatedYears"],
        "averageSalary": meta["averageSalary"],
        "jobGrowth": meta["jobGrowth"],
        "futureCareer": meta["futureCareer"]
    }

    r = requests.post(url, json=payload)

    if r.status_code not in (200, 201):
        st.error("Erro ao salvar carreira:")
        st.code(r.text)
        return None

    return r.json()["data"]["id"]


def get_career(id):
    r = requests.get(f"{DOTNET_API}/api/v1/career-paths/{id}")
    return r.json().get("data", {})


# -----------------------------------------------------------
# .NET API — PREDICTIONS (ML.NET)
# -----------------------------------------------------------

def create_prediction(user_id, career_id):
    url = f"{DOTNET_API}/api/v1/career-predictions/generate"
    payload = {
        "userId": user_id,
        "careerPathId": career_id,
        "type": 1
    }

    r = requests.post(url, json=payload)

    if r.status_code not in (200, 201):
        st.error("Erro ao gerar previsão:")
        st.code(r.text)
        return None

    return r.json()["data"]["id"]


def get_prediction(id):
    r = requests.get(f"{DOTNET_API}/api/v1/career-predictions/{id}")
    return r.json().get("data", {})


# -----------------------------------------------------------
# STREAMLIT
# -----------------------------------------------------------

st.title("📄 IA de Currículo → Carreira (.NET + Gemini + ML.NET)")
st.caption(f"API .NET detectada: **{DOTNET_API}**")

user_id = st.number_input("ID do Usuário", min_value=1, value=1)
uploaded = st.file_uploader("Envie seu currículo (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded:
    if st.button("🔍 Analisar Currículo"):
        with st.spinner("IA analisando..."):

            result = analyze_cv(uploaded)

            st.success("JSON interpretado com sucesso!")
            st.json(result)

            skills = result["skills"]
            career = result["career"]
            meta = result["career_meta"]

            # SKILLS
            st.subheader("💾 Salvando skills")
            skill_ids = []
            for skill in skills:
                sid = send_skill(skill)
                if sid:
                    skill_ids.append(sid)

            st.success(f"{len(skill_ids)} skills salvas!")

            for sid in skill_ids:
                st.json(get_skill(sid))

            # CAREER
            st.subheader("💾 Salvando carreira recomendada")
            career_id = send_career(career, meta)
            st.success(f"Carreira salva ID={career_id}")
            st.json(get_career(career_id))

            # PREDICTION
            st.subheader("📊 Gerando previsão ML.NET")
            prediction_id = create_prediction(user_id, career_id)
            st.success(f"Previsão gerada ID={prediction_id}")
            st.json(get_prediction(prediction_id))

        st.success("🎉 Processo FINALIZADO!")
