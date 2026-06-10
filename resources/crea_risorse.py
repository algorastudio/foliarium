from PIL import Image, ImageDraw, ImageFont
import os

# Crea directory se non esiste
os.makedirs('resources', exist_ok=True)

# Colori
DARK_BLUE = (30, 58, 95)
MEDIUM_BLUE = (46, 90, 143)
WHITE = (255, 255, 255)
LIGHT_GRAY = (200, 200, 200)

# Banner (164x314)
banner = Image.new('RGB', (164, 314), DARK_BLUE)
draw_banner = ImageDraw.Draw(banner)

# Gradiente semplice per il banner
for y in range(314):
    r = int(DARK_BLUE[0] + (MEDIUM_BLUE[0] - DARK_BLUE[0]) * y / 314)
    g = int(DARK_BLUE[1] + (MEDIUM_BLUE[1] - DARK_BLUE[1]) * y / 314)
    b = int(DARK_BLUE[2] + (MEDIUM_BLUE[2] - DARK_BLUE[2]) * y / 314)
    draw_banner.rectangle([(0, y), (164, y+1)], fill=(r, g, b))

# Testo principale
try:
    # Prova a usare un font di sistema
    font_title = ImageFont.truetype("arial.ttf", 24)
    font_subtitle = ImageFont.truetype("arial.ttf", 14)
    font_small = ImageFont.truetype("arial.ttf", 10)
except (OSError, IOError):
    # Usa font default se non disponibile (file font non trovato)
    font_title = ImageFont.load_default()
    font_subtitle = ImageFont.load_default()
    font_small = ImageFont.load_default()

# Aggiungi testi
draw_banner.text((82, 50), "FOLIARIUM", font=font_title, fill=WHITE, anchor="mm")
draw_banner.text((82, 80), "1.3", font=font_title, fill=WHITE, anchor="mm")
draw_banner.text((82, 120), "Gestionale", font=font_subtitle, fill=WHITE, anchor="mm")
draw_banner.text((82, 140), "Catasto Storico", font=font_subtitle, fill=WHITE, anchor="mm")

# Copyright
draw_banner.text((82, 250), "© 2025 Marco Santoro", font=font_small, fill=LIGHT_GRAY, anchor="mm")
draw_banner.text((82, 265), "Concesso in comodato d'uso", font=font_small, fill=LIGHT_GRAY, anchor="mm")
draw_banner.text((82, 280), "all'Archivio di Stato", font=font_small, fill=LIGHT_GRAY, anchor="mm")
draw_banner.text((82, 295), "di Savona", font=font_small, fill=LIGHT_GRAY, anchor="mm")

# Salva banner
banner.save('resources/installer_banner.bmp', 'BMP')

# Icon (55x58)
icon = Image.new('RGB', (55, 58), DARK_BLUE)
draw_icon = ImageDraw.Draw(icon)

# Bordo
draw_icon.rectangle([(0, 0), (54, 57)], outline=WHITE, width=2)

# Lettera M stilizzata
draw_icon.text((27, 29), "M", font=font_title, fill=WHITE, anchor="mm")

# Salva icon
icon.save('resources/installer_icon.bmp', 'BMP')

print("File BMP creati con successo in resources/")