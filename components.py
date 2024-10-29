import json

import fasthtml.common as fh
from const import (ADDRESS_FLDS, AVCB_TYPE, CHOICE_TYPE, FILTER_FLDS, RANGES,
                   ZONE)
from mysettings import db


async def get_address_flds():
    return (
        get_autocomplete_for('cities', 'Cidade'),
        get_autocomplete_for('regions', 'Região'),
        get_autocomplete_for('districts', 'Bairro'),
    )

def get_dialog(hdr_msg: str, item) -> fh.DialogX:
    hdr = fh.Div(fh.Button(aria_label='Close', rel='prev', hx_get='/cls_dialog', hx_swap='outerHTML'),  # Close button
                 fh.P(hdr_msg))
    return fh.DialogX(item, open=True, header=hdr, id='dialog', hx_swap='outerHTML')

def slct_fld(nm: str, cs: dict, multiple: bool = False, **kwargs) -> fh.Select:
    return fh.Select(*[fh.Option(v, value=k) for k, v in cs.items()], name=nm, multiple=multiple, **kwargs)

def range_script(prefix: str):
    return f"""
function updateSliderValues(prefix) {{
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
    updateSliderValues('{prefix}');  // Reinitialize slider after HTMX swap
}});
"""

def range_container(label: str, minimum: int, maximum: int, step: int, prefix: str):
    return fh.Div(
        fh.Label(label, _for='range'),
        fh.Div(
            fh.Grid(
                fh.Div(fh.Label('Min', _for=f'{prefix}_min'),
                    fh.Input(id=f'{prefix}_min', type='number', value=str(minimum), min=str(minimum), max=str(maximum), step=str(step))),
                fh.Div(fh.Label('Max', _for=f'{prefix}_max'),
                    fh.Input(id=f'{prefix}_max', type='number', value=str(maximum), min=str(minimum), max=str(maximum), step=str(step))),
            ),
            fh.Div(
                fh.Span(id=f'{prefix}_selected', cls='range-selected'),
                cls='range-slider',
            ),
            fh.Div(
                fh.Input(id=f'{prefix}_min_handler', type='range', value=str(minimum), min=str(minimum), max=str(maximum), step=str(step)),
                fh.Input(id=f'{prefix}_max_handler', type='range', value=str(maximum), min=str(minimum), max=str(maximum), step=str(step)),
                cls='range-input',
            ),
            cls='range',
        ),
        fh.Script(range_script(prefix)),
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

def get_autocomplete_for(table: str, label: str, multiple: bool=False, tp: str='text'):
    """
    Provide autocomplete field with options from db.table
    """
    qry = f"""
    SELECT name AS option, id
    FROM {table}
    """
    if table == 'users':
        qry = """
        SELECT name || ' - ' || email AS option, id
        FROM users
        """
    qry_l = db.query(qry)
    return fh.Div(
        fh.Input(
            id=f"{table}", type=tp, placeholder=label,
            autocomplete="off",  # Disable default browser autocomplete
        ),
        fh.Ul(
            *[fh.Li(option['option'], value=option['id'], cls="dropdown-item") for option in qry_l],  # Render the options dynamically with class
            id=f"{table}_dropdown", cls="dropdown-list", style="display:none;"  # Hide dropdown initially
        ),
        fh.Div(id=f"{table}_selected", cls="selected-container"),  # Container for selected options
        fh.Div(id=f"{table}_hidden"),  # Container for hidden inputs (submitted with form)
        fh.Script(autocomplete_script(table, multiple))  # Add the dynamic filtering and selection script
    )

def fltr_flds():
    rngs = [range_container(**v, prefix=k) for k, v in RANGES.items()]
    return (
        get_autocomplete_for(
            'infrastructures', 'Infraestrutura', multiple=True
        ),
        fh.Input(type='search', id="name", placeholder="Codigo do imovel"),
        *[slct_fld(k, v) for k, v in FILTER_FLDS.items()],
        (fh.Label('Em condomínio', _for='in_conodminium'),
        slct_fld("in_conodminium", CHOICE_TYPE)),
        get_autocomplete_for('cities', 'Cidade'),
        get_autocomplete_for('regions', 'Região'),
        get_autocomplete_for('districts', 'Bairro'),
        slct_fld('Zona', ZONE),
        *rngs,
        slct_fld('avcb', AVCB_TYPE),
        (fh.Label('Em construção', _for='under_construction'),
        slct_fld("under_construction", CHOICE_TYPE),
        ),
    )

def mk_fltr():
    return fh.Form(
        fh.Div(
            fh.Button('x', rel='prev', hx_post='/cls_fltr'),
            cls='frm-header'
        ),
        fltr_flds(),
        (fh.Div(
            fh.Button('Limpar', type='button', hx_get='/clr_fltr'),
            fh.Button('Buscar', type='button', hx_post="/search_ppts", hx_target="#result"),
            cls='frm-footer'),)
    )

def short_fltr():
    return fh.Form(
        fh.Grid(
            fh.Input(type='search', name="name", placeholder="Codigo do imovel"),
            *[slct_fld(k, v) for k, v in FILTER_FLDS.items()],
            (fh.Label('Em condomínio', _for='in_conodminium'),
            slct_fld("in_conodminium", CHOICE_TYPE)),
            get_autocomplete_for('cities', 'Cidade'),
            range_container(**RANGES['price'], prefix='price'),
        ),
        fh.Hidden(name='in_conodminium'),
        fh.Hidden(name='region'),
        fh.Hidden(name='district'),
        fh.Hidden(name='zone'),
        fh.Hidden(name='area_min', value=str(RANGES['area']['minimum'])),
        fh.Hidden(name='area_max', value=str(RANGES['area']['maximum'])),
        fh.Hidden(name='area_min_handler', value=str(RANGES['area']['minimum'])),
        fh.Hidden(name='area_max_handler', value=str(RANGES['area']['maximum'])),
        fh.Hidden(name='height_min', value=str(RANGES['height']['minimum'])),
        fh.Hidden(name='height_max', value=str(RANGES['height']['maximum'])),
        fh.Hidden(name='height_min_handler', value=str(RANGES['height']['minimum'])),
        fh.Hidden(name='height_max_handler', value=str(RANGES['height']['maximum'])),
        fh.Hidden(name='efficiency_min', value=str(RANGES['efficiency']['minimum'])),
        fh.Hidden(name='efficiency_max', value=str(RANGES['efficiency']['maximum'])),
        fh.Hidden(name='efficiency_min_handler', value=str(RANGES['efficiency']['minimum'])),
        fh.Hidden(name='efficiency_max_handler', value=str(RANGES['efficiency']['maximum'])),
        fh.Hidden(name='abl_min', value=str(RANGES['abl']['minimum'])),
        fh.Hidden(name='abl_max', value=str(RANGES['abl']['maximum'])),
        fh.Hidden(name='abl_min_handler', value=str(RANGES['abl']['minimum'])),
        fh.Hidden(name='abl_max_handler', value=str(RANGES['abl']['maximum'])),
        fh.Hidden(name='doks_min', value=str(RANGES['doks']['minimum'])),
        fh.Hidden(name='doks_max', value=str(RANGES['doks']['maximum'])),
        fh.Hidden(name='doks_min_handler', value=str(RANGES['doks']['minimum'])),
        fh.Hidden(name='doks_max_handler', value=str(RANGES['doks']['maximum'])),
        fh.Hidden(name='flr_capacity_min', value=str(RANGES['flr_capacity']['minimum'])),
        fh.Hidden(name='flr_capacity_max', value=str(RANGES['flr_capacity']['maximum'])),
        fh.Hidden(name='flr_capacity_min_handler', value=str(RANGES['flr_capacity']['minimum'])),
        fh.Hidden(name='flr_capacity_max_handler', value=str(RANGES['flr_capacity']['maximum'])),
        fh.Hidden(name='office_area_min', value=str(RANGES['office_area']['minimum'])),
        fh.Hidden(name='office_area_max', value=str(RANGES['office_area']['maximum'])),
        fh.Hidden(name='office_area_min_handler', value=str(RANGES['office_area']['minimum'])),
        fh.Hidden(name='office_area_max_handler', value=str(RANGES['office_area']['maximum'])),
        fh.Hidden(name='energy_min', value=str(RANGES['energy']['minimum'])),
        fh.Hidden(name='energy_max', value=str(RANGES['energy']['maximum'])),
        fh.Hidden(name='energy_min_handler', value=str(RANGES['energy']['minimum'])),
        fh.Hidden(name='energy_max_handler', value=str(RANGES['energy']['maximum'])),
        # fh.Hidden(name='last_update_min', value=str(RANGES['last_update']['minimum'])),
        # fh.Hidden(name='last_update_max', value=str(RANGES['last_update']['maximum'])),
        # fh.Hidden(name='last_update_min_handler', value=str(RANGES['last_update']['minimum'])),
        # fh.Hidden(name='last_update_max_handler', value=str(RANGES['last_update']['maximum'])),
        fh.Hidden(name='avcb'),
        fh.Hidden(name='under_construction'),
        fh.Button('Buscar', type='button', hx_post="/search_ppts", hx_target="#result"),
        fh.Button('Mais filtros', type='button', hx_post='/filters', hx_target='#search-section')
    )

def map_locations_script(d: list, ad_type: int):
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

        marker.addListener("click", () => {{
            infoWindow.setContent(`
                <div class="carousel" id="carousel-${{poi.id}}">
                    ${{poi.images.map((img, index) => `
                        <div class="carousel-item ${{index === 0 ? 'active' : ''}}">
                            <img src="${{img}}" alt="Image ${{index + 1}}">
                        </div>
                    `).join('')}}
                    <button class="carousel-control left" onclick="prevSlide('${{poi.id}}')">&#10094;</button>
                    <button class="carousel-control right" onclick="nextSlide('${{poi.id}}')">&#10095;</button>
                </div>
                <h5>${{poi.name}}</h5>
                <p>${{poi.city}}, ${{poi.street}}</p>
            `);
            infoWindow.open(map, marker);
        }}, {{ passive: true }});

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
                <a href='{ad_type}/properties/${{poi.id}}' style="text-decoration: none; color: inherit;" target="blank">
                    <div class="content">
                        <h5>${{poi.type}}: ${{poi.name}}</h5>
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

def module_form(ppt_id:int):
    hdr = fh.Div(fh.Button(aria_label='Close', rel='prev', hx_get='/cls_dialog', hx_swap='outerHTML'),
                 fh.P("Cadastro do Modulo"))
    return fh.DialogX(fh.Form(
        fh.Hidden(name='pd_id', value=ppt_id),
        # *(slct_fld(k, v) for k, v in BROKERS.items()),
        fh.Input(name='owner_id', placeholder='Proprietario'),
        fh.Fieldset(
            fh.Label('Modulo:', fh.Input(name='title', placeholder='Nome')),
            fh.Label('Pe direito, m', fh.Input(name='height', placeholder='Pe direito, m')),
            fh.Label('Piso, ton/m2', fh.Input(name='flr_capacity', placeholder='Piso, ton/m2')),
            fh.Label('Entre pilares, m', fh.Input(name='width', placeholder='Entre pilares, m')),
            fh.Label('ABL, m2', fh.Input(name='abl', placeholder='ABL, m2')),
            fh.Label('Escritorio/Mezanino, m2', fh.Input(name='office_area', placeholder='Escritorio/Mezanino, m2')),
            fh.Label('Docas, qda', fh.Input(name='docks', placeholder='Docas, qda')),
            fh.Label('Aluguel, R$/m2', fh.Input(name='rent', placeholder='Aluguel, R$/m2')),
            fh.Label('Venta, R$/m2', fh.Input(name='sell', placeholder='Venta, R$/m2')),
            fh.Label('Enargia, Kva', fh.Input(name='energy', placeholder='Enargia, Kva')),
            fh.Label('Data de disponibilidade', fh.Input(name='available', placeholder='Data de disponibilidade'))),
        fh.Button("Salva e Sai", type="submit", name="action", value="save_exit"),
        fh.Button("Adiciona mais modulos", type="submit", name="action", value="add_modules"),
        hx_post=f'/properties/{ppt_id}/warehouses'), open=True, header=hdr, id='dialog', hx_swap='outerHTML')

def ppt_serializer(ppt) -> dict:
    ppt['location'] = json.loads(ppt.get('location'))
    if ppt.get('images'):
        ppt['images'] = ppt['images'].split(',')
    return ppt

def arrow(d):
    return fh.Button(fh.Img(src=f"/assets/icons/arrow-{d}.svg", alt="Arrow left"),
           cls="disabled:opacity-40 transition-opacity", id=f"slide{d.capitalize()}", aria_label=f"Slide {d}")
    
def carousel(items, id="carousel-container", extra_classes=""):
    carousel_content = fh.Div(*items, id=id,
        # cls=f"hide-scrollbar {col} lg:flex-row gap-4 lg:gap-6 rounded-l-3xl xl:rounded-3xl w-full lg:overflow-hidden xl:overflow-hidden whitespace-nowrap {extra_classes}"
    )

    arrows = fh.Div(
        fh.Div(arrow("left"), arrow("right"),
            # cls=f"w-[4.5rem] {between} ml-auto"
        ),
        # cls=f"hidden lg:flex xl:flex justify-start {maxrem(41)} py-6 pl-6 pr-20"
    )
    return fh.Div(
        fh.Div(*items, id=id), arrows,
        # cls=f"max-h-fit {col} items-start lg:-mr-16 {maxpx(1440)} overflow-hidden"
    )

