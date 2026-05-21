import re

with open('foliarium/ui/widgets/workflow/operazioni_partita.py', 'r') as f:
    content = f.read()

# Nel file il tipo "CatastoDBManager" in `__init__` si rompe.
# Lo sostituiamo con 'Any' (o non specificarlo), dato che è coperto dal Protocollo.
# Oppure togliamo il type hint nell'init, ma siccome c'è "if TYPE_CHECKING: from catasto_db_manager import CatastoDBManager", a runtime fallisce se il blocco TYPE_CHECKING è ignorato e lo si usa non come stringa.

content = content.replace("def __init__(self, db_manager: CatastoDBManager, parent=None):", "def __init__(self, db_manager: 'CatastoDBManager', parent=None):")

with open('foliarium/ui/widgets/workflow/operazioni_partita.py', 'w') as f:
    f.write(content)
