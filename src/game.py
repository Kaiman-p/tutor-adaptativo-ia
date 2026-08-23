"""
game.py
-------
Interfaz de consola del "RPG de Fundamentos de Programacion" (alternativa
ligera a app.py/Streamlit). Recorre el ciclo completo:

    mostrar nivel -> estudiante escribe/pega codigo -> sandbox valida
    -> LLM juzga dominio conceptual -> BKT actualiza mastery
    -> recomendador decide siguiente paso -> repetir

Uso:
    python game.py --lang python
    python game.py --lang c
    python game.py --lang java
    python game.py --lang sql

Requiere una API key configurada (ANTHROPIC_API_KEY o GOOGLE_API_KEY) para
el analisis conceptual real. Sin ella, cae a un fallback basado solo en
tests (ver llm_judge.py) para que el motor siga siendo demostrable.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from mastery import StudentModel
from sandbox import run_level
from llm_judge import judge_submission
from recommender import decide_next_action, pick_next_level
from exercise_generator import generate_remedial_exercise

CONTENT_DIR = os.path.join(os.path.dirname(__file__), "..", "content")
SAVE_DIR = os.path.join(os.path.dirname(__file__), "..", "saves")


def load_content(language: str) -> dict:
    path = os.path.join(CONTENT_DIR, f"{language}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def print_header(text: str):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def print_mastery_bar(student_model: StudentModel, concepts: list):
    print("\n--- Perfil de Dominio ---")
    for c in concepts:
        p = student_model.get_mastery(c)
        filled = int(p * 20)
        bar = "#" * filled + "-" * (20 - filled)
        print(f"  {c:28s} [{bar}] {p:5.1%}")


def get_student_code(prompt_label: str) -> str:
    print(f"\n{prompt_label}")
    print("(Pega tu codigo/consulta. Termina con una linea que contenga solo 'FIN')")
    lines = []
    while True:
        line = input()
        if line.strip() == "FIN":
            break
        lines.append(line)
    return "\n".join(lines)


def play_level(language: str, level: dict, student_model: StudentModel, schema: str = None):
    print_header(level["title"])
    print(f"\n[Teoria]\n{level['theory']}")
    if language == "sql" and schema:
        print(f"\n[Esquema de la base de datos]\n{schema}")
    print(f"\n[Mision] {level['exercise']['prompt']}")
    print(f"\n[Codigo base]\n{level['exercise']['starter_code']}")

    student_code = get_student_code("Escribe tu solucion completa:")

    test_result = run_level(language, level, student_code, schema)

    if "error" in test_result and not test_result.get("results"):
        print(f"\n[!] Error al ejecutar: {test_result['error']}")

    print(f"\n[Resultado de tests] {'PASO' if test_result.get('passed') else 'NO PASO'} "
          f"(score: {test_result.get('score', 0):.0%})")

    judgment = judge_submission(level, student_code, test_result)
    print(f"\n[Analisis de IA - fuente: {judgment.get('_source')}]")
    print(f"  Feedback: {judgment.get('feedback')}")
    for issue in judgment.get("detected_issues", []):
        print(f"  - Detectado: {issue}")

    for concept, score in judgment.get("concept_scores", {}).items():
        student_model.update(concept, correct=test_result.get("passed", False), partial_credit=score)

    decision = decide_next_action(student_model, level, judgment.get("concept_scores", {}), test_result.get("passed", False))
    print(f"\n[Decision del sistema] {decision['action'].upper()}")
    print(f"  {decision['reason']}")

    if decision["action"] == "remedial":
        remedial = generate_remedial_exercise(language, decision["target_concept"], judgment.get("detected_issues", []))
        print(f"\n[Ejercicio remedial generado por IA - fuente: {remedial.get('_source')}]")
        print(f"  {remedial['prompt']}")
        print(f"  Pista: {remedial.get('hint')}")

    return decision


def main():
    parser = argparse.ArgumentParser(description="RPG de Fundamentos de Programacion (consola)")
    parser.add_argument("--lang", required=True, choices=["python", "c", "java", "sql"])
    parser.add_argument("--student", default="default")
    args = parser.parse_args()

    content = load_content(args.lang)
    schema = content.get("schema")  # solo presente/usado para SQL
    save_path = os.path.join(SAVE_DIR, f"{args.student}_{args.lang}.json")
    student_model = StudentModel.load(save_path, language=args.lang)

    completed = set(student_model.completed_ids)
    concepts = [lv["concept"] for lv in content["levels"]]

    print_header(f"Mundo: {content['display_name']}")
    print("Bienvenido/a al RPG de Fundamentos de Programacion.")
    print("(Para la experiencia visual completa tipo videojuego, usa: streamlit run src/app.py)")

    while True:
        next_level = pick_next_level(content["levels"], student_model, completed)
        if next_level is None:
            print_header("Has completado todos los niveles de este mundo. GG!")
            break
        if next_level.get("reinforcement"):
            print_header(f"Refuerzo obligatorio: {next_level['concept']}")
            print("Tu dominio de este concepto es bajo. Genera un ejercicio de refuerzo...")
            exercise = generate_remedial_exercise(args.lang, next_level["concept"], [])
            print(f"  {exercise['prompt']}")
            get_student_code("Practica aqui (no se evalua para avanzar, es refuerzo libre):")
            student_model.update(next_level["concept"], correct=True, partial_credit=0.6)
            continue

        decision = play_level(args.lang, next_level, student_model, schema)
        print_mastery_bar(student_model, concepts)

        if decision["action"] in ("advance", "advance_with_reinforcement"):
            completed.add(next_level["id"])
            student_model.completed_ids = list(completed)

        student_model.save(save_path)

        cont = input("\nPresiona ENTER para continuar, o 'q' para salir: ")
        if cont.strip().lower() == "q":
            break

    print(f"\nProgreso guardado en {save_path}")


if __name__ == "__main__":
    main()
