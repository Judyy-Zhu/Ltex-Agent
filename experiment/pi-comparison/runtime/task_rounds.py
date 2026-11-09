"""Five whole-task candidates, shared across every file and helper name."""
import json
import hashlib
from pathlib import Path
from recovery import save


class TaskRounds:
    def __init__(self,root,job):
        self.path=Path(root)/'task-rounds.json'
        self.limit=job.get('max_task_rounds')

    def read(self):
        return json.loads(self.path.read_text()) if self.path.exists() else {'limit':self.limit,'rounds':[]}

    def save(self,data):
        save(self.path,data)

    def begin(self,receipt_id=None,kind='candidate',api_attempt_id=None,source=None):
        if self.limit is None:return None
        data=self.read()
        used=len(data['rounds'])-data.get('window_start',0)
        if used>=self.limit:
            data['exhausted']=True;self.save(data)
            raise ValueError('Whole-task round limit exhausted; no sixth candidate is permitted')
        number=len(data['rounds'])+1
        data['rounds'].append({'round':number,'window_round':used+1,'kind':kind,'receipt_id':receipt_id,'status':'checking',
                               **({'api_attempt_id':api_attempt_id} if api_attempt_id is not None else {}),
                               **(source or {})})
        data['exhausted']=False;self.save(data);return number

    def finish(self,number,passed,reason=None):
        if number is None:return
        data=self.read();entry=data['rounds'][number-1]
        entry.update(status='passed' if passed else 'failed',passed=bool(passed),reason=reason)
        active=data['rounds'][data.get('window_start',0):]
        data['exhausted']=len(active)>=self.limit and not passed
        data['transport_only_exhausted']=bool(data['exhausted'] and all(r.get('kind')=='transport' for r in active))
        self.save(data)

    def unused_generation(self,reason):
        number=self.begin(kind='generation');self.finish(number,False,reason)

    def transport_failure(self,reason,api_attempt_id=None):
        number=self.begin(kind='transport',api_attempt_id=api_attempt_id);self.finish(number,False,reason)

    def reopen_transport_window(self):
        data=self.read()
        if not data.get('transport_only_exhausted'):return False
        data.update(window_start=len(data['rounds']),exhausted=False,transport_only_exhausted=False)
        self.save(data);return True

    def accepted_candidate(self):
        candidates=[r for r in self.read()['rounds'] if r.get('receipt_id')]
        if not candidates or not candidates[-1].get('passed'):return False
        try:
            receipt=json.loads((self.path.parent/'receipts'/(candidates[-1]['receipt_id']+'.json')).read_text())
            name=receipt['entry']
            if Path(name).is_absolute() or '..' in Path(name).parts:return False
            current=hashlib.sha256((self.path.parent/'work'/name).read_bytes()).hexdigest()
            return receipt['passed'] and current==receipt['source_hashes'][name]
        except (OSError,ValueError,KeyError):return False

    def summary(self):
        data=self.read();active=data['rounds'][data.get('window_start',0):];used=len(active)
        return {'limit':self.limit,'used':used,'remaining':None if self.limit is None else max(0,self.limit-used),
                'total_used':len(data['rounds']),'exhausted':data.get('exhausted',False),
                'transport_only_exhausted':data.get('transport_only_exhausted',False),
                'rounds':active,'history':data['rounds']}
