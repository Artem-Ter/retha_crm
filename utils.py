import os

from fasthtml.common import UploadFile
from mysettings import (BASE_DIR, cities, db, districts, infrastructures,
                        ppt_images, regions, streets)


async def save_img(ppt_id: int, img: UploadFile) -> None:
    img_filename = f'{ppt_id}_{img.filename}'
    img_path = os.path.join(f'{BASE_DIR}/images', img_filename)
    # Save the image file to the server
    with open(img_path, "wb") as f:
        f.write(await img.read())
    ppt_images.insert({'ppt_id': ppt_id,
                       'img': f'/images/{img_filename}'})

def get_or_create(tbl: str, name: str) -> int:
    """Get or create item in db. Return item id"""
    qry = f"""
    SELECT id
    FROM {tbl}
    WHERE LOWER(name) = ?
    LIMIT 1
    """
    itm = db.q(qry, (name.lower(),))
    if itm:
        return itm[0]['id']
    d = {
        'streets': streets,
        'districts': districts,
        'cities': cities,
        'regions': regions,
        'infrastructures': infrastructures,
    }
    itm = d[tbl].insert(name=name)
    return itm['id']
