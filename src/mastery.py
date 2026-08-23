"""
mastery.py
----------
Modelo probabilistico de dominio del estudiante por concepto, basado en
Bayesian Knowledge Tracing (BKT). Este es el "cerebro" que decide que tan
bien domina el estudiante cada concepto (variables, recursion, punteros, etc.)
a partir de observaciones (correcto/incorrecto) generadas por el juez de IA.

BKT es un Modelo Oculto de Markov de 2 estados (dominado / no dominado) con
4 parametros por concepto:
    p_init  -> probabilidad de dominar el concepto antes de practicar
    p_transit -> probabilidad de "aprender" el concepto tras un intento
    p_slip  -> probabilidad de fallar aun dominando el concepto (error tonto)
    p_guess -> probabilidad de acertar sin dominar el concepto (adivinar)

No se usan valores fijos tipo if/else: cada observacion actualiza una
probabilidad continua mediante la regla de Bayes.
"""

from dataclasses import dataclass, field
import json
import os


@dataclass
class ConceptParams:
    p_init: float = 0.30
    p_transit: float = 0.20
    p_slip: float = 0.10
    p_guess: float = 0.15


@dataclass
class StudentModel:
    """Perfil de dominio de un estudiante para un lenguaje especifico."""
    language: str
    mastery: dict = field(default_factory=dict)   # concepto -> P(dominado)
    params: dict = field(default_factory=dict)    # concepto -> ConceptParams
    history: list = field(default_factory=list)   # log de observaciones
    completed_ids: list = field(default_factory=list)  # ids de niveles completados

    def _get_params(self, concept: str) -> ConceptParams:
        if concept not in self.params:
            self.params[concept] = ConceptParams()
        return self.params[concept]

    def get_mastery(self, concept: str) -> float:
        return self.mastery.get(concept, self._get_params(concept).p_init)

    def update(self, concept: str, correct: bool, partial_credit: float = None):
        """
        Actualiza P(dominado) para un concepto tras una observacion.

        partial_credit: opcional, valor 0-1 entregado por el juez de IA
        cuando la evaluacion no es binaria (ej: "entendio recursion pero
        con un error de caso base"). Se interpreta como una mezcla
        probabilistica entre la actualizacion "correcta" e "incorrecta".
        """
        p = self._get_params(concept)
        p_prev = self.get_mastery(concept)

        # Paso 1: actualizacion bayesiana segun la observacion (evidencia)
        if correct:
            p_obs = (p_prev * (1 - p.p_slip)) / (
                p_prev * (1 - p.p_slip) + (1 - p_prev) * p.p_guess + 1e-9
            )
        else:
            p_obs = (p_prev * p.p_slip) / (
                p_prev * p.p_slip + (1 - p_prev) * (1 - p.p_guess) + 1e-9
            )

        if partial_credit is not None:
            # mezcla entre update "correcto" y "incorrecto" ponderada por el
            # credito parcial que dio el LLM (ej: 0.6 = 60% de acierto conceptual)
            p_correct_branch = (p_prev * (1 - p.p_slip)) / (
                p_prev * (1 - p.p_slip) + (1 - p_prev) * p.p_guess + 1e-9
            )
            p_incorrect_branch = (p_prev * p.p_slip) / (
                p_prev * p.p_slip + (1 - p_prev) * (1 - p.p_guess) + 1e-9
            )
            p_obs = partial_credit * p_correct_branch + (1 - partial_credit) * p_incorrect_branch

        # Paso 2: probabilidad de transicion (aprendizaje) hacia el siguiente intento
        p_next = p_obs + (1 - p_obs) * p.p_transit
        p_next = min(max(p_next, 0.01), 0.99)  # evitar certezas absolutas (0 o 1)

        self.mastery[concept] = p_next
        self.history.append({
            "concept": concept,
            "correct": correct,
            "partial_credit": partial_credit,
            "p_before": p_prev,
            "p_after": p_next,
        })
        return p_next

    def is_mastered(self, concept: str, threshold: float = 0.85) -> bool:
        return self.get_mastery(concept) >= threshold

    def weakest_concept(self, concepts: list) -> str:
        """Retorna el concepto con menor probabilidad de dominio."""
        return min(concepts, key=lambda c: self.get_mastery(c))

    def to_dict(self):
        return {
            "language": self.language,
            "mastery": self.mastery,
            "history": self.history,
            "completed_ids": self.completed_ids,
        }

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str, language: str):
        if not os.path.exists(path):
            return cls(language=language)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        model = cls(language=language, mastery=data.get("mastery", {}))
        model.history = data.get("history", [])
        model.completed_ids = data.get("completed_ids", [])
        return model
