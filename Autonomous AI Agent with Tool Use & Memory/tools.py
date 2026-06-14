"""
tools.py
--------
All the tools the agent can call. Each function is decorated with @tool, which
turns it into a LangChain tool the LLM can invoke by name. The LLM reads the
docstring to decide WHEN to use each tool, so keep docstrings clear.

Most tools need no API keys, so the project runs out of the box (only the LLM
itself needs an OpenAI key).
"""

import datetime
import io
import contextlib
import math

import requests
from langchain_core.tools import tool


# 1. Web search (no API key needed — uses DuckDuckGo)
@tool
def web_search(query: str) -> str:
    """Search the web for current or recent information (news, facts, prices, people).
    Use this whenever the answer might be newer than your training data."""
    try:
        from ddgs import DDGS
    except ImportError:  # older package name
        from duckduckgo_search import DDGS
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
    except Exception as e:
        return f"Search error: {e}"
    if not results:
        return "No results found."
    return "\n\n".join(
        f"{r.get('title','')}\n{r.get('body','')}\n{r.get('href','')}" for r in results
    )


# 2. Wikipedia summary
@tool
def wikipedia_summary(topic: str) -> str:
    """Get a short encyclopedic summary of a topic from Wikipedia."""
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "ai-agent/1.0"})
        resp.raise_for_status()
        return resp.json().get("extract", "No summary found.")
    except Exception as e:
        return f"Error: {e}"


# 3. Fetch the text of any web page
@tool
def fetch_url(url: str) -> str:
    """Fetch the raw text content of a web page given its full URL."""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        return resp.text[:3000]
    except Exception as e:
        return f"Error: {e}"


# 4. Calculator (safe eval, math functions only)
@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression, e.g. '2 * (3 + 4)', 'sqrt(144)', 'sin(pi/2)'."""
    allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
    allowed.update({"abs": abs, "round": round, "min": min, "max": max, "pow": pow})
    try:
        return str(eval(expression, {"__builtins__": {}}, allowed))
    except Exception as e:
        return f"Error: {e}"


# 5. Python code execution
@tool
def python_repl(code: str) -> str:
    """Execute Python code and return whatever it prints. Useful for data work,
    string processing, or multi-step calculations. (Local/demo use only — this
    runs code on the host machine.)"""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(code, {"__builtins__": __builtins__})
        out = buf.getvalue()
        return out if out.strip() else "Code ran successfully (no output)."
    except Exception as e:
        return f"Error: {e}"


# 6. Current date/time
@tool
def current_datetime() -> str:
    """Return the current local date and time."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 7. Word/character count
@tool
def word_count(text: str) -> str:
    """Count the number of words and characters in a piece of text."""
    return f"Words: {len(text.split())}, Characters: {len(text)}"


# 8. Read a local file
@tool
def read_file(path: str) -> str:
    """Read the contents of a local text file at the given path."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()[:5000]
    except Exception as e:
        return f"Error: {e}"


# 9. Write a local file
@tool
def write_file(path: str, content: str) -> str:
    """Write the given text content to a local file at the given path."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote {len(content)} characters to {path}."
    except Exception as e:
        return f"Error: {e}"


# 10. Unit conversion
@tool
def unit_convert(value: float, from_unit: str, to_unit: str) -> str:
    """Convert between simple units: km<->miles, kg<->lb, c<->f (celsius/fahrenheit)."""
    try:
        v = float(value)
    except Exception:
        return "Value must be a number."
    conversions = {
        ("km", "miles"): v * 0.621371,
        ("miles", "km"): v / 0.621371,
        ("kg", "lb"): v * 2.20462,
        ("lb", "kg"): v / 2.20462,
        ("c", "f"): v * 9 / 5 + 32,
        ("f", "c"): (v - 32) * 5 / 9,
    }
    key = (from_unit.lower(), to_unit.lower())
    if key in conversions:
        return f"{value} {from_unit} = {conversions[key]:.4f} {to_unit}"
    return "Unsupported conversion. Try km/miles, kg/lb, or c/f."


# The full toolbox the agent gets access to.
ALL_TOOLS = [
    web_search,
    wikipedia_summary,
    fetch_url,
    calculator,
    python_repl,
    current_datetime,
    word_count,
    read_file,
    write_file,
    unit_convert,
]
