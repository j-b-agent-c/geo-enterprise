name: Daily Audit

on:
  workflow_dispatch:  # Allows manual triggering
  schedule:
    - cron: '0 8 * * *'  # Runs daily at 8am UTC

jobs:
  run-audit:
    runs-on: ubuntu-latest
    
    permissions:
      contents: write  # CRITICAL: Allows the bot to save files

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run Audit Script
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          # TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }} # Optional if using Tavily
        run: python daily_audit.py

      - name: Commit and Push Data
        run: |
          git config --global user.name "GitHub Action"
          git config --global user.email "action@github.com"
          git add history.csv
          # The following line only commits if there are changes
          git commit -m "Update audit history" || echo "No changes to commit"
          git push
