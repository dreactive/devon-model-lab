"""Prepare or execute the explicitly authorized, fixed sixteen-case Elice campaign."""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import argparse
import asyncio
import json
from pathlib import Path
from campaign_runtime import prepare_campaign,prepare_continuation,execute_campaign,LAB_ROOT


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--prepare',action='store_true')
    mode.add_argument('--execute',action='store_true')
    parser.add_argument('--devon-root',type=Path,default=LAB_ROOT.parent/'devon')
    parser.add_argument('--campaign',type=Path,default=LAB_ROOT/'campaigns/dev-30pct-10usd.json')
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--bundle',type=Path)
    parser.add_argument('--continue-from',dest='continue_from',type=Path,
                        help='Prepare the one explicitly authorized first404 continuation; retains its full unknown-cost hold.')
    parser.add_argument('--env-file',type=Path,default=LAB_ROOT/'.env')
    args=parser.parse_args(argv)
    try:
        if args.execute:
            if args.continue_from is not None:raise ValueError('continuation_prepare_only')
            if args.bundle is None:raise ValueError('bundle_required')
            result=asyncio.run(execute_campaign(args.bundle,env_path=args.env_file))
            print(json.dumps({'run_state':result['run_state'],'global_budget':result['global_budget'],
                'recorded_cases':result['recorded_cases'],'pending_jobs':result['pending_jobs']}))
            return 0 if result['run_state']=='completed' else 1
        if args.output_dir is None:raise ValueError('output_directory_required')
        if args.continue_from is not None:
            bundle=prepare_continuation(args.continue_from,args.output_dir,env_path=args.env_file)
        else:
            bundle=prepare_campaign(args.devon_root,args.campaign,args.output_dir,env_path=args.env_file)
        print(json.dumps({'status':'prepared_only','jobs':len(bundle['jobs']),'budget_usd_total':'10.00',
            'max_http_attempts_total':192,'active_budget_usd':bundle.get('active_budget_usd','10.00'),
            'active_max_http_attempts':bundle.get('active_max_http_attempts',192),
            'API_calls':0,'bundle_path':str(args.output_dir/'bundle.json')}))
        return 0
    except Exception:
        print(json.dumps({'status':'blocked','error':'campaign_rejected'}))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
