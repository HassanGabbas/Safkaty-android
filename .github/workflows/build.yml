name: Build SAFKATY APK

on:
  push:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout
      uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install flet requests beautifulsoup4
    
    - name: Create main.py if missing
      run: |
        # Falls main.py nicht existiert, erstelle eine einfache
        if [ ! -f "main.py" ]; then
          echo 'import flet as ft' > main.py
          echo 'def main(page: ft.Page):' >> main.py
          echo '    page.add(ft.Text("SAFKATY App lädt..."))' >> main.py
          echo 'ft.app(target=main)' >> main.py
          echo "⚠️  main.py wurde automatisch erstellt"
        else
          echo "✅ main.py existiert bereits"
        fi
        
        # Zeige Dateien
        ls -la
    
    - name: Build APK
      run: |
        echo "y" | flet build apk --verbose
    
    - name: Upload APK
      uses: actions/upload-artifact@v4
      with:
        name: safkaty-apk
        path: build/apk/*.apk
        if-no-files-found: error
