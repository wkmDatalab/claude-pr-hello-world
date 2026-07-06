"""Optional human-applied fix script.

This is not run by the agent. It exists so you can simulate the human accepting
the proposed PR patch after reviewing reports/PR_PROPOSAL.md.
"""

from pathlib import Path

path = Path("src/hello_world.py")
text = path.read_text(encoding="utf-8")
text = text.replace('return "H world"', 'return "Hello world"')
text = text.replace("printf(greeting())", "print(greeting())")
path.write_text(text, encoding="utf-8")
print("Applied suggested fix to src/hello_world.py")
