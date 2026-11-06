import fitz
from pathlib import Path

out_dir = Path('data/real_blueprints')
log_file = out_dir / 'inspection_log.txt'

lines = []
for name, fname in [
    ('Yukuhashi Public Renovation Drawings', 'Yukuhashi_3965.pdf'),
    ('Saitama Prefectural Architectural Set A', 'Saitama_403886.pdf'),
    ('Saitama Prefectural Architectural Set B', 'Saitama_403883.pdf'),
    ('Atsugi Existing Facility Set', 'ATSUGI-KIZONN-PUBLIC-FACILITY-5P.pdf'),
    ('Nagareyama Architectural Plans', 'NAGAREYAMA-ISYOU-SCHEDULE-AND-PLANS-3P.pdf')
]:
    p = out_dir / fname
    if not p.exists():
        continue
    doc = fitz.open(str(p))
    lines.append(f'==============================\n{name} ({fname}) - Pages: {len(doc)} - Size: {p.stat().st_size/1024:.1f} KB\n')
    for i in range(min(15, len(doc))):
        page = doc[i]
        txt = page.get_text()
        first_few = [l.strip() for l in txt.splitlines() if l.strip()][:6]
        summary_str = " | ".join(first_few)
        lines.append(f'  [Page {i+1}]: {summary_str}\n')

log_file.write_text(''.join(lines), encoding='utf-8')
print('Wrote inspection_log.txt successfully!')

