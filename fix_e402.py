import re

with open('foliarium/ui/widgets/workflow/operazioni_partita.py', 'r') as f:
    content = f.read()

content = content.replace("from foliarium.ui.widgets.genealogia_widget import GenealogiaTimelineWidget\n", "")

# Inseriamo l'import dopo "from __future__ import annotations"
content = content.replace("from __future__ import annotations", "from __future__ import annotations\nfrom foliarium.ui.widgets.genealogia_widget import GenealogiaTimelineWidget")

with open('foliarium/ui/widgets/workflow/operazioni_partita.py', 'w') as f:
    f.write(content)
