# main.py - Flet 0.28.3 Version
import flet as ft
import subprocess
import sys
import os

def main(page: ft.Page):
    # App-Einstellungen
    page.title = "SAFKATY - Marchés Publics"
    page.theme_mode = "light"
    page.padding = 20
    page.bgcolor = "white"
    
    # Header
    header = ft.Row([
        ft.Icon(name="public", color="blue", size=40),
        ft.Column([
            ft.Text("SAFKATY", size=32, weight="bold", color="blue700"),
            ft.Text("Marchés Publics Manager", size=16, color="bluegrey600")
        ])
    ])
    
    # Status-Anzeige
    status_text = ft.Text("Bereit", size=18, weight="bold", color="green700")
    
    # Output-Bereich
    output_area = ft.TextField(
        label="Ausgabe",
        multiline=True,
        min_lines=12,
        max_lines=25,
        expand=True,
        read_only=True,
        border_color="blue200",
        filled=True,
        fill_color="grey50"
    )
    
    # Fortschrittsbalken
    progress_bar = ft.ProgressBar(width=400, visible=False)
    
    # SAFKATY starten
    def start_safkaty(e):
        status_text.value = "🔄 SAFKATY wird ausgeführt..."
        status_text.color = "orange"
        output_area.value = ""
        progress_bar.visible = True
        page.update()
        
        try:
            # Prüfe ob safkaty.py existiert
            if not os.path.exists("safkaty.py"):
                output_area.value = "❌ FEHLER: safkaty.py nicht gefunden!\n\n"
                output_area.value += "Verfügbare Dateien:\n"
                for f in os.listdir("."):
                    output_area.value += f"- {f}\n"
                status_text.value = "❌ Datei nicht gefunden"
                status_text.color = "red"
                progress_bar.visible = False
                page.update()
                return
            
            # Skript ausführen
            result = subprocess.run(
                [sys.executable, "safkaty.py"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=30
            )
            
            # Ergebnis verarbeiten
            output = ""
            
            if result.stdout:
                output += f"✅ ERGEBNIS:\n{result.stdout}\n"
            
            if result.stderr:
                output += f"⚠️  WARNUNGEN:\n{result.stderr}\n"
            
            output_area.value = output
            
            # Status setzen
            if result.returncode == 0:
                status_text.value = "✅ Abgeschlossen"
                status_text.color = "green"
            else:
                status_text.value = f"⚠️  Exit-Code: {result.returncode}"
                status_text.color = "orange"
                
        except subprocess.TimeoutExpired:
            output_area.value = "⏱️  Zeitüberschreitung: Skript lief zu lange (30s)."
            status_text.value = "⏱️  Zeitüberschreitung"
            status_text.color = "red"
        except Exception as ex:
            output_area.value = f"❌ UNBEKANNTER FEHLER:\n{str(ex)}"
            status_text.value = "❌ Fehler"
            status_text.color = "red"
        
        # Fortschrittsbalken ausblenden
        progress_bar.visible = False
        page.update()
    
    # Dateien anzeigen
    def show_files(e):
        files = os.listdir(".")
        file_list = "\n".join([f"📄 {f}" for f in files])
        output_area.value = f"📁 Dateien im Ordner:\n{file_list}"
        page.update()
    
    # Info anzeigen
    def show_info(e):
        info = f"""
📱 SAFKATY App v1.0
===================

Funktionen:
• Marchés Publics verwalten
• Daten von marchéspublics.gov.ma abrufen
• Ergebnisse anzeigen und exportieren

System:
• Python: {sys.version.split()[0]}
• Flet: {ft.__version__}
• Verzeichnis: {os.getcwd()}

Dein Original-Skript 'safkaty.py' bleibt unverändert.
"""
        output_area.value = info
        page.update()
    
    # Buttons
    buttons = ft.Row([
        ft.ElevatedButton(
            "🚀 SAFKATY starten",
            icon="play_arrow",
            on_click=start_safkaty,
            style=ft.ButtonStyle(
                padding=15,
                bgcolor="blue",
                color="white"
            ),
            width=220
        ),
        ft.OutlinedButton(
            "📁 Dateien",
            icon="folder_open",
            on_click=show_files,
            width=120
        ),
        ft.OutlinedButton(
            "ℹ️  Info",
            icon="info",
            on_click=show_info,
            width=120
        )
    ])
    
    # UI aufbauen
    page.add(
        ft.Column([
            header,
            ft.Divider(height=20),
            
            # Status-Bereich
            ft.Container(
                ft.Column([
                    ft.Text("Status:", size=20, weight="bold"),
                    ft.Row([status_text, progress_bar])
                ]),
                padding=10,
                bgcolor="bluegrey50",
                border_radius=8
            ),
            
            ft.Divider(height=15),
            
            # Buttons
            buttons,
            
            ft.Divider(height=15),
            
            # Ausgabe-Bereich
            ft.Text("Ausgabe:", size=20, weight="bold"),
            output_area,
            
            # Footer
            ft.Container(
                ft.Text(
                    "Tipp: Klicke 'SAFKATY starten' um dein Skript auszuführen",
                    size=12,
                    color="grey600",
                    text_align="center"
                ),
                padding=10,
                bgcolor="bluegrey100",
                border_radius=8,
                margin=ft.margin.only(top=10)
            )
        ], spacing=10)
    )

# App starten
if __name__ == "__main__":
    ft.app(target=main)
