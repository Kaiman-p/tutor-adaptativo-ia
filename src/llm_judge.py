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
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text


def _call_gemini(system: str, user: str) -> str:
    import google.generativeai as genai  # pip install google-generativeai
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
    model = genai.GenerativeModel(model_name, system_instruction=system)
    resp = model.generate_content(user)
    return resp.text


def _call_groq(system: str, user: str) -> str:
    from groq import Groq  # pip install groq
    client = Groq(timeout=30.0)  # mas margen de tiempo, la VM puede ser mas lenta
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    # max_tokens alto a proposito: gpt-oss-120b es un modelo "razonador"
    # que gasta una parte de los tokens pensando internamente (ver
    # reasoning_tokens en la respuesta) antes de escribir el JSON final.
    # Con poco margen, la respuesta puede llegar vacia o cortada.
    resp = client.chat.completions.create(
        model=model,
        max_tokens=1024,
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


REEXPLAIN_SYSTEM_PROMPT = """Eres un profesor paciente que explica fundamentos de programacion a \
alguien que nunca ha programado antes (puede ser un adolescente o un adulto sin ningun \
conocimiento tecnico previo). Se te dara un concepto y su explicacion actual, que la persona \
NO entendio. Tu trabajo es explicarlo de nuevo, de una forma COMPLETAMENTE DISTINTA a la \
explicacion original -- usa una analogia diferente, un ejemplo de la vida cotidiana distinto, \
y un lenguaje todavia mas simple. Evita jerga tecnica sin explicarla. Maximo 3 parrafos cortos. \
Responde en espanol, en texto plano (sin JSON, sin markdown)."""


def reexplain_concept(language: str, concept: str, explicacion_actual: str) -> dict:
    """
    Genera una explicacion ALTERNATIVA del concepto de un nivel, para el
    boton "no entendi, explicamelo diferente" en la interfaz. Esto refuerza
    el criterio de Personalizacion: el contenido se adapta en vivo a lo que
    el estudiante necesita, en vez de ser siempre el mismo texto estatico.
    """
    user_prompt = json.dumps({
        "lenguaje": language,
        "concepto": concept,
        "explicacion_que_no_entendio": explicacion_actual,
    }, ensure_ascii=False)
    try:
        texto = _call_llm(REEXPLAIN_SYSTEM_PROMPT, user_prompt)
        return {"texto": texto.strip(), "_source": "llm"}
    except Exception as e:
        return {
            "texto": "No se pudo generar una nueva explicacion en este momento "
                     "(revisa tu conexion o API key). Mientras tanto, relee el "
                     "ejemplo resuelto con calma, o pregunta a un companero.",
            "_source": "fallback",
            "_error": str(e),
        }


HINT_SYSTEM_PROMPT = """Eres un tutor de programacion ayudando a un estudiante principiante que \
esta atascado en un ejercicio. Te daran el enunciado del ejercicio y el codigo base (sin resolver). \

Tu tarea es dar una PISTA en pasos de razonamiento -- NUNCA escribas el codigo completo de la \
solucion ni la linea exacta que hay que escribir. Divide el problema en 3 a 5 pasos de pensamiento \
(que revisar primero, que estructura de control conviene usar, que caso especial no hay que \
olvidar), en lenguaje simple para alguien sin experiencia previa. El objetivo es que la persona \
piense y termine escribiendo el codigo por si misma, no que se lo copies.

Responde en espanol, en texto plano, con los pasos numerados, sin codigo completo."""


def generate_hint(level: dict, language: str) -> dict:
    """
    Genera una pista de razonamiento (sin la solucion completa) para el
    ejercicio actual, para el boton "necesito una pista" en la interfaz.
    """
    user_prompt = json.dumps({
        "lenguaje": language,
        "ejercicio": level["exercise"]["prompt"],
        "codigo_base": level["exercise"]["starter_code"],
    }, ensure_ascii=False)
    try:
        texto = _call_llm(HINT_SYSTEM_PROMPT, user_prompt)
        return {"texto": texto.strip(), "_source": "llm"}
    except Exception as e:
        return {
            "texto": "No se pudo generar una pista en este momento. Mientras tanto: "
                     "relee el ejemplo resuelto de la leccion, e identifica que parte "
                     "de ese ejemplo se parece a lo que te estan pidiendo aqui.",
            "_source": "fallback",
            "_error": str(e),
        }


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

