# main.py - MIT FUNKTIONIERENDEM BUTTON
import flet as ft
import subprocess
import sys
import os

print("=== SAFKATY APP STARTET ===")

def main(page: ft.Page):
    print("✓ App-Fenster wird erstellt")
    
    # 1. Einstellungen
    page.title = "SAFKATY"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    
    # 2. Statusanzeige (oben grün)
    status_text = ft.Text(
        "✅ SAFKATY IST BEREIT",
        size=20,
        color=ft.colors.GREEN,
        weight=ft.FontWeight.BOLD
    )
    
    # 3. Haupt-Container
    result_display = ft.TextField(
        label="Programm-Ausgabe",
        multiline=True,
        min_lines=8,
        max_lines=15,
        width=500,
        read_only=True,
        border_color=ft.colors.BLUE_GREY_300,
        filled=True,
        bgcolor=ft.colors.BLUE_GREY_50,
        text_size=14
    )
    
    # 4. BUTTON-FUNKTION die WIRKLICH FUNKTIONIERT
    def button_geklickt(e):
        print("🔘 Button wurde geklickt!")
        
        # Sofortige Rückmeldung im Textfeld
        result_display.value = "🔄 SAFKATY wird gestartet...\n"
        page.update()  # WICHTIG: Sofort aktualisieren!
        
        try:
            # 1. Prüfen ob safkaty.py existiert
            if os.path.exists("safkaty.py"):
                result_display.value += "✓ Datei 'safkaty.py' gefunden\n"
                page.update()
                
                # 2. Python-Pfad finden
                python_exe = sys.executable
                result_display.value += f"✓ Python: {python_exe}\n"
                
                # 3. Skript ausführen
                result_display.value += "🚀 Starte Programm...\n"
                page.update()
                
                # Einfacher Testbefehl
                process = subprocess.run(
                    [python_exe, "safkaty.py"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # 4. Ergebnisse anzeigen
                if process.returncode == 0:
                    result_display.value += f"\n✅ PROGRAMM ERFOLGREICH!\n"
                    result_display.value += f"Rückgabecode: {process.returncode}\n\n"
                    
                    if process.stdout:
                        # Erste 1000 Zeichen anzeigen
                        output = process.stdout[:1000]
                        result_display.value += f"Ausgabe:\n{output}\n"
                        
                        if len(process.stdout) > 1000:
                            result_display.value += f"... (noch {len(process.stdout)-1000} Zeichen)\n"
                
                else:
                    result_display.value += f"\n⚠️ PROGRAMM MIT FEHLER BEENDET\n"
                    result_display.value += f"Rückgabecode: {process.returncode}\n"
                    
                    if process.stderr:
                        result_display.value += f"Fehler:\n{process.stderr}\n"
                        
            else:
                # Datei nicht gefunden
                result_display.value = "❌ FEHLER: 'safkaty.py' nicht gefunden!\n\n"
                result_display.value += f"Aktuelles Verzeichnis: {os.getcwd()}\n"
                result_display.value += "Vorhandene Dateien:\n"
                
                # Alle Dateien auflisten
                files = os.listdir(".")
                for file in files:
                    result_display.value += f"- {file}\n"
        
        except subprocess.TimeoutExpired:
            result_display.value += "\n⏱️ ZEITÜBERSCHREITUNG: Programm lief zu lange!\n"
            
        except Exception as error:
            result_display.value += f"\n❌ UNERWARTETER FEHLER:\n{str(error)}\n"
        
        # Zum Schluss alles aktualisieren
        page.update()
        print("✓ Button-Aktion beendet")
    
    # 5. BUTTON mit KORREKTER Funktion
    start_button = ft.ElevatedButton(
        text="🚀 SAFKATY STARTEN 🚀",
        on_click=button_geklickt,  # WICHTIG: Richtige Funktion!
        width=300,
        height=60,
        style=ft.ButtonStyle(
            bgcolor=ft.colors.BLUE_700,
            color=ft.colors.WHITE,
            padding=ft.padding.all(15),
            elevation=8
        )
    )
    
    # 6. Alles auf der Seite anordnen
    page.add(
        ft.Column([
            # Statuszeile
            ft.Container(
                content=status_text,
                padding=ft.padding.only(bottom=20)
            ),
            
            # Titel
            ft.Text(
                "SAFKATY",
                size=36,
                weight=ft.FontWeight.BOLD,
                color=ft.colors.BLUE_900
            ),
            
            # Untertitel
            ft.Text(
                "Marchés Publics Manager",
                size=18,
                color=ft.colors.BLUE_GREY_600
            ),
            
            ft.Divider(height=30, thickness=1),
            
            # Button in der Mitte
            ft.Container(
                content=start_button,
                alignment=ft.alignment.center,
                padding=ft.padding.only(bottom=30)
            ),
            
            # Ausgabe-Feld
            result_display,
            
            # Hinweis
            ft.Text(
                "Klicke oben auf den blauen Button um SAFKATY zu starten",
                size=12,
                color=ft.colors.GREY_600,
                italic=True
            )
        ],
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO)
    )
    
    print("✓ App-UI ist fertig geladen")
    page.update()

# WICHTIGER TEIL - DIE BUTTON-FUNKTION:
def on_button_klick(e):
    # 1. SOFORT was anzeigen
    result_text.value = "🔄 Starte SAFKATY...\n"
    page.update()  # WICHTIG!
    
    # 2. Programmlogik
    try:
        # Hier kommt dein Code...
        result_text.value += "✓ Programm läuft\n"
    except Exception as fehler:
        result_text.value = f"❌ Fehler: {fehler}"
    
    # 3. Seite aktualisieren
    page.update()

# Button erstellen
button = ft.ElevatedButton(
    "SAFKATY STARTEN",
    on_click=on_button_klick  # Funktion verknüpfen
)

# App starten
if __name__ == "__main__":
    print("🚀 Starte Flet App...")
    ft.app(target=main)
