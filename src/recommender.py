"""
recommender.py
---------------
Toma de decisiones autonoma: dado el estado de mastery del estudiante tras
un intento, decide que pasa despues. No es un simple if/else de "aprobado
o no": pondera la probabilidad de dominio continua (BKT) y decide entre
4 acciones posibles, cumpliendo el resultado 'Toma de Decisiones' ademas
de 'Personalizacion'.
"""

MASTERY_THRESHOLD = 0.85
REMEDIAL_THRESHOLD = 0.45


def decide_next_action(student_model, level: dict, concept_scores: dict, test_passed: bool) -> dict:
    """
    Retorna un dict con:
      action: "advance" | "remedial" | "boss_challenge" | "retry"
      reason: explicacion legible
      target_concept: concepto en el que enfocarse despues
    """
    concept = level["concept"]
    mastery = student_model.get_mastery(concept)

    if not test_passed and mastery < REMEDIAL_THRESHOLD:
        return {
            "action": "remedial",
            "reason": f"Dominio de '{concept}' bajo ({mastery:.0%}). Se genera un ejercicio "
                      f"remedial mas simple enfocado en este concepto antes de continuar.",
            "target_concept": concept,
        }

    if not test_passed:
        return {
            "action": "retry",
            "reason": f"El codigo no paso las pruebas pero el dominio conceptual de "
                      f"'{concept}' es aceptable ({mastery:.0%}). Se sugiere reintentar "
                      f"el mismo nivel con una pista.",
            "target_concept": concept,
        }

    if mastery >= MASTERY_THRESHOLD:
        return {
            "action": "advance",
            "reason": f"Dominio solido de '{concept}' ({mastery:.0%}). Avanza al siguiente nivel.",
            "target_concept": None,
        }

    return {
        "action": "advance_with_reinforcement",
        "reason": f"Nivel superado pero el dominio de '{concept}' aun no es solido "
                  f"({mastery:.0%}). Avanza, pero el concepto reaparecera reforzado "
                  f"en un 'jefe final' mas adelante.",
        "target_concept": concept,
    }


def pick_next_level(levels: list, student_model, completed_ids: set) -> dict:
    """
    Elige el siguiente nivel a mostrar. Prioriza avanzar linealmente por
    dificultad, pero si hay conceptos previos con mastery bajo, inserta
    refuerzo antes de dejar pasar al 'jefe final' (ultimo nivel).
    """
    remaining = [lv for lv in levels if lv["id"] not in completed_ids]
    if not remaining:
        return None

    concepts_seen = [lv["concept"] for lv in levels if lv["id"] in completed_ids]
    if concepts_seen:
        weakest = student_model.weakest_concept(concepts_seen)
        if student_model.get_mastery(weakest) < REMEDIAL_THRESHOLD and remaining[-1]["difficulty"] == 4:
            # No dejar pasar al jefe final con una base debil
            return {
                "id": f"reinforce_{weakest}",
                "title": f"Refuerzo: {weakest}",
                "concept": weakest,
                "difficulty": 1,
                "reinforcement": True,
            }

    return remaining[0]
