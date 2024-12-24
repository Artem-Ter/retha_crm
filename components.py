import asyncio
import json
from collections import ChainMap
from datetime import datetime as dt

import aiofiles.os
import const
import fasthtml.common as fh
import mysettings as s
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

_blank = dict(target="_blank", rel="noopener noreferrer")
_flex = "display: flex; flex-wrap: wrap; align-content: flex-start; gap: 1em;"
_grid = "display: grid; gap: 1.5rem; grid-template-columns: 1fr 1fr 1fr"


async def save_item(path: str, ppt_id: int, item):
    if path == "infrs":
        infr = {"name": item, "id": get_or_create("infr_id", item)}
        s.ppt_infrastructures.insert(ppt_id=ppt_id, infr_id=infr["id"])
        return infr
    # logic for pdf and images
    item_filename = f"{ppt_id}_{item.filename}"
    tbl = s.FILE_TABLES[path]
    if path == "pdfs":
        item_path = s.PDF_DIR / item_filename
    else:
        item_path = s.IMG_DIR / item_filename
    # Save file to the server
    with item_path.open("wb") as f:
        f.write(await item.read())
    _path = f"/{path}/{item_filename}"
    i = tbl.insert({"ppt_id": ppt_id, "name": _path})
    return i


def get_or_create(field: str, name: str | None = None) -> int:
    """Get or create item in db. Return item id"""
    tbl = s.FK_TABLES.get(field)
    srch = ["", name][bool(name)]
    itm = tbl.rows_where(
        "LOWER(name) = ?",
        (srch.lower(),),
        select="id",
        limit="1",
    )
    itm = list(itm)
    if itm:
        return itm[0]["id"]

    itm = tbl.insert(name=name)
    return itm["id"]


async def delete_pdf(fpath: str):
    await aiofiles.os.remove(fpath)


def get_tbl_flds_for(ppt_type: int, ad_type: int | None, *args) -> list:
    flds = [*args, "title", "available", "area"]
    price_flds = [
        "sell",
        "rent",
    ]
    if ad_type:
        price_flds = [["sell"], ["price", "rent"]][ad_type == s.AdType.RENT]
    if ppt_type == s.PropertyType.WAREHOUSE:
        flds += ["efficiency"] + price_flds + [*s.PPT_COSTS_FLDS]
        flds += [
            *s.WH_BOOL_FLDS,
            *s.WH_RANGE_FLDS,
            "between_pilars",
        ]
        return flds
    flds += price_flds + [*s.PPT_COSTS_FLDS]
    return flds


async def get_renamed_flds_for(
    ppt_type: int | None = None, price_per_month: bool = False
) -> dict:
    d = const.RENAME_FLDS.copy()
    if ppt_type == s.PropertyType.WAREHOUSE:
        d["area"] = "ABL, m2"
    add = "R$/mes" if price_per_month else "R$/m2"
    for k in ("price", *s.PPT_COSTS_FLDS, *s.RENT_SELL_FLDS):
        d[k] = f"{d[k]}, {add}"
    return d


def delete_file(path: str, id: int):
    t = s.FILE_TABLES[path]
    item = t[id]
    link = s.BASE_DIR / item["name"][1:]
    link.unlink()
    t.delete(id)


async def save_task_params(d: dict) -> None:
    for k, tbl in s.TSK_MULT_FK.items():
        if d.get(k):
            items = d[k] if isinstance(d.get(k), list) else [d[k]]
            for itm in items:
                if itm:
                    tbl.insert({"task_id": d["task_id"], k: get_or_create(k, itm)})
    ppt_type = int(d["ppt_type"])
    tbl = s.PPT_TSK_TABLES[ppt_type]
    for m in ("min", "max"):
        d[f"price_{m}"] = (
            d.get(f"rent_{m}") if d.get(f"rent_{m}") else d.get(f"sell_{m}")
        )
    params = ChainMap(s.PPT_TSK_PARAMS[ppt_type], {"task_id": int})
    tbl.insert({k: v(d[k]) for k, v in params.items() if d.get(k)})


def get_loginout_fld(out: bool = False, **kwargs):
    s = ["login", "logout"][out]
    t = ["#register", "#login-section"][out]
    return fh.Div(
        fh.Strong(fh.AX(s.capitalize(), hx_get=f"/{s}", hx_target=t)),
        id="login-section",
        **kwargs,
    )


def get_hdr_flds(sess, role, **kwargs) -> tuple:
    usr_id = sess.get("auth", const.ANONIM)
    if role in const.EMPLOYEES:
        rfld = fh.Strong(fh.AX("Tasks", hx_get="/tasks", hx_target="#result"))
        lfld = fh.Strong(fh.A("Dashboard", href="/dashboard", **_blank))
    else:
        rfld = fh.Strong(fh.A("Comparisons", href="/comparisons", **_blank))
        lfld = fh.Strong(fh.A("Retha", href="/"))
    return (
        fh.Div(lfld, id="hdr-left-fld", **kwargs),
        fh.Div(rfld, id="hdr-right-fld", **kwargs),
    )


def get_dialog(
    hdr_msg: str,
    item,
    div_id: str = "dialog",
    z_index: int = 500,
    cls_btn: str = "cls_details",
) -> fh.DialogX:
    hdr = fh.Div(
        fh.Button(
            aria_label="Close",
            rel="prev",
            hx_get=f"/{cls_btn}/{div_id}",
            hx_include=f"#{div_id}",
            hx_swap="outerHTML",
        ),  # Close button
        fh.P(hdr_msg),
    )
    return fh.DialogX(
        item,
        open=True,
        header=hdr,
        id=div_id,
        hx_swap="outerHTML",
        style=f"z-index: {z_index}",
    )


def slct_fld(nm: str, cs: dict, multiple: bool = False, **kwargs) -> fh.Select:
    return fh.Label(
        const.RENAME_FLDS[nm],
        fh.Select(
            *[fh.Option(v, value=str(k)) for k, v in cs.items()],
            name=nm,
            multiple=multiple,
            **kwargs,
        ),
    )


def range_script(prefix: str):
    return f"""
function updateSliderValues(prefix) {{
    console.log("updateSliderValues is triggered for: " + prefix)
    var minHandler = document.getElementById(prefix + "_min_handler");
    var maxHandler = document.getElementById(prefix + "_max_handler");
    var minInput = document.getElementById(prefix + "_min");
    var maxInput = document.getElementById(prefix + "_max");
    var range = document.getElementById(prefix + "_selected");

    var minValue = parseInt(minHandler.value);
    var maxValue = parseInt(maxHandler.value);

    // Determine which slider is further left and which is further right
    if (minValue > maxValue) {{
        [minValue, maxValue] = [maxValue, minValue];  // Swap the values if needed
    }}

    // Update the input fields with slider values
    minInput.value = minValue;
    maxInput.value = maxValue;

    // Update the slider track background to color the range in blue
    fillrange(minHandler, maxHandler, range);
}}

function updateInputFields(prefix) {{
    var minHandler = document.getElementById(prefix + "_min_handler");
    var maxHandler = document.getElementById(prefix + "_max_handler");
    var minInput = document.getElementById(prefix + "_min");
    var maxInput = document.getElementById(prefix + "_max");
    var range = document.getElementById(prefix + "_selected");

    var minValue = parseInt(minInput.value);
    var maxValue = parseInt(maxInput.value);

    // Prevent the minimum input from exceeding the maximum input
    if (minValue > maxValue) {{
        minValue = 0;  // Swap the values if needed
    }}

    // Update the sliders with input values
    minHandler.value = minValue;
    maxHandler.value = maxValue;

    // Trigger the slider value update logic
    updateSliderValues(prefix);
}}

// Color the track between the two slider handles
function fillrange(minHandler, maxHandler, range) {{
    var rangeMin = parseInt(minHandler.min);
    var rangeMax = parseInt(maxHandler.max);
    var minValue = Math.min(minHandler.value, maxHandler.value);
    var maxValue = Math.max(minHandler.value, maxHandler.value);

    var leftPercentage = ((minValue - rangeMin) / (rangeMax - rangeMin)) * 100 + "%";
    var rightPercentage = ((rangeMax - maxValue) / (rangeMax - rangeMin)) * 100 + "%";

    range.style.left = leftPercentage;
    range.style.right = rightPercentage;
    
}}

// Attach event listeners to the input fields for initial setup
document.getElementById("{prefix}_min").addEventListener("change", function() {{ updateInputFields('{prefix}'); }});
document.getElementById("{prefix}_max").addEventListener("change", function() {{ updateInputFields('{prefix}'); }});

// Attach event listeners to the slider handles
document.getElementById("{prefix}_min_handler").addEventListener("input", function() {{ updateSliderValues('{prefix}'); }});
document.getElementById("{prefix}_max_handler").addEventListener("input", function() {{ updateSliderValues('{prefix}'); }});

// Initialize the slider with the correct track fill
window.addEventListener('load', function() {{
    updateSliderValues('{prefix}');
}});

document.body.addEventListener('htmx:afterSettle', function() {{
    console.log("HTMX swap completed for prefix:", '{prefix}');
    updateSliderValues('{prefix}');  // Reinitialize slider after HTMX swap
}});
"""


def range_container(field: str, minimum: int, maximum: int, step: int, rename: str):
    d = {"min": minimum, "max": maximum}
    return fh.Div(
        fh.Label(
            rename,
            fh.Div(
                fh.Grid(
                    *(
                        fh.Label(
                            k.capitalize(),
                            fh.Input(
                                id=f"{field}_{k}",
                                type="number",
                                value=str(v),
                                min=str(minimum),
                                max=str(maximum),
                                step=str(step),
                            ),
                        )
                        for k, v in d.items()
                    )
                )
            ),
            fh.Div(
                fh.Span(id=f"{field}_selected", cls="range-selected"),
                cls="range-slider",
            ),
            fh.Div(
                *(
                    fh.Input(
                        id=f"{field}_{k}_handler",
                        type="range",
                        value=str(v),
                        min=str(minimum),
                        max=str(maximum),
                        step=str(step),
                    )
                    for k, v in d.items()
                ),
                cls="range-input",
            ),
            cls="range",
        ),
        fh.Script(range_script(field)),
    )


def autocomplete_script(prefix: str, multiple: bool):
    return f"""
    // Use 'me' and 'any' from Surreal for streamlined DOM interaction

    // Show dropdown and filter options when typing
    me("#{prefix}").on("input", ev => {{
        let filter = me(ev).value.toLowerCase();
        let options = any("#{prefix}_dropdown li");

        options.forEach(option => {{
            if (option.textContent.toLowerCase().includes(filter)) {{
                option.style.display = "";  // Show matching option
            }} else {{
                option.style.display = "none";  // Hide non-matching option
            }}
        }});

        me("#{prefix}_dropdown").style.display = "block";  // Show dropdown
    }});

    // Select an option from the dropdown
    any("#{prefix}_dropdown li").on("click", ev => {{
        let value = me(ev).textContent;
        let prefix = "{prefix}";
        
        if ({'true' if multiple else 'false'}) {{            
            addSelectedOption(value, prefix);  // Handle multiple selection
            me("#" + prefix).value = "";  // Clear input after selection for multiple
        }} else {{
            me("#{prefix}").value = value;  // Handle single selection
        }}

        me("#{prefix}_dropdown").style.display = "none";  // Hide dropdown after selection
    }});

    // Add custom option on Enter key press for multiple selections
    me("#{prefix}").on("keydown", ev => {{
        if (ev.key === "Enter") {{
            ev.preventDefault();  // Prevent form submission
            let value = me("#{prefix}").value.trim();
            let prefix = "{prefix}";
            if (value) {{
                if ({'true' if multiple else 'false'}) {{
                    addSelectedOption(value, prefix);  // Add custom option for multiple
                    me("#{prefix}").value = "";  // Clear input after Enter for multiple
                }} else {{
                    me("#{prefix}").value = value;  // For single selection, put the value in the input
                }}
                me("#{prefix}_dropdown").style.display = "none";  // Hide dropdown
            }}
        }}
    }});

    // Close the dropdown when clicking outside the input or dropdown
    document.addEventListener("click", function(event) {{
        let input = me("#{prefix}");
        let dropdown = me("#{prefix}_dropdown");

        // Close dropdown if the click is outside the input or dropdown
        if (!input.contains(event.target) && !dropdown.contains(event.target)) {{
            dropdown.style.display = "none";
        }}
    }});

    // Function to add a selected option below the input and add a hidden input
    function addSelectedOption(value, prefix) {{
        let selected = "#" + prefix + "_selected";
        let hidden = "#" + prefix + "_hidden";
        let selected_span = "#" + prefix + "_selected span";
        
        let selectedContainer = me(selected);
        let hiddenContainer = me(hidden);
        let existingOptions = any(selected_span).map(option => option.textContent.trim());

        if (!existingOptions.includes(value)) {{
            let selectedItem = document.createElement("span");
            selectedItem.className = "selected-item";
            selectedItem.innerHTML = `${{value}} <button type="button" onclick="removeSelectedOption(this, '${{prefix}}', '${{value}}')">x</button>`;
            selectedContainer.appendChild(selectedItem);

            // Create a hidden input field to hold the value
            let hiddenInput = document.createElement("input");
            hiddenInput.type = "hidden";
            hiddenInput.name = prefix;  // Treat as an array input
            hiddenInput.value = value;
            hiddenInput.id = prefix + "_hidden_" + value.replace(/\\s+/g, '_');  // Unique ID
            hiddenContainer.appendChild(hiddenInput);
        }}
    }}

    // Function to remove selected option and its corresponding hidden input
    function removeSelectedOption(button, prefix, value) {{
        me(button).parentElement.remove();  // Remove selected option from view
        let hiddenInput = me("#" + prefix + "_hidden_" + value.replace(/\\s+/g, '_'));
        if (hiddenInput) {{
            hiddenInput.remove();  // Remove the hidden input
        }}
    }}
    """


def get_autocomplete_for(
    field: str,
    multiple: bool = False,
    tp: str = "text",
    labled: bool = True,
    prefil: list | None = None,
):
    """
    Provide autocomplete field with options from db.table. For tables with name fld.
    """
    fld = fh.Input(
        id=field,
        type=tp,
        placeholder=const.RENAME_FLDS[field],
        autocomplete="off",  # Disable default browser autocomplete
    )
    if labled:
        fld = fh.Label(
            const.RENAME_FLDS[field],
            fld,
        )
    return fh.Div(
        fld,
        fh.Ul(
            *[
                fh.Li(option["name"], value=option["id"], cls="dropdown-item")
                for option in get_tbl_options(field)
            ],  # Render the options dynamically with class
            id=f"{field}_dropdown",
            cls="dropdown-list",
            style="display:none;",  # Hide dropdown initially
        ),
        fh.Div(
            *[mult_choice(s, field) for s in prefil if s] if prefil else [],
            id=f"{field}_selected",
            style="display: flex; justify-content: flex-start;",
        ),  # Container for selected options
        fh.Div(
            id=f"{field}_hidden"
        ),  # Container for hidden inputs (submitted with form)
        fh.Script(
            autocomplete_script(field, multiple)
        ),  # Add the dynamic filtering and selection script
    )


async def short_fltr(
    ad_type: int = s.AdType.RENT,
    ppt_type: int = s.PropertyType.WAREHOUSE,
    prefil: list | None = None,
):
    ad_fld = const.AD_TYPE_FLDS[ad_type]
    btns = fh.Grid(
        fh.Button(
            "Buscar", hx_get="/ppts", hx_target="#result", hx_include="#short-fltr"
        ),
        fh.Button(
            "Mais filtros",
            hx_get="/filters",
            hx_target="#dialog",
            hx_include="#short-fltr",
        ),
    )
    ppt_flds = (
        (
            (
                fh.Hidden(
                    name=f"{k}_{m}", value=str(const.RANGES[k][const.MIN_MAX[m]])
                ),
                fh.Hidden(
                    name=f"{k}_{m}_handler",
                    value=str(const.RANGES[k][const.MIN_MAX[m]]),
                ),
            )
            for k in s.WH_RANGE_FLDS
            for m in ("min", "max")
        )
        if ppt_type == s.PropertyType.WAREHOUSE
        else tuple()
    )

    rnm = await get_renamed_flds_for(ppt_type)
    return fh.Div(
        fh.Form(
            fh.Grid(
                get_ad_ppt_type_flds(),
                get_autocomplete_for("city_id", prefil=prefil),
                fh.Div(
                    range_container(ad_fld, **const.RANGES[ad_fld], rename=rnm[ad_fld]),
                    id="price_type",
                ),
                fh.Div(
                    (
                        range_container(k, **const.RANGES[k], rename=rnm[k])
                        for k in s.UNIT_RANGE_FLDS
                    ),
                ),
            ),
            *(fh.Hidden(name=k) for k in s.PPT_CHOICE_FLDS),
            *ppt_flds,
            fh.Hidden(name="region_id"),
            fh.Hidden(name="district_id"),
            fh.Hidden(name="avcb_id"),
            fh.Hidden(name="infr_id"),
        ),
        btns,
        id="short-fltr",
    )


def map_locations_script(d: list, query: str):
    return f"""
async function initMap() {{
    const map = new google.maps.Map(document.getElementById("map"), {{
        zoom: 4,
        center: {{ lat: -23.533773, lng: -46.62529 }},
        mapId: "DEMO_MAP_ID",
    }});

    const infoWindow = new google.maps.InfoWindow({{
        content: "",
    }});

    const locations = {json.dumps(d)};  // 'd' is passed from Python as a list of locations
    let markers = locations.map(poi => {{
        const marker = new google.maps.Marker({{
            position: poi.location,
            map: map,
            title: poi.name
        }});

        return marker;
    }});

    new markerClusterer.MarkerClusterer({{ markers, map }});

    // Function to update the list of visible markers
    function updateLocationList() {{
        const bounds = map.getBounds();
        const visibleLocations = locations.filter(poi => bounds.contains(new google.maps.LatLng(poi.location.lat, poi.location.lng)));
        const locationList = document.getElementById("location-list");

        locationList.innerHTML = visibleLocations.map(poi => `
            <article class="card">
                <div class="carousel" id="carousel-${{poi.id}}">
                    ${{poi.images.map((img, index) => `
                        <div class="carousel-item ${{index === 0 ? 'active' : ''}}">
                            <img src="${{img}}" alt="Image ${{index + 1}}">
                        </div>
                    `).join('')}}
                    <button class="carousel-control left" onclick="prevSlide('${{poi.id}}')">&#10094;</button>
                    <button class="carousel-control right" onclick="nextSlide('${{poi.id}}')">&#10095;</button>
                </div>
                <a href='/ppts/${{poi.id}}{query}' style="text-decoration: none; color: inherit;" target="blank">
                    <div class="content">
                        <h5>${{poi.ppt_type}}: ${{poi.name}}</h5>
                        <h6>Preço a partir de: ${{poi.price}} R$/m2</h6>
                        <p>Area disponivel: ${{poi.min_area}} - ${{poi.max_area}} m2</p>
                        <p>${{poi.street}}, ${{poi.city}}</p>
                    </div>
                </a>
            </article>
        `).join("");
    }}

    // Add listeners for zoom or drag events to update the list
    map.addListener("bounds_changed", updateLocationList);
    map.addListener("zoom_changed", updateLocationList);

    // Initial update for the location list after map tiles have loaded
    google.maps.event.addListenerOnce(map, 'tilesloaded', updateLocationList);
}}

document.body.addEventListener("htmx:afterSettle", function(evt) {{
    if (document.querySelector("#map")) {{
        initMap();  
    }}
}}, {{ passive: true }});

// Carousel functions
function nextSlide(id) {{
    const carousel = document.querySelector(`#carousel-${{id}}`);
    const items = carousel.querySelectorAll('.carousel-item');
    let currentIndex = Array.from(items).findIndex(item => item.classList.contains('active'));

    items[currentIndex].classList.remove('active');
    const nextIndex = (currentIndex + 1) % items.length;
    items[nextIndex].classList.add('active');
}}

function prevSlide(id) {{
    const carousel = document.querySelector(`#carousel-${{id}}`);
    const items = carousel.querySelectorAll('.carousel-item');
    let currentIndex = Array.from(items).findIndex(item => item.classList.contains('active'));

    items[currentIndex].classList.remove('active');
    const prevIndex = (currentIndex - 1 + items.length) % items.length;
    items[prevIndex].classList.add('active');
}}
"""


def map_comparisons_script(d: list):
    return f"""
async function initMap() {{
    const map = new google.maps.Map(document.getElementById("comparisons-map"), {{
        zoom: 4,
        center: {{ lat: -23.533773, lng: -46.62529 }},
        mapId: "DEMO_MAP_ID",
    }});

    const infoWindow = new google.maps.InfoWindow({{
        content: "",
    }});

    const locations = {json.dumps(d)};  // 'd' is passed from Python as a list of locations
    let markers = locations.map(poi => {{
        const marker = new google.maps.Marker({{
            position: poi.location,
            map: map,
            title: poi.name
        }});
        return marker;
    }});
    new markerClusterer.MarkerClusterer({{ markers, map }});
}}

// Directly call initMap on window load
window.addEventListener("load", function () {{
    initMap();
}});
"""


def ppt_serializer(ppt) -> dict:
    ppt["location"] = json.loads(ppt.get("location"))
    ppt["images"] = ppt.get("images").split(",") if ppt.get("images") else s.DEFAULT_IMG
    ppt_type = int(ppt["ppt_type"])
    ppt["ppt_type"] = const.PPT_TYPE[ppt_type]
    return ppt


def arrow(d):
    return fh.Button(
        fh.Img(src=f"/assets/icons/arrow-{d}.svg", alt="Arrow left"),
        cls="disabled:opacity-40 transition-opacity",
        id=f"slide{d.capitalize()}",
        aria_label=f"Slide {d}",
    )


def carousel(items, id="carousel-container"):
    arrows = fh.Div(
        fh.Div(
            arrow("left"),
            arrow("right"),
        ),
    )
    return fh.Div(
        fh.Div(*items, id=id),
        arrows,
    )


def mk_opts(nm, cs):
    return (fh.Option(v, value=k) for k, v in cs.items())


async def get_body_layout(*args, **kwargs):
    return fh.Container(
        fh.Div(
            *args,
            hx_swap_oob="true",
            id="body",
            **kwargs,
        )
    )


async def get_workspace_for(table):
    hdr = fh.Div(
        fh.Group(
            fh.Input(type="search", name="search", placeholder="search"),
            fh.Button("Search", type="submit", role="search"),
        ),
        fh.Select(fh.Option("Ordena por", selected="", disabled="", value="")),
        cls="header-grid",
    )
    return fh.Card(
        fh.Ul(
            fh.Form(*table(order_by="id"), id="item-list"),
        ),
        header=hdr,
    )


def get_usr_flds(*args) -> tuple:
    return (
        fh.Input(name="name", type="name", placeholder="Nome"),
        fh.Input(name="email", type="email", placeholder="Email"),
        fh.Input(name="phone", type="phone", placeholder="Cellular"),
        fh.Input(name="organization", type="organization", placeholder="Empresa"),
        *args,
    )


def get_adrs_flds(cnb: dict | None = None) -> tuple:
    hidden_flds = []
    adrs_flds = [get_autocomplete_for(k) for k in s.CDRS_FK]
    if cnb:
        for k in s.CNB_FLDS:
            adrs_flds.append(
                fh.Label(const.RENAME_FLDS[k], fh.Input(name=k, disabled=True))
            )
            hidden_flds.append(fh.Hidden(name=k, value=cnb[k]))

    else:
        adrs_flds += [
            fh.Label(
                const.RENAME_FLDS[k],
                fh.Input(name=k),
            )
            for k in s.CNB_FLDS
        ]
    return (
        fh.Grid(
            *adrs_flds,
            style="grid-template-columns: 1fr 1fr 1fr",
        ),
        *hidden_flds,
    )


async def get_ppt_flds(ppt_type: int | None = None):
    if ppt_type:
        flds = (
            fh.Hidden(name="ppt_type", value=ppt_type),
            fh.Input(
                name="ppt_type_name", value=const.PPT_TYPE[ppt_type], disabled=True
            ),
        )
    else:
        flds = (slct_fld("ppt_type", const.PPT_TYPE),)
        ppt_type = s.PropertyType.WAREHOUSE
    rnm = await get_renamed_flds_for(ppt_type)
    return (
        *flds,
        *(
            fh.Label(
                fh.Input(
                    type="checkbox",
                    role="switch",
                    name=k,
                ),
                rnm.get(k),
            )
            for k in s.PPT_BOOL_FLDS
        ),
        *(
            fh.Label(
                rnm.get(k),
                fh.Input(
                    name=k,
                ),
            )
            for k in ("name", *s.PPT_COSTS_FLDS)
        ),
        fh.Textarea(name="description", placeholder="Descrição", rows=10),
    )


async def get_unit_flds(ppt_type: int):
    flds = []
    rnm = await get_renamed_flds_for(ppt_type)
    for k, v in s.PPT_FRM_FLDS[ppt_type].items():
        if v == bool:
            flds.append(
                fh.Label(
                    fh.Input(
                        type="checkbox",
                        role="switch",
                        name=k,
                    ),
                    rnm.get(k),
                )
            )
        else:
            flds.append(
                fh.Label(
                    rnm.get(k),
                    fh.Input(name=k),
                )
            )
    return flds


async def get_unit_frm(sess, ppt_type: int, ppt_id: int, for_edit: bool = False):
    hidden_flds = [
        fh.Hidden(id="ppt_type", value=ppt_type),
    ]
    link = f"/ppts/{ppt_id}/units"
    if for_edit:
        btns = fh.Button("Salva")
        d = {"hx_put": link}
        hidden_flds.append(fh.Hidden(id="id"))
    else:
        btns = fh.Grid(
            fh.Button("Salva e sai", id="action", value="exit"),
            fh.Button("Adiciona mais unidades", id="action", value="add"),
        )
        d = {
            "hx_post": link,
        }
    unit_flds = await get_unit_flds(ppt_type)
    return fh.Form(
        *hidden_flds,
        broker_hide_or_slct_fld(sess),
        user_add_or_slct_fld("owner_id"),
        *unit_flds,
        btns,
        **d,
    )


def get_tbl_options(fld_name: str):
    """Options for tables with name fld."""
    tbl = s.FK_TABLES[fld_name]
    if fld_name in const.ROLE_FLDS:
        role = const.ROLE_FLDS[fld_name]
        return tbl.rows_where(
            "role = ?",
            (role,),
            select='name || " - " || email || " - " || id AS name, id',
        )
    return tbl.rows


def get_add_frm(
    parent_id: int, path: str, tp: str = "text", mlt: bool = False
) -> fh.Form:
    new_inp = fh.Input(id=f"new_{path}", name=path, type=tp, multiple=mlt)
    add = fh.Form(
        fh.Group(new_inp, fh.Button("+")),
        hx_post=f"/{parent_id}/{path}",
        target_id=f"{path}-list",
        hx_swap="afterbegin",
    )
    return add


def show_item(path: str, ppt_id: int, item: dict):
    _path = f'/ppts/{ppt_id}/{path}/{item["id"]}'
    if path == "imgs":
        return fh.Div(
            fh.Grid(
                fh.Label(
                    fh.Input(
                        type="checkbox", role="switch", name="cover", value=item["id"]
                    ),
                    "cover",
                ),
                fh.Button(
                    aria_label="Close",
                    rel="prev",
                    hx_delete=_path,
                    style="margin-bottom: -2px; margin-top: 0px;",
                ),
            ),
            fh.Embed(src=item["name"], type="image/jpeg", width="100%", height="200px"),
            id=f'{path}-{item["id"]}',
        )
    if path == "pdfs":
        dtls = {"href": _path, **_blank}
    else:
        dtls = {"hx_get": _path, "hx_target": f"#{const.INFR_EDIT}"}
    return fh.Div(
        fh.A(item["name"], **dtls),
        fh.Button(
            aria_label="Close",
            rel="prev",
            hx_delete=_path,
            style="display: inline; margin: 0px; padding: 5px",
        ),
        style="display: inline-block; margin: 0px; padding: 5px; background-color: #e0e0e0;",
        id=f'{path}-{item["id"]}',
    )


def get_layout_for(path: str, ppt_id: int, *args):
    style = _flex
    if path == "infrs":
        frm = get_add_frm(ppt_id, path)
        edit_div = fh.Div(id=const.INFR_EDIT)
    else:
        frm = get_add_frm(ppt_id, path, tp="file", mlt=True)
        edit_div = None
    if path == "imgs":
        style = _grid
    return fh.Div(
        fh.Label(
            const.RENAME_FLDS[path],
            frm,
        ),
        fh.Div(*args, id=f"{path}-list", style=style),
        edit_div,
    )


def get_block_for(path: str, ppt_id: int):
    if path == "infrs":
        i_qry = """
        SELECT i.*
        FROM ppt_infrastructures as p
        LEFT JOIN infrastructures as i ON p.infr_id = i.id
        WHERE p.ppt_id = ?
        """
        qry = s.db.q(i_qry, (ppt_id,))
    else:
        tbl = s.FILE_TABLES[path]
        qry = tbl.rows_where("ppt_id = ?", (ppt_id,))
    items = (show_item(path, ppt_id, i) for i in qry)
    return get_layout_for(path, ppt_id, *items)


def get_ppt_with_adrs(ppt_id: int) -> dict:
    ppt_qry = """
    SELECT p.*, c.name as city, s.name as street, r.name as region,
    a.str_number, a.block
    FROM properties as p
    LEFT JOIN addresses as a ON p.adrs_id = a.id
    LEFT JOIN cities as c ON a.city_id = c.id
    LEFT JOIN streets as s ON a.street_id = s.id
    LEFT JOIN districts as d ON a.district_id = d.id
    LEFT JOIN regions as r ON a.region_id = r.id
    WHERE p.id = ?
    LIMIT 1
    """
    ppt = s.db.q(ppt_qry, (ppt_id,))
    return ppt[0]


def get_adrs(adrs_id: int, return_str: bool = True) -> str:
    qry = """
    SELECT c.name as city_id, s.name as street_id, r.name as region_id,
    d.name as district_id, cep, a.str_number, a.block
    FROM addresses as a
    LEFT JOIN cities as c ON a.city_id = c.id
    LEFT JOIN streets as s ON a.street_id = s.id
    LEFT JOIN districts as d ON a.district_id = d.id
    LEFT JOIN regions as r ON a.region_id = r.id
    WHERE a.id = ?
    LIMIT 1
    """
    adrs = s.db.q(qry, (adrs_id,))[0]
    if return_str:
        return f"{adrs['street_id']} {adrs['str_number']}, block {adrs['block']}, {adrs['city_id']}, {adrs['region_id']}"
    return adrs


def get_ad_ppt_type_flds() -> tuple:
    return fh.Label(
        const.RENAME_FLDS["ad_type"],
        fh.Select(
            *[
                fh.Option(v, value=str(k))
                for k, v in const.FILTER_FLDS["ad_type"].items()
            ],
            name="ad_type",
            get="get_price_fld",
            hx_target="#price_type",
        ),
    ), fh.Label(
        const.RENAME_FLDS["ppt_type"],
        fh.Select(
            *[
                fh.Option(v, value=str(k))
                for k, v in const.FILTER_FLDS["ppt_type"].items()
            ],
            name="ppt_type",
            get="get_ppts_fld",
            hx_target="#ppt_type",
        ),
    )


async def get_fltr(
    ad_type: int = s.AdType.RENT,
    ppt_type: int = s.PropertyType.WAREHOUSE,
    prefil: dict | None = None,
) -> tuple:
    if not prefil:
        prefil = dict()
    ad_fld = const.AD_TYPE_FLDS[ad_type]
    rnm = await get_renamed_flds_for(ppt_type)
    range_flds = s.UNIT_RANGE_FLDS
    if ppt_type == s.PropertyType.WAREHOUSE:
        range_flds += s.WH_RANGE_FLDS
    return (
        get_ad_ppt_type_flds(),
        *(slct_fld(k, const.CHOICE_TYPE) for k in s.PPT_CHOICE_FLDS),
        *(
            get_autocomplete_for(k, multiple=True, prefil=prefil.get(k))
            for k in s.CDR_FK
        ),
        fh.Div(
            range_container(ad_fld, **const.RANGES[ad_fld], rename=rnm[ad_fld]),
            id="price_type",
        ),
        fh.Div(
            (range_container(k, **const.RANGES[k], rename=rnm[k]) for k in range_flds),
            id="ppt_type",
        ),
        *(
            get_autocomplete_for(k, multiple=True, prefil=prefil.get(k))
            for k in ("avcb_id", "infr_id")
        ),
    )


def extract_lat_lng(address: str) -> dict | None:
    """Return lat lng of the address"""
    # Geocoding an address
    geocode_result = s.gmaps.geocode(address)
    if geocode_result:
        goecode = geocode_result[0]
        lat_lng = goecode.get("geometry")["location"]
        return lat_lng
    return None


def broker_hide_or_slct_fld(sess: dict):
    if sess["auth_r"] == s.Role.BROKER:
        return fh.Hidden(name="broker_id", value=sess["auth"])
    else:
        cs = {o["id"]: o["name"] for o in get_tbl_options("broker_id")}
        return slct_fld("broker_id", cs)


def user_add_or_slct_fld(fld: str, **kwargs):
    return fh.Label(
        const.RENAME_FLDS[fld],
        fh.Grid(
            get_autocomplete_for(fld, labled=False),
            fh.Button(
                "+",
                hx_get="/register",
                data_tooltip="Cadastrar Usuario",
                hx_target="#register",
            ),
            id="user",
        ),
        id="user",
        **kwargs,
    )


async def get_ppt_units(ppt_id: int, flds: list, ad_type: int | None = None):
    ppt = s.properties[ppt_id]
    ppt_type = ppt.ppt_type
    unit = s.PPT_TABLE_NAMES.get(ppt_type)
    slct = """
    (rent * area) as rent,
    (sell * area) as sell,
    """
    if ad_type:
        slct = [
            """
        (rent * area) as rent,
        (iptu + condominium + foro + rent) * area as price,
        """,
            "(sell * area) as sell,",
        ][ad_type == s.AdType.SELL]
    if ppt_type == s.PropertyType.WAREHOUSE:
        slct += "ROUND((area - office_area) * 100.0 / area, 1) as efficiency,"
    qry = f"""
    SELECT p.*, u.*,
    c.name as city, s.name as street,
    {slct}
    (iptu*area) as iptu,
    (condominium*area) as condominium,
    ROUND(foro*area, 1) as foro
    FROM properties as p
    LEFT JOIN addresses as a ON p.adrs_id = a.id
    LEFT JOIN cities as c ON a.city_id = c.id
    LEFT JOIN streets as s ON a.street_id = s.id
    LEFT JOIN {unit} as u ON p.id = u.ppt_id
    WHERE p.id = ?
    """

    db_q = s.db.q(qry, (ppt_id,))
    ppt = db_q[0]

    return ppt, await get_units_tbl(db_q, ppt_type, ad_type, *flds)


def get_min_max_modified(fld: str):
    min_fld = f"min_{fld}"
    max_fld = f"max_{fld}"
    return lambda row: (
        f"{row[min_fld]}"
        if f"{row[min_fld]}" == f"{row[max_fld]}"
        else f"{row[min_fld]} a {row[max_fld]}"
    )


def get_modification_dict(for_comparison: bool = False) -> dict:
    md_dict = {
        "edit": lambda row: f"<a hx-get='/ppts/{row['ppt_id']}/units/{row['id']}/edit_frm' hx-target='#dialog' hx-swap='innerHTML'>Editar</a>",
        "select": lambda row: f'<input type="checkbox" name="selected" value="{row["id"]}">',
        "address": lambda row: f"{row['district']} - {row['city']}",
        "details": lambda row: f"<a hx-get='/comparisons/{row['id']}' hx-target='#dialog' hx-swap='innerHTML'>Details</a>",
    }
    if for_comparison:
        md_dict.update(**{k: get_min_max_modified(k) for k in s.WH_MD_FLDS})
    return md_dict


async def get_units_tbl(
    db_q, ppt_type: int, ad_type: int | None, *flds, for_comparison: bool = False
):
    df = pd.DataFrame(db_q)
    bool_flds = bool_flds = (
        list(s.WH_BOOL_FLDS)
        if ppt_type == s.PropertyType.WAREHOUSE
        else ["under_construction"]
    )
    df[bool_flds] = df[bool_flds].replace({1: "Sim", 0: "Não"})
    flds_list = get_tbl_flds_for(ppt_type, ad_type, *flds)
    modification_dict = get_modification_dict(for_comparison)
    for k in flds_list:
        if modification_dict.get(k):
            df[k] = df.apply(modification_dict[k], axis=1)
    rename_dict = await get_renamed_flds_for(ppt_type, price_per_month=True)
    tbl = df[flds_list].rename(columns=rename_dict)
    tbl = tbl.transpose()
    return tbl


async def get_infr(ppt_id: int):
    qry = """
    SELECT name
    FROM ppt_infrastructures as pi
    LEFT JOIN infrastructures as i ON pi.infr_id = i.id
    WHERE ppt_id = ?
    """
    db_q = s.db.q(qry, (ppt_id,))
    return fh.Label(
        fh.H2("Infraestrutura:"),
        fh.Grid(
            *(fh.Li(i["name"]) for i in db_q),
            style="grid-template-columns: 1fr 1fr",
        ),
    )


async def get_embeded_imgs(ppt_id: int, **kwargs):
    return (
        fh.Embed(src=i["name"], type="image/jpeg", width="100%", height="200px")
        for i in s.ppt_images.rows_where("ppt_id = ?", (ppt_id,), **kwargs)
    )


async def get_imgs(ppt_id):
    n = s.ppt_images.count_where("ppt_id = ?", (ppt_id,))
    return fh.Div(
        fh.Grid(
            *(await get_embeded_imgs(ppt_id, limit=3)),
            style="grid-template-columns: 1fr 1fr 1fr",
        ),
        fh.Button(f"Ver {n} fotos", hx_get=f"/{ppt_id}/imgs", hx_target="#dialog"),
    )


async def get_ppt_infr_img_units(
    ppt_id: int, user_id: int, tbl_flds: list, *submit_btns, ad_type: int | None = None
):
    (ppt, tbl), inf, img = await asyncio.gather(
        get_ppt_units(ppt_id, tbl_flds, ad_type),
        get_infr(ppt_id),
        get_imgs(ppt_id),
    )
    btns = {"submit": (add_btn_for(k) for k in submit_btns)}
    if "edit" in tbl_flds:
        btns["edit"] = fh.AX(
            "Edit",
            hx_get=f"/ppts/{ppt_id}/edit",
            hx_target="#dialog",
        )
        btns["add_unit"] = add_btn_for(
            "unit_frm",
            name="+",
            data_tooltip=const.RENAME_FLDS["unit_frm"],
            hx_target="#dialog",
        )
        if ppt["pdf_path"]:
            path = ppt["pdf_path"]
            btns["pdf_path"] = fh.A(
                "Mostrar arquivo", href=f"/pdf?pdf_path={path}", **_blank
            )
    return fh.Titled(
        f'{const.PPT_TYPE.get(ppt["ppt_type"])} RET{ppt_id:03d}',
        fh.Grid(
            fh.P(f"{ppt['street']} - {ppt['city']}", id="address"),
            btns.get("edit"),
        ),
        img,
        fh.Label(fh.H2("Descricao:"), _for="description"),
        fh.Div(ppt["description"], id="description"),
        inf,
        btns.get("pdf_path"),
        fh.Label(fh.Grid(fh.H2("Unidades:"), btns.get("add_unit")), _for="#modules"),
        fh.Form(
            fh.Hidden(id="user_id", value=user_id),
            fh.Hidden(id="ppt_id", value=ppt_id),
            fh.Hidden(id="ppt_type", value=ppt["ppt_type"]),
            fh.Hidden(id="ad_type", value=ad_type),
            fh.NotStr(tbl.to_html(escape=False, header=False)),
            id="modules",
            cls="table-container",
        ),
        *btns.get("submit"),
        fh.Div(id="dialog"),
        fh.Div(id="register"),
        id="result",
    )


async def create_cmp(data: dict, unit_ids: list[str]):
    qry = "&".join(f"{k}={v}" for k, v in data.items())
    ppt_type = data.pop("ppt_type")
    cmp = s.comparisons.insert(
        {
            **data,
            "status": s.Status.NEW,
            "date": dt.now().strftime("%Y/%m/%d, %H:%M:%S"),
        }
    )
    cmp_table = s.PPT_CMP_TABLES.get(int(ppt_type))
    for id in unit_ids:
        cmp_table.insert(comparison_id=cmp["id"], unit_id=int(id))
    return fh.A("Ver comparações", type="submit", href=f"/comparisons?{qry}", **_blank)


async def get_cmp_for(data: dict, flds: tuple, return_frm: bool = False):
    ppt_type = int(data["ppt_type"])
    ad_type = int(data["ad_type"])
    user_id = int(data["user_id"])
    where_fld = "WHERE cmp.user_id = ? AND cmp.ad_type = ? AND NOT cmp.status = ? AND p.ppt_type = ?"
    params = (user_id, ad_type, s.Status.ARCHIVE, ppt_type)
    if data.get("selected"):
        placeholders = ", ".join(["?" for _ in data["selected"]])
        where_fld = f"WHERE cmp.id IN ({placeholders})"
        params = data["selected"]
    table = s.PPT_TABLE_NAMES.get(ppt_type)
    cmp_table = s.PPT_CMP_TABLES.get(ppt_type)
    slct = (
        "SUM(sell*area) AS sell,"
        if ad_type == s.AdType.SELL
        else "SUM(rent*area) AS rent, SUM((iptu + condominium + foro + rent) * area) as price,"
    )
    slct += ", ".join(f"SUM({k}*area) as {k}" for k in s.PPT_COSTS_FLDS) + ", "
    if ppt_type == s.PropertyType.WAREHOUSE:
        slct += (
            "ROUND(SUM(area - office_area) * 100.0 / SUM(area), 1) as efficiency,"
            + ", ".join(f"m.{k}" for k in s.WH_BOOL_FLDS)
            + ", "
            + ", ".join(f"SUM({k}) AS {k}" for k in ("docks", "office_area"))
            + ", "
            + ", ".join(
                f"{m.upper()}({k}) AS {m}_{k}"
                for k in s.WH_MD_FLDS
                for m in ("min", "max")
            )
            + ", "
        )
    qry = f"""
    SELECT cmp.id as id, p.name, p.ppt_type, d.name as district, c.name as city, a.location,
    GROUP_CONCAT(m.title, ', ') as title,
    {slct}
    SUM(area) as area
    FROM comparisons as cmp
    LEFT JOIN properties as p ON cmp.ppt_id = p.id
    LEFT JOIN addresses as a ON p.adrs_id = a.id
    LEFT JOIN districts AS d ON a.district_id = d.id
    LEFT JOIN cities AS c ON a.city_id = c.id
    LEFT JOIN {cmp_table} as cmp_m ON cmp.id = cmp_m.comparison_id
    LEFT JOIN {table} as m ON cmp_m.unit_id = m.id
    {where_fld}
    GROUP BY cmp.id
    """
    db_q = s.db.q(qry, params)
    locations = [
        {"index": i + 1, "location": json.loads(d.get("location"))}
        for i, d in enumerate(db_q)
    ]
    tbl = await get_units_tbl(db_q, ppt_type, ad_type, *flds, for_comparison=True)
    if return_frm:
        tbl = fh.Form(
            fh.Hidden(id="user_id", value=user_id),
            fh.Hidden(id="ad_type", value=ad_type),
            fh.Hidden(id="ppt_type", value=ppt_type),
            fh.NotStr(tbl.to_html(escape=False, header=False)),
            fh.Button("Download site selection", id="download_btn"),
            action="/download_pdf",
            method="post",
            id="comparisons",
            cls="table-container",
        )
    return tbl, locations


async def create_pdf(data: dict, output_pdf):
    """Create pdf using reportlab."""
    ppt_type = int(data["ppt_type"])
    ad_type = int(data["ad_type"])
    user_id = int(data["user_id"])
    where_fld = "WHERE cmp.user_id = ? AND cmp.ad_type = ? AND NOT cmp.status = ? AND p.ppt_type = ?"
    params = (user_id, ad_type, s.Status.ARCHIVE, ppt_type)
    if data.get("selected"):
        placeholders = ", ".join(["?" for _ in data["selected"]])
        where_fld = f"WHERE cmp.id IN ({placeholders})"
        params = data["selected"]
    flds = ("address", "name")
    tbl, locations = await get_cmp_for(data, flds)
    qry_img = f"""
    SELECT cmp.id,
    GROUP_CONCAT(DISTINCT pi.name) as img,
    GROUP_CONCAT(DISTINCT i.name) as infr
    FROM comparisons as cmp
    LEFT JOIN properties as p ON cmp.ppt_id = p.id
    LEFT JOIN ppt_images as pi ON p.id = pi.ppt_id
    LEFT JOIN ppt_infrastructures as p_i ON p.id = p_i.ppt_id
    LEFT JOIN infrastructures as i ON p_i.infr_id = i.id
    {where_fld}
    GROUP BY cmp.id
    """
    db_imgs = s.db.q(qry_img, params)

    # Register fonts
    pdfmetrics.registerFont(TTFont("Poppins", "assets/fonts/Poppins-Regular.ttf"))

    # Create a PPTF
    pdf_canvas = canvas.Canvas(
        output_pdf, pagesize=(const.PAGE_WIDTH, const.PAGE_HEIGHT), pageCompression=1
    )
    # First page
    pdf_canvas.drawImage(
        const.COVER_BGD, 0, 0, width=const.PAGE_WIDTH, height=const.PAGE_HEIGHT
    )
    pdf_canvas.setFont("Poppins", 60)
    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.drawString(const.LR_PADDING, const.TOP_PADDING, "Opções para locação")
    pdf_canvas.drawString(const.LR_PADDING, const.TOP_PADDING - 60, "Limeira e região")

    # Bookmark the first page and add an outline entry
    pdf_canvas.bookmarkPage("first_page")
    pdf_canvas.addOutlineEntry("Cover", "first_page", level=0)

    pdf_canvas.showPage()

    # About page
    pdf_canvas.drawImage(
        const.ABOUT_BGD, 0, 0, width=const.PAGE_WIDTH, height=const.PAGE_HEIGHT
    )

    # Bookmark the about page and add an outline entry
    pdf_canvas.bookmarkPage("about_page")
    pdf_canvas.addOutlineEntry("About", "about_page", level=0)

    pdf_canvas.showPage()

    # Step 1: Define a form XObject for the background
    pdf_canvas.beginForm("background_form")
    pdf_canvas.drawImage(
        const.BODY_BGD, 0, 0, width=const.PAGE_WIDTH, height=const.PAGE_HEIGHT
    )
    pdf_canvas.endForm()

    # Second page (static map and links)
    pdf_canvas.doForm("background_form")

    # Insert static map
    pdf_canvas.drawImage(const.static_map_image, 400, 200, width=1200, height=800)

    locations_list = (
        (
            f"Imóvel_{i['index']:02d}",
            f"https://www.google.com/maps?q={i['location']['lat']},{i['location']['lng']}",
        )
        for i in locations
    )
    # Add "See on map" links
    y_position = 150
    pdf_canvas.setFont("Poppins", 40)
    pdf_canvas.drawString(400, y_position, "See on map:")
    w = 250
    for idx, (label, url) in enumerate(locations_list, start=1):
        pdf_canvas.drawString(400 + idx * w, y_position, label)
        pdf_canvas.linkURL(
            url, (400 + idx * w, y_position, 400 + idx * w + w, y_position + 40)
        )

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
        name="Custom",
        fontName="Poppins",  # Use Poppins font or your preferred font
        fontSize=25,  # Set desired font size here
        leading=28,  # Set line height (optional)
        # alignment=1,  # Center align (optional)
    )
    # Convert the DataFrame headers and rows to Paragraphs
    data = []
    header_row = [Paragraph("Imóvel", custom_style)] + [
        Paragraph(f"{i + 1:02d}", custom_style) for i in tbl.columns
    ]
    data.append(header_row)
    # Convert each row in the DataFrame to Paragraphs
    for index, row in tbl.iterrows():
        row_data = [Paragraph(str(index), custom_style)] + [
            Paragraph(str(cell), custom_style) for cell in row
        ]
        data.append(row_data)

    # Dynamically calculate column widths based on page size and padding
    available_width = const.PAGE_WIDTH - 2 * const.LR_PADDING
    col_width = available_width / len(data[0])
    tbl_width = [col_width] * len(data[0])

    # Create a table with dynamically calculated column widths
    table = Table(data, colWidths=tbl_width)

    # Define table style with increased font size
    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 1),
                    colors.lightblue,
                ),  # Header background color
                ("TEXTCOLOR", (0, 0), (-1, 1), colors.whitesmoke),  # Header text color
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), "Poppins"),
                ("FONTSIZE", (0, 0), (-1, -1), 46),  # Increased font size
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),  # Align text to the top of the cell
                # ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
                ("BACKGROUND", (0, 2), (-1, -1), colors.beige),  # Body background color
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )

    # Table height for calculating col positions (assumes uniform col heights)
    first_col_y = (
        const.PAGE_HEIGHT - const.TOP_PADDING
    )  # Starting y-position for the first col
    col_height = 40

    # Add links manually for the first column cols
    for col_idx in tbl.columns:
        header_number = f"{col_idx + 1:02d}"

        # Calculate the y position of each col's cell
        col_x_position = const.LR_PADDING + (col_idx + 1) * col_width

        # Define the clickable rectangle (adjust left/right as needed)
        link_rect = (
            col_x_position,
            first_col_y,
            col_x_position + col_width,
            first_col_y - col_height,
        )

        # Add the clickable area linking to the bookmark
        pdf_canvas.linkRect(header_number, header_number, link_rect)

    # Wrap and draw the table
    table_width, table_height = table.wrap(
        const.PAGE_WIDTH, const.PAGE_HEIGHT - const.TOP_PADDING
    )
    table.drawOn(
        pdf_canvas,
        const.LR_PADDING,
        const.PAGE_HEIGHT - const.TOP_PADDING - table_height,
    )

    # Bookmark the table page and add an outline entry
    pdf_canvas.bookmarkPage("table_page")
    pdf_canvas.addOutlineEntry("Table Overview", "table_page", level=0)

    pdf_canvas.showPage()

    # Add Dynamic Pages for each comparison
    for idx in tbl.columns:
        header_number = f"{idx + 1:02d}"

        # Bookmark each row dynamically and add to the outline
        pdf_canvas.bookmarkPage(header_number)
        pdf_canvas.addOutlineEntry(
            f"Details for Column {idx + 1}", header_number, level=1
        )

        # Create two pages for each row
        pdf_canvas.doForm("background_form")
        pdf_canvas.setFont("Poppins", 40)
        pdf_canvas.drawString(
            const.LR_PADDING,
            const.PAGE_HEIGHT - const.TOP_PADDING + 100,
            f"Imóvel {idx + 1:02d}",
        )

        column_data = (
            tbl[idx].reset_index().values.tolist()
        )  # Converts the column into a list of [index, value] pairs
        table1 = Table(column_data[:-5], colWidths=[350] * 2)
        # Define table style with increased font size
        table1.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (0, -1),
                        colors.lightblue,
                    ),  # Header background color
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (0, -1),
                        colors.whitesmoke,
                    ),  # Header text color
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Poppins"),
                    ("FONTSIZE", (0, 0), (-1, -1), 26),  # Increased font size
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),  # Align text to the top of the cell
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 30),
                    (
                        "BACKGROUND",
                        (1, 0),
                        (1, -1),
                        colors.beige,
                    ),  # Body background color
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        # Wrap and draw the table
        table1_width, table1_height = table1.wrap(
            const.PAGE_WIDTH, const.PAGE_HEIGHT - const.TOP_PADDING
        )
        table1.drawOn(
            pdf_canvas,
            const.LR_PADDING,
            const.PAGE_HEIGHT - const.TOP_PADDING - table1_height,
        )
        table2 = Table(column_data[-5:], colWidths=[350] * 2)
        # Define table style with increased font size
        table2.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (0, -1),
                        colors.lightblue,
                    ),  # Header background color
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (0, -1),
                        colors.whitesmoke,
                    ),  # Header text color
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Poppins"),
                    ("FONTSIZE", (0, 0), (-1, -1), 26),  # Increased font size
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),  # Align text to the top of the cell
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 30),
                    (
                        "BACKGROUND",
                        (1, 0),
                        (1, -1),
                        colors.beige,
                    ),  # Body background color
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        # Wrap and draw the table
        table2_width, table2_height = table2.wrap(
            const.PAGE_WIDTH, const.PAGE_HEIGHT - const.TOP_PADDING
        )
        table2.drawOn(
            pdf_canvas,
            const.LR_PADDING + 1000,
            const.PAGE_HEIGHT - const.TOP_PADDING - table2_height - 300,
        )

        img_list = db_imgs[idx]["img"].split(",")
        infr_list = db_imgs[idx]["infr"].split(",")

        if img_list:
            pdf_canvas.drawImage(
                img_list[0][1:],
                const.LR_PADDING + 1000,
                const.PAGE_HEIGHT - const.TOP_PADDING - 300,
                width=700,
                height=300,
            )
        pdf_canvas.showPage()
        pdf_canvas.doForm("background_form")
        for i in range(1, 3):
            try:
                pdf_canvas.drawImage(
                    img_list[i][1:],
                    const.LR_PADDING,
                    const.PAGE_HEIGHT - const.TOP_PADDING - 330 * i,
                    width=700,
                    height=300,
                )
            except IndexError:
                break
        col = [[Paragraph("Infraestrutura:", custom_style)]] + [
            [Paragraph(f"•  {c}", custom_style)] for c in infr_list
        ]
        table3 = Table(col, colWidths=const.PAGE_WIDTH / 2 - const.LR_PADDING)
        # Define table style
        table3.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (1, 0),
                        (-1, -1),
                        colors.transparent,
                    ),  # Body background color
                    ("GRID", (0, 0), (-1, -1), 0, colors.transparent),
                ]
            )
        )
        # Wrap and draw the table
        table3_width, table3_height = table3.wrap(
            const.PAGE_WIDTH, const.PAGE_HEIGHT - const.TOP_PADDING
        )
        table3.drawOn(
            pdf_canvas,
            const.PAGE_WIDTH / 2,
            const.PAGE_HEIGHT - const.TOP_PADDING - table3_height,
        )

        pdf_canvas.showPage()
    # Last page (background 1.jpg)
    pdf_canvas.drawImage(
        const.LAST_PAGE_BGD, 0, 0, width=const.PAGE_WIDTH, height=const.PAGE_HEIGHT
    )

    # Bookmark the last page and add an outline entry
    pdf_canvas.bookmarkPage("last_page")
    pdf_canvas.addOutlineEntry("Last Page", "last_page", level=0)

    # Save the PPTF
    pdf_canvas.save()


def task_frm(sess: dict, prefil: dict = dict()):
    return fh.Form(
        user_add_or_slct_fld("client_id"),
        *(slct_fld(k, const.FILTER_FLDS[k]) for k in s.TSK_SLC_FLDS),
        fh.Label("Descrição", fh.Textarea(name="initial_dscr", rows=10)),
        broker_hide_or_slct_fld(sess),
        fh.Button("Next", type="submit"),
        hx_post="/tasks",
        hx_target="#dialog",
    )


def add_btn_for(path: str, include: str = "modules", name: str | None = None, **kwargs):
    nm = name if name else const.RENAME_FLDS[path]
    return fh.Button(
        nm,
        type="submit",
        hx_post=f"/{path}",
        hx_include=f"#{include}",
        hx_swap="outerHTML",
        **kwargs,
    )


async def get_ppt_frm(adrs_id: int, ppt_type: int, ppt_id: int | None = None):
    hiddens = [
        fh.Hidden(id="adrs_id", value=adrs_id),
    ]
    if ppt_id:
        hiddens.append(fh.Hidden(id="id", value=ppt_id))
        d = {"hx_put": "/ppts", "id": "ppt_edit"}
        btns = fh.Button("Save")
    else:
        d = {"hx_post": "/ppts"}
        btns = fh.Grid(
            fh.Button("Back", hx_get="/adrs_frm"),
            fh.Button("Next"),
        )
    return fh.Form(
        *hiddens,
        await get_ppt_flds(ppt_type),
        get_autocomplete_for("avcb_id"),
        btns,
        **d,
    )


def test_script(prefix: str, multiple: bool):
    value = (
        f'me("#{prefix}").value = "";'
        if multiple
        else f'me("#{prefix}").value = value;'
    )
    return f"""
    // Show dropdown and filter options when typing
    me("#{prefix}").on("input", ev => {{
        let filter = me(ev).value.toLowerCase();
        let options = any("#{prefix}_dropdown li");

        options.forEach(option => {{
            if (option.textContent.toLowerCase().includes(filter)) {{
                option.style.display = "";  // Show matching option
            }} else {{
                option.style.display = "none";  // Hide non-matching option
            }}
        }});

        me("#{prefix}_dropdown").style.display = "block";  // Show dropdown
    }});

    // Select an option from the dropdown
    any("#{prefix}_dropdown li").on("click", ev => {{
        let value = me(ev).textContent;
        
        {value}
        me("#{prefix}_dropdown").style.display = "none";  // Hide dropdown after selection
    }});

    // Close the dropdown when clicking outside the input or dropdown
    document.addEventListener("click", function(event) {{
        let input = me("#{prefix}");
        let dropdown = me("#{prefix}_dropdown");

        // Close dropdown if the click is outside the input or dropdown
        if (!input.contains(event.target) && !dropdown.contains(event.target)) {{
            dropdown.style.display = "none";
        }}
    }});
    
    // Add custom option on Enter key press for multiple selections
    me("#{prefix}").on("keydown", ev => {{
        if (ev.key === "Enter") {{
            ev.preventDefault();  // Prevent form submission
            let value = me("#{prefix}").value.trim();
            let prefix = "{prefix}";
            if (value) {{
                if ({'true' if multiple else 'false'}) {{
                    me("#{prefix}").value = "";  // Clear input after Enter for multiple
                }} else {{
                    me("#{prefix}").value = value;  // For single selection, put the value in the input
                }}
                me("#{prefix}_dropdown").style.display = "none";  // Hide dropdown
            }}
        }}
    }});
    """


def test(
    prefil: list = ["Minsk", "Moscow"],
    field: str = "city_id",
    multiple: bool = True,
    tp: str = "text",
    labled: bool = True,
):
    fld = (
        fh.Input(
            id=field,
            type=tp,
            placeholder=const.RENAME_FLDS[field],
            autocomplete="off",  # Disable default browser autocomplete
        ),
    )
    # fld = fh.Group(
    #     fh.Input(
    #         id=field, type=tp, placeholder=const.RENAME_FLDS[field],
    #         autocomplete="off",  # Disable default browser autocomplete
    #     ),
    #     fh.Button(
    #         "+",
    #         type='submit',
    #         hx_get='/autocomplete',
    #         hx_include=f'#{field}',
    #         target_id=f'{field}_selected',
    #         hx_swap='afterbegin',
    #         id='prefix',
    #         value=field,
    #     )
    # )
    # fld = fh.Form(
    #     fh.Hidden(id='prefix', value=field),
    #     fh.Input(
    #         id=field, type=tp, placeholder=const.RENAME_FLDS[field],
    #         autocomplete="off"  # Disable default browser autocomplete
    #     ),
    #     **on_input
    # )
    if labled:
        fld = fh.Label(
            const.RENAME_FLDS[field],
            fld,
        )

    return fh.Div(
        fld,
        fh.Ul(
            *[
                fh.Li(
                    option["name"],
                    value=option["id"],
                    cls="dropdown-item",
                    # hx_trigger='click',
                    # hx_get=f'/autocomplete?{field}={option["name"]}&prefix={field}&id={option["id"]}',
                    # target_id=f'{field}_selected',
                    # hx_swap='afterbegin',
                )
                for option in get_tbl_options(field)
            ],  # Render the options dynamically with class
            id=f"{field}_dropdown",
            cls="dropdown-list",
            style="display:none;",  # Hide dropdown initially
        ),
        fh.Div(
            *[mult_choice(field, s) for s in prefil] if prefil else None,
            id=f"{field}_selected",
            cls="selected-container",
            style="display: flex;",
        ),  # Container for selected options
        fh.Div(
            id=f"{field}_hidden"
        ),  # Container for hidden inputs (submitted with form)
        fh.Script(
            autocomplete_script(field, multiple)
        ),  # Add the dynamic filtering and selection script
    )


def mult_choice(item: str, prefix: str):
    return fh.Div(
        fh.Hidden(id=prefix, value=item),
        fh.Span(
            item,
            fh.Button("x", hx_get=f"/cls_details/{prefix}_{item}"),
            cls="selected-item",
        ),
        id=f"{prefix}_{item}",
    )
