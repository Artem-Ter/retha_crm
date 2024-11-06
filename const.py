
import mysettings as s

DESCR = 'test description'

NA = 'not_available'
ZERO = 0
ANONIM = 'anonim'

SECRETARY_REGISTER = {
    s.Role.BROKER: 'Corretor',
    s.Role.OWNER: 'Proprietário',
    s.Role.USER: 'Usuário',
}

ADMIN_REGISTER = {
    s.Role.ADMIN: 'Administrador',
    s.Role.SECRETARY: 'Secretária',
    **SECRETARY_REGISTER
}

AVCB_TYPE = {
    s.Avcb.opt1: 'opt1',
    s.Avcb.opt2: 'opt2'
}

CHOICE_TYPE = {
    s.Choice.BOTH: 'Tanto faz',
    s.Choice.YES: 'Sim',
    s.Choice.NO: 'Não',
}

PPT_TYPE = {
    s.PropertyType.WAREHOUSE: 'Galpão',
    s.PropertyType.LAND: 'Terreno',
    s.PropertyType.OFFICE: 'Escritório',
    s.PropertyType.SHOP: 'Loja'
}

PPT_TABLE = {
    s.PropertyType.WAREHOUSE: 'warehouses',
    s.PropertyType.LAND: 'lands',
    s.PropertyType.OFFICE: 'offices',
    s.PropertyType.SHOP: 'shops'
}

CMP_TABLE = {
    s.PropertyType.WAREHOUSE: s.warehouse_comparisons,
    s.PropertyType.LAND: s.land_comparisons,
    s.PropertyType.OFFICE: s.office_comparisons,
    s.PropertyType.SHOP: s.shop_comparisons,
}
AD_TYPE = {
    s.AdType.SELL: 'Venda',
    s.AdType.RENT: 'Locacão',
}

ZONE = {
    s.Zone.NORTH: 'NORTE',
    s.Zone.EAST: 'LESTE',
    s.Zone.WEST: 'OESTE',
    s.Zone.SOUTH: 'SUL',
    s.Zone.CENTER: 'CENTRO',
}

ADDRESS_FLDS = {
    'cep': 'CEP',
    'street': 'Rua',
    'number': 'Numero',
    'district': 'Bairo',
    'city': 'Cidade',
    'region': 'Região',
}

COSTS = {
    'iptu': 'IPTU, R$/m2',
    'condominium': 'Condomínio, R$/m2',
    'foro': 'Foro, R$/m2',
}


SLCT_FLD = {
    'modify': {
        'select': lambda row: f'<input type="checkbox" name="select_{row["id"]}" value="{row["id"]}">'
    },
    'rename': {'select': 'Selecionados'},
}

CMP_MODIFY = {
    'address': lambda row: f"{row['district']} - {row['city']}",
    'flr_capacity': lambda row: (f"{row['min_flr_capacity']}"
                                 if f"{row['min_flr_capacity']}" == f"{row['max_flr_capacity']}"
                                 else f"{row['min_flr_capacity']} a {row['max_flr_capacity']}"),
    'details': lambda row: f"<a hx-get='/comparisons/{row['id']}/{row['ppt_type']}' hx-target='#dialog' hx-swap='innerHTML'>Details</a>",
    'available': lambda row: (f"{row['min_available']}"
                              if f"{row['min_available']}" == f"{row['max_available']}"
                              else f"{row['min_available']} a {row['max_available']}"),
    'height': lambda row: (f"{row['min_height']}"
                          if f"{row['min_height']}" == f"{row['max_height']}"
                          else f"{row['min_height']} a {row['max_height']}"),
    'energy': lambda row: (f"{row['min_energy']}"
                            if f"{row['min_energy']}" == f"{row['max_energy']}"
                            else f"{row['min_energy']} a {row['max_energy']}"),
    'width': lambda row: (f"{row['min_width']}"
                          if f"{row['min_width']}" == f"{row['max_width']}"
                          else f"{row['min_width']} a {row['max_width']}"),
}

FLDS_MODIFICATIONS = {
    'rent':{
        'comparisons': {
            **SLCT_FLD['modify'],
            **CMP_MODIFY,
            # 'height': lambda row: (f"{row['min_height']}"
            #                               if f"{row['min_height']}" == f"{row['max_height']}"
            #                               else f"{row['min_height']} a {row['max_height']}"),
        },
    }
}

RENAME = {
    'select': 'Selecionados',
    'details': 'Detalhes',
    'title': 'Ref.',
    'address': 'Endereço',
    'cep': 'CEP',
    'street': 'Rua',
    'number': 'Numero',
    'district': 'Bairro',
    'city': 'Cidade',
    'region': 'Região',
    'available': 'Disponível',
    'height': 'Pé direito, m',
    'efficiency': 'Eficiência logistica, %',
    'abl': 'ABL, m2',
    'docks': 'Docas',
    'flr_capacity': 'Piso, ton/m2',
    'office_area': 'Escritório / Mezanino, m2',
    'energy': 'Capacidade Elétrica, kVa',
    'width': 'Entre pilares, m',
    'condominium': 'Condominio, R$/mes',
    'iptu': 'IPTU, R$/mes',
    'foro': 'Foro, R$/mes',
    'rent': 'Locacão, R$/mes',
    'sell': 'Venta, R$',
    'price': 'Total, R$/mes',
}

MODIFICATIONS = {
    'select': lambda row: f'<input type="checkbox" name="select_{row["id"]}" value="{row["id"]}">',
    'address': lambda row: f"{row['district']} - {row['city']}",
    'flr_capacity': lambda row: (f"{row['min_flr_capacity']}"
                                 if f"{row['min_flr_capacity']}" == f"{row['max_flr_capacity']}"
                                 else f"{row['min_flr_capacity']} a {row['max_flr_capacity']}"),
    'details': lambda row: f"<a hx-get='/comparisons/{row['id']}/{row['ppt_type']}' hx-target='#dialog' hx-swap='innerHTML'>{RENAME['details']}</a>",
    'available': lambda row: (f"{row['min_available']}"
                              if f"{row['min_available']}" == f"{row['max_available']}"
                              else f"{row['min_available']} a {row['max_available']}"),
    'height': lambda row: (f"{row['min_height']}"
                          if f"{row['min_height']}" == f"{row['max_height']}"
                          else f"{row['min_height']} a {row['max_height']}"),
    'energy': lambda row: (f"{row['min_energy']}"
                            if f"{row['min_energy']}" == f"{row['max_energy']}"
                            else f"{row['min_energy']} a {row['max_energy']}"),
    'width': lambda row: (f"{row['min_width']}"
                          if f"{row['min_width']}" == f"{row['max_width']}"
                          else f"{row['min_width']} a {row['max_width']}"),
}

BASIC_RENAME = {
    # 'rent': 'Valor, R$',
    # 'area': 'Area Total, m2',
    'title': 'Ref.',
    'available': 'Disponível',
    'height': 'Pé direito, m',
    'efficiency': 'Eficiência logistica, %',
    'abl': 'ABL, m2',
    'docks': 'Docas',
    'flr_capacity': 'Piso, ton/m2',
}

MDL_RENAME = {
    **BASIC_RENAME,
    'office_area': 'Escritório / Mezanino, m2',
    'energy': 'Capacidade Elétrica, kVa',
    'width': 'Entre pilares, m',
    'condominium': 'Condominio, R$/mes',
    'iptu': 'IPTU, R$/mes',
    'foro': 'Foro, R$/mes',
    'rent': 'Locacão, R$/mes',
    'price': 'Total, R$/mes',
}

CMP_RENAME = {
    'address': 'Bairro',
    'price': 'Total, R$/mes',
    **BASIC_RENAME,
}

# correspondance and sequence of eng to pt field's names
FLDS_RENAME = {
    'comparisons': {
        **SLCT_FLD['rename'],
        'details': 'Detalhes',
        'address': 'Bairro',
        'price': 'Total, R$/mes',
        **BASIC_RENAME,
    },
    'modules': {
        **MDL_RENAME
    },
    'properties': {
        **SLCT_FLD['rename'],
        **MDL_RENAME,
    }
}

FILTER_FLDS = {
    "ad_type": AD_TYPE,
    "ppt_type": PPT_TYPE
}

BROKERS = {
    'broker_id': ('Corretor1', 'Corretor2', 'Corretor3')
}

RANGES = {
    'price': {'minimum': 0, 'step': 5, 'maximum': 1000, 'label': 'Valor, R$/m2'},
    'area': {'minimum': 0, 'step': 10, 'maximum': 1000, 'label': 'Area Total, m2'},
    'height': {'minimum': 0, 'step': 1, 'maximum': 20, 'label': 'Pé direito, m'},
    'efficiency': {'minimum': 0, 'step': 10, 'maximum': 100, 'label': 'Eficiência logistica, %'},
    'abl': {'minimum': 0, 'step': 10, 'maximum': 1000, 'label': 'ABL, m2'},
    'doks': {'minimum': 0, 'step': 5, 'maximum': 100, 'label': 'Docas'},
    'flr_capacity': {'minimum': 0, 'step': 1, 'maximum': 20, 'label': 'Piso, ton/m2'},
    'office_area': {'minimum': 0, 'step': 10, 'maximum': 1000, 'label': 'Escritório/Mezanino, m2'},
    'energy': {'minimum': 0, 'step': 5, 'maximum': 100, 'label': 'Capacidade de energia, kVa'},
    # 'last_update': {'minimum': 0, 'step': 10, 'maximum': 1000, 'label': 'Dias da última atualização'},
}

INFRA = ('Refrigeração', 'Segurança', 'ETE')

def costs_const(price_per: str = 'm2') -> dict:
    return {
        'condominium': f'Condominio, R$/{price_per}',
        'iptu': f'IPTU, R$/{price_per}',
        'foro': f'Foro, R$/{price_per}',
    }

MDL_COL = {
    # 'rent': 'Valor, R$',
    # 'area': 'Area Total, m2',
    'title': 'Ref.',
    'height': 'Pé direito, m',
    # 'efficiency': 'Eficiência logistica, %',
    'abl': 'ABL, m2',
    'docks': 'Docas',
    'flr_capacity': 'Piso, ton/m2',
    'office_area': 'Escritório / Mezanino, m2',
    'energy': 'Capacidade de energia, kVa',
    'width': 'Entre pilares, m',
    'available': 'Disponível',
}

# PDF creation section
# Page size (2000px by 1414px)
PAGE_WIDTH = 2000
PAGE_HEIGHT = 1414

# Padding
LR_PADDING = 100
TOP_PADDING = 600

COVER_BGD = "assets/backgrounds/cover.jpg"
BODY_BGD = "assets/backgrounds/body.jpg"
ABOUT_BGD = "assets/backgrounds/about.jpg" # will be changed with code, probably
LAST_PAGE_BGD = "assets/backgrounds/last_page.jpg"
static_map_image = "assets/backgrounds/map.jpg"  # Pre-generated static map with pins

PPT_DTLS_FLDS = {
    **BASIC_RENAME,
    'iptu': 'IPTU',
    'condominium': 'Condomínio',
    'rent': ...
}