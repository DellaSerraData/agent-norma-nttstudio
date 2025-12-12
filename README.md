# Streamlit + LangChain Demo

Este é um projeto simples demonstrando a integração do [Streamlit](https://streamlit.io/) com [LangChain](https://langchain.com/).

## Instalação

1. Crie um ambiente virtual (opcional, mas recomendado):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

## Configuração da API Key

- Defina a variável de ambiente `OPENAI_API_KEY`, ou
- Crie um arquivo `.env` na raiz com:
  ```
  OPENAI_API_KEY=sua-chave-aqui
  ```

## Como Executar

1. Execute o aplicativo Streamlit:
   ```bash
   streamlit run app.py
   ```
2. Abra o navegador no endereço indicado (geralmente `http://localhost:8501`).
3. Informe sua OpenAI API Key na barra lateral (ou use a carregada do `.env`).
4. Comece a conversar!

## Estrutura

- `app.py`: Arquivo principal da aplicação Streamlit.
- `chain.py`: Lógica de integração com LangChain e OpenAI.
- `requirements.txt`: Lista de dependências do projeto.
