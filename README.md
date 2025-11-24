# IA de Currículo + Carreira

Este projeto é uma aplicação em Streamlit que utiliza a API do Gemini para analisar currículos e recomendar uma carreira para o usuário. A aplicação também se integra com uma API .NET para salvar as habilidades e os dados da carreira.

## Funcionalidades

- Upload de currículo em formato PDF, PNG, JPG ou JPEG.
- Análise do currículo utilizando a API do Gemini.
- Extração de habilidades do currículo.
- Recomendação de carreira com base no currículo.
- Integração com uma API .NET para salvar as habilidades e os dados da carreira.
- Geração de previsão de carreira utilizando ML.NET.

## Como executar

1. Crie um ambiente virtual e ative-o:
```
python -m venv venv
source venv/bin/activate
```
2. Instale as dependências:
```
pip install -r requirements.txt
```
3. Execute a aplicação:
```
streamlit run main.py
```

## Dependências

- streamlit
- requests
- python-dotenv

**Observação:** Certifique-se de que a API .NET esteja em execução e acessível pela aplicação. O endereço da API é detectado automaticamente, mas pode ser configurado manualmente no código.
