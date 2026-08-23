"""
llm_judge.py
------------
Este modulo es el NUCLEO DE IA del proyecto: envia el codigo del estudiante
a un LLM (Anthropic Claude, Google Gemini o Groq -- intercambiables) y
obtiene una clasificacion probabilistica de que tan bien domina cada
concepto asociado al nivel. NO es una llamada decorativa: la salida
estructurada (JSON) es la que alimenta directamente al modelo de mastery
(BKT) y a la recomendacion.

Configuracion (variables de entorno, o desde la barra lateral de app.py):
    LLM_PROVIDER = "anthropic" | "gemini" | "groq"   (default: "anthropic")
    ANTHROPIC_API_KEY   -> si usas Claude (ej. claude-sonnet-5, claude-fable-5)
    ANTHROPIC_MODEL     -> default "claude-sonnet-5"
    GOOGLE_API_KEY        -> si usas Gemini via Google AI Studio
    GEMINI_MODEL           -> default "gemini-2.0-flash"
    GROQ_API_KEY           -> si usas Groq (console.groq.com/keys)
    GROQ_MODEL              -> default "openai/gpt-oss-120b"

Nota: Fable (Claude) es exclusivo de Anthropic -- no esta disponible via
Groq ni Google AI Studio, cada proveedor aloja sus propios modelos.

Registro de "IA como copiloto" del PROPIO proyecto (para la documentacion
exigida por la rubrica) va aparte, en docs/registro_prompts.md -- esto de
aqui es la IA usada EN TIEMPO DE EJECUCION por la aplicacion, que es lo que
la rubrica exige que sea el nucleo computacional.
"""

import os
import json

JUDGE_SYSTEM_PROMPT = """Eres un evaluador tecnico de codigo para una plataforma educativa \
de fundamentos de programacion. Recibiras: el enunciado de un ejercicio, los conceptos que \
evalua, y el codigo que un estudiante escribio como solucion.

Tu tarea es analizar el CODIGO EN SI (no solo si el resultado es correcto) y devolver \
UNICAMENTE un JSON valido con esta forma exacta, sin texto adicional:

{
  "concept_scores": {"<concepto>": <float 0.0-1.0>},
  "detected_issues": ["<breve descripcion de un error o mala practica detectada>"],
  "feedback": "<1-2 frases de retroalimentacion dirigida al estudiante, en espanol>"
}

concept_scores debe reflejar que tan bien el codigo demuestra comprension real del \
concepto (no memorizacion): 1.0 = dominio solido, 0.5 = comprension parcial o con \
errores menores, 0.0 = no demuestra comprension del concepto o esta ausente."""


def _build_user_prompt(level: dict, student_code: str, test_result: dict) -> str:
    return json.dumps({
        "ejercicio": level["exercise"]["prompt"],
        "concepto_principal": level["concept"],
        "codigo_estudiante": student_code,
        "resultado_tests": test_result,
    }, ensure_ascii=False)


def _call_anthropic(system: str, user: str) -> str:
    from anthropic import Anthropic  # pip install anthropic
    client = Anthropic()  # lee ANTHROPIC_API_KEY del entorno
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
    resp = client.messages.create(
        model=model,
        max_tokens=500,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text


def _call_gemini(system: str, user: str) -> str:
    import google.generativeai as genai  # pip install google-generativeai
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    model = genai.GenerativeModel(model_name, system_instruction=system)
    resp = model.generate_content(user)
    return resp.text


def _call_groq(system: str, user: str) -> str:
    from groq import Groq  # pip install groq
    client = Groq()  # lee GROQ_API_KEY del entorno
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    resp = client.chat.completions.create(
        model=model,
        max_tokens=500,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content


def _call_llm(system: str, user: str) -> str:
    # Se lee el proveedor en CADA llamada (no una sola vez al importar el
    # modulo) para que cambiarlo desde la barra lateral de app.py, en medio
    # de una sesion, tenga efecto inmediato sin reiniciar la app.
    provider = os.environ.get("LLM_PROVIDER", "anthropic")
    if provider == "gemini":
        return _call_gemini(system, user)
    if provider == "groq":
        return _call_groq(system, user)
    return _call_anthropic(system, user)


def judge_submission(level: dict, student_code: str, test_result: dict) -> dict:
    """
    Devuelve algo como:
    {
      "concept_scores": {"recursion": 0.8},
      "detected_issues": ["No maneja el caso base para n=0"],
      "feedback": "Tu logica recursiva es correcta pero revisa el caso base."
    }
    Si la llamada al LLM falla (sin API key configurada, sin conexion, etc.)
    cae a un fallback determinista basado solo en el resultado de los tests,
    para que el motor nunca se caiga por completo -- pero queda registrado
    que ese turno NO tuvo analisis conceptual real, solo aprobado/reprobado.
    """
    user_prompt = _build_user_prompt(level, student_code, test_result)
    try:
        raw = _call_llm(JUDGE_SYSTEM_PROMPT, user_prompt)
        raw = raw.strip().strip("```json").strip("```").strip()
        parsed = json.loads(raw)
        parsed["_source"] = "llm"
        return parsed
    except Exception as e:
        concept = level["concept"]
        fallback_score = 1.0 if test_result.get("passed") else 0.2
        return {
            "concept_scores": {concept: fallback_score},
            "detected_issues": [f"Analisis LLM no disponible ({type(e).__name__}); usando fallback por tests."],
            "feedback": "Analisis conceptual detallado no disponible en este momento.",
            "_source": "fallback",
            "_error": str(e),
        }

