"""
exercise_generator.py
----------------------
Cuando el modelo de mastery detecta dominio bajo en un concepto, en vez de
simplemente repetir el mismo ejercicio, la IA genera uno nuevo y mas simple,
enfocado exclusivamente en ese concepto. Esto es automatizacion real: el
contenido no esta pre-escrito, se produce en tiempo de ejecucion segun el
estado del estudiante.
"""

import json
from llm_judge import _call_llm

GENERATOR_SYSTEM_PROMPT = """Eres un disenador de ejercicios de programacion para principiantes. \
Se te dara un lenguaje y un concepto especifico en el que un estudiante tiene dificultades. \
Genera UN ejercicio nuevo, mas simple que el original, enfocado unicamente en ese concepto.

Responde UNICAMENTE con JSON valido de esta forma:
{
  "prompt": "<enunciado claro y corto>",
  "starter_code": "<codigo base con la firma de la funcion, sin resolver>",
  "hint": "<una pista breve, sin dar la solucion completa>"
}"""


def generate_remedial_exercise(language: str, concept: str, previous_issues: list) -> dict:
    user_prompt = json.dumps({
        "lenguaje": language,
        "concepto": concept,
        "errores_previos_detectados": previous_issues,
    }, ensure_ascii=False)

    try:
        raw = _call_llm(GENERATOR_SYSTEM_PROMPT, user_prompt)
        raw = raw.strip().strip("```json").strip("```").strip()
        parsed = json.loads(raw)
        parsed["_source"] = "llm_generated"
        return parsed
    except Exception as e:
        return {
            "prompt": f"(Fallback) Practica manualmente el concepto '{concept}' en {language} "
                      f"antes de continuar.",
            "starter_code": "",
            "hint": "Generador de IA no disponible en este momento.",
            "_source": "fallback",
            "_error": str(e),
        }
