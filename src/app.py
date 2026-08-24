"""
app.py
------
Interfaz visual (Streamlit) del RPG de Fundamentos de Programacion.
Envuelve el mismo motor de src/*.py (sandbox, llm_judge, mastery,
recommender, exercise_generator) en un mapa de niveles jugable.

Ejecutar con:
    streamlit run src/app.py
"""

import os
import sys
import json
import glob

import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

from mastery import StudentModel
from sandbox import run_level
from llm_judge import judge_submission, reexplain_concept, generate_hint
from recommender import decide_next_action, pick_next_level
from exercise_generator import generate_remedial_exercise

CONTENT_DIR = os.path.join(os.path.dirname(__file__), "..", "content")
SAVE_DIR = os.path.join(os.path.dirname(__file__), "..", "saves")

st.set_page_config(page_title="RPG de Fundamentos de Programacion", page_icon="🎮", layout="wide")

STATE_COLORS = {"completed": "#1D9E75", "current": "#378ADD", "locked": "#888780"}
STATE_ICONS = {"completed": "✅", "current": "▶", "locked": "🔒"}


# --------------------------------------------------------------------------
# Utilidades de carga
# --------------------------------------------------------------------------

@st.cache_data
def list_languages():
    langs = []
    for path in sorted(glob.glob(os.path.join(CONTENT_DIR, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        langs.append((data["language"], data["display_name"]))
    return langs


@st.cache_data
def load_content(language: str) -> dict:
    with open(os.path.join(CONTENT_DIR, f"{language}.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def get_student_model(student: str, language: str) -> StudentModel:
    key = f"model_{student}_{language}"
    if key not in st.session_state:
        save_path = os.path.join(SAVE_DIR, f"{student}_{language}.json")
        st.session_state[key] = StudentModel.load(save_path, language=language)
    return st.session_state[key]


def save_student_model(student: str, language: str, model: StudentModel):
    save_path = os.path.join(SAVE_DIR, f"{student}_{language}.json")
    model.save(save_path)


# --------------------------------------------------------------------------
# Sidebar: identidad del estudiante + configuracion de IA
# --------------------------------------------------------------------------

st.sidebar.title("🎮 Tutor Adaptativo")
student = st.sidebar.text_input("Tu nombre / usuario", value="default")

languages = list_languages()
lang_labels = {code: name for code, name in languages}
selected_lang = st.sidebar.selectbox(
    "Mundo (lenguaje)", options=[c for c, _ in languages], format_func=lambda c: lang_labels[c]
)

st.sidebar.markdown("---")
st.sidebar.subheader("Configuración de IA")
provider = st.sidebar.selectbox("Proveedor del LLM", ["groq", "anthropic", "gemini"])

KEY_LABELS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
}
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-5",
    "gemini": "gemini-3.6-flash",
    "groq": "openai/gpt-oss-120b",
}

api_key = st.sidebar.text_input(
    KEY_LABELS[provider],
    type="password",
    help="Sin esto, el sistema funciona en modo fallback (solo revisa si pasaron los tests, sin analisis conceptual real).",
)
model_name = st.sidebar.text_input("Modelo", value=DEFAULT_MODELS[provider])

os.environ["LLM_PROVIDER"] = provider
if api_key:
    if provider == "anthropic":
        os.environ["ANTHROPIC_API_KEY"] = api_key
        os.environ["ANTHROPIC_MODEL"] = model_name
    elif provider == "gemini":
        os.environ["GOOGLE_API_KEY"] = api_key
        os.environ["GEMINI_MODEL"] = model_name
    else:
        os.environ["GROQ_API_KEY"] = api_key
        os.environ["GROQ_MODEL"] = model_name

if not api_key:
    st.sidebar.warning("Sin API key: el juicio de IA cae a modo fallback (solo tests, sin analisis conceptual real).")

# --------------------------------------------------------------------------
# Cargar contenido y modelo del estudiante
# --------------------------------------------------------------------------

content = load_content(selected_lang)
levels = content["levels"]
model = get_student_model(student, selected_lang)

st.sidebar.markdown("---")
st.sidebar.subheader("Perfil de dominio")
concepts_seen = sorted({lv["concept"] for lv in levels if lv["id"] in model.completed_ids})
if concepts_seen:
    for c in concepts_seen:
        st.sidebar.progress(model.get_mastery(c), text=f"{c} — {model.get_mastery(c):.0%}")
else:
    st.sidebar.caption("Aun no hay progreso registrado en este mundo.")

# --------------------------------------------------------------------------
# Mapa de niveles
# --------------------------------------------------------------------------

st.title(f"Mundo: {content['display_name']}")

next_level = pick_next_level(levels, model, set(model.completed_ids))
next_level_id = next_level["id"] if next_level and not next_level.get("reinforcement") else None

if "selected_level_id" not in st.session_state:
    st.session_state["selected_level_id"] = next_level_id or (levels[0]["id"] if levels else None)

cols = st.columns(len(levels))
for i, lv in enumerate(levels):
    if lv["id"] in model.completed_ids:
        state = "completed"
    elif lv["id"] == next_level_id:
        state = "current"
    else:
        state = "locked"
    with cols[i]:
        label = f"{STATE_ICONS[state]} N{i+1}"
        if st.button(label, key=f"btn_{lv['id']}", help=lv["title"], disabled=(state == "locked")):
            st.session_state["selected_level_id"] = lv["id"]
        st.caption(f"{model.get_mastery(lv['concept']):.0%}")

st.markdown("---")

# --------------------------------------------------------------------------
# Detalle del nivel seleccionado
# --------------------------------------------------------------------------

selected_level = next((lv for lv in levels if lv["id"] == st.session_state["selected_level_id"]), None)

if selected_level is None:
    st.success("🏆 ¡Has completado todos los niveles de este mundo!")
else:
    is_current = selected_level["id"] == next_level_id
    st.header(selected_level["title"])
    st.markdown(f"**Teoría:** {selected_level['theory']}")

    lesson = selected_level.get("lesson")
    if lesson:
        with st.expander("📖 Lección completa (explicado desde cero, sin conocimientos previos)"):
            st.markdown(lesson["explicacion_simple"])
            st.markdown("---")
            st.markdown(f"**Ejemplo resuelto:** {lesson['ejemplo_resuelto']['descripcion']}")
            code_lang = "sql" if selected_lang == "sql" else selected_lang
            st.code(lesson["ejemplo_resuelto"]["codigo"], language=code_lang)
            st.markdown(lesson["ejemplo_resuelto"]["explicacion_paso_a_paso"])

        reexplain_key = f"reexplain_{selected_level['id']}"
        if st.button("🤔 No entendí, explícamelo diferente", key=f"btn_reexplain_{selected_level['id']}"):
            with st.spinner("Pensando en otra forma de explicarlo..."):
                st.session_state[reexplain_key] = reexplain_concept(
                    selected_lang, selected_level["concept"], lesson["explicacion_simple"]
                )
        if reexplain_key in st.session_state:
            r = st.session_state[reexplain_key]
            st.info(r["texto"])
            if r.get("_source") == "fallback":
                st.caption("(No se pudo consultar la IA en este momento, ver mensaje arriba)")

    st.info(selected_level["exercise"]["prompt"])

    hint_key = f"hint_{selected_level['id']}"
    if st.button("💡 Pista paso a paso", key=f"btn_hint_{selected_level['id']}"):
        with st.spinner("Pensando en una pista..."):
            st.session_state[hint_key] = generate_hint(selected_level, selected_lang)
    if hint_key in st.session_state:
        st.warning(st.session_state[hint_key]["texto"])

    solucion = selected_level.get("solucion_paso_a_paso")
    if solucion:
        with st.expander("🔓 Ver solución paso a paso (revela la respuesta completa)"):
            st.caption("Ábrelo solo si ya lo intentaste y sigues atascado, o para revisar tu código línea por línea buscando un detalle pequeño (un `;`, un `&`, una comilla...).")
            code_lang_sol = "sql" if selected_lang == "sql" else selected_lang
            st.code(solucion["codigo"], language=code_lang_sol)
            st.markdown(solucion["explicacion"])

    if selected_lang == "sql":
        with st.expander("Ver esquema de la base de datos"):
            st.code(content["schema"], language="sql")

    if not is_current:
        st.caption("Este nivel ya fue completado. Puedes revisarlo pero no reenviarlo.")

    default_code = selected_level["exercise"]["starter_code"]
    code_key = f"code_{selected_level['id']}"
    if code_key not in st.session_state:
        st.session_state[code_key] = default_code
    student_code = st.text_area("Tu solución", height=220, key=code_key)

    result_key = f"last_result_{selected_level['id']}"

    if is_current and st.button("Enviar solución", type="primary"):
        with st.spinner("Ejecutando tests y consultando IA..."):
            schema = content.get("schema") if selected_lang == "sql" else None
            test_result = run_level(selected_lang, selected_level, student_code, schema)
            judgment = judge_submission(selected_level, student_code, test_result)

            for concept, score in judgment.get("concept_scores", {}).items():
                model.update(concept, correct=test_result.get("passed", False), partial_credit=score)

            decision = decide_next_action(
                model, selected_level, judgment.get("concept_scores", {}), test_result.get("passed", False)
            )

            if decision["action"] in ("advance", "advance_with_reinforcement"):
                if selected_level["id"] not in model.completed_ids:
                    model.completed_ids.append(selected_level["id"])

            save_student_model(student, selected_lang, model)

            remedial = None
            if decision["action"] == "remedial":
                remedial = generate_remedial_exercise(
                    selected_lang, decision["target_concept"], judgment.get("detected_issues", [])
                )

        # Se guarda en session_state (no se muestra directo) porque el
        # st.rerun() de abajo reinicia el script: cualquier st.success/
        # st.error escrito aqui se perderia antes de que el usuario lo vea.
        st.session_state[result_key] = {
            "test_result": test_result,
            "judgment": judgment,
            "decision": decision,
            "remedial": remedial,
        }
        st.rerun()

    if result_key in st.session_state:
        r = st.session_state[result_key]
        test_result, judgment, decision, remedial = r["test_result"], r["judgment"], r["decision"], r["remedial"]

        if test_result.get("passed"):
            st.success(f"✅ Tests superados (score: {test_result.get('score', 0):.0%})")
        else:
            st.error(f"❌ Tests no superados (score: {test_result.get('score', 0):.0%})")
            if test_result.get("error"):
                st.code(test_result["error"])

        st.markdown(f"**Retroalimentación de IA** _(fuente: {judgment.get('_source')})_")
        st.write(judgment.get("feedback", ""))
        for issue in judgment.get("detected_issues", []):
            st.markdown(f"- {issue}")
        if judgment.get("_source") == "fallback" and judgment.get("_error"):
            with st.expander("Detalle técnico del error (para depuración)"):
                st.code(judgment["_error"])

        st.markdown(f"**Decisión del sistema:** `{decision['action']}`")
        st.caption(decision["reason"])

        if remedial:
            st.warning("Ejercicio remedial generado por IA:")
            st.write(remedial["prompt"])
            st.caption(f"Pista: {remedial.get('hint')}")
