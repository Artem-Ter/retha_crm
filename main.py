import json
from datetime import datetime as dt
from hmac import compare_digest

import aiofiles.os
import fasthtml.common as fh
import pandas as pd
from components import (autocomplete_field, carousel, fltr_flds, get_dialog,
                        map_comparisons_script, map_locations_script, mk_fltr,
                        module_form, ppt_serializer, short_fltr, slct_fld)
from const import (ABOUT_BGD, AD_TYPE, ADDRESS_FLDS, BODY_BGD, CMP_MODIFY,
                   CMP_RENAME, COSTS, COVER_BGD, DESCR, FILTER_FLDS,
                   FLDS_MODIFICATIONS, FLDS_RENAME, LAST_PAGE_BGD, LR_PADDING,
                   NA, PAGE_HEIGHT, PAGE_WIDTH, PPT_TYPE, RENAME, SLCT_FLD,
                   TOP_PADDING, ZERO, ZONE, static_map_image)
from mysettings import (GOOGLE_API, PDF_DIR, AdType, Comparison, Property,
                        PropertyInfrastructure, Role, Status, User, cities,
                        comparison_modules, comparisons, db, districts,
                        infrastructures, modules, ppt_images,
                        ppt_infrastructures, properties, regions, streets,
                        tasks, users)
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from starlette.background import BackgroundTask
from utils import get_or_create, save_img

hdrs = [
    fh.Link(href='/css/main.css', rel='stylesheet'),
]
login_redir = fh.RedirectResponse('/login', status_code=303)

# The `before` function is a *Beforeware* function. These are functions that run before a route handler is called.
def before(req, sess):
    auth = req.scope['auth'] = sess.get('auth', None)
    if not auth: return login_redir

bware = fh.Beforeware(before, skip=[r'/favicon\.ico', r'/static/.*', r'.*\.css', '/login', '/', '/cls_dialog', '/register'])

bodykw = {"class": "relative bg-black font-geist text-black/80 font-details-off"}

app, rt = fh.fast_app(before=bware, hdrs=hdrs, bodykw=bodykw, live=True, debug=True)
app.mount('/pdfs', fh.StaticFiles(directory='./pdfs'), name='pdfs')
app.mount('/images', fh.StaticFiles(directory='./images'), name='images')

@app.get('/clr_fltr')
def clr_fltr():
    frm = short_fltr()
    return fh.Div(frm, hx_swap_oob='true', id='search-section')

@app.post('/cls_fltr')
def cls_fltr(d: dict):
    frm = short_fltr()
    frm = fh.fill_form(frm, d)
    return fh.Div(frm, hx_swap_oob='true', id='search-section')

@app.get('/cls_dialog')
def cls_dialog():
    return fh.Div(hx_swap_oob='true', id='dialog')

@app.get("/login")
def login_form():
    frm = fh.Form(
        fh.Input(id='email', type='email', placeholder='Email', required=True),
        fh.Input(id='pwd', type='password', placeholder='Password', required=True),
        fh.Button('Login', type='submit', hx_post='/login'),  # Swap dialog on submit
        fh.P(fh.Small("Don't have an account yet?")),
        fh.Button('Register', hx_get='/register', hx_swap='outerHTML', hx_target='#dialog'),
        id='login-form'
    )
    return get_dialog('Login', frm)
# , fh.Script("document.getElementById('login-section').close();")

def admin_view():
    return fh.Div(
        fh.Button('+ Primeiro Atendimento', hx_get='/task_frm', hx_target='#dialog'),
        hx_swap_oob='true',
        id='body'
    )

@app.get('/task_frm')
def get_task_frm():
    frm = fh.Form(
        fh.Input(name='broker', placeholder='Corretor'),
        fltr_flds(),
        fh.Button('Salvar e ver opcoes', type='submit', hx_post='/search_ppts', hx_target='#result')
    )
    return get_dialog('Tarefa', frm)
    
@fh.dataclass
class Login: email:str; pwd:str

@app.post("/login")
def login(login:Login, sess):
    if not login.email or not login.pwd: return login_redir
    try:
        u = users[login.email]
    # If the primary key does not exist, the method raises a `NotFoundError`.
    except fh.NotFoundError:
        return fh.P("User doesn't exist. Please register.")
    # This compares the passwords using a constant time string comparison
    # https://sqreen.github.io/DevelopersSecurityBestPractices/timing-attack/python
    if not compare_digest(u.pwd.encode("utf-8"), login.pwd.encode("utf-8")): return login_redir
    # Because the session is signed, we can securely add information to it. It's stored in the browser cookies.
    # If you don't pass a secret signing key to `FastHTML`, it will auto-generate one and store it in a file `./sesskey`.
    sess['auth'] = u.email
    sess['auth_r'] = u.role
    role_views = {
        Role.ADMIN: admin_view
    }
    return fh.P(
        fh.Strong(
            fh.AX("Logout", hx_get="/logout", hx_swap='outerHTML', hx_target="#login-section")
        ), id="login-section", hx_swap_oob='true'
    ), fh.Div(id='dialog', hx_swap_oob='true'), role_views.get(u.role)()

@app.get('/register')
def get_register():
    frm = fh.Form(
        fh.Input(id='name', type='name', placeholder='Nome', required=True),
        fh.Input(id='email', type='email', placeholder='Email', required=True),
        fh.Input(id='phone', type='phone', placeholder='Cellular', required=True),
        fh.Input(id='organization', type='organization', placeholder='Empresa', required=True),
        fh.Input(id='pwd', type='password', placeholder='Password', required=True),
        fh.Button('Register', type='submit', hx_post='/register'),  # Swap dialog on submit
        id='login-form'
    )
    return get_dialog('Cadastrar', frm)

@app.post('/register')
def register(sess, user:User):
    u = users.insert(user)
    sess['auth'] = u.email
    sess['auth_r'] = u.role
    return fh.P(
        fh.Strong(
            fh.AX("Logout", hx_get="/logout", hx_swap='outerHTML', hx_target="#login-section")
        ), id="login-section", hx_swap_oob='true'
    ), fh.Div(id='dialog', hx_swap_oob='true')

@app.get("/logout")
def logout(sess):
    del sess['auth']
    return fh.P(fh.Strong(fh.AX("Login", hx_get="/login", hx_swap='outerHTML', hx_target='#dialog')), id="login-section")

@app.get('/ppt_form')
async def ppt_form():
    infras = [d['name'] for d in infrastructures()]
    frm = fh.Form(
        slct_fld('type', PPT_TYPE),
        fh.CheckboxX(name='in_conodminium', role='switch', label='Em condomínio'),
        fh.Input(name='name', placeholder='Nome de Condominio / Monousuário'),
        fh.CheckboxX(name='on_site', role='switch', label='Publicar no Site'),
        fh.CheckboxX(name='retha_admin', role='switch', label='Administração Retha'),
        fh.CheckboxX(name='under_construction', role='switch', label='Em construção'),
        *(fh.Input(name=k, placeholder=v) for k, v in COSTS.items()),
        fh.Grid(*(fh.Input(name=k, placeholder=v) for k, v in ADDRESS_FLDS.items())),
        slct_fld('zone', ZONE),
        fh.Textarea(name='description', placeholder='Descrição', rows=10),
        fh.Label('Fotos:', _for='images'),
        fh.Input(name='images', type='file', multiple=True),
        autocomplete_field('infrastructure', infras, 'Infraestrutura', multiple=True),
        # fh.Input(name='infrastructure', placeholder='Infraestrutura'),
        fh.Input(name='location', placeholder='Localização'),
        fh.Button('Salva e Sai', type='submit', name='action', value='save_exit'),
        fh.Button('Adiciona modulos', type='submit', name='action', value='add_modules'),
        hx_post='/ppt_form',
    )
    return get_dialog('Cadastro do Imóvel', frm)

@app.post('/ppt_form')
async def add_ppt(frm: dict):
    d = {
        'street': 'streets',
        'district': 'districts',
        'city': 'cities',
        'region': 'regions',
    }
    action = frm.pop('action')  # Retrieve the action from the form submission
    infra = frm.pop('infrastructure')
    del frm['infrastructure_input']
    
    ppt_imgs = frm.get('images')
    if ppt_imgs:
        del frm['images']
    adrs = {f'{k}_id': get_or_create(v, frm.pop(k)) for k, v in d.items()}
    
    for k, v in frm.items():
        f = Property.__annotations__[k]
        try:
            frm[k] = f(v)
        except ValueError:
            frm[k] = None
    frm.update(adrs)
    
    cur_ppt = properties.insert(frm)
    if ppt_imgs:
        try:
            for img in ppt_imgs:
                await save_img(cur_ppt.id, img)
        except TypeError:
            await save_img(cur_ppt.id, ppt_imgs)
    if infra:
        for i in infra:
            idx = get_or_create('infrastructures', i)
            ppt_infrastructures.insert({'ppt_id': cur_ppt.id,
                                        'infr_id': idx})
    if action == 'save_exit':
        return cls_dialog()
    return module_form(cur_ppt.id)

async def ppt_imgs(ppt):
    # Parse the images string as JSON, assuming it's a JSON array of base64 strings
    try:
        images_list = json.loads(ppt.images)
    except json.JSONDecodeError:
        images_list = []
    images = [(fh.Img(src=f'data:image/jpeg;base64,{image}', alt='Image description', cls='carousel-image')) for image in images_list]
    return images

@app.get('/{ad_type}/properties/{ppt_id}')
async def ppt_dtls(sess, ad_type: int, ppt_id: int):
    print(f'{ad_type=}')
    print(f'{type(ad_type)=}')
    
    price_type = 'rent'
    if ad_type == AdType.SELL:
        price_type = 'sell'
    qry = f"""
    SELECT m.id, title, flr_capacity, hight, width, abl,
    office_area, docks, energy, available,
    p.type, p.description,
    c.name as city, s.name as street,
    (p.iptu*m.abl) as iptu,
    (p.condominium*m.abl) as condominium,
    (p.foro*m.abl) as foro,
    (m.{price_type}*m.abl) as rent,
    (iptu + condominium + foro + {price_type}) * abl as price,
    (m.abl - m.office_area) * 100 / m.abl as efficiency
    FROM modules as m
    LEFT JOIN properties as p ON m.ppt_id = p.id
    LEFT JOIN cities as c ON p.city_id = c.id
    LEFT JOIN streets as s ON p.street_id = s.id
    WHERE p.id = ?
    """
    model = 'properties'
    db_q = db.q(qry, (ppt_id,))
    ppt = db_q[0]
    df = pd.DataFrame(db_q)
    
    for k, v in SLCT_FLD['modify'].items():
        df[k] = df.apply(v, axis=1)
    tbl = df[list(FLDS_RENAME[model])].rename(columns=FLDS_RENAME[model]).transpose()
    user_id = sess['auth']
    imgs = ppt_images.rows_where('ppt_id = ?', (ppt_id,))
    return fh.Titled(
        f'{PPT_TYPE.get(ppt["type"])} RET{ppt_id:03d}',
        fh.Div(
            carousel(imgs),
            cls='property'
        ),
        fh.P(f"{ppt['street']} - {ppt['city']}", id='address'),
        # fh.Group(*(fh.Div(f'{v}: {ppt.__dict__[k]}', id=k) for k, v in costs_const().items()), id='costs'),
        fh.Label(fh.H2('Descricao:'), _for='description'),
        fh.Div(ppt['description'], id='description'),
        fh.Label(fh.H2('Infraestrutura:'), _for='infrastructure'),
        # fh.Div(ppt['infrastructure'], id='infrastructure'),
        fh.Label(fh.H2('Modulos:'), _for='modules'),
        fh.Form(
            fh.NotStr(tbl.to_html(escape=False, header=False)),
            id='modules', cls='table-container'
        ),
        fh.Button('Adicionar à comparação', type='submit', hx_post=f'/{user_id}/{ad_type}/{ppt_id}/comparison', hx_include='#modules'),
        fh.Button('Agendar visita', type='submit', hx_post=f'/{user_id}/{ad_type}/{ppt_id}/visit', hx_include='#modules'),
    ), fh.Script(src='/js/carouselScroll.js')

@app.post('/{user_id}/{ad_type}/{ppt_id}/comparison')
async def add_comparison(req, sess, user_id: str, ad_type: int, ppt_id: int, d: dict):
    mdl_ids = d.values()
    cmp_cls = Comparison(user_id=user_id, ppt_id=ppt_id, ad_type=ad_type, date=dt.now().strftime('%d/%m/%Y, %H:%M:%S'))
    cmp = comparisons.insert(cmp_cls)
    for id in mdl_ids:
        comparison_modules.insert(comparison_id=cmp['id'], module_id=id)
    return 'Done'

@app.get('/{user_id}/comparisons/{status}')
async def get_comparisons(user_id: str, status: str):
    qry = """
    SELECT cmp.id, ppt.name, d.name as district, c.name as city, ppt.location,
    ppt.iptu, ppt.foro, ppt.condominium,
    GROUP_CONCAT(m.title, ', ') as title,
    MIN(m.flr_capacity) as min_flr_capacity,
    MAX(m.flr_capacity) as max_flr_capacity,
    MIN(m.available) as min_available,
    MAX(m.available) as max_available,
    MIN(m.hight) as min_hight,
    MAX(m.hight) as max_hight,
    MIN(m.energy) as min_energy,
    MAX(m.energy) as max_energy,
    MIN(m.width) as min_width,
    MAX(m.width) as max_width,
    SUM(m.docks) as docks,
    SUM(m.abl) as abl,
    SUM(m.abl * (m.rent + ppt.iptu + ppt.foro + ppt.condominium)) as price,
    SUM(m.office_area) as office_area,
    (abl - office_area) * 100 / abl as efficiency
    FROM comparisons as cmp
    LEFT JOIN properties as ppt ON cmp.ppt_id = ppt.id
    LEFT JOIN districts AS d ON ppt.district_id = d.id
    LEFT JOIN cities AS c ON ppt.city_id = c.id
    LEFT JOIN comparison_modules as cmp_m ON cmp.id = cmp_m.comparison_id
    LEFT JOIN modules as m ON cmp_m.module_id = m.id
    WHERE cmp.user_id = ? AND status = ?
    GROUP BY cmp.id
    """
    db_q = db.q(qry, (user_id, status))
    cmp_list = [{'index': i + 1, 'location': json.loads(d.get('location'))} for i, d in enumerate(db_q)]
    df = pd.DataFrame(db_q)
    model = 'comparisons'
    for k, v in FLDS_MODIFICATIONS['rent'][model].items():
        df[k] = df.apply(v, axis=1)
    tbl = df[list(FLDS_RENAME[model])].rename(columns=FLDS_RENAME[model]).transpose()
    return fh.Div(
        (fh.Titled(
            'Comparacao',
            fh.Div(id='comparisons-map', cls='map'),
            fh.Div(id='dialog'),
            fh.Form(
                fh.NotStr(tbl.to_html(escape=False, header=False)),
                fh.Button('Download site selection'),
                action='/download_pdf', method='post',
                id='comparisons', cls='table-container'),
            fh.Button('Arquivar', type='submit', hx_post=f'/{user_id}/comparisons/add_archive', hx_include='#comparisons'),
            fh.Button('Agendar visita', type='submit', hx_post=f'/{user_id}/{NA}/{ZERO}/visit', hx_include='#comparisons'),
        ),
            fh.Script(map_comparisons_script(cmp_list)), *scripts),
            hx_swap_oob='true', id='body'
    )

async def delete_pdf(fpath: str):
    await aiofiles.os.remove(fpath)

@app.post("/download_pdf")
async def download_pdf(d: dict):
    cmp_ids = tuple(d.values())

    now = dt.now()
    date = now.strftime('%d_%m_%Y_%H:%M:%S')

    # File path
    output_pdf = f'./pdfs/{date}_dynamic_output.pdf'
    create_pdf(cmp_ids, output_pdf)
    task = BackgroundTask(delete_pdf, output_pdf)
    return fh.FileResponse(
        f'{output_pdf}',
        media_type='application/pdf',
        filename="my_report.pdf",
        content_disposition_type='attachment',
        background=task
    )

# @app.post('/create_pdf')
def create_pdf(cmp_ids, output_pdf):
    """Create pdf using reportlab."""
    # cmp_ids = tuple(d.values())
    placeholders = ', '.join(['?' for _ in cmp_ids])
    
    qry = f"""
    SELECT cmp.id, ppt.id, ppt.name, d.name as district, c.name as city, ppt.location,
    ppt.iptu, ppt.foro, ppt.condominium,
    GROUP_CONCAT(m.title, ', ') as title,
    MIN(m.flr_capacity) as min_flr_capacity,
    MAX(m.flr_capacity) as max_flr_capacity,
    MIN(m.available) as min_available,
    MAX(m.available) as max_available,
    MIN(m.hight) as min_hight,
    MAX(m.hight) as max_hight,
    MIN(m.energy) as min_energy,
    MAX(m.energy) as max_energy,
    MIN(m.width) as min_width,
    MAX(m.width) as max_width,
    SUM(m.docks) as docks,
    SUM(m.abl) as abl,
    SUM(m.abl * (m.rent + ppt.iptu + ppt.foro + ppt.condominium)) as price,
    SUM(m.abl * m.rent) / SUM(m.abl) as rent,
    SUM(m.office_area) as office_area,
    (abl - office_area) * 100 / abl as efficiency
    FROM comparisons as cmp
    LEFT JOIN comparison_modules as cmp_m ON cmp.id = cmp_m.comparison_id
    LEFT JOIN modules as m ON cmp_m.module_id = m.id
    LEFT JOIN properties as ppt ON cmp.ppt_id = ppt.id
    LEFT JOIN districts as d ON ppt.district_id = d.id
    LEFT JOIN cities as c ON ppt.city_id = c.id
    WHERE cmp.id IN ({placeholders})
    GROUP BY cmp.id
    """
    qry_img = f"""
    SELECT c.id,
    GROUP_CONCAT(DISTINCT pi.img) as img,
    GROUP_CONCAT(DISTINCT i.name) as infr
    FROM comparisons as c
    LEFT JOIN ppt_images as pi ON c.ppt_id = pi.ppt_id
    LEFT JOIN ppt_infrastructures as p ON c.ppt_id = p.ppt_id
    LEFT JOIN infrastructures as i ON p.infr_id = i.id
    WHERE c.id IN ({placeholders})
    GROUP BY c.id
    
    """
    db_imgs = db.q(qry_img, cmp_ids)
    db_q = db.q(qry, cmp_ids)
    locations = [{'index': i + 1, 'location': json.loads(d.get('location'))} for i, d in enumerate(db_q)]
    df = pd.DataFrame(db_q)
    for k, v in CMP_MODIFY.items():
        df[k] = df.apply(v, axis=1)
    tbl = df[list(CMP_RENAME)].rename(columns=CMP_RENAME).transpose()
    # now = dt.now()
    # date = now.strftime('%d_%m_%Y_%H:%M:%S')

    # # File paths
    # output_pdf = f'./pdfs/{date}_dynamic_output.pdf'
    # Register fonts
    pdfmetrics.registerFont(TTFont('Poppins', 'assets/fonts/Poppins-Regular.ttf'))

    # Create a PDF
    pdf_canvas = canvas.Canvas(output_pdf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT), pageCompression=1)

    # First page
    pdf_canvas.drawImage(COVER_BGD, 0, 0, width=PAGE_WIDTH, height=PAGE_HEIGHT)
    pdf_canvas.setFont("Poppins", 60)
    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.drawString(LR_PADDING, TOP_PADDING, "Opções para locação")
    pdf_canvas.drawString(LR_PADDING, TOP_PADDING - 60, "Limeira e região")

    # Bookmark the first page and add an outline entry
    pdf_canvas.bookmarkPage("first_page")
    pdf_canvas.addOutlineEntry("Cover", "first_page", level=0)

    pdf_canvas.showPage()

    # About page
    pdf_canvas.drawImage(ABOUT_BGD, 0, 0, width=PAGE_WIDTH, height=PAGE_HEIGHT)

    # Bookmark the about page and add an outline entry
    pdf_canvas.bookmarkPage("about_page")
    pdf_canvas.addOutlineEntry("About", "about_page", level=0)

    pdf_canvas.showPage()

    # Step 1: Define a form XObject for the background
    pdf_canvas.beginForm("background_form")
    pdf_canvas.drawImage(BODY_BGD, 0, 0, width=PAGE_WIDTH, height=PAGE_HEIGHT)
    pdf_canvas.endForm()

    # Second page (static map and links)
    pdf_canvas.doForm("background_form")

    # Insert static map
    pdf_canvas.drawImage(static_map_image, 400, 200, width=1200, height=800)

    locations_list = ((f"Imóvel_{i['index']:02d}", f"https://www.google.com/maps?q={i['location']['lat']},{i['location']['lng']}") for i in locations)
    # Add "See on map" links
    y_position = 150
    pdf_canvas.setFont("Poppins", 40)
    pdf_canvas.drawString(400, y_position, "See on map:")
    w = 250
    for idx, (label, url) in enumerate(locations_list, start=1):
        pdf_canvas.drawString(400 + idx * w, y_position, label)
        pdf_canvas.linkURL(url, (400 + idx * w, y_position, 400 + idx * w + w, y_position + 40))

    # Bookmark the map page and add an outline entry
    pdf_canvas.bookmarkPage("map_page")
    pdf_canvas.addOutlineEntry("Map and Locations", "map_page", level=0)

    pdf_canvas.showPage()

    # Add Table Page (with 2.jpg background)
    pdf_canvas.doForm("background_form")

    # Create a ReportLab stylesheet for Paragraphs
    styles = getSampleStyleSheet()

    # Define a custom ParagraphStyle with increased font size
    custom_style = ParagraphStyle(
        name='Custom',
        fontName='Poppins',  # Use Poppins font or your preferred font
        fontSize=25,  # Set desired font size here
        leading=28,  # Set line height (optional)
        # alignment=1,  # Center align (optional)
    )
    # Convert the DataFrame headers and rows to Paragraphs
    data = []
    header_row = [Paragraph('Imóvel', custom_style)] + [Paragraph(f'{i + 1:02d}', custom_style) for i in tbl.columns]
    data.append(header_row)
    # Convert each row in the DataFrame to Paragraphs
    for index, row in tbl.iterrows():
        row_data = [Paragraph(str(index), custom_style)] + [Paragraph(str(cell), custom_style) for cell in row]
        data.append(row_data)

    # Dynamically calculate column widths based on page size and padding
    available_width = PAGE_WIDTH - 2 * LR_PADDING
    col_width = available_width / len(data[0])
    tbl_width = [col_width] * len(data[0])

    # Create a table with dynamically calculated column widths
    table = Table(data, colWidths=tbl_width)

    # Define table style with increased font size
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightblue),  # Header background color
        ('TEXTCOLOR', (0, 0), (-1, 1), colors.whitesmoke),  # Header text color
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Poppins'),
        ('FONTSIZE', (0, 0), (-1, -1), 46),  # Increased font size
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Align text to the top of the cell
        # ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ('BACKGROUND', (0, 2), (-1, -1), colors.beige),  # Body background color
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    # Table height for calculating col positions (assumes uniform col heights)
    first_col_y = PAGE_HEIGHT - TOP_PADDING  # Starting y-position for the first col
    col_height = 40

    # Add links manually for the first column cols
    for col_idx in tbl.columns:
        header_number = f"{col_idx + 1:02d}"
        
        # Calculate the y position of each col's cell
        col_x_position = LR_PADDING + (col_idx + 1) * col_width
        
        # Define the clickable rectangle (adjust left/right as needed)
        link_rect = (col_x_position, first_col_y, col_x_position + col_width, first_col_y - col_height)
        
        # Add the clickable area linking to the bookmark
        pdf_canvas.linkRect(header_number, header_number, link_rect)

    # Wrap and draw the table
    table_width, table_height = table.wrap(PAGE_WIDTH, PAGE_HEIGHT - TOP_PADDING)
    table.drawOn(pdf_canvas, LR_PADDING, PAGE_HEIGHT - TOP_PADDING - table_height)
    
    # Bookmark the table page and add an outline entry
    pdf_canvas.bookmarkPage("table_page")
    pdf_canvas.addOutlineEntry("Table Overview", "table_page", level=0)

    pdf_canvas.showPage()

    # Add Dynamic Pages for each comparison
    tbl_dtls = df[list(FLDS_RENAME['modules'])].rename(columns=FLDS_RENAME['modules']).transpose()
    for idx in tbl_dtls.columns:
        header_number = f"{idx + 1:02d}"
        
        # Bookmark each row dynamically and add to the outline
        pdf_canvas.bookmarkPage(header_number)
        pdf_canvas.addOutlineEntry(f"Details for Column {idx + 1}", header_number, level=1)

        # Create two pages for each row
        pdf_canvas.doForm("background_form")
        pdf_canvas.setFont("Poppins", 40)
        pdf_canvas.drawString(LR_PADDING, PAGE_HEIGHT - TOP_PADDING + 100, f"Imóvel {idx + 1:02d}")
        
        column_data = tbl_dtls[idx].reset_index().values.tolist()  # Converts the column into a list of [index, value] pairs
        table1 = Table(column_data[:-5], colWidths=[350] * 2)
        # Define table style with increased font size
        table1.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),  # Header background color
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),  # Header text color
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Poppins'),
            ('FONTSIZE', (0, 0), (-1, -1), 26),  # Increased font size
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Align text to the top of the cell
            ('BOTTOMPADDING', (0, 0), (-1, -1), 30),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),  # Body background color
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        # Wrap and draw the table
        table1_width, table1_height = table1.wrap(PAGE_WIDTH, PAGE_HEIGHT - TOP_PADDING)
        table1.drawOn(pdf_canvas, LR_PADDING, PAGE_HEIGHT - TOP_PADDING - table1_height)
        table2 = Table(column_data[-5:], colWidths=[350] * 2)
        # Define table style with increased font size
        table2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),  # Header background color
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),  # Header text color
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Poppins'),
            ('FONTSIZE', (0, 0), (-1, -1), 26),  # Increased font size
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Align text to the top of the cell
            ('BOTTOMPADDING', (0, 0), (-1, -1), 30),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),  # Body background color
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        # Wrap and draw the table
        table2_width, table2_height = table2.wrap(PAGE_WIDTH, PAGE_HEIGHT - TOP_PADDING)
        table2.drawOn(pdf_canvas, LR_PADDING + 1000, PAGE_HEIGHT - TOP_PADDING - table2_height - 300)
        
        img_list = db_imgs[idx]['img'].split(',')
        infr_list = db_imgs[idx]['infr'].split(',')
        
        if img_list:
            pdf_canvas.drawImage(
                img_list[0][1:],
                LR_PADDING + 1000, PAGE_HEIGHT - TOP_PADDING - 300,
                width=700, height=300
            )
        pdf_canvas.showPage()
        pdf_canvas.doForm("background_form")
        for i in range(1, 3):
            try:
                pdf_canvas.drawImage(
                    img_list[i][1:],
                    LR_PADDING, PAGE_HEIGHT - TOP_PADDING - 330 * i,
                    width=700, height=300
                )
            except IndexError:
                break
        col = [[Paragraph('Infraestrutura:', custom_style)]] + [[Paragraph(f'•  {c}', custom_style)] for c in infr_list]
        table3 = Table(col, colWidths=PAGE_WIDTH / 2 - LR_PADDING)
        # Define table style
        table3.setStyle(TableStyle([
            # ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            # ('FONTNAME', (0, 0), (-1, -1), 'Poppins'),
            # ('FONTSIZE', (0, 0), (-1, -1), 26),  # Increased font size
            # ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Align text to the top of the cell
            # ('BOTTOMPADDING', (0, 0), (-1, -1), 30),
            ('BACKGROUND', (1, 0), (-1, -1), colors.transparent),  # Body background color
            ('GRID', (0, 0), (-1, -1), 0, colors.transparent),
        ]))
        # Wrap and draw the table
        table3_width, table3_height = table3.wrap(PAGE_WIDTH, PAGE_HEIGHT - TOP_PADDING)
        table3.drawOn(pdf_canvas, PAGE_WIDTH / 2, PAGE_HEIGHT - TOP_PADDING - table3_height)

        pdf_canvas.showPage()
    # Last page (background 1.jpg)
    pdf_canvas.drawImage(LAST_PAGE_BGD, 0, 0, width=PAGE_WIDTH, height=PAGE_HEIGHT)

    # Bookmark the last page and add an outline entry
    pdf_canvas.bookmarkPage("last_page")
    pdf_canvas.addOutlineEntry("Last Page", "last_page", level=0)

    # Save the PDF
    pdf_canvas.save()

    print(f"PDF generated: {output_pdf}")

@app.post('/{user_id}/{table}/add_archive')
def add_archive(user_id: str, table: str, d: dict):
    # Extract the values from the dict as a tuple of IDs
    ids = tuple(d.values())

    if ids:
        # Dynamically generate placeholders for each ID
        placeholders = ', '.join(['?' for _ in ids])
        qry = f"""
        UPDATE {table}
        SET status = 'archive'
        WHERE id IN ({placeholders});
        """
        # Execute the query and pass the tuple of IDs
        db.q(qry, ids)
    return 'Done'

@app.get('/comparisons/{id}')
async def get_comparison(id: int):
    qry = """
    SELECT  title, flr_capacity, hight, width, abl,
    office_area, docks, energy, available,
    p.id, p.type, p.description, ct.name as city,
    s.name as street,
    (p.iptu*m.abl) as iptu,
    (p.condominium*m.abl) as condominium,
    (p.foro*m.abl) as foro,
    (m.rent*m.abl) as rent,
    (iptu + condominium + foro + rent) * abl as price,
    (m.abl - m.office_area) * 100 / m.abl as efficiency
    FROM comparisons as c
    LEFT JOIN properties as p ON c.ppt_id = p.id
    LEFT JOIN cities as ct ON p.city_id = ct.id
    LEFT JOIN streets as s ON p.street_id = s.id
    LEFT JOIN comparison_modules as cm ON c.id = cm.comparison_id
    LEFT JOIN modules as m ON cm.module_id = m.id
    WHERE c.id = ?
    """
    db_q = db.q(qry, (id,))
    ppt = db_q[0]
    infra_qry = """
    SELECT i.name
    FROM ppt_infrastructures AS p
    LEFT JOIN infrastructures AS i ON p.infr_id = i.id
    WHERE p.ppt_id = ?
    """
    infras = db.q(infra_qry, (ppt['id'],))
    imgs = ppt_images.rows_where('ppt_id = ?', (ppt['id'],))
    df = pd.DataFrame(db_q)
    tbl = df[list(FLDS_RENAME['modules'])].rename(columns=FLDS_RENAME['modules']).transpose()
    item = fh.Titled(
        f'{PPT_TYPE.get(ppt["type"])} RET{ppt["id"]:03d}',
        fh.Div(
            carousel(imgs),
            cls='property'
        ),
        fh.P(f"{ppt['street']} - {ppt['city']}", id='address'),
        # fh.Group(*(fh.Div(f'{v}: {ppt.__dict__[k]}', id=k) for k, v in costs_const().items()), id='costs'),
        fh.Label(fh.H2('Descricao:'), _for='description'),
        fh.Div(ppt['description'], id='description'),
        fh.Label(fh.H2('Infraestrutura:'), _for='infrastructure'),
        fh.Ul(*[fh.Li(d['name']) for d in infras]),
        fh.Label(fh.H2('Modulos:'), _for='modules'),
        fh.Div(
            fh.NotStr(tbl.to_html(escape=False, header=False)),
            id='modules', cls='table-container'
        ),
    )
    return get_dialog('Detalhes', item)
    
@app.post('/{user_id}/{ad_type}/{ppt_id}/visit')
async def add_visit(req, sess, user_id: str, ad_type: str, ppt_id: int, d: dict):
    if ad_type == NA:
        return 'Done'
    return 'Done'

@app.post("/properties/{ppt_id}/modules")
async def add_module(ppt_id:int, mdl:dict):
    action = mdl.pop('action')
    modules.insert(mdl)
    if action == 'save_exit':
        return cls_dialog()
    del mdl['title']
    return fh.fill_form(module_form(ppt_id), mdl)

async def header_section(sess):
    # Conditional navigation elements based on login status
    if sess.get('auth'):
        login_element = fh.P(fh.Strong(fh.AX("Logout", hx_get="/logout", hx_swap="outerHTML", hx_target="#login-section")), id="login-section")
    else:
        login_element = fh.P(fh.Strong(fh.AX("Login", hx_get="/login", hx_target="#dialog")), id="login-section")
    role = sess.get('auth_r', 'anonim')
    return fh.Container(fh.Header(
        fh.Nav(fh.P(fh.Strong(fh.A("Retha", href="/", id='retha')), id='Retha'),
               fh.P(fh.Strong(fh.AX('Tasks', '/add_task', 'body'))),
               fh.P(
                   fh.Strong(
                       fh.AX("Comparisons", hx_get=f"{sess.get('auth')}/comparisons/{Status.ACTIVE}", id='profile', hx_target='#body')
                    ), id='Profile'),
               login_element)), id='header')

@app.get('/profile')
def profile(sess):
    u = users[sess['auth']]
    return fh.Titled('Profile Info', fh.Div(id='profile'))

@app.post('/filters')
def show_filters(d: dict):
    frm = mk_fltr()
    frm = fh.fill_form(frm, d)
    return fh.Div(
        frm,
        cls='sidebar',
    )

@app.post('/search_ppts')
async def get_locations(d:dict):
    commercial = d['commercial']
    ad_type = AdType.RENT
    price_type = 'rent'
    if int(commercial) == AdType.SELL:
        price_type = 'sell'
        ad_type = AdType.SELL
        
    qry = f"""
    SELECT p.id, p.location, p.name, p.type,
    c.name AS city, s.name AS street,
    GROUP_CONCAT(pi.img) AS images,
    SUM(m.abl) as max_area,
    MIN(m.abl) as min_area,
    MIN(m.{price_type}) as price
    FROM properties AS p
    LEFT JOIN cities AS c ON p.city_id = c.id
    LEFT JOIN streets AS s ON p.street_id = s.id
    LEFT JOIN ppt_images AS pi ON p.id = pi.ppt_id
    LEFT JOIN modules AS m ON p.id = m.ppt_id
    GROUP BY p.id
    """
    ppts = db.q(qry)
    locations = list(map(ppt_serializer, ppts))
    
    broker = d.get('broker')
    print(broker)
    if broker:
        print(f'{d=}')
        search_section = fh.Div(id='dialog', hx_swap_oob='true')
        
    else:
        frm = short_fltr()
        d['commercial'] = ad_type
        # d['under_construction'] = CHOICE_TYPE[int(d['under_construction'])]
        frm = fh.fill_form(frm, d)
        search_section = fh.Div(frm, hx_swap_oob='true', id='search-section')
    return (fh.Grid(fh.Ul(id="location-list"),
                    fh.Div(id="map", cls='map')),
            fh.Script(map_locations_script(locations, commercial))), search_section

@app.get('/add_task')
def get_task_form():
    return fh.Div(
        fh.Form(
            fh.Fieldset(
                fh.Label('Client:', fh.Input(name='client')),
                *[slct_fld(k, v) for k, v in FILTER_FLDS.items()],
                fh.Label('Broker:', fh.Input(name='broker')),
            ),
            fh.Button('Save', type='submit', hx_post='/tasks')
    ))

@app.post('/tasks')
def create_task(d: dict):
    print(f'{d=}')
    return 'done'

async def body_section():
    """Body section. Swaped based on view and user_role"""
    return fh.Container(
        fh.Div(
            fh.Div(fh.Button('+', data_tooltip='Cadastrar imovel', type='button', hx_get='/ppt_form', hx_target='#dialog')),
            fh.Div(short_fltr(), id='search-section'),
            id='body'
        )
    )

async def footer_section():
    """Footer section. Useful links"""
    cur_year = dt.now().year
    return fh.Container(
        # fh.Grid(fh.P('Links Rápidos'), fh.P('Contato')),
        fh.P(f'Retha ©{cur_year} - Todos os direitos reservados.'),
        id='footer')
    
scripts = (
    fh.Script(src=f"https://maps.googleapis.com/maps/api/js?key={GOOGLE_API}&callback=initMap&v=3&libraries=marker", defer=True),
    fh.Script(src="https://unpkg.com/@googlemaps/markerclusterer/dist/index.min.js"),
    
)

from fastcore.xtras import timed_cache


# @timed_cache(seconds=60)
async def home(sess):
    return (fh.Title(f"Retha - {DESCR}"),
        *scripts,
        fh.Main(
            await header_section(sess),
            await body_section(),
            fh.Container(fh.Div(id='result')),
            fh.Div(id='dialog'),
            await footer_section(),
            # await search_section(),
        ),
    )

@app.get("/")
async def homepage(sess): return await home(sess)

fh.serve()