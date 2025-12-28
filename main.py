# main.py - Android-kompatible Version
import flet as ft
import sys
import os
import traceback

def main(page: ft.Page):
    # App-Einstellungen
    page.title = "SAFKATY - Marchés Publics"
    page.theme_mode = "light"
    page.padding = 20
    page.bgcolor = "white"
    
    # Debug-Info: Prüfe ob wir auf Android sind
    IS_ANDROID = hasattr(sys, 'getandroidapilevel')
    
    # Header
    header = ft.Row([
        ft.Icon(name="public", color="blue", size=40),
        ft.Column([
            ft.Text("SAFKATY", size=32, weight="bold", color="blue700"),
            ft.Text("Marchés Publics Manager", size=16, color="bluegrey600"),
            ft.Text(f"Android: {'Ja' if IS_ANDROID else 'Nein'}", size=12, color="grey")
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
    
    # SAFKATY starten (ANDROID-KOMPATIBEL)
    def start_safkaty(e):
        status_text.value = "🔄 SAFKATY wird gestartet..."
        status_text.color = "orange"
        output_area.value = ""
        page.update()
        
        try:
            # Prüfe ob wir auf Android sind
            if IS_ANDROID:
                # Auf Android können wir nicht subprocess.run() verwenden
                # Stattdessen: Importiere und führe das Skript direkt aus
                
                # 1. Versuche das Skript zu importieren
                output_area.value = "📦 Lade SAFKATY-Skript...\n"
                page.update()
                
                # Importiere das safkaty.py Modul
                import importlib.util
                
                # Prüfe ob safkaty.py existiert
                script_path = "safkaty.py"
                if not os.path.exists(script_path):
                    output_area.value += f"❌ Datei nicht gefunden: {script_path}\n"
                    status_text.value = "❌ Datei fehlt"
                    status_text.color = "red"
                    page.update()
                    return
                
                # Lese den Inhalt der Datei
                with open(script_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
                
                output_area.value += f"✅ Skript geladen ({len(script_content)} Zeichen)\n"
                page.update()
                
                # 2. Versuche die Hauptfunktion zu extrahieren und auszuführen
                output_area.value += "🔍 Analysiere Skript...\n"
                
                # Einfache Demo-Ausgabe (ersetzte dies durch deine echte Logik)
                output = """
✅ SAFKATY-Simulation auf Android

📊 Demo-Ergebnisse:
• Angebot 1: 100.000 DH - Bauarbeiten
• Angebot 2: 50.000 DH - IT-Dienstleistungen  
• Angebot 3: 75.000 DH - Möbellieferung

⚠️ Hinweis: Auf Android wird eine Simulation ausgeführt.
   Auf dem PC läuft das volle SAFKATY-Skript.
"""
                
                output_area.value += output
                status_text.value = "✅ Simulation abgeschlossen"
                status_text.color = "green"
                
            else:
                # Auf PC: Normales subprocess.run()
                output_area.value = "🖥️  PC-Version wird ausgeführt...\n"
                page.update()
                
                import subprocess
                result = subprocess.run(
                    [sys.executable, "safkaty.py"],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    timeout=30
                )
                
                if result.stdout:
                    output_area.value += f"✅ ERGEBNIS:\n{result.stdout}\n"
                if result.stderr:
                    output_area.value += f"⚠️  WARNUNGEN:\n{result.stderr}\n"
                
                if result.returncode == 0:
                    status_text.value = "✅ Abgeschlossen"
                    status_text.color = "green"
                else:
                    status_text.value = f"⚠️  Exit-Code: {result.returncode}"
                    status_text.color = "orange"
                    
        except Exception as ex:
            error_msg = f"❌ FEHLER:\n{str(ex)}\n\n{traceback.format_exc()}"
            output_area.value += error_msg
            status_text.value = "❌ Fehler"
            status_text.color = "red"
        
        page.update()
    
    # Dateien anzeigen (ANDROID-KOMPATIBEL)
    def show_files(e):
        try:
            files = os.listdir(".")
            file_list = "\n".join([f"📄 {f}" for f in files if not f.startswith('.')])
            
            # Zusätzliche Android-Info
            android_info = ""
            if IS_ANDROID:
                android_info = "\n\n📱 Android-Info:\n"
                android_info += f"• Python: {sys.version}\n"
                android_info += f"• Verzeichnis: {os.getcwd()}\n"
                android_info += f"• Dateien: {len(files)}\n"
                android_info += "• Berechtigung: Eingeschränkt (kein subprocess)"
            
            output_area.value = f"📁 Dateien im Ordner:\n{file_list}{android_info}"
            status_text.value = "✅ Dateien angezeigt"
            status_text.color = "green"
            
        except Exception as ex:
            output_area.value = f"❌ Fehler beim Lesen der Dateien:\n{str(ex)}"
            status_text.value = "❌ Fehler"
            status_text.color = "red"
        
        page.update()
    
    # Demo-Daten anzeigen
    def show_demo(e):
        demo_data = """
📊 SAFKATY - Demo-Daten
=======================

🎯 Funktionen:
1. Marchés Publics durchsuchen
2. Angebote filtern und vergleichen
3. Daten exportieren (CSV/Excel)
4. Benachrichtigungen bei neuen Ausschreibungen

📈 Letzte Ergebnisse:
• Projekt: Rathaus Renovierung - 150.000 DH
• Projekt: Schul-IT Ausstattung - 80.000 DH  
• Projekt: Krankenhaus Möbel - 120.000 DH

📍 Region: Casablanca
📅 Letzte Aktualisierung: Heute
"""
        output_area.value = demo_data
        status_text.value = "📊 Demo angezeigt"
        status_text.color = "blue"
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
            width=200
        ),
        ft.OutlinedButton(
            "📁 Dateien",
            icon="folder_open",
            on_click=show_files,
            width=100
        ),
        ft.OutlinedButton(
            "📊 Demo",
            icon="show_chart",
            on_click=show_demo,
            width=100
        )
    ])
    
    # Info-Text
    info_text = ft.Text(
        "ℹ️  Auf Android: Demo-Modus. Auf PC: Volles Skript.",
        size=12,
        color="grey600",
        text_align="center"
    )
    
    # UI aufbauen
    page.add(
        ft.Column([
            header,
            ft.Divider(height=20),
            
            # Status-Bereich
            ft.Container(
                ft.Column([
                    ft.Text("Status:", size=20, weight="bold"),
                    status_text
                ]),
                padding=10,
                bgcolor="bluegrey50",
                border_radius=8
            ),
            
            ft.Divider(height=15),
            
            # Buttons
            buttons,
            info_text,
            
            ft.Divider(height=15),
            
            # Ausgabe-Bereich
            ft.Text("Ausgabe:", size=20, weight="bold"),
            output_area
        ], spacing=10)
    )

# App starten
if __name__ == "__main__":
    ft.app(target=main)
