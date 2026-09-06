import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(num_pages)
            super().showPage()
        super().save()

    def draw_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))
        
        # Linea superior de footer
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(40, 35, 572, 35)
        
        # Texto footer
        self.drawString(40, 24, "Pack Secreto de Admision Remota 2026 | Material Exclusivo para Miembros")
        page_str = f"Pagina {self._pageNumber} de {page_count}"
        self.drawRightString(572, 24, page_str)
        self.restoreState()

def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    
    # Colores corporativos sobrios
    C_PRIMARY = colors.HexColor("#0F172A")    # Slate 900
    C_ACCENT = colors.HexColor("#0D9488")     # Teal 600
    C_DARK = colors.HexColor("#1E293B")       # Slate 800
    C_TEXT = colors.HexColor("#334155")       # Slate 700
    C_BG_LIGHT = colors.HexColor("#F8FAFC")   # Slate 50
    C_BORDER = colors.HexColor("#CBD5E1")     # Slate 300
    C_ALERT = colors.HexColor("#991B1B")      # Red 800

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=C_PRIMARY,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=C_ACCENT,
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        'Heading1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=C_PRIMARY,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=C_DARK,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=C_TEXT,
        spaceAfter=6
    )

    bold_style = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=4,
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1E293B")
    )

    story = []

    # =======================================================
    # PORTADA / HEADER
    # =======================================================
    story.append(Paragraph("PACK SECRETO: CLAVES DE ADMISIÓN Y ENTREVISTA REMOTA 2026", title_style))
    story.append(Paragraph("Guía Táctica Confidencial: Outlier AI, DataAnnotation, Remotasks y Empresas Internacionales", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_ACCENT, spaceAfter=12))

    intro_box = Table([
        [Paragraph("<b>ADVERTENCIA DE USO:</b> Este documento contiene las pautas exactas, rúbricas de evaluación de Inteligencia Artificial y plantillas en inglés que utilizan los reclutadores en EE.UU. y Europa para filtrar candidatos. Su contenido está diseñado para maximizar tu tasa de aprobación de pruebas de ingreso del 15% habitual a más del 85%.", callout_style)]
    ], colWidths=[532])
    intro_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.75, C_ACCENT),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(intro_box)
    story.append(Spacer(1, 12))

    # =======================================================
    # MÓDULO 1: EXAMEN DE ADMISIÓN OUTLIER & DATAANNOTATION
    # =======================================================
    story.append(Paragraph("MÓDULO 1: CÓMO APROBAR EL EXAMEN DE ADMISIÓN DE IA (OUTLIER / DATAANNOTATION)", h1_style))
    story.append(Paragraph("El 80% de los postulantes es rechazado en la primera evaluación no por falta de capacidad, sino por desconocer la <b>Rúbrica de Calificación RLHF</b> (Reinforcement Learning from Human Feedback). Las plataformas buscan evaluadores rigurosos y metodológicos.", body_style))

    story.append(Paragraph("1.1 El Filtro Crítico: Instruction Following (Cumplimiento Estricto)", h2_style))
    story.append(Paragraph("Los evaluadores de IA colocan <i>restricciones negativas o limitantes</i> a propósito para ver si prestas atención al detalle:", body_style))

    puntos_instrucciones = [
        "<b>Restricciones de longitud:</b> Si el prompt dice <i>'en exactamente 3 oraciones'</i> o <i>'máximo 50 palabras'</i>, 51 palabras es descalificación automática inmediata. Cuenta las palabras manualmente.",
        "<b>Restricciones de formato:</b> Si solicitan lista numerada, no uses viñetas circulares. Si piden formato Markdown con encabezados H2, asegúrate de colocar <code>##</code>.",
        "<b>Palabras trampa:</b> Pueden pedir: <i>'Escribe un resumen de la fotosíntesis sin utilizar la letra e'</i> o <i>'menciona la palabra mandarina en el segundo párrafo'</i>. Los modelos fallan esto; tu trabajo es auditar si el modelo cumplió cada restricción."
    ]
    for p in puntos_instrucciones:
        story.append(Paragraph(f"• {p}", body_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("1.2 Rúbrica de Calificación: La Jerarquía de Verdad (Factuality)", h2_style))
    story.append(Paragraph("Cuando Outlier o DataAnnotation te piden comparar dos respuestas de modelos (Respuesta A vs Respuesta B), debes aplicar esta jerarquía inquebrantable:", body_style))

    rubric_data = [
        [Paragraph("<b>Criterio</b>", bold_style), Paragraph("<b>Peso</b>", bold_style), Paragraph("<b>Regla de Oro en la Evaluación</b>", bold_style)],
        [Paragraph("1. Veracidad (Truthfulness)", body_style), Paragraph("60%", body_style), Paragraph("Una alucinación factual (dato inventado, fecha falsa, link roto) hace que la respuesta sea <b>severamente rechazada</b>, sin importar qué tan bien escrita esté.", body_style)],
        [Paragraph("2. Instruction Following", body_style), Paragraph("25%", body_style), Paragraph("¿Cumplió el 100% de las instrucciones explícitas e implícitas del usuario?", body_style)],
        [Paragraph("3. Claridad y Estilo", body_style), Paragraph("10%", body_style), Paragraph("Estructura limpia, sin redundancias y tono profesional objetivo.", body_style)],
        [Paragraph("4. Seguridad (Safety)", body_style), Paragraph("5%", body_style), Paragraph("No generar contenido dañino, ilegal o que vulnere derechos de autor.", body_style)]
    ]
    t_rubric = Table(rubric_data, colWidths=[140, 50, 342])
    t_rubric.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_rubric)
    story.append(Spacer(1, 8))

    story.append(Paragraph("1.3 Estructura de la Justificación (El Secreto para no ser Despedido)", h2_style))
    story.append(Paragraph("En cada tarea debes escribir una justificación (Rationale). Las justificaciones mediocres de 1 línea causan suspensión. Usa siempre esta plantilla de 3 partes:", body_style))
    
    just_box = Table([
        [Paragraph("<b>PLANTILLA DE JUSTIFICACIÓN DE EVALUACIÓN (RATIONALE):</b><br/>"
                   "<i>1. Conclusión directa:</i> 'Model A is significantly better than Model B because it adheres to all negative constraints.'<br/>"
                   "<i>2. Análisis factual:</i> 'Model A accurately states that [hecho verificado en fuente primaria]. In contrast, Model B hallucinates by claiming that [error del modelo B], which is factually incorrect according to [fuente confiable].'<br/>"
                   "<i>3. Cumplimiento de formato:</i> 'Furthermore, Model A respected the 100-word limit (92 words), whereas Model B wrote 145 words, violating the prompt constraints.'", callout_style)]
    ], colWidths=[532])
    just_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#94A3B8")),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(just_box)
    story.append(Spacer(1, 14))

    # =======================================================
    # MÓDULO 2: CARTA DE PRESENTACIÓN ATS EN INGLÉS
    # =======================================================
    story.append(Paragraph("MÓDULO 2: PLANTILLA MAESTRA DE COVER LETTER (EN INGLÉS) PARA PUESTOS REMOTOS", h1_style))
    story.append(Paragraph("Las empresas extranjeras exigen una carta de presentación breve, cuantificable y directa. No cuentes tu vida; demuestra cómo resuelves sus necesidades operativas en 3 párrafos:", body_style))

    cl_text = (
        "<b>Subject:</b> Application for [Job Title - e.g. AI Data Trainer / Bilingual Virtual Assistant] - [Your Full Name]<br/><br/>"
        "Dear Hiring Team at [Company Name],<br/><br/>"
        "I am writing to express my strong interest in the [Job Title] role. With a rigorous background in [Your Field, e.g. research, content quality, or operations] and native-level fluency in Spanish paired with professional English proficiency (C1/B2), I specialize in delivering high-accuracy deliverables under tight deadlines with minimal supervision.<br/><br/>"
        "Throughout my professional experience, I have consistently focused on detail orientation and quality assurance. Specifically, I have:<br/>"
        "• Evaluated and refined complex datasets and text outputs with an accuracy rating exceeding 98%.<br/>"
        "• Maintained autonomous remote communication, resolving operational inquiries within 2 hours and adhering strictly to guidelines.<br/>"
        "• Adapted rapidly to proprietary tooling, LLM evaluation platforms, and CRM software, maintaining 100% on-time milestone delivery.<br/><br/>"
        "I am equipped with a dedicated high-speed home office setup (fiber optic internet, backup power, dual monitors) and available to commit [20 to 40] hours per week across flexible time zones. I welcome the opportunity to discuss how my analytical skills can contribute to [Company Name]'s ongoing milestones.<br/><br/>"
        "Sincerely,<br/>"
        "<b>[Your Full Name]</b><br/>"
        "[Your City, Country] | [Your LinkedIn URL] | [Your Telegram / WhatsApp]"
    )

    cl_box = Table([[Paragraph(cl_text, code_style)]], colWidths=[532])
    cl_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor("#0D9488")),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(cl_box)
    story.append(Spacer(1, 14))

    # =======================================================
    # MÓDULO 3: ENTREVISTAS EN VIDEO Y MÉTODO STAR
    # =======================================================
    story.append(Paragraph("MÓDULO 3: EL MÉTODO STAR PARA ENTREVISTAS EN VIDEO (HIREVUE / WILLO)", h1_style))
    story.append(Paragraph("En plataformas como Virtual Latinos, Centific o Appen, te pedirán grabar respuestas en video de 60 a 90 segundos. Aplica siempre la técnica <b>STAR</b> (Situation, Task, Action, Result):", body_style))

    star_data = [
        [Paragraph("<b>Fase STAR</b>", bold_style), Paragraph("<b>Tiempo</b>", bold_style), Paragraph("<b>Qué debes decir (Fórmula de Éxito)</b>", bold_style)],
        [Paragraph("<b>S</b>ituation (Situación)", body_style), Paragraph("15 seg", body_style), Paragraph("Contexto breve: <i>'En mi anterior proyecto remoto, teníamos una entrega urgente con pautas ambiguas...'</i>", body_style)],
        [Paragraph("<b>T</b>ask (Tarea)", body_style), Paragraph("15 seg", body_style), Paragraph("Tu responsabilidad exacta: <i>'Mi objetivo era auditar 150 registros garantizando cero margen de error.'</i>", body_style)],
        [Paragraph("<b>A</b>ction (Acción)", body_style), Paragraph("40 seg", body_style), Paragraph("Lo que hiciste tú (no tu equipo): <i>'Creé un checklist de verificación de 4 pasos, contrasté fuentes primarias y automaticé la validación de formato.'</i>", body_style)],
        [Paragraph("<b>R</b>esult (Resultado)", body_style), Paragraph("20 seg", body_style), Paragraph("Métrica final cuantificada: <i>'Completamos la entrega un día antes, logrando un 99.2% de precisión aprobada por el cliente.'</i>", body_style)]
    ]
    t_star = Table(star_data, colWidths=[120, 55, 357])
    t_star.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_star)
    story.append(Spacer(1, 10))

    # Checklist técnico de video
    story.append(Paragraph("Checklist Técnico para tu Grabación de Video:", h2_style))
    checklist_items = [
        "<b>Iluminación frontal:</b> Una lámpara o ventana frente a ti; nunca a contraluz detrás de tu cabeza.",
        "<b>Audio limpio:</b> Usa audífonos con micrófono cercano a la boca; el eco de habitación vacía descarta candidatos.",
        "<b>Contacto visual con la cámara:</b> Mira al lente de la cámara, no a tu propia cara en la pantalla.",
        "<b>Vestimenta sobria:</b> Camisa lisa o polo de cuello oscuro; transmite profesionalismo ejecutivo."
    ]
    for item in checklist_items:
        story.append(Paragraph(f"✓ {item}", body_style))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF generado exitosamente en: {filename}")

if __name__ == "__main__":
    dest1 = os.path.join(os.path.dirname(__file__), "Pack_Secreto_Admision_Remota_2026.pdf")
    dest2 = os.path.join(os.path.expanduser("~"), "Desktop", "Pack_Secreto_Admision_Remota_2026.pdf")
    build_pdf(dest1)
    import shutil
    try:
        shutil.copyfile(dest1, dest2)
        print(f"Copia creada en el Escritorio: {dest2}")
    except Exception as e:
        print(f"No se pudo copiar a Escritorio: {e}")
