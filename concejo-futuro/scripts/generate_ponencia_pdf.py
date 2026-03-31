"""Genera el PDF de presentación del proyecto SIADR."""

import os
from fpdf import FPDF

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "static", "ponencia_siadr.pdf")

# Colors
DARK_GREEN = (30, 80, 30)
WHITE = (255, 255, 255)
LIGHT_BG = (245, 245, 240)
ACCENT = (46, 125, 50)
RED_ACCENT = (198, 40, 40)
BLUE_ACCENT = (25, 118, 210)
GOLD = (180, 140, 20)


class PonenciaPDF(FPDF):
    def slide_bg(self, color=LIGHT_BG):
        self.set_fill_color(*color)
        self.rect(0, 0, 297, 210, "F")

    def green_header(self, text, y=10):
        self.set_fill_color(*DARK_GREEN)
        self.rect(0, y, 297, 28, "F")
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 22)
        self.set_y(y + 5)
        self.cell(0, 18, text, align="C")
        self.set_text_color(0, 0, 0)

    def subtitle(self, text, y=42):
        self.set_font("Helvetica", "", 13)
        self.set_text_color(80, 80, 80)
        self.set_y(y)
        self.cell(0, 8, text, align="C")
        self.set_text_color(0, 0, 0)

    def bullet(self, text, x=30, bold_prefix=""):
        self.set_x(x)
        if bold_prefix:
            self.set_font("Helvetica", "B", 13)
            self.cell(self.get_string_width(bold_prefix) + 2, 8, bold_prefix)
            self.set_font("Helvetica", "", 13)
            self.cell(0, 8, text)
            self.ln(9)
        else:
            self.set_font("Helvetica", "", 13)
            self.cell(0, 8, f"  {text}")
            self.ln(9)

    def big_number(self, number, label, x, y, color=ACCENT):
        self.set_xy(x, y)
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(*color)
        self.cell(60, 14, number, align="C")
        self.set_xy(x, y + 16)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(60, 60, 60)
        self.cell(60, 8, label, align="C")
        self.set_text_color(0, 0, 0)


def generate():
    pdf = PonenciaPDF(orientation="L", format="A4")
    pdf.set_auto_page_break(False)

    # === SLIDE 1: PORTADA ===
    pdf.add_page()
    pdf.slide_bg(DARK_GREEN)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_y(50)
    pdf.cell(0, 20, "Proyecto de Acuerdo 001-2026", align="C")
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_y(75)
    pdf.cell(0, 16, "SIADR", align="C")
    pdf.set_font("Helvetica", "", 16)
    pdf.set_y(95)
    pdf.cell(0, 12, "Sistema Inteligente de Asignacion de Recursos", align="C")
    pdf.set_y(108)
    pdf.cell(0, 12, "para el Desarrollo Rural", align="C")
    pdf.set_y(135)
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 10, "Gran Concejo del Futuro de Cundinamarca", align="C")
    pdf.set_y(150)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, "Gobernacion de Cundinamarca  |  2026", align="C")
    pdf.set_text_color(0, 0, 0)

    # === SLIDE 2: EL PROBLEMA ===
    pdf.add_page()
    pdf.slide_bg()
    pdf.green_header("1. EL PROBLEMA")
    pdf.subtitle("Las decisiones de inversion rural se toman sin datos")

    pdf.set_y(58)
    pdf.set_font("Helvetica", "", 13)

    problems = [
        ("68%", "de veredas rurales SIN internet"),
        ("Censo 2014", "datos agropecuarios de hace 10+ anos"),
        ("2 agronomos", "para 116 municipios del departamento"),
        ("200 luminarias/ano", "maximo por municipio con presupuesto actual"),
    ]

    y = 62
    for num, desc in problems:
        pdf.set_xy(30, y)
        pdf.set_font("Helvetica", "B", 15)
        pdf.set_text_color(*RED_ACCENT)
        pdf.cell(50, 10, num)
        pdf.set_font("Helvetica", "", 13)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 10, desc)
        y += 18

    pdf.set_xy(30, y + 10)
    pdf.set_fill_color(255, 240, 240)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*RED_ACCENT)
    pdf.cell(237, 14, "  Resultado: los recursos llegan donde hay mas votos, no donde hay mas necesidad", fill=True)
    pdf.set_text_color(0, 0, 0)

    # === SLIDE 3: LA PROPUESTA ===
    pdf.add_page()
    pdf.slide_bg()
    pdf.green_header("2. LA PROPUESTA: SIADR")
    pdf.subtitle("Inteligencia artificial para priorizar inversion rural con datos objetivos")

    # Componente 1
    pdf.set_xy(20, 58)
    pdf.set_fill_color(230, 245, 230)
    pdf.rect(20, 58, 125, 80, "F")
    pdf.set_xy(25, 60)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 10, "Componente 1: Alumbrado Rural")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 12)
    items1 = [
        "Luminarias inteligentes para veredas",
        "Priorizacion por densidad poblacional",
        "Tasa de criminalidad nocturna",
        "Condicion de infraestructura vial",
        "Cobertura actual de iluminacion",
    ]
    y = 74
    for item in items1:
        pdf.set_xy(30, y)
        pdf.cell(0, 8, f"* {item}")
        y += 10

    # Componente 2
    pdf.set_xy(152, 58)
    pdf.set_fill_color(225, 240, 255)
    pdf.rect(152, 58, 125, 80, "F")
    pdf.set_xy(157, 60)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*BLUE_ACCENT)
    pdf.cell(0, 10, "Componente 2: Agricultura de Precision")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 12)
    items2 = [
        "90 estaciones de sensores IoT",
        "Datos climaticos en tiempo real",
        "Analisis de suelos",
        "Optimizacion de productividad",
        "480 familias/municipio beneficiadas",
    ]
    y = 74
    for item in items2:
        pdf.set_xy(162, y)
        pdf.cell(0, 8, f"* {item}")
        y += 10

    # === SLIDE 4: CIFRAS CLAVE ===
    pdf.add_page()
    pdf.slide_bg()
    pdf.green_header("3. CIFRAS CLAVE")

    pdf.big_number("$2.400M", "Inversion total (COP)", 15, 50, ACCENT)
    pdf.big_number("30", "Municipios piloto", 85, 50, BLUE_ACCENT)
    pdf.big_number("10.200", "Familias beneficiadas", 155, 50, ACCENT)
    pdf.big_number("2.550", "Luminarias", 225, 50, GOLD)

    pdf.big_number("13.500 ha", "Con agrotecnologia", 50, 95, ACCENT)
    pdf.big_number("90", "Estaciones IoT", 145, 95, BLUE_ACCENT)
    pdf.big_number("15", "Provincias", 225, 95, ACCENT)

    # Financiación
    pdf.set_xy(30, 140)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Financiacion:")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_xy(30, 152)
    pdf.cell(0, 8, "* SGP (Sistema General de Participaciones)")
    pdf.set_xy(30, 162)
    pdf.set_text_color(*RED_ACCENT)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "* $1.200M en regalias (VENCEN el 30 de junio de 2026)")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_xy(30, 172)
    pdf.cell(0, 8, "* Cooperacion internacional")

    # === SLIDE 5: LOS 5 ARTÍCULOS ===
    pdf.add_page()
    pdf.slide_bg()
    pdf.green_header("4. LOS 5 ARTICULOS DEL PROYECTO")

    articles = [
        ("Art. 1:", "Creacion del SIADR para priorizacion de alumbrado rural + agricultura de precision"),
        ("Art. 2:", "Variables del algoritmo: densidad, criminalidad, productividad, clima, infraestructura"),
        ("Art. 3:", "Financiacion y sostenibilidad - plan a 5 anos con clausula de reversion (20%)"),
        ("Art. 4:", "Transparencia algoritmica - publicacion trimestral + auditoria externa obligatoria"),
        ("Art. 5:", "Participacion ciudadana - consultas digitales Y presenciales en zonas rurales"),
    ]

    y = 55
    for art_num, art_text in articles:
        pdf.set_xy(25, y)
        pdf.set_fill_color(230, 245, 230)
        pdf.rect(25, y, 247, 22, "F")
        pdf.set_xy(30, y + 3)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*ACCENT)
        pdf.cell(40, 8, art_num)
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(200, 8, art_text)
        pdf.set_text_color(0, 0, 0)
        y += 28

    # === SLIDE 6: POR QUÉ APROBAR + RIESGOS ===
    pdf.add_page()
    pdf.slide_bg()
    pdf.green_header("5. POR QUE APROBAR + RIESGOS")

    # Left: pros
    pdf.set_fill_color(230, 248, 230)
    pdf.rect(15, 48, 130, 110, "F")
    pdf.set_xy(20, 50)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 10, "A FAVOR")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 11)
    pros = [
        "Decisiones por datos, no clientelismo",
        "Transparencia total - codigo abierto",
        "$1.200M en regalias se pierden en junio",
        "30 municipios piloto = prueba controlada",
        "UMATA como puente con campesinos",
        "Codigo abierto + capacitacion gratuita",
    ]
    y = 64
    for p in pros:
        pdf.set_xy(22, y)
        pdf.cell(0, 8, f"+ {p}")
        y += 11

    # Right: risks
    pdf.set_fill_color(255, 235, 230)
    pdf.rect(152, 48, 130, 110, "F")
    pdf.set_xy(157, 50)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*RED_ACCENT)
    pdf.cell(0, 10, "RIESGOS")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 11)
    risks = [
        "32% de internet rural (se necesita offline)",
        "Datos del censo de 2014 (desactualizados)",
        "Solo 2 agronomos para 116 municipios",
        "Costos de mantenimiento a largo plazo",
        "Brecha digital: 68% rural sin conexion",
        "Riesgo ambiental: baterias en acuiferos",
    ]
    y = 64
    for r in risks:
        pdf.set_xy(157, y)
        pdf.cell(0, 8, f"! {r}")
        y += 11

    # Bottom question
    pdf.set_xy(30, 170)
    pdf.set_fill_color(*DARK_GREEN)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 14)
    pdf.rect(30, 168, 237, 18, "F")
    pdf.cell(237, 14, "Seguimos decidiendo por clientelismo o dejamos que los datos hablen?", align="C")
    pdf.set_text_color(0, 0, 0)

    # Save
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    pdf.output(OUTPUT)
    print(f"PDF generated: {OUTPUT}")
    print(f"Pages: {pdf.pages_count}")


if __name__ == "__main__":
    generate()
