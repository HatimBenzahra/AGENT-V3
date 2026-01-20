"""PDF generation tool."""
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from src.tools.base import Tool

if TYPE_CHECKING:
    from src.execution.docker_context import DockerExecutionContext
    from src.session.conversation_context import ConversationContext


class CreatePDFTool(Tool):
    """Create PDF files from text content."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize PDF tool."""
        super().__init__(execution_context, conversation_context)
        if not execution_context:
            raise ValueError("CreatePDFTool requires DockerExecutionContext")

    @property
    def name(self) -> str:
        return "create_pdf"

    @property
    def description(self) -> str:
        return (
            "Create a PDF document from text content. "
            "Supports basic formatting with markdown-like syntax. "
            "Use # for titles, ## for subtitles, and regular text for paragraphs."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Output PDF filename (e.g., 'article.pdf', 'report.pdf')",
                },
                "title": {
                    "type": "string",
                    "description": "Document title",
                },
                "content": {
                    "type": "string",
                    "description": "Text content for the PDF. Use # for headings, ## for subheadings.",
                },
            },
            "required": ["file_path", "title", "content"],
        }

    @property
    def requires_docker(self) -> bool:
        return True

    async def execute(self, file_path: str, title: str, content: str) -> str:
        """Create PDF from content."""
        try:
            # First ensure reportlab is installed in the container
            install_cmd = "pip install reportlab -q"
            await self.execution_context.execute_command(install_cmd)
            
            # Create a Python script to generate the PDF
            pdf_script = '''
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def create_pdf(output_path, title, content):
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                          rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=72)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubheading',
        parent=styles['Heading3'],
        fontSize=14,
        spaceBefore=15,
        spaceAfter=8
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        spaceBefore=6,
        spaceAfter=6,
        leading=14
    )
    
    story = []
    
    # Add title
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 0.5*inch))
    
    # Process content
    lines = content.split('\\n')
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.2*inch))
        elif line.startswith('### '):
            story.append(Paragraph(line[4:], subheading_style))
        elif line.startswith('## '):
            story.append(Paragraph(line[3:], heading_style))
        elif line.startswith('# '):
            story.append(Paragraph(line[2:], heading_style))
        else:
            story.append(Paragraph(line, body_style))
    
    doc.build(story)
    return True

# Execute
title = """''' + title.replace('"', '\\"') + '''"""
content = """''' + content.replace('"', '\\"').replace('\\n', '\\\\n') + '''"""
create_pdf("''' + file_path + '''", title, content)
print("PDF created successfully")
'''
            
            # Write the script
            script_path = self.execution_context.resolve_path("_pdf_generator.py")
            script_path.write_text(pdf_script, encoding="utf-8")
            
            # Run the script
            stdout, stderr, exit_code = await self.execution_context.execute_command(
                f"python _pdf_generator.py"
            )
            
            # Clean up script
            script_path.unlink(missing_ok=True)
            
            if exit_code != 0:
                return f"Error creating PDF: {stderr or stdout}"
            
            # Get the output path
            output_path = self.execution_context.resolve_path(file_path)
            
            if not output_path.exists():
                return f"Error: PDF file was not created"
            
            # Register file
            if self.conversation_context:
                self.conversation_context.register_file(file_path, auto_protect=True)
            
            # Get absolute path and download URL
            absolute_path = str(output_path.resolve())
            session_id = self.execution_context.session_id
            download_url = f"/api/files/{session_id}/download?path={file_path}"
            
            return (
                f"PDF created successfully: {file_path}\n"
                f"Size: {output_path.stat().st_size} bytes\n"
                f"Local path: {absolute_path}\n"
                f"Download URL: {download_url}"
            )
            
        except Exception as exc:
            return f"Error creating PDF: {exc}"
