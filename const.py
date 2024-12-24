import mysettings as s

DESCR = "test description"

NA = "not_available"
ZERO = 0
ANONIM = "anonim"
INFR_EDIT = "edit-infr"

FLTR_MULT_CHOICE_FLDS = (
    "city_id",
    "region_id",
    "district_id",
    "infr_id",
    "avcb_id",
)

EMPLOYEES = (
    s.Role.BROKER,
    s.Role.ADMIN,
    s.Role.SECRETARY,
)

STATUS_TYPE = {
    s.Status.ACTIVE: "Ativo",
    s.Status.ARCHIVE: "Arquivado",
    s.Status.NEW: "Novo",
}

SECRETARY_REGISTER = {
    s.Role.OWNER: "Proprietário",
    s.Role.USER: "Usuário",
}

ROLE_TYPE = {
    s.Role.BROKER: "Corretor",
    s.Role.ADMIN: "Administrador",
    s.Role.SECRETARY: "Secretária",
    **SECRETARY_REGISTER,
}

ROLE_FLDS = {
    "client_id": s.Role.USER,
    "broker_id": s.Role.BROKER,
    "owner_id": s.Role.OWNER,
}

ROLE_FK = {
    s.Role.USER: "client_id",
    s.Role.BROKER: "broker_id",
    s.Role.OWNER: "owner_id",
}

CHOICE_TYPE = {
    s.Choice.BOTH: "Tanto faz",
    s.Choice.YES: "Sim",
    s.Choice.NO: "Não",
}

PPT_TYPE = {
    s.PropertyType.WAREHOUSE: "Galpão",
    s.PropertyType.LAND: "Terreno",
    s.PropertyType.OFFICE: "Escritório",
    s.PropertyType.SHOP: "Loja",
}

AD_TYPE = {
    s.AdType.RENT: "Locacão",
    s.AdType.SELL: "Venta",
}

AD_TYPE_FLDS = {
    s.AdType.RENT: "rent",
    s.AdType.SELL: "sell",
}

R_M2 = "R$/m2"
R_MONTH = "R$/mes"

RENAME_FLDS = {
    "select": "Selecionados",
    "edit": "Editar",
    "name": "Nome de Condominio / Monousuário",
    "cep": "CEP",
    "street": "Rua",
    "str_number": "Numero",
    "block": "Complemento",
    "district": "Bairo",
    "city": "Cidade",
    "region": "Região",
    "iptu": "IPTU",
    "condominium": "Condomínio",
    "foro": "Foro",
    "details": "Detalhes",
    "title": "Unidade",
    "address": "Endereço",
    "available": "Disponível",
    "height": "Pé direito, m",
    "efficiency": "Eficiência logistica, %",
    "docks": "Docas",
    "flr_capacity": "Piso, ton/m2",
    "office_area": "Escritório / Mezanino, m2",
    "energy": "Capacidade Elétrica, kVa",
    "width": "Entre pilares, m",
    "rent": "Locacão",
    "sell": "Venta",
    "price": "Preço",
    "client_id": "Cliente",
    "broker_id": "Corretor",
    "owner_id": "Proprietario",
    "infr_id": "Infraestrutura",
    "street_id": "Rua",
    "district_id": "Bairo",
    "city_id": "Cidade",
    "region_id": "Região",
    "avcb_id": "AVCB",
    "area": "Area Total, m2",
    "in_conodminium": "Em condomínio",
    "on_site": "Publicar no Site",
    "retha_admin": "Administração Retha",
    "under_construction": "Em construção",
    "sprinklers": "Sprinklers",
    "dock_leveler": "Nivelador de doca",
    "refrigeration": "Refrigeração",
    "between_pilars": "Entre pilares, m x m",
    "ppt_type": "Tipo de propriedade",
    "ad_type": "Tipo de anúncio",
    "role": "Role",
    "archives": "Arquivar",
    "visits": "Agendar visita",
    "download_pdf": "Download site selection",
    "comparisons": "Adicionar à comparação",
    "unit_frm": "Adicionar unidade",
    "infrs": "Infraestrutura:",
    "pdfs": "PDF:",
    "imgs": "Fotos:",
}

COSTS_FLDS = ("iptu", "condominium", "foro")

FILTER_FLDS = {"ad_type": AD_TYPE, "ppt_type": PPT_TYPE}

MIN_MAX = {
    "min": "minimum",
    "max": "maximum",
}

RANGES = {
    "price": {"minimum": 0, "step": 5, "maximum": 1000},
    "rent": {"minimum": 0, "step": 5, "maximum": 1000},
    "sell": {"minimum": 0, "step": 5, "maximum": 1000},
    "area": {"minimum": 0, "step": 10, "maximum": 1000},
    "height": {"minimum": 0, "step": 1, "maximum": 20},
    "efficiency": {"minimum": 0, "step": 10, "maximum": 100},
    "abl": {"minimum": 0, "step": 10, "maximum": 1000},
    "docks": {"minimum": 0, "step": 5, "maximum": 100},
    "flr_capacity": {"minimum": 0, "step": 1, "maximum": 20},
    "office_area": {"minimum": 0, "step": 10, "maximum": 1000},
    "energy": {"minimum": 0, "step": 5, "maximum": 100},
    # 'last_update': {'minimum': 0, 'step': 10, 'maximum': 1000},
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
ABOUT_BGD = "assets/backgrounds/about.jpg"  # will be changed with code, probably
LAST_PAGE_BGD = "assets/backgrounds/last_page.jpg"
static_map_image = "assets/backgrounds/map.jpg"  # Pre-generated static map with pins
