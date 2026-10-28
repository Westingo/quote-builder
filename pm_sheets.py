"""Publisher-style preventive maintenance worksheets and local contract storage."""
import json
import os
import re
import tempfile
import uuid
from pathlib import Path

import pymupdf as fitz
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix='/api/pm')
STORE = Path(__file__).resolve().parent / 'pm_sheets'
FIELDS = ('account', 'zone', 'ticket', 'months', 'starting_month', 'frequency', 'customer', 'address',
          'contact', 'created', 'phone', 'scope', 'checklist', 'price', 'notes')


MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')
FREQUENCIES = {'Quarterly': 3, 'Semiannual': 6, 'Annual': 12}

def validate(data):
    result = {}
    for key in FIELDS:
        value = data.get(key, '')
        if not isinstance(value, str):
            raise ValueError(f'{key} must be text.')
        if len(value) > 5000:
            raise ValueError(f'{key} is too long.')
        result[key] = value.strip()
    start, frequency = result['starting_month'], result['frequency']
    if start and start not in MONTHS:
        raise ValueError('Choose a valid starting month.')
    if frequency and frequency not in FREQUENCIES:
        raise ValueError('Choose Quarterly, Semiannual, or Annual.')
    if start and frequency:
        step = FREQUENCIES[frequency]
        result['months'] = ', '.join(MONTHS[(MONTHS.index(start)+offset)%12] for offset in range(0,12,step))
    elif 'starting_month' in data or 'frequency' in data:
        result['months'] = ''
    return result


def render(data):
    """Letter-sized worksheet. Reject overflow instead of silently clipping text."""
    d = validate(data)
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    fonts = {}
    for bold, filename in [(False, 'arial.ttf'), (True, 'arialbd.ttf')]:
        path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / filename
        font = fitz.Font(fontfile=str(path)) if path.exists() else fitz.Font('cjk')
        name = 'PMBold' if bold else 'PMRegular'
        page.insert_font(fontname=name, fontbuffer=font.buffer)
        fonts[bold] = (name, font)
    def box(text, x, y, w, h, size=10, bold=False, align=0):
        if not text:
            return
        remaining = page.insert_textbox(fitz.Rect(x, y, x+w, y+h), text,
            fontname=fonts[bold][0], fontsize=size, lineheight=1.25, align=align)
        if remaining < 0:
            raise ValueError('Text does not fit on one page. Shorten the customer/contact, scope, checklist, or notes and preview again.')
    def line(x, y, x2, y2):
        page.draw_line((x,y), (x2,y2), width=.5)
    def rect(x, y, w, h):
        page.draw_rect(fitz.Rect(x,y,x+w,y+h), width=.6)
    box('Account #'+d['account'], 74, 52, 185, 22, 9)
    rect(275,48,59,24)
    box('Zone #'+d['zone'], 278,55,53,15,9,align=1)
    box('Ticket # '+(d['ticket'] or '__________________'), 410,53,130,25,9)
    months = [s.strip() for s in d['months'].split(',') if s.strip()]
    # Center the automatically scheduled visit months without emphasizing a single visit.
    widths = [fonts[False][1].text_length(m+(',' if i<len(months)-1 else ''), fontsize=13)
        for i,m in enumerate(months)]
    total = sum(widths)+10*max(0,len(months)-1)
    if total > 468:
        raise ValueError('Service months are too wide. Use abbreviated month names.')
    x = 72+(468-total)/2
    for i,m in enumerate(months):
        box(m+(',' if i<len(months)-1 else ''),x,79,widths[i]+2,22,13)
        x += widths[i]+10
    line(72,99,540,99)
    rect(72,108,468,63)
    line(306,108,306,171)
    box('\n'.join(filter(None,[d['customer'],d['address']])),75,113,226,56)
    box('Contact: '+d['contact'],310,113,226,56)
    box('Date Created:    '+d['created'],74,180,208,20,9)
    box('Phone:  '+d['phone'],291,180,249,20,9)
    rect(72,198,468,158)
    box(d['scope'],75,204,460,40)
    items = ['•   '+s.strip().lstrip('•').strip() for s in d['checklist'].splitlines() if s.strip()]
    box('\n'.join(items),75,245,459,80)
    box(('$ '+d['price']) if d['price'] else '',385,331,151,20,10,align=2)
    for i,label in enumerate(['Tech:', 'Leave:', 'Arrive:', 'Depart:', 'Total Time:']):
        y=370+17*i
        box(label,74,y,68,17)
        line(132 if i==4 else 111,y+12,230,y+12)
    for i,label in enumerate(['Date Complete:', 'Contacted:']):
        y=370+17*i
        box(label,363,y,80,17)
        line(440,y+12,534,y+12)
    box('Notes:',74,466,80,18)
    box(d['notes'],74,480,465,104)
    doc.embfile_add('worksheet.metropm',json.dumps(d,ensure_ascii=False).encode('utf-8'))
    doc.subset_fonts()
    content=doc.tobytes(garbage=4,deflate=True)
    doc.close()
    return content


def checked(data):
    try:
        return render(data)
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc


@router.post('/preview')
def preview(data: dict = Body(...)):
    with fitz.open(stream=checked(data),filetype='pdf') as doc:
        return Response(doc[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).tobytes('png'),media_type='image/png')


@router.post('/pdf')
def pdf(data: dict = Body(...)):
    content = checked(data)
    name = re.sub(r'[^a-zA-Z0-9-]+','-',data.get('customer','')).strip('-') or 'PM-sheet'
    return Response(content,media_type='application/pdf',headers={
        'Content-Disposition':f'attachment; filename="{name}-PM.pdf"'})


@router.get('/sheets')
def listing():
    out=[]
    for path in STORE.glob('*.json'):
        try:
            data=json.loads(path.read_text(encoding='utf-8'))
            out.append({'id':path.stem,'customer':data['customer'],'account':data['account'],'mtime':path.stat().st_mtime})
        except (OSError,ValueError,KeyError):
            continue
    return sorted(out,key=lambda row:row['mtime'],reverse=True)


def sheet_path(identifier):
    if not re.fullmatch(r'[a-f0-9]{32}',identifier):
        raise HTTPException(400,'Invalid worksheet ID.')
    return STORE / (identifier+'.json')


@router.get('/sheets/{identifier}')
def load(identifier: str):
    path=sheet_path(identifier)
    if not path.exists():
        raise HTTPException(404,'Worksheet not found.')
    return json.loads(path.read_text(encoding='utf-8'))


@router.post('/sheets')
def save(data: dict = Body(...)):
    try:
        clean=validate(data)
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc
    if not clean['customer']:
        raise HTTPException(400,'Customer / site is required to save.')
    identifier=data.get('id') or uuid.uuid4().hex
    path=sheet_path(identifier)
    STORE.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=STORE,suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(clean,stream,ensure_ascii=False,indent=2)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return {'id':identifier}
