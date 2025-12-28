# main.py - EINFACHE SAFKATY APP
import flet as ft

def main(page: ft.Page):
    # Einfache App die garantiert funktioniert
    page.title = "SAFKATY"
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"
    
    # Einfacher Text zum Testen
    page.add(
        ft.Column([
            ft.Text("SAFKATY APP", size=40, weight="bold", color="blue"),
            ft.Text("Mobile Version", size=20, color="grey"),
            ft.Divider(height=20),
            ft.ElevatedButton(
                "Test Button",
                icon="check",
                on_click=lambda e: print("Button clicked!")
            )
        ], alignment="center", horizontal_alignment="center")
    )
    
    print("✅ App gestartet!")

# App starten
ft.app(target=main)
