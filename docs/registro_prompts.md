# Registro de Uso de IA como Copiloto

> Registro de las sesiones de trabajo con IA usadas para diseñar, escribir
> y depurar este proyecto. Esto es lo que la rúbrica pide como
> "Trazabilidad completa" (10%).

## Modelos utilizados

| Herramienta | Modelo / versión | Para qué se usó |
|---|---|---|
| Claude (claude.ai) | Sonnet 5 | Diseño de arquitectura completa, generación del motor (BKT, sandbox multi-lenguaje, integración LLM, recomendador), currícula de los 32 niveles, depuración de conexión con proveedores de IA, configuración de Git/GitHub |
| [OpenAI Tokenizer](https://platform.openai.com/tokenizer) | — (herramienta de análisis, no un modelo) | Verificar cómo se descomponen los prompts en tokens entre distintas plataformas — visto en clase como referencia para entender consumo de tokens al automatizar prompts. Se usó como apoyo conceptual durante la Sesión 3 para entender por qué `gpt-oss-120b` (Groq) consumía tokens en razonamiento interno (`reasoning_tokens`) antes de escribir su respuesta visible |

## Registro de sesiones

### Sesión 1 — 22 de agosto de 2026
- **Bloqueo o tarea:** definir qué proyecto construir a partir del documento de especificaciones del Summer Camp, y diseñar una arquitectura donde la IA fuera el núcleo computacional real (no decorativo).
- **Prompt principal (resumen):** análisis del PDF de especificaciones + "quiero un tutor adaptativo de programación tipo videojuego, con IA analizando el código del estudiante para detectar dominio conceptual real, para practicar los fundamentos de los lenguajes más usados".
- **Qué generó/resolvió la IA:** arquitectura completa del motor (`mastery.py` con Bayesian Knowledge Tracing, `sandbox.py`, `llm_judge.py`, `recommender.py`, `exercise_generator.py`), y la currícula base de niveles.
- **Qué modifiqué yo:** decisión de escalar de 10 a 4 lenguajes (Python, C, Java, SQL en vez de C/Python/JavaScript inicial), y de 5 a 8 niveles por lenguaje para mayor profundidad.

### Sesión 2 — 22 de agosto de 2026
- **Bloqueo o tarea:** integrar Groq como proveedor de IA (visto en clase, con capa gratuita), además de Anthropic/Gemini que ya estaban soportados.
- **Prompt principal (resumen):** "quiero usar Groq, no sé nada de APIs, ayúdame a configurarlo".
- **Qué generó/resolvió la IA:** función `_call_groq` en `llm_judge.py`, selector de proveedor en la interfaz, y guía paso a paso para crear la API key en console.groq.com.
- **Qué modifiqué yo:** ninguna modificación de código; configuré mi propia API key en la interfaz.

### Sesión 3 — 22-23 de agosto de 2026
- **Bloqueo o tarea:** la IA caía en modo *fallback* (`APIConnectionError`) al usar Groq desde mi VM de Kali Linux, aunque la conexión de red funcionaba (confirmado con `curl`).
- **Prompt principal (resumen):** diagnóstico paso a paso del error real usando scripts de prueba aislados (`test_groq.py`, `test_groq2.py`).
- **Qué generó/resolvió la IA:** identificó que `openai/gpt-oss-120b` es un modelo "razonador" que gasta tokens en pensar internamente antes de responder (confirmado viendo `reasoning_tokens` en la respuesta real de la API); corrigió `max_tokens` de 500 a 1024 y agregó `timeout` más alto.
- **Qué modifiqué yo:** ninguna, apliqué el fix generado.
- **Herramienta de apoyo:** [OpenAI Tokenizer](https://platform.openai.com/tokenizer), vista en clase como herramienta para automatizar y verificar el conteo de tokens de un prompt entre distintas plataformas de IA — util aquí para entender conceptualmente por qué un mismo `max_tokens` rinde distinto según el modelo (los modelos "razonadores" como gpt-oss-120b consumen una parte de ese límite en tokens de razonamiento interno, no solo en la respuesta final).

### Sesión 4 — 23 de agosto de 2026
- **Bloqueo o tarea:** Groq seguía fallando de forma intermitente desde la VM; probé Google AI Studio (Gemini) como alternativa.
- **Prompt principal (resumen):** configuración de Gemini + corrección de un error real de la API ("model gemini-2.0-flash is no longer available, use gemini-3.6-flash").
- **Qué generó/resolvió la IA:** actualización del modelo por defecto en `llm_judge.py` y `app.py`.
- **Qué modifiqué yo:** configuré mi API key de Google AI Studio; verifiqué en vivo que la IA daba feedback real y específico sobre mi código (ejercicio de punteros en C).

### Sesión 5 — 23 de agosto de 2026
- **Bloqueo o tarea:** quería que la herramienta también sirviera para **aprender** los fundamentos, no solo para pasar el quiz — con explicaciones fáciles de entender para cualquier persona sin conocimiento previo.
- **Prompt principal (resumen):** "quiero usar la herramienta también para aprender las bases... que la explicación sea fácil de entender para todo tipo de edades".
- **Qué generó/resolvió la IA:** una lección completa por cada uno de los 32 niveles (explicación con analogía + ejemplo resuelto aparte del ejercicio), y un botón que le pide a la IA re-explicar el concepto de forma distinta si no se entendió.
- **Qué modifiqué yo:** pedí que la explicación fuera aún más simple (frase corta al inicio de cada lección, tipo resumen), y renombré el botón de pista a "Pista paso a paso".

### Sesión 6 — 23 de agosto de 2026
- **Bloqueo o tarea:** el "paso a paso" debía mostrar la solución real del ejercicio (no un ejemplo aparte), explicando cada símbolo de sintaxis (`&`, comillas, `;`, `return`) para poder detectar errores pequeños de sintaxis por cuenta propia.
- **Prompt principal (resumen):** "quiero que en el paso a paso pueda ver literalmente cómo resolverlo... con todo detallado, un punto, una coma, un &".
- **Qué generó/resolvió la IA:** un bloque de solución completa y detallada por cada uno de los 32 niveles, verificado ejecutando el código real contra los tests (no solo revisado a ojo).
- **Qué modifiqué yo:** ninguna, revisé y aprobé el resultado en la interfaz.

### Sesión 7 — 23 de agosto de 2026
- **Bloqueo o tarea:** configurar Git y GitHub desde cero (sin experiencia previa en la terminal de Linux) para poder entregarle el proyecto al docente.
- **Prompt principal (resumen):** guía completa paso a paso para instalar dependencias, crear el repositorio, autenticarme con un token, y resolver un error de privacidad de email de GitHub.
- **Qué generó/resolvió la IA:** instrucciones exactas por comando, diagnóstico de errores de autenticación y de paths de archivos duplicados.
- **Qué modifiqué yo:** ejecuté cada comando yo mismo, generé mis propias credenciales (API keys y token de GitHub).

---

**Nota para la defensa:** distingue claramente entre:
1. IA usada **para desarrollar** el proyecto (esta tabla) — Claude, usado desde fuera del proyecto, como copiloto de programación.
2. IA usada **dentro** del proyecto en tiempo de ejecución (`llm_judge.py`,
   `exercise_generator.py`) — Groq/Gemini/Anthropic, configurable por el
   usuario final, es el núcleo computacional de la solución. Son conceptos
   distintos y en la defensa suelen confundirse: una es la herramienta que
   usé YO para construir la app; la otra es la IA que la APP misma usa
   para evaluar a cada estudiante.
