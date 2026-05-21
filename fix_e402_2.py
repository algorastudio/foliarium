with open('foliarium/ui/widgets/workflow/operazioni_partita.py', 'r') as f:
    content = f.read()

# Gli E402 sono causati dalla docstring che si trova DOPO "from __future__ import annotations"
content = content.replace('from __future__ import annotations\nfrom foliarium.ui.widgets.genealogia_widget import GenealogiaTimelineWidget\n"""\noperazioni_partita.py', '"""\noperazioni_partita.py')

# Mettiamo gli import SOTTO la docstring.
content = content.replace('"""\nfrom __future__ import annotations\n', '"""\nfrom __future__ import annotations\nfrom foliarium.ui.widgets.genealogia_widget import GenealogiaTimelineWidget\n')

with open('foliarium/ui/widgets/workflow/operazioni_partita.py', 'w') as f:
    f.write(content)
