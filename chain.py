from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


def get_chain(api_key):
    if not api_key:
        return None

    model = ChatOpenAI(openai_api_key=api_key, model="gpt-3.5-turbo")
    prompt = ChatPromptTemplate.from_template(
        "Responda à seguinte mensagem de forma útil e concisa: {topic}"
    )
    output_parser = StrOutputParser()

    chain = prompt | model | output_parser
    return chain
