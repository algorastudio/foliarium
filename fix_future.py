import re

with open('foliarium/ui/widgets/workflow/operazioni_partita.py', 'r') as f:
    content = f.read()

# Rimuovo qualsiasi "from __future__ import annotations"
content = re.sub(r'^from __future__ import annotations\n', '', content, flags=re.MULTILINE)

# Lo metto all'inizio
content = "from __future__ import annotations\n" + content

with open('foliarium/ui/widgets/workflow/operazioni_partita.py', 'w') as f:
    f.write(content)
