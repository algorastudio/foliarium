import re

with open('foliarium/ui/widgets/workflow/operazioni_partita.py', 'r') as f:
    content = f.read()

# Controllo che le classi necessarie siano importate
if "from foliarium.ui.widgets.genealogia_widget import GenealogiaTimelineWidget" not in content:
    content = "from foliarium.ui.widgets.genealogia_widget import GenealogiaTimelineWidget\n" + content

with open('foliarium/ui/widgets/workflow/operazioni_partita.py', 'w') as f:
    f.write(content)
