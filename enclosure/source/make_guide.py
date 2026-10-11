"""Readable Spanish assembly PDF, illustrations from actual rendered CAD."""
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
R=Path(__file__).resolve().parents[1]
pdfmetrics.registerFont(TTFont('ManropeBold',str(R/'source/Manrope-Bold.ttf')))
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='FSH',fontName='ManropeBold',fontSize=25,leading=30,textColor=colors.HexColor('#17262e'),spaceAfter=14))
styles.add(ParagraphStyle(name='FSS',fontName='ManropeBold',fontSize=13,leading=18,textColor=colors.HexColor('#177e75'),spaceBefore=13,spaceAfter=7))
styles.add(ParagraphStyle(name='FSB',fontName='Helvetica',fontSize=10,leading=15,textColor=colors.HexColor('#243840'),spaceAfter=8))
story=[]
def p(t,style='FSB'):story.append(Paragraph(t,styles[style]))
def pic(path,width=480):
    im=ImageReader(str(path));w,h=im.getSize();story.append(Image(str(path),width=width,height=width*h/w));story.append(Spacer(1,9))
def table(rows,widths):
    rows=[[Paragraph(str(v),styles['FSB']) for v in row] for row in rows]
    t=Table(rows,colWidths=widths,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e0f3ef')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#bdcfcd')),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),7)]));story.append(t)
p('FlowSight Desk','FSH')
p('Carcasa imprimible para tu pantalla externa FlowSight. Cuerpo grafito, marca turquesa, cierre trasero y soporte de escritorio a 65 grados.')
pic(R/'preview/FlowSight-Desk-front.png',455)
p('Render del modelo CAD real. La pantalla muestra una captura de demostración del firmware; no es una fotografía de un producto fabricado.')
p('104 × 78 × 25,2 mm · Base 90 × 64 mm · PETG · Tornillería M3 / M2,5','FSS')
p('La CS-32 N4XX aún necesita una prueba física de encaje. Su perfil eléctrico no demuestra el tamaño de la placa. Imprime primero la plantilla pequeña antes de una carcasa completa o de fabricar un lote.')
story.append(PageBreak())
p('Elegir e imprimir','FSH')
table([['Unidad','Referencia y archivo'],['CS-32 N4XX actual','Referencia 024: placa 74,4 × 42,9 mm, agujeros 68 × 36,5 mm. FlowSight_Desk_CS32_024_reference.3mf'],['CYD 2,8 pulgadas','Referencia 028: placa hasta 86,6 × 50 mm, agujeros 78 × 42 mm. FlowSight_Desk_CYD_028.3mf']],[120,360])
p('Primero, la plantilla de encaje','FSS')
p('Imprime Fit_check_CS32_024_reference.stl para comprobar la unidad actual. Si la placa es la de 2,8 pulgadas, prueba Fit_check_CYD_028.stl. Verifica los cuatro agujeros y que la ventana deja ver toda el área activa. La plantilla consume aproximadamente 5–6 g de PETG.')
p('Ajustes iniciales','FSS')
table([['Ajuste','Recomendación'],['Material / boquilla','PETG mate grafito / 0,4 mm'],['Capas / paredes','0,20 mm / cuatro perímetros / cinco capas arriba y abajo'],['Relleno','20 % gyroid; base 25–30 %'],['Escala / soportes','100 %, milímetros. Orientación ya incluida. Sin soportes previstos; revisar las capas del laminador.'],['Cama','Disposición de 214 × 148 mm. Separar las piezas si hay una zona de exclusión.']],[120,360])
p('Los 3MF contienen cuatro piezas: frontal, tapa, registro de servicio y base. Cada frontal usa su propio patrón de anclajes. No combines ambos frontales. No se incluye G-code porque depende de la impresora y del filamento.')
p('Marca FlowSight','FSS')
p('Símbolo oficial y nombre grabados a 0,6 mm. Una impresora de un solo material puede imprimir el frontal grafito y rellenar el grabado con pintura turquesa. La alternativa multimaterial es Brand_inlay_optional.stl; consultar la posición exacta en README.md.')
story.append(PageBreak())
p('Montaje','FSH')
pic(R/'preview/FlowSight-Desk-exploded.png',420)
p('Vista de piezas separadas. La placa y el LCD se muestran como componentes ilustrativos; las piezas de la carcasa proceden de los STL finales.')
table([['Cantidad','Componente'],['4 + 4','Insertos M3 de 4,6 × 5 mm y tornillos M3 × 8 mm para la tapa.'],['6','Insertos M2,5 de 3,5 × 3 mm: cuatro del PCB, dos del registro.'],['4 + 2','Tornillos M2,5 × 4 mm para PCB y M2,5 × 8 mm para registro; cabeza baja.'],['4','Pies adhesivos de goma de 10 mm y 1,5–2 mm de grosor.']],[75,405])
story.append(PageBreak())
p('Terminar la primera unidad','FSH')
p('<b>1.</b> Instala los insertos con la electrónica fuera. Comprueba diámetro y longitud; ajusta los pilotos si tu marca de insertos difiere.')
p('<b>2.</b> Coloca el PCB en los cuatro postes. No presiones el cristal con el frontal. Usa separadores uniformes si necesitas más altura y comprueba que la placa no flexiona al sujetarla.')
p('<b>3.</b> Prueba touch, USB y alcance del cable. El hueco es de 20 × 13 mm; una funda de conector de hasta 18 × 11 mm deja holgura. La posición del USB puede variar entre revisiones.')
p('<b>4.</b> Atornilla la tapa y el registro de servicio. El registro se desmonta para acceder a BOOT, RESET y conectores internos. La base es una cuna desmontable por gravedad.')
p('<b>5.</b> Coloca los pies y comprueba estabilidad al tocar la pantalla. Tras elegir la placa y el cable definitivos, valida también el montaje y la temperatura de uso antes de fabricar un lote.')
pic(R/'preview/FlowSight-Desk-rear.png',385)
p('Archivos editables','FSS')
p('Los STEP de conjunto se encuentran en la carpeta enclosure y los STEP de piezas en source. El diseño paramétrico original es source/build.py y source/parameters.json. README.md incluye reproducción, tolerancias y montaje detallado.')

def footer(c,doc):
    c.setStrokeColor(colors.HexColor('#55cec1'));c.line(42,35,553,35)
    c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#52686b'));c.drawString(42,23,'FlowSight Desk · Guía de impresión y montaje · 1.0');c.drawRightString(553,23,str(doc.page))
doc=SimpleDocTemplate(str(R/'FlowSight-Desk-guia.pdf'),pagesize=(595.28,841.89),rightMargin=50,leftMargin=50,topMargin=42,bottomMargin=48,title='FlowSight Desk - impresión y montaje',author='FlowSight')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print('PDF assembly guide generated.')
