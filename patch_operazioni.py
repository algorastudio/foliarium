import re

with open('foliarium/ui/widgets/workflow/operazioni_partita.py', 'r') as f:
    content = f.read()

# 1. Aggiungi l'importazione
import_stmt = "from foliarium.ui.widgets.genealogia_widget import GenealogiaTimelineWidget\n"
if "GenealogiaTimelineWidget" not in content:
    content = import_stmt + content

# 2. Aggiungi la chiamata per creare la tab genealogia in setup_ui (dopo _crea_tab_passaggio_proprieta)
setup_tab_pattern = r'self\._crea_tab_passaggio_proprieta\(\)\s+self\.setLayout\(main_layout\)'
replacement = """self._crea_tab_passaggio_proprieta()
        self._crea_tab_genealogia()

        self.setLayout(main_layout)"""
content = re.sub(setup_tab_pattern, replacement, content)

# 3. Definisci il nuovo metodo _crea_tab_genealogia()
new_method = """
    def _crea_tab_genealogia(self):
        self.genealogia_widget = GenealogiaTimelineWidget(self.db)
        # Quando un nodo è cliccato, si potrebbe cambiare partita.
        # Per semplicità lo connettiamo a una slot che ricarica se stessa (opzionale)
        self.genealogia_widget.navigate_to_partita.connect(self.carica_partita)
        self.operazioni_tabs.addTab(self.genealogia_widget, "Timeline e Genealogia")
"""

if "_crea_tab_genealogia" not in content:
    content += new_method

# 4. Assicurati che quando carica_partita è chiamato, il widget della genealogia venga aggiornato
carica_partita_pattern = r'(def carica_partita\(self, partita_id: int\):.*?self\.partita_selezionata = partita_dettagli)'

def inject_load(match):
    return match.group(1) + "\n        if hasattr(self, 'genealogia_widget'):\n            self.genealogia_widget.load_partita(partita_id)"

content = re.sub(carica_partita_pattern, inject_load, content, flags=re.DOTALL)


with open('foliarium/ui/widgets/workflow/operazioni_partita.py', 'w') as f:
    f.write(content)

print("Patching widget workflow done.")
