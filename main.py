import streamlit as st
import base64
import requests
import mimetypes
import json

GEMINI_KEY = "AIzaSyDB4vy-oTmnhb83XVg3r_03Rm_RarbZofM"

# -----------------------------------------------------------
# Detecta automaticamente onde a API .NET está rodando
# -----------------------------------------------------------
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

# -----------------------------------------------------------
# Convert file to base64
# -----------------------------------------------------------
def file_to_base64(file):
    return base64.b64encode(file.read()).decode()

# -----------------------------------------------------------
# Gemini Vision API
# -----------------------------------------------------------
def analyze_cv(base64_file, mime_type):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

    prompt = """
    Analise este currículo e retorne SOMENTE o JSON abaixo, sem nada fora do JSON.

    {
        "skills": ["skill1", "skill2", "..."],
        "career": "carreira recomendada pela IA",
        "recommendation": "explicação da recomendação",
        "career_meta": {
            "type": 0,
            "estimatedYears": 0,
            "averageSalary": 0.0,
            "jobGrowth": 0,
            "futureCareer": true
        }
    }

    Regras do career_meta:
    - "type": 0 = Tech, 1 = Business, 2 = Saúde, 3 = Criativo, 4 = Operacional
    - estimatedYears: tempo médio para entrar nessa carreira
    - averageSalary: salário médio no Brasil
    - jobGrowth: previsão de crescimento (0 a 100)
    - futureCareer: true/false
    """

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": base64_file}}
                ]
            }
        ]
    }

    response = requests.post(url, json=payload)
    response.raise_for_status()

    text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)

# -----------------------------------------------------------
# POST Skill (sem auth)
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
    if r.status_code in (200, 201):
        return r.json()["id"]
    return None

# -----------------------------------------------------------
# GET Skill (sem auth)
# -----------------------------------------------------------
def get_skill(id):
    url = f"{DOTNET_API}/api/v1/skills/{id}"
    return requests.get(url).json()

# -----------------------------------------------------------
# POST Career (com dados da IA)
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
    return r.json()["id"]

# -----------------------------------------------------------
# GET Career (sem auth)
# -----------------------------------------------------------
def get_career(id):
    url = f"{DOTNET_API}/api/v1/career-paths/{id}"
    return requests.get(url).json()

# -----------------------------------------------------------
# POST Prediction ML.NET (sem auth)
# -----------------------------------------------------------
def create_prediction(user_id, career_id):
    url = f"{DOTNET_API}/api/v1/career-predictions/generate"

    payload = {
        "userId": user_id,
        "careerPathId": career_id,
        "type": 1
    }

    r = requests.post(url, json=payload)
    return r.json()["id"]

# -----------------------------------------------------------
# GET Prediction (sem auth)
# -----------------------------------------------------------
def get_prediction(id):
    url = f"{DOTNET_API}/api/v1/career-predictions/{id}"
    return requests.get(url).json()

# -----------------------------------------------------------
# STREAMLIT UI
# -----------------------------------------------------------
st.title("📄 IA de Currículo + Carreira (Gemini + .NET + ML.NET — sem autenticação)")

st.caption(f"API conectada em: **{DOTNET_API}**")

user_id = st.number_input("ID do Usuário", min_value=1, value=1)
uploaded = st.file_uploader("Envie seu currículo", type=["png", "jpg", "jpeg", "pdf"])

if uploaded:

    mime_type = mimetypes.guess_type(uploaded.name)[0]

    if st.button("🔍 Analisar Currículo"):
        st.info("Processando currículo com Gemini...")

        base64_file = file_to_base64(uploaded)
        result = analyze_cv(base64_file, mime_type)

        st.success("Análise concluída pela IA!")
        st.json(result)

        skills = result["skills"]
        career = result["career"]
        meta = result["career_meta"]

        # ------------------------------
        # POST skills
        # ------------------------------
        st.subheader("💾 Enviando skills para a API .NET...")
        skill_ids = []

        for s in skills:
            sid = send_skill(s)
            if sid:
                skill_ids.append(sid)

        st.success(f"{len(skill_ids)} skills salvas com sucesso!")

        # ------------------------------
        # GET skills salvas
        # ------------------------------
        st.subheader("📌 Skills gravadas na API:")
        for sid in skill_ids:
            st.json(get_skill(sid))

        # ------------------------------
        # POST career com dados da IA
        # ------------------------------
        st.subheader("💾 Salvando carreira recomendada...")
        career_id = send_career(career, meta)
        st.success(f"Carreira salva! ID = {career_id}")

        st.subheader("📌 Carreira cadastrada📌")
        st.json(get_career(career_id))

        # ------------------------------
        # POST prediction ML.NET
        # ------------------------------
        st.subheader("🤖Gerando previsão de carreira (ML.NET)...")
        prediction_id = create_prediction(user_id, career_id)
        st.success(f"Previsão criada! ID = {prediction_id}")

        st.subheader("📌 Previsão ML.NET:")
        st.json(get_prediction(prediction_id))

        st.success("🎉Processo completo!")