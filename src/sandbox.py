"""
sandbox.py
----------
Ejecuta el codigo que el estudiante escribe contra los tests del nivel
para verificar correccion funcional (independiente del analisis conceptual
que hace el LLM). Corre en un subproceso con timeout para evitar loops
infinitos o codigo malicioso.

Cuatro lenguajes, cuatro estrategias distintas (cada una es la forma
natural de probar ese lenguaje, no una adaptacion forzada):

  - Python: se arma un pequeno arnes que evalua una expresion ("call")
    y compara el resultado con el valor esperado (tests: [{call, expected}]).
  - JavaScript: mismo patron que Python, via node.
  - C / Java: no tienen REPL/eval nativo, asi que cada nivel provee un
    'harness_main' (codigo real que llama a la solucion del estudiante y
    imprime resultados) y un 'expected_stdout' exacto para comparar.
  - SQL: no se "ejecuta" como programa, se corre la consulta del
    estudiante sobre una base de datos SQLite en memoria (sembrada con el
    'schema' del nivel) y se compara el resultado como conjunto de filas.

Requisitos del sistema: python3, gcc, node, java+javac deben estar
disponibles en PATH para que los 4 mundos funcionen. Si alguno falta, ese
lenguaje queda inhabilitado (el motor lo detecta y avisa, no truena).
"""

import subprocess
import tempfile
import os
import json
import shutil
import sqlite3

TIMEOUT_SECONDS = 5


def _runner_available(cmd: str) -> bool:
    return shutil.which(cmd) is not None


# --------------------------------------------------------------------------
# PYTHON
# --------------------------------------------------------------------------

def run_python(student_code: str, tests: list) -> dict:
    results = []
    for t in tests:
        harness = f"{student_code}\n\nprint(repr({t['call']}))\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(harness)
            path = f.name
        try:
            proc = subprocess.run(
                ["python3", path], capture_output=True, text=True, timeout=TIMEOUT_SECONDS
            )
            actual = proc.stdout.strip()
            passed = actual == repr(t["expected"]) or _loose_equal(actual, t["expected"])
            results.append({"call": t["call"], "passed": passed, "stderr": proc.stderr.strip()})
        except subprocess.TimeoutExpired:
            results.append({"call": t["call"], "passed": False, "stderr": "timeout"})
        finally:
            os.unlink(path)
    return _summarize(results)


def _loose_equal(actual_str: str, expected) -> bool:
    try:
        return json.loads(actual_str.replace("'", '"')) == expected
    except Exception:
        return False


# --------------------------------------------------------------------------
# JAVASCRIPT
# --------------------------------------------------------------------------

def run_javascript(student_code: str, tests: list) -> dict:
    if not _runner_available("node"):
        return {"passed": False, "error": "node no disponible en el sistema", "results": []}
    results = []
    for t in tests:
        harness = f"{student_code}\n\n(async () => {{ console.log(JSON.stringify(await {t['call']})); }})();\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(harness)
            path = f.name
        try:
            proc = subprocess.run(
                ["node", path], capture_output=True, text=True, timeout=TIMEOUT_SECONDS
            )
            actual = proc.stdout.strip()
            passed = actual == json.dumps(t["expected"])
            results.append({"call": t["call"], "passed": passed, "stderr": proc.stderr.strip()})
        except subprocess.TimeoutExpired:
            results.append({"call": t["call"], "passed": False, "stderr": "timeout"})
        finally:
            os.unlink(path)
    return _summarize(results)


# --------------------------------------------------------------------------
# C
# --------------------------------------------------------------------------

def run_c(student_code: str, harness_main: str, expected_stdout: str) -> dict:
    if not _runner_available("gcc"):
        return {"passed": False, "error": "gcc no disponible en el sistema", "results": []}
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, "sol.c")
        bin_path = os.path.join(tmpdir, "sol.out")
        full_source = (
            "#include <stdio.h>\n#include <stdlib.h>\n#include <math.h>\n\n"
            + student_code + "\n\n"
            + "int main() {\n" + harness_main + "\nreturn 0;\n}\n"
        )
        with open(src_path, "w") as f:
            f.write(full_source)
        compile_proc = subprocess.run(
            ["gcc", src_path, "-o", bin_path, "-lm"], capture_output=True, text=True
        )
        if compile_proc.returncode != 0:
            return {"passed": False, "score": 0.0, "error": compile_proc.stderr, "results": []}
        try:
            run_proc = subprocess.run([bin_path], capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
            actual = run_proc.stdout.strip()
            passed = actual == expected_stdout.strip()
            return {"passed": passed, "score": 1.0 if passed else 0.0, "stdout": actual, "results": []}
        except subprocess.TimeoutExpired:
            return {"passed": False, "score": 0.0, "error": "timeout", "results": []}


# --------------------------------------------------------------------------
# JAVA
# --------------------------------------------------------------------------

def run_java(student_code: str, harness_main: str, expected_stdout: str) -> dict:
    if not _runner_available("javac") or not _runner_available("java"):
        return {
            "passed": False, "score": 0.0,
            "error": "javac/java no disponibles en el sistema (se requiere un JDK completo, no solo JRE)",
            "results": [],
        }
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, "Main.java")
        full_source = (
            "public class Main {\n"
            + student_code + "\n\n"
            + "public static void main(String[] args) {\n" + harness_main + "\n}\n"
            + "}\n"
        )
        with open(src_path, "w") as f:
            f.write(full_source)
        compile_proc = subprocess.run(
            ["javac", src_path], capture_output=True, text=True, cwd=tmpdir
        )
        if compile_proc.returncode != 0:
            return {"passed": False, "score": 0.0, "error": compile_proc.stderr, "results": []}
        try:
            run_proc = subprocess.run(
                ["java", "-cp", tmpdir, "Main"], capture_output=True, text=True, timeout=TIMEOUT_SECONDS
            )
            actual = run_proc.stdout.strip()
            passed = actual == expected_stdout.strip()
            return {"passed": passed, "score": 1.0 if passed else 0.0, "stdout": actual, "results": []}
        except subprocess.TimeoutExpired:
            return {"passed": False, "score": 0.0, "error": "timeout", "results": []}


# --------------------------------------------------------------------------
# SQL
# --------------------------------------------------------------------------

def run_sql(schema: str, student_query: str, expected_result: list, order_matters: bool = False) -> dict:
    """
    Ejecuta la consulta del estudiante sobre una base SQLite en memoria
    sembrada con 'schema'. No requiere ningun runner externo: sqlite3 es
    parte de la libreria estandar de Python.
    """
    try:
        conn = sqlite3.connect(":memory:")
        conn.executescript(schema)
        cursor = conn.execute(student_query)
        rows = cursor.fetchall()
        conn.close()
    except sqlite3.Error as e:
        return {"passed": False, "score": 0.0, "error": str(e), "results": []}

    actual = [list(r) for r in rows]
    expected = [list(r) for r in expected_result]

    if order_matters:
        passed = actual == expected
    else:
        passed = sorted(map(str, actual)) == sorted(map(str, expected))

    return {
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "actual_rows": actual,
        "expected_rows": expected,
        "results": [],
    }


def run_level(language: str, level: dict, student_code: str, schema: str = None) -> dict:
    """
    Despachador unico: dado un nivel (con su estructura de 'exercise') y el
    codigo/consulta del estudiante, llama al runner correcto segun el
    lenguaje. Usado tanto por game.py (consola) como por app.py (Streamlit)
    para no duplicar esta logica en dos lugares.
    """
    ex = level["exercise"]
    if language == "python":
        return run_python(student_code, ex["tests"])
    if language == "javascript":
        return run_javascript(student_code, ex["tests"])
    if language == "c":
        return run_c(student_code, ex["harness_main"], ex["expected_stdout"])
    if language == "java":
        return run_java(student_code, ex["harness_main"], ex["expected_stdout"])
    if language == "sql":
        return run_sql(schema, student_code, ex["expected_result"], ex.get("order_matters", False))
    return {"passed": False, "score": 0.0, "error": f"lenguaje no soportado: {language}"}


def _summarize(results: list) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    return {
        "passed": passed == total and total > 0,
        "score": passed / total if total else 0.0,
        "results": results,
    }
