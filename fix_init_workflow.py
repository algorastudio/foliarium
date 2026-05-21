with open('foliarium/ui/widgets/workflow/__init__.py', 'r') as f:
    content = f.read()

# Trovo l'export esistente e aggiungo GenealogiaTimelineWidget
if "GenealogiaTimelineWidget" not in content:
    content = content.replace(
        "from .operazioni_partita import OperazioniPartitaWidget",
        "from .operazioni_partita import OperazioniPartitaWidget\nfrom .genealogia_widget import GenealogiaTimelineWidget"
    )
    content = content.replace(
        "'OperazioniPartitaWidget',",
        "'OperazioniPartitaWidget',\n    'GenealogiaTimelineWidget',"
    )
    with open('foliarium/ui/widgets/workflow/__init__.py', 'w') as f:
        f.write(content)
