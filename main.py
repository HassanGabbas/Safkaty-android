# main.py - DIESE DATEI MUSS REINER PYTHON-CODE SEIN!

import flet as ft
import subprocess
import sys
import os

def main(page: ft.Page):
    # Einfache Startseite
    page.title = "SAFKATY App"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    def on_start_click(e):
        result.value = "SAFKATY wird gestartet..."
        page.update()
        
        try:
            # Prüfe ob safkaty.py existiert
            if os.path.exists("safkaty.py"):
                # Skript ausführen
                process = subprocess.run(
                    [sys.executable, "safkaty.py"],
                    capture_output=True,
                    text=True
                )
                
                if process.stdout:
                    result.value = f"Erfolg:\n{process.stdout[:500]}..."  # Erste 500 Zeichen
                if process.stderr:
                    result.value += f"\nFehler:\n{process.stderr}"
            else:
                result.value = "Fehler: safkaty.py nicht gefunden!"
                
        except Exception as ex:
            result.value = f"Fehler: {str(ex)}"
        
        page.update()
    
    # UI Elemente
    title = ft.Text("SAFKATY", size=32, weight=ft.FontWeight.BOLD)
    subtitle = ft.Text("Marchés Publics Manager", size=18, color=ft.colors.BLUE_GREY)
    
    start_btn = ft.ElevatedButton(
        "Start SAFKATY",
        icon=ft.icons.PLAY_ARROW,
        on_click=on_start_click,
        width=200,
        height=50
    )
    
    result = ft.TextField(
        multiline=True,
        min_lines=10,
        max_lines=20,
        width=400,
        read_only=True,
        border_color=ft.colors.GREY_300
    )
    
    # Alles zur Seite hinzufügen
    page.add(
        ft.Column([
            title,
            subtitle,
            ft.Divider(height=20),
            start_btn,
            ft.Divider(height=20),
            result
        ], 
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=15)
    )

# App starten
if __name__ == "__main__":
    ft.app(target=main)
