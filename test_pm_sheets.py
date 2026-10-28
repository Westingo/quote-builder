import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pymupdf as fitz
from fastapi.testclient import TestClient
import app
import pm_sheets

SAMPLE = dict(account='12345',zone='8',ticket='',months='March, June, September, December',starting_month='March',frequency='Quarterly',customer='Example Maintenance Site',address='100 Example Way\nExample City, OR 97000',contact='Contact Name — 503.555.0100',created='3/10/15',phone='503.555.0100 — Contact Name',scope='Quarterly Preventive Maintenance Service on One Double Swing Elite CSW-200 at North Entry / Exit and One Elite SL-3000 at South Entry / Exit',checklist='Includes Lubrication, Adjustments and Inspection For Wear\nIf Need For Further Repairs Are Found, They Will Be Quoted First\nIf UL325 Required Safety Warning Signs Are Unreadable Or Missing, Replace at $10/ea\nReplace Batteries on CSL-24V if Test Fails Below 10% of Rated Value at $29/ea',price='280.00',notes='Need a key from office to open padlock on slide operator [padlock is for Tomar strobe]\nGates held open via software\nAsk the site contact for access.')

class PMSheetsTest(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(app.app)
    def test_pdf_layout_and_embedded_data(self):
        with fitz.open(stream=pm_sheets.render(SAMPLE),filetype='pdf') as doc:
            self.assertEqual(len(doc),1)
            self.assertEqual(tuple(doc[0].rect),(0,0,612,792))
            text=doc[0].get_text().replace('\xa0',' ')
            for value in ['Example Maintenance','280.00','Total Time:','September']:
                self.assertIn(value,text)
            for removed in ['Material', 'Labor', 'Cost', 'Price', 'T -']:
                self.assertNotIn(removed,text)
            import json
            self.assertEqual(json.loads(doc.embfile_get('worksheet.metropm')),SAMPLE)
    def test_schedule_intervals_and_year_wrap(self):
        for frequency, expected in [('Quarterly','November, February, May, August'), ('Semiannual','November, May'), ('Annual','November')]:
            data={**SAMPLE,'starting_month':'November','frequency':frequency,'months':'stale value'}
            self.assertEqual(pm_sheets.validate(data)['months'],expected)
            with fitz.open(stream=pm_sheets.render(data),filetype='pdf') as doc:
                import json
                self.assertEqual(json.loads(doc.embfile_get('worksheet.metropm'))['months'],expected)
        for change in [{'starting_month':'Smarch'},{'frequency':'Monthly'}]:
            self.assertEqual(self.client.post('/api/pm/preview',json={**SAMPLE,**change}).status_code,400)
        self.assertEqual(pm_sheets.validate({**SAMPLE,'frequency':''})['months'],'')
        legacy={k:v for k,v in SAMPLE.items() if k not in ('starting_month','frequency')}
        self.assertEqual(pm_sheets.validate(legacy)['months'],SAMPLE['months'])

    def test_overflow_is_rejected(self):
        result=self.client.post('/api/pm/preview',json={**SAMPLE,'notes':'too much text '*300})
        self.assertEqual(result.status_code,400)
        self.assertIn('does not fit',result.json()['detail'])
    def test_save_reopen_and_duplicate(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(pm_sheets,'STORE',Path(folder)):
            first=self.client.post('/api/pm/sheets',json=SAMPLE).json()['id']
            second=self.client.post('/api/pm/sheets',json=SAMPLE).json()['id']
            self.assertNotEqual(first,second)
            revised={**SAMPLE,'price':'350.00','id':first}
            self.assertEqual(self.client.post('/api/pm/sheets',json=revised).status_code,200)
            self.assertEqual(self.client.get('/api/pm/sheets/'+first).json()['price'],'350.00')
            self.assertEqual(self.client.get('/api/pm/sheets/'+second).json()['price'],'280.00')
            self.assertEqual(len(self.client.get('/api/pm/sheets').json()),2)
            self.assertEqual(self.client.post('/api/pm/sheets',json={**SAMPLE,'id':'../escape'}).status_code,400)
    def test_preview_pdf_and_invalid_fields(self):
        self.assertEqual(self.client.post('/api/pm/preview',json=SAMPLE).headers['content-type'],'image/png')
        self.assertEqual(self.client.post('/api/pm/pdf',json=SAMPLE).headers['content-type'],'application/pdf')
        self.assertEqual(self.client.post('/api/pm/preview',json={'months':[]}).status_code,400)
        self.assertEqual(self.client.post('/api/pm/sheets',json={}).status_code,400)

if __name__=='__main__':
    unittest.main()
