# Tutor Adaptativo de Fundamentos de Programación

Proyecto para el Summer Camp 2026 de CyberMinds EPN — "Fundamentos de
Inteligencia Artificial".

Un RPG de aprendizaje de programación donde un LLM analiza tu código para
detectar qué conceptos dominas de verdad (no solo si "pasó" el test), un
modelo probabilístico (Bayesian Knowledge Tracing) rastrea tu dominio por
concepto, y el sistema decide y genera automáticamente tu siguiente paso.

4 mundos, 8 niveles cada uno: **Python, C, Java y SQL** (cuatro paradigmas
distintos: dinámico, manejo manual de memoria, orientado a objetos, y
declarativo).

## Estructura

```
proyecto_ia/
├── docs/
│   ├── Documentacion_Tecnica.md   <- documento principal para entrega
│   └── registro_prompts.md        <- llena esto mientras desarrollas
├── content/
│   ├── python.json   <- 8 niveles: variables -> decoradores
│   ├── c.json         <- 8 niveles: variables -> listas enlazadas
│   ├── java.json      <- 8 niveles: variables -> excepciones
│   └── sql.json        <- 8 niveles: SELECT -> CTEs
├── src/
│   ├── mastery.py             <- modelo BKT (el "cerebro" probabilístico)
│   ├── sandbox.py             <- ejecuta y verifica cada lenguaje (4 estrategias distintas)
│   ├── llm_judge.py           <- NÚCLEO DE IA: clasifica dominio conceptual
│   ├── exercise_generator.py  <- genera ejercicios remediales con IA
│   ├── recommender.py         <- decide la siguiente acción
│   ├── app.py                  <- interfaz PRINCIPAL (Streamlit, tipo videojuego)
│   └── game.py                  <- interfaz de consola alternativa
└── requirements.txt
```

## Quickstart

```bash
pip install -r requirements.txt --break-system-packages
streamlit run src/app.py
```

Configura tu API key (Groq, Anthropic o Google AI Studio) desde la barra
lateral de la app. Sin ella, el motor sigue funcionando en modo
*fallback* (basado solo en resultado de tests) para que siempre sea
demostrable — ver `src/llm_judge.py`.

## Empieza aquí

Lee `docs/Documentacion_Tecnica.md` — tiene la definición del problema,
la arquitectura completa, qué está verificado con ejecución real (Python,
C, SQL) y qué falta verificar en tu máquina (Java, requiere JDK completo),
y el mapeo directo a cada criterio de la rúbrica del Summer Camp.
