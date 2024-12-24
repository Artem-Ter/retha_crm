import time
from datetime import datetime as dt
from hmac import compare_digest

import components as c
import const
import fasthtml.common as fh
import mysettings as s
from starlette.background import BackgroundTask

hdrs = [
    fh.Link(href="/css/main.css", rel="stylesheet"),
]
login_redir = fh.RedirectResponse("/login", status_code=303)


# The `before` function is a *Beforeware* function. These are functions that run before a route handler is called.
def before(req, sess):
    auth = req.scope["auth"] = sess.get("auth")
    if not auth:
        return login_redir


bware = fh.Beforeware(
    before,
    skip=[
        r"/favicon\.ico",
        r"/static/.*",
        r".*\.css",
        "/login",
        "/",
        r"/cls_details/.*",
        "/register",
        r"/ppts.*",
        r"/filter.*",
    ],
)

bodykw = {"class": "relative bg-black font-geist text-black/80 font-details-off"}

app, rt = fh.fast_app(before=bware, hdrs=hdrs, bodykw=bodykw, live=True, debug=True)
app.mount("/pdfs", fh.StaticFiles(directory="./pdfs"), name="pdfs")
app.mount("/imgs", fh.StaticFiles(directory="./imgs"), name="imgs")

fh.setup_toasts(app)


@app.get("/cls_fltr/{div_id}")
async def cls_fltr(d: dict, div_id: str = "dialog"):
    prefil = d.pop("city_id") if isinstance(d.get("city_id"), list) else None
    frm = await c.short_fltr(int(d["ad_type"]), int(d["ppt_type"]), prefil=prefil)
    frm = fh.fill_form(frm, d)
    return fh.Div(frm, hx_swap_oob="true", id="short-fltr"), cls_details(div_id)


@app.get("/cls_details/{div_id}")
def cls_details(div_id: str = "dialog"):
    return fh.Div(hx_swap_oob="true", id=div_id)


@app.get("/login")
def login_form():
    frm = fh.Form(
        fh.Input(name="email", type="email", placeholder="Email", required=True),
        fh.Input(name="pwd", type="password", placeholder="Password", required=True),
        fh.Button("Login", type="submit", hx_post="/login"),  # Swap dialog on submit
        fh.P(fh.Small("Don't have an account yet?")),
        fh.Button(
            "Register", hx_get="/register", hx_swap="outerHTML", hx_target="#register"
        ),
    )
    return c.get_dialog("Login", frm, "register")


@fh.dataclass
class Login:
    email: str
    pwd: str


@app.post("/login")
async def login(login: Login, sess):
    if not login.email or not login.pwd:
        return login_redir
    try:
        u = list(s.users.rows_where("email = ?", (login.email,), limit=1))[0]
    # If the primary key does not exist, the method raises a `NotFoundError`.
    except fh.NotFoundError:
        fh.add_toast(sess, "User doesn't exist. Please register.", "info")
        return login_redir
    # This compares the passwords using a constant time string comparison
    # https://sqreen.github.io/DevelopersSecurityBestPractices/timing-attack/python
    if not compare_digest(u.get("pwd").encode("utf-8"), login.pwd.encode("utf-8")):
        fh.add_toast(sess, "Incorrect password.", "info")
        return login_redir
    # Because the session is signed, we can securely add information to it. It's stored in the browser cookies.
    # If you don't pass a secret signing key to `FastHTML`, it will auto-generate one and store it in a file `./sesskey`.
    sess["auth"] = u["id"]
    sess["auth_r"] = u["role"]
    body_section = get_user_view if u["role"] == s.Role.USER else get_employee_view
    flds = None
    if u["role"] in const.EMPLOYEES:
        flds = c.get_hdr_flds(sess, u["role"], hx_swap_oob="true")
    return (
        c.get_loginout_fld(True, hx_swap_oob="true"),
        flds,
        cls_details("register"),
        await body_section(sess),
    )


@app.get("/register")
async def get_register(sess):
    role = sess.get("auth_r", const.ANONIM)
    if role == s.Role.ADMIN:
        add_field = (
            fh.Hidden(name="pwd", value="superpassword"),
            c.slct_fld("role", const.ROLE_TYPE),
        )
    elif role in (s.Role.SECRETARY, s.Role.BROKER):
        add_field = (
            fh.Hidden(name="pwd", value="superpassword"),
            c.slct_fld("role", const.SECRETARY_REGISTER),
        )
    else:
        add_field = (fh.Input(name="pwd", type="password", placeholder="Password"),)
    frm = fh.Form(
        c.get_usr_flds(*add_field),
        fh.Button(
            "Register", type="submit", hx_post="/register"
        ),  # Swap dialog on submit
        id="login-form",
    )
    return c.get_dialog("Cadastrar", frm, "register", 1000)


@app.post("/register")
async def register(sess, user: dict):
    if not user.get("role"):
        user["role"] = s.Role.USER
    u = s.users.insert(user)
    if sess.get("auth_r"):
        fh.add_toast(sess, "User was registrered", "success")
        return fh.Div(
            fh.Input(
                name=const.ROLE_FK[u.role],
                value=f"{u.name} - {u.email} - {u.id}",
                disabled=True,
            ),
            fh.Hidden(
                name=const.ROLE_FK[u.role], value=f"{u.name} - {u.email} - {u.id}"
            ),
            id="user",
            hx_swap_oob="true",
        ), cls_details("register")
    sess["auth"] = u.id
    sess["auth_r"] = u.role
    body_section = get_user_view if u.role == s.Role.USER else get_employee_view
    flds = None
    if u.role in const.EMPLOYEES:
        flds = c.get_hdr_flds(sess, u.role, hx_swap_oob="true")
    return (
        tuple(c.get_loginout_fld(True, hx_swap_oob="true")),
        flds,
        cls_details("register"),
        await body_section(sess),
    )


@app.get("/logout")
async def logout(sess):
    del sess["auth"]
    del sess["auth_r"]
    return (
        c.get_loginout_fld(hx_swap_oob="true"),
        c.get_hdr_flds(sess, const.ANONIM, hx_swap_oob="true"),
        await get_user_view(sess),
    )


@app.post("/comparisons")
async def add_comparison(sess, d: dict):
    if d.get("selected"):
        unit_ids = d.pop("selected")
        if not isinstance(unit_ids, list):
            unit_ids = [unit_ids]
        d["author_id"] = sess["auth"]
        return await c.create_cmp(d, unit_ids)
    fh.add_toast(sess, "Select units for comparison", "error")
    return fh.Button(
        "Adicionar à comparação",
        type="submit",
        hx_post="/comparisons",
        hx_include="#modules",
        hx_swap="outerHTML",
    )


@app.get("/comparisons")
async def get_comparisons(sess, req):
    data = {**req.query_params}
    slctd = None
    if not data:
        data = {
            "user_id": sess["auth"],
            "ppt_type": s.PropertyType.WAREHOUSE,
            "ad_type": s.AdType.RENT,
        }
        frm = fh.Form(
            fh.Grid(
                *(c.slct_fld(k, v) for k, v in const.FILTER_FLDS.items()), id="fltr"
            ),
            fh.Button(
                "Ver comparacoes",
                hx_get="/comparisons",
                hx_target="#result",
                hx_include="#fltr",
            ),
        )
        slctd = fh.fill_form(frm, data)
    data["user_id"] = data.get("user_id", sess["auth"])
    flds = ("select", "details", "address", "name")
    try:
        tbl, locations = await c.get_cmp_for(data, flds, return_frm=True)
    except ValueError:
        fh.add_toast(sess, "You don't have this type of comparisons yet", "error")
        return fh.Div(slctd, id="result")
    return fh.Div(
        slctd,
        (
            fh.Titled(
                "Comparacao",
                fh.Div(id="comparisons-map", cls="map"),
                fh.Div(id="dialog"),
                tbl,
                fh.Grid(
                    *(
                        c.add_btn_for(k, include="comparisons")
                        for k in ("archives", "visits")
                    ),
                    style="gap: 1.5rem",
                ),
            ),
            fh.Script(c.map_comparisons_script(locations)),
            *scripts,
        ),
        id="result",
    )


@app.get("/comparisons/{cmp_id}")
async def get_comparisons(sess, req, cmp_id: int):
    cmp = s.comparisons[cmp_id]
    return c.get_dialog(
        "Imovel",
        await c.get_ppt_infr_img_units(
            cmp["ppt_id"], cmp["user_id"], tbl_flds=[], ad_type=cmp["ad_type"]
        ),
    )


@app.post("/download_pdf")
async def download_pdf(sess, d: dict):
    if d.get("selected"):
        cmp_ids = d.get("selected")
        if not isinstance(cmp_ids, list):
            cmp_ids = [cmp_ids]
            d["selected"] = cmp_ids
    date = int(time.time())
    # File path
    output_pdf = f"./pdfs/{date}_dynamic_output.pdf"
    await c.create_pdf(d, output_pdf)
    task = BackgroundTask(c.delete_pdf, output_pdf)
    return fh.FileResponse(
        output_pdf,
        media_type="application/pdf",
        filename=f"{const.PPT_TYPE[int(d['ppt_type'])]}_selection.pdf",
        content_disposition_type="attachment",
        background=task,
    )


@app.post("/archives")
def add_archive(sess, d: dict):
    # Extract the values from the dict as a tuple of IDs
    # ids = tuple(d.values())

    # if ids:
    #     # Dynamically generate placeholders for each ID
    #     placeholders = ', '.join(['?' for _ in ids])
    #     qry = f"""
    #     UPPTATE {table}
    #     SET status = 'archive'
    #     WHERE id IN ({placeholders});
    #     """
    #     # Execute the query and pass the tuple of IDs
    #     s.db.q(qry, ids)
    return "Done"


@app.post("/visits")
async def add_visit(sess, d: dict):
    return "Done"


async def header_section(sess):
    # Conditional navigation elements based on login status
    if sess.get("auth"):
        login_element = fh.P(
            fh.Strong(
                fh.AX(
                    "Logout",
                    hx_get="/logout",
                    hx_swap="outerHTML",
                    hx_target="#login-section",
                )
            ),
            id="login-section",
        )
    else:
        login_element = fh.P(
            fh.Strong(fh.AX("Login", hx_get="/login", hx_target="#dialog")),
            id="login-section",
        )
    role = sess.get("auth_r", const.ANONIM)
    return fh.Container(
        fh.Header(
            fh.Nav(
                *c.get_hdr_flds(sess, role),
                c.get_loginout_fld(bool(sess.get("auth"))),
            )
        ),
        id="header",
    )


@app.get("/profile")
def profile(sess):
    u = s.users[sess["auth"]]
    return fh.Titled("Profile Info", fh.Div(id="profile"))


@app.get("/task_frm")
def get_task_frm(sess, req):
    frm = c.task_frm(sess)
    return c.get_dialog("Novo Negócio", frm), cls_details("result")


@app.post("/tasks")
async def create_new_task(sess, d: dict):
    client = d["client_id"].split(" - ")
    if len(client) != 3:
        d["client_id"] = ""
        frm = fh.fill_form(c.task_frm(sess), d)
        fh.add_toast(sess, "Wrong client", "error")
        return c.get_dialog("Novo Negócio", frm)
    tsk = d.copy()
    tsk["client_id"] = client[-1]

    task = s.tasks.insert(
        {
            **{k: v(tsk[k]) for k, v in s.TSK_FLDS.items() if tsk.get(k)},
            "start_date": dt.now().strftime("%Y/%m/%d, %H:%M:%S"),
            "status": s.Status.NEW,
        }
    )
    btns = fh.Grid(
        fh.Button("Salva e busca", type="submit", id="action", value="save"),
        fh.Button("Buscar", type="submit", id="action", value="search"),
    )
    ad_type = int(d["ad_type"])
    frm = fh.Form(
        fh.Hidden(id="task_id", value=task["id"]),
        await c.get_fltr(ad_type, int(d["ppt_type"])),
        btns,
        hx_get="/ppts",
        hx_params="*",
        hx_trigger="submit",
        hx_target="#result",
    )
    srch = fh.fill_form(frm, d)
    fh.add_toast(sess, "Negócio adicionado.", "success")
    return c.get_dialog(
        "task params",
        fh.Div(
            fh.Label("Descrição:", fh.P(d.get("initial_dscr"))),
            srch,
        ),
    )


@app.route("/adrs", methods=["PUT", "POST"])
async def create_adrs(sess, req, d: dict):
    adrs_str = f"{d['cep']} {d['street_id']}, {d['str_number']}, "
    f"{d['city_id']}, {d['region_id']}"
    location = c.extract_lat_lng(adrs_str)
    adrs_d = {
        **{k: c.get_or_create(k, d[k]) for k in s.CDRS_FK if d.get(k)},
        **{k: v(d[k]) for k, v in s.CNB_FLDS.items() if d.get(k)},
        "location": location,
    }
    text = "Endereço foi "
    if req.method == "PUT":
        adrs_d["id"] = d["id"]
        s.addresses.update(adrs_d)
        text += "editado"
        fh.add_toast(sess, text, "success")
        return None
    adrs = s.addresses.insert(adrs_d)
    print(adrs)
    text += "adicionado"
    frm = await c.get_ppt_frm(adrs["id"], int(d["ppt_type"]))
    fh.add_toast(sess, text, "success")
    return c.get_dialog("Imovel", frm)


@app.route("/ppts", methods=["PUT", "POST"])
async def create_ppt(sess, req, d: dict):
    if d.get("avcb_id"):
        d["avcb_id"] = c.get_or_create("avcb_id", d["avcb_id"])
    for k in s.PPT_BOOL_FLDS:
        d[k] = bool(d.get(k))
    text = f'Propriedade {d["name"]} foi '
    if req.method == "PUT":
        s.properties.update(d)
        text += "editada"
        fh.add_toast(sess, text, "success")
        return None
    ppt = s.properties.insert(d)
    text += "adicionada"
    fh.add_toast(sess, text, "success")
    return c.get_dialog(
        f"Cadstrar {const.PPT_TYPE[ppt.ppt_type]}",
        fh.Div(
            fh.Form(
                fh.Hidden(id="ppt_id", value=ppt.id),
                fh.Hidden(id="ppt_type", value=ppt.ppt_type),
                c.get_layout_for("pdfs", ppt.id),
                c.get_layout_for("infrs", ppt.id),
                c.get_layout_for("imgs", ppt.id),
                id="modules",
            ),
            c.add_btn_for("unit_frm", name="Next"),
        ),
    )


@app.post("/unit_frm")
async def get_unit_form(sess, d: dict):
    ppt_id = int(d["ppt_id"])
    ppt_type = int(d["ppt_type"])
    return c.get_dialog(
        f"Cadstrar {const.PPT_TYPE[ppt_type]}",
        await c.get_unit_frm(sess, ppt_type, ppt_id),
    )


@app.get("/ppts/{ppt_id}")
async def get_ppt(sess, req, ppt_id: int):
    ad_type = req.query_params.get("ad_type")
    tsk_id = req.query_params.get("task_id")
    usr_id = sess.get("auth")
    if ad_type:
        ad_type = int(ad_type)
    if tsk_id:
        tsk = s.tasks[int(tsk_id)]
        usr_id = tsk["client_id"]
    flds = ["select"]  # extra flds for unit table
    btns = ["comparisons"]
    if sess.get("auth_r") in const.EMPLOYEES:
        flds.append("edit")
    else:
        btns.append("visits")
    return await c.get_ppt_infr_img_units(ppt_id, usr_id, flds, *btns, ad_type=ad_type)


@app.get("/ppts/{ppt_id}/pdfs/{pdf_id}")
def get_pdf(sess, ppt_id: int, pdf_id: int):
    pdf = s.ppt_pdfs[pdf_id]
    if sess["auth_r"] in const.EMPLOYEES:
        return fh.Titled(
            "PDF",
            fh.Embed(
                src=pdf["name"],
                type="application/pdf",
                style="width: 100%; height: 1000px;",
            ),
        )


@app.get("/adrs_frm")
async def get_adrs_frm(sess, req, d: dict):
    """
    Return address registration form or redirect to ppt if it exists.
    """
    cnb = {}
    cnb_str = ""
    ppt_type = int(d.get("ppt_type"))

    for k in s.CNB_FLDS:
        cnb[k] = d.get(k)
        cnb_str += f" and a.{k} = ?"
    qry = f"""
    SELECT p.*
    FROM properties as p
    LEFT JOIN addresses as a ON p.adrs_id = a.id
    WHERE p.ppt_type = ?{cnb_str}
    """
    ppt = s.db.q(qry, (ppt_type, *cnb.values()))
    if ppt:
        p = ppt[0]
        ppt_id = p["id"]
        btn_path = "unit_frm"
        flds = []  # extra flds for unit table
        if sess["auth_r"] in const.EMPLOYEES:
            flds.append("edit")
        return c.get_dialog(
            "imovel",
            await c.get_ppt_infr_img_units(ppt_id, sess["auth"], flds, btn_path),
        )
    frm = fh.Form(
        fh.Hidden(name="ppt_type", value=ppt_type),
        c.get_adrs_flds(cnb),
        fh.Grid(fh.Button("Back", hx_get="/check_ppt_frm"), fh.Button("Next")),
        hx_post="/adrs",
    )
    f_frm = fh.fill_form(frm, d)
    return c.get_dialog(f"Cadastrar {const.PPT_TYPE.get(ppt_type)}", f_frm)


@app.get("/check_ppt_frm")
async def get_ppt_check_frm():
    frm = fh.Form(
        c.slct_fld("ppt_type", const.PPT_TYPE),
        *(fh.Label(const.RENAME_FLDS[k], fh.Input(name=k)) for k in s.CNB_FLDS),
        fh.Button("Next", type="submit"),
        hx_get="/adrs_frm",
        hx_params="*",
        hx_trigger="submit",
        hx_target="#dialog",
    )
    return c.get_dialog("Cadastrar Imovel", frm)


@fh.patch
def __ft__(self: s.USER):
    role = const.ROLE_TYPE.get(self.role)
    show = (
        fh.AX(f"{self.name}", f"/users/{self.id}", "dialog"),
        f': {role}, email: {self.email}, phone: {self.phone if self.phone else "na"}',
    )
    edit = fh.AX("edit", f"/users/{self.id}/edit", "dialog")
    cts = (
        *show,
        " | ",
        edit,
        fh.Hidden(id="id", value=self.id),
        fh.Hidden(id="priority", value="0"),
    )
    return fh.Li(*cts, id=f"user-{self.id}")


@app.get("/users")
async def get_users(sess):
    if sess["auth_r"] in (s.Role.ADMIN, s.Role.SECRETARY):
        return await c.get_workspace_for(s.users)


@app.get("/users/{id}")
def get_user(sess, id: int):
    if sess["auth"] == id or sess["auth_r"] in const.EMPLOYEES:
        usr = s.users[id]
        return c.get_dialog(f"User {usr.name}", usr)


@app.get("/users/{id}/edit")
async def get_user_edit(sess, id: int):
    add_flds = (
        fh.Hidden(id="id"),
        fh.Hidden(id="role"),
        fh.Input(id="pwd"),
    )
    res = fh.Form(
        c.get_usr_flds(*add_flds),
        fh.Button("Save"),
        hx_put="/users",
        target_id=f"user-{id}",
        id="edit",
    )
    usr = s.users[id]
    frm = fh.fill_form(res, usr)
    return c.get_dialog(f"User {usr.name}", frm)


@app.get("/tasks")
def get_tasks(sess):
    if sess["auth_r"] == s.Role.BROKER:
        tasks = [
            fh.Li(
                fh.AX(
                    fh.Card(
                        f"Description: {t['initial_dscr']}",
                        header=fh.AX(
                            t["start_date"],
                            hx_get=f"/ppts?ad_type={t['ad_type']}&ppt_type={t['ppt_type']}&task_id={t['id']}&action=add_params",
                            hx_target="#result",
                        ),
                    )
                )
            )
            for t in s.tasks.rows_where(
                "broker_id = ? AND status IN (?, ?)",
                (sess["auth"], s.Status.NEW, s.Status.ACTIVE),
            )
        ]
        return fh.Titled("Tasks:", fh.Ul(*tasks), id="result")
    else:
        return fh.Div(id="result")


@app.put("/users")
async def edit_user(user: s.USER):
    return s.users.update(user), cls_details()


@fh.patch
def __ft__(self: s.PPT):
    adrs = c.get_adrs(self.adrs_id)
    pt = const.PPT_TYPE.get(self.ppt_type)
    show = f"{self.id}. {pt}: {adrs}"
    edit = fh.AX("edit", f"/ppts/{self.id}/edit", "dialog")
    cts = (show, " | ", edit, fh.Hidden(id="id", value=self.id))
    return fh.Li(*cts, id=f"ppt-{self.id}")


@rt
def get_price_fld(ad_type: int):
    fld = const.AD_TYPE_FLDS[ad_type]
    return fh.Div(
        c.range_container(
            fld, **const.RANGES[fld], rename=f"{const.RENAME_FLDS[fld]}, R$/m2"
        ),
        id="price_type",
        hx_swap_oob="true",
    )


@rt
async def get_ppts_fld(ppt_type: int):
    range_flds = s.UNIT_RANGE_FLDS
    rnm = await c.get_renamed_flds_for(ppt_type)
    if ppt_type == s.PropertyType.WAREHOUSE:
        range_flds += s.WH_RANGE_FLDS
    return fh.Div(
        tuple(
            c.range_container(k, **const.RANGES[k], rename=rnm[k]) for k in range_flds
        ),
        id="ppt_type",
        hx_swap_oob="true",
    )


@app.get("/filters")
async def get_filters(sess, req, ad_type: int, ppt_type: int):
    my_dict = {**req.query_params}
    frm = fh.Form(
        await c.get_fltr(ad_type, ppt_type),
        fh.Button("Buscar", type="submit", id="action", value="search"),
        hx_get="/ppts",
        hx_params="*",
        hx_trigger="submit",
        hx_target="#result",
    )
    frm = fh.fill_form(frm, my_dict)
    return c.get_dialog("filters", frm, cls_btn="cls_fltr"), cls_details("short-fltr")


@app.get("/ppts")
async def get_ppts(sess, req):
    role = sess.get("auth_r", const.ANONIM)
    d = {**req.query_params}
    if d:
        ppt_type = int(d["ppt_type"])
        ad_type = int(d["ad_type"])
        query = f"?ad_type={ad_type}"
        if role in const.EMPLOYEES:
            ppt_id = d.get("ppt_id")
            tsk_id = d.get("task_id")
            if tsk_id:
                query += f"&task_id={tsk_id}"
                action = d.get("action")
                if action == "save":
                    await c.save_task_params(d)
                elif action == "add_params":
                    tbl = s.PPT_TSK_TABLES[ppt_type]
                    tsk_params = list(tbl.rows_where("task_id = ?", (int(tsk_id),)))[0]
                    price_fld = const.AD_TYPE_FLDS[ad_type]
                    qry = """
                    SELECT c.name
                    FROM task_cities as tc
                    LEFT JOIN cities as c ON tc.city_id = c.id
                    WHERE task_id = ?
                    """
                    d["city_id"] = list(k["name"] for k in s.db.q(qry, (int(tsk_id),)))
                    for k in const.MIN_MAX:
                        tsk_params[f"{price_fld}_{k}"] = tsk_params[f"price_{k}"]
                    for k, v in tsk_params.items():
                        if k.endswith("_min") or k.endswith("_max"):
                            v = str(v)
                            d[k] = v
                            d[f"{k}_handler"] = v
            if ppt_id:
                ppt_id = ppt_id.strip().lower()
                if ppt_id.startswith("ret"):
                    ppt_id = int(ppt_id[3:])
                elif ppt_id.isalnum():
                    ppt_id = int(ppt_id)
                else:
                    fh.add_toast(sess, "Wrong ref.", "error")
                    return fh.Div(
                        fh.Group(
                            fh.Input(
                                type="search", name="ppt_id", placeholder="search"
                            ),
                            fh.Button("Search", type="submit", role="search"),
                        ),
                        id="srch_btn",
                        hx_swap_oob="true",
                    )
                if tsk_id:
                    tsk = s.tasks[tsk_id]
                    return await c.get_ppt_infr_img_units(
                        ppt_id,
                        tsk["client_id"],
                        ["select", "edit"],
                        "comparisons",
                        ad_type=ad_type,
                    )
                return await c.get_ppt_infr_img_units(
                    ppt_id, int(sess["auth"]), ["edit"], ad_type=ad_type
                )
        unit_tbl = s.PPT_TABLE_NAMES.get(ppt_type)
        qry = f"""
        SELECT p.id, a.location, p.ppt_type, p.name,
        c.name AS city, s.name AS street,
        GROUP_CONCAT(DISTINCT pi.name) AS images,
        SUM(area) as max_area,
        MIN(area) as min_area,
        MIN({const.AD_TYPE_FLDS[ad_type]}) as price
        FROM addresses AS a
        LEFT JOIN cities AS c ON a.city_id = c.id
        LEFT JOIN streets AS s ON a.street_id = s.id
        LEFT JOIN properties AS p ON a.id = p.adrs_id
        LEFT JOIN ppt_images AS pi ON p.id = pi.ppt_id
        LEFT JOIN {unit_tbl} AS m ON p.id = m.ppt_id
        GROUP BY p.id
        """
        ppts = s.db.q(qry)
        if ppts:
            locations = [c.ppt_serializer(ppt) for ppt in ppts]
            prefil = d.pop("city_id") if isinstance(d.get("city_id"), list) else None
            frm = await c.short_fltr(ad_type, ppt_type, prefil=prefil)
            frm = fh.fill_form(frm, d)
            return (
                fh.Div(
                    frm,
                    fh.Grid(fh.Ul(id="location-list"), fh.Div(id="map", cls="map")),
                    id="result",
                ),
                fh.Script(c.map_locations_script(locations, query)),
                cls_details(),
            )
        else:
            fh.add_toast(sess, "Não há propriedades com tais parâmetros", "info")
    # handle request without query params
    srch_fld = (
        fh.Div(
            fh.Group(
                fh.Input(type="search", name="ppt_id", placeholder="search"),
                fh.Button("Search", type="submit", role="search"),
            ),
            id="srch_btn",
        )
        if role in const.EMPLOYEES
        else None
    )
    frm = fh.Form(
        srch_fld,
        await c.get_fltr(),
        fh.Button("Buscar", type="submit", id="action", value="search"),
        hx_get="/ppts",
        hx_params="*",
        hx_trigger="submit",
        hx_target="#result",
    )
    return c.get_dialog("Filter", frm)


@app.get("/ppts/{ppt_id}/edit")
async def edit_property(sess, ppt_id: int):
    ppt = s.properties[ppt_id]
    adrs_frm = fh.Form(
        fh.Hidden(id="id", value=ppt.adrs_id),
        c.get_adrs_flds(),
        fh.Button("Save"),
        hx_put="/adrs",
    )
    ppt_frm = await c.get_ppt_frm(ppt.adrs_id, ppt.ppt_type, ppt.id)
    adrs = c.get_adrs(ppt.adrs_id, False)
    frm_adrs = fh.fill_form(adrs_frm, adrs)
    frm_ppt = fh.fill_form(ppt_frm, ppt)
    return c.get_dialog(
        f"Imovel {ppt.name}",
        fh.Div(
            frm_adrs,
            frm_ppt,
            c.get_block_for("pdfs", ppt_id),
            c.get_block_for("infrs", ppt_id),
            c.get_block_for("imgs", ppt_id),
        ),
        z_index=1000,
    )


@app.get("/ppts/{ppt_id}/units/{unit_id}/edit_frm")
async def get_unit_edit_frm(sess, ppt_id: int, unit_id: int):
    ppt = s.properties[ppt_id]
    ppt_type = ppt.ppt_type
    u = s.PPT_UNIT_TABLES[ppt_type][unit_id]
    o = s.users[u["owner_id"]]
    u["owner_id"] = f"{o.name} - {o.email} - {o.id}"
    frm = await c.get_unit_frm(sess, ppt_type, ppt_id, for_edit=True)
    return c.get_dialog(
        f'Editar unidade {u["title"]}',
        fh.fill_form(frm, u),
    )


@app.route("/ppts/{ppt_id}/units", methods=["PUT", "POST"])
async def edit_unit(sess, req, ppt_id: int, unit: dict):
    print(f"{unit=}")
    owner = unit["owner_id"].split(" - ")
    if len(owner) != 3:
        return None
    u = unit.copy()
    ppt_type = int(u.pop("ppt_type"))
    u["owner_id"] = owner[-1]
    u["ppt_id"] = ppt_id
    tbl = s.PPT_UNIT_TABLES[ppt_type]
    text = f'Unidade {unit["title"]} foi '
    bool_flds = (
        s.WH_BOOL_FLDS
        if ppt_type == s.PropertyType.WAREHOUSE
        else ("under_construction",)
    )
    for k in bool_flds:
        u[k] = bool(u.get(k))

    if req.method == "PUT":
        tbl.update(u)
        text += "editada"
    else:
        action = u.pop("action")
        u["last_update"] = int(time.time())
        u["status"] = s.Status.ACTIVE
        tbl.insert(u)
        text += "adicionada"
        if action == "add":
            del unit["title"]
            frm = await c.get_unit_frm(sess, ppt_type, ppt_id)
            frm = fh.fill_form(frm, unit)
            fh.add_toast(sess, text, "success")
            return frm
    fh.add_toast(sess, text, "success")
    return cls_details()


@app.get("/{ppt_id}/imgs")
async def get_imgs(ppt_id: int):
    return c.get_dialog(
        "Fotos",
        fh.Grid(
            *(await c.get_embeded_imgs(ppt_id)), style="grid-template-columns: 1fr 1fr"
        ),
    )


@app.post("/{ppt_id}/{path}")
async def create_item(ppt_id: int, path: str, d: dict):
    items = list()
    fls = d[path]
    if fls:
        if not isinstance(fls, list):
            fls = (fls,)
        for itm in fls:
            i = await c.save_item(path, ppt_id, itm)
            items.append(c.show_item(path, ppt_id, i))
    inp_prms = dict(id=f"new_{path}", name=path, hx_swap_oob="true")
    if path != "infrs":
        inp_prms.update(type="file", multiple=True)

    return *items, fh.Input(**inp_prms)


@app.delete("/ppts/{ppt_id}/{path}/{item_id}")
async def delete_item(ppt_id: int, item_id: int, path: str):
    if path == "infrs":
        s.ppt_infrastructures.delete_where(
            "infr_id = ? and ppt_id = ?", (item_id, ppt_id)
        )
    else:
        c.delete_file(path, item_id)
    return cls_details(f"{path}-{item_id}")


@app.get("/ppts/{ppt_id}/infrs/{infr_id}")
def get_infr_frm(ppt_id: int, infr_id: int):
    div_id = const.INFR_EDIT
    res = fh.Form(
        fh.Hidden(id="id"),
        fh.Input(id="name"),
        fh.Button("Save"),
        hx_put="/infrs",
        target_id=f"infrs-{infr_id}",
        id="edit",
    )
    infr = s.infrastructures[infr_id]
    hdr = fh.Div(
        fh.Button(
            aria_label="Close",
            rel="prev",
            hx_get=f"/cls_details/{div_id}",
            hx_swap="outerHTML",
        ),
        fh.P(f'Editar {infr["name"][:10]}'),
    )
    frm = fh.fill_form(res, infr)
    return fh.Div(fh.Card(frm, header=hdr), id=div_id, hx_swap_oob="true")


@app.put("/infrs")
def edit_infr(infr: dict):
    s.infrastructures.update(infr)
    return c.show_item("infrs", infr["ppt_id"], infr), cls_details(const.INFR_EDIT)


async def get_employee_view(sess):
    return await c.get_body_layout(
        fh.Div(
            fh.Div(
                fh.Group(
                    fh.AX("Negócios", "/tasks", "result"),
                    fh.Button(
                        "+",
                        data_tooltip="Adicionar Novo Negócio",
                        hx_get="/task_frm",
                        hx_target="#dialog",
                    ),
                    cls="body-hdr",
                ),
                fh.Group(
                    fh.AX("Imoveis", "/ppts", "result"),
                    fh.Button(
                        "+",
                        data_tooltip="Cadastrar imovel",
                        type="button",
                        hx_get="/check_ppt_frm",
                        hx_target="#dialog",
                    ),
                    cls="body-hdr",
                ),
                fh.Group(
                    fh.AX("Usuarios", "/users", "result"),
                    fh.Button(
                        "+",
                        hx_get="/register",
                        hx_target="#register",
                        data_tooltip="Cadastrar Usuario",
                    ),
                    cls="body-hdr",
                ),
                id="navbar",
            ),
            get_tasks(sess),
            fh.Div(id="result"),
            cls="body-grid",
        ),
        fh.Div(id="edit"),
    )


async def get_user_view(sess):
    return await c.get_body_layout(
        fh.Div(await c.short_fltr(), id="result"),
    )


async def footer_section():
    """Footer section. Useful links"""
    cur_year = dt.now().year
    return fh.Div(
        # fh.Grid(fh.P('Links Rápidos'), fh.P('Contato')),
        fh.P(f"Retha ©{cur_year} - Todos os direitos reservados."),
        id="footer",
    )


scripts = (
    fh.Script(
        src=f"https://maps.googleapis.com/maps/api/js?key={s.GOOGLE_API}&callback=initMap&v=3&libraries=marker",
        defer=True,
    ),
    fh.Script(src="https://unpkg.com/@googlemaps/markerclusterer/dist/index.min.js"),
)

from fastcore.xtras import timed_cache


@timed_cache(seconds=60)
async def home(sess):
    role = sess.get("auth_r", const.ANONIM)
    body_section = (
        get_user_view if role in (s.Role.USER, const.ANONIM) else get_employee_view
    )
    return (
        fh.Title(f"Retha - {const.DESCR}"),
        *scripts,
        # fh.Div(id='sidebar'),
        fh.Main(
            await header_section(sess),
            await body_section(sess),
            fh.Div(id="dialog"),
            fh.Div(id="register"),
        ),
    )


@app.get("/")
async def homepage(sess):
    return await home(sess)


fh.serve()
