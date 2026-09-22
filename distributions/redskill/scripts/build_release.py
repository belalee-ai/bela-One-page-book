"""Build allowlisted release archives, never copying user books or local work folders."""
from pathlib import Path
import hashlib,json,zipfile
BASE=Path(__file__).resolve().parent.parent
FILES=['SKILL.md','README.md','INSTALL.md','TESTING.md']
DIRS=['agents','assets','docs','examples','references','scripts','vendor']
def build(root,name,out):
 paths=[]
 for item in FILES:
  if (root/item).is_file():paths.append(root/item)
 for folder in DIRS:
  if (root/folder).exists():paths.extend(p for p in (root/folder).rglob('*') if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and 'node_modules' not in p.parts and p.suffix!='.pyc' and p.name!='.DS_Store')
 entries={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
 archive=out/(name+'-0.2.zip')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for p in paths:z.write(p,name+'/'+p.relative_to(root).as_posix())
  z.writestr(name+'/MANIFEST.json',json.dumps(entries,ensure_ascii=False,indent=2))
 return archive.name,hashlib.sha256(archive.read_bytes()).hexdigest(),len(paths),archive.stat().st_size
if __name__=='__main__':
 out=BASE/'release-artifacts';out.mkdir(exist_ok=True)
 name=next(line.split(':',1)[1].strip() for line in (BASE/'SKILL.md').read_text().splitlines() if line.startswith('name:'))
 results=[build(BASE,name,out)]
 if (BASE/'distributions/redskill/SKILL.md').exists():results.append(build(BASE/'distributions/redskill','bela-one-page-book-redskill',out))
 (out/'SHA256.txt').write_text(''.join(f'{h}  {name}\n' for name,h,_,_ in results))
 for row in results:print(row)
