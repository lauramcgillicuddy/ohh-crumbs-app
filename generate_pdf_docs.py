"""
PDF Generator for Documentation
Converts FEATURE_GUIDE.md and TECHNICAL_DOCS.md to beautiful PDFs
"""

import markdown
from weasyprint import HTML, CSS
from pathlib import Path


def markdown_to_pdf(markdown_file, pdf_file):
    """Convert a markdown file to a styled PDF"""

    # Read the markdown file
    with open(markdown_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Convert markdown to HTML
    html_content = markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'codehilite', 'toc']
    )

    # Add CSS styling for a beautiful PDF
    styled_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: A4;
                margin: 2cm;
                @bottom-right {{
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 9pt;
                    color: #666;
                }}
            }}

            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
            }}

            h1 {{
                color: #F29BB2;
                border-bottom: 3px solid #FFE4F2;
                padding-bottom: 10px;
                page-break-before: always;
                margin-top: 30px;
            }}

            h1:first-of-type {{
                page-break-before: avoid;
            }}

            h2 {{
                color: #FF6B9D;
                border-bottom: 2px solid #FFE4F2;
                padding-bottom: 5px;
                margin-top: 25px;
            }}

            h3 {{
                color: #F29BB2;
                margin-top: 20px;
            }}

            code {{
                background-color: #FFF7F2;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: "Courier New", monospace;
                font-size: 0.9em;
                color: #2C1735;
            }}

            pre {{
                background-color: #FFF7F2;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #F29BB2;
                overflow-x: auto;
                page-break-inside: avoid;
            }}

            pre code {{
                background: none;
                padding: 0;
            }}

            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
                page-break-inside: avoid;
            }}

            th, td {{
                border: 1px solid #FFE4F2;
                padding: 10px;
                text-align: left;
            }}

            th {{
                background-color: #FFF7F2;
                color: #2C1735;
                font-weight: bold;
            }}

            tr:nth-child(even) {{
                background-color: #FFFBF8;
            }}

            blockquote {{
                border-left: 4px solid #F29BB2;
                padding-left: 15px;
                margin-left: 0;
                color: #666;
                font-style: italic;
                background-color: #FFF7F2;
                padding: 10px 15px;
            }}

            ul, ol {{
                margin: 10px 0;
                padding-left: 25px;
            }}

            li {{
                margin: 5px 0;
            }}

            a {{
                color: #FF6B9D;
                text-decoration: none;
            }}

            a:hover {{
                text-decoration: underline;
            }}

            hr {{
                border: none;
                border-top: 2px solid #FFE4F2;
                margin: 30px 0;
            }}

            .emoji {{
                font-family: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # Convert HTML to PDF
    HTML(string=styled_html).write_pdf(pdf_file)
    print(f"✅ Generated: {pdf_file}")


def generate_all_pdfs():
    """Generate PDFs for all documentation files"""

    print("🍰 Ohh Crumbs - PDF Generator")
    print("=" * 50)
    print()

    docs = [
        ("FEATURE_GUIDE.md", "FEATURE_GUIDE.pdf"),
        ("TECHNICAL_DOCS.md", "TECHNICAL_DOCS.pdf")
    ]

    for md_file, pdf_file in docs:
        if Path(md_file).exists():
            print(f"📄 Converting {md_file} to PDF...")
            try:
                markdown_to_pdf(md_file, pdf_file)
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print(f"⚠️  File not found: {md_file}")

    print()
    print("🎉 PDF generation complete!")
    print()
    print("📍 Generated files:")
    print("   - FEATURE_GUIDE.pdf")
    print("   - TECHNICAL_DOCS.pdf")
    print()
    print("💜✨ Your docs are ready to print or share!")


if __name__ == "__main__":
    generate_all_pdfs()
