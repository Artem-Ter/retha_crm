import json
from datetime import datetime as dt
from hmac import compare_digest

import aiofiles.os
import const
import fasthtml.common as fh
import mysettings as s
import pandas as pd
from components import (carousel, fltr_flds, get_address_flds,
                        get_autocomplete_for, get_dialog,
                        map_comparisons_script, map_locations_script, mk_fltr,
                        module_form, ppt_serializer, short_fltr, slct_fld)
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from starlette.background import BackgroundTask
from utils import get_or_create, save_img, transform_to

hdrs = [
    fh.Link(href='/css/main.css', rel='stylesheet'),
]
login_redir = fh.RedirectResponse('/login', status_code=303)

# The `before` function is a *Beforeware* function. These are functions that run before a route handler is called.
def before(req, sess):
    auth = req.scope['auth'] = sess.get('auth')
    if not auth: return login_redir

bware = fh.Beforeware(before, skip=[r'/favicon\.ico', r'/static/.*', r'.*\.css', '/login', '/', '/cls_dialog', '/register'])

bodykw = {"class": "relative bg-black font-geist text-black/80 font-details-off"}

app, rt = fh.fast_app(before=bware, hdrs=hdrs, bodykw=bodykw, live=True, debug=True)
app.mount('/pdfs', fh.StaticFiles(directory='./pdfs'), name='pdfs')
app.mount('/images', fh.StaticFiles(directory='./images'), name='imgs')

fh.setup_toasts(app)

@app.get('/clr_fltr')
def clr_fltr():
    frm = short_fltr()
    return fh.Div(frm, hx_swap_oob='true', id='body')

@app.post('/cls_fltr')
def cls_fltr(d: dict):
    frm = short_fltr()
    frm = fh.fill_form(frm, d)
    print(f'cls fltr {d=}')
    return fh.Div(
        frm,
        hx_swap_oob='true',
        id='body'
    ), fh.Div(id='sidebar', hx_swap_oob='true')

@app.get('/cls_dialog')
def cls_dialog():
    return fh.Div(hx_swap_oob='true', id='dialog')

@app.get("/login")
def login_form():
    frm = fh.Form(
        fh.Input(name='email', type='email', placeholder='Email', required=True),
        fh.Input(name='pwd', type='password', placeholder='Password', required=True),
        fh.Button('Login', type='submit', hx_post='/login'),  # Swap dialog on submit
        fh.P(fh.Small("Don't have an account yet?")),
        fh.Button('Register', hx_get='/register', hx_swap='outerHTML', hx_target='#dialog'),
        id='login-form'
    )
    return get_dialog('Login', frm)
# , fh.Script("document.getElementById('login-section').close();")
    
@fh.dataclass
class Login: email:str; pwd:str

@app.post("/login")
async def login(login:Login, sess):
    if not login.email or not login.pwd: return login_redir
    try:
        u = list(s.users.rows_where('email = ?', (login.email,), limit=1))[0]
    # If the primary key does not exist, the method raises a `NotFoundError`.
    except fh.NotFoundError:
        fh.add_toast(sess, "User doesn't exist. Please register.", 'info')
        return login_redir
    # This compares the passwords using a constant time string comparison
    # https://sqreen.github.io/DevelopersSecurityBestPractices/timing-attack/python
    if not compare_digest(u.get('pwd').encode("utf-8"), login.pwd.encode("utf-8")):
        fh.add_toast(sess, "Incorrect password.", 'info')
        return login_redir
    # Because the session is signed, we can securely add information to it. It's stored in the browser cookies.
    # If you don't pass a secret signing key to `FastHTML`, it will auto-generate one and store it in a file `./sesskey`.
    sess['auth'] = u['id']
    sess['auth_r'] = u['role']
    body_section = VIEWS.get(u['role'])
    return fh.P(
        fh.Strong(
            fh.AX("Logout", hx_get="/logout", hx_swap='outerHTML', hx_target="#login-section")
        ), id="login-section", hx_swap_oob='true'
    ), fh.Div(id='dialog', hx_swap_oob='true'), await body_section()

@app.get('/register')
async def get_register(sess):
    role = sess.get('auth_r', const.ANONIM)
    if role == s.Role.ADMIN:
        add_field = (
            fh.Hidden(name='pwd', value='superpassword'),
            slct_fld('role', const.ADMIN_REGISTER),
        )
    elif role == s.Role.SECRETARY:
        add_field = (
            fh.Hidden(name='pwd', value='superpassword'),
            slct_fld('role', const.SECRETARY_REGISTER)
        )
    else:
        add_field = (
            fh.Input(name='pwd', type='password', placeholder='Password'),
        )
    frm = fh.Form(
        fh.Input(name='name', type='name', placeholder='Nome'),
        fh.Input(name='email', type='email', placeholder='Email'),
        fh.Input(name='phone', type='phone', placeholder='Cellular'),
        fh.Input(name='organization', type='organization', placeholder='Empresa'),
        *add_field,
        fh.Button('Register', type='submit', hx_post='/register'),  # Swap dialog on submit
        id='login-form'
    )
    return get_dialog('Cadastrar', frm)

@app.post('/register')
async def register(sess, user:s.User):
    u = s.users.insert(user)
    if not sess.get('auth_r'):
        sess['auth'] = u.id
        sess['auth_r'] = u.role
        body_section = VIEWS.get(u.role)
        return fh.P(
            fh.Strong(
                fh.AX("Logout", hx_get="/logout", hx_swap='outerHTML', hx_target="#login-section")
            ), id="login-section", hx_swap_oob='true'
        ), fh.Div(id='dialog', hx_swap_oob='true'), await body_section()
    fh.add_toast(sess, f'User was registrered', 'success')
    return fh.Div(id='dialog', hx_swap_oob='true'), fh.Div(fh.Input(name='users', value=f'{u.name} - {u.email} - {u.id}', disabled=True), fh.Hidden(name='users', value=f'{u.name} - {u.email} - {u.id}'), id='user', hx_swap_oob='true')

@app.get("/logout")
async def logout(sess):
    del sess['auth']
    del sess['auth_r']
    body_section = VIEWS.get(const.ANONIM)
    return fh.P(
        fh.Strong(
            fh.AX(
                "Login",
                hx_get="/login",
                hx_swap='outerHTML',
                hx_target='#dialog'
            )
        ),
        id="login-section", hx_swap_oob='true'
    ), await body_section()

async def ppt_imgs(ppt):
    # Parse the images string as JSON, assuming it's a JSON array of base64 strings
    try:
        images_list = json.loads(ppt.images)
    except json.JSONDecodeError:
        images_list = []
    images = [(fh.Img(src=f'data:image/jpeg;base64,{image}', alt='Image description', cls='carousel-image')) for image in images_list]
    return images

@app.get('/{ad_type}/properties/{ppt_id}/{ppt_type}')
async def ppt_dtls(sess, ad_type: int, ppt_id: int, ppt_type: int):
    price_type = 'rent'
    ppt_table = const.PPT_TABLE.get(ppt_type)
    if ad_type == s.AdType.SELL:
        price_type = 'sell'
    qry = f"""
    SELECT m.id, title, flr_capacity, height, width, abl,
    office_area, docks, energy, available,
    pd.ppt_type, pd.description,
    c.name as city, s.name as street, pd.id as pd_id,
    (pd.iptu*m.abl) as iptu,
    (pd.condominium*m.abl) as condominium,
    (pd.foro*m.abl) as foro,
    (m.{price_type}*m.abl) as rent,
    (iptu + condominium + foro + {price_type}) * abl as price,
    (m.abl - m.office_area) * 100 / m.abl as efficiency
    FROM {ppt_table} as m
    LEFT JOIN property_details as pd ON m.pd_id = pd.id
    LEFT JOIN properties as p ON pd.ppt_id = p.id
    LEFT JOIN cities as c ON p.city_id = c.id
    LEFT JOIN streets as s ON p.street_id = s.id
    WHERE p.id = ?
    """
    model = 'properties'
    db_q = s.db.q(qry, (ppt_id,))
    ppt = db_q[0]
    df = pd.DataFrame(db_q)
    
    for k, v in const.SLCT_FLD['modify'].items():
        df[k] = df.apply(v, axis=1)
    tbl = df[list(const.FLDS_RENAME[model])].rename(columns=const.FLDS_RENAME[model]).transpose()
    user_id = sess['auth']
    # imgs = s.ppt_images.rows_where('pd_id = ?', (ppt_id,))
    return fh.Titled(
        f'{const.PPT_TYPE.get(ppt["ppt_type"])} RET{ppt_id:03d}',
        # fh.Div(
        #     carousel(imgs),
        #     cls='property'
        # ),
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
        fh.Button(
            'Adicionar à comparação',
            type='submit',
            hx_post=f'/{user_id}/{ad_type}/{ppt['pd_id']}/{ppt_type}/comparison',
            hx_include='#modules',
            hx_swap='outerHTML'
        ),
        fh.Button('Agendar visita', type='submit', hx_post=f'/{user_id}/{ad_type}/{ppt_id}/visit', hx_include='#modules'),
    ), fh.Script(src='/js/carouselScroll.js')

@app.post('/{user_id}/{ad_type}/{pd_id}/{ppt_type}/comparison')
async def add_comparison(req, sess, user_id: str, ad_type: int, pd_id: int, ppt_type: int, d: dict):
    mdl_ids = d.values()
    cmp_cls = s.Comparison(user_id=user_id, pd_id=pd_id, ad_type=ad_type, date=dt.now().strftime('%d/%m/%Y, %H:%M:%S'))
    cmp = s.comparisons.insert(cmp_cls)
    cmp_table = const.CMP_TABLE.get(ppt_type)
    for id in mdl_ids:
        cmp_table.insert(comparison_id=cmp['id'], unit_id=id)
    return fh.A('Ver comparações', type='submit', href=f'/{user_id}/comparisons/{ppt_type}/{int(s.Status.ACTIVE)}', target='blank')

@app.get('/{user_id}/comparisons/{ppt_type}/{status}')
async def get_comparisons(user_id: str, ppt_type: int, status: int):
    table = const.PPT_TABLE.get(ppt_type)
    cmp_table = const.CMP_TABLE.get(ppt_type)
    qry = f"""
    SELECT cmp.id, ppt.name, d.name as district, c.name as city, ppt.location,
    pd.iptu, pd.foro, pd.condominium, pd.ppt_type,
    GROUP_CONCAT(m.title, ', ') as title,
    MIN(m.flr_capacity) as min_flr_capacity,
    MAX(m.flr_capacity) as max_flr_capacity,
    MIN(m.available) as min_available,
    MAX(m.available) as max_available,
    MIN(m.height) as min_height,
    MAX(m.height) as max_height,
    MIN(m.energy) as min_energy,
    MAX(m.energy) as max_energy,
    MIN(m.width) as min_width,
    MAX(m.width) as max_width,
    SUM(m.docks) as docks,
    SUM(m.abl) as abl,
    SUM(m.abl * (m.rent + pd.iptu + pd.foro + pd.condominium)) as price,
    SUM(m.office_area) as office_area,
    (abl - office_area) * 100 / abl as efficiency
    FROM comparisons as cmp
    LEFT JOIN property_details as pd ON cmp.pd_id = pd.id
    LEFT JOIN properties as ppt ON pd.ppt_id = ppt.id
    LEFT JOIN districts AS d ON ppt.district_id = d.id
    LEFT JOIN cities AS c ON ppt.city_id = c.id
    LEFT JOIN {cmp_table} as cmp_m ON cmp.id = cmp_m.comparison_id
    LEFT JOIN {table} as m ON cmp_m.unit_id = m.id
    WHERE cmp.user_id = ? AND status = ?
    GROUP BY cmp.id
    """
    db_q = s.db.q(qry, (user_id, status))
    cmp_list = [{'index': i + 1, 'location': json.loads(d.get('location'))} for i, d in enumerate(db_q)]
    df = pd.DataFrame(db_q)
    model = 'comparisons'
    for k, v in const.FLDS_MODIFICATIONS['rent'][model].items():
        df[k] = df.apply(v, axis=1)
    tbl = df[list(const.FLDS_RENAME[model])].rename(columns=const.FLDS_RENAME[model]).transpose()
    return fh.Div(
        (fh.Titled(
            'Comparacao',
            fh.Div(id='comparisons-map', cls='map'),
            fh.Div(id='dialog'),
            fh.Form(
                fh.NotStr(tbl.to_html(escape=False, header=False)),
                fh.Button('Download site selection'),
                action=f'/{ppt_type}/download_pdf', method='post',
                id='comparisons', cls='table-container'),
            fh.Button('Arquivar', type='submit', hx_post=f'/{user_id}/comparisons/add_archive', hx_include='#comparisons'),
            fh.Button('Agendar visita', type='submit', hx_post=f'/{user_id}/{const.NA}/{const.ZERO}/visit', hx_include='#comparisons'),
        ),
            fh.Script(map_comparisons_script(cmp_list)), *scripts),
            # hx_swap_oob='true', id='body'
    )

async def delete_pdf(fpath: str):
    await aiofiles.os.remove(fpath)

@app.post("/{ppt_type}/download_pdf")
async def download_pdf(d: dict, ppt_type: int):
    cmp_ids = tuple(d.values())

    now = dt.now()
    date = now.strftime('%d_%m_%Y_%H:%M:%S')

    # File path
    output_pdf = f'./pdfs/{date}_dynamic_output.pdf'
    create_pdf(cmp_ids, output_pdf, ppt_type)
    task = BackgroundTask(delete_pdf, output_pdf)
    return fh.FileResponse(
        f'{output_pdf}',
        media_type='application/pdf',
        filename="my_report.pdf",
        content_disposition_type='attachment',
        background=task
    )

def create_pdf(cmp_ids, output_pdf, ppt_type):
    """Create pdf using reportlab."""
    # cmp_ids = tuple(d.values())
    placeholders = ', '.join(['?' for _ in cmp_ids])
    table = const.PPT_TABLE.get(ppt_type)
    cmp_table = const.CMP_TABLE.get(ppt_type)
    qry = f"""
    SELECT cmp.id, ppt.name, d.name as district, c.name as city, ppt.location,
    pd.iptu, pd.foro, pd.condominium, pd.ppt_type,
    GROUP_CONCAT(m.title, ', ') as title,
    MIN(m.flr_capacity) as min_flr_capacity,
    MAX(m.flr_capacity) as max_flr_capacity,
    MIN(m.available) as min_available,
    MAX(m.available) as max_available,
    MIN(m.height) as min_height,
    MAX(m.height) as max_height,
    MIN(m.energy) as min_energy,
    MAX(m.energy) as max_energy,
    MIN(m.width) as min_width,
    MAX(m.width) as max_width,
    SUM(m.docks) as docks,
    SUM(m.abl) as abl,
    SUM(m.abl * (m.rent + pd.iptu + pd.foro + pd.condominium)) as price,
    SUM(m.abl * m.rent) / SUM(m.abl) as rent,
    SUM(m.office_area) as office_area,
    (abl - office_area) * 100 / abl as efficiency
    FROM comparisons as cmp
    LEFT JOIN property_details as pd ON cmp.pd_id = pd.id
    LEFT JOIN properties as ppt ON pd.ppt_id = ppt.id
    LEFT JOIN districts AS d ON ppt.district_id = d.id
    LEFT JOIN cities AS c ON ppt.city_id = c.id
    LEFT JOIN {cmp_table} as cmp_m ON cmp.id = cmp_m.comparison_id
    LEFT JOIN {table} as m ON cmp_m.unit_id = m.id
    WHERE cmp.id IN ({placeholders})
    GROUP BY cmp.id
    """
    qry_img = f"""
    SELECT c.id,
    GROUP_CONCAT(DISTINCT pi.img) as img,
    GROUP_CONCAT(DISTINCT i.name) as infr
    FROM comparisons as c
    LEFT JOIN ppt_images as pi ON c.pd_id = pi.pd_id
    LEFT JOIN property_details as pd ON c.pd_id = pd.id
    LEFT JOIN properties as p ON pd.id = p.id
    LEFT JOIN ppt_infrastructures as p_i ON p.id = p_i.ppt_id
    LEFT JOIN infrastructures as i ON p_i.infr_id = i.id
    WHERE c.id IN ({placeholders})
    GROUP BY c.id
    """
    db_imgs = s.db.q(qry_img, cmp_ids)
    db_q = s.db.q(qry, cmp_ids)
    locations = [{'index': i + 1, 'location': json.loads(d.get('location'))} for i, d in enumerate(db_q)]
    df = pd.DataFrame(db_q)
    for k, v in const.CMP_MODIFY.items():
        df[k] = df.apply(v, axis=1)
    tbl = df[list(const.CMP_RENAME)].rename(columns=const.CMP_RENAME).transpose()
    # now = dt.now()
    # date = now.strftime('%d_%m_%Y_%H:%M:%S')

    # # File paths
    # output_pdf = f'./pdfs/{date}_dynamic_output.pdf'
    # Register fonts
    pdfmetrics.registerFont(TTFont('Poppins', 'assets/fonts/Poppins-Regular.ttf'))

    # Create a PDF
    pdf_canvas = canvas.Canvas(output_pdf, pagesize=(const.PAGE_WIDTH, const.PAGE_HEIGHT), pageCompression=1)

    # First page
    pdf_canvas.drawImage(const.COVER_BGD, 0, 0, width=const.PAGE_WIDTH, height=const.PAGE_HEIGHT)
    pdf_canvas.setFont("Poppins", 60)
    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.drawString(const.LR_PADDING, const.TOP_PADDING, "Opções para locação")
    pdf_canvas.drawString(const.LR_PADDING, const.TOP_PADDING - 60, "Limeira e região")

    # Bookmark the first page and add an outline entry
    pdf_canvas.bookmarkPage("first_page")
    pdf_canvas.addOutlineEntry("Cover", "first_page", level=0)

    pdf_canvas.showPage()

    # About page
    pdf_canvas.drawImage(const.ABOUT_BGD, 0, 0, width=const.PAGE_WIDTH, height=const.PAGE_HEIGHT)

    # Bookmark the about page and add an outline entry
    pdf_canvas.bookmarkPage("about_page")
    pdf_canvas.addOutlineEntry("About", "about_page", level=0)

    pdf_canvas.showPage()

    # Step 1: Define a form XObject for the background
    pdf_canvas.beginForm("background_form")
    pdf_canvas.drawImage(const.BODY_BGD, 0, 0, width=const.PAGE_WIDTH, height=const.PAGE_HEIGHT)
    pdf_canvas.endForm()

    # Second page (static map and links)
    pdf_canvas.doForm("background_form")

    # Insert static map
    pdf_canvas.drawImage(const.static_map_image, 400, 200, width=1200, height=800)

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
    available_width = const.PAGE_WIDTH - 2 * const.LR_PADDING
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
    first_col_y = const.PAGE_HEIGHT - const.TOP_PADDING  # Starting y-position for the first col
    col_height = 40

    # Add links manually for the first column cols
    for col_idx in tbl.columns:
        header_number = f"{col_idx + 1:02d}"
        
        # Calculate the y position of each col's cell
        col_x_position = const.LR_PADDING + (col_idx + 1) * col_width
        
        # Define the clickable rectangle (adjust left/right as needed)
        link_rect = (col_x_position, first_col_y, col_x_position + col_width, first_col_y - col_height)
        
        # Add the clickable area linking to the bookmark
        pdf_canvas.linkRect(header_number, header_number, link_rect)

    # Wrap and draw the table
    table_width, table_height = table.wrap(const.PAGE_WIDTH, const.PAGE_HEIGHT - const.TOP_PADDING)
    table.drawOn(pdf_canvas, const.LR_PADDING, const.PAGE_HEIGHT - const.TOP_PADDING - table_height)
    
    # Bookmark the table page and add an outline entry
    pdf_canvas.bookmarkPage("table_page")
    pdf_canvas.addOutlineEntry("Table Overview", "table_page", level=0)

    pdf_canvas.showPage()

    # Add Dynamic Pages for each comparison
    tbl_dtls = df[list(const.FLDS_RENAME['modules'])].rename(columns=const.FLDS_RENAME['modules']).transpose()
    for idx in tbl_dtls.columns:
        header_number = f"{idx + 1:02d}"
        
        # Bookmark each row dynamically and add to the outline
        pdf_canvas.bookmarkPage(header_number)
        pdf_canvas.addOutlineEntry(f"Details for Column {idx + 1}", header_number, level=1)

        # Create two pages for each row
        pdf_canvas.doForm("background_form")
        pdf_canvas.setFont("Poppins", 40)
        pdf_canvas.drawString(const.LR_PADDING, const.PAGE_HEIGHT - const.TOP_PADDING + 100, f"Imóvel {idx + 1:02d}")
        
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
        table1_width, table1_height = table1.wrap(const.PAGE_WIDTH, const.PAGE_HEIGHT - const.TOP_PADDING)
        table1.drawOn(pdf_canvas, const.LR_PADDING, const.PAGE_HEIGHT - const.TOP_PADDING - table1_height)
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
        table2_width, table2_height = table2.wrap(const.PAGE_WIDTH, const.PAGE_HEIGHT - const.TOP_PADDING)
        table2.drawOn(pdf_canvas, const.LR_PADDING + 1000, const.PAGE_HEIGHT - const.TOP_PADDING - table2_height - 300)
        
        img_list = db_imgs[idx]['img'].split(',')
        infr_list = db_imgs[idx]['infr'].split(',')
        
        if img_list:
            pdf_canvas.drawImage(
                img_list[0][1:],
                const.LR_PADDING + 1000, const.PAGE_HEIGHT - const.TOP_PADDING - 300,
                width=700, height=300
            )
        pdf_canvas.showPage()
        pdf_canvas.doForm("background_form")
        for i in range(1, 3):
            try:
                pdf_canvas.drawImage(
                    img_list[i][1:],
                    const.LR_PADDING, const.PAGE_HEIGHT - const.TOP_PADDING - 330 * i,
                    width=700, height=300
                )
            except IndexError:
                break
        col = [[Paragraph('Infraestrutura:', custom_style)]] + [[Paragraph(f'•  {c}', custom_style)] for c in infr_list]
        table3 = Table(col, colWidths=const.PAGE_WIDTH / 2 - const.LR_PADDING)
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
        table3_width, table3_height = table3.wrap(const.PAGE_WIDTH, const.PAGE_HEIGHT - const.TOP_PADDING)
        table3.drawOn(pdf_canvas, const.PAGE_WIDTH / 2, const.PAGE_HEIGHT - const.TOP_PADDING - table3_height)

        pdf_canvas.showPage()
    # Last page (background 1.jpg)
    pdf_canvas.drawImage(const.LAST_PAGE_BGD, 0, 0, width=const.PAGE_WIDTH, height=const.PAGE_HEIGHT)

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
        s.db.q(qry, ids)
    return 'Done'

@app.get('/comparisons/{id}/{ppt_type}')
async def get_comparison(id: int, ppt_type: int):
    table = const.PPT_TABLE.get(ppt_type)
    cmp_table = const.CMP_TABLE.get(ppt_type)
    qry = f"""
    SELECT  title, flr_capacity, height, width, abl,
    office_area, docks, energy, available,
    pd.id, ppt_type, description, c.name as city,
    s.name as street,
    (iptu*m.abl) as iptu,
    (condominium*m.abl) as condominium,
    (foro*m.abl) as foro,
    (m.rent*m.abl) as rent,
    (iptu + condominium + foro + rent) * abl as price,
    (m.abl - m.office_area) * 100 / m.abl as efficiency
    FROM comparisons as cmp
    LEFT JOIN property_details as pd ON cmp.pd_id = pd.id
    LEFT JOIN properties as ppt ON pd.ppt_id = ppt.id
    LEFT JOIN streets AS s ON ppt.street_id = s.id
    LEFT JOIN cities AS c ON ppt.city_id = c.id
    LEFT JOIN {cmp_table} as cmp_m ON cmp.id = cmp_m.comparison_id
    LEFT JOIN {table} as m ON cmp_m.unit_id = m.id
    WHERE cmp.id = ?
    """
    db_q = s.db.q(qry, (id,))
    ppt = db_q[0]
    infra_qry = """
    SELECT i.name
    FROM ppt_infrastructures AS p
    LEFT JOIN infrastructures AS i ON p.infr_id = i.id
    WHERE p.ppt_id = ?
    """
    infras = s.db.q(infra_qry, (ppt['id'],))
    imgs = s.ppt_images.rows_where('pd_id = ?', (ppt['id'],))
    df = pd.DataFrame(db_q)
    tbl = df[list(const.FLDS_RENAME['modules'])].rename(columns=const.FLDS_RENAME['modules']).transpose()
    item = fh.Titled(
        f'{const.PPT_TYPE.get(ppt["ppt_type"])} RET{ppt["id"]:03d}',
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
    if ad_type == const.NA:
        return 'Done'
    return 'Done'

@app.post("/properties/{ppt_id}/warehouses")
async def add_module(ppt_id:int, mdl:dict):
    action = mdl.pop('action')
    s.warehouses.insert(mdl)
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
    role = sess.get('auth_r', const.ANONIM)
    return fh.Container(fh.Header(
        fh.Nav(fh.P(fh.Strong(fh.A("Retha", href="/", id='retha')), id='Retha'),
               fh.P(fh.Strong(fh.AX('Tasks', '/tasks', 'body'))),
               fh.P(
                   fh.Strong(
                       fh.A(
                           "Comparisons",
                           href=f"{sess.get('auth')}/comparisons/{s.PropertyType.WAREHOUSE}/{s.Status.ACTIVE}",
                           id='profile',
                           target='blank'
                        )
                    ), id='Profile'),
               login_element)), id='header')

@app.get('/profile')
def profile(sess):
    u = s.users[sess['auth']]
    return fh.Titled('Profile Info', fh.Div(id='profile'))

@app.post('/filters')
def show_filters(d: dict):
    frm = mk_fltr()
    frm = fh.fill_form(frm, d)
    return fh.Div(
        frm,
        cls='sidebar',
        id='sidebar',
        hx_swap_oob='true',
    )

@app.post('/search_ppts')
async def get_locations(d:dict):
    ad_type = int(d['ad_type'])
    ppt_type = const.PPT_TABLE.get(int(d['ppt_type']))
    price_type = 'rent'
    if ad_type == s.AdType.SELL:
        price_type = 'sell'
    qry = f"""
    SELECT p.id, p.location, p.name, pd.ppt_type,
    c.name AS city, s.name AS street,
    GROUP_CONCAT(pi.img) AS images,
    SUM(m.abl) as max_area,
    MIN(m.abl) as min_area,
    MIN(m.{price_type}) as price
    FROM properties AS p
    LEFT JOIN cities AS c ON p.city_id = c.id
    LEFT JOIN streets AS s ON p.street_id = s.id
    LEFT JOIN property_details AS pd ON p.id = pd.ppt_id
    LEFT JOIN ppt_images AS pi ON pd.id = pi.pd_id
    LEFT JOIN {ppt_type} AS m ON pd.id = m.pd_id
    GROUP BY p.id
    """
    ppts = s.db.q(qry)
    locations = list(map(ppt_serializer, ppts))
    frm = short_fltr()
    frm = fh.fill_form(frm, d)
    print(f'locations {d=}')
    return (fh.Grid(fh.Ul(id="location-list"),
                    fh.Div(id="map", cls='map')),
            fh.Script(map_locations_script(locations, ad_type))), fh.Div(frm, hx_swap_oob='true', id='body')

@app.get('/new_task')
def get_new_task(sess, req):
    role = sess.get('auth_r')
    clients = fh.Label(
        'Cliente',
        fh.Grid(
            get_autocomplete_for('users', 'Cliente'),
            fh.Button('+', hx_get='/register', data_tooltip='Cadastrar Usuario', hx_target='#dialog'),
            id='user'
        ),
    )
    if role == s.Role.BROKER:
        brokers = fh.Hidden(name='broker', value=sess['auth'])
    else:
        brks = s.users.rows_where('role = ?', (s.Role.BROKER,), select='name || " - " || email AS broker, id')
        # qry = """
        # SELECT name || ' - ' || email as broker, id
        # FROM users AS u
        # WHERE u.role = ?
        # """
        # brks = s.db.q(qry, (s.Role.BROKER,))
        cs = {b.get('id'): b.get('broker') for b in brks}
        brokers = fh.Label('Corretor', slct_fld('broker', cs))
    frm = fh.Form(
        fh.Div(id='register', hx_swap='outerHTML'),
        clients,
        brokers,
        fh.Label('Descrição', fh.Textarea(name='initial_dscr', rows=10)),
        # fltr_flds(),
        fh.Button('Salvar', type='submit',),
        hx_post='/new_task', hx_target='#result'
    )
    return fh.Titled('Novo Negócio', frm)

@app.post('/new_task')
def create_new_task(sess, d: dict):
    l = d['users'].split(' - ')
    if len(l) == 3:
        u_id = l[-1]
        task = s.tasks.insert({
            'client_id': u_id,
            'broker_id': d.get('broker'),
            'initial_dscr': d.get('initial_dscr'),
            'date': dt.now().strftime('%d/%m/%Y, %H:%M:%S'),
        })
        btn = fh.Button('Salva e busca', type='button', hx_post=f'/tasks/{task["id"]}', hx_target='#result')
        frm = mk_fltr(btn)
        srch = fh.fill_form(frm, task)
        fh.add_toast(sess, "Negócio adicionado.", 'success')
        return fh.Div(
            fh.Label('Descrição', fh.P(d.get('initial_dscr'))),
            fh.Div(
                srch,
                cls='sidebar'
            ),
            id='result'
        )

@app.post('/tasks/{task_id}')
async def add_srch(task_id: int, d: dict):
    task_params = s.task_params.insert({
        'task_id': task_id,
        'city_id': get_or_create('cities', d.get('cities')),
        'region_id': get_or_create('regions', d.get('regions')),
        'district_id': get_or_create('districts', d.get('districts')),
        'date': dt.now().strftime('%d/%m/%Y, %H:%M:%S'),
        'ad_type': int(d.get('ad_type')),
        'ppt_type': int(d.get('ppt_type')),
        'in_conodminium': int(d.get('in_conodminium')),
        'under_construction': int(d.get('under_construction')),
        'price_min': int(d.get('price_min')),
        'price_max': int(d.get('price_max')),
        'area_min': int(d.get('area_min')),
        'area_max': int(d.get('area_max')),
        'height_min': int(d.get('height_min')),
        'height_max': int(d.get('height_max')),
        'efficiency_min': int(d.get('efficiency_min')),
        'efficiency_max': int(d.get('efficiency_max')),
        'abl_min': int(d.get('abl_min')),
        'abl_max': int(d.get('abl_max')),
        'doks_min': int(d.get('doks_min')),
        'doks_max': int(d.get('doks_max')),
        'flr_capacity_min': int(d.get('flr_capacity_min')),
        'flr_capacity_max': int(d.get('flr_capacity_max')),
        'office_area_min': int(d.get('office_area_min')),
        'office_area_max': int(d.get('office_area_max')),
        'energy_min': int(d.get('energy_min')),
        'energy_max': int(d.get('energy_max')),
        'avcb': int(d.get('avcb')),
    })
    return await get_locations(d)
    # return fh.RedirectResponse(f'/tasks/{task_id}', status_code=303)

@app.get('/tasks/{task_id}')
async def get_task(task_id: int):
    d = list(s.task_params.rows_where('task_id = ?', (task_id,)))[0]
    d['cities'] = s.cities[d.get('city_id')]['name']
    d['regions'] = s.regions[d.get('region_id')]['name']
    d['districts'] = s.districts[d.get('district_id')]['name']
    d['in_conodminium'] = str(d.get('in_conodminium'))
    d['under_construction'] = str(d.get('under_construction'))
    d['ad_type'] = str(d.get('ad_type'))
    d['ppt_type'] = str(d.get('ppt_type'))
    d['avcb'] = str(d.get('avcb'))
    # fltr = mk_fltr()
    # frm = fh.fill_form(fltr, d)
    srch_d = {}
    for k, v in d.items():
        if k.endswith('_min') or k.endswith('_max'):
            srch_d[f'{k}_handler'] = str(v)
            srch_d[k] = str(v)
            
        else:
            srch_d[k] = v

    return await get_locations(srch_d)
    # return fh.Div(frm, cls='sidebar', id='sidebar'), fh.Div(fh.P('map and applied filters'), id='result')

@app.get('/tasks')
def get_tasks_list():
    return fh.Ul(*(fh.Li(fh.AX(f'{t["date"]}', f'/tasks/{t["id"]}', 'result')) for t in s.tasks()))

@app.post('/ppt/{ppt_id}/{ppt_type}')
async def add_ppt_dtls(ppt_id:int, ppt_type: int, frm: dict):
    ppt_d = s.property_details.insert({
        'ppt_id': ppt_id,
        'ppt_type': ppt_type,
        'description': frm.get('description'),
        'iptu': transform_to(float, frm.get('iptu')),
        'condominium': transform_to(float, frm.get('condominium')),
        'foro': transform_to(float, frm.get('foro')),
    })
    
    imgs = frm.get('images')
    if imgs:
        try:
            for img in imgs:
                await save_img(ppt_d.id, img)
        except TypeError:
            await save_img(ppt_d.id, imgs)
    # insert logic to select next form based on type
    d = {
        s.PropertyType.WAREHOUSE: module_form,
        s.PropertyType.LAND: module_form,
        s.PropertyType.OFFICE: module_form,
        s.PropertyType.SHOP: module_form,
    }
    return d.get(ppt_type)(ppt_d.id)

@app.get('/frm/{ppt_id}/{ppt_type}')
async def get_ppt_dtls(ppt_id:int, ppt_type: int):
    form = fh.Form(
        *(fh.Input(name=k, placeholder=v) for k, v in const.COSTS.items()),
        fh.Textarea(name='description', placeholder='Descrição', rows=10),
        fh.Label(
            'Fotos',
            fh.Input(name='images', type='file', multiple=True)
        ),
        fh.Button('Next'),
        hx_post=f'/ppt/{ppt_id}/{ppt_type}'
    )
    return get_dialog('Detalhes', form)

@app.post('/ppts')
async def add_ppt(frm: dict):
    infra = frm.pop('infrastructures')
    str_id = get_or_create('streets', frm.get('street'))
    dstr_id = get_or_create('districts', frm.get('district'))
    city_id = get_or_create('cities', frm.get('city'))
    rgn_id = get_or_create('regions', frm.get('region'))
    
    ppt = s.properties.insert({
        'in_conodminium': transform_to(bool, frm.get('in_conodminium')),
        'on_site': transform_to(bool, frm.get('on_site')),
        'name': frm.get('name'),
        'cep': frm.get('cep'),
        'street_id': str_id,
        'number': transform_to(int, frm.get('number')),
        'district_id': dstr_id,
        'city_id': city_id,
        'region_id': rgn_id,
        'retha_admin': transform_to(bool, frm.get('retha_admin')),
        'under_construction': transform_to(bool, frm.get('under_construction')),
        'location': frm.get('location')
    })
    if infra:
        for i in infra:
            if i:
                idx = get_or_create('infrastructures', i)
                
                s.ppt_infrastructures.insert({
                    'ppt_id': ppt.id,
                    'infr_id': idx
                })
    return await get_ppt_dtls(ppt.id, int(frm.get('ppt_type')))

@app.get('/ppt/{ppt_id}/{ppt_type}')
def get_ppt(sess, ppt_id:int, ppt_type:int):
    d = {
        s.PropertyType.WAREHOUSE: 'warehouses',
        s.PropertyType.LAND: 'lands',
        s.PropertyType.OFFICE: 'offices',
        s.PropertyType.SHOP: 'shops',
    }
    ppt_qry = f"""
    SELECT p.id, in_conodminium, on_site, p.name, cep,
    number, retha_admin, under_construction, location,
    c.name as city, s.name as street, r.name as region
    FROM properties as p
    LEFT JOIN cities as c ON p.city_id = c.id
    LEFT JOIN streets as s ON p.street_id = s.id
    LEFT JOIN districts as d ON p.district_id = d.id
    LEFT JOIN regions as r ON p.region_id = r.id
    WHERE p.id = ?
    """
    ppt = s.db.q(ppt_qry, (ppt_id,))
    qry = f"""
    SELECT pd.*,
    GROUP_CONCAT(u.title, ', ') as title
    FROM property_details as pd
    LEFT JOIN {d.get(ppt_type)} as u ON pd.id = u.pd_id
    WHERE pd.ppt_id = ? and pd.ppt_type = ?
    GROUP BY pd.id
    """
    pds = s.db.q(qry, (ppt_id, ppt_type))
    add_flds = None
    if pds:
        df = pd.DataFrame(pds)
        df['add_module'] = df.apply(
            lambda row: f"<a hx-get='{row['id']}/{d.get(ppt_type)}/form' hx-target='#dialog' hx-swap='innerHTML'>Adiciona mais modulos</a>",
            axis=1
        )    
        df = df.transpose()
        add_flds = (
            fh.NotStr(df.to_html(escape=False, header=False)),
        )
    return get_dialog(
        'Imovel',
        fh.Div(
            fh.Div(fh.P(f'{k}: {v},') for k, v in ppt[0].items()),
            add_flds,
            fh.Button(
                f'Cadastrar {const.PPT_TYPE.get(ppt_type)}',
                type='submit',
                hx_get=f'/frm/{ppt_id}/{ppt_type}'
            )
        )
    )

@app.post('/frm_dtls')
def get_frm_dtls(d: dict):
    ppt = list(s.properties.rows_where(
        'cep = ? and number = ?',
        (d.get('cep'), d.get('number')),
        limit=1
    ))
    ppt_type = int(d.get('ppt_type'))
    if ppt:
        return fh.RedirectResponse(f'/ppt/{ppt[0]["id"]}/{ppt_type}', status_code=303)
    frm = fh.Form(
        fh.Hidden(name='ppt_type', value=ppt_type),
        fh.Hidden(name='number', value=d.get('number')),
        fh.Hidden(name='cep', value=d.get('cep')),
        fh.CheckboxX(name='in_conodminium', role='switch', label='Em condomínio'),
        fh.Input(name='name', placeholder='Nome de Condominio / Monousuário'),
        fh.CheckboxX(name='on_site', role='switch', label='Publicar no Site'),
        fh.CheckboxX(name='retha_admin', role='switch', label='Administração Retha'),
        fh.CheckboxX(name='under_construction', role='switch', label='Em construção'),
        fh.Label(
            'CEP',
            fh.Input(name='cep', value=d.get('cep'), disabled=True)),
        fh.Label(
            'Numero de casa',
            fh.Input(name='number', value=d.get('number'), disabled=True)),
        fh.Grid(
            *(fh.Input(name=k, placeholder=v) for k, v in const.ADDRESS_FLDS.items() if k not in ('cep', 'number'))
        ),
        get_autocomplete_for('infrastructures', 'Infraestrutura', multiple=True),
        fh.Input(name='location', placeholder='Localização'),
        fh.Grid(
            fh.Button('Back', hx_get='/frm_adrs'),
            fh.Button('Next')
        ),
        hx_post='/ppts'
    )
    return get_dialog(f'Cadastrar {const.PPT_TYPE.get(ppt_type)}', frm)

@app.get('/frm_adrs')
async def get_frm_adrs():
    frm = fh.Form(
        fh.Fieldset(
            fh.Label(
                'Type:',
                fh.Select(
                    *mk_opts('ppt_type', const.PPT_TYPE),
                    name='ppt_type',
                )
            ),
            fh.Label(
                'CEP', fh.Input(
                    name='cep'
                )
            ),
            fh.Label(
                'Numero de casa', fh.Input(
                    name='number'
                )
            ),
            # *(fh.Label(v, fh.Input(name=k)) for k, v in const.ADDRESS_FLDS.items()),
        ),
        fh.Button('Next', hx_post='/frm_dtls', hx_target='#dialog')
    )
    return get_dialog('Cadastrar Imovel', frm)

def mk_opts(nm, cs):
    return (fh.Option(v, value=k) for k, v in cs.items())

async def get_body_layout(*args, **kwargs):
    return fh.Container(
        fh.Div(
            *args,
            hx_swap_oob='true',
            id='body',
            **kwargs,
        )
    )

async def get_secretary_view():
    return await get_body_layout(
        fh.Grid(
            fh.Button(
                '+ Novo Negócio',
                hx_get='/new_task',
                hx_target='#result'
            ),
            fh.Button(
                '+ Imovel',
                data_tooltip='Cadastrar imovel',
                type='button',
                hx_get='/frm_adrs',
                hx_target='#dialog'
            ),
            fh.Button(
                '+ Usuario',
                hx_get='/register',
                hx_target='#dialog'
            ),
        ),
    )

async def get_user_view():
    return await get_body_layout(
        short_fltr()
    )

async def get_admin_view():
    buttons = fh.Button('Cadastrar usuario', hx_get='/register', hx_target='#dialog')
    return await get_body_layout(buttons)

async def footer_section():
    """Footer section. Useful links"""
    cur_year = dt.now().year
    return fh.Container(
        # fh.Grid(fh.P('Links Rápidos'), fh.P('Contato')),
        fh.P(f'Retha ©{cur_year} - Todos os direitos reservados.'),
        id='footer')

scripts = (
    fh.Script(
        src=f"https://maps.googleapis.com/maps/api/js?key={s.GOOGLE_API}&callback=initMap&v=3&libraries=marker",
        defer=True
    ),
    fh.Script(
        src="https://unpkg.com/@googlemaps/markerclusterer/dist/index.min.js"
    ),
    
)

from fastcore.xtras import timed_cache

VIEWS = {
    s.Role.ADMIN: get_admin_view,
    s.Role.BROKER: get_user_view,
    s.Role.SECRETARY: get_secretary_view,
    s.Role.USER: get_user_view,
    const.ANONIM: get_user_view,
}

# @timed_cache(seconds=60)
async def home(sess):
    role = sess.get('auth_r', const.ANONIM)
    body_section = VIEWS.get(role)
    return (fh.Title(f"Retha - {const.DESCR}"),
        *scripts,
        fh.Div(id='sidebar'),
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