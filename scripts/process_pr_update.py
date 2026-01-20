"""
Process validated PR: copy added images to main, run update, commit results, then comment on PR.

Behavior:
- Reads validate_info.json produced by validate_update_files.py
- Copies added images and template files from PR branch into main branch
- Runs scripts/update.py (which will run convert.py to update README)
- Commits and pushes changes to main
- Comments on PR summarizing actions (PR branch is NOT modified)
- Does NOT reset contributor's branch (per new policy)

"""
import os
import sys
import subprocess
import json
import requests

# ensure project root on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def run(cmd, check=True, cwd=None):
    print('RUN:', ' '.join(cmd))
    return subprocess.run(cmd, check=check, cwd=cwd)


def get_pr_info():
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if not event_path:
        return None
    with open(event_path, 'r', encoding='utf-8') as f:
        ev = json.load(f)
    pr = ev.get('pull_request')
    return pr


def main():
    repo_root = os.path.dirname(os.path.dirname(__file__))
    pr = get_pr_info()
    if not pr:
        print('No PR info available; aborting processing')
        sys.exit(1)
    pr_num = pr.get('number')
    pr_branch = pr.get('head', {}).get('ref')
    token = os.environ.get('GITHUB_TOKEN')
    if not pr_branch or not token:
        print('Missing PR branch or GITHUB_TOKEN')
        sys.exit(1)

    info_path = os.path.join(os.path.dirname(__file__), 'validate_info.json')
    if not os.path.exists(info_path):
        print('No validate_info.json found; aborting')
        sys.exit(1)
    with open(info_path, 'r', encoding='utf-8') as f:
        info = json.load(f)

    added_images = info.get('added_images', [])
    json_changed = info.get('json_changed', False)
    xlsx_changed = info.get('xlsx_changed', False)

    figure_dir = None
    # determine figure_dir basename from config
    import configparser
    cfg_path = os.path.join(repo_root, 'config', 'setting.config')
    cp = configparser.ConfigParser()
    cp.read(cfg_path, encoding='utf-8')
    paths = cp['paths'] if 'paths' in cp else {}
    figure_dir = paths.get('figure_dir', 'figures') if paths else 'figures'
    if os.path.isabs(figure_dir):
        figure_dir = os.path.basename(figure_dir)
    figure_dir = figure_dir.replace('\\', '/').rstrip('/')

    # Checkout main and prepare for changes
    run(['git', 'fetch', 'origin', 'main'])
    run(['git', 'checkout', 'main'])
    run(['git', 'reset', '--hard', 'origin/main'])

    # Merge added images from PR branch into main (only added images)
    files_to_add = []
    for f in added_images:
        # Ensure file exists in PR branch
        run(['git', 'checkout', pr_branch, '--', f])
        files_to_add.append(f)

    # Also copy templates from PR branch into working tree if changed
    if json_changed:
        run(['git', 'checkout', pr_branch, '--', 'submit_template.json'])
        files_to_add.append('submit_template.json')
    if xlsx_changed:
        run(['git', 'checkout', pr_branch, '--', 'submit_template.xlsx'])
        files_to_add.append('submit_template.xlsx')

    # If there are files to add, stage them
    if files_to_add:
        run(['git', 'add'] + files_to_add)
        run(['git', 'commit', '-m', f'Apply assets from PR #{pr_num}: add images/templates'])
        run(['git', 'push', 'origin', 'main'])

    # Run update processor (works on submit_template.* in repo root)
    # We run it under scripts/
    try:
        run([sys.executable, 'update.py'], cwd=os.path.join(repo_root, 'scripts'))
    except subprocess.CalledProcessError as e:
        print('update.py failed:', e)
        # comment PR with failure
        comment_on_pr(pr_num, f'Update processor failed: {e}')
        sys.exit(1)

    # After update.py, commit any changes (database, README)
    run(['git', 'add', '.'])
    run(['git', 'commit', '-m', f'Automated update from PR #{pr_num}'], check=False)
    run(['git', 'push', 'origin', 'main'])

    # Clear submit_template.json/xlsx in main (create empty ones)
    with open(os.path.join(repo_root, 'submit_template.json'), 'w', encoding='utf-8') as f:
        json.dump({'papers': []}, f, ensure_ascii=False)
    # create empty xlsx via pandas if available
    try:
        import pandas as pd
        df = pd.DataFrame()
        df.to_excel(os.path.join(repo_root, 'submit_template.xlsx'), index=False)
    except Exception:
        # fallback: touch file
        open(os.path.join(repo_root, 'submit_template.xlsx'), 'a').close()

    run(['git', 'add', 'submit_template.json', 'submit_template.xlsx'])
    run(['git', 'commit', '-m', f'Clear update files after processing PR #{pr_num}'], check=False)
    run(['git', 'push', 'origin', 'main'])

    # Do NOT reset PR branch. Just comment on PR with results.
    comment_on_pr(pr_num, f'Processed PR #{pr_num}: added {len(added_images)} image(s), database and README updated. PR branch was NOT modified. Only the approved images/templates were applied to main.')

    print('Processing complete')


def comment_on_pr(pr_num, message):
    token = os.environ.get('GITHUB_TOKEN')
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if not token or not event_path:
        print('Cannot comment on PR: missing token or event payload')
        return
    with open(event_path, 'r', encoding='utf-8') as f:
        ev = json.load(f)
    repo = ev.get('repository', {}).get('full_name')
    owner, repo_name = repo.split('/')
    url = f'https://api.github.com/repos/{owner}/{repo_name}/issues/{pr_num}/comments'
    headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
    requests.post(url, headers=headers, json={'body': message})


if __name__ == '__main__':
    main()
