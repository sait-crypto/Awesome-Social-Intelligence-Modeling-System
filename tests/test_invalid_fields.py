import sys
sys.path.insert(0, '.')
from src.core.database_manager import DatabaseManager
from src.core.database_model import Paper

db = DatabaseManager()
df = db.load_database()

# 检查 invalid_fields 列是否存在
print(f"Database columns: {list(df.columns)}")
print()

if 'invalid fields' in df.columns:
    print('✓ Column "invalid fields" exists')
    col_data = df['invalid fields'].astype(str)
    non_empty = (col_data.str.strip() != '').sum()
    print(f'  Non-empty values: {non_empty}')
    print()
    
    # Show sample values
    if non_empty > 0:
        print('  Sample values with invalid_fields:')
        for idx, val in enumerate(df['invalid fields']):
            if val and str(val).strip() not in ['', '0', 'False', 'false']:
                title = df['title'].iloc[idx] if 'title' in df.columns else f'Row {idx}'
                print(f'    {title[:50]}: invalid_fields={repr(val)}')
                if idx > 4:
                    print('    ...')
                    break
else:
    print('✗ Column "invalid fields" NOT FOUND')

# Now test by loading as Paper objects
print('\n' + '='*60)
print('Loading papers and checking invalid_fields:')
print('='*60)

papers = db.update_utils.excel_to_paper(df, only_non_system=False, skip_invalid=False)
print(f'Total papers loaded: {len(papers)}')

papers_with_invalid = [p for p in papers if getattr(p, 'invalid_fields', '')]
print(f'Papers with invalid_fields set: {len(papers_with_invalid)}')

if papers_with_invalid:
    print('\nSample papers with invalid_fields:')
    for p in papers_with_invalid[:3]:
        print(f'  {p.title[:50]}: invalid_fields={repr(p.invalid_fields)}')
