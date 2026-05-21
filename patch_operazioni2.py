import re

with open('foliarium/ui/widgets/workflow/operazioni_partita.py', 'r') as f:
    content = f.read()

# Trovo l'import di GenealogiaTimelineWidget
pattern = r'from foliarium\.ui\.widgets\.genealogia_widget import GenealogiaTimelineWidget'
if pattern not in content:
    content = 'from foliarium.ui.widgets.genealogia_widget import GenealogiaTimelineWidget\n' + content

with open('foliarium/ui/widgets/workflow/operazioni_partita.py', 'w') as f:
    f.write(content)
