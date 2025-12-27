# main.py - EINFACHE FUNKTIONIERENDE APP
import flet as ft
import subprocess
import sys
import os

print("=== SAFKATY APP STARTET ===")

def main(page: ft.Page):
    print("✓ App-Fenster wird erstellt")
    
    # 1. Einstellungen für die Seite
    page.title = "SAFKATY App"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # 2. SOFORT SICHTBARER TEXT (gegen weißen Bildschirm)
    status = ft.Text(
        "SAFKATY ist bereit!",
        size=24,
        color="green",
        weight="bold"
    )
    page.add(status)
    
    # 3. TITEL
    page.add(ft.Text("SAFKATY", size=36, weight="bold"))
    page.add(ft.Text("Marchés Publics Manager", size=18))
    page.add(ft.Divider())
    
    # 4. RESULTAT-FELD
    result = ft.TextField(
        multiline=True,
        min_lines=8,
        max_lines=15,
        width=500,
        read_only=True,
        border_color="gray",
        filled=True,
        bgcolor="#f5f5f5"
    )
    page.add(result)
    
    # 5. START-BUTTON
    def start_program(e):
        result.value = "➤ Starte SAFKATY...\n"
        page.update()
        
        try:
            # Prüfe ob Datei existiert
            if os.path.exists("safkaty.py"):
                result.value += "✓ Datei gefunden\n"
                page.update()
                
                # Skript ausführen
                process = subprocess.run(
                    [sys.executable, "safkaty.py"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                # Ergebnis anzeigen
                if process.stdout:
                    result.value += f"\n✅ ERFOLG:\n{process.stdout}\n"
                if process.stderr:
                    result.value += f"\n⚠️ HINWEISE:\n{process.stderr}\n"
                
                result.value += f"\n🔚 Programm beendet mit Code: {process.returncode}"
                
            else:
                result.value = "❌ FEHLER: safkaty.py nicht gefunden!\n\n"
                result.value += f"Aktuelle Dateien:\n"
                for file in os.listdir("."):
                    result.value += f"- {file}\n"
                
        except Exception as error:
            result.value = f"❌ FEHLER: {str(error)}"
        
        page.update()
    
    start_button = ft.ElevatedButton(
        "SAFKATY STARTEN",
        icon="play_arrow",
        on_click=start_program,
        width=200,
        height=50,
        style=ft.ButtonStyle(
            bgcolor=ft.colors.BLUE,
            color=ft.colors.WHITE
        )
    )
    
    page.add(start_button)
    page.add(ft.Divider())
    page.add(ft.Text("Klicke oben auf den Button um zu starten", size=14))
    
    print("✓ App ist fertig geladen")

print("=== APP WIRD GESTARTET ===")
ft.app(target=main)
