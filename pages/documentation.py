import streamlit as st
import markdown
from weasyprint import HTML
import os
from datetime import datetime

st.set_page_config(page_title="📚 Documentation", page_icon="📚", layout="wide")

def markdown_to_pdf(markdown_file, pdf_file):
    """Convert a markdown file to a styled PDF."""
    try:
        # Read the markdown file
        with open(markdown_file, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # Convert markdown to HTML with extensions
        html_content = markdown.markdown(
            md_content,
            extensions=['tables', 'fenced_code', 'toc']
        )

        # Create styled HTML
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
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                }}

                h1 {{
                    color: #F29BB2;
                    border-bottom: 3px solid #FFE4F2;
                    padding-bottom: 10px;
                    margin-top: 30px;
                    page-break-after: avoid;
                }}

                h2 {{
                    color: #FF6B9D;
                    border-bottom: 2px solid #FFE4F2;
                    padding-bottom: 8px;
                    margin-top: 25px;
                    page-break-after: avoid;
                }}

                h3 {{
                    color: #FF6B9D;
                    margin-top: 20px;
                    page-break-after: avoid;
                }}

                h4 {{
                    color: #F29BB2;
                    margin-top: 15px;
                }}

                code {{
                    background-color: #FFF7F2;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                    color: #E63946;
                    font-size: 0.9em;
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
                    background-color: transparent;
                    padding: 0;
                    color: #333;
                }}

                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                    page-break-inside: avoid;
                }}

                th {{
                    background-color: #F29BB2;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    border: 1px solid #FFE4F2;
                }}

                td {{
                    padding: 10px;
                    border: 1px solid #FFE4F2;
                }}

                tr:nth-child(even) {{
                    background-color: #FFF7F2;
                }}

                blockquote {{
                    border-left: 4px solid #F29BB2;
                    padding-left: 20px;
                    margin-left: 0;
                    color: #666;
                    font-style: italic;
                    background-color: #FFF7F2;
                    padding: 15px 20px;
                    border-radius: 0 5px 5px 0;
                }}

                ul, ol {{
                    margin: 15px 0;
                    padding-left: 30px;
                }}

                li {{
                    margin: 8px 0;
                }}

                a {{
                    color: #FF6B9D;
                    text-decoration: none;
                }}

                a:hover {{
                    text-decoration: underline;
                }}

                .toc {{
                    background-color: #FFF7F2;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                    border: 2px solid #FFE4F2;
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
        return True
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")
        return False

def show_documentation():
    st.title("📚 Documentation & PDF Export")
    st.markdown("---")

    st.markdown("""
    Welcome to the documentation center! Here you can view and download PDF versions
    of the complete feature guide and technical documentation.
    """)

    # Check if markdown files exist
    feature_guide_exists = os.path.exists('FEATURE_GUIDE.md')
    technical_docs_exists = os.path.exists('TECHNICAL_DOCS.md')

    if not feature_guide_exists and not technical_docs_exists:
        st.warning("⚠️ No documentation files found. Please ensure FEATURE_GUIDE.md and TECHNICAL_DOCS.md exist in the project root.")
        return

    col1, col2 = st.columns(2)

    # Feature Guide
    with col1:
        st.markdown("### 📖 Feature Guide")
        st.markdown("""
        Complete user manual with step-by-step guides for:
        - All features and how to use them
        - Tips and best practices
        - Troubleshooting guides
        - Learning path for new users
        """)

        if feature_guide_exists:
            if st.button("📥 Generate Feature Guide PDF", key="feature_pdf", use_container_width=True):
                with st.spinner("✨ Creating your PDF..."):
                    pdf_path = "FEATURE_GUIDE.pdf"
                    if markdown_to_pdf("FEATURE_GUIDE.md", pdf_path):
                        with open(pdf_path, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()

                        st.download_button(
                            label="💾 Download Feature Guide PDF",
                            data=pdf_bytes,
                            file_name=f"Ohh_Crumbs_Feature_Guide_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        st.success("✅ PDF generated successfully!")
        else:
            st.info("Feature guide not available")

    # Technical Documentation
    with col2:
        st.markdown("### 🔧 Technical Documentation")
        st.markdown("""
        Developer reference covering:
        - System architecture
        - Database schema
        - Implementation details
        - Code examples
        """)

        if technical_docs_exists:
            if st.button("📥 Generate Technical Docs PDF", key="tech_pdf", use_container_width=True):
                with st.spinner("✨ Creating your PDF..."):
                    pdf_path = "TECHNICAL_DOCS.pdf"
                    if markdown_to_pdf("TECHNICAL_DOCS.md", pdf_path):
                        with open(pdf_path, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()

                        st.download_button(
                            label="💾 Download Technical Docs PDF",
                            data=pdf_bytes,
                            file_name=f"Ohh_Crumbs_Technical_Docs_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        st.success("✅ PDF generated successfully!")
        else:
            st.info("Technical documentation not available")

    st.markdown("---")

    # Generate both at once
    st.markdown("### 📦 Generate All Documentation")
    if st.button("📥 Generate All PDFs", use_container_width=True, type="primary"):
        success_count = 0
        total_count = 0

        with st.spinner("✨ Creating all PDFs..."):
            if feature_guide_exists:
                total_count += 1
                if markdown_to_pdf("FEATURE_GUIDE.md", "FEATURE_GUIDE.pdf"):
                    success_count += 1

            if technical_docs_exists:
                total_count += 1
                if markdown_to_pdf("TECHNICAL_DOCS.md", "TECHNICAL_DOCS.pdf"):
                    success_count += 1

        if success_count == total_count:
            st.success(f"✅ All {total_count} PDF(s) generated successfully!")
            st.info("💡 Click the individual download buttons above to get your PDFs.")
        else:
            st.warning(f"⚠️ Generated {success_count} of {total_count} PDFs. Some files may have errors.")

    st.markdown("---")

    # View markdown files directly
    st.markdown("### 👀 Quick Preview")

    preview_option = st.selectbox(
        "Select document to preview:",
        ["None", "Feature Guide", "Technical Documentation"]
    )

    if preview_option == "Feature Guide" and feature_guide_exists:
        with st.expander("📖 View Feature Guide", expanded=True):
            with open("FEATURE_GUIDE.md", 'r', encoding='utf-8') as f:
                st.markdown(f.read())

    elif preview_option == "Technical Documentation" and technical_docs_exists:
        with st.expander("🔧 View Technical Documentation", expanded=True):
            with open("TECHNICAL_DOCS.md", 'r', encoding='utf-8') as f:
                st.markdown(f.read())

if __name__ == "__main__":
    show_documentation()
