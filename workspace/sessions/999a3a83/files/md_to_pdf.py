from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# Read the markdown file
with open('ai_impact_developers.md', 'r') as f:
    md_content = f.read()

# Create PDF document
doc = SimpleDocTemplate("ai_impact_developers.pdf", pagesize=letter)
styles = getSampleStyleSheet()

story = []

# Process markdown content
for line in md_content.split('\n'):
    if line.startswith('# '):
        story.append(Paragraph(line[2:], styles['Heading1']))
    elif line.startswith('## '):
        story.append(Paragraph(line[3:], styles['Heading2']))
    elif line.startswith('### '):
        story.append(Paragraph(line[4:], styles['Heading3']))
    elif line.strip():
        story.append(Paragraph(line, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

# Build PDF
doc.build(story)
print("PDF created successfully!")