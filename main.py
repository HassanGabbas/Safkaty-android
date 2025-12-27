import flet as ft
import subprocess
import sys
import os
import threading

def main(page: ft.Page):
    page.title = "SAFKATY - Marchés Publics"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 30
    page.scroll = ft.ScrollMode.AUTO
    
    # Status-Anzeige
    status = ft.Text(
        "✅ SAFKATY BEREIT",
        size=20,
        color=ft.colors.GREEN_700,
        weight=ft.FontWeight.BOLD
    )
    
    # Fortschrittsanzeige
    progress_bar = ft.ProgressBar(width=400, visible=False)
    progress_text = ft.Text("", size=14, color=ft.colors.BLUE_700)
    
    # Ausgabe-Feld
    ausgabe = ft.TextField(
        label="SAFKATY Ausgabe",
        multiline=True,
        min_lines=15,
        max_lines=30,
        width=700,
        read_only=True,
        border_color=ft.colors.BLUE_300,
        filled=True,
        bgcolor=ft.colors.GREY_50,
        text_size=14,
        border_radius=10
    )
    
    # Button-Funktion MIT ECHTEM PROGRAMM
    def start_safkaty(e):
        # UI zurücksetzen
        ausgabe.value = ""
        progress_bar.visible = True
        progress_bar.value = None  # Unbestimmter Fortschritt
        progress_text.value = "🚀 Starte SAFKATY..."
        status.value = "🔄 SAFKATY LÄUFT..."
        status.color = ft.colors.ORANGE_700
        button.disabled = True
        page.update()
        
        def programm_ausfuehren():
            try:
                # 1. Prüfen ob Datei existiert
                if not os.path.exists("safkaty.py"):
                    page.run_task(lambda: fehler_anzeigen("❌ safkaty.py nicht gefunden!"))
                    return
                
                # 2. Programm ausführen
                page.run_task(lambda: status_update("📥 Projekte werden abgerufen..."))
                
                process = subprocess.Popen(
                    [sys.executable, "safkaty.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # 3. Ausgabe live sammeln
                gesamte_ausgabe = ""
                for line in process.stdout:
                    gesamte_ausgabe += line
                    # Live-Update (nur alle 10 Zeilen)
                    if len(gesamte_ausgabe.split('\n')) % 10 == 0:
                        page.run_task(lambda l=gesamte_ausgabe: live_update(l))
                
                # Warten bis fertig
                process.wait()
                
                # 4. Finale Ausgabe
                if process.stderr:
                    gesamte_ausgabe += "\n⚠️ WARNUNGEN:\n" + process.stderr.read()
                
                # 5. Erfolg anzeigen
                page.run_task(lambda: erfolg_anzeigen(gesamte_ausgabe, process.returncode))
                
            except Exception as error:
                page.run_task(lambda: fehler_anzeigen(f"❌ Fehler: {str(error)}"))
        
        # UI-Update Funktionen
        def status_update(nachricht):
            progress_text.value = nachricht
            page.update()
        
        def live_update(text):
            ausgabe.value = text[-5000:]  # Letzte 5000 Zeichen
            page.update()
        
        def erfolg_anzeigen(text, returncode):
            progress_bar.visible = False
            progress_text.value = "✅ Fertig!"
            status.value = f"✅ SAFKATY BEENDET (Code: {returncode})"
            status.color = ft.colors.GREEN_700
            
            # Ausgabe formatieren
            ausgabe.value = "=" * 70 + "\n"
            ausgabe.value += "SAFKATY - MARCHÉS PUBLICS\n"
            ausgabe.value += "=" * 70 + "\n\n"
            ausgabe.value += text[-10000:]  # Letzte 10.000 Zeichen
            
            if len(text) > 10000:
                ausgabe.value += f"\n\n... ({len(text) - 10000} weitere Zeichen)\n"
            
            ausgabe.value += "\n" + "=" * 70 + "\n"
            ausgabe.value += f"Programm beendet mit Code: {returncode}"
            
            button.disabled = False
            page.update()
        
        def fehler_anzeigen(fehler_text):
            progress_bar.visible = False
            progress_text.value = "❌ Fehler!"
            status.value = "❌ FEHLER"
            status.color = ft.colors.RED_700
            ausgabe.value = fehler_text
            button.disabled = False
            page.update()
        
        # Programm im Hintergrund starten
        thread = threading.Thread(target=programm_ausfuehren)
        thread.daemon = True
        thread.start()
    
    # Button
    button = ft.ElevatedButton(
        "🚀 SAFKATY STARTEN (Marchés Publics abrufen)",
        icon=ft.icons.SEARCH,
        on_click=start_safkaty,
        width=450,
        height=60,
        style=ft.ButtonStyle(
            bgcolor=ft.colors.BLUE_600,
            color=ft.colors.WHITE,
            padding=20,
            elevation=10
        )
    )
    
    # Alles auf Seite platzieren
    page.add(
        ft.Column([
            # Kopfzeile
            ft.Container(
                content=ft.Column([
                    status,
                    ft.Text("SAFKATY", size=42, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_900),
                    ft.Text("Marchés Publics Manager", size=18, color=ft.colors.BLUE_GREY_600),
                    ft.Divider(height=20, thickness=2)
                ]),
                alignment=ft.alignment.center
            ),
            
            # Fortschritt
            ft.Container(
                content=ft.Column([
                    progress_text,
                    progress_bar,
                    ft.Divider(height=30)
                ]),
                alignment=ft.alignment.center
            ),
            
            # Haupt-Button
            ft.Container(
                content=button,
                alignment=ft.alignment.center,
                padding=ft.padding.only(bottom=30)
            ),
            
            # Ausgabe
            ft.Text("Ergebnisse:", size=16, weight=ft.FontWeight.BOLD),
            ausgabe,
            
            # Fußzeile
            ft.Container(
                content=ft.Column([
                    ft.Divider(height=20),
                    ft.Text(
                        "⚠️ Das Abrufen der Marchés Publics kann mehrere Minuten dauern",
                        size=12,
                        color=ft.colors.ORANGE_700,
                        italic=True
                    ),
                    ft.Text(
                        "Die App bleibt während der Ausführung reagierend",
                        size=11,
                        color=ft.colors.GREY_600
                    )
                ]),
                padding=ft.padding.only(top=20)
            )
        ],
        spacing=15,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO)
    )

# App starten
if __name__ == "__main__":
    ft.app(target=main)
