# main.py - SAFKATY App mit Debug-Informationen
import flet as ft
import subprocess
import sys
import os
import traceback

def main(page: ft.Page):
    try:
        # Grundlegende Seiten-Einstellungen
        page.title = "SAFKATY - Marchés Publics"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.scroll = ft.ScrollMode.ADAPTIVE
        
        # Debug-Info sammeln
        debug_info = []
        debug_info.append(f"Python Version: {sys.version}")
        debug_info.append(f"Flet Version: {ft.__version__}")
        debug_info.append(f"Verzeichnis: {os.getcwd()}")
        debug_info.append(f"Dateien im Ordner: {os.listdir('.')}")
        
        # Status-Text
        status_text = ft.Text(
            "App gestartet",
            size=18,
            color=ft.colors.GREEN,
            weight=ft.FontWeight.BOLD
        )
        
        # Debug-Anzeige
        debug_display = ft.TextField(
            label="Debug-Informationen",
            value="\n".join(debug_info),
            multiline=True,
            min_lines=8,
            max_lines=15,
            read_only=True,
            border_color=ft.colors.BLUE_GREY_300,
            bgcolor=ft.colors.BLUE_GREY_50
        )
        
        # Output-Anzeige
        output_display = ft.TextField(
            label="Ausgabe",
            multiline=True,
            min_lines=10,
            max_lines=20,
            expand=True,
            read_only=True,
            border_color=ft.colors.GREY_400
        )
        
        # SAFKATY starten
        def start_safkaty(e):
            try:
                status_text.value = "SAFKATY wird ausgeführt..."
                status_text.color = ft.colors.ORANGE
                output_display.value = ""
                page.update()
                
                # Prüfe ob safkaty.py existiert
                if not os.path.exists("safkaty.py"):
                    output_display.value = "❌ FEHLER: safkaty.py nicht gefunden!\n\n"
                    output_display.value += f"Verfügbare Dateien:\n"
                    for file in os.listdir("."):
                        output_display.value += f"- {file}\n"
                    status_text.value = "Fehler: Datei nicht gefunden"
                    status_text.color = ft.colors.RED
                    page.update()
                    return
                
                # Skript ausführen mit Timeout
                output_display.value = "🔄 Skript wird gestartet...\n"
                page.update()
                
                result = subprocess.run(
                    [sys.executable, "safkaty.py"],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    timeout=30  # 30 Sekunden Timeout
                )
                
                # Ergebnis verarbeiten
                output_text = ""
                if result.stdout:
                    output_text += f"✅ ERGEBNIS:\n{result.stdout}\n"
                if result.stderr:
                    output_text += f"⚠️  WARNUNGEN:\n{result.stderr}\n"
                
                output_display.value = output_text[:2000]  # Begrenze Länge
                
                if result.returncode == 0:
                    status_text.value = "✅ Abgeschlossen"
                    status_text.color = ft.colors.GREEN
                else:
                    status_text.value = f"⚠️  Exit-Code: {result.returncode}"
                    status_text.color = ft.colors.ORANGE
                    
            except subprocess.TimeoutExpired:
                output_display.value = "⏱️  Zeitüberschreitung: Skript lief zu lange."
                status_text.value = "⏱️  Zeitüberschreitung"
                status_text.color = ft.colors.RED
            except Exception as ex:
                output_display.value = f"❌ UNBEKANNTER FEHLER:\n{str(ex)}\n\n{traceback.format_exc()}"
                status_text.value = "❌ Fehler"
                status_text.color = ft.colors.RED
            
            page.update()
        
        # UI bauen
        page.add(
            ft.Column([
                # Header
                ft.Row([
                    ft.Icon(ft.icons.PUBLIC, color=ft.colors.BLUE, size=40),
                    ft.Column([
                        ft.Text("SAFKATY", size=32, weight=ft.FontWeight.BOLD),
                        ft.Text("Marchés Publics Manager", size=16, color=ft.colors.BLUE_GREY)
                    ])
                ]),
                
                ft.Divider(height=20),
                
                # Status
                ft.Container(
                    ft.Column([
                        ft.Text("Status:", size=20, weight=ft.FontWeight.BOLD),
                        status_text
                    ]),
                    padding=10,
                    bgcolor=ft.colors.BLUE_GREY_50,
                    border_radius=10
                ),
                
                # Buttons
                ft.Row([
                    ft.ElevatedButton(
                        "🚀 SAFKATY starten",
                        icon=ft.icons.PLAY_ARROW,
                        on_click=start_safkaty,
                        style=ft.ButtonStyle(
                            padding=20,
                            bgcolor=ft.colors.BLUE_600,
                            color=ft.colors.WHITE
                        ),
                        width=250
                    ),
                    ft.OutlinedButton(
                        "🔄 App neu laden",
                        icon=ft.icons.REFRESH,
                        on_click=lambda e: page.update(),
                        width=150
                    )
                ], alignment=ft.MainAxisAlignment.CENTER),
                
                ft.Divider(height=20),
                
                # Debug Info (ausblendbar)
                ft.ExpansionTile(
                    title=ft.Text("Debug-Informationen"),
                    controls=[debug_display]
                ),
                
                # Ausgabe
                ft.Text("Ausgabe:", size=20, weight=ft.FontWeight.BOLD),
                output_display,
                
                # Footer
                ft.Container(
                    ft.Text(
                        "Version 1.0 • Dein Original-Skript bleibt unverändert",
                        size=12,
                        color=ft.colors.GREY,
                        text_align=ft.TextAlign.CENTER
                    ),
                    padding=10,
                    alignment=ft.alignment.center
                )
            ], 
            spacing=15,
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True)
        )
        
        # Erfolgreich geladen
        print("✅ Flet App erfolgreich geladen")
        
    except Exception as e:
        # Falls beim Setup etwas schief geht
        error_msg = f"❌ FEHLER BEIM APP-START:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        page.add(ft.Text(error_msg, color=ft.colors.RED, size=14))

# App starten MIT CONSOLE für Debugging
if __name__ == "__main__":
    print("🚀 SAFKATY App startet...")
    ft.app(target=main, view=ft.AppView.FLET_APP)
