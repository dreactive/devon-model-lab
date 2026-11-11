"""Create new local prompt-path manifests; never call a model or modify DEVON."""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'artifacts/experiments/elice-dev30-20261111'
SOURCE = ARCHIVE / 'runs/elice-dev30-10usd-20261111-recovery-4/manifests'

def prepare(devon_root, output):
    devon_root = devon_root.resolve(strict=True)
    output = output.resolve()
    if not output.is_relative_to(ROOT / 'manifests') or output == ROOT / 'manifests' or output.exists():
        raise ValueError('output must be a new directory below this repository/manifests')
    if output.is_relative_to(devon_root):
        raise ValueError('DEVON is read-only')
    plans = ARCHIVE / 'runs/elice-dev30-10usd-20261111-recovery-4/plans'
    plan = json.loads(next(plans.glob('*.json')).read_text(encoding='utf-8-sig'))
    pins = {row['path']: row['sha256'] for row in plan['fingerprints']['devon_source']}
    pins.update({row['file']['path'].replace('\\', '/').split('/devon/', 1)[1]: row['file']['sha256']
                 for row in plan['fingerprints']['prompts']})
    for relative, expected in pins.items():
        source = (devon_root / relative).resolve(strict=True)
        if not source.is_relative_to(devon_root) or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError('DEVON source differs from recorded experiment: ' + relative)
    outputs = {}
    for source in sorted(SOURCE.glob('*.json')):
        data = json.loads(source.read_text(encoding='utf-8-sig'))
        for prompt in data['prompts']:
            old = prompt['template_path'].replace('\\', '/')
            relative = old.split('/devon/', 1)[1]
            path = (devon_root / relative).resolve(strict=True)
            if not path.is_relative_to(devon_root) or hashlib.sha256(path.read_bytes()).hexdigest() != pins[relative]:
                raise ValueError('DEVON prompt differs from recorded experiment: ' + relative)
            prompt['template_path'] = os.path.relpath(path, output).replace('\\', '/')
        outputs[source.name] = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    if len(outputs) != 6:
        raise ValueError('expected six model manifests')
    output.mkdir(parents=True)
    for name, content in outputs.items():
        (output / name).write_text(content, encoding='utf-8')
    return {'created': [str(output / name) for name in outputs], 'model_calls': 0,
            'note': 'Path-only copies of final 2000-output-token manifests; no approval is copied.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--devon-root', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.devon_root, args.output_dir), ensure_ascii=False, indent=2))
