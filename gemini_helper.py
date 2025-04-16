import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def configure_api(api_key):
    """
    Configures the Generative AI API with the provided API key.
    
    Args:
        api_key (str): The API key for the Generative AI service.
    """
    genai.configure(api_key=api_key)

def create_model(model_name, system_instruction):
    """
    Creates a GenerativeModel instance with the specified model name and system instruction.
    
    Args:
        model_name (str): The name of the generative model.
        system_instruction (str): The system instruction for the model.
    
    Returns:
        genai.GenerativeModel: The configured generative model instance.
    """
    return genai.GenerativeModel(model_name, system_instruction=system_instruction)

def answer_question(model, context, question):
    """
    Provides an answer to a question based on the given context.
    
    Args:
        model (genai.GenerativeModel): The generative model instance.
        context (str): The context or document.
        question (str): The question to answer.
    
    Returns:
        str: The generated answer.
    """
    response = model.generate_content(
        f"Context: {context}\nQuestion: {question}",
        generation_config=genai.GenerationConfig(
            max_output_tokens=1000,
            temperature=0.1,
        )
    )
    return response.text.strip()

if __name__ == "__main__":
    # Test the Gemini integration
    configure_api(os.getenv("GEMINI_API_KEY"))
    model = create_model("gemini-1.5-flash", "You are a senior data analyst.")
    answer = answer_question(model, "Artificial Intelligence is a field of study that...", "What is AI?")
    print("Answer:", answer)
