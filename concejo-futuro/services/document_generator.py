"""Generador de documentos legislativos en PDF — WeasyPrint + Jinja2."""

import logging
from datetime import datetime

logger = logging.getLogger("services.document_generator")

ROLES_LABEL = {
    "concejal": "Concejal Municipal",
    "presidente_concejo": "Presidente del Concejo",
    "alcalde": "Alcalde Proponente",
    "sec_planeacion": "Secretario/a de Planeación",
    "contralor": "Contralor/a Municipal",
    "personero": "Personero/a Municipal",
    "lider_campesino": "Líder Campesino/a",
    "diputado": "Diputado/a Departamental",
    "gobernador": "Gobernador/a Departamental",
}

_PONENCIA_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  @page {
    size: A4 portrait;
    margin: 2.5cm 2.5cm 3cm 2.5cm;
    @bottom-center {
      content: "Página " counter(page) " de " counter(pages);
      font-size: 9pt; color: #888;
    }
  }
  body {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 11pt;
    line-height: 1.65;
    color: #1a1a1a;
    background: #FAFAF5;
  }
  .header-band {
    background: #1B5E20;
    color: #fff;
    padding: 14px 20px 10px;
    margin-bottom: 0;
  }
  .header-band h1 {
    font-size: 13pt;
    font-weight: bold;
    margin: 0 0 2px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }
  .header-band .subtitulo {
    font-size: 10pt;
    font-weight: normal;
    opacity: 0.88;
    margin: 0;
  }
  .meta-band {
    background: #E8F5E9;
    border-left: 4px solid #1B5E20;
    padding: 10px 20px;
    margin-bottom: 22px;
    font-size: 9.5pt;
    color: #2E7D32;
  }
  .meta-band table { width: 100%; border-collapse: collapse; }
  .meta-band td { padding: 1px 6px 1px 0; vertical-align: top; }
  .meta-band td:first-child { font-weight: bold; width: 160px; }
  .tipo-doc {
    text-align: center;
    font-size: 14pt;
    font-weight: bold;
    color: #1B5E20;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin: 0 0 4px;
    padding-top: 18px;
  }
  .tipo-doc-sub {
    text-align: center;
    font-size: 10pt;
    color: #555;
    margin: 0 0 22px;
  }
  .divider {
    border: none;
    border-top: 1.5px solid #1B5E20;
    margin: 16px 0;
  }
  .section-title {
    font-size: 10pt;
    font-weight: bold;
    color: #1B5E20;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin: 20px 0 6px;
    border-bottom: 1px solid #C8E6C9;
    padding-bottom: 2px;
  }
  .ponencia-body {
    text-align: justify;
    white-space: pre-wrap;
  }
  .firma-block {
    margin-top: 50px;
    display: flex;
    justify-content: flex-end;
  }
  .firma-inner {
    text-align: center;
    min-width: 260px;
  }
  .firma-linea {
    border-top: 1px solid #333;
    margin-bottom: 4px;
  }
  .firma-nombre { font-weight: bold; font-size: 10.5pt; }
  .firma-cargo { font-size: 9.5pt; color: #555; }
  .folio {
    margin-top: 30px;
    font-size: 8.5pt;
    color: #999;
    text-align: right;
  }
</style>
</head>
<body>

<div class="header-band">
  <h1>{{ evento_nombre }}</h1>
  <p class="subtitulo">{{ proyecto_nombre }}</p>
</div>

<div class="meta-band">
  <table>
    <tr>
      <td>Fecha:</td>
      <td>{{ fecha }}</td>
      <td style="width:20px"></td>
      <td>Radicado:</td>
      <td>PON-{{ folio }}</td>
    </tr>
    <tr>
      <td>Ponente:</td>
      <td>{{ nombre_completo }}</td>
      <td></td>
      <td>Cargo:</td>
      <td>{{ rol_label }}</td>
    </tr>
    <tr>
      <td>Bancada / Sector:</td>
      <td>{{ bancada_nombre }}</td>
      <td></td>
      <td>Municipio:</td>
      <td>{{ municipio }}{% if provincia %}, {{ provincia }}{% endif %}</td>
    </tr>
  </table>
</div>

<p class="tipo-doc">Ponencia</p>
<p class="tipo-doc-sub">Presentada ante {{ evento_nombre }}</p>

<hr class="divider">

<div class="section-title">Texto de la ponencia</div>
<div class="ponencia-body">{{ contenido }}</div>

<div class="firma-block">
  <div class="firma-inner">
    <div class="firma-linea"></div>
    <div class="firma-nombre">{{ nombre_completo }}</div>
    <div class="firma-cargo">{{ rol_label }}</div>
    {% if bancada_nombre %}<div class="firma-cargo">{{ bancada_nombre }}</div>{% endif %}
    <div class="firma-cargo">{{ municipio }}{% if provincia %}, {{ provincia }}{% endif %}</div>
  </div>
</div>

<div class="folio">Documento generado por TavoDebate · {{ fecha }} · Folio PON-{{ folio }}</div>

</body>
</html>
"""

_PROPUESTA_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  @page {
    size: A4 portrait;
    margin: 2.5cm 2.5cm 3cm 2.5cm;
    @bottom-center {
      content: "Página " counter(page) " de " counter(pages);
      font-size: 9pt; color: #888;
    }
  }
  body {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 11pt;
    line-height: 1.65;
    color: #1a1a1a;
    background: #FAFAF5;
  }
  .header-band {
    background: #1B5E20;
    color: #fff;
    padding: 14px 20px 10px;
  }
  .header-band h1 {
    font-size: 13pt;
    font-weight: bold;
    margin: 0 0 2px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .header-band .subtitulo { font-size: 10pt; opacity: 0.88; margin: 0; }
  .meta-band {
    background: #E8F5E9;
    border-left: 4px solid #1B5E20;
    padding: 10px 20px;
    margin-bottom: 22px;
    font-size: 9.5pt;
    color: #2E7D32;
  }
  .meta-band table { width: 100%; border-collapse: collapse; }
  .meta-band td { padding: 1px 6px 1px 0; vertical-align: top; }
  .meta-band td:first-child { font-weight: bold; width: 160px; }
  .tipo-doc {
    text-align: center;
    font-size: 14pt;
    font-weight: bold;
    color: #1B5E20;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin: 0 0 4px;
    padding-top: 18px;
  }
  .tipo-doc-sub { text-align: center; font-size: 10pt; color: #555; margin: 0 0 22px; }
  .divider { border: none; border-top: 1.5px solid #1B5E20; margin: 16px 0; }
  .section-title {
    font-size: 10pt;
    font-weight: bold;
    color: #1B5E20;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin: 20px 0 6px;
    border-bottom: 1px solid #C8E6C9;
    padding-bottom: 2px;
  }
  .propuesta-box {
    background: #F1F8E9;
    border: 1px solid #A5D6A7;
    border-left: 4px solid #1B5E20;
    padding: 16px 20px;
    text-align: justify;
    white-space: pre-wrap;
    margin: 10px 0;
  }
  .articulo-badge {
    display: inline-block;
    background: #1B5E20;
    color: #fff;
    padding: 2px 10px;
    font-size: 9.5pt;
    font-weight: bold;
    border-radius: 3px;
    margin-bottom: 10px;
  }
  .apoyos {
    margin-top: 14px;
    font-size: 10pt;
    color: #555;
  }
  .firma-block { margin-top: 50px; display: flex; justify-content: flex-end; }
  .firma-inner { text-align: center; min-width: 260px; }
  .firma-linea { border-top: 1px solid #333; margin-bottom: 4px; }
  .firma-nombre { font-weight: bold; font-size: 10.5pt; }
  .firma-cargo { font-size: 9.5pt; color: #555; }
  .folio { margin-top: 30px; font-size: 8.5pt; color: #999; text-align: right; }
</style>
</head>
<body>

<div class="header-band">
  <h1>{{ evento_nombre }}</h1>
  <p class="subtitulo">{{ proyecto_nombre }}</p>
</div>

<div class="meta-band">
  <table>
    <tr>
      <td>Fecha:</td>
      <td>{{ fecha }}</td>
      <td style="width:20px"></td>
      <td>Radicado:</td>
      <td>ENM-{{ propuesta_id }}</td>
    </tr>
    <tr>
      <td>Proponente:</td>
      <td>{{ nombre_completo }}</td>
      <td></td>
      <td>Cargo:</td>
      <td>{{ rol_label }}</td>
    </tr>
    <tr>
      <td>Bancada / Sector:</td>
      <td>{{ bancada_nombre }}</td>
      <td></td>
      <td>Municipio:</td>
      <td>{{ municipio }}{% if provincia %}, {{ provincia }}{% endif %}</td>
    </tr>
  </table>
</div>

<p class="tipo-doc">Propuesta de Enmienda N.º {{ propuesta_id }}</p>
<p class="tipo-doc-sub">Al {{ proyecto_nombre }}</p>

<hr class="divider">

{% if articulo_afectado %}
<div class="section-title">Artículo objeto de la enmienda</div>
<span class="articulo-badge">{{ articulo_afectado }}</span>
{% endif %}

<div class="section-title">Texto de la propuesta</div>
<div class="propuesta-box">{{ texto_propuesta }}</div>

<div class="apoyos">Apoyos registrados: <strong>{{ apoyos }}</strong></div>

<div class="firma-block">
  <div class="firma-inner">
    <div class="firma-linea"></div>
    <div class="firma-nombre">{{ nombre_completo }}</div>
    <div class="firma-cargo">{{ rol_label }}</div>
    {% if bancada_nombre %}<div class="firma-cargo">{{ bancada_nombre }}</div>{% endif %}
    <div class="firma-cargo">{{ municipio }}{% if provincia %}, {{ provincia }}{% endif %}</div>
  </div>
</div>

<div class="folio">Documento generado por TavoDebate · {{ fecha }} · Folio ENM-{{ propuesta_id }}</div>

</body>
</html>
"""


def _to_pdf(html: str) -> bytes:
    try:
        import weasyprint
        return weasyprint.HTML(string=html).write_pdf()
    except ImportError:
        raise RuntimeError(
            "WeasyPrint no está instalado. Agrega 'weasyprint>=62.0' a requirements.txt "
            "y reconstruye el contenedor."
        )


def _render(template_str: str, context: dict) -> str:
    try:
        from jinja2 import Template
    except ImportError:
        raise RuntimeError("Jinja2 no está instalado. Agrega 'jinja2>=3.1' a requirements.txt.")
    return Template(template_str).render(**context)


def render_ponencia_pdf(user: dict, evento: dict, contenido: str) -> bytes:
    fecha = datetime.now().strftime("%d de %B de %Y")
    folio = f"{datetime.now().strftime('%Y%m%d')}-{user.get('id', 0):04d}"
    ctx = {
        "evento_nombre": evento.get("nombre", "Cuerpo Legislativo"),
        "proyecto_nombre": evento.get("proyecto_nombre", "Proyecto de Acuerdo"),
        "nombre_completo": user.get("nombre_completo", ""),
        "rol_label": ROLES_LABEL.get(user.get("rol", ""), user.get("rol", "")),
        "bancada_nombre": user.get("bancada_nombre", ""),
        "municipio": user.get("municipio", ""),
        "provincia": user.get("provincia", ""),
        "contenido": contenido,
        "fecha": fecha,
        "folio": folio,
    }
    html = _render(_PONENCIA_TEMPLATE, ctx)
    return _to_pdf(html)


def render_propuesta_pdf(user: dict, evento: dict, propuesta: dict) -> bytes:
    fecha = datetime.now().strftime("%d de %B de %Y")
    ctx = {
        "evento_nombre": evento.get("nombre", "Cuerpo Legislativo"),
        "proyecto_nombre": evento.get("proyecto_nombre", "Proyecto de Acuerdo"),
        "propuesta_id": propuesta.get("id", 0),
        "nombre_completo": user.get("nombre_completo", ""),
        "rol_label": ROLES_LABEL.get(user.get("rol", ""), user.get("rol", "")),
        "bancada_nombre": user.get("bancada_nombre", ""),
        "municipio": user.get("municipio", ""),
        "provincia": user.get("provincia", ""),
        "texto_propuesta": propuesta.get("texto_propuesta", ""),
        "articulo_afectado": propuesta.get("articulo_afectado", ""),
        "apoyos": propuesta.get("apoyos", 1),
        "fecha": fecha,
    }
    html = _render(_PROPUESTA_TEMPLATE, ctx)
    return _to_pdf(html)
