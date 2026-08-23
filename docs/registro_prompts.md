# Registro de Uso de IA como Copiloto

> Llena una fila por cada sesión de trabajo relevante en la que usaste IA
> para diseñar, escribir o depurar código. Esto es lo que la rúbrica pide
> como "Trazabilidad completa" (10%). Cópialo y ve llenándolo mientras
> avanzas — no lo dejes para el final.

## Modelos utilizados

| Herramienta | Modelo / versión | Para qué se usó |
|---|---|---|
| Claude (claude.ai) | Sonnet 5 | Diseño de arquitectura, generación de motor (BKT, sandbox, integración LLM, recomendador), contenido curricular base |
| _(agrega otras si usas más de una)_ | | |

## Registro de sesiones

### Sesión 1 — [fecha]
- **Bloqueo o tarea:** ej. "Definir la arquitectura del motor de tutoría adaptativa"
- **Prompt principal (resumen):** ej. "Diseña un sistema que use un LLM para clasificar dominio conceptual de código y lo combine con un modelo probabilístico de mastery"
- **Qué generó/resolvió la IA:** ej. "Esqueleto completo de mastery.py con Bayesian Knowledge Tracing"
- **Qué modificaste tú manualmente:** ej. "Ajusté los umbrales de MASTERY_THRESHOLD y agregué manejo de credito parcial"

### Sesión 2 — [fecha]
- **Bloqueo o tarea:**
- **Prompt principal (resumen):**
- **Qué generó/resolvió la IA:**
- **Qué modificaste tú manualmente:**

### Sesión 3 — [fecha]
- **Bloqueo o tarea:**
- **Prompt principal (resumen):**
- **Qué generó/resolvió la IA:**
- **Qué modificaste tú manualmente:**

---

**Nota para la defensa:** distingue claramente entre:
1. IA usada **para desarrollar** el proyecto (esta tabla).
2. IA usada **dentro** del proyecto en tiempo de ejecución (`llm_judge.py`,
   `exercise_generator.py`) — esa es el núcleo computacional de la
   solución, no un copiloto de desarrollo. Son conceptos distintos y en
   la defensa suelen confundirse.
